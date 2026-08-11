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

from tests.conftest import CONSUMER_REPO, PARTNER_PACKAGES, SIBLINGS, require_sibling

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
#: ``test_the_declared_consumer_name_matches_the_registry`` closes that half against the
#: **public coordinate registry** rather than the consumer's source (ADR-017 §5). It runs
#: for every partner and needs no credential, because the registry is public even when the
#: consumer is not — which is why it reaches the FAO partner and its predecessor could not.
#:
#: One partner is still ALSO read at the source, and only one:
#: ``_CONSUMER_SELF_CHECK_PENDING`` below names it and the issue that retires it.
_CONSUMER_DOCUMENT_NAME = {
    "unfao": "un_fao",
    "crafd": "un_crafd",
}

#: Where the consumer's name lives, and the mechanism that consumes it. Both are
#: pinned: a consumer that kept the string but started filtering on a different field
#: would strand a delivery just as thoroughly as one that renamed it.
_PKG = Path(__file__).resolve().parent.parent / "views_postprocessing"

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



@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_both_delivery_legs_name_the_document_from_the_declaration(partner):
    """Register C-77 — the forecast and historical legs must agree, by construction.

    The two legs upload separately and the consumer selects them separately: forecasts
    by the newest manifest, historical actuals by ``category="historical"``. Both are
    filtered on the document ``name``, so if the legs disagree the delivery half-arrives
    — and the failure mode is an **empty endpoint, not an error**, which is ADR-013
    §4.1a's exact shape.

    **They used to disagree.** The historical leg passed
    ``name=self._model_path.model_name`` — the views-models *directory* name — while the
    forecast leg passed the declared ``CONSUMER_DOCUMENT_NAME``. For FAO the two happen
    to match, so nothing was wrong; nothing *asserted* they matched either, and the
    agreement lived in a different repository's filesystem layout. The trap was about to
    be sprung for real: views-models#333 creates CRAF'd's launcher directory, and
    whoever named it would have decided, without knowing it, whether CRAF'd's historical
    artifact was retrievable.

    A source scan rather than a call: the managers need Appwrite env and a views-models
    path manager to instantiate, which is this repo's standing pattern for manager-side
    facts.
    """
    source = (_PKG / partner / "managers" / f"{partner}.py").read_text()

    assert "name=self._model_path.model_name" not in source, (
        f"[{partner}] an upload names its document from the model path again. That is "
        "the views-models DIRECTORY name — a fact in another repository, not a "
        "declaration here. Use product.CONSUMER_DOCUMENT_NAME (register C-77)."
    )

    # Counted separately, and the lookbehind matters: `consumer_name=product...`
    # contains `name=product...` as a substring, so a naive count reports three legs
    # where there are two. (It did, on the first run of this guard.)
    legs = {
        "forecast (via the sink)": len(
            re.findall(r"\bconsumer_name=product\.CONSUMER_DOCUMENT_NAME", source)
        ),
        "historical (direct upload)": len(
            re.findall(r"(?<!consumer_)\bname=product\.CONSUMER_DOCUMENT_NAME", source)
        ),
    }
    assert legs == {"forecast (via the sink)": 1, "historical (direct upload)": 1}, (
        f"[{partner}] expected exactly one forecast leg and one historical leg naming "
        f"the document from the declaration; found {legs}. A missing leg means one "
        "stopped using the declaration; an extra means a new delivery leg nobody has "
        "checked against the consumer's filter."
    )

# ── across the seam: the pin above, checked against the repo that owns the fact ──


def test_every_partner_has_a_declared_consumer_repository():
    """The gated check below iterates this map; assert it is real (ADR-014 §2)."""
    assert set(CONSUMER_REPO) == set(PARTNER_PACKAGES), (
        f"partners with no declared consumer repository: "
        f"{sorted(set(PARTNER_PACKAGES) - set(CONSUMER_REPO))}. Without one, that "
        "partner's consumer-name pin is never checked against the consumer."
    )
    undeclared = sorted(r for r in CONSUMER_REPO.values() if r not in SIBLINGS)
    assert not undeclared, (
        f"consumer repositories with no SIBLINGS entry: {undeclared}. "
        "require_sibling() raises KeyError rather than skipping for those, so the "
        "check would fail confusingly instead of skipping cleanly."
    )


