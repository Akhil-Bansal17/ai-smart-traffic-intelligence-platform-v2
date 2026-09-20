"""
Deterministic test fixture video source for live monitoring loop verification.
Phase 21: Live Traffic Monitoring & Camera Source Management.

IMPORTANT:
- Explicitly labeled TEST_FIXTURE.
- Never represents observations as REAL_WORLD or LIVE.
- Deterministic synthetic frames with moving vehicle geometries.
- Does not generate random vehicle counts or synthetic ML datasets.
"""
from dataclasses import dataclass
import time
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class FixtureMetadata:
    width: int = 640
    height: int = 480
    fps: float = 10.0
    source_type: str = "test_fixture"
    is_live: bool = False
    provenance_tag: str = "test_fixture_observation"


class TestFixtureCameraSource:
    """
    Deterministic frame generator simulating a live traffic camera stream.
    Provides controllable frame rates, deterministic moving vehicle contours,
    and simulated network failure injection for reconnect testing.
    """
    __test__ = False

    def __init__(
        self,
        source_id: str = "test_fixture_01",
        width: int = 640,
        height: int = 480,
        fps: float = 10.0,
    ):
        self.source_id = source_id
        self.width = width
        self.height = height
        self.fps = fps if fps > 0 else 10.0
        self._connected = False
        self._frame_index = 0
        self._start_time: Optional[float] = None
        self._failures_remaining = 0
        self.reconnect_count = 0
        self.dropped_frames = 0
        self.frames_acquired = 0

    def connect(self) -> bool:
        """Connects to the fixture source."""
        self._connected = True
        self._start_time = time.monotonic()
        return True

    def is_connected(self) -> bool:
        """Returns whether the source is currently connected and active."""
        return self._connected

    def read_metadata(self) -> FixtureMetadata:
        """Returns metadata describing the deterministic fixture stream."""
        return FixtureMetadata(
            width=self.width,
            height=self.height,
            fps=self.fps,
            source_type="test_fixture",
            is_live=False,
            provenance_tag="test_fixture_observation",
        )

    def simulate_transient_failure(self, failure_count: int = 1) -> None:
        """Injects artificial frame acquisition failures to test reconnect behavior."""
        self._failures_remaining = max(0, failure_count)

    def reconnect(self) -> bool:
        """Simulates reconnecting to the fixture feed."""
        self.reconnect_count += 1
        self._connected = True
        return True

    def release(self) -> None:
        """Releases the fixture source."""
        self._connected = False

    def read_frame(self) -> Optional[tuple[int, float, np.ndarray]]:
        """
        Generates and returns the next deterministic synthetic frame:
        (frame_index, timestamp_seconds, bgr_numpy_array).
        Returns None if source is disconnected or experiencing injected failure.
        """
        if not self._connected:
            return None

        if self._failures_remaining > 0:
            self._failures_remaining -= 1
            return None

        # Build synthetic frame
        frame = np.full((self.height, self.width, 3), 45, dtype=np.uint8)

        # Draw road lane markings (two lanes)
        lane_divider_y = int(self.height / 2)
        cv2.line(frame, (0, lane_divider_y), (self.width, lane_divider_y), (100, 100, 100), 2)
        for x in range(0, self.width, 40):
            cv2.line(frame, (x, lane_divider_y), (x + 20, lane_divider_y), (200, 200, 200), 2)

        # Deterministic moving vehicles:
        # Vehicle 1: moving left-to-right (inbound) on lane 1 (upper half)
        # Position wraps every 100 frames
        cycle_1 = self._frame_index % 100
        v1_x = int((cycle_1 / 100.0) * (self.width + 120)) - 60
        v1_y = int(self.height * 0.25)
        if -40 <= v1_x <= self.width:
            cv2.rectangle(frame, (v1_x, v1_y), (v1_x + 50, v1_y + 30), (180, 130, 70), -1)
            cv2.rectangle(frame, (v1_x, v1_y), (v1_x + 50, v1_y + 30), (255, 255, 255), 1)

        # Vehicle 2: moving right-to-left (outbound) on lane 2 (lower half)
        cycle_2 = (self._frame_index + 40) % 100
        v2_x = self.width - int((cycle_2 / 100.0) * (self.width + 120)) + 60
        v2_y = int(self.height * 0.70)
        if -40 <= v2_x <= self.width:
            cv2.rectangle(frame, (v2_x, v2_y), (v2_x + 50, v2_y + 30), (70, 130, 180), -1)
            cv2.rectangle(frame, (v2_x, v2_y), (v2_x + 50, v2_y + 30), (255, 255, 255), 1)

        timestamp_sec = round(self._frame_index / self.fps, 3)
        idx = self._frame_index
        self._frame_index += 1
        self.frames_acquired += 1

        return (idx, timestamp_sec, frame)
