"""
Backward compatibility module.

This module re-exports all functions from the new modular structure.
For new code, prefer importing directly from submodules:
    - rooftop_tools.s2
    - rooftop_tools.rooftops
    - rooftop_tools.roads
    - rooftop_tools.visualization
"""

# S2 operations
from .s2.coverage import (
    get_s2_cells_containing_points,
    get_s2_cells_covering_geodataframe,
)
from .s2.geometry import get_s2_cell_polygon, get_s2_cell_polygons

# Rooftop operations
from .rooftops.matching import get_matched_rooftop_centroids_from_s2_file
from .rooftops.sampling import sample_rooftops

# Road snapping
from .roads.snapping import (
    get_nearest_points_on_road,
    get_nearest_points_on_road_api_call,
)

# Visualization
from .visualization import generate_colormap

__all__ = [
    # S2
    "get_s2_cell_polygon",
    "get_s2_cell_polygons",
    "get_s2_cells_containing_points",
    "get_s2_cells_covering_geodataframe",
    # Rooftops
    "get_matched_rooftop_centroids_from_s2_file",
    "sample_rooftops",
    # Roads
    "get_nearest_points_on_road",
    "get_nearest_points_on_road_api_call",
    # Visualization
    "generate_colormap",
]
