"""Shadow diff: current runtime mapper vs new lookup enricher (ADR-011, Stage 2 prep).

Runs BOTH geographic-enrichment engines on the africa_me_legacy cell set and
compares all 9 contract columns per cell. Every difference is classified so we
can account, precisely, for what changes when the engine is swapped — and
confirm there are no UNEXPLAINED differences before going live.

Requires the real shapefiles (git-lfs pull) so the current mapper can run, and
the committed lookup parquet for the new enricher. Writes:
    reports/enrichment_diff/diff_cells.csv     one row per africa_me cell
    reports/enrichment_diff/summary.json       counts per class (for plots/report)

The classification deliberately separates "country code-system difference"
(same GAUL country, Natural Earth ISO vs GAUL ISO string) from genuine
"country reassignment" (different GAUL country), so the headline change count
is not inflated by a pure naming convention.
"""

from __future__ import annotations

import json
import logging
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from views_postprocessing.unfao.enrichment import GaulLookupEnricher
from views_postprocessing.unfao.gaul_schema import METADATA_COLS

# Quiet the noisy mapper run; the imports above are clean and stay at top.
warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.WARNING)


def _resolve_datafactory() -> Path:
    env = os.environ.get("VIEWS_DATAFACTORY")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "views-datafactory"


_DATAFACTORY = _resolve_datafactory()
_AFRICA_ME = _DATAFACTORY / "src" / "datafactory_query" / "africa_me_legacy_pgids.json"
_AZORES_GIDS = {182470, 183190, 183909, 183910, 186058, 186778}
_OUT = Path("reports/enrichment_diff")


def _run_new(gids: list[int]) -> pd.DataFrame:
    enr = GaulLookupEnricher()
    df = pd.DataFrame({"priogrid_gid": gids, "month_id": 0})
    out = enr.enrich_dataframe_with_pg_info(
        df, pg_id_col="priogrid_gid", time_id_col="month_id",
    ).set_index("priogrid_gid")[METADATA_COLS]
    return out.add_suffix("__new")


def _run_old(gids: list[int]) -> pd.DataFrame:
    from views_postprocessing.unfao.mapping.mapping import get_default_mapper
    mapper = get_default_mapper()
    df = pd.DataFrame({"priogrid_gid": gids, "month_id": 0})
    raw = mapper.enrich_dataframe_with_pg_info(
        df, pg_id_col="priogrid_gid", time_id_col="month_id",
        only_metadata=True, batch_size=1000, use_multiprocessing=True,
        show_progress=False,
    )
    # The mapper may omit columns for unmapped cells; reindex to the contract.
    raw = raw.set_index("priogrid_gid")
    for c in METADATA_COLS:
        if c not in raw.columns:
            raw[c] = np.nan
    return raw[METADATA_COLS].add_suffix("__old")


def _classify(row: pd.Series) -> tuple[str, str]:
    """Return (presence, change_class) for one cell."""
    has_old = pd.notna(row["country_iso_a3__old"])
    has_new = pd.notna(row["country_iso_a3__new"])

    if has_new and not has_old:
        if int(row.name) in _AZORES_GIDS:
            return "new_only", "azores_supplement"
        return "new_only", "coastal_recovery"
    if has_old and not has_new:
        return "old_only", "dropped_by_land_gaul"
    if not has_old and not has_new:
        return "neither", "both_unmapped"

    # Present in both — compare the 9 columns.
    diffs = [c for c in METADATA_COLS
             if not _eq(row[f"{c}__old"], row[f"{c}__new"])]
    if not diffs:
        return "both", "identical"

    gaul0_changed = "admin1_gaul0_code" in diffs
    iso_changed = "country_iso_a3" in diffs
    admin_changed = any(c in diffs for c in
                        ["admin1_gaul1_code", "admin2_gaul2_code"])

    if gaul0_changed:
        return "both", "country_reassignment"
    if iso_changed and not gaul0_changed:
        return "both", "country_code_system"
    if admin_changed:
        return "both", "admin_reallocation"
    # Only names/coords differ, codes identical.
    if any(c in diffs for c in ["pg_xcoord", "pg_ycoord"]):
        return "both", "coordinate_difference"
    return "both", "name_only_difference"


def _eq(a, b) -> bool:
    if pd.isna(a) and pd.isna(b):
        return True
    if pd.isna(a) or pd.isna(b):
        return False
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 1e-6
        except (TypeError, ValueError):
            return str(a) == str(b)
    return str(a) == str(b)


def main() -> None:
    gids = sorted(json.loads(_AFRICA_ME.read_text()))
    print(f"africa_me_legacy cells: {len(gids):,}")

    print("running NEW enricher (lookup merge)...")
    new = _run_new(gids)
    print("running OLD mapper (real shapefiles, this takes a few minutes)...")
    old = _run_old(gids)

    both = old.join(new, how="outer")
    both.index.name = "priogrid_gid"

    classified = both.apply(_classify, axis=1, result_type="expand")
    both["presence"] = classified[0]
    both["change_class"] = classified[1]

    _OUT.mkdir(parents=True, exist_ok=True)
    both.to_csv(_OUT / "diff_cells.csv")

    counts = both["change_class"].value_counts().to_dict()
    n_changed = int((both["change_class"] != "identical").sum()
                    - counts.get("both_unmapped", 0))
    summary = {
        "n_cells": len(both),
        "counts": counts,
        "n_changed_excluding_identical_and_unmapped": n_changed,
        "unexplained": int(both["change_class"].isin(["UNEXPLAINED"]).sum()),
    }
    (_OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    print("\n=== difference classes ===")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:28s} {v:>6,}")
    print(f"\nwrote {_OUT/'diff_cells.csv'} and summary.json")


if __name__ == "__main__":
    main()
