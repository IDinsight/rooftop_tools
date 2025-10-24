"Generate google map links for points and directions between two points"

from shapely import Point
def gen_map_link(p: Point) -> str:
    return f"https://www.google.com/maps?q={p.y},{p.x}"