#: The platform registry, relative to a views-appwrite checkout.
#:
#: Loaded locally rather than imported from ``tests/test_env_declaration.py``: a test
#: module importing another test module is a dependency nobody declared, and the two read
#: different things — that file reads coordinate sections, this one reads one contract
#: row. Two four-line readers that are understood beat one shared one that has to serve
#: both (WET before DRY).
_REGISTRY_RELPATH = Path("docs") / "ADRs" / "platform" / "coordinate_registry.toml"


def _registry(repo: Path) -> dict:
    tomllib = pytest.importorskip("tomllib", reason="stdlib from 3.11; pyproject requires it")
    return tomllib.loads((repo / _REGISTRY_RELPATH).read_text())


#: partner -> the registry row that is the AUTHORITY for its delivery label.
#:
#: Declared, never derived from the partner name: `unfao` -> `UNFAO_...` is mechanical,
#: `crafd` -> `UNCRAFD_...` is not, and guessing it would be the inference ADR-003 forbids.
_CONTRACT_ROW = {
    "unfao": "UNFAO_CONSUMER_DOCUMENT_NAME",
    "crafd": "UNCRAFD_CONSUMER_DOCUMENT_NAME",
}


def test_every_partner_has_a_declared_contract_row():
    """Assert this file's declared scope is the real one (ADR-014 §2).

    A partner missing from ``_CONTRACT_ROW`` is a partner whose delivery label is checked
    against nothing, and the suite stays green — which is exactly how ``crafd`` arrived
    the first time.
    """
    assert set(_CONTRACT_ROW) == set(PARTNER_PACKAGES), (
        f"partners with no declared contract row: "
        f"{sorted(set(PARTNER_PACKAGES) - set(_CONTRACT_ROW))}; declared but no longer a "
        f"partner: {sorted(set(_CONTRACT_ROW) - set(PARTNER_PACKAGES))}."
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_declared_consumer_name_matches_the_registry(partner):
    """ADR-017 §5, the producer half: our mirror against the public declaration.

    **What this replaces, and why.** Until 2026-08-11 this check read the *consumer's
    source* — a regex over `managers/api.py` looking for the argument to an
    `APIPathManager(...)` construction. That worked on a laptop and never in CI for the
    private partner, and it broke on 2026-08-11 when views-faoapi tidied that file into a
    named constant. Their code got better and our check went looking for something that
    had moved. ADR-017 §7: we were never entitled to depend on another repository's file
    layout.

    Now both sides read one public declaration. The registry lives in views-appwrite,
    which is public, so this needs no credential even for the private partner — that is
    the whole of ADR-017 §5 in one assertion.

    *"Neither reads the other" is the end state, not yet the present one:* CRAF'd's source
    is still read by the check below, until views-crafdapi#53 lands.

    The value it guards is the one whose failure is silent: a delivery filed under a name
    the consumer does not ask for is uploaded, stored, billed, and invisible — no error
    anywhere (ADR-013 §4.1a).
    """
    repo = require_sibling("views-appwrite")
    registry = _registry(repo)

    contract = registry.get("contract") or {}
    row = _CONTRACT_ROW[partner]
    assert row in contract, (
        f"[{partner}] the registry has no `[contract.{row}]` row. That row is the "
        "authority this package's CONSUMER_DOCUMENT_NAME mirrors (ADR-017 §5); without "
        "it there is nothing to check the mirror against. Either it was retired upstream "
        "or this file names the wrong row."
    )
    declared = contract[row].get("value")
    ours = _product(partner).CONSUMER_DOCUMENT_NAME
    assert declared == ours, (
        f"[{partner}] this package writes every delivery under {ours!r}, but the platform "
        f"registry declares {declared!r} in `[contract.{row}]`. The registry is the "
        "authority — the consumer owns this name and changing it is a contract amendment. "
        "A delivery under a name the consumer does not ask for is uploaded, stored, and "
        "invisible (ADR-013 §4.1a)."
    )
    assert declared == _CONSUMER_DOCUMENT_NAME[partner], (
        f"[{partner}] the pin in this file disagrees with the registry — the local "
        "always-on test above should have caught a mismatch with the module first."
    )


#: Partners whose consumer-side self-check has NOT landed yet, so this repository still
#: reads their source as well as the registry (ADR-017 §5's sequencing constraint).
#:
#: Declared rather than inferred, and deliberately a *shrinking* list: an entry leaves it
#: when that partner's own check lands, and the day it empties this whole mechanism goes.
_CONSUMER_SELF_CHECK_PENDING = {
    "crafd": "views-crafdapi#53",
}


def test_the_pending_list_is_not_empty_and_names_only_real_partners():
    """An empty map must be a prompt to delete code, not a silent skip.

    ``parametrize`` over an empty collection is a **skip** under pytest's default
    ``empty_parameter_set_mark``, and this repository declares no pytest configuration at
    all. So emptying this map — by a premature cleanup, or an edit made before
    views-crafdapi#53 lands — would retire the only check that reads what a consumer
    actually does, and report ``1 skipped`` on a green build. The registry check would
    then be comparing two values this platform authored to each other, which is the exact
    failure the retained test's docstring warns about.

    So the map is asserted non-empty. When it legitimately empties, this assertion is
    what tells you to delete the test, its regexes, and the sibling fetch that serves it.
    """
    unknown = sorted(set(_CONSUMER_SELF_CHECK_PENDING) - set(PARTNER_PACKAGES))
    assert not unknown, f"not partners: {unknown}"
    assert _CONSUMER_SELF_CHECK_PENDING, (
        "_CONSUMER_SELF_CHECK_PENDING is empty, which means every consumer now checks "
        "itself against the registry. That is the end state ADR-017 §5 describes — so "
        "finish it: delete test_the_consumer_still_filters_on_the_name_until_it_checks_"
        "itself, the _CONSUMER_PATH_MANAGER and _CONSUMER_FILTER patterns, and the "
        "views-crafdapi entry in tests/conftest.py::SIBLINGS whose note says that fetch "
        "serves exactly this one test. Leaving them costs a clone on every pull request "
        "and asserts nothing."
    )


@pytest.mark.parametrize("partner", sorted(_CONSUMER_SELF_CHECK_PENDING))
def test_the_consumer_still_filters_on_the_name_until_it_checks_itself(partner):
    """The source-read, kept ONLY for partners whose own check does not exist yet.

    ADR-017 §5 constrains the order: this repository stops reading a consumer's source
    when *that consumer* starts checking itself against the registry. Otherwise there is
    a window where the registry row is a string a human typed, our check compares our
    copy to it, and nothing anywhere consults what the consumer actually does — a green
    build proving only that two values this platform authored agree.

    views-faoapi#379 landed on 2026-08-11, so the FAO half of this check is gone.
    views-crafdapi#53 has not, so CRAF'd's stays — and with it the crafd sibling fetch,
    whose ``note`` in ``tests/conftest.py`` records that it lives or dies with this one
    check.

    **This test is meant to be deleted.** When #53 lands, remove that partner from
    ``_CONSUMER_SELF_CHECK_PENDING``; when the map empties, remove this test, the regexes
    it uses, and the fetch.
    """
    repo = require_sibling(CONSUMER_REPO[partner])
    pkg = _consumer_package(repo)

    api = (pkg / "managers" / "api.py").read_text()
    found = _CONSUMER_PATH_MANAGER.findall(api)
    assert len(found) == 1, (
        f"expected exactly one APIPathManager(...) construction in "
        f"{CONSUMER_REPO[partner]}'s managers/api.py, found {found}. This is the fragile "
        "half ADR-017 retires — a layout change there breaks a check here, which is what "
        "happened to the FAO half on 2026-08-11. It survives only until "
        f"{_CONSUMER_SELF_CHECK_PENDING[partner]} lands."
    )
    assert found[0] == _CONSUMER_DOCUMENT_NAME[partner], (
        f"{CONSUMER_REPO[partner]} filters on {found[0]!r}; this repository declares "
        f"{_CONSUMER_DOCUMENT_NAME[partner]!r}. A delivery under a name the consumer does "
        "not ask for is uploaded, stored, and invisible (ADR-013 §4.1a)."
    )

    manager = (pkg / "managers" / "prediction" / "manager.py").read_text()
    assert _CONSUMER_FILTER in manager, (
        f"{CONSUMER_REPO[partner]} no longer selects by {_CONSUMER_FILTER!r}. The name "
        "may still match while the consumer filters on something else entirely — same "
        "invisibility, different cause."
    )
