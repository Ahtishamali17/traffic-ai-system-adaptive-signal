"""
app/services/heatmap.py
--------------------------------------------------------------------
Accumulates vehicle centroid positions into a coarse density grid
over the lifetime of a session, then renders it as a color-mapped
overlay -- this is the "vehicle heatmap" / "traffic density
estimation" feature.

Kept as a simple grid-counter rather than a full kernel-density
estimate: it's O(1) per frame to update, needs no extra dependency
beyond OpenCV/NumPy (already required), and is precise enough for
"which areas of this scene see the most traffic" at typical camera
resolutions.
--------------------------------------------------------------------
"""

from __future__ import annotations

import cv2
import numpy as np


class HeatmapAccumulator:
    """Grid-based density accumulator for one camera's frame area."""

    def __init__(self, frame_width: int, frame_height: int, cell_size: int = 20):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cell_size = cell_size
        self.cols = max(1, frame_width // cell_size)
        self.rows = max(1, frame_height // cell_size)
        self.grid = np.zeros((self.rows, self.cols), dtype=np.float32)

    def add_point(self, x: float, y: float) -> None:
        """Record one vehicle-centroid observation."""
        col = min(int(x // self.cell_size), self.cols - 1)
        row = min(int(y // self.cell_size), self.rows - 1)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.grid[row, col] += 1.0

    def render_overlay(self, base_frame: np.ndarray, alpha: float = 0.45) -> np.ndarray:
        """
        Returns a copy of base_frame with a color-mapped heatmap blended
        on top. Cells with zero observations are left fully transparent
        (not tinted), so empty areas of the scene aren't colored.
        """
        if self.grid.max() <= 0:
            return base_frame.copy()

        normalized = (self.grid / self.grid.max() * 255).astype(np.uint8)
        normalized_resized = cv2.resize(
            normalized, (self.frame_width, self.frame_height), interpolation=cv2.INTER_LINEAR
        )
        colored = cv2.applyColorMap(normalized_resized, cv2.COLORMAP_JET)

        mask = (normalized_resized > 5).astype(np.uint8) * 255
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0

        result = base_frame.copy().astype(np.float32)
        blended = result * (1 - alpha * mask_3ch) + colored.astype(np.float32) * (alpha * mask_3ch)
        return blended.astype(np.uint8)

    def reset(self) -> None:
        self.grid.fill(0)

    def total_observations(self) -> int:
        return int(self.grid.sum())
