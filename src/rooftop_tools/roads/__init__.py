"""Road snapping operations using Google Roads API."""

from .snapping import (
    get_nearest_points_on_road,
    get_nearest_points_on_road_api_call,
)

__all__ = [
    "get_nearest_points_on_road",
    "get_nearest_points_on_road_api_call",
]
