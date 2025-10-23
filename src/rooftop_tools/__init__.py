"""Rooftop tools for geospatial analysis and sampling."""

from . import roads, rooftops, s2
from .visualization import generate_colormap

__all__ = [
    "s2",
    "rooftops",
    "roads",
    "generate_colormap",
]


def hello() -> str:
    return "Hello from rooftop-tools!"
