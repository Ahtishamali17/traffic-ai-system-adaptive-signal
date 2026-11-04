"""
Unit tests for app/services/heatmap.py. Requires numpy/opencv only
(already installed for other draw-related tests).
"""

import numpy as np

from app.services.heatmap import HeatmapAccumulator


def test_add_point_increments_correct_cell():
    heatmap = HeatmapAccumulator(frame_width=640, frame_height=480, cell_size=20)
    heatmap.add_point(x=100, y=100)
    row, col = 100 // 20, 100 // 20
    assert heatmap.grid[row, col] == 1.0
    assert heatmap.total_observations() == 1


def test_add_point_clamps_out_of_bounds():
    heatmap = HeatmapAccumulator(frame_width=640, frame_height=480, cell_size=20)
    heatmap.add_point(x=10000, y=10000)  # way outside the frame
    assert heatmap.total_observations() == 1  # still recorded, clamped to last cell


def test_render_overlay_returns_same_shape_and_dtype():
    heatmap = HeatmapAccumulator(frame_width=64, frame_height=48, cell_size=8)
    for _ in range(5):
        heatmap.add_point(x=32, y=24)

    base_frame = np.zeros((48, 64, 3), dtype=np.uint8)
    overlay = heatmap.render_overlay(base_frame)

    assert overlay.shape == base_frame.shape
    assert overlay.dtype == np.uint8


def test_render_overlay_with_no_data_returns_unchanged_copy():
    heatmap = HeatmapAccumulator(frame_width=64, frame_height=48, cell_size=8)
    base_frame = np.full((48, 64, 3), 100, dtype=np.uint8)
    overlay = heatmap.render_overlay(base_frame)
    assert np.array_equal(overlay, base_frame)


def test_reset_clears_grid():
    heatmap = HeatmapAccumulator(frame_width=64, frame_height=48, cell_size=8)
    heatmap.add_point(x=10, y=10)
    assert heatmap.total_observations() == 1
    heatmap.reset()
    assert heatmap.total_observations() == 0
