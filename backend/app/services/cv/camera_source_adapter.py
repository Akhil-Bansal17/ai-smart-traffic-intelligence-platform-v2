"""
Camera source adapter abstraction and frame acquisition layer.
Phase 21: Live Traffic Monitoring & Camera Source Management.

Provides unified interface for local cameras, RTSP network streams,
HTTP video streams, and deterministic test fixtures with bounded buffering,
frame-drop tracking, and bounded reconnect logic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import queue
import threading
import time
from typing import Optional

import cv2
import numpy as np

from app.config.settings import settings
from app.core.credential_sanitizer import redact_uri_credentials
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.services.cv.test_fixture_source import TestFixtureCameraSource

logger = get_logger(__name__)


@dataclass(frozen=True)
class CameraMetadata:
    width: int
    height: int
    fps: float
    source_type: str
    is_live: bool
    codec: str = "unknown"
    provenance_tag: str = "live_observation"


class BaseCameraSource(ABC):
    """Abstract base class for all camera stream sources."""

    def __init__(self, source_id: str, source_type: str, uri: str):
        self.source_id = source_id
        self.source_type = source_type
        self.uri = uri
        self.reconnect_count = 0
        self.dropped_frames = 0
        self.frames_acquired = 0
        self._connected = False

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the underlying camera source."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the source is currently connected."""
        pass

    @abstractmethod
    def read_metadata(self) -> CameraMetadata:
        """Returns structural metadata about the stream."""
        pass

    @abstractmethod
    def read_frame(self, timeout_seconds: float = 5.0) -> Optional[tuple[int, float, np.ndarray]]:
        """
        Reads and returns the next frame: (frame_index, timestamp_seconds, frame_bgr).
        Returns None on timeout, EOF, or source failure.
        """
        pass

    @abstractmethod
    def reconnect(self) -> bool:
        """Attempts to reconnect to the stream."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Releases underlying native handles and worker threads."""
        pass


class OpenCVCameraSource(BaseCameraSource):
    """
    OpenCV-backed camera source for local hardware cameras, RTSP streams,
    and HTTP/MJPEG streams.
    Uses a bounded queue and dedicated reader thread to decouple frame acquisition
    from inference, enforcing latest-frame-wins backpressure and tracking dropped frames.
    """

    def __init__(self, source_id: str, source_type: str, uri: str):
        super().__init__(source_id, source_type, uri)
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=settings.live_frame_queue_size)
        self._width = 640
        self._height = 480
        self._fps = 30.0
        self._frame_index = 0
        self._start_time: Optional[float] = None

    def connect(self) -> bool:
        with self._lock:
            if self._connected:
                return True

            redacted = redact_uri_credentials(self.uri)
            logger.info("Connecting to OpenCV camera source %s (%s)", self.source_id, redacted)

            try:
                # Local camera passes int device index, RTSP/HTTP passes URL string
                if self.source_type == "local_camera" and (self.uri.isdigit() or self.uri == "0"):
                    dev_index = int(self.uri)
                    cap = cv2.VideoCapture(dev_index)
                else:
                    cap = cv2.VideoCapture(self.uri)

                if not cap.isOpened():
                    logger.warning("Failed to open camera stream %s (%s)", self.source_id, redacted)
                    return False

                # Configure bounded buffering if supported by backend
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                f = float(cap.get(cv2.CAP_PROP_FPS))

                self._width = w if w > 0 else 640
                self._height = h if h > 0 else 480
                self._fps = f if f > 0 else 30.0
                self._cap = cap
                self._connected = True
                self._start_time = time.monotonic()

                # Start bounded background reader thread
                self._stop_event.clear()
                self._reader_thread = threading.Thread(
                    target=self._capture_loop,
                    name=f"camera-reader-{self.source_id[:8]}",
                    daemon=True,
                )
                self._reader_thread.start()
                logger.info(
                    "Connected to camera %s: %sx%s @ %.1f FPS",
                    self.source_id,
                    self._width,
                    self._height,
                    self._fps,
                )
                return True

            except Exception as err:
                logger.error("Error opening camera %s: %s", self.source_id, err)
                return False

    def is_connected(self) -> bool:
        return self._connected and self._cap is not None and self._cap.isOpened()

    def read_metadata(self) -> CameraMetadata:
        provenance = "unverified_live" if self.source_type != "test_fixture" else "test_fixture_observation"
        return CameraMetadata(
            width=self._width,
            height=self._height,
            fps=self._fps,
            source_type=self.source_type,
            is_live=True,
            codec="raw",
            provenance_tag=provenance,
        )

    def _capture_loop(self) -> None:
        """Background acquisition thread maintaining bounded queue."""
        while not self._stop_event.is_set():
            if not self._cap or not self._cap.isOpened():
                break

            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            self.frames_acquired += 1
            now = time.monotonic()
            elapsed = now - (self._start_time or now)
            idx = self._frame_index
            self._frame_index += 1

            frame_item = (idx, round(elapsed, 3), frame)

            # Enforce bounded buffer: drop oldest frame when queue is full
            try:
                self._frame_queue.put_nowait(frame_item)
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()
                    self.dropped_frames += 1
                    self._frame_queue.put_nowait(frame_item)
                except Exception:
                    pass

    def read_frame(self, timeout_seconds: float = 5.0) -> Optional[tuple[int, float, np.ndarray]]:
        if not self._connected:
            return None

        try:
            return self._frame_queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def reconnect(self) -> bool:
        """Bounded reconnection attempt."""
        logger.warning(
            "Attempting reconnection for camera %s (attempt %s/%s)",
            self.source_id,
            self.reconnect_count + 1,
            settings.live_reconnect_attempts,
        )
        self.reconnect_count += 1
        self.release()
        time.sleep(settings.live_reconnect_delay_seconds)
        return self.connect()

    def release(self) -> None:
        with self._lock:
            self._stop_event.set()
            if self._reader_thread and self._reader_thread.is_alive():
                self._reader_thread.join(timeout=1.0)
                self._reader_thread = None

            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception as err:
                    logger.warning("Error releasing camera handle: %s", err)
                self._cap = None

            self._connected = False
            # Drain queue
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except Exception:
                    break


