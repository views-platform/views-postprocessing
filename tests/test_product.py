"""Each partner's declared product — ADR-013 §4.2a/§6/§4.1a/§11.4 pins.

**Scoped to the FAO product until #211.** When `crafd/product.py` landed, every pin
here still read `unfao.product`: nothing asserted CRAF'd's consumer document name,
its target vocabulary, or that its upload interlock defaulted off. The values were all
correct — but "correct and unchecked" is the state a product declaration is in right
up until the day it is not, and §4.1a's failure mode is silence, not an error.

The consumer-name pin is the one that matters most and the one a partner-scoped test
could never catch: a document written under a name the consumer does not filter for is
delivered, stored, billed, and invisible. That is not hypothetical here — six
`orange_ensemble` forecast documents sat in `unfao_bucket` for months while FAO's
forecast serving read empty (ADR-013 §11.4 post-adoption record, register C-01).

Parametrised over `tests/conftest.PARTNER_PACKAGES`, so a third partner is caught by
`test_clone_readiness.py::test_the_declared_partner_list_is_the_real_one` rather than
quietly skipped.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

from tests.conftest import CONSUMER_REPO, PARTNER_PACKAGES, SIBLING_ENV, require_sibling

#: partner -> the document name its consumer filters on, DECLARED here rather than
#: read back from the module under test.
#:
#: A test that asserts ``product.CONSUMER_DOCUMENT_NAME == product.CONSUMER_DOCUMENT_NAME``
#: passes for every possible value, which is the shape of the replica defect epic #181
#: spent a story retiring. So the expected value is written out.
#:
#: **But a literal transcribed from another repository is a guarantee, and ADR-014 §1
#: says a guarantee needs a check.** On its own this pin catches drift authored *here* —
#: which was never the danger. If views-crafdapi changed its filter tomorrow, this file
#: would stay green, the delivery would upload, and the document would be invisible:
#: ADR-013 §4.1a, the defect that stranded six `orange_ensemble` documents in
#: `unfao_bucket` while FAO's forecast serving read empty for months.
#:
#: ``test_the_declared_consumer_name_still_matches_the_consumer`` closes that half
#: against the sibling checkout, following the pattern
#: ``tests/test_env_declaration.py`` already uses for the coordinate registry: declared
#: locally, verified across the seam when the other repo is on disk.
_CONSUMER_DOCUMENT_NAME = {
    "unfao": "un_fao",
    "crafd": "un_crafd",
}

#: Where the consumer's name lives, and the mechanism that consumes it. Both are
#: pinned: a consumer that kept the string but started filtering on a different field
#: would strand a delivery just as thoroughly as one that renamed it.
_CONSUMER_PATH_MANAGER = re.compile(r'APIPathManager\(\s*"([a-z0-9_]+)"')
_CONSUMER_FILTER = 'filters["name"] = self.model_path.model_name'


def _product(partner: str):
    return importlib.import_module(f"views_postprocessing.{partner}.product")


def _consumer_package(repo: Path) -> Path:
    """``src/views_<something>api`` inside a consumer checkout."""
    candidates = sorted((repo / "src").glob("views_*api"))
    assert len(candidates) == 1, (
        f"expected exactly one package under {repo}/src, found {candidates}. The "
        "consumer's layout changed; this test's assumption about where to look is "
        "part of what it asserts."
    )
    return candidates[0]


def test_every_partner_has_its_consumer_name_pinned():
    """Assert this file's declared scope is the real one (ADR-014 §2)."""
    assert set(_CONSUMER_DOCUMENT_NAME) == set(PARTNER_PACKAGES), (
        f"partners with no pinned consumer name: "
        f"{sorted(set(PARTNER_PACKAGES) - set(_CONSUMER_DOCUMENT_NAME))}; "
        f"pinned but no longer a partner: "
        f"{sorted(set(_CONSUMER_DOCUMENT_NAME) - set(PARTNER_PACKAGES))}. An unpinned "
        "partner can be renamed into invisibility without a single test failing."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_targets_are_the_pinned_wire_vocabulary(partner):
    # §7a: wire names, never internal model names; order stable for manifests.
    assert _product(partner).TARGETS == ("lr_ged_sb", "lr_ged_ns", "lr_ged_os")


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_s_min_is_the_walking_skeleton_floor(partner):
    # §6's walking-skeleton value. The production floor is still an open maintainer
    # item in ADR-013's post-adoption record; both partners inherit it, deliberately.
    assert _product(partner).S_MIN == 2


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_consumer_document_name_is_the_pin_its_consumer_filters_on(partner):
    # §4.1a: any other name is invisible to the consumer's unconditional name filter.
    assert _product(partner).CONSUMER_DOCUMENT_NAME == _CONSUMER_DOCUMENT_NAME[partner]


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_upload_interlock_defaults_off(partner):
    # §11.4: the default configuration must be unable to touch the live bucket.
    assert _product(partner).UPLOAD_ENABLED is False


# ── across the seam: the pin above, checked against the repo that owns the fact ──


def test_every_partner_has_a_declared_consumer_repository():
    """The gated check below iterates this map; assert it is real (ADR-014 §2)."""
    assert set(CONSUMER_REPO) == set(PARTNER_PACKAGES), (
        f"partners with no declared consumer repository: "
        f"{sorted(set(PARTNER_PACKAGES) - set(CONSUMER_REPO))}. Without one, that "
        "partner's consumer-name pin is never checked against the consumer."
    )
    undeclared = sorted(r for r in CONSUMER_REPO.values() if r not in SIBLING_ENV)
    assert not undeclared, (
        f"consumer repositories with no SIBLING_ENV entry: {undeclared}. "
        "require_sibling() raises KeyError rather than skipping for those, so the "
        "check would fail confusingly instead of skipping cleanly."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_declared_consumer_name_still_matches_the_consumer(partner):
    """§4.1a across the seam — the half a local literal cannot carry.

    The consumer decides what it filters on. This repository declares what it writes.
    Agreement between the two is the whole of §4.1a, and it is not a fact this
    repository owns — so it is checked against the consumer's checkout, exactly as the
    coordinate registry is checked against views-appwrite's.

    Gated: skips without the sibling, naming the variable to set. The always-on pin
    above still runs everywhere, so CI is never left with nothing.
    """
    repo = require_sibling(CONSUMER_REPO[partner])
    pkg = _consumer_package(repo)

    api = (pkg / "managers" / "api.py").read_text()
    found = _CONSUMER_PATH_MANAGER.findall(api)
    assert len(found) == 1, (
        f"expected exactly one APIPathManager(...) construction in "
        f"{CONSUMER_REPO[partner]}'s managers/api.py, found {found}. More than one "
        "means the consumer serves several document names and this check no longer "
        "knows which one is ours."
    )
    assert found[0] == _CONSUMER_DOCUMENT_NAME[partner], (
        f"{CONSUMER_REPO[partner]} filters on {found[0]!r}; this repository declares "
        f"{_CONSUMER_DOCUMENT_NAME[partner]!r} and writes it as "
        f"{partner}/product.py's CONSUMER_DOCUMENT_NAME. A delivery under a name the "
        "consumer does not ask for is uploaded, stored, and invisible (ADR-013 §4.1a)."
    )
    assert found[0] == _product(partner).CONSUMER_DOCUMENT_NAME, (
        "the declared pin in this file and the module's constant disagree — the "
        "always-on test above should have caught this first"
    )

    manager = (pkg / "managers" / "prediction" / "manager.py").read_text()
    assert _CONSUMER_FILTER in manager, (
        f"{CONSUMER_REPO[partner]} no longer selects by "
        f"{_CONSUMER_FILTER!r}. The name may still match while the consumer filters on "
        "something else entirely — same invisibility, different cause. Re-read its "
        "selection path before assuming this repository's deliveries are reachable."
    )
