"""
app/services/video_source.py
--------------------------------------------------------------------
Unified abstraction over every kind of video input the system
supports: webcam, RTSP stream, IP camera, or an uploaded/recorded
video file. Downstream code (detection sessions) just calls
`read_frame()` and doesn't care where the pixels came from.

Design notes:
  - Uses OpenCV's VideoCapture, which already handles files, webcam
    indices, and RTSP/HTTP URLs (via FFmpeg backend) transparently.
  - RTSP/IP camera streams get a small reconnect-retry loop since
    network cameras drop frames/connections in the real world --
    a naive read() failure would otherwise kill the whole session.
  - Frame skipping is implemented here (not in the detector) so CPU
    time is saved on decode+detect, not just detect.
--------------------------------------------------------------------
"""

from __future__ import annotations

import time
from typing import Generator, Optional

import cv2
import numpy as np

from app.core.logging import logger
from app.schemas.detection import SourceType


class VideoSourceError(RuntimeError):
    """Raised when a video source cannot be opened or read from."""


class VideoSource:
    """Opens and reads frames from webcam / RTSP / IP camera / file sources."""

    RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY_SEC = 2.0

    def __init__(self, source_type: SourceType, source: str, frame_skip: int = 1):
        self.source_type = source_type
        self.source = source
        self.frame_skip = max(1, frame_skip)
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_live = source_type in (SourceType.WEBCAM, SourceType.RTSP, SourceType.IP_CAMERA)
        self._open()

    def _resolve_capture_target(self) -> int | str:
        """Webcam sources use an integer device index; everything else is a string URL/path."""
        if self.source_type == SourceType.WEBCAM:
            try:
                return int(self.source)
            except ValueError as exc:
                raise VideoSourceError(
                    f"Webcam source must be a device index (e.g. '0'), got '{self.source}'"
                ) from exc
        return self.source

    def _open(self) -> None:
        target = self._resolve_capture_target()
        logger.info(f"Opening video source: type={self.source_type} target={target}")
        cap = cv2.VideoCapture(target)
        if not cap.isOpened():
            raise VideoSourceError(f"Failed to open video source: {self.source}")
        self._cap = cap

    @property
    def fps(self) -> float:
        if self._cap is None:
            return 0.0
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        return fps if fps and fps > 0 else 25.0  # sensible fallback for webcams that report 0

    @property
    def total_frames(self) -> Optional[int]:
        """None for live sources (webcam/RTSP), an int for files."""
        if self._is_live or self._cap is None:
            return None
        count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return count if count > 0 else None

    def _read_with_reconnect(self) -> tuple[bool, np.ndarray | None]:
        """Read a frame; for live network sources, retry-reconnect on failure."""
        assert self._cap is not None
        ok, frame = self._cap.read()
        if ok:
            return ok, frame

        if not self._is_live:
            return False, None  # end of file -- not an error, just done

        logger.warning(f"Frame read failed for live source '{self.source}', attempting reconnect")
        for attempt in range(1, self.RECONNECT_ATTEMPTS + 1):
            time.sleep(self.RECONNECT_DELAY_SEC)
            self._cap.release()
            try:
                self._open()
                ok, frame = self._cap.read()
                if ok:
                    logger.info(f"Reconnected to source '{self.source}' on attempt {attempt}")
                    return ok, frame
            except VideoSourceError:
                logger.warning(f"Reconnect attempt {attempt}/{self.RECONNECT_ATTEMPTS} failed")

        return False, None

    def frames(self) -> Generator[tuple[int, np.ndarray], None, None]:
        """
        Yields (frame_index, frame) tuples, honoring frame_skip.
        Stops naturally at end-of-file for recorded videos, or on
        unrecoverable failure for live sources.
        """
        frame_index = 0
        while True:
            ok, frame = self._read_with_reconnect()
            if not ok or frame is None:
                logger.info(f"Video source '{self.source}' exhausted or unreadable, stopping")
                break

            if frame_index % self.frame_skip == 0:
                yield frame_index, frame

            frame_index += 1

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            logger.debug(f"Released video source: {self.source}")