class TestFixtureSourceAdapter(BaseCameraSource):
    """Adapter wrapping TestFixtureCameraSource into the BaseCameraSource protocol."""

    def __init__(self, source_id: str, uri: str = "test_fixture"):
        super().__init__(source_id, "test_fixture", uri)
        self._fixture = TestFixtureCameraSource(source_id=source_id)

    def connect(self) -> bool:
        self._connected = self._fixture.connect()
        return self._connected

    def is_connected(self) -> bool:
        return self._fixture.is_connected()

    def read_metadata(self) -> CameraMetadata:
        meta = self._fixture.read_metadata()
        return CameraMetadata(
            width=meta.width,
            height=meta.height,
            fps=meta.fps,
            source_type=meta.source_type,
            is_live=False,
            codec="synthetic",
            provenance_tag="test_fixture_observation",
        )

    def read_frame(self, timeout_seconds: float = 5.0) -> Optional[tuple[int, float, np.ndarray]]:
        frame = self._fixture.read_frame()
        self.frames_acquired = self._fixture.frames_acquired
        return frame

    def simulate_transient_failure(self, count: int = 1) -> None:
        self._fixture.simulate_transient_failure(count)

    def reconnect(self) -> bool:
        self.reconnect_count += 1
        return self._fixture.reconnect()

    def release(self) -> None:
        self._fixture.release()
        self._connected = False


def create_camera_source(source_id: str, source_type: str, uri: str) -> BaseCameraSource:
    """
    Factory creating the appropriate camera source adapter based on source_type.
    """
    norm_type = source_type.lower().strip()
    if norm_type in ("test_fixture", "fixture"):
        return TestFixtureSourceAdapter(source_id=source_id, uri=uri)
    elif norm_type in ("local_camera", "rtsp", "http_stream", "file"):
        return OpenCVCameraSource(source_id=source_id, source_type=norm_type, uri=uri)
    else:
        raise AppException(
            f"Unsupported camera source type: '{source_type}'",
            code="unsupported_source_type",
            status_code=422,
        )
