"""Generate google map links for points and directions between two points."""

from shapely import Point


def gen_map_link(p: Point) -> str:
    """
    Generate a Google Maps link for a single point.

    Args:
        p (Point): A Shapely Point object with coordinates.

    Returns:
        str: A Google Maps URL showing the point location.
    """
    return f"https://www.google.com/maps?q={p.y},{p.x}"


def gen_directions_link(orig_point: Point, road_point: Point | None = None) -> str:
    """
    Generate a Google Maps directions link between two points.

    If road_point is not provided, returns a simple map link for the origin point.
    Otherwise, returns a directions link from orig_point to road_point.

    Args:
        orig_point (Point): The starting point for directions.
        road_point (Point | None): The destination point. If None, only shows orig_point on map.

    Returns:
        str: A Google Maps URL with directions between the two points, or a simple
            map link if road_point is None.
    """
    if road_point is None:
        return gen_map_link(orig_point)
    else:
        return f"https://www.google.com/maps/dir/{orig_point.y},{orig_point.x}/{road_point.y},{road_point.x}"



