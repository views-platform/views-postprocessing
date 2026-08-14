"""Each partner's declared product — ADR-013 §4.2a/§6/§4.1a/§11.4 pins.

**Scoped to the FAO product until #211.** When `crafd/product.py` landed, every pin
here still read `unfao.product`: nothing asserted CRAF'd's consumer document name,
its target vocabulary, or that its upload interlock defaulted off. The values were all
correct — but "correct and unchecked" is the state a product declaration is in right
up until the day it is not, and §4.1a's failure mode is silence, not an error.

The consumer-name pin is the one that matters most and the one a partner-scoped test
could never catch: a document written under a name the consumer does not filter for is
delivered, stored, billed, and invisible. That is not hypothetical here — six forecast
documents sat in the UNFAO bucket for months, under a name nothing was looking for, while
FAO's forecast serving read empty (ADR-013 §11.4 post-adoption record, register C-01).
*(Named, not quoted: the bucket's declared value is a coordinate, and this docstring is
printed by pytest whenever anything in this file fails — register C-97.)*

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
from tests.seam_registry import registry_current

#: partner -> the document name its consumer filters on, DECLARED here rather than
#: read back from the module under test.
#:
#: A test that asserts ``product.CONSUMER_DOCUMENT_NAME == product.CONSUMER_DOCUMENT_NAME``
#: passes for every possible value, which is the shape of the replica defect epic #181
#: spent a story retiring. So the expected value is written out.
#:
#: **A literal transcribed from another repository is a guarantee, and ADR-014 §1 says a
#: guarantee needs a check.** On its own this pin catches drift authored *here*, which was
#: never the danger: if a consumer changed its filter tomorrow this file would stay green,
#: the delivery would upload, and the document would be invisible (ADR-013 §4.1a).
#:
#: ``test_the_declared_consumer_name_matches_the_registry`` closes that half against the
#: **public coordinate registry** rather than the consumer's source (vpp_017 (ADR-017) §5). It runs
#: for every partner and needs no credential, because the registry is public even when the
#: consumer is not — which is why it reaches the FAO partner and its predecessor could not.
#:
#: What it does **not** close is whether the consumer's query uses the name it declares.
#: This repository used to read their source for that; the check broke twice in 24 hours
#: because both consumers refactored a literal into a named constant, and #248 deleted it
#: rather than repairing it. Register **C-92** carries the gap; views-faoapi#390 and
#: views-crafdapi#55 are the asks that would close it where the fact lives.
_CONSUMER_DOCUMENT_NAME = {
    "unfao": "un_fao",
    "crafd": "un_crafd",
}

_PKG = Path(__file__).resolve().parent.parent / "views_postprocessing"

def _product(partner: str):
    return importlib.import_module(f"views_postprocessing.{partner}.product")


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

# ── across the seam: the pin above, checked against the registry that owns the fact ──


def test_every_partner_names_the_repository_that_consumes_its_delivery():
    """Every partner must name its consumer, and that name must be a declared sibling.

    **No test reads a consumer's checkout any more** (#248), so this no longer guards a
    call site. It guards the *addressing*: `CONSUMER_REPO` is how this repository says who
    receives each delivery, and it is what the cross-repo asks in register C-92 are
    addressed to. A partner with no consumer named is a delivery with no recorded
    recipient; a consumer named but absent from `SIBLINGS` is a name nothing else in this
    repository can resolve.
    """
    assert set(CONSUMER_REPO) == set(PARTNER_PACKAGES), (
        f"partners with no declared consumer repository: "
        f"{sorted(set(PARTNER_PACKAGES) - set(CONSUMER_REPO))}. Without one, nothing "
        "records who receives that partner's delivery."
    )
    undeclared = sorted(r for r in CONSUMER_REPO.values() if r not in SIBLINGS)
    assert not undeclared, (
        f"consumer repositories with no SIBLINGS entry: {undeclared}. Every repository "
        "this one names must be resolvable from one declaration, or the two lists drift."
    )


#: The registry reader is shared with ``tests/test_env_declaration.py`` — see
#: ``tests/seam_registry.py``.
#:
#: It began here as a local four-line copy, defended as WET. The copies immediately
#: disagreed: that module was moved to read the sibling's ``main`` after a review found
#: reading its working tree meant grading this repository against unreviewed content
#: (#196's shape), and this copy was left behind still reading the working tree. Two
#: copies of a rule are fine; two copies that answer the same question differently are
#: the second incident, which is this repository's trigger for extracting.


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
    """vpp_017 §5, the producer half: our mirror against the public declaration.

    **What this replaces, and why.** Until 2026-08-11 this check read the *consumer's
    source* — a regex over `managers/api.py` looking for the argument to an
    `APIPathManager(...)` construction. That worked on a laptop and never in CI for the
    private partner, and it broke on 2026-08-11 when views-faoapi tidied that file into a
    named constant. Their code got better and our check went looking for something that
    had moved. vpp_017 §7: we were never entitled to depend on another repository's file
    layout.

    Now both sides read one public declaration. The registry lives in views-appwrite,
    which is public, so this needs no credential even for the private partner — that is
    the whole of vpp_017 §5 in one assertion.

    *"Neither reads the other" is now the present state, not just the end state* — #248
    deleted the last source read. What that costs is register C-92: nothing here verifies
    that a consumer's query uses the name it declares.

    The value it guards is the one whose failure is silent: a delivery filed under a name
    the consumer does not ask for is uploaded, stored, billed, and invisible — no error
    anywhere (ADR-013 §4.1a).
    """
    repo = require_sibling("views-appwrite")
    registry = registry_current(repo)

    contract = registry.get("contract") or {}
    row = _CONTRACT_ROW[partner]
    assert row in contract, (
        f"[{partner}] the registry has no `[contract.{row}]` row. That row is the "
        "authority this package's CONSUMER_DOCUMENT_NAME mirrors (vpp_017 §5); without "
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
