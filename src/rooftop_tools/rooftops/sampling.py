"""Sampling rooftops from geographic areas."""

import geopandas as gpd


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
