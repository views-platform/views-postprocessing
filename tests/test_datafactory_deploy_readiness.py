"""Falsification stubs — "views-datafactory development is ready to push to main
and deploy to serve" (assessed from the views-postprocessing perspective).

These guard the cross-repo preconditions that the FAO global-delivery plan
(umbrella views-postprocessing#20, region flip views-models#127) depends on.
They are written against a local views-datafactory checkout.

**"FAIL BY DESIGN" no longer describes this module as a whole, and saying so was
misleading.** The release-gate half is satisfied: the land_gaul work reached a tag, and
that is asserted below. What still fails by design is the *served-artifact* half — the
two ``xfail(strict)`` classes, which flip to failures the moment the served artifact
catches up with the branch. Corrected 2026-08-03.

Resolution is the repo's one declared way of finding a sibling checkout
(``tests/conftest.sibling_repo``): ``$VIEWS_DATAFACTORY``, else the conventional
directory beside this repo. Never an absolute path to a particular machine — that
was C-46, and it kept this gate from ever running anywhere but one laptop.
"""

import json
import subprocess

import pytest

from tests.conftest import sibling_repo

_DF = sibling_repo("views-datafactory")
pytestmark = pytest.mark.skipif(
    _DF is None,
    reason=(
        "views-datafactory checkout not found — set VIEWS_DATAFACTORY=/path/to/"
        "views-datafactory, or place it alongside this repo. Until S7 (#188) this "
        "module hardcoded an absolute path to one developer's machine, so the only "
        "cross-repo release gate in the repo could not run anywhere else (C-46)."
    ),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(_DF), *args],
        capture_output=True, text=True, check=False,
    ).stdout.strip()


class TestReleaseGate:
    """P1: the deploy gate (ADR-022) checks out an exact git TAG on the server, so
    anything this repository depends on must be *inside a tag* — not merely committed.

    **The blocker this class was written for is discharged.** When it was written,
    land_gaul / Azores / SHDI were all committed after the latest tag (v1.2.29) with
    pyproject unchanged, so deploying "to serve" would have served a package without
    land_gaul and views-models#127's ``REGION='land_gaul'`` flip would have hit it.
    That is no longer the situation: ``bac163e`` is contained in v1.10.0 and v1.11.0,
    and datafactory's latest tag is v1.11.0.

    What survives is the standing check — the commit this repository depends on is in a
    release tag — which is the durable form of the same question and does not care what
    anyone's version number says today. The prose above described a live cross-repo
    blocker for a while after it stopped being one; corrected 2026-08-03.
    """

    # **`test_version_bumped_past_latest_tag` was RETIRED here on 2026-08-03.**
    #
    # It asserted `f"v{current}" not in tags` — that datafactory's pyproject version is
    # ahead of its latest tag. That is true only in the window between a version bump
    # and the tag that follows it, so the check went green or red on another
    # repository's release *timing*, not on anything this repository depends on. It had
    # been xfail(strict) for that reason, with a written re-promotion trigger; the
    # trigger fired (datafactory reached v1.10.0 tagged / 1.11.0 in pyproject), the
    # marker turned the unexpected pass into a failure, and re-reading it showed the
    # test was the problem rather than the marker. datafactory's HEAD is literally
    # "chore: bump to 1.11.0": the moment it cuts v1.11.0 this would have gone red
    # again, in a repository doing everything right.
    #
    # Nothing is lost. Its stated purpose — "the land_gaul work is committed but
    # UNTAGGED, so the tag-based deploy gate would serve a release without it" — is
    # exactly what the surviving test below asserts, directly and without reference to
    # anyone's release cadence. A gate that flaps gets ignored, and then the thing it
    # guarded is unguarded (ADR-014 §3).

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
        # Neither is tracked in views-datafactory. Before 2026-08-17 the module-level
        # skipif covered that; now CI fetches the sibling, so without this the test
        # xfails on a MISSING FILE rather than on the staleness it asserts — and a
        # strict xfail that can only ever xfail can never flip, which is the entire
        # mechanism (ADR-014 §1).
        if not (grid.exists() and parquet.exists()):
            pytest.skip(
                "the assembled grid and/or GAUL parquets are absent — they are not "
                "tracked in views-datafactory, so a checkout alone cannot answer this. "
                "Skipping rather than xfailing keeps the strict flip meaningful."
            )
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
        provenance = _DF / "data/assembled/provenance.json"
        if not provenance.exists():
            pytest.skip(
                "data/assembled/provenance.json is absent — not tracked in "
                "views-datafactory, so a checkout alone cannot answer this. Skipping "
                "rather than xfailing keeps the strict flip meaningful."
            )
        prov = json.loads(provenance.read_text())
        sources = prov.get("sources", {})
        assert "admin_digest" in sources, (
            "provenance.sources has no admin_digest — GAUL parquet changes are "
            "invisible to the content-addressed skip, so the served grid will "
            "not rebuild when GAUL changes. Add the admin digest to the "
            "assembly provenance."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
