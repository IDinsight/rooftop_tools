import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import geopandas as gpd
import matplotlib.cm
import numpy as np
import requests
import s2sphere
from s2cell.s2cell import lat_lon_to_cell_id
from shapely import Point
from shapely.geometry import Polygon
from tqdm.notebook import tqdm


def generate_colormap(N):
    arr = np.arange(N) / N
    N_up = int(math.ceil(N / 7) * 7)
    arr.resize(N_up)
    arr = arr.reshape(7, N_up // 7).T.reshape(-1)
    ret = matplotlib.cm.hsv(arr)
    n = ret[:, 3].size
    a = n // 2
    b = n - a

    # Create arrays of exactly matching sizes
    for i in range(3):
        ret[0:a, i] *= np.linspace(0.2, 1, a)
    ret[a:, 3] *= np.linspace(1, 0.3, b)

    return ret[:N]  # Return only the requested number of colors


def get_s2_cell_polygon(s2_cell_id):
    """
    Convert an S2 cell ID to a shapely polygon.

    Parameters:
    - s2_cell_id (int): The S2 cell ID

    Returns:
    - shapely.geometry.Polygon: Polygon representing the S2 cell
    """
    # Convert string to int if necessary
    if isinstance(s2_cell_id, str):
        s2_cell_id = int(s2_cell_id)

    # Create an S2 cell from the ID
    cell = s2sphere.CellId(s2_cell_id)
    cell = s2sphere.Cell(cell)

    # Extract the vertices of the cell
    vertices = []
    for i in range(4):
        vertex = cell.get_vertex(i)
        lat_lng = s2sphere.LatLng.from_point(vertex)
        vertices.append((lat_lng.lng().degrees, lat_lng.lat().degrees))

    # Close the polygon by repeating the first vertex
    vertices.append(vertices[0])

    # Create a shapely polygon
    return Polygon(vertices)


def get_s2_cell_polygons(s2_cell_ids):
    """
    Convert a list of S2 cell IDs to a GeoDataFrame with polygon geometries.

    Parameters:
    - s2_cell_ids (list): List of S2 cell IDs

    Returns:
    - geopandas.GeoDataFrame: GeoDataFrame with S2 cells as polygons
    """
    geometries = []
    for s2_id in s2_cell_ids:
        polygon = get_s2_cell_polygon(s2_id)
        geometries.append(polygon)

    return gpd.GeoDataFrame(
        {"s2_cell_id": s2_cell_ids, "geometry": geometries}, crs="EPSG:4326"
    )


def get_overlapping_s2_cell_ids_from_points(points, level=6) -> list[int]:
    """
    Get S2 cell IDs for the given points at the specified level.
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


def get_overlapping_s2_cell_ids(gdf, level=6) -> list[int]:
    """
    Get S2 cell IDs of S2 cells that overlap the given GeoDataFrame at the specified level.

    Uses centroids to identify potential S2 cells and then iteratively checks if any area is
    not covered by an S2 cell and continues checking centroids of leftover areas until everywhere
    is covered.

    Parameters:
    - gdf: GeoDataFrame in WGS84 (EPSG:4326) CRS
    - level: int

    Returns:
    - list[int]: List of S2 cell IDs
    """

    # check if crs is set to WGS84 (EPSG:4326)
    if gdf.crs is None or gdf.crs.to_string() != "EPSG:4326":
        raise ValueError("GeoDataFrame must be in WGS84 (EPSG:4326) CRS.")

    # generate initial S2 cell IDs from the GeoDataFrame centroids
    points = gdf.geometry.centroid.to_frame(name="geometry")
    s2_cell_ids = get_overlapping_s2_cell_ids_from_points(points, level=level)

    # get initial S2 cell shapes and check for full coverage
    s2_cell_shapes = get_s2_cell_polygons(s2_cell_ids)
    leftover_shapes = gdf.difference(s2_cell_shapes.unary_union)
    leftover_shapes = leftover_shapes[~leftover_shapes.is_empty]

    print(f"Shapes with spillover after round 1: {len(leftover_shapes)}")

    step = 2
    while len(leftover_shapes) > 0:
        # get new s2 cell IDs from the leftover shapes
        points_new = leftover_shapes.geometry.centroid.to_frame(name="geometry")
        s2_cell_ids_new = get_overlapping_s2_cell_ids_from_points(
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


def get_matched_rooftop_centroids_from_s2_file(
    s2_file_dir: Path, s2_cell_id: int, boundaries_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Get rooftops from the S2 cell file that match the boundaries:
    1. loads the rooftops data for the specified S2 cell ID
    2. filters the rooftops to only those that intersect with the boundaries
    3. returns a GeoDataFrame of the matched rooftops centroids with unique IDs

    Parameters:
    - s2_file_dir (Path): Directory where the S2 rooftops data files are stored.
    - s2_cell_id (int): The S2 cell ID to filter rooftops for.
    - boundaries_gdf (gpd.GeoDataFrame): The GeoDataFrame containing the boundaries.
    """

    # load the rooftops data for the S2 cell
    s2_rooftops_path = s2_file_dir / f"{s2_cell_id}.parquet"
    s2_rooftops_gdf = gpd.read_parquet(s2_rooftops_path)

    # replace polygons with just the centroid of the rooftops
    s2_rooftop_centroids_gdf = s2_rooftops_gdf.set_geometry(
        s2_rooftops_gdf.geometry.centroid
    )

    # filter the boundaries dataset to only the shapes that overlap the S2 cell
    s2_cell_polygon = get_s2_cell_polygon(s2_cell_id)
    boundaries_gdf_s2_overlap = boundaries_gdf[
        boundaries_gdf.intersects(s2_cell_polygon)
    ]

    # perform a spatial join to filter and add area metadata to the rooftops
    matched_rooftop_centroids_gdf = gpd.sjoin(
        s2_rooftop_centroids_gdf,
        boundaries_gdf_s2_overlap,
        how="inner",
        predicate="within",
    ).drop(columns=["index_right"])

    return matched_rooftop_centroids_gdf


def get_nearest_points_on_road_api_call(
    points: list[Point], api_key: str
) -> list[Point | None]:
    """
    Retrieves the nearest points on the road for a list of points using the Google Roads API.
    Max 100 points per request.

    Args:
        points (list[Point]): The points for which to find the nearest point on the road.
        api_key (str): Your Google Roads API key.

    Returns:
        list[Point | None]: List of snapped points (None if not found).
    """
    # checks
    if len(points) > 100:
        raise ValueError(
            "Google Roads API supports a maximum of 100 points per request."
        )
    for pt in points:
        if not isinstance(pt, Point):
            raise ValueError("All points must be of type shapely.geometry.Point")

    # Format: points=lat1,lng1|lat2,lng2|...
    points_param = "|".join(f"{pt.y},{pt.x}" for pt in points)
    url = f"https://roads.googleapis.com/v1/nearestRoads?points={points_param}&key={api_key}"
    response = requests.get(url)
    snapped_points = response.json().get("snappedPoints", [])

    # Map originalIndex to snapped Point
    snapped_dict = {}
    for entry in snapped_points:
        idx = entry.get("originalIndex")
        if (
            idx is not None and idx not in snapped_dict
        ):  # Avoid overwriting if index already exists
            loc = entry["location"]
            snapped_dict[idx] = Point(loc["longitude"], loc["latitude"])

    # Build result in original order, None for points not found
    return [snapped_dict.get(i, None) for i in range(len(points))]


def _get_nearest_points_on_road_api_call_helper(args):
    """Helper function to snap a batch of points to the nearest road."""
    idx_list, points, api_key = args
    try:
        snapped_points = get_nearest_points_on_road_api_call(points, api_key)
        return list(zip(idx_list, snapped_points))
    except Exception as e:
        print(f"Error snapping points at indices {idx_list}: {str(e)}")
        return [(idx, None) for idx in idx_list]


def get_nearest_points_on_road(
    gdf: gpd.GeoDataFrame, api_key: str, max_workers: int = 12
) -> gpd.GeoSeries:
    """
    Snap all points in a GeoDataFrame to the nearest road using parallel processing and batching.

    Args:
        gdf: GeoDataFrame containing point geometries
        api_key: Google Roads API key
        max_workers: Number of parallel workers

    Returns:
        GeoSeries with snapped geometries (order matches input). NOTE: If any point could not be snapped,
        the corresponding entry will be None.
    """

    # Ensure the GeoDataFrame contains only Point geometries
    if not all(gdf.geometry.type == "Point"):
        raise ValueError("GeoDataFrame must contain only Point geometries.")

    points = list(gdf.geometry)
    batch_size = 100  # Google Roads API supports a maximum of 100 points per request
    args_list = []
    for i in range(0, len(points), batch_size):
        idx_list = list(range(i, min(i + batch_size, len(points))))
        batch_points = points[i : i + batch_size]
        args_list.append((idx_list, batch_points, api_key))

    snapped_points = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(
            tqdm(
                executor.map(_get_nearest_points_on_road_api_call_helper, args_list),
                total=len(args_list),
                desc="Snapping points to roads (batched)",
            )
        )

    # Flatten results and fill snapped_points dict
    for batch in results:
        for idx, snapped_point in batch:
            snapped_points[idx] = snapped_point

    # Ensure output order matches input
    snapped_points_series = gpd.GeoSeries(
        [snapped_points.get(i, None) for i in range(len(points))], index=gdf.index
    )

    return snapped_points_series


def sample_rooftops(
    matched_rooftops_gdf: gpd.GeoDataFrame,
    psu_id_col: str,
    sample_per_psu: int,
    sample_multiplier_col: str | None = None,
):
    """
    Sample rooftops per PSU.
    If sample_multiplier_col is provided, multiply sample_per_psu by that column's (first) value in each group.
    Falls back to fixed sample_per_psu when sample_multiplier_col is None.
    """
    if sample_multiplier_col is None:

        def sampler(x):
            n = min(sample_per_psu, len(x))
            return x.sample(n=n, random_state=42)

    else:
        if sample_multiplier_col not in matched_rooftops_gdf.columns:
            raise ValueError(f"Column '{sample_multiplier_col}' not in dataframe.")

        def sampler(x):
            multiplier = int(x[sample_multiplier_col].iloc[0])
            n = min(sample_per_psu * multiplier, len(x))
            return x.sample(n=n, random_state=42)

    return matched_rooftops_gdf.groupby(psu_id_col, group_keys=False).apply(sampler)
