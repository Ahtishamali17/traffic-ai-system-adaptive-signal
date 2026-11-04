"""
app/utils/geometry.py
--------------------------------------------------------------------
Small, dependency-free geometry helpers shared by ROI/zone checks,
violation detection, and heatmaps.
--------------------------------------------------------------------
"""

from __future__ import annotations

from app.schemas.detection import LinePoint


def point_in_polygon(x: float, y: float, polygon: list[LinePoint]) -> bool:
    """
    Standard ray-casting point-in-polygon test.
    Returns True if (x, y) lies inside the polygon defined by `polygon`
    (list of at least 3 vertices, in order).
    """
    if len(polygon) < 3:
        return False

    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y

        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside
