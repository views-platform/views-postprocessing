# Class Intent Contract: CRAFDPostProcessorManager

**Status:** Active
**Owner:** PRIO MD&D Team
**Last reviewed:** 2026-11-27
**Related ADRs:** ADR-002, ADR-006, ADR-008, ADR-009, ADR-013, vpp_018
**Sibling contract:** [UNFAOPostProcessorManager.md](UNFAOPostProcessorManager.md)

---

> **This contract is stated as a delta, deliberately.** `CRAFDPostProcessorManager` is a
> clone of the UN-FAO manager (`docs/CLONING.md`, register **C-33**). Measured 2026-11-27
> with the command below: **31 lines on the `unfao` side, 53 on the `crafd` side**, and the
> difference now DOES change behaviour — #327 gave the CRAF'd delivery a second Appwrite
> connection, which FAO does not yet have (#337). Until then the two managers are no longer
> the same program with the names swapped, and the row for it is in §3. Verify rather than
> trusting this sentence:
>
> ```
> diff views_postprocessing/unfao/managers/unfao.py \
>      views_postprocessing/crafd/managers/crafd.py
> ```
>
> A second full contract was considered and rejected. Two 189-line documents describing
> one behaviour is not redundancy, it is **two things that can disagree** — and this
> repository has already paid for exactly that: register **C-75**, where the sibling CIC
> and this directory's other file asserted opposite things about the same call for weeks.
> One contract, one delta. If the managers ever diverge behaviourally, C-33's extraction
> trigger has fired and this document's form should be revisited along with the code.

## 1. Purpose

`CRAFDPostProcessorManager` orchestrates the end-to-end postprocessing pipeline that
delivers VIEWS conflict predictions to the **Complex Risk Analytics Fund (CRAF'd)**,
served by views-crafdapi.

It is the single entrypoint for producing and delivering CRAF'd-formatted prediction data.

## 2. What this contract inherits

**Sections 2–11 of [UNFAOPostProcessorManager.md](UNFAOPostProcessorManager.md) apply
to this class unchanged**, substituting the partner identity below. That includes the
non-goals, the four-stage pipeline guarantee, the inputs and assumptions, the failure
modes and their loudness, the boundaries (ADR-002 topology: `crafd/` → `contract/` →
`delivery/`, one way only), and the test-alignment position.

Two of those are worth naming here because they are the ones a reader most often assumes
differ, and they do not:

- **The wire is partner-neutral** (#153). CRAF'd receives the same ADR-013 artifacts
  built by the same `contract/` code. Only the *product* differs — and, since #327, the
  *connection*: the artifacts are identical, the project they are written into is not.
- **This class is one of the repository's only two importers of `views_pipeline_core`**,
  mechanically pinned to an allowlist by `tests/test_doc_accuracy.py`. That is what keeps
  C-40's blast radius at one file per partner.

## 3. What differs — the whole of it

| | `unfao` | `crafd` |
|---|---|---|
| consumer document `name` | `un_fao` | `un_crafd` |
| partner store | `unfao_bucket` | `crafd_bucket` |
| env tuple validated | `appwrite_env.UNFAO_ENV` | `appwrite_env.SHELF_CONNECTION_ENV` + `AUDIENCE_CONNECTION_ENV` + `CRAFD_ENV` |
| Appwrite projects used | **one** — reads and writes the shared project | **two** — reads the shared project, writes CRAF'd's own (#327, **vpp_018**) |
| write credential | the platform key, shared with the read | `APPWRITE_CRAFD_PUBLISHER_API_KEY`, CRAF'd's own |
| isolation rule | none — there is one connection to isolate from | `contract/audience.assert_audience_is_not_the_shelf`, refusing before any byte moves; no fallback |
| consumer repository | views-faoapi | views-crafdapi (its ADR-034) |
| §11.4 interlock history | precondition met 2026-07-20 (faoapi C-161) | precondition met 2026-08-12 (views-crafdapi#53) |

`TARGETS` and `S_MIN` are **the same values today** (`lr_ged_sb`, `lr_ged_ns`,
`lr_ged_os`; `S_MIN = 2`) but are independently declared per partner and may diverge
without either being wrong — CRAF'd naming an additional target is an Amendment A1 edit
to `crafd/product.py` alone.

**Both partners are gated closed.** `product.UPLOAD_ENABLED` is `False` in each, and the
gate that holds is the same one for both: **views-appwrite#171**, the non-production
Appwrite project decision, without which the upload path cannot be rehearsed against a
real store (#18). The partner-specific preconditions in the table above are satisfied and
no longer gate anything.

## 4. The uncertainty surface is the consumer's, not this class's

CRAF'd is FAO *extended*: same forecasts, same PRIO-GRID geography, same cadence. The
additional surface CRAF'd wants — exceedance probabilities alongside HDI/MAP — is
computed in **views-crafdapi** (their ADR-034), not here. This producer ships the same
posterior-sample wire the FAO producer ships.

This is a **non-goal** and belongs in a contract because the alternative is attractive and
wrong: a manager that starts summarising draws for one partner has taken a consumer
concern into the delivery, and the §6 no-collapse gate exists to prevent exactly that.

## 5. Test alignment

Covered by the same source-scan and seam tests as its sibling, parametrised over both
partners via `PARTNER_PACKAGES` in `tests/conftest.py` — including
`tests/test_clone_readiness.py`, which asserts the two partner packages are **independent**
(neither imports the other), and the line budgets in `tests/test_doc_accuracy.py`.

**A note on the budget, current at this review:** `crafd/` sits at **737 of 760** lines
and `crafd/managers/` at **457 of 475** — measured 2026-11-27. Both bounds were raised by
#327, the package twice, and `tests/test_doc_accuracy.py` carries the measurements and the
argument for each. The note that stood here said 699 of 700 and had been true since
2026-08-26; what it did not say, and the reason it is worth recording at all, is that a
bound with no headroom turns the next unrelated comment into a red build. Both now carry
roughly twenty lines of deliberate slack.

**The lever if they bind again, measured:** `crafd/store_port.py` and
`unfao/store_port.py` are byte-identical at 111 lines each, and moving that port into
`contract/` would free 111 lines from both packages at once. It is not done, because the
duplication is a recorded decision — register **C-33**, re-affirmed with reasons on
2026-08-14 — whose extraction trigger is a third partner package or a bug hand-patched in
both copies. A line budget is not that trigger.

## End of Contract

This document defines the **intended meaning** of `CRAFDPostProcessorManager`.

Changes to behavior that violate this intent are bugs.
Changes to intent must update this contract — and, where the intent is inherited, its
sibling.
