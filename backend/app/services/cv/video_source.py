"""
VideoSource module: metadata extraction and frame decoding foundation.

Acts as the computer vision pipeline's frame extraction source.
Decodes video on demand with configurable sampling rate (driven by PROCESSING_FPS)
to avoid unnecessary decoding overhead.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

import cv2
import numpy as np

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    resolution: str
    fps: float
    frame_count: int
    duration_seconds: float
    codec: str


class VideoSource:
    """
    Video stream reader and frame extraction engine.
    Supports context manager pattern for safe native handle management.
    """

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path).resolve()
        if not self.file_path.exists():
            raise AppException("Video file not found.", code="file_not_found", status_code=404)
        self._cap: Optional[cv2.VideoCapture] = None

    def __enter__(self) -> "VideoSource":
        self._open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    def _open(self) -> cv2.VideoCapture:
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(str(self.file_path))
            if not self._cap.isOpened():
                raise AppException(
                    "Unable to open video stream. The file may be corrupted or in an unsupported format.",
                    code="corrupted_video",
                    status_code=400,
                )
        return self._cap

    def release(self) -> None:
        """Release underlying OpenCV VideoCapture handle."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def read_metadata(self) -> VideoMetadata:
        """
        Validate content readability and extract structural metadata.
        Throws AppException if the file cannot be decoded.
        """
        cap = self._open()

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))

        # Decode fourcc codec tag
        codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()

        # Sanity check: must be able to read at least the first frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, first_frame = cap.read()
        if not ret or first_frame is None:
            raise AppException(
                "Video stream contains no readable frames or is corrupted.",
                code="corrupted_video",
                status_code=400,
            )

        # Handle edge case where fps or frame_count is 0 or unpopulated
        if fps <= 0:
            fps = 30.0  # Fallback assumption
        if frame_count <= 0:
            frame_count = 1

        duration_seconds = round(frame_count / fps, 2)
        resolution = f"{width}x{height}"

        metadata = VideoMetadata(
            width=width,
            height=height,
            resolution=resolution,
            fps=round(fps, 2),
            frame_count=frame_count,
            duration_seconds=duration_seconds,
            codec=codec or "unknown",
        )
        logger.debug("Extracted metadata for video: %s", metadata)
        return metadata

    def extract_frames(
        self,
        target_fps: Optional[int] = None,
        max_frames: Optional[int] = None,
    ) -> Generator[tuple[int, float, np.ndarray], None, None]:
        """
        Sample and yield video frames.
        Yields (frame_index, timestamp_seconds, frame_bgr_ndarray).

        If target_fps is provided (or configured in settings.processing_fps),
        samples frames at that rate rather than decoding every frame.
        """
        cap = self._open()
        metadata = self.read_metadata()

        source_fps = metadata.fps if metadata.fps > 0 else 30.0
        sample_fps = target_fps if target_fps is not None else settings.processing_fps

        # Determine frame skip step
        step = max(1, int(round(source_fps / sample_fps))) if sample_fps > 0 else 1

        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        frame_idx = 0
        yielded_count = 0

        while True:
            if max_frames is not None and yielded_count >= max_frames:
                break

            ret = cap.grab()
            if not ret:
                break

            if frame_idx % step == 0:
                ret, frame = cap.retrieve()
                if not ret or frame is None:
                    break

                timestamp_sec = round(frame_idx / source_fps, 3)
                yield (frame_idx, timestamp_sec, frame)
                yielded_count += 1

            frame_idx += 1
