"""Matching rooftops to geographic boundaries."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from ..s2.coverage import get_s2_cells_covering_geodataframe
from ..s2.geometry import get_s2_cell_polygon


def match_s2_rooftops_to_psus(
    s2_file_dir: Path, s2_cell_id: int, psu_boundaries_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Match rooftops from an S2 cell file to PSU boundaries using spatial join.

    Loads rooftop polygons from an S2 cell parquet file, converts them to centroids,
    and performs a spatial join to find which rooftops fall within each PSU boundary.
    Only rooftops whose centroids are within a PSU boundary are returned.

    Parameters:
    - s2_file_dir (Path): Directory containing S2 rooftop parquet files (named {cell_id}.parquet)
    - s2_cell_id (int): S2 cell ID to load rooftops from
    - psu_boundaries_gdf (gpd.GeoDataFrame): GeoDataFrame with PSU boundary polygons and metadata

    Returns:
    - gpd.GeoDataFrame: Rooftop centroids with PSU metadata columns joined from psu_boundaries_gdf.
                        Only includes rooftops that fall within a PSU boundary.
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
    psu_boundaries_gdf_s2_overlap = psu_boundaries_gdf[
        psu_boundaries_gdf.intersects(s2_cell_polygon)
    ]

    # perform a spatial join to filter and add area metadata to the rooftops
    matched_rooftop_centroids_gdf = gpd.sjoin(
        s2_rooftop_centroids_gdf,
        psu_boundaries_gdf_s2_overlap,
        how="inner",
        predicate="within",
    ).drop(columns=["index_right"])

    return matched_rooftop_centroids_gdf


def match_all_rooftops_to_psus(
    s2_file_dir: Path, psu_boundaries_gdf: gpd.GeoDataFrame, level: int = 6
) -> gpd.GeoDataFrame:
    """
    Match all rooftops from an S2 folder to PSU boundaries.

    This function determines which S2 cells are needed to cover the PSU boundaries,
    verifies that all required S2 parquet files exist, then matches rooftops from
    all S2 cells to the PSU boundaries and combines the results.

    Parameters:
    - s2_file_dir (Path): Directory containing S2 rooftop parquet files (named {cell_id}.parquet)
    - psu_boundaries_gdf (gpd.GeoDataFrame): GeoDataFrame with PSU boundary polygons and metadata
    - level (int): S2 cell level (default=6). Must match the level used in the S2 file naming.

    Returns:
    - gpd.GeoDataFrame: Combined rooftop centroids from all S2 cells with PSU metadata.
                        Only includes rooftops that fall within PSU boundaries.

    Raises:
    - FileNotFoundError: If any required S2 parquet files are missing from s2_file_dir
    """
    # Determine which S2 cells are needed to cover the PSU boundaries
    required_s2_cells = get_s2_cells_covering_geodataframe(
        psu_boundaries_gdf, level=level
    )
    print(f"Required S2 cells: {len(required_s2_cells)}")

    # Get all available S2 parquet files in the directory
    s2_file_dir = Path(s2_file_dir)
    available_files = list(s2_file_dir.glob("*.parquet"))
    available_cell_ids = {int(f.stem) for f in available_files}

    # Check if all required cells have corresponding files
    required_cell_ids = set(required_s2_cells)
    missing_cell_ids = required_cell_ids - available_cell_ids

    if missing_cell_ids:
        raise FileNotFoundError(
            f"Missing {len(missing_cell_ids)} required S2 parquet files. "
            f"Missing cell IDs: {sorted(missing_cell_ids)[:10]}..."
            if len(missing_cell_ids) > 10
            else f"Missing cell IDs: {sorted(missing_cell_ids)}"
        )

    print(f"All required S2 files found. Processing {len(required_s2_cells)} cells...")

    # Match rooftops from each S2 cell to PSU boundaries
    results = []
    for s2_cell_id in required_s2_cells:
        print(f"Processing s2 file {s2_cell_id}")
        matched_rooftops = match_s2_rooftops_to_psus(
            s2_file_dir, s2_cell_id, psu_boundaries_gdf
        )
        if len(matched_rooftops) > 0:
            results.append(matched_rooftops)

    # Combine all results
    if len(results) == 0:
        print("No rooftops found within PSU boundaries.")
        return gpd.GeoDataFrame()

    combined_gdf = pd.concat(results, ignore_index=True)
    print(f"Total rooftops matched: {len(combined_gdf)}")

    return combined_gdf
