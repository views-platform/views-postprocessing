# Class Intent Contract: CRAFDPostProcessorManager

**Status:** Active
**Owner:** PRIO MD&D Team
**Last reviewed:** 2026-08-26
**Related ADRs:** ADR-002, ADR-006, ADR-008, ADR-009, ADR-013
**Sibling contract:** [UNFAOPostProcessorManager.md](UNFAOPostProcessorManager.md)

---

> **This contract is stated as a delta, deliberately.** `CRAFDPostProcessorManager` is a
> clone of the UN-FAO manager (`docs/CLONING.md`, register **C-33**), and the two
> managers differ by fourteen lines on each side, none of which changes behaviour. Verify
> that rather than trusting this sentence:
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
  built by the same `contract/` code. Only the *product* differs.
- **This class is one of the repository's only two importers of `views_pipeline_core`**,
  mechanically pinned to an allowlist by `tests/test_doc_accuracy.py`. That is what keeps
  C-40's blast radius at one file per partner.

## 3. What differs — the whole of it

| | `unfao` | `crafd` |
|---|---|---|
| consumer document `name` | `un_fao` | `un_crafd` |
| partner store | `unfao_bucket` | `crafd_bucket` |
| env tuple validated | `appwrite_env.UNFAO_ENV` | `appwrite_env.CRAFD_ENV` |
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

**A note on the budget, current at this review:** `crafd/` sits at **699 of 700** lines.
The next line added anywhere in that package fails the guard, which is what the guard is
for. It is not a defect and is not scheduled; it is recorded so the next contributor meets
it here rather than in a red build.

## End of Contract

This document defines the **intended meaning** of `CRAFDPostProcessorManager`.

Changes to behavior that violate this intent are bugs.
Changes to intent must update this contract — and, where the intent is inherited, its
sibling.
