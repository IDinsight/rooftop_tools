"""Snapping points to roads using the Google Roads API."""

import os
from concurrent.futures import ThreadPoolExecutor

import geopandas as gpd
import requests
from shapely import Point
from tqdm.notebook import tqdm


def get_nearest_points_on_road_api_call(
    points: list[Point], api_key: str | None = None
) -> list[Point | None]:
    """
    Retrieves the nearest points on the road for a list of points using the Google Roads API.
    Max 100 points per request.

    Args:
        points (list[Point]): The points for which to find the nearest point on the road.
        api_key (str | None): Your Google Roads API key. If None, reads from
            GOOGLE_MAPS_API_KEY environment variable.

    Returns:
        list[Point | None]: List of snapped points (None if not found).

    Raises:
        ValueError: If API key is not provided and not found in environment.
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if api_key is None:
            raise ValueError(
                "API key must be provided either as a parameter or via "
                "GOOGLE_MAPS_API_KEY environment variable"
            )

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
    gdf: gpd.GeoDataFrame, api_key: str | None = None, max_workers: int = 12
) -> gpd.GeoSeries:
    """
    Snap all points in a GeoDataFrame to the nearest road using parallel processing and batching.

    Args:
        gdf: GeoDataFrame containing point geometries
        api_key: Google Roads API key. If None, reads from GOOGLE_MAPS_API_KEY environment variable.
        max_workers: Number of parallel workers

    Returns:
        GeoSeries with snapped geometries (order matches input). NOTE: If any point could not be snapped,
        the corresponding entry will be None.

    Raises:
        ValueError: If API key is not provided and not found in environment.
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if api_key is None:
            raise ValueError(
                "API key must be provided either as a parameter or via "
                "GOOGLE_MAPS_API_KEY environment variable"
            )

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
