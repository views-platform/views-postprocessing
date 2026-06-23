"""Falsification stubs — "views-datafactory development is ready to push to main
and deploy to serve" (assessed from the views-postprocessing perspective).

These guard the cross-repo preconditions that the FAO global-delivery plan
(umbrella views-postprocessing#20, region flip views-models#127) depends on.
They are written against a local views-datafactory checkout and FAIL BY DESIGN
until the datafactory deploy candidate is actually releasable and the served
artifact matches the branch.

Point _DF at the local datafactory checkout to run.
"""

import json
import subprocess
from pathlib import Path

import pytest

_DF = Path("/home/simon/Documents/scripts/views_platform/views-datafactory")
_pytestmark = pytest.mark.skipif(not _DF.exists(), reason="datafactory checkout not present")
pytestmark = _pytestmark


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(_DF), *args],
        capture_output=True, text=True, check=False,
    ).stdout.strip()


class TestReleaseGate:
    """P1 (HARD): the deploy gate (ADR-022) checks out an exact git TAG on the
    server. land_gaul / Azores / SHDI are all committed AFTER the latest tag
    (v1.2.29) and the version in pyproject is unchanged. Deploying 'to serve'
    the current state would serve v1.2.29 — which has none of this work — and
    views-models#127's REGION='land_gaul' flip would hit a package without it.
    """

    # views-datafactory#224 RESOLVED 2026-06-24 (datafactory 6f7f4ec bumped to
    # v1.4.0, untagged) — xfail(strict) flipped this to a pass, so it's promoted
    # to a live guard: it now fails if a future version collides with a tag again.
    def test_version_bumped_past_latest_tag(self):
        version_line = (_DF / "pyproject.toml").read_text()
        current = next(
            ln.split("=")[1].strip().strip('"')
            for ln in version_line.splitlines()
            if ln.startswith("version")
        )
        tags = _git("tag", "-l").splitlines()
        assert f"v{current}" not in tags, (
            f"pyproject version {current} is already tagged (v{current}). The "
            f"land_gaul/Azores/SHDI work is committed but UNTAGGED; the tag-based "
            f"deploy gate would serve v{current}, which lacks land_gaul. Bump the "
            f"version and cut a release before merging to main / deploying."
        )

    def test_land_gaul_commit_is_in_a_release_tag(self):
        # bac163e = "feat: add bundled curated region land_gaul"
        containing = _git("tag", "--contains", "bac163e").splitlines()
        assert containing, (
            "the land_gaul commit (bac163e) is contained in NO release tag — "
            "a tag-gated deployment cannot serve it. Tag a release that includes it."
        )


class TestServedArtifactMatchesBranch:
    """P3 (HARD): the served artifact (assembled grid / zarr) must reflect the
    parquets land_gaul and the postprocessing lookup are derived from. The grid
    was assembled 2026-06-08; the GAUL parquets were regenerated 2026-06-12
    (Azores supplement). Serving the stale grid ships GAUL channels that
    disagree with land_gaul and with the postprocessing lookup.
    """

    @pytest.mark.xfail(
        reason="cross-repo deploy gate — tracked as views-datafactory#223 "
               "(served grid stale vs June-12 GAUL parquets); xfail(strict) "
               "passes once the grid is re-assembled. See C-36.",
        strict=True,
    )
    def test_assembled_grid_not_older_than_gaul_parquets(self):
        grid = _DF / "data/assembled/grid.npy"
        parquet = _DF / "data/raw/gaul_admin/gaul0_code.parquet"
        assert grid.exists() and parquet.exists()
        assert grid.stat().st_mtime >= parquet.stat().st_mtime, (
            "assembled grid is older than the GAUL parquets — re-assemble and "
            "re-export the zarr before deploying, or the served GAUL channels "
            "are stale relative to land_gaul (64,742)."
        )


class TestServedArtifactProvenanceTracksGaul:
    """P6 (SOFT): the grid provenance tracks ucdp/acled/ghspop/ghsbuilts/vdem
    digests but NOT an admin/GAUL digest. So a GAUL parquet change (e.g. the
    Azores fix) cannot trigger a content-addressed rebuild — the served GAUL
    channels can silently stay stale across pipeline runs.
    """

    @pytest.mark.xfail(
        reason="cross-repo deploy gate — tracked as views-datafactory#223 "
               "(provenance omits admin_digest, so ADR-041 skip can't rebuild "
               "on GAUL change); xfail(strict) passes once added. See C-36.",
        strict=True,
    )
    def test_provenance_includes_admin_digest(self):
        prov = json.loads((_DF / "data/assembled/provenance.json").read_text())
        sources = prov.get("sources", {})
        assert "admin_digest" in sources, (
            "provenance.sources has no admin_digest — GAUL parquet changes are "
            "invisible to the content-addressed skip, so the served grid will "
            "not rebuild when GAUL changes. Add the admin digest to the "
            "assembly provenance."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
