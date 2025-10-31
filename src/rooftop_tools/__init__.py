"""Rooftop tools for geospatial analysis and sampling."""

from . import points, merging, s2
from .points import (
    gen_map_link,
    get_nearest_points_on_road,
    get_nearest_points_on_road_api_call,
)
from .visualization import generate_colormap

__all__ = [
    "points",
    "merging",
    "s2",
    "generate_colormap",
    "gen_map_link",
    "get_nearest_points_on_road",
    "get_nearest_points_on_road_api_call",
]


def hello() -> str:
    return "Hello from rooftop-tools!"
