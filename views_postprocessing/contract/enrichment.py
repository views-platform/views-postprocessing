"""Lookup-based geographic enrichment (ADR-011).

Drop-in replacement for the runtime spatial mapper's
``enrich_dataframe_with_pg_info``. Instead of loading 774 MB of shapefiles and
computing spatial intersections at run time, it merges a precomputed lookup
table (built by ``scripts/build_gaul_lookup.py`` from the views-datafactory's
area-majority GAUL parquets) onto the input DataFrame by PRIO-GRID cell id.

No geopandas, no shapefiles, no spatial computation. The lookup contains only
fully-complete cells; an unknown or incomplete cell id gathers to null, so the
delivery's null gate still crashes (fail-loud) rather than shipping a hole. This
is intentional and matches the old mapper's behaviour (it returned ``None`` for
such cells).

**The lookup side is pandas-free (S4 / #89, epic #85).** It is read with pyarrow
and held as numpy arrays plus a sorted key index; attaching metadata to a frame is
a **keyed gather**, not frame algebra, and it never needed a pandas merge. The
input frame is still whatever the caller passes — this class is the *build and
verification* path's object, and its callers hand it DataFrames. What changed is
that the ~880 KiB artifact is no longer materialised as a pandas frame, and the
join no longer depends on the artifact carrying pandas index metadata — which is
what unblocks S5 (#90) making the builder pyarrow-native.

Produces exactly the 9-column contract enforced at
the delivery's artifact builders and at
views-faoapi ``handlers.py`` (``FAO_PGMDataset._METADATA_COLS``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from views_postprocessing.contract import gaul_lookup

if TYPE_CHECKING:  # pragma: no cover — pandas is in this module's INTERFACE, not its
    import pandas as pd  # implementation. Callers hand it DataFrames; nothing here
    # constructs, reads or joins one. Removing the runtime import is the point of
    # S4 (#89): the ~880 KiB lookup is no longer materialised as a pandas frame, and the
    # join no longer needs the artifact to carry pandas index metadata.
from views_postprocessing.contract.gaul_schema import METADATA_COLS

logger = logging.getLogger(__name__)

# The artifact's identity lives in `gaul_lookup` (#152, C-68) — this alias keeps the
# enricher's own default working without re-deriving the path.
_DEFAULT_LOOKUP = gaul_lookup.LOOKUP_PATH

#: int64 bounds, named because they are a correctness condition rather than trivia:
#: a value outside them does not raise on cast, it WRAPS, and a wrapped id that is
#: flagged valid is the fabricated value this module forbids.
_INT64_MIN = int(np.iinfo(np.int64).min)
_INT64_MAX = int(np.iinfo(np.int64).max)

#: Float-comparison bounds. Deliberately NOT the int bounds above: 2**63-1 is odd and
#: unrepresentable in float64, so comparing a float against it rounds up to 2**63 and
#: lets through the very values the bound excludes. 2**63 and -2**63 are both powers
#: of two and exact, so the float check is `>= -2**63` and `< 2**63`.
_INT64_MIN_F = -(2.0**63)
_INT64_MAX_EXCLUSIVE_F = 2.0**63

#: The lookup's key column. Named once — the artifact calls it `priogrid_gid`, the
#: wire calls it `priogrid_id` (§5.1), and confusing the two is a silent join failure.
_KEY = "priogrid_gid"


class GaulLookupEnricher:
    """Merge precomputed GAUL metadata onto an input DataFrame by cell id."""

    def __init__(self, lookup_path: str | Path | None = None) -> None:
        self._lookup_path = Path(lookup_path) if lookup_path else _DEFAULT_LOOKUP
        if not self._lookup_path.exists():
            err_msg = (
                f"GAUL lookup table not found at {self._lookup_path}. "
                f"Build it with scripts/build_gaul_lookup.py."
            )
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)
        table = gaul_lookup.load(self._lookup_path)
        missing = [c for c in (_KEY, *METADATA_COLS) if c not in table.column_names]
        if missing:
            err_msg = f"Lookup table is missing contract columns: {missing}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        if table.column(_KEY).null_count:
            err_msg = (
                f"GAUL lookup at {self._lookup_path} has null values in {_KEY!r}. A "
                "null key cannot identify a cell, and coercing it would make it "
                "collide with any unusable id on the query side — the row would then "
                "be reported as FOUND and receive another cell's metadata. Rebuild "
                "with scripts/build_gaul_lookup.py. (That script does not check the "
                "key column either — its null check runs after the key becomes the "
                "index, and DataFrame.isna() does not inspect an index. A null key is "
                "unreachable there only because the earlier astype('int64') raises. "
                "See register C-76.)"
            )
            logger.error(err_msg)  # ADR-008: logged persistently AND raised
            raise ValueError(err_msg)

        if table.num_rows == 0:
            err_msg = (
                f"GAUL lookup at {self._lookup_path} is empty. Every cell would gather "
                "to null and the delivery would fail downstream complaining about "
                "missing metadata rather than about a missing lookup. Rebuild it with "
                "scripts/build_gaul_lookup.py."
            )
            logger.error(err_msg)  # ADR-008: logged persistently AND raised
            raise ValueError(err_msg)

        # Sort the whole table once by key, in arrow, so the gather below is a binary
        # search per row rather than a scan. `take` reorders every column together —
        # doing it column-by-column in python was measurably quadratic and is exactly
        # the mistake this comment exists to stop the next person repeating.
        keys = table.column(_KEY).to_numpy(zero_copy_only=False).astype(np.int64)
        order = np.argsort(keys, kind="stable")
        table = table.take(pa.array(order))
        self._keys = keys[order]
        # One `to_pylist` per column, not per row. Lists rather than numpy arrays
        # because the columns are of mixed kind (float codes, string names) and the
        # output is assembled per column anyway.
        #
        # DTYPE CHANGE, deliberate and measured (S4 / #89). The pandas merge this
        # replaced produced `category` name columns, inherited from the artifact's
        # dictionary encoding; assigning lists produces `object`. On a 200-row output:
        # category 1,795,191 bytes vs object 60,061 — a categorical carries the full
        # 64,742-entry dictionary whatever the output size, so this is far lighter for
        # the small frames this object actually sees and heavier only past the point
        # where the dictionary amortises. The builder's `# names/iso categorical (C-32
        # memory)` note governs the ARTIFACT; it never governed this method's output.
        self._values = {col: table.column(col).to_pylist() for col in METADATA_COLS}
        self.lookup_version = self._read_version(self._lookup_path)
        logger.info(
            "Loaded GAUL lookup: %d cells from %s (version=%s)",
            len(self._keys), self._lookup_path, self.lookup_version,
        )

    @staticmethod
    def _as_cell_ids(gids) -> tuple[np.ndarray, np.ndarray]:
        """``(int64 ids, usable mask)`` — DECLARED, never coerced (ADR-003).

        A cell id is an integer. Anything that is not one — a missing value, a
        non-integral float, a ``pd.NA`` — is marked **unusable** rather than cast,
        and unusable ids gather to null exactly as an unknown gid does. The
        downstream gate then sees a hole, which is what it exists for.

        **Why not just cast.** ``np.asarray(gids, dtype=np.int64)`` looks equivalent
        and is not, in three ways found in review of #210:

        - a ``NaN`` becomes ``INT64_MIN`` with only a ``RuntimeWarning``. If a lookup
          key were ever null it would take the same sentinel, the two would collide,
          and the row would be reported FOUND — receiving another cell's metadata.
          That is the fabricated value this module's docstring forbids (cf. C-35).
        - a non-integral float **truncates silently**: ``54220.000000001`` becomes
          ``54220`` and matches a real, *different* cell. Verified against the pandas
          merge this replaced: it returns null there, and even warns. A silent wrong
          match is strictly worse than the crash it would replace.
        - a ``pd.NA`` raises a bare ``TypeError`` from numpy — no log, no
          contract-shaped error, unlike every other guard in this file.
        """
        arr = np.asarray(gids)

        if arr.dtype.kind in ("i", "u"):
            # In range, or it is not the id the caller wrote. uint64 max silently
            # wraps to -1 under `astype(np.int64)` and would be flagged VALID.
            usable = (arr >= _INT64_MIN) & (arr <= _INT64_MAX)
            return np.where(usable, arr, 0).astype(np.int64), usable

        if arr.dtype.kind == "f":
            # Finite, integral, AND representable. `1e30` passes the first two and
            # then overflows the cast to INT64_MIN — an id nobody asked for, marked
            # valid. Same silent-coercion class this method exists to remove.
            # STRICTLY below 2**63, not `<= _INT64_MAX`. `_INT64_MAX` is 2**63-1,
            # which is odd and NOT representable in float64 — comparing against it
            # promotes to float and rounds UP to 2**63, so the bound admitted exactly
            # the values it was added to exclude. `float(2**63)` passed every check
            # and then wrapped to INT64_MIN, flagged valid. `_INT64_MIN` has no
            # equivalent hole: -2**63 is a power of two and exactly representable.
            #
            # `isfinite` is kept for intent and is SUBSUMED — `inf` fails the upper
            # bound, `NaN` fails `arr == rint(arr)` (NaN equals nothing). It is the
            # one condition here that survives its own removal, so it is defensive
            # rather than load-bearing; the other three each fail the suite.
            usable = (
                np.isfinite(arr)
                & (arr == np.rint(arr))
                & (arr >= _INT64_MIN_F)
                & (arr < _INT64_MAX_EXCLUSIVE_F)
            )
            return np.where(usable, arr, 0).astype(np.int64), usable

        # object / pandas-nullable. Accept only values that ALREADY ARE integers.
        #
        # An earlier draft used `float(value)`, which parses. That accepted the string
        # `"54220"` as a cell id — where the pandas merge this replaced raised
        # `ValueError: You are trying to merge on object and int64 columns`. A string
        # gid column is a declaration error and the old path said so; parsing it is
        # inference (ADR-003) and it is the same defect as the drifted float, just
        # pointing the other way. `bool` is excluded for the same reason: `True` is
        # not cell 1.
        ids = np.zeros(len(arr), dtype=np.int64)
        usable = np.zeros(len(arr), dtype=bool)
        for i, value in enumerate(arr):
            # `np.timedelta64` IS an `np.integer` instance — a numpy quirk, and
            # `np.datetime64` is not, so the hole was specific to that one type. A
            # duration is not a cell id any more than `True` is cell 1.
            if isinstance(value, (bool, np.timedelta64)):
                continue
            if not isinstance(value, (int, np.integer)):
                continue
            if _INT64_MIN <= int(value) <= _INT64_MAX:
                ids[i], usable[i] = int(value), True
        return ids, usable

    def _gather(self, gids) -> dict:
        """The metadata for each gid, warning about the ones that got none.

        A sorted-key ``searchsorted`` rather than a hash map: the lookup is 64,742
        rows read once per process, and the gather is over the delivery's row count.
        Absent gids yield ``None`` in every column — the null the downstream gate
        exists to catch, not a sentinel it would pass. An id that is not a usable
        cell id is treated the same way: absent, never guessed at.
        """
        wanted, usable = self._as_cell_ids(gids)
        # `self._keys` is non-empty — __init__ refuses an empty lookup. An earlier draft
        # guarded with `(len(self._keys) > 0) & (...)`, which READS as a guard and is
        # not one: `&` evaluates both operands, so the index happened regardless and an
        # empty lookup raised IndexError from inside the gather rather than ValueError
        # from the constructor. Guard where the condition is knowable, not where it bites.
        idx = np.clip(np.searchsorted(self._keys, wanted), 0, len(self._keys) - 1)
        # `& usable` is NOT belt-and-braces, and no substitute value would make it so.
        # Unusable ids substitute to 0, but int64 reserves nothing — the lookup is
        # arbitrary data and may legally contain 0, or -1, or INT64_MIN, or whatever
        # else one might pick instead. The mask is what carries correctness; the
        # substitute is only a placeholder. Pinned by
        # `test_an_unusable_id_cannot_match_the_cell_it_was_substituted_with`.
        found = (self._keys[idx] == wanted) & usable
        out = {
            col: [vals[i] if hit else None for i, hit in zip(idx, found)]
            for col, vals in self._values.items()
        }

        # Warn HERE rather than handing the caller three arrays to reassemble one
        # message. `__init__` already co-locates detection and logging at every guard
        # (ADR-008); this is the same shape. An earlier draft returned four values,
        # three of which existed only to build the string below.
        absent = ~found
        n_unmapped = int(absent.sum())
        if n_unmapped:
            unknown = sorted({int(i) for i, miss, ok in zip(wanted, absent, usable) if miss and ok})
            n_unusable = int((absent & ~usable).sum())
            detail = f"unknown cells {unknown[:20]}" if unknown else "no unknown cells"
            if n_unusable:
                detail += f"; {n_unusable} row(s) carried no usable cell id"
            logger.warning(
                "%d/%d rows have no lookup match (will fail validation): %s",
                n_unmapped, len(wanted), detail,
            )
        return out

    @staticmethod
    def _read_version(path: Path) -> str:
        """The lookup's build stamp. Delegates to ``gaul_lookup.version`` (#152) —
        this was a ``@staticmethod`` that never touched the instance, i.e. a fact
        about the artifact, not about the enricher."""
        return gaul_lookup.version(path)

    def enrich_dataframe_with_pg_info(
        self,
        df: pd.DataFrame,
        pg_id_col: str = "priogrid_gid",
        time_id_col: str = "month_id",
        only_metadata: bool = True,
        **ignored_mapper_kwargs,
    ) -> pd.DataFrame:
        """Return ``df`` with the 9 metadata columns merged in by cell id.

        Signature mirrors the mapper's method so the manager call site changes
        minimally. Mapper-only kwargs (``batch_size``, ``use_multiprocessing``,
        ``show_progress`` …) are accepted and ignored — a table join needs none
        of them — but any unrecognised kwarg is logged at debug so a genuine
        caller mistake is not wholly silent.

        Cells absent from the lookup get NaN metadata (fail-loud downstream).
        """
        if ignored_mapper_kwargs:
            logger.debug(
                "GaulLookupEnricher ignoring mapper-only kwargs: %s",
                sorted(ignored_mapper_kwargs),
            )
        if pg_id_col not in df.columns:
            err_msg = f"Column '{pg_id_col}' not found in DataFrame"
            logger.error(err_msg)
            raise ValueError(err_msg)

        if only_metadata:
            keep = [pg_id_col]
            if time_id_col in df.columns:
                keep.append(time_id_col)
            base = df[keep].copy()
        else:
            base = df.copy()

        gids = base[pg_id_col].to_numpy()
        gathered = self._gather(gids)

        merged = base.copy()
        for col in METADATA_COLS:
            merged[col] = gathered[col]
        return merged

    # Convenience alias for new call sites that don't need the legacy name.
    enrich = enrich_dataframe_with_pg_info
