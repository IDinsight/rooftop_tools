"""S2 cell coverage calculation for geographic areas."""

import geopandas as gpd
from s2cell.s2cell import lat_lon_to_cell_id

from .geometry import get_s2_cell_polygons


def get_s2_cells_containing_points(points, level=6) -> list[int]:
    """
    Find unique S2 cell IDs that contain the given points.

    For each point in the GeoDataFrame, this function identifies which S2 cell
    contains that point at the specified level and returns the unique set of
    cell IDs. Multiple points may fall within the same cell.

    This is a helper function used by get_s2_cells_covering_geodataframe() to
    identify initial candidate cells based on geometry centroids.

    Parameters:
    - points: GeoDataFrame with point geometries in WGS84 (EPSG:4326) CRS
    - level: S2 cell level (default=6, which is used for India; other countries typically
             require different levels). Higher levels = smaller cells

    Returns:
    - list[int]: List of unique S2 cell IDs containing the input points

    Raises:
    - ValueError: If GeoDataFrame is not in EPSG:4326 CRS
    """
    # check if crs is set to WGS84 (EPSG:4326)
    if points.crs is None or points.crs.to_string() != "EPSG:4326":
        raise ValueError("Points GeoDataFrame must be in WGS84 (EPSG:4326) CRS.")

    # convert points to S2 cell IDs
    s2_cell_id_list = points.geometry.apply(
        lambda geom: lat_lon_to_cell_id(geom.y, geom.x, level)
    )
    s2_cell_ids = s2_cell_id_list.unique().tolist()

    return s2_cell_ids


def get_s2_cells_covering_geodataframe(gdf, level=6) -> list[int]:
    """
    Find all S2 cell IDs needed to fully cover the areas in a GeoDataFrame.

    This function ensures complete spatial coverage by iteratively identifying S2 cells
    until every part of every geometry in the GeoDataFrame is covered. It starts with
    cells containing geometry centroids, then adds additional cells for any "spillover"
    areas that extend beyond initial cell boundaries.

    Useful for determining which S2-indexed data files need to be downloaded to cover
    a region of interest.

    Parameters:
    - gdf: GeoDataFrame in WGS84 (EPSG:4326) CRS containing areas to cover
    - level: S2 cell level (default=6, which is used for India; other countries typically
             require different levels). Higher levels = smaller cells = more tiles

    Returns:
    - list[int]: List of S2 cell IDs that completely cover all geometries in the GeoDataFrame

    Raises:
    - ValueError: If GeoDataFrame is not in EPSG:4326 CRS

    Example:
        >>> import geopandas as gpd
        >>> district_boundaries = gpd.read_file("districts.geojson")
        >>> s2_cells = get_s2_cells_covering_geodataframe(district_boundaries)
        >>> print(f"Need to download {len(s2_cells)} S2 data files")
    """

    # check if crs is set to WGS84 (EPSG:4326)
    if gdf.crs is None or gdf.crs.to_string() != "EPSG:4326":
        raise ValueError("GeoDataFrame must be in WGS84 (EPSG:4326) CRS.")

    # generate initial S2 cell IDs from the GeoDataFrame centroids
    points = gdf.geometry.centroid.to_frame(name="geometry")
    s2_cell_ids = get_s2_cells_containing_points(points, level=level)

    # get initial S2 cell shapes and check for full coverage
    s2_cell_shapes = get_s2_cell_polygons(s2_cell_ids)
    leftover_shapes = gdf.difference(s2_cell_shapes.unary_union)
    leftover_shapes = leftover_shapes[~leftover_shapes.is_empty]

    print(f"Shapes with spillover after round 1: {len(leftover_shapes)}")

    step = 2
    while len(leftover_shapes) > 0:
        # get new s2 cell IDs from the leftover shapes
        points_new = leftover_shapes.geometry.centroid.to_frame(name="geometry")
        s2_cell_ids_new = get_s2_cells_containing_points(
            points_new, level=level
        )

        # get new s2 cell shapes
        s2_cell_shapes = get_s2_cell_polygons(s2_cell_ids_new)
        leftover_shapes = leftover_shapes.difference(s2_cell_shapes.unary_union)
        leftover_shapes = leftover_shapes[~leftover_shapes.is_empty]

        # add new s2 cell IDs to the existing list
        s2_cell_ids = s2_cell_ids + s2_cell_ids_new

        print(f"Shapes with spillover after round {step}: {len(leftover_shapes)}")
        step += 1

    return s2_cell_ids
