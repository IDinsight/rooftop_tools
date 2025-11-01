"""Rooftop tools for geospatial analysis and sampling."""

from . import points, merging, s2
from .points import (
    gen_map_link,
    gen_directions_link,
    get_nearest_points_on_road,
    get_nearest_points_on_road_api_call,
)
from .merging import (
    match_all_rooftops_to_psus,
    match_s2_rooftops_to_psus,
)

from .s2 import (
    get_s2_cell_polygon,
    get_s2_cell_polygons,
    get_s2_cells_containing_points,
    get_s2_cells_covering_geodataframe,
)


__all__ = [
    "points",
    "merging",
    "s2",
    "generate_colormap",
    "gen_map_link",
    "gen_directions_link",
    "get_nearest_points_on_road",
    "get_nearest_points_on_road_api_call",
    "match_all_rooftops_to_psus",
    "match_s2_rooftops_to_psus",
    "get_s2_cell_polygon",
    "get_s2_cell_polygons",
    "get_s2_cells_containing_points",
    "get_s2_cells_covering_geodataframe",
]


