"""Rich verification maps for the enrichment diff (ADR-011, Stage 2).

Renders the old-mapper-vs-new-lookup differences over africa_me as maps, so the
change can be shown and accounted for visually. Reads
reports/enrichment_diff/diff_cells.csv and writes PNGs to
reports/enrichment_diff/maps/.

Cells are PRIO-GRID 0.5-degree squares drawn with pcolormesh on a regular grid;
country outlines come from Natural Earth 110m (fast context layer).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_DIFF = Path("reports/enrichment_diff/diff_cells.csv")
_MAPS = Path("reports/enrichment_diff/maps")
_NE110 = Path("views_postprocessing/shapefiles/ne_110m_admin_0_countries/"
              "ne_110m_admin_0_countries.shp")
_CELL = 0.5

CLASS_COLORS = {
    "identical": "#e8e8e8",
    "country_reassignment": "#d62728",
    "admin_reallocation": "#ff7f0e",
    "coastal_recovery": "#2ca02c",
    "dropped_by_land_gaul": "#9467bd",
    "both_unmapped": "#7f7f7f",
}


def _gid_to_colrow(gid):
    col = (gid - 1) % 720
    row = (gid - 1) // 720
    return col, row


def _borders(ax, bbox):
    try:
        import geopandas as gpd
        ne = gpd.read_file(_NE110)
        ne.boundary.plot(ax=ax, color="black", linewidth=0.4, zorder=3)
    except Exception:
        pass
    ax.set_xlim(bbox[0], bbox[1])
    ax.set_ylim(bbox[2], bbox[3])
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")


def _grid(values: pd.Series, bbox):
    """Build a masked 2D array over bbox at 0.5deg from a per-gid value Series."""
    col0 = int((bbox[0] + 180) / _CELL)
    row0 = int((bbox[2] + 90) / _CELL)
    ncol = int((bbox[1] - bbox[0]) / _CELL)
    nrow = int((bbox[3] - bbox[2]) / _CELL)
    grid = np.full((nrow, ncol), np.nan)
    for gid, v in values.items():
        c, r = _gid_to_colrow(gid)
        cc, rr = c - col0, r - row0
        if 0 <= cc < ncol and 0 <= rr < nrow:
            grid[rr, cc] = v
    extent = [bbox[0], bbox[1], bbox[2], bbox[3]]
    return grid, extent


def _bbox(df, pad=2.0):
    xs = [(_gid_to_colrow(g)[0]) * _CELL - 180 for g in df.index]
    ys = [(_gid_to_colrow(g)[1]) * _CELL - 90 for g in df.index]
    return [min(xs) - pad, max(xs) + _CELL + pad,
            min(ys) - pad, max(ys) + _CELL + pad]


def map_agree_disagree(df, bbox):
    fig, ax = plt.subplots(figsize=(11, 11))
    code = (df["change_class"] != "identical").astype(int)
    grid, extent = _grid(
        pd.Series(code.values, index=df.index), bbox)
    cmap = mcolors.ListedColormap(["#e8e8e8", "#d62728"])
    ax.imshow(np.ma.masked_invalid(grid), origin="lower", extent=extent,
              cmap=cmap, vmin=0, vmax=1, interpolation="nearest", zorder=2)
    _borders(ax, bbox)
    n_changed = int(code.sum())
    ax.set_title(f"africa_me: enrichment agreement\n"
                 f"{len(df)-n_changed:,} identical (grey)  |  "
                 f"{n_changed:,} changed (red)")
    ax.legend(handles=[mpatches.Patch(color="#e8e8e8", label="identical"),
                       mpatches.Patch(color="#d62728", label="changed")],
              loc="lower left")
    fig.savefig(_MAPS / "01_agree_disagree.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def map_by_class(df, bbox):
    classes = [c for c in CLASS_COLORS if c in set(df["change_class"])]
    code_of = {c: i for i, c in enumerate(classes)}
    codes = df["change_class"].map(code_of)
    grid, extent = _grid(pd.Series(codes.values, index=df.index), bbox)
    cmap = mcolors.ListedColormap([CLASS_COLORS[c] for c in classes])
    fig, ax = plt.subplots(figsize=(11, 11))
    ax.imshow(np.ma.masked_invalid(grid), origin="lower", extent=extent,
              cmap=cmap, vmin=-0.5, vmax=len(classes) - 0.5,
              interpolation="nearest", zorder=2)
    _borders(ax, bbox)
    ax.set_title("africa_me: difference class per cell")
    ax.legend(handles=[mpatches.Patch(color=CLASS_COLORS[c],
                                      label=f"{c} ({int((df['change_class']==c).sum())})")
                       for c in classes], loc="lower left", fontsize=9)
    fig.savefig(_MAPS / "02_by_class.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def map_country_before_after(df, bbox):
    present = df[df["country_iso_a3__old"].notna()
                 | df["country_iso_a3__new"].notna()]
    countries = sorted(set(present["country_iso_a3__old"].dropna())
                       | set(present["country_iso_a3__new"].dropna()))
    cof = {c: i for i, c in enumerate(countries)}
    cmap = plt.get_cmap("tab20", max(len(countries), 1))
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    for ax, col, title in [
        (axes[0], "country_iso_a3__old", "OLD mapper (Natural Earth country)"),
        (axes[1], "country_iso_a3__new", "NEW lookup (GAUL country)"),
    ]:
        codes = df[col].map(cof)
        grid, extent = _grid(pd.Series(codes.values, index=df.index), bbox)
        ax.imshow(np.ma.masked_invalid(grid), origin="lower", extent=extent,
                  cmap=cmap, vmin=0, vmax=len(countries), interpolation="nearest",
                  zorder=2)
        _borders(ax, bbox)
        ax.set_title(title)
    fig.suptitle("Country assignment: before vs after (color = country)")
    fig.savefig(_MAPS / "03_country_before_after.png", dpi=120,
                bbox_inches="tight")
    plt.close(fig)


def map_zoom(df, bbox, name, title):
    sub = df.copy()
    classes = [c for c in CLASS_COLORS if c in set(sub["change_class"])]
    code_of = {c: i for i, c in enumerate(classes)}
    grid, extent = _grid(
        pd.Series(sub["change_class"].map(code_of).values, index=sub.index), bbox)
    cmap = mcolors.ListedColormap([CLASS_COLORS[c] for c in classes])
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(np.ma.masked_invalid(grid), origin="lower", extent=extent,
              cmap=cmap, vmin=-0.5, vmax=len(classes) - 0.5,
              interpolation="nearest", zorder=2, alpha=0.85)
    _borders(ax, bbox)
    ax.set_title(title)
    ax.legend(handles=[mpatches.Patch(color=CLASS_COLORS[c], label=c)
                       for c in classes if c != "identical"],
              loc="lower left", fontsize=9)
    fig.savefig(_MAPS / name, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main():
    _MAPS.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(_DIFF).set_index("priogrid_gid")
    bbox = _bbox(df)

    map_agree_disagree(df, bbox)
    map_by_class(df, bbox)
    map_country_before_after(df, bbox)
    # Zoom 1: Lesotho / South Africa enclave (biggest reassignment cluster).
    map_zoom(df, [24, 36, -32, -24], "04_zoom_lesotho_sa.png",
             "Zoom: Lesotho / Eswatini / South Africa border reassignments")
    # Zoom 2: Namibia / Botswana / South Africa tri-border.
    map_zoom(df, [13, 30, -30, -17], "05_zoom_namibia_botswana.png",
             "Zoom: Namibia / Botswana / South Africa / Mozambique borders")
    print(f"wrote maps to {_MAPS}/")
    for p in sorted(_MAPS.glob("*.png")):
        print(f"  {p.name}  ({p.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
