# Technical Risk Register

| Register Info     | Details                              |
|-------------------|--------------------------------------|
| Project           | views-postprocessing                 |
| Owner             | Dylan Pinheiro / PRIO MD&D Team      |
| Last Updated      | 2026-08-03                           |
| Total Concerns    | 83                                   |
| Open Concerns     | 15                                   |
| Resolved Concerns | 68                                   |

---

## Tier Definitions

| Tier | Severity | Description |
|------|----------|-------------|
| 1 | Critical | Silent data corruption or model output correctness risk. Requires immediate attention. |
| 2 | High | Structural fragility that will cause failures under realistic change scenarios. |
| 3 | Medium | Maintainability or coupling issues that increase cost of change. |
| 4 | Low | Code quality concerns that do not affect correctness or reliability. |

---

## Causal Clusters

Clusters group open entries by shared **root cause** — fix the cause and the
symptoms collapse together. Restructured during review-rr 2026-07-31: the
original Clusters A–F all described the deleted runtime-mapper era and no longer
covered a single open entry (see Historical clusters below).

### Cluster G: Inherited pipeline-core surface
**Root cause:** this repo *is-a* pipeline-core postprocessor by double inheritance, so it inherits that project's data loader, container, store I/O, and dependency tree — defects in that surface land in FAO delivery without this repo owning the fix.
**Entries:** C-40 (root), C-26, C-27, C-28 — plus **C-07, C-13, C-29, C-44, C-58, C-62, all RESOLVED**
**Update 2026-08-03 — the cluster halved at the 3.0.0 bump.** Six of its ten entries closed with the pin: the inherited surface stopped being a liability for timeouts (C-13), silent provisioning (C-58), the transitive drag (C-62) and the undeclared SDK (C-07). What remains is the root — the double inheritance itself — and the three genuinely upstream-owned data concerns (C-26, C-27, C-28). The cluster's thesis held: fixing the surface upstream fixed them here with a pin and no code.
**Amended 2026-08-03:** the root's defining measurement — pipeline-core imported by exactly one module — became **two** when `crafd/managers/crafd.py` landed (PR #211). The count is still pinned by an explicit allowlist, so the cluster's boundary holds; what changed is that every fix in it now has two landing sites. See C-33 for why the second copy is deliberate and what triggers its removal.
**Highest tier:** 1 (C-26)
**Fix strategy:** the thin-shell de-inheritance C-40 prescribes — and which is **half-built**: the sink side landed (`_ContractStorePort`, `unfao.py:37-78`) and the invariants are already pipeline-core-free modules the manager calls (`delivery/*`, `unfao/historical.py`, `unfao/wire/`). The remaining half is the **input** side (loader + `PGMDataset`), gated on pipeline-core Epic #186/#207.
**Resolution scope:** Partial — C-26/C-27/C-28 are upstream-owned; de-inheritance makes them visible and testable, not fixed.

### Cluster H: Go-global verification debt — discharged unevenly by run-0
**Root cause:** a family of entries whose entire risk statement was "unverified until the first global run" — all keyed to one event, which occurred **2026-07-27**.
**Entries:** C-43 (the survivor), C-30 + C-34 (merged, discharged), C-32 (discharged), C-25 (residual), D-12 and D-09 (deferral conditions)
**Highest tier:** 2 (C-43)
**Fix strategy:** one post-run-0 verification pass against producer run `rusty_bucket_forecasting_20260727_095355` — issue **#131 q1**, **CLOSED 2026-07-31**. C-43 resolved 2026-08-02; this cluster is discharged.
**Resolution scope:** Full for C-30/C-32/C-34. **Partial for C-43 — the finding that matters.** Run-0 discharged the *availability* half of this cluster (the path runs, memory is bounded at 5.6 GB, coverage is proven at 64,742 cells). It discharged **none of the correctness half**, because proving the path *runs* at scale was never what C-43 asked for. **C-43 now stands alone and un-gated, with delivered data in the partner store.**

### Cluster I: Governance-artifact drift
**Root cause:** the register, ADR prose, and issue bodies are hand-maintained mirrors of cross-repo state that moves under them.
**Entries:** C-44, C-46, C-47, C-57, C-74 (a guard whose declared scan roots silently stopped existing — the cluster's disease inside the cluster's own prescription) — plus this register's own findings at review-rr 2026-07-31 (header miscount, two RESOLVED entries misfiled under Open, eight stale `unfao.py` line ranges after the manager grew 273→636 lines, two unnamespaced foreign-register IDs). Historical precedent: the entire C-48–C-55 ADR-013 audit series, and C-42/C-47.
**Highest tier:** 3
**Fix strategy:** this repo already solved this disease once — the ADR-013 audit series ended with **40 permanent guard tests** (`tests/test_falsify_adr013_*.py`), and the same pattern now guards the þing-01 invariants (`tests/test_env_declaration.py`, `tests/test_redaction_guard.py` — the latter briefly **only over the roots that still existed**, see C-74, resolved: a guard is only as good as the assertion that its inputs are real, and it now carries that assertion). There is **no equivalent for the register**. A small `tests/test_register_integrity.py` — header counts match section counts; no RESOLVED body under `## Open Concerns`; every `C-\d+`/`D-\d+` reference resolves or is namespaced to a foreign register — would make this class self-detecting.
**Resolution scope:** Full for the mechanical half.

### Cluster J: Delivery aftercare has no mechanism
**Root cause:** the delivery pipeline is write-only — nothing exists downstream of upload for correction, recall, or provenance audit.
**Entries:** C-22 (acute), C-15, C-24
**Highest tier:** 3
**Fix strategy:** the C-22 correction procedure (issue #15) plus pipeline-core #245's structured metadata field to retire the description-as-carrier abuse.
**Resolution scope:** Partial (process, not code).
**Newly acute 2026-07-31:** every entry here was written conditionally — "*if* wrong data ever reaches FAO." Run-0 shipped 108 arrow shards, a sidecar, a manifest and 28.3M historical rows to `unfao_bucket`, and its integrity verification is still open. The conditional is spent.

### Cluster K: The committed lookup artifact is trusted but unverified in CI
**Root cause:** `views_postprocessing/data/gaul_lookup.parquet` is a 64,742-row binary that the enricher, the historical builder and the wire sidecar all treat as ground truth — yet no test in the suite checks it against views-datafactory, and the build script's own guarantees are enforced by strippable `assert`s. Everything downstream verifies *presence* (nulls, counts, gid-set equality); nothing verified *values* until the 2026-07-31 forward-check.
**Entries:** C-59, C-61 (build-time guarantees unenforced), C-60 (provenance stamp can silently degrade), C-46 (the one cross-repo check is CI-skipped on a hardcoded path), C-43 (the value-correctness debt this cluster's fix discharges)
**Highest tier:** 3 (C-59, C-60, C-61 — C-59 recalibrated 2→3 on 2026-07-31 mutation evidence)
**Fix strategy:** one test file — `tests/test_gaul_lookup_fidelity.py` — split into an always-on half (gid uniqueness, region-set equality, coordinate formula against a committed ground-truth sample, no nulls, no `-1` codes) and a `skipif`-gated half comparing all 7 GAUL columns against the datafactory sibling. Plus two one-line hardenings in `scripts/build_gaul_lookup.py`: assert index uniqueness, and convert the bare `assert`s to explicit raises.
**Resolution scope:** Full for all five. C-59/C-61/C-43 discharged by the one test file this strategy predicted; C-60 by the flat declared `lookup_version` key (S5 / #186); C-46 by one declared way of resolving the producer's checkout (S7 / #188).

**✅ MOSTLY CLOSED 2026-08-02 (S2 / #183).** The prediction held: **one test file discharged three entries.** `tests/test_gaul_lookup_fidelity.py` (18 tests) closed **C-43**, **C-59** and **C-61** together, exactly as the fix strategy above said it would — the always-on half against the committed artifact, the `skipif` half against views-datafactory, plus the builder's bare `assert`s converted to `LookupBuildError` raises.

**What the cluster actually cost, and it is not what the entries said.** All three were **fixed on 2026-07-31 and stayed filed under Open until 2026-08-02**, C-43 with its own closing condition written into its body and already met. The engineering took one session; the *record* took two more days and a direct question from the maintainer to correct. That asymmetry is the finding — not the geography bug the cluster was opened for, which never existed.

**The lesson, and it generalises past this cluster.** C-43's residual said the forward-check *"was a one-off session result, not a standing guarantee"* — and the fix was to attach it to something the interpreter runs. The entries then reproduced the identical error one level up: they stated their closing conditions in prose and attached them to nothing. S2 therefore added a closing-condition check to `test_register_integrity.py`. **A guarantee needs a check, and that applies to the register's own guarantees too.**

**✅ CLOSED 2026-08-02 (epic #181).** All five entries resolved: C-59 and C-61 (build-time guarantees, S2), C-43 (the value-correctness debt, S2), C-60 (the declared `lookup_version`, S5) and C-46 (the machine-specific path, S7).

**The fix strategy predicted the shape correctly** — *"one test file, split into an always-on half and a `skipif`-gated half, plus two one-line hardenings in the builder"* — and that is what discharged three of the five. What it did not anticipate is that the cluster's own tooling was part of the problem: the gated half it prescribed could not run for anyone but the maintainer (C-46), and the provenance stamp it relied on could silently become the string `"unknown"` (C-60). A cluster about *"the artifact is trusted but unverified"* had a verification apparatus that was itself partly unverifiable.

**What remains is not this repo's:** the artifact is now checked value-for-value against views-datafactory's parquets, but whether the **producer's** area-majority join is correct at high latitudes is views-datafactory#387. C-43's scope split holds — transcription fidelity is proven, assignment correctness is not ours to prove.

### Cluster L: The won migration was never cleaned up
**Root cause:** the frame-native contract path replaced the pandas path and **won** — run-0 delivered global-land on 2026-07-27 and FAO has been served from it since. The replaced path was deliberately kept behind a config fork "until run 0 proves the contract path live" (C-40) and was then never removed. Everything below is residue of that one omission, not independent defects.
**Entries:** C-63 (the fork is silent), C-64 (an invariant nothing calls), C-65 (a seam four-fifths dead), C-66 (an object built and unused), C-68 (a private name holding the survivors together) — plus **#145** (the retired path's uploads discard their failure result) and **C-40**'s residual scope.
**Highest tier:** 2 (C-63)
**Fix strategy:** one deletion, not five fixes. Remove the retired path and replace the silent fork with a loud refusal; C-64/C-65/C-66/C-68 collapse as consequences. D-11 ratified exactly this shape ("concrete siblings + delete") and named the missing step: *"only correct if the legacy forecast branch is actually deleted… If it lingers, three-way duplication becomes the permanent shape."*
**Resolution scope:** Full for C-63/C-65/C-66/C-68 and #145; partial for C-64 (the identity rule's *home* still needs deciding) and C-40 (the double-inheritance shell is separate work).

**✅ CLOSED 2026-08-01 (epic #148, stories #149–#156).** The prediction held: it was **one deletion, not five fixes**. Retiring the legacy delivery path (#149) collapsed the cluster — C-63 closed with it, and C-64, C-65, C-66 and C-68 followed as consequences rather than as separate repairs, each in its own story so the reasoning survives. #145 closed with the path that carried its silent uploads, and **C-29** turned out to be cluster residue too — its disk side-channel was the legacy leg. C-25 closed alongside as *superseded by mechanism*.

**What the cluster cost, measured:** the manager went 636 → **406 lines**, 14 config forks → **0 plus one refusal**, pandas importers 3 → **1**, lookup reads per delivery 3 → **1**. Nine register entries closed.

**The lesson worth carrying, and it is D-11's:** WET-before-DRY was applied *correctly* — the pandas and frame seams ran as deliberate siblings through the migration, and a premature abstraction would have outlived the implementation it existed to unify. What went wrong was not the duplication; it was that the removal condition (*"until run 0 proves the contract path live"*) was written down without a **named trigger to act on**, so the box expired on 2026-07-27 and nobody opened it. D-11 predicted exactly this. **A deferral needs an owner and a trigger, not just a reason.**

### Epic #181 closeout — "every claim checkable" (2026-08-02)

**Eleven stories, ten register entries closed, one cluster closed, one ADR written.** Recorded here rather than only in the issue tracker, because an epic that ends in a closed issue ends nowhere a future reader looks.

| closed | by | proven by |
|---|---|---|
| **C-71** ADR-008 in the entry validator | S1 | a check parametrised over **both** validators, so the pair cannot drift again |
| **C-43, C-59, C-61** Cluster K's build-time guarantees | S2 | `tests/test_gaul_lookup_fidelity.py`, 26 tests |
| **C-03** the `_validate` replica | S4 | 43 self-referential tests replaced by 14 against the real gate |
| **C-60** the lookup's declared version | S5 | the artifact rebuilt, values byte-identical, stamp unchanged |
| **C-57** coordinate-registry drift | S6 | four checks, each mutation-proven |
| **C-46** the machine-specific path | S7 | `grep -rn "/home/"` over the repo → 0 |
| **C-74** the þing-01 redaction guard | S10 | scan coverage 6 → 17 files |
| **C-22** the correction procedure | S8 | written for the delivery that exists; partner-facing step decided 2026-08-02 |

Plus, outside the register: #158's rename finished and the **broken URL it created** in ADR-013 §7d repaired (Erratum E2); #154's undone half completed across four living documents; #15 superseded; a cross-repo pin re-taken after #196 showed it sat on an unmerged branch.

**Open count 24 → 15 (review-rr, 2026-07-31) → 16 at the #211 closeout → 16 after the 3.0.0 bump**, the bump having closed six while three governance entries were opened. Every remaining entry is classified: **one** still blocked upstream (C-72 — the pyarrow CVE whose fix changes wire bytes), **four** owned by another repo (C-24, C-26, C-27, C-28), **four** deliberately deferred (C-15, C-30, C-33, C-40), and the rest verification and governance debt (C-75 through C-82). None is unexamined.

**What the epic did NOT do, stated because a closeout that reports only successes is the defect this epic exists to fix:**

1. **Cluster M is untouched and correctly so.** Six entries, two of them Tier 2, all resolving on one upstream publish. No engineering here moves them.
2. **The CI question is decided in writing but not implemented.** Three gated cross-repo checks run nowhere automatic. C-46's residual carries the argued recommendation — *do not couple per-PR CI to another repo's default branch; if wanted, a weekly scheduled check that opens an issue on divergence* — with a named trigger. **It is a decision awaiting an owner, not a task awaiting effort.**
3. **Withdrawal of a bad delivery is the chosen policy and is not built.** Supersession is in force because it is what the wire does. Deliberately not started: it needs an ADR-013 amendment plus views-faoapi work, and FAO's answer on audit requirements (Pre-Release Note 07, B.2) decides whether it is wanted at all.
4. **Two questions are with the UN FAO**, not with us — recipients and notification timing (B.1), withdrawal versus supersession (B.2).
5. **`test_datafactory_deploy_readiness`'s `xfail` tuning was left alone**, deliberately: S7 fixed how the checkout is found, not what the gate asserts. If it needs re-pinning now that datafactory has moved past `v1.4.0`, that is a separate judgement.
6. **The local Python is 3.10 while `pyproject` declares `>=3.11`**, so three checks skip on the maintainer's machine and run in CI. Not a repo defect; recorded because "a gate that does not run" is the shape C-46 was open for.

**The lessons are in [ADR-014](../docs/ADRs/014_claims_and_the_guards_that_carry_them.md)** — including §5, the one rule no test can carry, which is written down *because* it cannot be mechanised. The attempt to mechanise it is recorded there too, so the next person does not repeat it.

**The sharpest thing the epic produced** is smaller than any of its stories: **existence is not reachability.** A cross-repo pin existed, its files existed at it, every check written at the time passed — and it had never reached `main`.

---

### Cluster M: Six open concerns, one upstream publish
**Root cause:** this repo pins `views-pipeline-core >=2.1.3,<3.0.0`, which resolves 2.3.0 from PyPI. Every fix and every removal below exists **only** on pipeline-core's unreleased 3.0.0. None is engineering work here; all five arrive together with one pin bump, and none can be taken before that bump.
**Entries:** **C-72** — and nothing else. **DISCHARGED 2026-08-03 apart from that one.**

The cluster held six entries waiting on a single upstream publish. views-pipeline-core 3.0.0 reached PyPI on 2026-08-03 and the operator took the bump: **C-44** (the bump itself), **C-62** (the transitive drag — geopandas and torch out, 155 → 118 packages), **C-73** (the Tier-2 stale-run defect), **C-58** (the Tier-2 auto-provision), and **C-07** (the undeclared `appwrite` dependency) all closed together, each verified in the installed wheel rather than from the changelog.

**C-72 does not close with them, and the difference is instructive.** The other five were fixed *upstream* and arrived with a version number. C-72's fix — a pyarrow release past the CVE — **changes delivered wire bytes**, so it needs a coordinated three-repo re-vendor of the ADR-013 §10 golden fixture. A pin bump cannot carry it. The pyarrow ceiling is deliberately unchanged at `>=16.1.0,<17.0.0`.

*(An earlier version of this cluster claimed "Full" resolution for C-72 at the 3.0.0 bump — the error C-82 was registered for, corrected here.)*
**Highest tier:** 2 (C-73)
**Fix strategy:** none here. The chain is **views-evaluation 0.5.0 → views-pipeline-core 3.0.0 → this repo's pin bump**, and it moves on the maintainer's platform-wide release signal, not on engineering. What this repo owes at the bump is one verification, recorded in C-73's trigger: **confirm the delivery selects the run it expects**, comparing the resolved `run_id` against the producer's newest published run.
**Resolution scope:** Full for C-62, C-73, C-58, C-07; C-44 closes as the act itself. **C-72 does NOT close** — see above. Five entries, two of them Tier 2, on one publish.

*(This line said "Full for C-62, **C-72**, C-73…" until 2026-08-03 — three lines below the paragraph correcting exactly that claim. I fixed the prose and left the scope line, which is the same defect one sentence apart. `test_register_integrity.py` has ten checks and none compares a cluster's scope line against its entries' actual status; that is why it passed. Recorded rather than quietly fixed, because it is C-82's subject occurring inside C-82's own correction.)*
**Why this cluster is worth having:** it stops five entries reading as five backlog items. They are one blocked action, and the register should say so rather than let a reader triage them separately five times.

### Historical clusters (mapper era — all resolved or moot)

Clusters **A** (cache architecture never unified), **B** (silent error-hiding
architecture), **C** (module-level import side effect), **D** (mapper–manager
boundary contract), **E** (replace runtime mapper with precomputed lookup) and
**F** (CIC–code drift) governed the register from 2026-06-02 to 2026-06-24. All
were dissolved by ADR-011's execution and the runtime-mapper deletion (**C-39,
PR #42**): C-02, C-04, C-05, C-06, C-10, C-11, C-12, C-14, C-16, C-17, C-19,
C-20, C-21 and D-01, D-02, D-03, D-04 all describe code that no longer exists,
and Cluster E's own goal shipped as `GaulLookupEnricher`. Cluster B's operational
residue survives as **C-22** (now in Cluster J); Cluster E's upstream residue as
**C-08** (relocated to views-datafactory). Full cluster text is preserved in git
history at `3f1ea1f` and earlier; it is omitted here because a navigation aid
that indexes only deleted code is noise.

---

## Open Concerns

### C-15: Upload metadata lacks enrichment provenance and carries test description

| Field | Value |
|-------|-------|
| ID | C-15 |
| Tier | 3 |
| Source | `expert-review` (2026-06-02), `falsification-audit` (2026-06-02) |
| Trigger | When wiring pipeline-core #245's structured metadata field, or when adding/removing a provenance key — verify the closed keyset in `delivery/provenance.py` and the `DESCRIPTION_MAX` bound still hold, and that the carrier is no longer free-text `description` |
| Location | `views_postprocessing/delivery/provenance.py` (`build_provenance`); `_historical_frame_description` in each partner's manager (the only caller); `contract/wire/sink.py` (the forecast leg, which attaches none). Symbols rather than line numbers — the earlier row's three line ranges were all past end-of-file. |

Both `dsm.upload_data()` calls in `_save()` carry metadata: `name`, `loa`, `type`, `targets`, `description`, `category`. The `description` field was updated from a hardcoded test string to an enrichment timestamp (`"Enriched with geographic metadata on {timestamp}"`). However, broader enrichment provenance is still missing: no shapefile version/hash, no enrichment error count, no unmapped cell count. The consumer cannot verify which shapefile version produced their data or whether any errors occurred during enrichment.

Tier recalibrated from 4 to 3 during falsification audit (2026-06-02): the missing provenance affects the partner's ability to audit data quality.

**Mitigation landed (S5, 2026-06-26, `sprint/fao-input-integrity`):** a representation-free `delivery/provenance.py` (`build_provenance`) assembles structured provenance — `lookup_version`, `region`, `expected_cell_count`, `actual_cell_count`, `unmapped_count` — sourced from the enricher + S1 coverage + a new `extraction.unmapped_cell_count` seam (nothing hardcoded). The historical upload carries it via `_historical_frame_description`. *(This sentence said "Both `_save` uploads now carry it via `_delivery_description`" — that method was deleted with the legacy path in #149, and there is now only one provenance-carrying upload: the forecast leg's shards carry `{name, category, loa}` and no `description` at all, which is the residual below.)* **Carrier constraint:** pipeline-core's `upload_data` exposes **no structured field** — only free-text `description` — so the dict is JSON-encoded into `description` behind a human prefix for now. A dedicated metadata field is requested upstream (**pipeline-core #245**); when it lands, only the manager's attach step changes (the provenance shape is already representation-free). `fill_count` is omitted until a fabricated-value count is available (cf. C-26). Residual is now just the carrier abuse, tracked by #245.

See also C-14 (stale cache without version tracking), C-22 (no post-delivery correction process), C-26 (fabricated zeros — the eventual `fill_count` source).

---

### C-24: Postprocessor output schema diverges from FAO-confirmed API contract

| Field | Value |
|-------|-------|
| ID | C-24 |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When views-faoapi implements the Release-Note-01 Topic-C renaming layer — verify this repo's column names stay **unchanged** (faoapi's `_METADATA_COLS` validation depends on them) and that the rename lands consumer-side only. Take no action here otherwise. |
| Location | `contract/gaul_schema.py` (`METADATA_COLS`, the declared 9-column contract); `contract/historical.py` and `contract/wire/sidecar.py` (which project it); FAO Release Note 01 `topic_c.tex`. *(This row previously cited `unfao.py:277 (filter_cols)` — no such symbol exists anywhere in the package, and `unfao/gaul_schema.py` moved to `contract/` in #153.)* |

The FAO API contract (Release Note 01, Topic C, confirmed and locked) specifies: UN M49 country codes, `ADM1_CODE`/`ADM1_NAME`/`ADM2_CODE`/`ADM2_NAME` for admin fields, and `lat`/`lon` for coordinates. The postprocessor's `filter_cols` uses: `country_iso_a3` (ISO Alpha-3), `admin1_gaul1_code`/`admin1_gaul1_name`/`admin2_gaul2_code`/`admin2_gaul2_name`, and `pg_xcoord`/`pg_ycoord`. Three of four data categories (country ID, admin fields, coordinates) use different naming conventions from the locked contract.

**D-06 resolved (2026-06-03):** Investigation of views-faoapi confirms NO renaming layer exists. The `FAOApiManager` passes postprocessor column names through to the HTTP response unmodified. FAO receives `country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord` — not the contract-specified names. The column renaming from Release Note 01 Topic C was never implemented in any repo.

**Cross-referenced upstream 2026-08-01** on views-faoapi **#222** (their output-schema epic, which mentions column renaming) asking directly whether the Topic-C rename is in its scope — with an explicit offer to close this entry pointing there if so, or to file it properly if not. Open fourteen months without a home in the repo that owns the fix.

**This is NOT this repo's responsibility to fix.** The schema mismatch is between the API layer (views-faoapi) and the FAO contract. The postprocessor should keep its current column names — changing them now would break views-faoapi's `FAO_PGMDataset._METADATA_COLS` validation. The renaming belongs in views-faoapi as a response-formatting step, coordinated with FAO.

See also C-17 (RESOLVED — implicit column naming between mapper and manager), D-06 (resolved: no renaming layer exists).

**Tier recalibrated from 2 to 3 during review-rr (2026-07-31):** the entry's own conclusion is that this is **not this repo's defect to fix** and that the correct action here is *inaction* (keep the current names). Tier 2 asserts structural fragility in this repo; what actually exists is a tracking stub for a views-faoapi contract gap, with a real but externally-owned consequence. Tier 3 (coordination / cost-of-change) matches. No change to the substance or the standing instruction.

---

### C-26: Unconditional fillna(0.0) fabricates "no conflict" from missing upstream data

| Field | Value |
|-------|-------|
| ID | C-26 |
| Tier | 1 — silent data fabrication with no error signal: absence of evidence becomes evidence of absence in FAO-delivered values |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When changing the historical fetch path, or when bumping views-pipeline-core's dataloader — verify whether the **currently active** path (`get_feature_frame`, since #126) zero-fills missing months/cells, and that any fill count is logged rather than silent |
| Location | views-pipeline-core `modules/dataloaders/dataloaders.py:1208` (`fillna(0.0)`, legacy pandas fetch); consumed at `views_postprocessing/unfao/managers/unfao.py:125-147` (`_read_historical_data`, legacy branch). Frame-native branch: `:101-124` (`_read_historical_frame` → `get_feature_frame`) |

`_fetch_data_from_datafactory()` applies `df.fillna(0.0)` unconditionally to all features. For `lr_ged_sb/ns/os`, a datafactory assembly gap (unharvested month, failed source) flows to FAO as "zero fatalities" rather than failing. The postprocessor's `_validate()` checks only the 9 metadata columns for nulls (`unfao.py:188-221`), never the feature columns — so the fabricated zeros pass every gate. There is no fill-count logging, so the corruption is unquantified and undetectable after the fact. The zarr exposes `last_valid_month_id` in its attributes, which would permit bounded filling (fill only outside the declared valid range, fail on fills inside it), but it is not consulted.

Location is in views-pipeline-core, but the impact lands on this repo's FAO delivery; registered here because the consuming call and the delivery responsibility are here.

**Filed upstream 2026-08-01 as views-pipeline-core#366**, carrying the open question this entry could not answer from this seat: **does `get_feature_frame` inherit the same unconditional `fillna(0.0)`, or does the frame-native fetch propagate NaN?** That decides whether C-26 is live (run-0 shipped 28.4M historical rows through the frame path) or historical (it describes only the branch #149 retired). The entry stays Tier 1 until answered — deliberately not downgraded on a guess.

See also C-25 (same data path, wrong-file variant), C-15 (upload provenance would aid post-hoc detection).

**OPEN VERIFICATION QUESTION (review-rr 2026-07-31) — tier held at 1 pending an answer.** `fillna` has **zero occurrences in this repo**; the fabrication site is entirely upstream. Since #126, the historical path run-0 actually used is `get_feature_frame` (`_read_historical_frame`), **not** the pandas `get_data` branch that reaches `dataloaders.py:1208`. It could not be verified from this seat (views-pipeline-core is deliberately absent from test environments, per repo convention). **Question for the pipeline-core seat: does `get_feature_frame` inherit the same unconditional `fillna(0.0)`, or does the frame-native fetch propagate NaN?** If it propagates NaN, this Tier 1 now describes only the legacy branch (retirement is the named post-run-0 follow-up) and should be re-tiered. **Do not downgrade on inspection of this repo alone** — the deliverable ran through the unverified path at global scale on 2026-07-27.

---

### C-27: Loader construction failures swallowed — surface as remote AttributeError

| Field | Value |
|-------|-------|
| ID | C-27 |
| Tier | 2 — structural fragility: any dependency or config breakage is converted into a misleading crash far from its cause |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When bumping views-pipeline-core, or changing this postprocessor's queryset/config — verify a `ViewsDataLoader` construction failure surfaces its real exception rather than a downstream `AttributeError`; today it is caught bare, logged as "No Queryset detected" with `exc_info=False`, and replaced with `self._data_loader = None` |
| Location | views-pipeline-core `managers/model/model.py:883-902`; crash sites `views_postprocessing/unfao/managers/unfao.py:105` (`_read_historical_frame`), `:134` (`_read_historical_data`) |

**Filed upstream 2026-08-01 as views-pipeline-core#367**, cross-referenced to their **#168** (views-pipeline-core C-166, narrow Appwrite exception handling) as the same defect class on a different call path — catch broadly, guess at the cause, discard the evidence — worth deciding once rather than twice.

`_initialize_data_loader()` catches bare `Exception`, discards the traceback, and nulls the loader. The failure then surfaces as `AttributeError: 'NoneType' object has no attribute 'get_data'` in `_read_historical_data` — the operator debugs the postprocessor while the cause (import error, malformed config, path issue) was erased at construction time. Cost is time-to-diagnosis during exactly the runs where time matters.

---

### C-28: No timeout on the datafactory zarr fetch — historical path can hang indefinitely

| Field | Value |
|-------|-------|
| ID | C-28 |
| Tier | 2 — same hazard class as C-13, on the other input path; a stalled chunk read blocks delivery with no deadline or alert |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When configuring the datafactory zarr fetch, or bumping views-pipeline-core's dataloader — verify a read deadline exists on the HTTP path; today none does anywhere on the fetch path, so a mid-chunk stall blocks the run forever |
| Location | views-pipeline-core `modules/dataloaders/dataloaders.py:1180-1188`; views-datafactory `src/datafactory_query/dataset.py:106-217` |

`load_dataset()` opens a remote zarr over plain HTTP. xarray chunk reads have no timeout; a stall blocks the scheduled run forever, and the only detection is manually noticing a run never finished. Risk grows with the planned global region (~5× data volume → longer fetch window). Partial overlap with C-13 (no timeout on Appwrite operations) — same problem type, different dependency and repo; registered separately because the fix sites are disjoint.

See also C-13.

---

### C-30: GAUL-uncovered land cells crash or corrupt global delivery (absorbs C-34: the coverage contract)

| Field | Value |
|-------|-------|
| ID | C-30 |
| Tier | 2 — the exclusion manifest and cell-count contract are pinned in code and were exercised live at global scale in run-0; residual is upstream-regression risk, not an unguarded silent-corruption path |
| Source | `expert-code-review` (2026-06-12), verified by direct data inspection; **merged with C-34** (`expert-code-review` 2026-06-12) during review-rr 2026-07-31 |
| Trigger | When a region's expected cell count or exclusion manifest changes upstream — a views-datafactory region redefinition (`regions.py`, the bundled `*_pgids.json`), a new GAUL curation like ADR-043, or a region-string change in views-models `config_queryset.py` — verify `EXPECTED_CELLS_BY_REGION` and `EXCLUDED_GIDS_BY_REGION` are re-derived from the live producer rather than trusted as frozen |
| Location | `views_postprocessing/delivery/coverage.py:56` (`land_gaul: 64_742`), `:92` (`EXCLUDED_GIDS_BY_REGION`), `:99`; `views_postprocessing/unfao/managers/unfao.py:397` (`_check_coverage`), `:300` (`_validate`); views-models `postprocessors/un_fao/configs/config_queryset.py`; views-datafactory `src/datafactory_query/regions.py` |

Verified 2026-06-12: of the datafactory's 64,818 `land`-region cells, 64,736 have complete area-majority metadata; exactly 82 are unassigned across all 7 GAUL fields — all remote sub-Antarctic islands FAO's GAUL 2024 boundaries do not cover (Macquarie, Auckland Islands, Prince Edward; sample gids 51078, 51798, 53979, 62356, 94776, 99027). The mitigation must be a named exclusion-list constant with the gids, count-asserted in both the enricher and a test, logged at WARNING, and disclosed to FAO — not a generic `code != -1` filter, which would silently absorb future coverage regressions. Generalizes the previously documented "5 ocean cells" of africa_me_legacy (those 5 are among the excluded set).

**Count drift corrected 2026-06-26 (the frozen-list tripwire working as designed):** deriving the exclusions from the live producer (datafactory **v1.4.0**) gives **64,742** complete + **76** excluded, *not* the 64,736 / 82 verified on 2026-06-12. Cause: datafactory **#163 (ADR-043)** supplemented **6 Azorean cells** (gids 182470, 183190, 183909, 183910, 186058, 186778) into `land_gaul` — they are now covered, not excluded. vpp's *own* built lookup (`data/gaul_lookup.parquet`) already ships 64,742, so the old 64,736 pin would have false-positived against our own artifact. NB the authoritative exclusion source is the **region complement** `land − land_gaul` (76), not the raw `gaul0_code == -1` (82) — the latter does not reflect the ADR-043 curation.

**Mitigation landed (S4, 2026-06-26, `sprint/fao-input-integrity`):** the 76 excluded gids are pinned as a frozen manifest in `delivery/coverage.py` (`EXCLUDED_GIDS_BY_REGION`), the count is corrected to 64,742, `assert_no_excluded_cells` is wired into the manager's `_check_coverage` **region-gated** (a no-op for unpinned `africa_me_legacy`, so its 5 ocean cells are unaffected), the 76 are disclosed in `docs/fao_excluded_cells.md`, and a test cross-checks the manifest against the datafactory sibling when present (drift tripwire). **Residual:** still Tier 1 until the live `land_gaul` run (views-platform/views-models#127) exercises it end-to-end — the guard is unit-proven but not yet run against a real global delivery.

**RESIDUAL DISCHARGED 2026-07-27 — run-0 exercised the guard live.** The stated residual was "*still Tier 1 until the live `land_gaul` run (views-models#127) exercises it end-to-end — the guard is unit-proven but not yet run against a real global delivery.*" **Run-0 delivered on 2026-07-27** against producer run `rusty_bucket_forecasting_20260727_095355`: `region=land_gaul`, coverage gate reported **64,742 distinct cells / 28,356,996 rows** for the historical frame, the forecast leg shipped 108 shards + sidecar + manifest, and the process exited cleanly with no loud failures. The pinned count and the 76-gid exclusion manifest were both correct against a real global delivery. **Tier recalibrated from 1 to 2 during review-rr (2026-07-31):** the silent-corruption path is now guarded and proven, so what remains is regression risk under upstream change — which is exactly what the rewritten trigger watches.

**MERGED: C-34 (Spatial coverage has no contract) absorbed here, review-rr 2026-07-31.** C-34 registered the absence of any expected-cell-count assertion, with the coverage decision split across three repos (views-models region string → views-datafactory cell-set → consequences here). Both concerns are now implemented by **one module** (`delivery/coverage.py`) and were discharged by **one event** (run-0), so tracking them separately doubled the maintenance without adding signal. C-34's distinctive contribution — that the trigger is an *upstream* region/cell-set change in either of two other repos — is carried into the merged trigger and Location above. C-34 remains as a forwarding stub in Resolved Concerns.

See also D-10 (handling decision), C-43 (the *value*-correctness sibling — run-0 discharged coverage but **not** enrichment-value verification), C-26 (the other coverage-integrity-without-signal path).

---

### C-33: Store identity hardcoded throughout the manager — blocks the planned multi-store rollout

| Field | Value |
|-------|-------|
| ID | C-33 |
| Tier | 2 — two to three additional Appwrite stores are planned imminently; the current design forces copy-pasting a 273-line manager per store |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | **Fired 2026-08-03 — see the update below.** The remaining trigger is the *extraction* one, and it is now named: a **third** in-repo partner package, **or** the first bug that must be hand-patched identically in both manager files — whichever comes first. |
| Owner | Whoever adds the third partner package, or hits the first double-patch. Until one of those happens the duplication is the deliberate WET position, not a task anyone is behind on. |
| Location | `views_postprocessing/<partner>/managers/<partner>.py` — `_prod_forecasts_datastore`, `_<partner>_datastore`, `_<partner>_appwrite_config`, and the four hardcoded `os.getenv("APPWRITE_<PARTNER>_*")` literals inside the last of those; declared names in each partner's `appwrite_env.py`. **Symbols, not line numbers** — see the note under the measurement below. |

Mitigation: a small `DeliveryProfile` (bucket/collection/database ids, category, targets) passed to the manager — one manager class, N store configs. Scheduled **after** the FAO global delivery ships (D-09); the only immediate action is deleting the commented-out config blocks at lines 80-107, which are a mis-uncomment hazard during deadline work.

**Update 2026-07-31 (review-rr — two stale facts corrected, and the deferral has expired):**
1. **The dead config blocks are gone.** `unfao.py:80-107` is now the class definition and `__init__`; the commented-out alternative `AppwriteConfig` blocks no longer exist. That immediate action — and D-09's first named exception — is **discharged**.
2. **"273-line manager" is stale**: `unfao.py` is now **636 lines**, so the copy-paste-per-store cost this entry warns about has roughly doubled.
3. **Partially mitigated by þing-01 #134.** `unfao/appwrite_env.py` now declares the env **names** centrally (`CONNECTION_ENV`, `PROD_FORECASTS_ENV`, `UNFAO_ENV`) and validates them fail-loud before every `AppwriteConfig` construction, following the PLATFORM-001 coordinate registry. Names are no longer scattered string literals. **What is still hardcoded is store *identity*** — which names apply to which store, the targets list, and the category strings — so the `DeliveryProfile` case stands. Tier held at 2.
4. **The deferral condition has expired**: D-09 scheduled this "after the FAO global delivery ships." It shipped 2026-07-27. Ready for the "calm 1-day job" whenever #97 scoping lands.

**Update 2026-08-03 (PR #211) — the thing this entry warned about has happened, and it is being kept on purpose.**

This entry's own Tier-2 rationale was that the design *"forces copy-pasting a 273-line manager per store."* PR #211 added `views_postprocessing/crafd/` — a second partner package whose `managers/crafd.py` is a **line-for-line copy** of `unfao/managers/unfao.py`. Measured with

    diff views_postprocessing/unfao/managers/unfao.py \
         views_postprocessing/crafd/managers/crafd.py | grep -c '^[<>]'

**32** — sixteen differing lines on each side. Substitute every form of the partner name (case-insensitively, including `un_fao`/`un_crafd` and `faoapi`) and it falls to **2**: one line per side.

The sixteen are, by category: one import, one class name, two partner-named method definitions, their two call sites, one refusal-message string, one line that is *both* the `*_ENV` tuple reference and the store label, the four env-name literals, and four lines of prose.

**None of the difference is behaviour, but "byte-identical" is too strong for one method.** `_read`, `_transform`, `_validate`, `_check_coverage` and `_build_historical_artifact` are byte-identical. `_save_contract` is not: five of the sixteen fall inside it — the datastore call, two comments, and the refusal string. All five are partner-name substitutions; none changes what the method does.

*(**This paragraph was wrong five times, and how it was wrong is the entry's most useful content.** (1) "roughly ten lines", carried from the review that found it and never measured. (2) A normalised count of 4 and a claim that `_save_contract` was byte-identical, neither checked. (3) A story that #211 "fixed two divergences that already existed" — false: at `9799e87` the second line was **byte-identical in both files**, an inherited inaccuracy rather than a divergence, and rewording CRAF'd's copy is what *created* a divergence there. Only the `:222` pair was real. (4) and (5) An exact list of sixteen line numbers and a line count, invalidated twice within the hour by comment corrections elsewhere in the same file.*

*The fix was not a sixth careful re-count. **Neither this measurement nor any `Location` field in C-33, C-40, C-77 or C-79 states a line number any more** — they name symbols, which grep can find and which survive an edit above them. There was a sixth failure, and it is why: a draft of this very paragraph announced that the entry "no longer states line numbers" while its own `Location` row still carried six, every one of them shifted by four lines by a comment correction made in the same commit. `tests/test_doc_accuracy.py` had already written the rule down — "The FILE is the claim; the line number is not." A count a reader relies on is a claim under ADR-014 §1, and each of these six was written by someone who believed it.)*

**The duplication is the right call today, and this is the record that says why.** CLAUDE.md's WET rule asks for a *second incident* before extracting, and this is genuinely it: one implementation showed nothing, two show that the seam is trivial — a partner-config object, not a behavioural one. The two candidate abstractions are both worse than the copy. A shared base class would stack a second, repo-owned Template Method under pipeline-core's imposed one, producing a three-tier inheritance chain to deduplicate ~10 lines; it would also have to live somewhere, and `contract/` is pinned pipeline-core-free by `tests/test_clone_readiness.py`. A factory solves a dispatch problem this system does not have — each partner is wired explicitly by its own launcher config, and nothing selects a manager class at runtime.

**What was missing was the trigger, and ADR-014 §4 says a deferral without one is not a deferral.** It is now in the Trigger field above. Both halves matter: a *third* package is the point at which "two copies you can hold in your head" becomes sprawl, and the *first double-patched bug* is the point at which the copies start costing correctness rather than bytes.

**Drift is the live risk, and both directions of it showed up immediately.**

*A real divergence the copy created.* At `9799e87`, `unfao/managers/unfao.py:222` named the artifact builder as `unfao/historical.py` — a path retired by #153 — while the fresh copy said `contract/historical.py` and was correct. **The clone silently fixed a stale reference in the original and the fix never propagated back.** #211 fixed the original too.

*An inherited inaccuracy that was not a divergence — until fixing it made one.* Both files carried *"same artifact shape faoapi already ingests"*. Identical, so no diff flagged it; wrong for CRAF'd, whose consumer is not faoapi. #211 reworded CRAF'd's copy, which is correct for both files and **puts that line into the raw diff for the first time**. A copy can therefore drift by being corrected, and a rising count is not by itself evidence of anything going wrong.

Both were prose, both were harmless, and together they are how a 16-line diff becomes a 40-line one — in under a day, with no contributor doing anything careless. #211 also extended the line-budget guard (`tests/test_doc_accuracy.py`) to cover **both** managers rather than only `unfao.py`, which had left the second copy of the file epic #148 shrank from 636 lines with no regrowth protection at all.

**What this does not license.** The four env-name literals in `_<partner>_appwrite_config` duplicate names that `appwrite_env.py` already declares as data, in both files. Removing that is not an abstraction and does not wait for the trigger — it is not encoding the partner's identity twice in the same package. Left as a follow-up rather than folded into #211, which is a partner-addition PR.

See also C-24 (schema contract per store), C-77 (the fourth home for partner identity, in the duplicated `name=` argument of the historical upload), D-09 (the deferral, now expired), ADR-014 §4 (a deferral needs a trigger and an owner), #97 (second-store scoping), #211.

---

### C-40: FAO delivery logic fused to pipeline-core via double inheritance + interleaved infrastructure

| Field | Value |
|-------|-------|
| ID | C-40 |
| Tier | 2 |
| Source | `expert-code-review` (2026-06-24) |
| Trigger | **(a) Upstream change:** when pipeline-core changes `PGMDataset` / the data loader / the postprocessor base (mid-migration: their #186/#188/#161), verify the inherited surface this repo depends on still holds. **(b) Standing work item:** the input-side de-inheritance (the sink side landed — see the 2026-07-31 update) — schedule it, don't wait for a trigger. |
| Location | `views_postprocessing/<partner>/managers/<partner>.py` — the `class <PARTNER>PostProcessorManager(PostprocessorManager, ForecastingModelManager)` statement (double inheritance); `_prod_forecasts_datastore`, `_<partner>_datastore`, `_<partner>_appwrite_config` (inline env/AppwriteConfig/DatastoreModule); `_validate` and `_check_coverage`; the DIP sink adapter `_ContractStorePort`. **Since 2026-08-03 all of it exists twice** — `unfao` and `crafd` are the same file with the partner name changed (C-33). Symbols rather than lines, deliberately: an earlier version of this row was invalidated by a comment edit four lines long. |

`UNFAOPostProcessorManager` subclasses **two concrete** pipeline-core base classes (`PostprocessorManager`, `ForecastingModelManager`) and **interleaves infrastructure** (env reading, `AppwriteConfig` construction, `DatastoreModule`, path resolution) with the FAO **business logic** (GAUL enrichment, the 9-column null gate) inside the lifecycle hooks. Consequences: (a) the FAO logic cannot be instantiated or unit-tested without the full framework + Appwrite env + viewser; (b) **pandas cannot leave the delivery path** because the inherited data loader and `PGMDataset` are pandas — gated on pipeline-core's own DataFrame retirement; (c) **SDP exposure** — heavy *inheritance* coupling to a pipeline-core that is itself unstable (mid-migration), so upstream changes break far from their cause (cf. C-27, C-29); (d) it's the repo's only composition-over-inheritance violation. The dependency itself is correct (`unfao.py` genuinely *is* a pipeline-core postprocessor) — the issue is its **blast radius**. Mitigation (does **not** fight the Template-Method framework): keep the subclass as a **thin shell** but extract `enrich` + `validate` + the 9-column contract into a pipeline-core-free core object the manager *calls*, and wrap the Appwrite I/O behind a small delivery-sink adapter (DIP). This makes the FAO logic testable standalone and insulates it from pipeline-core churn.

**Update 2026-07-27 — the pandas gate (consequence b) has LIFTED, and the mitigation shape largely landed via ADR-013:** pipeline-core shipped its frame-native fetch (`get_feature_frame`, tested, previously zero consumers), and this repo became its **first production consumer** (#126 / PR #129): the historical path now fetches a `views_frames.FeatureFrame` and builds the artifact pandas-free (`unfao/historical.py`), reader-parity-proven against a legacy characterization golden. The forecast path is frame-native end-to-end (wire/ + streaming leases, PRs #115–#129). Pandas remains ONLY on the legacy forecast branch (kept until run 0 proves the contract path live; its deletion is the named post-run-0 follow-up) and in the retired-in-place `enrichment.py`/`extraction.py` legacy seams. The double-inheritance shell (consequences a/c/d) still stands — the residual scope of this entry.

**Priority raised by the samples/uncertainty requirement (2026-06-27).** The delivery is moving from point estimates to **predictions-with-uncertainty (S samples per cell)**. This makes the pandas gate (consequence b) materially worse, not just cosmetic:
- **views-frames** stores a distribution as a native contiguous `(N, S)` float32 array (sample axis always explicit; point = S=1). **pandas `PGMDataset`** stores it as **object-dtype list-in-cell** — each of N cells holds a separate length-S numpy array (`_ViewsDataset._convert_to_arrays` / `_check_prediction_samples` in pipeline-core `data/handlers.py`).
- Cost of the object-dtype representation scales ~linearly with S: memory blow-up (this is pipeline-core's own OOM, **#181/#189** — "~18 GB, kills runs" off list-in-cell DataFrames), an encode/decode tax at every parquet/API boundary (faoapi's inverse `_convert_to_arrays`), and a silent `np.resize` pad on mismatched sample counts (feature path).
- At S=1 the penalty is invisible; at S≈1000 it dominates → the uncertainty work is the strongest driver for the frame migration.

**Concrete pipeline-core gate (what "DataFrame retirement" actually requires).** vpp inherits three *concrete* pandas pieces (the abstract `PostprocessorManager` base is fine): the input loader (`ViewsDataLoader.get_data` → parquet→pandas), the container (`PGMDataset`/`_ViewsDataset`, object-dtype cells), and the prediction-store parquet I/O. Closing the gate = pipeline-core **Epic #186 + #207** landing: frame-native input loader (**#161**, gated on the datafactory↔core output contract **#162/#136**), a frame container replacing/re-backing `PGMDataset` (**#159**), frame/arrow store I/O, and retiring the legacy pandas report path (**#211**, the #181 OOM source). It is an epic, not a PR. The half **vpp owns and can do now** (unblocked): the thin-shell de-inheritance above — extract enrich/validate into a pipeline-core-free core the manager *calls*, so the eventual frame swap is a one-seam change. Dependency direction confirmed: pipeline-core does **not** import vpp; vpp **is-a** pipeline-core postprocessor (Template-Method subclass), so it inherits pipeline-core's representation rather than choosing its own.

**Migration backlog (2026-06-28):** the full pandas→views-frames map + sequenced, parity-preserving removal plan is now tracked as epic **#85** ("Push pandas to the seams") with stories #86–#92 and tracking #93. The unilateral arc (S1–S3: generalize `frames.py` to S>1, frame-native extraction siblings, forecast convert-at-the-door) makes vpp's interior carry `(N,S)` behind frozen wires; S6 (#91, outbound arrow wire) is gated on faoapi #45, and S7 (#92, historical inbound) is gated on this entry's pipeline-core gate above.

**Wire contract posted (2026-07-03) — the S6/#45 circular wait is dissolved.** A three-way audit (pipeline-core / producers / consumer+substrate, all on `origin/development` + maintainer-authored issues) established: (i) there are **two wire hops** (producer→store; vpp→faoapi) and the roadmap's arrow work covered only the second; (ii) **no publish path from PFE to the prediction store exists at all** — models#143's "no pipeline-core change required" is **falsified** (PFE's `use_prediction_store` is stored then only logged, `prediction_frame_ensemble.py:141/:799`; `PredictionIOManager._upload_to_prediction_store` raises `NotImplementedError`, `io.py:117`); (iii) full global draws ≈ **9.5 GB/target**, so the wire mandates per-month sharding; (iv) the "platform ADR-046" cited as the format authority **does not exist** (phantom). **ADOPTED 2026-07-15 as ADR-013** *(post-adoption: F1 invisibility confirmed live — six stranded orange_ensemble forecast docs in unfao_bucket, forecast serving has been empty all along; both §11.4 legacy guards merged same day, Hop-B guard must reach production before vpp's first contract upload — **views-faoapi C-161**)* after five reviewed iterations (two seat reviews, reconciliation, owner-ratified F1) — maintainer sign-off on views-models#149. The v1 proposal history: Hop A = Track A zip archive per (run,target,month) + manifest-last commit marker (new **pipeline-core#269**); Hop B = per-month `views_frames.io.arrow` (#91/faoapi#100); interior = per-target 2-D `PredictionFrame`; the 9 GAUL columns move to a **gid-keyed sidecar**; the **#149 no-collapse boundary is named: vpp `delivery/draws.py`** (a new invariant, sibling of coverage/identity — follow-on vpp work with the durable vpp ADR after explicit sign-off); target vocabulary **decided: `lr_ged_sb/ns/os`**, producers rename at publish (models#146).

**Update 2026-07-31 (review-rr — the prescribed DIP mitigation has half landed, uncredited).** This entry's mitigation was: "*keep the subclass as a thin shell but extract `enrich` + `validate` + the 9-column contract into a pipeline-core-free core object the manager calls, and wrap the Appwrite I/O behind a small delivery-sink adapter (DIP).*" The **sink half exists**: `_ContractStorePort` (`unfao.py:37-78`) wraps `DatastoreModule` behind a four-method port (`latest_file_id` / `file_metadata` / `download` / `upload`), and the contract delivery path drives the store through it. The **invariant half also largely exists** as pipeline-core-free modules the manager calls: `delivery/coverage.py`, `identity.py`, `draws.py`, `parity.py`, `provenance.py`, `observed_range.py` (the package docstring pins them representation-free), plus `unfao/historical.py` and `unfao/wire/`. **Residual scope of this entry is now the input side and the shell itself:** the double inheritance at `:80` (consequences a/c/d), the inherited `ViewsDataLoader`/`PGMDataset` on the legacy branch, and the fact that the FAO logic still cannot be instantiated without the framework. Tier held at 2 — the blast radius argument is unchanged for what remains. This is the root of **Cluster G**.

**Update 2026-07-31 (`repo-assimilation`, clone-readiness pass — the coupling is CONTAINED, and this file is the only clone blocker).** Two measurements that change how this entry should be read:

1. **`views_pipeline_core` is imported by exactly ONE module in the repository — this one** (`managers/unfao.py:1-20`, 8 import sites). Every other module is pipeline-core-free: `delivery/*`, `unfao/wire/*`, `frames.py`, `historical.py`, `gaul_schema.py`, `track_a_source.py`. The blast radius this entry describes is real but **one file wide**, which is materially better than the narrative above conveys and makes the thin-shell extraction a bounded job rather than an open-ended one.
2. **The file is 636 lines — 25% of the package's 2,528** — and holds: the pipeline-core adapter, an inner `_ContractStorePort` class, two read strategies, two save strategies, provenance formatting, coverage orchestration, and env assembly. **Every SRP/CCP violation in the repository is in this one file**, and it is the only file a clone (views-crafdapi, views-productionapi) cannot reuse as-is.

**Consequence for the clone work:** the reusable core already exists and is clean — `delivery/` is partner-agnostic by its own declaration and `unfao/wire/` takes its consumer name as a parameter. What blocks reuse is this manager, plus the packaging problem registered separately as **C-69**. Note also that ADR-012 still calls this class **"the *thin* `UNFAOPostProcessorManager`"** (**C-67**).

**Update 2026-08-01 (epic #148 closeout) — what the epic did and did NOT do to this entry.**

*Did:* the surrounding surface shrank sharply. The manager is **406 lines** (from 636); it imports neither pandas nor `PGMDataset`; the partner-neutral machinery moved out to `contract/` (#153); and **`views_pipeline_core` is still imported by exactly one module — this one — now pinned mechanically** by `tests/test_doc_accuracy.py` and `tests/test_clone_readiness.py`. That property is what keeps this entry's blast radius one file wide, and it is no longer a claim anyone has to re-check by hand.

**⚠ Superseded 2026-08-03 (PR #211): "exactly one module" is now exactly TWO.** `views_postprocessing/crafd/managers/crafd.py` is the second, and it imports the same `views_pipeline_core.modules.{appwrite,datastore}` surface at the same lines. The claim above was true when written and is left visible rather than edited away, per ADR-014 §5.

**What actually changed, and what did not.** The blast radius is no longer *one file wide* — it is **one file, twice**, which is a different and slightly worse property: an upstream change now has two identical landing sites and no mechanism guarantees they are patched together (C-33). What did **not** change is the more important half: the count is still **bounded and pinned**. `test_views_pipeline_core_is_confined_to_the_partner_managers` (renamed in #211 — it had asserted *two* under a name that said *one*) was widened to an explicit allowlist, not deleted, so a *third* importer still fails CI. Every other module in the repository remains pipeline-core-free, including the whole of `contract/` and `delivery/`, and `tests/test_clone_readiness.py` still proves the machinery imports in a subprocess without it.

**Recorded as ADR-015 (2026-08-04).** The reasoning for keeping this import — and the two-part condition under which it is revisited — now lives in `docs/ADRs/015_the_pipeline_core_appwrite_import.md` rather than only in issue #146 and the platform's deliberation folder. That was the condition attached when the deferral was ratified, and it had not been met. The ADR also records that the **supply** half of the trigger has *partially* moved: pipeline-core 3.0.0 relocated provisioning and transport out of the Appwrite module (3,064 → 2,841 lines), but exports no client surface, so there is still nothing to unwind to.

**On þing-02 S24(5).** `docs/CLONING.md` cited that verdict as forbidding these imports outright. Reading it directly (`þingit/02_credential_identity_key_ownership/sáttmál.md:240-242` — precondition (5) itself; the section opens at `:232` under the heading *"§5 — The clone (`un-crafdapi`)"* — and `orð_dómr.md:418-441`), it binds *"the clone"* — `un-crafdapi` and `views-productionapi`, repositories **git-cloned from views-faoapi** — and does not reach an in-repo partner package of the producer. CLONING.md over-claimed; PR #211 corrects the citation rather than weakening the rule. This entry's own scope is unaffected: the coupling is a design concern here regardless of what the verdict binds, and issue **#146**'s deferred unwind now covers two files instead of one.

Tier held at 2. The residual scope — the double inheritance and the framework-bound instantiation — is unchanged, and is still gated on views-pipeline-core 3.0.0 (C-44/C-62).

*Did not:* the double inheritance (the `class UNFAOPostProcessorManager(...)` statement — this row cited `unfao.py:80` when written, and that number has moved twice since) stands, and so do consequences (a) — the FAO logic still cannot be instantiated without the framework — and (c)/(d). **This entry remains open on exactly that scope.** Its remaining fix is gated on views-pipeline-core's 3.0.0 (C-44/C-62), which is a release signal rather than engineering work.

See also C-07/C-27/C-29 (pipeline-core coupling symptoms), C-39 (the dead-mapper cleanup that precedes any unfao restructuring), **#45** (the delivery-side draw carrier — ship `(N, S)` uncollapsed as a native frame, the producer half of this same problem), and **epic #85** (the migration backlog).

---

### C-72: The pyarrow pin holds this repo inside a high-severity CVE, and the fix changes the wire bytes

| Field | Value |
|-------|-------|
| ID | C-72 |
| Tier | 3 — **not currently exploitable here**: the CVE is a *read-path* use-after-free and this repo only **writes** arrow in production (the three `vf_arrow.load` calls are all in tests). It is Tier 3 rather than 4 because the bytes we write are read by views-faoapi under the same platform-wide pin, so the platform's exposure is real even though this repo's is not, and because the remedy collides with a ratified contract. |
| Source | `manual` (2026-08-01) — GitHub surfaced 32 Dependabot alerts on the push that made `main` current; reviewed alert by alert |
| Trigger | When lifting the `pyarrow < 17` ceiling — pipeline-core **#280** (the viewser → views-storage chain) is the platform half — **regenerate the ADR-013 §10 golden fixture in the same change and notify the faoapi seat**, because the upgrade is expected to change the delivered bytes. Also fires if this repo ever gains a production arrow **read**. |
| Location | `pyproject.toml:15` (`pyarrow = ">=16.1.0,<17.0.0"`); `poetry.lock`; the affected operation would be `views_frames.io.arrow.load`, called only at `tests/test_wire_shard.py:90`, `tests/test_wire_fixture.py:73`, `tests/test_wire_header.py:39` |

**GHSA — "Apache Arrow: potential use-after-free when reading IPC file with pre-buffering."** Vulnerable range `>= 15.0.0, < 23.0.1`; patched in **23.0.1**. This repo's declared pin is `>=16.1.0,<17.0.0` — **entirely inside the vulnerable range, with a ceiling that excludes the fix.** It is the only one of the 32 alerts against a dependency this repo declares itself (`pyproject.toml`); the other 31 are `poetry.lock` resolution — see the disposition note below.

**Why it is not exploitable here, stated precisely rather than reassuringly.** The defect is on the *read* path. Production writes arrow (`contract/wire/shard.py` → `views_frames.io.arrow`) and never reads it back; the only `vf_arrow.load` calls in the repository are the three byte-parity tests above, operating on committed fixtures we generated. So there is no path from partner or producer input to the vulnerable code **in this process**.

**Where the exposure actually sits: views-faoapi.** It reads these shards, under the same platform-wide `pyarrow < 17` ceiling. Our output is its input. This entry does not claim to size that repo's risk — it records that the platform's pyarrow pin is a shared exposure and that the consumer is the reading half.

**The collision worth understanding — the fix and the contract point in opposite directions.** The five byte-parity failures this repo has treated as "known local toolchain noise" all session are precisely this: the local environment runs **pyarrow 23.0.1 — the patched version** — while CI runs the pinned 16.1.x, and the two produce **different bytes** for the same input. So upgrading to the patched pyarrow is not a dependency bump; it **changes the §10 golden fixture**, which ADR-013 declares normative and which views-faoapi verifies against. Security remediation here is a **contract event**, not maintenance, and must be sequenced with the consumer.

**⚠ TWO CORRECTIONS to this entry, made the same day it was written (2026-08-01), on evidence gathered while filing the cross-repo issues.**

**(a) views-faoapi is NOT exposed, and the platform ceiling is not uniform.** This entry implied the consumer shared our pin. It does not: faoapi pins **`pyarrow==23.0.1`** — the patched version — in its `pyproject.toml:31`, and it is the repo that actually reads the wire (`forecast/ingestion/wire_reader.py` → `arrow.load`). So nobody on the platform is currently exposed through this path, and the `<17` ceiling views-pipeline-core#280 exists to lift is binding on the **producers** only. One consumer has already moved past it, in production.

**(b) The re-vendor obligation is stronger than "our fixture changes".** ADR-013 §10 is explicit: *"All three implementing repos' test suites consume the same bytes … The other two repos **vendor a copy** and carry a **pinned root-hash equality test** … A change to the fixture is a change to the contract."* Verified — faoapi's copy is at `tests/forecast/golden/wire_contract/SHA256SUMS`, pinned by `tests/forecast/test_wire_golden_fixture.py`. So the upgrade is a **coordinated three-repo re-vendor**, and it carries an undecided question: whether it bumps `contract_version` (the payload schema does not change, only the encoder's bytes — §10 says a fixture change *is* a contract change).

**Filed, so the relocation is complete rather than assumed** (the C-08 lesson): **views-postprocessing#174** (the coordinating issue), **views-faoapi#348** (heads-up + two questions only their seat can answer), and a comment on **views-pipeline-core#280** adding the security dimension and the non-uniform-ceiling finding.

Cross-refs: **C-62** (the transitive dependency drag; the other 31 alerts), **C-46** (the datafactory version-state coupling), ADR-013 §10 (the byte-pinned fixture), views-pipeline-core **#280** (the platform pyarrow ceiling), views-faoapi **#348** (the reading half), **#174**.

---

### C-75: `GaulLookupEnricher` has no production caller, and now implements a second copy of the delivery path's keyed gather

| Field | Value |
|-------|-------|
| ID | C-75 |
| Tier | 3 — no correctness impact today: the class is off the delivery path, so a defect in it cannot reach the UN FAO. The cost is that **the verification path and the delivery path now implement the same algorithm twice**, and the tests that check the artifact run through the copy that does *not* ship. A fix applied to one and not the other makes the verification stop verifying what ships — quietly, because both would still pass their own tests. |
| Source | `code-review max` (2026-08-02) — PR #210, five parallel reviewers; two reached this independently |
| Trigger | When a bug is fixed in `contract/historical.py`'s gather (the one that ships), check whether `contract/enrichment.py`'s copy needs the same fix — nothing links them. Also fires at **S5 (#90)**: once the builder is pyarrow-native, the enricher's pandas interface is the last one in the package, and the question "does this class survive?" has to be answered rather than deferred again. |
| Owner | Whoever takes **#90** — the keep-or-retire decision is theirs to make and record, not to defer a third time. Added 2026-08-03: the first draft of this entry named two triggers and no owner, while citing ADR-014 §4 in its own body. This register had already learned that twice — *"a deferral needs an owner and a trigger, not just a reason"* (Cluster L) and *"a decision awaiting an owner, not a task awaiting effort"* (epic #181 closeout). |
| Location | `views_postprocessing/contract/enrichment.py` (the whole class; `_gather` specifically); the shipping twin is `views_postprocessing/contract/historical.py:54-68` |

**Verified, not inferred (2026-08-02):** `grep -rn "GaulLookupEnricher\|enrich_dataframe_with_pg_info"` across the package finds **zero** production callers — the two hits are docstring mentions in `gaul_lookup.py`. The manager calls `gaul_lookup.load()` directly and has zero `enrich` references. **C-66**'s resolution already said this plainly: *"the pandas enricher leaves the delivery path entirely."*

**What PR #210 did, and why that raises the question.** S4 (#89) rewrote this class's lookup side from a pandas merge to a numpy/pyarrow keyed gather: a measured dtype analysis, an empty-lookup guard, a mutation-proven bug fix, a corrected CIC, and five reviewers' attention. All of it spent on a method with no reachable caller outside its own test suite. The engineering is sound; what is missing is anyone having **decided** that the class should exist.

**The duplication is the concrete consequence.** `_gather`'s `argsort → searchsorted → clip → equality-mask` is the same shape as `historical.py:54-68`. The policies differ deliberately — `historical` **raises** on an absent gid (*"geography must never silently vanish"*), the enricher returns nulls for the downstream gate to catch — so extracting a shared helper would mean parameterising the failure policy, which is the guessed abstraction **WET before DRY** exists to prevent. Two copies that are understood is the right call *today*. The trigger above is what stops "today" lasting indefinitely, per **ADR-014 §4**.

**The precedent is C-45**, `unfao/frames.py`: an unused adapter carried on no live path, resolved by deleting it. This is the same shape with a different module, and the same question — keep it as the declared verification/reference implementation, or retire it and let the fidelity suite test `historical.py` directly.

**DECISION 2026-08-04 (#90), which this entry's Owner field required of whoever took it: RETIRE.**

The conditions are no longer arguable. The class has **zero production callers** — only three test files import it. Its last stated justification was "the build/verification path", and #90 rewrote that path arrow-native without touching it, so the justification is spent. It holds the package's **last pandas reference** (a `TYPE_CHECKING` import), which is the one thing standing between epic #85 and an honest close. And its `_gather` duplicates `contract/historical.py`'s shipping gather, which is independently covered by four test files.

**C-45 is the precedent and it was resolved by deleting.** Same shape, different module.

**Not executed in #90, deliberately.** The retirement touches ten files — the module, its 39 tests, references in two other test files, its CIC, ADR-012, `gaul_lookup.py`'s docstring, the machinery list in `test_clone_readiness.py`, and the pandas-importer assertion in `test_doc_accuracy.py`. Folding that into a builder rewrite would mix a behaviour-preserving change with a large deletion, which is the thing epic #148's S5 explicitly refused to do. It is the next change, not a later one.

**Epic #85 and tracking #93 stay open until it lands**, because their claim — pandas pushed to the seams — only becomes true when this module is gone.

**Deliberately NOT registered from the same review** (defects in unmerged code, all fixed in #210 before merge rather than tracked): a NaN gid crashing the warning path, the unvalidated int64 coercion at both ends, the AST guard's `else`-branch blind spot, ADR-012's stale pandas-merge claim, and three CIC claims retired elsewhere by #200. The register tracks standing risk; a defect fixed before it ships is not one. They are recorded in the PR.

Cross-refs: **C-45** (RESOLVED — the same shape, resolved by deletion), **C-66** (RESOLVED — established the enricher left the delivery path), **C-40** (which calls `enrichment.py` and `extraction.py` together *"the retired-in-place `enrichment.py`/`extraction.py` legacy seams"*), **#89** / **#90** / epic **#85**, ADR-014 §4.

---

### C-80: The doc-accuracy scan exempts ADRs and CICs — the two artifact classes that define the contracts

| Field | Value |
|-------|-------|
| ID | C-80 |
| Tier | 2 — structural, with a demonstrated failure. A CIC is what a contributor reads before changing a class; an ADR is what a consumer reads before building against the wire. Both were free to describe deleted code indefinitely, and did. |
| Source | `code-review max` (2026-08-03) — development→main sync audit |
| Trigger | When the next module is moved or deleted, check whether any ADR or CIC names it. The deleted-symbol regex will not tell you. #153 moved seven modules out of `unfao/` and the ADRs still cite the old paths. |
| Owner | Whoever next extends `tests/test_doc_accuracy.py`. It is a scope change plus a decision about how to exempt genuine history. |
| Location | `tests/test_doc_accuracy.py` — `_living_docs()` and `_link_checked_docs()` |

`_living_docs()` returns `README.md`, `docs/architecture/*.md`, and package `README.md`s. **`docs/ADRs/` and `docs/CICs/` are outside it**, deliberately — an ADR legitimately records superseded designs, and a scan that fires on history gets deleted (§3). The exemption is right in principle and far too wide in practice.

**What it cost, measured in this sync.** `docs/CICs/UNFAOPostProcessorManager.md` named `GaulLookupEnricher` as the manager's enrichment collaborator in **six** places, one of them a specific call — while the manager contains zero references and `tests/test_gaul_lookup_access.py` actively asserts its absence. The sibling CIC said the opposite in plain words. Two contract documents contradicted each other about the same call, and nothing could see it. Five further claims in the same file described a `dotenv` load that does not happen, an env-validation "known gap" that C-19 closed, an upload count wrong in three ways, and two "incorrect usage" examples for code deleted in #149/#152. ADR-013 still cites `unfao/wire/`, `unfao/product.py` and `unfao/launch_config.py`, all moved in #153.

**The exemption is not understood by the people writing under it.** `docs/CICs/UNFAOPostProcessorManager.md` carries a `legacy-ok` marker — the line-scoped opt-out from a scan that never reaches that file. Its author believed they were suppressing a guard that was not looking.

**A second, narrower hole in the same file.** `test_internal_doc_links_resolve` follows only markdown `](...)` links. Every path written as prose in backticks — which is how this repository writes paths almost everywhere — is unchecked. That is why the stale `unfao/...` references survived a dedicated sweep (S11) and were still being found two epics later.

*Not proposed as a fix here:* pointing the existing regex at ADRs would fire on every historical passage and be reverted within a day. The shape that works is what §3 already recommends — check the **claim**, not the vocabulary: for CICs, that every collaborator named is actually referenced by the class (the negative form already exists at `test_gaul_lookup_access.py:156`); for backticked paths, that a path-shaped token which looks like a repo path resolves, with an opt-out for history.

Cross-refs: **C-74** (a guard narrower than its declared surface), **C-78** (a guard whose declared scope missed a package), **C-67** (ADR-012 drift, which *is* covered and was caught), ADR-014 §1–§3, #211.

---

### C-81: What actually gates `main` is weaker than it looks — CI verifies 17 fewer tests than local, and nothing requires it to pass

| Field | Value |
|-------|-------|
| ID | C-81 |
| Tier | 2 — the guards this arc built to catch cross-repo drift do not run where drift happens, and the branch they protect has no required check. Both halves are structural and both have fired-in-practice evidence. |
| Source | `code-review max` (2026-08-03) — development→main sync audit |
| Trigger | **Coverage half:** when the Appwrite Seam Contract registry next moves — it moved twice on 2026-08-03 alone — nothing in CI will notice; only a maintainer running the suite locally will. **Enforcement half:** the first time someone merges a red PR to `main`. |
| Owner | Simon — both halves need operator action. The coverage half needs a token for two private repositories; the enforcement half is a GitHub console/ruleset change. Neither is engineering work. |
| Location | `.github/workflows/run_pytest.yml`; the `protect_main` ruleset; `tests/conftest.py::sibling_repo` |

**Coverage.** Measured in an isolated clone, not estimated — **402 collected in every run**, so the whole delta is skips:

| environment | result |
|---|---|
| local, all siblings present | 362 passed / 40 xfailed / **0 skipped** |
| CI as it was | 347 passed / **17 skipped** / 38 xfailed |
| CI with the views-crafdapi checkout added | 348 passed / **16 skipped** / 38 xfailed |

*(**This table was wrong twice, and the second time it refuted itself.** Draft one said 361/40 and "same 401" — measured before the same change added a test. Draft two fixed the collected figure to 402 and did not re-derive the rows, so both rows summed to 401 beside an assertion that 402 was collected. The cause of the second error is worth recording: the measurement was taken on a `git clone` of the branch, and a clone carries **committed** state — the new tests were still uncommitted in the working tree. Measuring a claim about your own change requires applying your own change. This is the entry about miscounted tests.)* `sibling_repo` resolves `$VIEWS_<NAME>` else `../<name>`; in a one-repo checkout neither exists and the tests skip. Skipping is correct behaviour — a missing sibling *is* normal — but the consequence is that **CI verifies strictly less than a developer's laptop, precisely on the assertions that cross a repository boundary.**

Nine of the seventeen are **new in this arc**, including both registry-drift detectors (pinned edition, commit-reachable-from-`main`) for both partners. Those detectors have a demonstrated drift rate: they fired **twice on 2026-08-03**, hours apart. A detector for a fault that recurs twice in a day, running only on one machine, is most of the way to not existing.

Where each sibling stands, after trying them:
- **views-crafdapi** — public, its check reads source text. **Now checked out in CI**, recovering **one** test: the cross-seam consumer-document-name pin for CRAF'd.
- **views-datafactory** — public, but its eight tests need the producer's raw GAUL parquets, which are **not in its git repository**. Checking it out converts an honest skip into a `FileNotFoundError`; tried and reverted.
- **views-appwrite**, **views-faoapi** — **private**. The most valuable checks live here. Closing this needs a token in CI.

**Enforcement.** `main` is **not branch-protected**: `gh api .../branches/main/protection` returns `404 Branch not protected`, and `gh api .../rules/branches/main` returns `[]`. The `protect_main` ruleset exists and is `active`, but its `ref_name` include-list is **empty**, so it matches nothing — and it declares no `required_status_checks` rule in any case. **A red `Run Pytest` would not block a merge to `main`.** This repository's own `tests/test_falsification_campaign_4_1.py` carries the question as an unverifiable xfail probe; it is verifiable through the API, and the answer is no.

The two compound: a suite that checks less than you think, and no requirement that even that much passes. Neither is caused by this sync — both are pre-existing — but this sync is the first time `main` receives an epic whose value is largely the guards themselves.

Cross-refs: **C-46** and **C-57** (both RESOLVED; this is the residual each recorded as *"a CI-cost and cross-repo-coupling decision"* and *"worth deciding once for both"* — it now has a live home and a concrete answer per sibling), **C-80** (the other verification gap found in the same audit), #188.

---

### C-83: A queryset that fails to import is reported as a queryset that declares the wrong format

| Field | Value |
|-------|-------|
| ID | C-83 |
| Tier | 2 — no wrong data ships; the delivery refuses, which is correct. What is wrong is the reason it gives, and it gives it on the live FAO path, at the moment someone is trying to fix a failed run. It sends them to edit a file that is already right. |
| Source | `code-review max` (2026-08-03) — the views-pipeline-core 3.0.0 bump review |
| Trigger | The next time the FAO delivery refuses with *"the queryset declares data_format='dataframe'"*, check whether `config_queryset.py` actually imports before editing it. Most likely on a machine missing views-datafactory, or after any change to that file's own imports. |
| Owner | Whoever next touches `_read_historical_frame`'s precondition. The fix is ours — distinguishing the two cases takes one branch. |
| Location | `views_postprocessing/unfao/managers/unfao.py` and the same line in `crafd` — `declared_data_format(self._model_path.get_queryset())` feeding `launch_config.assert_frame_native_historical` |

Three correct-in-isolation behaviours compose into a lie:

1. pipeline-core's `ModelPathManager.get_queryset()` catches **any** exception from importing `config_queryset.py`, logs it, and returns `None`.
2. `declared_data_format(None)` returns `'dataframe'` — the documented default for a non-dict.
3. `assert_frame_native_historical('dataframe')` raises: *"the queryset declares `data_format='dataframe'` … **Set `data_format: 'feature_frame'` in the postprocessor's config_queryset**."*

So a queryset that **failed to import** is indistinguishable from one that **declared the wrong format**, and the operator is told to fix a file that is already correct. Reproduced: in an environment without views-datafactory the real `un_fao` queryset reports `dataframe` while declaring `feature_frame`; in a complete environment the same file reports `feature_frame`.

This is ADR-003's rule broken by composition rather than by anyone inferring anything: each layer declares faithfully, and the *absence* of an answer is silently given the shape of an answer. Cluster J's disease — *cannot distinguish "no" from "I could not tell"* — reached through a new door, because #126 made this repo depend on `declared_data_format` in the first place.

**The fix is ours and it is small:** call `get_queryset()` once, and if it returns `None`, refuse with *that* — the queryset could not be imported — rather than passing `None` into a function whose contract is to default. Upstream could also raise instead of returning `None`, but we should not wait for that; we are the ones holding the ambiguous value.

Cross-refs: **C-44** (the bump whose review found this), **C-40** (the inherited surface it arrives through), Cluster J (the *no* vs *could not tell* family), ADR-003, #126, #149.

---

### C-82: Governance-artifact prose carries numbers and statuses that nothing checks

| Field | Value |
|-------|-------|
| ID | C-82 |
| Tier | 3 — no delivery is affected, but these are the artifacts people plan from. One instance materially under-scopes a planned dependency bump. |
| Source | `code-review max` (2026-08-03) — development→main sync audit |
| Trigger | When the pipeline-core 3.0.0 bump (C-44) is scoped from Cluster M's summary rather than from C-72's body, or when anyone counts on a test-count or issue-state stated in the register. |
| Owner | Whoever runs the next `review-rr` pass; this is curation, not engineering. |
| Location | `reports/technical_risk_register.md` (Clusters I, J, M; D-09, D-11); `docs/CICs/*.md` front matter |

`tests/test_register_integrity.py` checks structure — header counts, section placement, reference resolution — and **no prose at all**. Roughly twenty-five statements drift beneath it.

**The one that would change a decision.** Cluster M declares resolution *"Full for … C-72 …"* at the pipeline-core 3.0.0 bump, while C-72's own body says its fix is gated on pipeline-core **#280** (open), **changes delivered wire bytes**, and requires a coordinated three-repo re-vendor of the ADR-013 §10 golden fixture. Someone planning that bump from the cluster summary under-scopes it badly. Cluster M's heading also says six entries where its body says five.

**Self-contradiction elsewhere.** Cluster I still argues that *"there is no equivalent for the register — a small `tests/test_register_integrity.py` … would make this class self-detecting"*; that file exists, has ten green tests, and is cited elsewhere in the same document. Cluster J names issue **#15** as its fix strategy; #15 is closed and superseded by `docs/operations/correction_procedure.md`. D-11 says a branch *"currently has no scheduled deletion PR"* two paragraphs after recording that it was deleted. D-09's `Status` row reads *"Open … after delivery"* directly above prose recording the deferral expired on 2026-07-31.

**Numbers.** The `test_gaul_lookup_fidelity.py` count appears as **26** twice in the register and as **18** twice more including `test_register_integrity.py`'s own docstring; the actual is **24**, and 26 was never true — it was written when the file held 24. Also *"40 ADR-013 guard tests"* (39) and *"`test_enrichment.py`, 16"* (39).

**CIC front matter.** `GaulLookupEnricher.md` says *Last reviewed 2026-06-18* and `UNFAOPostProcessorManager.md` *2026-06-02*, while both bodies carry 2026-08 content. A reader calibrating trust from the header calibrates it wrong in the safe direction, which is lucky rather than designed.

*The general fix is C-80's, not a re-count:* prose that states a number is a claim, and a claim needs a check. Where a number cannot be checked, the honest move is to state the command that produces it — which is what C-33 was forced into after its measurement was wrong five times.

Cross-refs: **C-80** (the same disease in ADRs and CICs, and the mechanism that would catch both), **C-72** and **C-44** (the bump this mis-scopes), **C-33** (the worked example of publishing the command instead of the result), ADR-014 §1.

---

### C-79: `_ContractStorePort.upload`'s result check is called "the whole mechanism" and has no test, and it fails open

| Field | Value |
|-------|-------|
| ID | C-79 |
| Tier | 3 — the check works today and is correct for what the store actually returns, so nothing is shipping wrong. What is missing is any assertion that it keeps working, plus a polarity that would swallow an unrecognised result rather than refuse it. |
| Source | `code-review max` (2026-08-03) — PR #211 fourth pass, while verifying the corrected comment beside it |
| Trigger | When views-pipeline-core changes what `DatastoreModule.upload_data` returns — a different result type, a renamed field, or a raise where it used to report — check this port still refuses a partial upload. The 3.0.0 bump (C-44) is the next occasion. |
| Owner | Whoever takes the pipeline-core 3.0.0 bump; it is the same reading of the same return contract. |
| Location | `_ContractStorePort.upload` in `views_postprocessing/unfao/managers/unfao.py` and `views_postprocessing/crafd/managers/crafd.py` (byte-identical in both) |

The port exists because the store **reports** a metadata failure without raising: after the file is uploaded it logs, then returns `OperationResult(success=False, code="PARTIAL_SUCCESS")`. A caller that discards the result ships a file with no metadata document — invisible to the consumer, which is what happened to run-0's historical artifact on 2026-07-27. This check is what converts that into a refusal.

**Two things are wrong with how it is held.**

*It is untested.* `grep -rn _ContractStorePort tests/` returns exactly one hit, in a docstring in `tests/test_selection_guard.py` noting that the port is **not** asserted. So the code the comment beside it calls *"the whole mechanism"* is carried by no check at all — ADR-014 §1, in the file that this change edited to say so.

*It fails open.* The refusal is `if success is False`, and `success` is resolved by `getattr(result, "success", None)` with a `to_dict()` fallback. A result object that is neither shape yields `None`, which is not `False`, so the upload is accepted. That is the wrong polarity for a repository whose ADR-003 forbids inferring what should be declared: an unrecognised result is exactly the case where refusing is cheap and guessing is not. The `to_dict()` branch is also dead on the real path — `OperationResult` has a `success` attribute — so it is untested code guarding an untested case.

Neither is urgent, because `OperationResult.success` is typed `bool` and is never `None` today. Both become live the moment the return contract moves, which is precisely when nobody will be looking at this file.

Cross-refs: **C-40** (the pipeline-core surface this port wraps), **C-44** (the 3.0.0 bump that is the named trigger), **C-77** (the other unguarded thing on the same delivery leg), ADR-014 §1, #211, #146.

---

## Disagreements

### D-12: Post-Run-0 infrastructure & naming intents — repo rename, internal-store transport, compute co-location

| Field | Value |
|-------|-------|
| ID | D-12 |
| Source | Maintainer direction during the ADR-013 read-through (2026-07-19); assessment in-session |
| Location | Repo-wide (rename); ADR-013 §3/§8 (store transport, co-location); mirrored as dated deferred intents in ADR-013 §8 |

Three maintainer-raised intents, assessed and **deliberately deferred** — all sequenced strictly after (1) Run 0 proves the wire as adopted and (2) a §3.5 retention owner exists (infrastructure ownership must exist before infrastructure multiplies):

1. **Rename this repo** to a delivery-screaming name (e.g. `views-delivery`). The repo is already purely delivery code (reconciliation retired to `views_frames_reconcile`, #62 closed 2026-06-26), so the name is the only mismatch with the screaming-architecture rubric. GitHub redirects soften the repo rename; the `views_postprocessing` *package* rename (cross-repo imports, views-models launchers) is the real churn and may trail.
2. **Move `production_forecasts` off Appwrite** to self-managed storage (e.g. Hetzner object storage) — no external consumer reads the internal store. Contract-tolerant: §3 payload + manifest-last semantics are transport-agnostic; only the store-document addressing needs a bounded amendment.
3. **Co-locate delivery compute with the internal store** to kill the ~29 GB/run upload-download round-trip — while **keeping the logical hop** (complete-or-invisible commit marker, hash verification, schedule independence, multi-partner fan-out). Fusing producer and delivery into one machine is **explicitly rejected** — it would rebuild the coupling ADR-013 dissolved.

**Re-open trigger:** Run 0 verified AND retention owner named — then sequence 2→3 (or 2 alone) as an infrastructure epic, and 1 whenever wire churn is calm. See also C-40 (the migration this rides on), ADR-013 §8.

**Status 2026-08-03 (both halves re-checked): #131 is CLOSED (2026-07-31), so the verification half of this trigger HAS fired.** The text below was written the day it closed and was already stale; it is corrected rather than deleted because the deferral it holds shut is a live decision. **Run 0 delivered** on 2026-07-27 (first FAO global-land forecast, frame-native, no OOM) and its integrity verification is closed — and #131 also surfaced a liveness dialect gap on the `unfao_delivery` forecast surface. **The retention owner is still unnamed** (ADR-013 §3.5 records the duty as OPEN), and that is now the *only* thing holding this deferral shut. Both halves must hold before it re-opens; one of the two now does. **Naming a retention owner re-opens D-12** — that is an operator decision, not engineering work. Note that intent 2 (move `production_forecasts` off Appwrite) and the unnamed retention owner compound: run-0 added ~110 objects in a single run to a store with no retention policy.

---

### D-11: Pandas→frames seam — concrete siblings + delete vs a polymorphic abstraction

| Field | Value |
|-------|-------|
| ID | D-11 |
| Source | `expert-code-review` (2026-06-28) — review of pandas-migration epic #85 |
| Location | epic #85 / stories #86 (`unfao/frames.py`), #87 (`unfao/extraction.py` + new frame module), #88/#91 (`unfao/managers/unfao.py` source/sink seams) |

The pandas→views-frames migration (epic #85) deliberately swaps each seam by adding a **concrete** frame-native sibling next to the pandas one and later **deleting** the pandas path — rather than introducing a polymorphic abstraction (an `Extractor` Protocol / a representation port) that both implementations satisfy.

- **Position A — concrete siblings + delete (the plan's choice; Martin/Beck-pragmatic, WET-before-DRY).** pandas and frames do **not** coexist at runtime — it is a migration, not a permanent dual representation — so a polymorphic interface would be speculative (YAGNI/ISP: don't force an interface nobody dispatches on). The seam stays readable, each representation is one-concept-per-file, and retirement is a clean file-delete. The invariants already depend on **primitives** (the real abstraction, DIP-satisfied at that boundary), so no port is needed above them.
- **Position B — abstraction/port (Hickey/strict-OCP).** Depending on a representation port would make the swap "extend, not modify," and would let the two paths coexist cleanly during cutover.

**Decision: A**, consistent with the maintainer's WET-before-DRY rule and the "migration not coexistence" reality. **Re-open trigger (the one acute case):** S6 (#91) introduces a temporary **dual-write** (legacy parquet + arrow sample-frame) for parity during the faoapi cutover — *if that coexistence proves long-lived* (rather than a brief cutover window), a small abstraction may then earn its place; revisit only then. Until then, concrete-and-delete stands.

**RE-INSTANTIATED 2026-07-31 (`expert-code-review`) — same tension, new subject; merged here rather than registered as its own disagreement entry.** The review surfaced the identical disagreement one level down, about the **keyed gather** rather than the representation seam. "Given gids, fetch their lookup rows" now exists **three times, all simultaneously live**: a pandas left-merge (`unfao/enrichment.py:117`), an argsort/searchsorted gather (`unfao/historical.py:57-68`), and an isin/filter/sort (`unfao/wire/sidecar.py:47-57`).

- **Position A (GoF, Hickey) — unify now.** Three implementations of one join is a correctness surface, not a migration artifact. They differ in failure semantics: two raise in place naming the absent gids; the pandas one yields NaN and defers to a downstream gate. That divergence is invisible at the call sites.
- **Position B (Feathers, Beck) — defer to #89.** The differing failure semantics are *deliberate*, each implementation is separately tested, and unification means changing three call sites while the legacy branch is still live. The duplication is scheduled to die with that branch.

**✅ CONDITION MET 2026-08-01 (epic #148).** The legacy forecast branch **was** deleted (#149) — before #89 landed, so the re-open trigger below never fired. Position A is vindicated by events rather than by argument: concrete siblings were built, the migration completed, and the second implementation was deleted rather than abstracted over. A Protocol introduced at decision time would have outlived the thing it existed to unify. Recorded in `tests/test_input_integrity_design_contract.py` ② so the next seam decision has the precedent.

**Adjudication: B — but conditionally, and the condition is now named.** B is only correct *if the legacy forecast branch is actually deleted*. It currently has no scheduled deletion PR — only a "named post-run-0 follow-up" (C-40). If it lingers, three-way duplication becomes the permanent shape and Position A wins retroactively. **Re-open trigger: if the legacy forecast branch still exists when #89 (numpy/pyarrow keyed gather) lands, unify all three consumers onto one fail-loud gather primitive as part of that story rather than deferring again.** Cross-refs C-59 (the duplicate-key hazard that lands differently in each of the three), C-40, #89.

**SETTLED 2026-07-31 (review-rr — the original re-open trigger resolved without firing).** The sole re-open condition was a long-lived S6/#91 dual-write. **#91 is CLOSED**, and the contract path shipped frame-native end-to-end (PRs #115–#129, wire delivered in run-0) without a durable dual-representation window. Position A is vindicated by events: concrete siblings + delete is what actually happened, the pandas path is confined to the legacy branch pending its named post-run-0 deletion, and no polymorphic representation port was ever needed. No live tension remains — this entry is kept as decision provenance for the remaining seam work (#89, #90) rather than as an open question.

See also C-40 (the inheritance/representation coupling this migration unwinds), #85 (the migration epic), #45 (the faoapi wire / S6 dual-write).

---

### D-09: Multi-store support — parameterize the manager now vs after the FAO global delivery

| Field | Value |
|-------|-------|
| ID | D-09 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | GoF: the manager is being touched anyway — extract the `DeliveryProfile` now while context is loaded. Beck/Hickey/Ousterhout: the smallest change that delivers wins; a profile refactor adds review surface to the highest-stakes week, and frameworks built under deadline pressure rot. |
| Location | `views_postprocessing/unfao/managers/unfao.py:109-122, 234-247, 272` |
| Status | Open. Review adjudication: **after delivery** — with two exceptions to do now: delete the dead config blocks (`unfao.py:80-107`, a mis-uncomment hazard) and ensure nothing added this week hardcodes additional store identity. The `DeliveryProfile` itself is a calm 1-day job the following week (C-33). |

**DEFERRAL EXPIRED 2026-07-31 (review-rr).** The adjudication was "after the FAO global delivery"; **that delivery shipped 2026-07-27** (run-0). Both named exceptions are discharged: the dead config blocks at `unfao.py:80-107` **no longer exist** (verified — that range is now the class definition and `__init__`), and store env **names** were subsequently centralized into `unfao/appwrite_env.py` by þing-01 #134, so nothing added since hardcodes new name literals. What the disagreement actually deferred — the `DeliveryProfile` value object (one manager class, N store configs) — is now unblocked and is the "calm 1-day job." **Not resolved, because the decision it defers is still undecided:** build the profile now, or wait for issue #97's second-store scoping to define what a profile must carry. Recommend deciding that alongside #97; on decision this closes into C-33.

---

## Resolved Concerns

### C-76: `build_gaul_lookup.py` will write an empty lookup without complaint — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-76 |
| Tier | 4 — no silent corruption. A zero-row artifact fails downstream at `historical.build_historical_table`, which raises on cells absent from the lookup. The cost is that it fails **late and confusingly**: the message names missing geography rather than an empty lookup, and the artifact is committed by then. |
| Source | `code-review max` (2026-08-03) — PR #210 second pass, while checking whether the consumer's new guards duplicated a producer guarantee. They do not. |
| Trigger | When `build_gaul_lookup.py` is next run with a new or renamed `--region`, or against a datafactory whose `gaul_admin` parquets have changed shape — check the printed `cells=` count is non-zero before committing the artifact. Nothing else will tell you. |
| Owner | Whoever next runs the builder. It is a two-line guard in a script one person runs by hand, not a scheduling decision. |
| Location | `scripts/build_gaul_lookup.py` — the invariant block at `:246-268` and the write at `:284` |

The builder's invariant block is thorough about what it checks: index uniqueness (C-59), nulls in the metadata columns, `-1` sentinels in the code columns (C-35). It does not check that any rows survived. A `--region` argument that filters every cell out, or an upstream join that produces nothing, writes a zero-row parquet and prints `cells=0` as though that were a result.

**Verified 2026-08-03, and the neighbouring worry is NOT real.** The same review asked whether the builder also fails to reject a null key, since `df.isna().sum().sum()` runs *after* `priogrid_gid` becomes the index and `DataFrame.isna()` does not inspect the index. It does not check it — but the null key is unreachable anyway: `df.index.astype("int64")` raises `IntCastingNaNError` two lines earlier. Protection by accident rather than by declaration, which is worth knowing, but not a defect to fix. **Only the empty case is reachable.**

**Why this was found now.** PR #210 added consumer-side refusals for both an empty lookup and a null key to `GaulLookupEnricher.__init__`, and the review challenged them as duplicating a producer guarantee. Checking established the opposite: for the empty case there is no producer guarantee to duplicate, and for the null key the producer's protection is incidental. The consumer guards stay, and this entry records the producer-side half rather than quietly assuming someone will notice.

Cross-refs: **C-59** and **C-61** (RESOLVED — the invariant block this sits beside, and the reason it is otherwise thorough), **C-35** (the `-1` defect class it does check for), **C-75** (the consumer whose guards prompted the check), #210.

---

**RESOLVED 2026-08-04 (#90).** `build()` now refuses a zero-row result:

> the build produced ZERO cells for region 'land_gaul'. Either the region filtered every cell out, or the join found no overlap between the seven source parquets. An empty lookup is writable and looks like a result; it is not one.

Pinned by `tests/test_gaul_lookup_fidelity.py::test_builder_refuses_a_build_with_zero_cells`.

**The guard did not survive its own first test, and that is worth recording.** On an empty table `pa.array([True] * 0)` infers NULL type, so `pc.and_` in the completeness filter raised `ArrowNotImplementedError` *before* the zero-row check could speak — the confusing-late-failure this entry exists to prevent, relocated by one function. The mask is now explicitly `pa.bool_()`. A guard written and not watched fail is decoration (ADR-014 §2); this one was watched, failed for the wrong reason, and was fixed.

---

### C-77: The historical leg names its document from the model path, not from the declared consumer name — and nothing checks the two agree — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-77 |
| Tier | 2 — structural fragility with a clear trigger, affecting **both** partners. Not Tier 1: the failure is a document the consumer cannot find, not a wrong value inside one. But it is the **F1 invisibility shape** — ADR-013 §4.1a, the defect that left six `orange_ensemble` forecast documents stranded in `unfao_bucket` while forecast serving read empty for months. Nobody notices a delivery that simply is not there. |
| Source | `code-review max` (2026-08-03) — PR #211, cross-checking the crafd producer against the views-crafdapi consumer |
| Trigger | When a postprocessor's directory is renamed in views-models, or a new partner package is added whose directory name differs from its `CONSUMER_DOCUMENT_NAME` — check that the historical artifact is still retrievable by the consumer's filter. The forecast leg will keep working, so a green delivery run is not evidence. |
| Owner | Whoever takes the guard. It is a one-line assertion plus a test, not a design decision — but it must be taken deliberately, because the current agreement is a coincidence nobody has written down. |
| Location | The historical-artifact upload in `views_postprocessing/<partner>/managers/<partner>.py` — the call passing `name=self._model_path.model_name`, in `_save_contract`. For contrast, the correct leg is the `consumer_name=product.CONSUMER_DOCUMENT_NAME` argument a few lines above, which reaches the wire as `common["name"]` in `contract/wire/sink.py::deliver_run`. |

The forecast leg is right. It threads the declared constant through: the manager passes `consumer_name=product.CONSUMER_DOCUMENT_NAME` into `deliver_run`, which sets `common = {"name": consumer_name, ...}`. One declaration, carried to the wire as a parameter — the shape C-69 credited as already correct.

**The historical-actuals leg does not use that constant at all.** It passes `name=self._model_path.model_name` — a value that comes from the postprocessor's *directory name* in views-models, not from any declaration in this repository. The consumer filters on exactly the string this repo declares: `filters["name"] = self.model_path.model_name`, where the path manager is constructed as `APIPathManager("un_crafd")`.

**For FAO the two agree; for CRAF'd nobody can yet say.** `views-models/postprocessors/` contains `un_fao` and nothing else — there is **no `un_crafd` postprocessor directory**, so CRAF'd's historical `name=` has never been resolved, let alone compared against its consumer's filter. That makes this worse rather than better: for the live partner the agreement is a coincidence nobody wrote down, and for the new one it is an assumption that will first be tested by a production run. Whoever creates that directory decides, without knowing it, whether CRAF'd's actuals are retrievable.

**Nothing in this repository asserts they agree.** `tests/test_product.py` asserts `CONSUMER_DOCUMENT_NAME` for the forecast leg; `tests/test_hop_b_sink_e2e.py` checks `consumer_name` on the forecast leg. Neither touches the historical leg's `name=`. A rename of the views-models directory — an ordinary, plausible act, done in a different repository by someone who has never read this file — silently detaches the historical artifact from the consumer's filter while every test here stays green and every delivery run reports success.

This is ADR-003's rule broken in the quiet direction: the delivery **infers** its consumer identity from a path instead of reading the declaration that exists three lines away. It is also the fourth home for partner identity, where C-69's 2026-07-31 note counted three and recommended consolidation rather than relocation. Consolidation did not reach this line.

**Scope note:** the crafd package inherited this unchanged from `unfao`; PR #211 did not introduce it, it doubled it. Registering it against both partners rather than against the PR.

Cross-refs: **C-01** (RESOLVED — the metadata-completeness gate; same partner, same delivery, different field), **C-69** (RESOLVED — "partner identity has THREE homes"; this is the fourth and the note's consolidation recommendation is the fix), **C-33** (the duplication that turned one instance into two), ADR-013 §4.1a (F1 invisibility), ADR-003 (declarations over inference), #211.

**RESOLVED 2026-08-04 (B1).** Both legs now name the document from the declaration:
`name=product.CONSUMER_DOCUMENT_NAME` replaces `name=self._model_path.model_name` in each
partner's historical upload, and `tests/test_product.py::test_both_delivery_legs_name_the_document_from_the_declaration`
asserts one forecast leg and one historical leg per partner, mutation-proven three ways
(revert one leg; add a third; stop declaring on the forecast leg).

**Delivery-neutral, verified before changing anything.** `CONSUMER_DOCUMENT_NAME` is
`"un_fao"` and the views-models directory is `un_fao`, so `model_name` resolved to the same
string. No delivered byte changes for FAO; what changes is that the agreement is now a
declaration rather than a coincidence in another repository's filesystem.

**Fixed now rather than when it broke, because it was about to be sprung.** views-models#333
creates CRAF'd's launcher directory. Whoever named it would have decided, without knowing
it, whether CRAF'd's historical artifact was retrievable — and the failure mode is an empty
endpoint, not an error. The constraint was posted on that issue on 2026-08-04; this removes
the need for anyone to honour it.

One residual, unchanged and not this entry's: the guard is a source scan, because the
managers cannot be instantiated without Appwrite env and a views-models path manager. That
is the standing pattern here and the reason **#18** exists.

---

### C-07: Undeclared direct runtime dependencies in pyproject.toml — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-07 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When `views-pipeline-core` updates its dependency tree (e.g., drops `geopandas` or `joblib`), verify that this package's imports still resolve |
| Location | `pyproject.toml` (the dependency block); the partner managers, which are the only modules importing `views_pipeline_core`. *(This row previously cited `unfao/enrichment.py` and `unfao/extraction.py` — both moved or deleted by #151/#153.)* |

`mapping.py` directly imports `geopandas`, `shapely`, `numpy`, `pandas`, `joblib`, and `multiprocessing`. `unfao.py` directly imports `pandas`, `polars`, and `python-dotenv`. Only `views-pipeline-core` and `cachetools` are declared in `pyproject.toml`. The undeclared dependencies presumably arrive transitively via `views-pipeline-core`, but this coupling is implicit and fragile. If the upstream package refactors its dependency tree, this package will break with `ImportError` at install time.

**Update 2026-06-24 (narrowed):** the `mapping.py` dimension is gone (C-39 — the `geopandas`/`shapely`/`joblib`/`multiprocessing` imports were deleted; `cachetools` dropped from `pyproject.toml`). Residual: `unfao.py` imports `pandas`/`polars`/`python-dotenv` undeclared, arriving transitively via `views-pipeline-core` (which *is* declared). Much smaller surface (Tier 4-ish); consider resolving outright if the transitive-via-pipeline-core guarantee is deemed sufficient.

**Update 2026-08-01 (`falsify`) — a SECOND undeclared dependency, and this one's transitive path is about to disappear.** `appwrite` is used in this repo (`contract/launch_config.py`, `unfao/managers/unfao.py`) and declared in **no** manifest — it arrives transitively via `views-pipeline-core`, exactly as `pandas` does. What makes it different from the pandas residual: **views-pipeline-core is making `appwrite` an optional extra** (their **#345**, on CRP grounds — three repos that never mention Appwrite currently install its SDK). **When that lands, the transitive path disappears.**

**⚠ Corrected 2026-08-03 — the trigger has FIRED and the stated failure mode was wrong.**
pipeline-core **#345 is CLOSED**, and 3.0.0 does make `appwrite` an optional extra. But
this repository contains **zero** direct Appwrite SDK imports (`grep -rn '^\s*\(from\|import\) appwrite' views_postprocessing/` → 0);
`contract/launch_config.py` mentions the word once, in a docstring naming its sibling
`appwrite_env`. So "this repo breaks at import" was never true of *our* imports.

The real and still-live risk is one level out: **pipeline-core's own `DatastoreModule`
imports the SDK unguarded**, so bumping to 3.0.0 without declaring the `appwrite` extra
breaks the delivery at import — inside a dependency, which is harder to diagnose than a
break in our own code. That is a precondition on the C-44 bump, and it belongs there as
much as here.

So this entry is no longer "Tier 4-ish, resolve if the transitive guarantee is deemed sufficient" — the guarantee is being **withdrawn upstream, deliberately**. Fix is one line: declare `appwrite` in `pyproject.toml`, or depend on `views-pipeline-core[appwrite]`. Relayed in **#172**; registered here rather than as a new entry because it is the same problem type at a new location. **New trigger: before views-pipeline-core#345 lands.**

**Update 2026-07-31 (review-rr — narrative corrected against the tree):** the 2026-06-24 residual is now overstated. Verified: **`polars` has zero references repo-wide**; **`python-dotenv` is dead** (þing-01 #134 killed the implicit ensemble-dotenv borrow — see `unfao/appwrite_env.py`); `cachetools` is gone. Meanwhile `views-frames` and `pyarrow` became **declared** direct dependencies. **The residual is `pandas` alone**, imported directly at the three locations above and arriving transitively via `views-pipeline-core`. One undeclared package on a path that is itself being retired (epic #85) — genuinely Tier 4-ish now; resolve outright if the transitive guarantee is deemed sufficient, or declare `pandas` explicitly in the same PR that closes #89.

**RESOLVED 2026-08-03 — declared, and the free-riding ended.** `pyproject.toml` now declares `views-pipeline-core = {version = ">=3.0.0,<4.0.0", extras = ["appwrite"]}` and a dev group carrying `pytest` and `ruff`.

The extra is **not optional despite its name**, and that was proven rather than assumed: with the SDK uninstalled from an otherwise-complete environment, `from views_postprocessing.unfao.managers import UNFAOPostProcessorManager` raises `ImportError: views_pipeline_core.modules.appwrite requires the optional 'appwrite' extra`. The failure is at **import**, inside a dependency — which is why declaring it matters more than the word "extra" suggests.

`pytest` was never declared here and arrived transitively through pipeline-core, which dropped it as a runtime dependency in 3.0.0. CI runs `poetry install` then `poetry run pytest`; without the dev group that job would have failed as *"pytest: command not found"*, which reads like a runner fault rather than a dependency one.

**One correction to this entry's own residual.** It said *"the residual is `pandas` alone."* Wrong twice, and an AST sweep of the shipped package says so:

- **`numpy` is a module-scope runtime import and is undeclared** — `delivery/draws.py`, `delivery/observed_range.py`, `contract/frames.py`, `contract/frame_extraction.py`, `contract/enrichment.py`. It arrives transitively (pyarrow requires `numpy>=1.16.6`; views-frames `numpy>=1.26,<3`), so nothing breaks — but it is exactly the free-riding this entry exists to end, and it is a **direct** import, not a transitive one.
- **`pandas` is not a runtime dependency at all** — `contract/enrichment.py` imports it under `if TYPE_CHECKING`, which `tests/test_doc_accuracy.py` pins.

So the honest residual is the reverse of what was written: pandas is already gone, and numpy should be declared. Small, and left as a follow-up rather than folded into a dependency bump whose point was to change one thing.

Cross-refs: **C-44** (the bump that carried this), views-postprocessing#172, pipeline-core #345/#361.

---

### C-13: No timeout on Appwrite operations — pipeline can hang indefinitely — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-13 |
| Tier | 2 |
| Source | `expert-review` (2026-06-02) |
| Trigger | When configuring Appwrite connection parameters — in `_ContractStorePort` (contract path) or `_save`/`_read_forecast_data` (legacy path) — verify that timeout parameters are set on the underlying HTTP client; currently no timeout exists and a hung endpoint blocks the pipeline indefinitely |
| Location | `views_postprocessing/unfao/managers/unfao.py:37-64` (`_ContractStorePort` — all four contract-path store calls), `:247` (legacy selection), `:560`, `:571` (legacy uploads) |

`prediction_store_manager.download_latest_file()` (line 131) and `dsm.upload_data()` (lines 262, 272) make network calls to Appwrite with no configured timeout. If the endpoint hangs (DNS resolution stalls, connection accepted but response never arrives, TLS handshake blocks), the pipeline blocks indefinitely. There is no watchdog timer, no circuit breaker, and no automated alert for a run that never completes. The only detection is manual observation that a scheduled run didn't finish.

**RESOLVED 2026-08-03 by the pipeline-core 3.0.0 bump (C-44).** `modules/appwrite/transport.py` now defines `install_request_timeout()`, and `modules/appwrite/file.py:1382` **calls it** — so the timeout applies to this repo's Appwrite operations without any change on our side. Verified against the installed 3.0.0 wheel, not the changelog.

---

### C-58: A wrong Appwrite coordinate auto-provisions a new empty target instead of raising — both client lineages, on every write — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-58 |
| Tier | 2 — a single wrong or drifted coordinate value silently redirects a delivery into a freshly created empty bucket/collection/database; the run reports success, FAO receives nothing, and no error is raised at the time of the mistake |
| Source | `manual` (2026-07-31) — review-rr blind-spot analysis; the underlying code finding was verified from this seat during þing-01 (recorded in `orð_09.md`, and it revised the assembly's own sáttmál S8 and D8 trigger wording) |
| Trigger | When any `APPWRITE_*_BUCKET_ID` / `_COLLECTION_ID` / `_DATABASE_ID` value changes — a registry amendment (C-57), a launcher reconfiguration, a second-store rollout (#97), or a typo — verify the delivery landed in the **intended** target rather than a newly created one: check the run's uploaded object count against the store's expected bucket, not just that the run exited 0 |
| Location | views-pipeline-core `modules/datastore/datastore.py:350-370` (`upload_data` creates a missing bucket and retries; their ADR-046 §5); `modules/appwrite/file.py:2205/2351/2395` → `create_metadata_collection_if_not_exists` (`:1184`) → `create_database_if_not_exists` (`:905`) → `create_collection` (`:1250`) → `_create_dynamic_attributes` (`:1027`, failures logged only). Consumed at `views_postprocessing/unfao/managers/unfao.py:56` (`_ContractStorePort.upload`), `:560`, `:571` (legacy `_save`) |

þing-01's **D5** ruled that a wrong coordinate **must RAISE**, that auto-provisioning must be **opt-in and default off**, and that a half-succeeded write must raise. The platform does not currently behave that way on the write path, and the assembly's own working document had this wrong until it was corrected from this seat: sáttmál S8 asserted "pipeline-core raises," which is true for reads and **false for writes**. Verified: **both** client lineages auto-provision. `DatastoreModule.upload_data` catches a missing bucket, creates it, and retries. `upload_file_with_metadata` traverses create-if-not-exists for the metadata collection, the database (the EXISTS short-circuit still exercises `databases.list`), the collection, and the dynamic attributes — on **every** metadata upload, with attribute-creation failures logged rather than raised. That correction is why the verdict's D8 trigger was widened to fire on a defect *common to* the client copies, not only on divergence between them.

The practical exposure here is bounded but real. Coordinates are validated for **presence** (`appwrite_env.assert_env_declared`, D6) — never for **correctness**, which is unobservable from this seat by design: this repo has no console access and no introspection, and none should be added, because scopes and coordinates are *declared, not discovered*. Run-0 delivered to the correct bucket, which proves the currently-configured coordinates are right; it does **not** prove the guard exists, because a correct coordinate never exercises the auto-create branch. The nearest thing to a detector today is the `_ContractStorePort.upload` orphan check (`unfao.py:56-64`) and the manifest-last commit marker, neither of which catches "wrote successfully to the wrong place."

Tier 2 rather than 1: no *value* is corrupted — the payload is exactly right, it lands in the wrong container — and the consequence is visible downstream (FAO serves nothing) rather than being wrong-but-plausible data. The precedent is already on record: six stranded `orange_ensemble` forecast documents sat invisible in `unfao_bucket` for months (ADR-013 Post-adoption, 2026-07-15) because a *name* filter mismatched — the same class of silent mis-addressing, discovered only by a deliberate read-only audit.

**Update 2026-08-01 — the upstream fix has LANDED, and this entry now rides the 3.0.0 bump (Cluster M).** views-pipeline-core **#322** (*"[þing-01] ADR-046 §5 + write-path raise-by-default"*) is **CLOSED**, as are **#331** (relocate the four `create_*` sites into a dedicated provisioning module) and **#332** (assert the delivery path does not import provisioning). That is D5's ruling implemented: provisioning moved out of the ordinary write path, and the write path raises by default.

**We do not have it yet.** All three landed on their `development` (3.0.0); our pin resolves 2.3.0 from PyPI, which still auto-creates. So this entry is **fixed upstream and live here** until the bump — the same shape as C-73. Added to **Cluster M**; verify at the bump that a wrong coordinate now raises rather than creating an empty target.

**Not this repo's code to fix.** The fix belongs in views-pipeline-core (make provisioning an explicit opt-in parameter defaulting to off, per D5), and D5's drill ordering is fixed verbatim by the verdict: amend → ship raise → drill the raise path → stand up a test project → drill provisioning. This repo's available mitigations are a post-upload target assertion in `_ContractStorePort`, or a read-back count check after the manifest commits.

Cross-refs: C-57 (registry drift — the most likely way a coordinate goes wrong), C-25 (the sibling wrong-*source* selection risk, mitigated by identity assertion), C-13 (the same store calls, timeout dimension), C-40 (the inherited pipeline-core surface this arrives through — **Cluster G**), C-22 (no recall procedure if a mis-delivery is discovered late).

**RESOLVED 2026-08-03 by the pipeline-core 3.0.0 bump (C-44).** The auto-create-and-retry is gone: `create_bucket` appears **zero** times in `modules/appwrite/file.py`, and `:1406` now carries an explicit *"Fail loud, BEFORE any write, if a target container does not exist"* guard. A wrong or stale coordinate now fails instead of silently provisioning new production storage. Upstream views-pipeline-core C-228; verified in the installed wheel.

**Residual, and it is not ours to close: the fix is verified by inspection, not by probe.** This entry closed on *provisioning* — `create_bucket` is gone and I read the guard. The neighbouring **delete** path is a different question and views-pipeline-core **#333** ([þing-02 ledger row C5](https://github.com/views-platform/views-pipeline-core/issues/333), **OPEN**) is the probe that would answer it. Its three siblings — their #322, #331, #332 — all shipped in 3.0.0; #333 did not, because it is **blocked on the operator issuing a test key** (þing-02 G2 item f/h).

What it probes is specific and is not covered by any check we own. The de-dup lookup is a **database** read; the verify step is a **storage** read; and entry to the delete branch requires *the lookup to have succeeded*. So a key with **database read and no bucket-file read** gets past the lookup, fails the verify, and reaches the delete — while a *wholly* read-restricted key fails benignly at the lookup and proves nothing. The dangerous asymmetry is what you get cutting a write-object key by **operation** rather than by **resource**.

Two facts make that concrete for this repository rather than theoretical:

1. **The path has already run 108 times in production on FAO's outbound bucket** — run-0's uploads — and the þing-02 verdict records it was benign *only because the files were readable* (`orð_dómr.md:294-298`).
2. **We cannot state our own key's scopes from evidence.** `docs/CLONING.md:131` records that this repository ran for months under a key named for pipeline-core and nobody could say what it was scoped to. So the dangerous shape cannot be ruled out by inspection here either.

Nothing to do in this repo, and no reason to reopen the entry: the code fix is real and verified. Recorded because closing C-58 on the provisioning half should not read as closing the delete half, and because #333's gate — *"no scoped writer key is issued before C1 and C2 ship and C5's probe passes"* — is an operator action with this repository downstream of it.

Cross-refs: **C-79** (`_ContractStorePort.upload` fails *open* on an unrecognised result — the same delete-adjacent surface), **C-40** (we run pipeline-core's client under our own identity, which is what þing-02 was about), views-pipeline-core #333/#322/#331/#332.

---

### C-62: The pinned pipeline-core release still installs geopandas and torch into a repo that architecturally excised them — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-62 |
| Tier | 3 — no correctness or reliability impact: the packages are installed but never imported. The cost is **measured at 3.4 GB of virtualenv** for a repo that writes parquet files, plus an architectural excision that is **real in the source but incomplete in the environment**, landing on the first-ever release. |
| Source | `manual` (2026-07-31) — maintainer challenge during the development→main sweep ("Is geopandas back? Is it still here?"), verified against `poetry.lock` and the sibling checkouts |
| Trigger | **The first half FIRED on 2026-08-01** — `1.0.0` was tagged and this drag shipped with it. Remaining trigger: when taking the views-pipeline-core 3.0.0 bump (**C-44**), verify `geopandas` and `torch` have left the resolved dependency tree. Also re-check before any *PyPI* publish, which is the point at which the footprint reaches someone other than this team. |
| Location | `poetry.lock` (`geopandas 1.0.1`, `optional = false`); `pyproject.toml:13` (`views-pipeline-core = ">=2.1.3,<3.0.0"`, which resolves to 2.3.0) |

This repo declares exactly three dependencies — `views-pipeline-core`, `views-frames`, `pyarrow` — and imports **zero** geospatial libraries. Verified 2026-07-31: the only three mentions of `geopandas`/`shapely` in `.py`/`.toml` are assertions of its *absence* (`enrichment.py:9`, `build_gaul_lookup.py:11`) and a doc-accuracy test that **bans the word** (`tests/test_doc_accuracy.py:29`). C-39's deletion held completely at the source level.

**The lockfile tells a different story, and the installed venv confirms it.** `poetry.lock` resolves `geopandas 1.0.1` with `optional = false`. The carrier is the pinned release: **views-pipeline-core 2.3.0** (PyPI) declares `geopandas >=1.0.1,<2.0.0`, `torch >=2.6.0,<3.0.0`, plus `scipy`, `seaborn`, `plotly` and `plotly-express`.

**Measured in the live project virtualenv** (`views-postprocessing-8UwQDgw_-py3.13` — the only poetry venv on the machine; views-pipeline-core has none of its own, it is a *package inside this one*). **Corrected figures, 2026-07-31**: the first measurement was taken mid-install and understated it.

| Installed, never imported | Size |
|---|---|
| `nvidia/` — CUDA runtime (`cu13`, `cudnn`, `cusparselt`, `nccl`, `nvshmem`) | **2.7 GB** |
| `plotly` | 42 MB |
| `matplotlib` | 25 MB |
| `geopandas` | 1.6 MB |
| **venv total** | **3.4 GB** |

**And `torch` itself is not installed at all** — no `torch/` directory, no dist-info, with no install running. Only its five `nvidia-*` dependencies landed (they are marked `platform_system == "Linux"`, i.e. this machine). The repo is therefore carrying **2.7 GB of GPU support libraries for a package that is absent**. Cause unknown — a failed wheel, an interrupted install, or a marker torch carries that its dependencies do not; recorded as unexplained rather than guessed at.

**⚠ Framing correction, recorded because it inverts the intuition that opened this investigation.** The audit began as "is geopandas back?" — and geopandas is the *architectural* violation (this repo spent PR #42 removing it). But it is **1.6 MB**. The *material* cost is **torch's NVIDIA CUDA stack at 2.5 GB — 89% of the entire virtualenv — in a delivery repo with no GPU code, no model training, and no tensor operations of any kind.** Optimising for the offensive dependency rather than the expensive one would have missed almost the whole bill.

**Update 2026-08-01 — the drag now has a measured security surface.** GitHub raised **32 Dependabot alerts** when `main` was brought current. **31 of them are `poetry.lock` resolution, not declared dependencies** — and the shape matches this entry exactly: **Pillow ×13** and **GitPython ×9** (via `plotly`/`seaborn`/`wandb`), plus `geopandas`, `torch`, `pytest`, `paramiko`, `pywin32`, `diskcache`, `setuptools`, `python-dotenv` — one each. Every one of those roots is declared by **views-pipeline-core 2.3.0**, none by this repo, and none is imported by this repo's code.

This does not make the entry more urgent; it makes it **measurable**. The 3.0.0 bump this entry is held on removes the roots, and with them most of this alert surface. Until then the alerts are real but unreachable, and closing them individually would be treating symptoms of a dependency this repo does not choose. The 32nd alert is `pyarrow`, which **is** declared here and is registered separately as **C-72**.

**Dependency chain, traced 2026-07-31.** `views-pipeline-core` is the **sole** requirer: `torch = ">=2.6.0,<3.0.0"` in the 2.3.0 metadata; torch 2.12.1 then pulls the five `nvidia-*` wheels on Linux. Nothing else in the tree asks for torch, and this repo imports it zero times.

**Removal path — there is no correct fix inside this repo.** views-pipeline-core `development` (already versioned **3.0.0**) declares **no torch, no geopandas, no scipy, no seaborn, no plotly**, and imports torch nowhere; their own test asserts the absence of `import torch`. The fix is complete upstream and purely a publishing gate. Their release runbook (#313) pins the order: **views-frames (done) → views-evaluation 0.5.0 → views-pipeline-core 3.0.0 → views-reporting 0.3.0 → models/postprocessing envs**, executing on the maintainer's platform-wide signal. So this entry closes when C-44's bump becomes takeable — not before, and not by local action.

*A local workaround exists and is deliberately NOT recommended: declaring `torch` here against the PyTorch CPU wheel index would shed the `nvidia-*` tree immediately, but it makes this repo declare a dependency it never imports, and the whole change would be reverted at the 3.0.0 bump. Churn for a footprint that is already scheduled to vanish. Recorded so the option is not rediscovered and mistaken for free.*

**This is not a live fight — it is a released-version lag.** views-pipeline-core's `development` branch already declares no geopandas and imports none, and its own falsification tests name the problem explicitly (*"geopandas, seaborn, plotly, matplotlib — ~2.5 GB) for 298 LOC of optional…"*, their `tests/test_falsification_extraction_docs_packaging.py:59`). The fix exists upstream and is gated purely on **publishing 3.0.0** (their #319 / #313).

**Why it matters here specifically.** PR #42 deleted a 3,171-line geopandas mapper and a 774 MB shapefile bundle to get geopandas out of this repo (ADR-011 / C-39). That excision is currently source-only. And it lands on this repo's **first-ever release** (#125, no tags exist): publishing a delivery package that resolves 2.5 GB of CUDA libraries is a materially different artifact from one that does not — and the first release is where that expectation gets set.

**⚠ This entry pulls in the OPPOSITE direction to C-44 — deliberately, and the tension should stay visible.** C-44 says *do not take the 3.0.0 bump* until the platform runs smoothly on `development` across all repos (a standing maintainer constraint, and the right call). C-62 records what *waiting* costs: every day on the 2.3.0 pin is a day this repo ships an environment contradicting its own architecture. Neither entry overrides the other; together they say "the bump is held on purpose, and here is the bill." Registered separately rather than folded into C-44 precisely so the bill is not hidden inside the entry arguing for the delay.

Cross-refs: **C-44** (the held bump — same action, opposing rationale), **C-39** (RESOLVED — the source-level deletion this shows is environment-incomplete), **C-07** (the sibling dependency-declaration concern: undeclared *direct* imports, where this is unwanted *transitive* installs), **C-40** (Cluster G — the inherited pipeline-core surface this arrives through), #125 (the release this bites at), views-pipeline-core #319 / #313 (the publish that resolves it), views-datafactory#387 (the same audit's cross-repo finding). **Cluster G.**

**RESOLVED 2026-08-03 by the pipeline-core 3.0.0 bump (C-44).** Measured against the lock file, before and after:

| package | before | after |
|---|---|---|
| geopandas, torch, shapely, pyogrio, seaborn, statsmodels, plotly | present | **gone** |
| total locked packages | 155 | **118** |

The CRP argument this entry made — that a repo which architecturally excised geospatial and ML stacks should not install them — was made upstream too, and 3.0.0 acted on it. Nothing was needed here beyond the pin.

**⚠ But the alert-surface half of this entry did NOT resolve, and saying otherwise would be the more comfortable error.** This entry itemised 31 Dependabot alerts. **Twenty-nine survive at unchanged versions.** Verified against both lock files:

| package | before | after |
|---|---|---|
| Pillow (13 alerts) | 12.2.0 | **12.2.0** — now via `matplotlib ← pyod` |
| GitPython (9 alerts) | 3.1.50 | **3.1.50** — now via `wandb`, still a pipeline-core dependency |
| matplotlib, scipy, paramiko, setuptools, python-dotenv, wandb | — | **all identical** |

Only geopandas and torch lost their root. The dependency **tree** got much smaller; the **vulnerability** surface barely moved. The entry is resolved on its stated subject — the transitive drag — and explicitly **not** on the alert count, which was never in its title but was in its body.

---

### C-73: The contract path selects the newest manifest over a broad filter — an unpaged upstream lookup can ship a stale run — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-73 |
| Tier | 2 — a delivery can **assemble and ship a stale run rather than failing**. Not Tier 1 because the run that ships is internally coherent: its manifest hashes verify, its shards match, per-shard declared identity is checked. The partner receives a *complete, valid, wrong-vintage* delivery, and nothing on either side reports a problem. |
| Source | `falsify` (2026-08-01) — audit of "there is nothing more to do in this repo"; the hazard itself is views-pipeline-core's **C-241**, relayed to this seat in **#172** |
| Trigger | Before the next delivery run, and again when bumping to the pipeline-core release carrying their **#341** — confirm the run actually selected is the run expected (compare the resolved `run_id` against the producer's newest published run, not merely that a manifest resolved) |
| Location | `views_postprocessing/contract/wire/source_selection.py:40` (`HOP_A_MANIFEST_FILTERS`) and `:106` (`store.latest_file_id(dict(HOP_A_MANIFEST_FILTERS))`); reached through `views_postprocessing/unfao/managers/unfao.py:44` (`_ContractStorePort.latest_file_id`) → pipeline-core's `get_latest_file_id` → `search_files_by_metadata` |

pipeline-core's `search_files_by_metadata` was **unpaged**: Appwrite returns 25 rows by default, and `get_latest_file_id` sorted *those* and called the result "latest". With more than 25 matching documents it returned **the newest of the oldest 25** — silently, and staler every run.

**This reaches this repo because `HOP_A_MANIFEST_FILTERS` is broad by design**: `{"category": "forecast", "type": "sampled_forecast_manifest"}` matches **every manifest ever published**, and the store has no retention (C-25's own note: *"every historical upload remains a candidate forever"*). Shard lookups are name-scoped and unique (`:120`, `:144`), so they resolve correctly **for whichever run was selected** — which is precisely why the failure is quiet: everything downstream of the selection is self-consistent.

**Not a defect in this repo's code, and the fix is not ours** — the upstream fix (pipeline-core #341) arrives with a pin bump because we import their `DatastoreModule` rather than keeping our own client. What *is* ours is that the register carried no record of it, and that the broad-filter-plus-newest-wins selection strategy is a choice this repo made and can revisit independently of the upstream fix.

**⚠ This falsifies a claim made in C-25's resolution earlier the same day.** That entry was closed as *"superseded by mechanism"* on the reasoning that *"the contract path selects by run manifest … so recency-based selection is not an operation the code can perform any more."* **It is exactly what the code does** (`:106`). The half of C-25 that genuinely is solved is **producer identity** — the manifest carries a declared ensemble, verified per shard header (`:73-81`), so a *different producer's* run cannot be selected. The **recency** half was never solved; it moved from picking the newest payload file to picking the newest manifest. C-25's resolution has been corrected in place rather than rewritten, because the overclaim is more instructive than the conclusion.

Cross-refs: **C-25** (whose resolution this corrects), **C-40** (the inherited pipeline-core surface this arrives through — **Cluster G**), **C-72** (the other pin-gated upstream item), **#172**, views-pipeline-core **#339** / **#341** / C-241, ADR-013 §4.3 (manifest selection).

**RESOLVED 2026-08-03 by the pipeline-core 3.0.0 bump (C-44).** This entry's cause was upstream and is fixed at the source. `search_files_by_metadata` now pages: `file.py:1023-1045` carries the views-pipeline-core C-241 remediation with `DEFAULT_PAGE_LIMIT = 100`, `Query.limit(...) + Query.offset(offset)`, and a `MAX_METADATA_PAGES = 1000` bound. Its own comment states the defect precisely — *"returned the newest of the OLDEST 25, which does not fail: it delivers a stale run."*

The second half matters as much: `get_predictions_by_metadata` used to return `[]` when the **search itself failed**, which `get_latest_file_id` turned into `None`. It now raises `MetadataSearchIncomplete`. Without that, paging would have traded a false-*stale* answer for a false-*absent* one.

**We did not find this ourselves** — it came from views-pipeline-core via views-postprocessing#172, reaching us because `_ContractStorePort.latest_file_id` feeds ADR-013 `resolve_run`, whose manifest lookup uses the deliberately broad `HOP_A_MANIFEST_FILTERS`. Every manifest ever published matched, and the store has no retention. Worth recording that the reach-out, not our own review, is what closed a Tier-2 delivery-correctness risk.

Cross-refs: **C-44**, **C-15** (retention), upstream views-pipeline-core C-241/C-231/C-232, #172.

---

### C-44: views-pipeline-core 3.0.0 dependency bump is pending and must not land until the platform runs on development across all repos — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-44 |
| Tier | 3 |
| Source | `manual` (2026-06-26) — surfaced while consolidating a stranded local commit after the input-integrity sprint merge |
| Trigger | When views-pipeline-core 3.0.0 is published to PyPI **and** the platform is confirmed running smoothly on `development` across all consumer repos — then bump `pyproject.toml` to a reproducible version pin (`views-pipeline-core = ">=3.0.0,<4.0.0"`), re-lock, and PR. Do **not** land the bump before both conditions hold, and do **not** source it from a moving git branch. |
| Location | `pyproject.toml:13` (currently `views-pipeline-core = ">=2.1.3,<3.0.0"`); `poetry.lock` (pins `views-pipeline-core 2.3.0`, a reproducible PyPI wheel); the deferred change preserved on local branch `backup/pipeline-core-3.0.0-git-source` (commit `78d238e`) |

`development` currently pins `views-pipeline-core = ">=2.1.3,<3.0.0"` and the committed `poetry.lock` resolves it to **2.3.0** from PyPI — reproducible, and the merged input-integrity sprint (#64) was CI-proven green against it. **3.0.0 is not yet on PyPI (political hold).** A local-only commit (`78d238e`, authored 2026-06-25 in a separate session, never pushed) repoints the dependency to pipeline-core's **git `development` branch** to track the unreleased 3.x "in tandem with other consumers."

That change was deliberately **not** landed on `development` (2026-06-26), for three reasons: (a) sourcing from a **moving git branch** makes builds **non-reproducible** (the branch advances under us); (b) it is a **major-version switch** (2.x→3.x) whose breaking changes were never exercised against the just-merged sprint code; (c) it would require a **full re-lock** resolving 3.x + its transitive tree, rippling through `poetry.lock`. The maintainer's standing constraint: **the platform must run smoothly on `development` across all repos before taking the major dependency bump.** Until then the bump is premature.

No silent corruption and no current breakage (development is green on 2.3.0) → **Tier 3** (coordination / release-sequencing / reproducibility).

**GATE RE-ASSESSED 2026-07-31 — the second condition now has substantial evidence behind it; the first does not, and the difference matters.**

This entry's trigger holds the bump on **two** conditions. Their status has diverged:

**Condition 2 — "the platform is confirmed running smoothly on `development` across all consumer repos."** The strongest available evidence arrived on **2026-07-27**: run-0 delivered the first FAO global-land forecast end to end, every hop on `development` — views-models config (`region: land_gaul`, `data_format: feature_frame`) → pipeline-core's frame-native fetch and Track A publish → this repo's contract delivery (108 shards + sidecar + manifest, 64,742 cells, 28,356,996 rows, 5.6 GB peak, no OOM) → views-faoapi ingest. Confirmed serving live on **2026-07-31** (`scripts/smoke.py`, ALL PASS at v1.3.11; `IDN` present on both surfaces, a cell outside the old Africa-only region, so global serving is proven).

**Scoped honestly:** that exercises the **FAO delivery chain** across five repos on `development`. It is *not* evidence about consumers outside that chain (views-reporting's report path, views-baseline, other model families). Whether "across all consumer repos" means the delivery chain or literally every consumer is a maintainer judgement this entry cannot make. What has changed is that the condition moved from *unevidenced* to *substantially evidenced for the path that matters most*.

**Condition 1 — "views-pipeline-core 3.0.0 is published to PyPI."** Still **unmet**, and it is not blocked on engineering. Verified 2026-07-31: pipeline-core's `development` already carries `version = "3.0.0"` with the heavy dependency set removed; views-evaluation's `to_metric_frame` (the one real release-train edge in their runbook #313) **exists in code**, 8 commits past its `v0.4.0` tag, needing only a version bump and a publish. The chain their runbook fixes is: views-frames ✅ → **views-evaluation 0.5.0** → **views-pipeline-core 3.0.0** → views-reporting 0.3.0 → models/postprocessing envs — and it states plainly that it *"executes only on Simon's platform-wide signal."*

**Net:** this entry is no longer waiting on two open questions. It is waiting on **one release signal**, with all the underlying code already written. That does **not** authorise the bump — the signal is the maintainer's alone, and the scoping caveat above is a real reason it might still be withheld. It is recorded so the next reader sees a gate that has *moved*, rather than assuming both conditions are still closed. **C-62 records what continuing to wait costs** (3.4 GB of unused dependencies, 2.7 GB of it CUDA libraries for an absent package).
 The deferred work is preserved (backup branch) and becomes a trivial, reproducible one-line pin once 3.0.0 ships and the cross-repo gate clears. Cross-refs C-40 (the underlying pipeline-core inheritance coupling that makes major bumps high-blast-radius), C-07 (the transitive-via-pipeline-core dependency surface), C-09 (publish-workflow version handling).

**RESOLVED 2026-08-03 — the bump landed, and the gate it named was the operator's to open.** This entry said the bump *"must not land until the platform runs on development across all repos."* views-pipeline-core 3.0.0 reached PyPI on 2026-08-03; the operator took the decision with the trade-off stated.

**What it closed, each verified in the installed wheel rather than from the changelog:** C-73 (upstream views-pipeline-core C-241 — the unpaged lookup that could ship a stale run), C-58 (views-pipeline-core C-228 — silent provisioning of new production storage), C-13 (a request timeout that now installs itself), C-62 (geopandas and torch out of the tree; 155 → 118 packages), and C-07 (appwrite and pytest now declared here rather than free-ridden).

**What it cost:** less than the release notes implied. Of the three breaking changes flagged as likely to touch us, one was already satisfied — this repo imports `PredictionFrame` from `views_frames`, constructs it positionally, and never reads `.y_pred`, so the leaf-class migration was already done. The other two were the two declarations above.

**Verification:** an isolated Python 3.11 venv built from PyPI with the exact resolved set — **362 passed, 40 xfailed, 0 failed**; both partner managers import; the ADR-013 §10 golden fixtures still verify byte-for-byte (`sha256sum -c SHA256SUMS`, all OK) because `pyarrow` and `views-frames` were deliberately left untouched.

**Not closed by this:** **C-72**. The pyarrow CVE fix still changes delivered wire bytes and still needs a coordinated three-repo re-vendor of the §10 fixture. That is a separate, harder job and the pin is unchanged at `>=16.1.0,<17.0.0`.

---

### C-78: A partner package without an `__init__.py` is invisible to the guard that inventories them — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-78 |
| Tier | 4 — FIXED in the same change that found it; recorded because the *reasoning* is what future guards need, not because work is outstanding. No delivery was ever affected. |
| Source | `code-review max` (2026-08-03) — PR #211 second pass, attacking the new scope guard |
| Trigger | When a future guard inventories the package tree, check what it uses as its "is this a package" test. If it asks for `__init__.py`, it disagrees with every other scan in this suite and with the repository's own root. |
| Owner | Discharged. |
| Location | `tests/test_clone_readiness.py` (the criterion); `views_postprocessing/` (which has no `__init__.py` of its own) |

`test_the_declared_partner_list_is_the_real_one` was written to stop a partner package going unguarded — the defect that let `crafd/` land exempt from at least seven checks — the four `tests/conftest.py` enumerates, plus the three product pins (`TARGETS`, `S_MIN`, `UPLOAD_ENABLED`) that `tests/test_product.py` held for FAO alone. Its first draft asked for a directory containing `__init__.py`.

**`views_postprocessing/` has no `__init__.py`.** The distribution root is already a PEP 420 namespace package, so the guard applied to its children a test its own parent fails. Verified by building a partner package without one, carrying three real defects — `UPLOAD_ENABLED = True` (ADR-013 §11.4), a wrong `CONSUMER_DOCUMENT_NAME` (§4.1a), and a live `load_dotenv` (þing-01 #134) — and running the full suite: **green**. Adding one empty `__init__.py` to the identical tree made the guard fire. It imported and ran fine at runtime throughout.

The criterion is now "contains at least one `.py`, and is not `__pycache__`", which is what the suite's eight other tree scans effectively use (`rglob("*.py")`). The same review found `MACHINERY_PACKAGES` was validated against nothing — a stale name there **pre-classifies** any future package that takes it, and `reconciliation` (C-47's phantom) is exactly such a name. Both lists are now checked against disk.

**One correction to C-47 while here.** That entry's Tier-4 rationale says the phantom directory was *"not importable (no `__init__.py`, no sources)"*. Under PEP 420 that reasoning is wrong: a directory with no `__init__.py` and no sources still imports as a **namespace package** whose `__path__` points at it — only its submodules fail. Reproduced on a copy of the tree. The directory itself was deleted by #177 on 2026-08-01, so nothing is importable today and the tier stands; what does not stand is the reason given for it. The harm C-47 actually recorded — *"misleading tools that inventory the tree"* — is precisely what this entry is about.

Cross-refs: **C-47** (the phantom directory, and the corrected rationale above), **C-57** (a guard scoped by name missing the second subject — the same disease, one file over), **C-74** (a guard whose declared roots stopped existing), ADR-014 §2, #211.

---

### C-22: No post-delivery correction process for wrong assignments — RESOLVED (procedure written; the partner-facing step is an open OPERATOR decision)

| Field | Value |
|-------|-------|
| ID | C-22 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S8 (#189)** — `docs/operations/correction_procedure.md`, written against the delivery that exists rather than the one #15 described in June (disk caches and shapefiles, both deleted with the runtime mapper).

**What it establishes.** Affected deliveries are identified by `run_id` and `lookup_version`, both present by construction — and `lookup_version` can no longer be the string `"unknown"`, because **C-60** made the reader raise instead of degrading. That is the dependency this story waited on: a procedure whose identification step rests on a field that can silently become a placeholder is not a procedure. Confirmation is offline against committed artifacts (`tests/test_gaul_lookup_fidelity.py`, 26 tests), so investigating does not change the thing being investigated.

**The wire mechanism is supersession, not retraction**, and the document says so plainly rather than inventing one: manifest-last commit ordering (ADR-013 §4) means a run is replaced by publishing a new complete run. It also states the consequence a reader would otherwise discover the hard way — views-faoapi selects **the newest manifest over a broad filter**, so a correction is picked up because it is *newer*, not because it is *correct*, and a test or partial correction published to the production bucket is indistinguishable from the real one. That is **C-73**, cited rather than re-solved, with **#133** named as the fix that would let a consumer select on intent.

Pinned by three checks in `tests/test_doc_accuracy.py`: the document exists and names the identification fields; it describes ADR-013 mechanisms and none of the deleted ones; and it still flags its undecided step.

**⚠ UPDATE 2026-08-02, later the same day — the operator answered the PRIO half; the FAO half is now formally asked.**

- **Who notifies:** **Simon Polichinel von der Maase**, by direct email, as soon as the scope of the error is established. Adopted.
- **Treatment of an affected delivery:** the intended policy is **withdrawal**. What is *implemented* is **supersession**, and the procedure now says so explicitly — supersession is in force because it is what the wire does, not because it was chosen. Withdrawal needs an ADR-013 amendment plus views-faoapi work, and whether that is worth building depends on FAO's answer about audit requirements.
- **Put to FAO** as **Pre-Release Note 07, Topic B** (Decision Points B.1 and B.2), which also records the interim defaults in force as placeholders rather than policy.

Recipients are deliberately **not in this repository**, which is public; naming a responsible person on our side is one thing, publishing an external organisation's individual email addresses is another. `tests/test_doc_accuracy.py` now refuses partner address strings anywhere in the repo, mutation-proven — and fired on the first draft of this very sentence, which spelled the pattern out. Third time in this epic that a guard has caught the prose explaining it (after S3's retired contract name and S5's ledger-schema docstring); the fix is the same each time — name the thing without spelling it.

The original residual, kept for the record:

**⚠ RESIDUAL — one step is written but NOT decided, and it is the step that reaches the partner.** Two questions belong to the operator (`CLAUDE.md`: anything touching an external party):

1. **Who contacts the UN FAO when a delivery is found wrong, through what channel, and how fast?** No named person, no address, no timing expectation. In practice it would be improvised by whoever noticed, under time pressure.
2. **Does FAO expect retraction or supersession?** Supersession is what the contract does. Retraction has **no wire mechanism** and would need an ADR-013 amendment plus agreement from views-faoapi. It is a question for them, not a decision for us.

The document states both verbatim and instructs the reader to stop and ask rather than improvise. **C-22 closes because the procedure now exists and says exactly where it stops**; what remains is a decision, not engineering. Registered as the standing gap rather than left as an open concern that would read as unfinished work.

`docs/CLONING.md` carries the same warning forward: a clone should answer its partner's correction questions **before** first delivery. This repo shipped run-0 on 2026-07-27 with that step undecided, and it still is. |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When any FAO/faoapi query surfaces a suspect delivered value — follow `docs/operations/correction_procedure.md`, **withdrawing first** via views-faoapi's quarantine before diagnosing. *(This row previously said "issue #15 must produce one first" and named #131 q1 as a precondition. #15 is CLOSED and superseded by the procedure; #131 closed 2026-07-31. The procedure exists — the trigger is now the incident, not the paperwork.)* |
| Location | `views_postprocessing/unfao/managers/unfao.py:442-494` (`_save_contract`), `:518-578` (legacy `_save`); issue #15 (the undocumented procedure) |

The delivery chain has four stages beyond the code: Appwrite bucket → UN FAO download → FAO systems → operational decisions. When an error is discovered post-delivery, correction requires clearing cache, re-running, re-uploading, notifying FAO, and FAO retracting old data. Steps 3-5 have no documented procedure.

Part of Cluster B (operational impact dimension). See also C-14 (RESOLVED — mapper-era cache), C-15.

**Update 2026-07-31 (review-rr — the conditional is spent):** this entry was written conditionally — "*if* wrong data ever reaches FAO." **Run-0 delivered on 2026-07-27** (108 arrow shards + sidecar + manifest to `unfao_bucket`, plus 28,356,996 historical rows at 64,742 cells). There is delivered data in the partner's store.

**Corrected 2026-08-03.** The paragraph above ended *"its integrity verification is still open (#131 q1) … still no documented correction/recall procedure … issue #15 is now the blocking artifact."* All three are spent: **#131 closed 2026-07-31**, the procedure landed as `docs/operations/correction_procedure.md`, and **#15 is closed and superseded by it**. What remains genuinely open is narrower and is in the procedure's §4: FAO has not yet answered who else to notify, in what period, and whether they want withdrawal or supersession (Pre-Release Note 07, Topic B).

---

### C-71: `appwrite_env.assert_env_declared` raises without logging — ADR-008 non-compliance in an entry-validation seam — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-71 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S1 (#182 / #193) on 2026-08-02 — and this entry then sat under Open for the rest of the day while eight further stories shipped.**

The fix is exactly what the entry predicted: `assert_env_declared` builds its message into a local, logs it at ERROR, then raises it. Verified — one `logger.error(err_msg)` call, and `tests/test_env_declaration.py::test_every_entry_validator_logs_before_it_raises` parametrises the ADR-008 obligation over **both** entry validators so the pair cannot drift apart again, which was the actual hazard: `launch_config` was written by mirroring this module, inherited the flaw, was fixed in review, and left its model as the odd one out.

**Why this was not caught, stated plainly rather than explained away.** S2 (#183) added exactly the guard for this class — an Open entry whose stated closing condition is already met. It did not fire here, because it matches two declarative phrasings (`closes when \`tests/…\`` and `Mitigation — landed`) and this entry's closing language is prose: *"It is a two-line change and the natural place to take it is S8."* That is the false negative S2 deliberately accepted — *"a guard that cries wolf gets deleted… false negatives are the accepted cost"* — and the cost came due within hours.

**The gap is process, not tooling, and widening the guard would be the wrong fix.** No regex reliably distinguishes "this entry describes work that is done" from prose. What went wrong is that #182 was closed without disposing of the entry it named in the same change. The generalisable rule — **a story that names a register entry disposes of it in the same PR** — belongs in S9's ADR question, alongside the CIC lagging three consecutive stories. Both are the same shape: a record updated by memory rather than by the change that invalidates it.

(The entry also pointed at **#156**, epic #148's closeout, which had already closed. A pointer to a finished story is how an item becomes nobody's.) |
| Tier | 4 — the raise is loud and its message is fully diagnostic, so nothing is silently swallowed today. What is missing is the persistent record ADR-008 requires, in the one seam whose whole job is to make a misconfigured launch visible. |
| Source | `review-diff` (2026-07-31) — S1/#149 review; found by mirroring this module when writing its sibling |
| Trigger | When a delivery run refuses on a missing Appwrite variable and the operator goes looking for *why* in the logs rather than the traceback — or when the next entry-validation module is written against this one as the pattern, as `unfao/launch_config.py` was |
| Location | `views_postprocessing/unfao/appwrite_env.py:44-51` (`assert_env_declared`) |

**ADR-008:48** requires that *"raised structural failures must be logged at `ERROR` level or higher"*, and **:51** that *"raising is not a substitute for logging."* `assert_env_declared` raises `EnvironmentError` naming every missing variable but never logs. A launcher misconfiguration is a structural failure by any reading of that ADR.

**How it was found, and why that matters:** `unfao/launch_config.py` (S1) was deliberately written to mirror this module — same shape, same failure style, same dependency-light constraint. It **inherited the flaw**, and the S1 diff review caught it in the new code. The new module was fixed to log-before-raise; this one was left alone for scope discipline, which means the pair is now **inconsistent** — the sibling written to match it no longer does.

Registered rather than fixed in #149 because it is pre-existing (shipped in þing-01 P1 / #134) and outside that story's boundary. It is a two-line change and the natural place to take it is **S8** (#156, epic closeout) or any PR that next touches `appwrite_env.py`.

Cross-refs: **C-19** (RESOLVED — the ADR-008 log-before-raise sweep whose convention this predates), **C-63** (the declaration-over-inference concern S1 closed), ADR-008, #134, #149, #156.

---

### C-74: The þing-01 redaction guard scans four paths that stopped existing — it reports success while covering one root of five — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-74 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S10 (#192).** The four roots that #153 orphaned now point at `contract/`, and the scan covers **17 files where it covered 6**. Verified 2026-08-02.

**The half that matters is the second one.** Re-pointing fixes today; `test_every_declared_credential_blind_root_exists` fixes the class. `rglob` on a nonexistent directory yields an empty iterator rather than raising, so a missing root and a clean root were indistinguishable — a package move silently emptied the scan while the suite stayed green. A declared path that does not exist is now an error, not silence. A third check bounds the count, so narrowing shows up as a number rather than as nothing.

Mutation-proven by restoring the pre-S10 roots: **two failures**, one naming all four missing paths, one reporting `covers only 6 files`. The guard was also proven to bite on the defect it was written for — a synthetic module reading `os.environ['APPWRITE_DATASTORE_API_KEY']` — which had never been demonstrated, and an unproven guard is what two silent days buys you.

**List, not derivation — decided and recorded.** `tests/test_clone_readiness.py` enumerates an overlapping module set for a *different* question ("does the machinery import without the partner?"). Folding them together would couple two guards whose sets are free to diverge: a module can be partner-neutral without being credential-blind. Two lists that each say what they mean beat one that means neither. What makes the explicit list safe is the existence assertion — without it, a list is exactly the fragile thing it looked like here.

**No leak occurred.** The relocated modules were checked directly at registration and again here: zero hits for `os.environ`, `getenv`, `load_dotenv`, `API_KEY`, `credentials`. The audited fact stayed true; what had gone was the thing that would notice it stopping. |
| Tier | 3 — **not a leak today**: the relocated modules were checked directly and are still credential-blind (zero hits for `os.environ`, `getenv`, `load_dotenv`, `API_KEY`, `credentials`). What is gone is the thing that would notice them ceasing to be. A security-adjacent control that cannot fail is a maintainability defect until the day it is a correctness one. |
| Source | `review-diff` (2026-08-02) — S1/#182 review; found while reading the redaction discipline the new ADR-008 test cites as "the wider rule" |
| Trigger | When any module under `contract/wire`, `contract/historical.py`, `contract/track_a_source.py` or `contract/frame_extraction.py` gains environment access — the #135 guard will not report it. Also fires on **the next package move**: `rglob` on a vanished root yields silence, not an error, so any future relocation narrows the scan again with no signal |
| Location | `tests/test_redaction_guard.py:25-31` (`_CREDENTIAL_BLIND`), `:34-39` (`_python_sources`) |

The þing-01 delivery-log redaction audit (#135, orð_09 §3) certified five module trees as credential-blind and pinned that finding as a permanent guard. Epic #148's S5 (#153) then moved the machinery out from under `unfao/` into `contract/`. **Four of the five roots were never re-pointed:**

| declared root | exists | files scanned |
|---|---|---|
| `unfao/wire` | no | 0 |
| `delivery` | yes | 6 |
| `unfao/historical.py` | no | 0 |
| `unfao/track_a_source.py` | no | 0 |
| `unfao/frame_extraction.py` | no | 0 |

**The failure is silent by construction.** `_python_sources` branches `if path.is_file(): … else: path.rglob("*.py")`, and `rglob` on a **nonexistent** directory yields an empty iterator rather than raising. A missing root and a clean root are therefore indistinguishable to the test, which passes either way. The guard reports an audited fact as pinned while pinning roughly a third of it.

**Why this is Cluster I and not merely a stale path.** The register's own text asserts the opposite. **C-57** says, in its "deliberately out of scope" paragraph, that *"the þing-01 redaction clause is **already mechanically enforced** (`tests/test_redaction_guard.py` — the delivery modules stay credential-blind…)"* — and **Cluster I's fix strategy cites this very file** as an example of the guard pattern working. Both were written in good faith and both are now overclaims. That is the cluster's disease reproducing inside the cluster's own prescription.

It is also the **sixth** instance of the stale-claim class found in two days, after C-63 and C-47 (filed Open with the defect fixed), C-43/C-59/C-61 (filed Open with their stated closing conditions met), #158 (closed with the code half undone) and `tests/test_validation.py` (claiming fidelity to a method it no longer resembles — **C-03**). The common shape is not carelessness: it is that a *move* leaves prose and paths behind, and nothing in this repo asserts that a declared path exists.

**Mitigation:** re-point the four roots at `contract/`, and add a root-existence assertion so a future relocation fails loudly instead of silently narrowing. The second half is the load-bearing one — re-pointing fixes today, asserting existence fixes the class. Tracked as a story under **epic #181**.

Cross-refs: **C-57** (whose "already mechanically enforced" claim this falsifies — corrected in place), **C-03** (the same class in `test_validation.py`), **C-46** (a different guard that also does not run, by a different mechanism), **C-63**, **C-47**, **Cluster I**, #135, #153, #182.

---

### C-46: `test_datafactory_deploy_readiness` is hardcoded to a local path — CI-skipped, and currently failing on the one machine that runs it — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-46 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S7 (#188).** Four sites resolved views-datafactory four different ways; one of them was `Path("/home/simon/Documents/scripts/views_platform/views-datafactory")`, so the repo's only cross-repo release gate had **never run anywhere but one laptop**. All four now go through one declared resolution — `$VIEWS_DATAFACTORY`, else the conventional directory beside this repo, never an absolute path to a particular machine.

| site | was |
|---|---|
| `tests/test_datafactory_deploy_readiness.py` | an absolute path to one developer's home directory |
| `tests/test_gaul_lookup_fidelity.py` | its own `_REPO.parent / "views-datafactory"` |
| `tests/test_delivery_coverage.py` | its own `parents[2] / …` (a fourth site, found while doing the work — the issue listed three) |
| `scripts/build_gaul_lookup.py` | the shape that was already right, kept |

Verified 2026-08-02: `grep -rn "/home/" tests/ scripts/ views_postprocessing/ --include=*.py` → **0**. With the sibling present the deploy gate runs (1 passed, 3 xfailed — its deliberately-tuned `xfail`s untouched); without it, 13 clean skips and no errors. Every skip names `VIEWS_DATAFACTORY` **and** the conventional path, so a contributor can run the test rather than watch it skip.

**The builder keeps its own resolver, deliberately.** A script must not import from `tests/` — that is the dependency direction backwards — and the contracts genuinely differ: the script returns a `Path` even when the checkout is absent so `main` can raise naming both the flag and the variable, while the test helper returns `None` because a missing sibling is a normal skip. WET before DRY: two copies that are understood beat one abstraction that is guessed. What is guarded instead is the property that actually matters — that they **agree** — because a builder writing from one checkout while the tests verify against another would report success on a lookup compared to a producer it was not built from.

**Residual, and the decision it needs.** These checks still do not run in CI. There are three such gated groups now — this deploy gate, the fidelity suite's producer-comparison half, and **C-57**'s registry-drift half — and the question should be answered once for all three rather than three times.

**Recommendation, for whoever takes it:** do **not** add sibling checkouts to the per-PR workflow. It couples this repo's CI to another repo's default branch, so an unrelated upstream commit turns this repo red — precisely the flapping `TestReleaseGate` already documents and was re-pinned for once. The always-on halves already guard the committed artifact; the gated halves answer *"is the producer's current state still consistent with ours?"*, which is a **scheduled** cross-repo question, not a merge gate. If it is wanted, the vehicle is a weekly workflow that opens an issue on divergence. **Named trigger:** the next time an upstream change reaches FAO through this repo without anyone noticing first. |
| Tier | 4 |
| Source | `repo-assimilation` (2026-06-27) |
| Trigger | When treating `test_datafactory_deploy_readiness` as a release gate (it never runs in CI), or when a contributor's local `pytest` fails on it — re-promote / re-pin the strict-xfail now that views-datafactory has advanced to `1.5.0`-dev past its `v1.4.0` tag |
| Location | `tests/test_datafactory_deploy_readiness.py` (`_DF = Path("/home/simon/.../views-datafactory")`, `skipif(not _DF.exists())`) |

The cross-repo deploy-readiness gates introduced under C-36 are guarded by `skipif` on a **hardcoded local datafactory checkout path**, so they are **skipped in CI** and only ever execute on one developer's machine. There, `test_version_bumped_past_latest_tag` is currently **failing**: it is an `xfail(strict)` that flipped to XPASS because datafactory moved to `1.5.0`-dev past its `v1.4.0` tag — exactly the auto-flip C-36's resolution anticipated, but because of the hardcoded path the flip surfaces as a **local red** rather than a CI signal, and breaks local `pytest` runs (the suite is run with this test deselected). No correctness/reliability impact on the delivery → **Tier 4** (test hygiene). C-36 (resolved) converted these gates to strict-xfail but did not capture the local-path / CI-skip dimension.

See also C-36 (the resolved strict-xfail conversion this extends), C-44 (the datafactory version-state coupling).

**Was tagged `[backlog]` at review-rr (2026-07-31)** — Tier 4, single-machine scope, mechanical fix — and kept for completeness rather than active risk management. The tag was dropped when S7 resolved it. Worth noting for the convention itself: a `[backlog]` entry is deprioritised, not dormant, and this one turned out to be blocking three gated cross-repo checks from running anywhere but one machine.

---

---

### C-57: PLATFORM-001 coordinate registry is referenced by URL, so nothing detects drift between it and this repo's declared environment — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-57 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S6 (#187).** The registry stays **referenced, never copied** — that was always the right call. What C-57 named was the gap it left: nothing mechanical could tell you the two had diverged. There is now a detector, built while the answer was known-good rather than after a failed delivery.

`appwrite_env` declares the edition it was verified against — `SEAM_CONTRACT_VERSION = "1.3.0"` and `SEAM_CONTRACT_COMMIT = "47172af"`. **A version string and a sha are not coordinate values**; what is recorded is *which edition was read*, which is precisely what makes drift detectable. Four checks in `tests/test_env_declaration.py`, each mutation-proven:

| check | mutation | result |
|---|---|---|
| every declared name exists, with the class the **registry declares** (never inferred from a prefix) | rename `APPWRITE_UNFAO_BUCKET_ID` here | 4 failures |
| the registry's `[meta] version` matches the pin | pretend v1.2.0 | 1 failure, naming the version to re-verify against |
| the pinned commit is **reachable from views-appwrite's `main`** | pin the withdrawn `b54928f` | 1 failure |
| no coordinate value is baked into a constant or default | add `UNFAO_BUCKET = "unfao_bucket"` | 1 failure |

**The reachability check exists because existence was not enough.** #196: S3 pinned a commit resolved with `rev-parse HEAD` on a checkout sitting on an unmerged branch. The commit existed, both cited files existed at it, every check anyone had written passed — and it had never reached `main`, declared a version never ratified, and was withdrawn. A pin is a claim about what the contract *says*; only reachability supports that claim.

**The value-copy check took two wrong narrowings before the right one, and both are worth recording.** A substring text scan flagged three "leaks": `file_metadata` (a **function name** in `contract/store_metadata.py`), `production_forecasts` and `unfao_bucket` (only in refusal labels and docstrings naming which store a function serves). None was a copy, and a guard that fails on `def file_metadata(record)` gets deleted — after which the real rule is unguarded.

Narrowing to *assignments and default arguments* then failed the other way: it caught neither a dict value nor a keyword argument, and the keyword argument is the shape this repo would actually produce — `AppwriteConfig(bucket_id=os.getenv(...))` is how every store is configured, and swapping one `os.getenv` for a literal there is the violation. Verified: that draft caught **zero** of the two.

The right axis was **exact equality on string constants**, not statement shape. It catches dict values, keyword arguments and constants alike, while all three original false positives fall out on their own: a function name is not a `Constant`; `"unfao_bucket datastore"` is not equal to `"unfao_bucket"`; docstrings are excluded outright. The lesson is narrow and reusable: **when a guard cries wolf, check whether the matching is wrong before assuming the scope is.**

**Gated, and honestly so.** The checks need a views-appwrite checkout and skip without one, naming `VIEWS_APPWRITE` and the conventional sibling path so a contributor can run them rather than merely watch them skip. The would-catch-a-rename proof runs in CI with no checkout at all. Resolution helper shared with **C-46** (S7) in `tests/conftest.py` — the second incident, which is this repo's named trigger for extracting.

**Residual — now tracked as C-81.** The gated half does not run in CI, which needs a views-appwrite checkout in the workflow. That was recorded here and in **C-46** as *"a CI-cost and cross-repo-coupling decision, not a code fix … worth deciding once for both"*, and it sat as a residual on two RESOLVED entries, which is where residuals go to be forgotten. It now has a live entry with a measured cost (17 tests, 9 of them new in this arc), a per-sibling answer, and an owner: **C-81**. views-appwrite is private, so it needs a token — an operator decision.

A second, smaller instance of the same shape: these checks parse TOML with `tomllib`, stdlib from Python 3.11, and `pyproject` declares `>=3.11`. CI runs 3.11 and executes them. The maintainer's box runs **3.10**, below the declared floor, so they skip there — the local suite is quietly weaker than a green `pytest -q` suggests. Not a repo defect and not worth its own entry; recorded because "a gate that does not run" is exactly what C-46 is open for, and the CI decision should cover both. |
| Tier | 3 |
| Source | `manual` (2026-07-31) — review-rr blind-spot analysis, following the þing-01 verdict (`orð_dómr.md`, ratified as amended 2026-07-28) |
| Trigger | When views-appwrite amends `coordinate_registry.toml` — renames a coordinate, retires the legacy secret slot in favour of `APPWRITE_{READ,WRITE,PROVISION}_API_KEY`, or adds a target — verify `views_postprocessing/unfao/appwrite_env.py` still matches. Nothing mechanical will tell you: the registry is deliberately **referenced, never copied**, and the two live in different repositories |
| Location | `views_postprocessing/unfao/appwrite_env.py` (`CONNECTION_ENV`, `PROD_FORECASTS_ENV`, `UNFAO_ENV`) and `views_postprocessing/crafd/appwrite_env.py` (`CRAFD_ENV`) — see the 2026-08-03 amendment; views-appwrite `docs/ADRs/platform/coordinate_registry.toml` (the authority); `tests/test_env_declaration.py` (guards this repo's half only); `docs/ADRs/013_sampled_forecast_wire_contract.md` §7(d) (the URL reference) |

The þing-01 assembly (D1) settled that the PLATFORM-001 contract is **homed in views-appwrite and referenced by URL, never by copy** — a deliberate and correct choice: copies were the platform's original disease (sáttmál S6, the copy-chain this repo's own `load_dotenv` borrow was the runtime edge of, killed in #134/PR #137). But referencing-not-copying moves the failure mode rather than removing it: **the registry can now change without this repo noticing.**

This repo's half is well guarded. `tests/test_env_declaration.py` pins that every `APPWRITE_*` name the manager reads is declared, that all three store paths validate before constructing an `AppwriteConfig`, that empty-string counts as missing, and that exactly one declared name is a secret by the D3 suffix rule. **What no test can see is the other side of the reference** — whether `coordinate_registry.toml` still spells the coordinates the way `appwrite_env.py` does. Divergence surfaces at runtime as a fail-loud `EnvironmentError` from `assert_env_declared` (good — that is D6 working), but only on a delivery run, and only after the launcher has already been reconfigured.

Two named changes are already anticipated and will fire this trigger: the **retirement of the legacy `APPWRITE_DATASTORE_API_KEY`** in favour of the three-tier read/write/provision slots (D4), and any target-coordinate addition for the second store (issue #97). Tier 3 — coordination and cost-of-change across a repo boundary; the failure is loud, not silent, and D6's entry validation is the backstop that keeps it that way.

**Deliberately out of scope here:** the þing-01 redaction clause is mechanically enforced (`tests/test_redaction_guard.py` — the delivery modules stay credential-blind and the provenance description is a closed keyset), and D2's ruling that **integration tests against the production Appwrite project are FORBIDDEN** (no non-production project exists) is a standing prohibition, not a drift risk.

**⚠ CORRECTED 2026-08-02, then restored the same day.** The word *already* above overclaimed at the time: **C-74** showed that guard scanning one of its five declared roots, four having pointed at paths #153 moved. **C-74 closed later that day (S10 / #192)** — the roots are re-pointed, the scan covers 17 files, and a declared root that does not exist now fails rather than emptying the scan silently. The sentence above is true again, and the episode is left visible because a claim that was false for two days is worth more as a record than as a correction quietly reverted.

**⚠ AMENDED 2026-08-03 (PR #211) — the detector was built for one partner, and the second partner proved it.** Two corrections to the resolution above, and one of them is the same disease in the cure.

1. **The pin quoted above is stale.** `SEAM_CONTRACT_VERSION = "1.3.0"` / `SEAM_CONTRACT_COMMIT = "47172af"` was accurate when written on 2026-08-02; the registry then moved twice in under twelve hours — to v1.4.0 (`4a5ab1b`, reaching `main` as `20dfd0f`, 2026-08-02 18:45) and to v1.4.1 (`0da2682`, reaching `main` as `5266b90`, 2026-08-03 02:52) — and `unfao/appwrite_env.py` was re-pinned each time. This repo's current pin, `90fc105`, is **neither** of those commits: it is a later views-appwrite merge that does not touch the registry at all. That is correct and intended — a pin names *an edition of `main` that was read*, not the commit that changed the file — but the two must not be written as though they were the same thing. The values are left above as the worked example they were written to be, but they are no longer what the file says.
2. **The detector was scoped to `unfao` by name and did not follow the second partner.** `tests/test_env_declaration.py` imported only `views_postprocessing.unfao.appwrite_env`; a grep for `crafd` in it returned zero. So when PR #211 added `views_postprocessing/crafd/appwrite_env.py` pinned at **`1.3.0` / `47172af`** — an edition at which all four `APPWRITE_CRAFD_*` coordinates were declared with **no value**, and which predates the very views-appwrite PR #38 that the file's own docstring cites as its justification — **nothing failed.** Had this entry's own **version** check covered crafd, that pin would have failed **locally** the moment it was written. Not CI: the check opens with `require_sibling("views-appwrite")` and skips without a checkout, and the workflow checks out only this repository — which is this entry's own standing Residual, below. Note which half does the work: the *reachability* check would have passed, because `47172af` is a perfectly good ancestor of views-appwrite's `main`. Existence and reachability were both satisfied by a pin that was nonetheless two editions out of date — which is precisely why the version check exists alongside them rather than instead of them.

This is ADR-014 §2 in its narrow form: a guard's *scope* is part of what has to be mutation-proven, not just its matching. The four checks were each proven to fail on the defect they were written for, against `unfao` — and stayed silent on an identical defect one package over. Same shape as **C-74**, one layer up: there the declared scan roots stopped existing; here the declared scope never grew.

PR #211 re-pins crafd to `1.4.1` / `90fc105` and parameterises **three** of the four checks over both partner declarations — names-and-class, pinned edition, commit reachability. The fourth, the value-copy scan, was never partner-scoped: it walks `_PKG.rglob("*.py")` and so covered `crafd/` from the day it landed. A third partner is now a one-line addition, and an unguarded one is a failure. This entry stays RESOLVED — the mechanism was right, its reach was not — but the residual below now has a companion: a detector that names its subject is a detector that will miss the next subject.

Cross-refs: C-74 (the guard this paragraph vouched for), C-33 (store identity still hardcoded per store — the same env surface, different concern), C-58 (what happens when a coordinate is wrong rather than missing), C-44 (the pipeline-core version coupling that would carry a registry change), issues #134/#135/#138 (this repo's discharged þing-01 obligations), #104 (README env block placeholders).

---

---

### C-60: The lookup provenance stamp reaches into the producer's ledger schema and degrades to `"unknown"` on a bare except — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-60 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S5 (#186).** The builder composes the stamp and writes one flat `lookup_version` key; `contract/gaul_lookup.version` reads that key and **raises** `LookupVersionError` (logged first, ADR-008) when it is absent. The three-level traversal of views-datafactory's ledger shape, the bare `except … pass` and the `"unknown"` branch are all gone — pinned by `tests/test_gaul_lookup_access.py`, which asserts by **AST** rather than by word-matching that the module imports no `json` and holds zero exception handlers. An untraceable *build* now fails at build time, where a human is present, instead of surfacing as a placeholder in production.

**The committed artifact was rebuilt, metadata-only.** 64,742 rows, column order and dtypes unchanged, a content hash over every column's values identical, and the stamp resolves to `land_gaul@f74d3b2b` — the same string the old traversal produced, so no delivered provenance changes meaning. ADR-013 untouched: `contract_version` 1.5, `tests/fixtures/` byte-identical (`build_sidecar` constructs a fresh table, so lookup metadata cannot reach the wire — verified empirically, sidecar schema metadata is `[]`).

**⚠ The fix reintroduced this entry's own defect class, caught in review before merge.** The first draft read `provenance.get("land_gaul_region") or provenance.get("gaul_admin_area_majority")`. Since `_provenance` takes no region, `land_gaul_region` is present for *every* build — so `--region all` would have been stamped `all@f74d3b2b`, the land_gaul region definition's digest, on a global artifact: authoritative-looking, wrong, silent. Replaced by a declared `stamp_dataset(region)` with no fallback; a region whose ledger entry is absent is **refused**, not substituted. Verified: `all@272cdb01`, `land_gaul@f74d3b2b`, `africa_me_legacy` → raises. Worth keeping visible — the reflex that produced C-60 reappeared while fixing C-60.

**Residual, deliberately deferred:** stamping `lookup_version` into the **sidecar's own** parquet metadata, so a delivered artifact is self-describing without the store document. Not done here because it changes wire bytes and therefore `contract_version` — an ADR-013 amendment with three repos to notify. Named trigger: **the next ADR-013 version bump**, whatever prompts it.

**Also recorded from review:** the ingestion ledger is append-only and the **last entry per dataset wins** (14 `gaul_admin_area_majority` entries, 2 `land_gaul_region`). Harmless while provenance was decorative; load-bearing now that the stamp raises, so it is stated in `_provenance` rather than left implicit — the same shape **C-73** was opened for on the forecast path, intended here and now said. `docs/CICs/GaulLookupEnricher.md` still documented the `"unknown"` degrade and was corrected. |
| Tier | 3 |
| Source | `expert-code-review` (2026-07-31) — Ousterhout lens (information leakage / silent degradation) |
| Trigger | When views-datafactory renames or restructures its ingestion-ledger entries (`dataset` key, `content_digest` field, or the `land_gaul_region` entry name) — verify `lookup_version` still resolves to a real value rather than the string `"unknown"`; nothing fails if it does not |
| Location | `views_postprocessing/unfao/enrichment.py:61-79` (`_read_version`); written at `scripts/build_gaul_lookup.py:89-107` (`_provenance`) and `:163-164`; consumed as the C-15 provenance field via the manager's delivery description |

`_read_version` reconstructs the stamp by traversing three levels of the producer's schema — parquet metadata → `source_provenance` JSON → `land_gaul_region` → `content_digest` — and wraps the traversal in `except (ValueError, AttributeError): pass`, returning `"unknown"` when anything along the path is absent. This is a **declare-don't-infer violation at the consumer**: the value that ties a delivered artifact to the exact lookup build (C-15's traceability provenance) can silently become a placeholder, and no gate notices.

No wrong data results — this is a traceability failure, not a correctness one → **Tier 3**. But it defeats the specific question C-15 exists to answer *after* a suspect delivery ("which lookup produced this?"), and C-22 has no correction procedure that could compensate.

**Mitigation:** have `build_gaul_lookup.py` write a **flat, declared `lookup_version` key** into the parquet metadata, and have `_read_version` read that one key and **raise** if absent. The consumer stops knowing the producer's nested ledger schema, and the stamp stops being able to vanish quietly. Separately worth stamping `lookup_version` into the sidecar's own parquet metadata so a delivered artifact is self-describing without the store document.

Cross-refs: C-15 (the provenance this field serves), C-22 (the recall process that would need it), C-57 (the same class — a cross-repo fact this repo reads without a way to detect drift), **Cluster K**.

---

---

### C-03: Test coverage gaps in manager validation and the enrich→validate path — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-03 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by S4 (#185): one of its two residuals is gone, the other is relocated to a tracker that already exists.**

**Residual 1 — the `_validate()` replica — REMOVED.** `tests/test_validation.py` defined its own `validate_dataframe` and then tested *that*: forty-odd parametrised cases exercising a function declared twelve lines above them and **no production code at all**. A closed loop that could not fail while the delivery broke. Its header claimed *"the logic tested matches unfao.py:_validate() exactly"* — false since **#149**, which stopped `_validate` null-gating entirely (its docstring now says *"Neither payload is null-gated here"*). It also carried `REQUIRED_METADATA_COLS` as a nine-element literal, a hand copy of the contract **C-70** was resolved to make single-source.

Replaced by tests of `contract/historical.assert_metadata_complete` — the code that actually gates a delivery — parametrised over the **imported** `METADATA_COLS`, plus source-scan pins that the gate stays at build time and is still invoked. Verified 2026-08-02: `pytest -q tests/test_validation.py` → **14 passed**. Mutation-tested: narrowing the gate to a single column fails **9 of 14**; the old suite passed that mutation untouched, because it was not testing the gate.

**Residual 2 — the enrich→validate end-to-end test — RELOCATED to #18**, per the Register Conventions' relocation rule (a relocation is not complete until the destination exists and is cited by number). Every *leg* is now covered — enrichment (`test_enrichment.py`, 16), artifact build (`test_historical_builder.py`, 7), reader parity (`test_historical_parity.py`, 3), the invariants on primitives (`test_input_integrity_e2e.py`, 8), the wire end to end (`test_hop_b_sink_e2e.py`, 6), the null-gate (`test_validation.py`, 14). What remains uncovered is **the manager orchestrating them**, which needs views-pipeline-core and a production-like Appwrite environment — and þing-02 **D2** forbids integration tests against the production project, no non-production one existing.

That gap has **two standing trackers already**, which is why keeping a third here is noise rather than signal: issue **#18** (open since 2026-06-04) and `tests/test_falsification_campaign_3_5.py`, an `xfail(strict)` probe that **flips to XPASS the moment someone writes the test** — a self-surfacing tracker, which is more than this entry was doing. |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02), `test-review` (2026-06-02) |
| Trigger | When modifying the manager's `_validate()` or the enricher, verify that the test suite covers the changed behavior — end-to-end coverage across the enrich→validate path is still absent |
| Location | `tests/test_validation.py`, `views_postprocessing/unfao/managers/unfao.py` |

Initial state was zero test coverage. A 73-test suite was written (2026-06-02) covering the (now-deleted) mapper's core guarantees and the validation logic (missing columns, null rejection, error messages). Remaining gaps after the mapper removal: (1) the validation tests replicate `_validate()` logic in a standalone function because `views-pipeline-core` is unavailable in test environments — if the real `_validate()` diverges, tests pass while production fails; (2) no end-to-end test enriches through `GaulLookupEnricher` then validates through the manager.

Tier recalibrated from 2 to 3 during review-rr (2026-06-02): the gap is maintainability (test-code divergence, missing integration path), not structural fragility.

**Update 2026-06-24:** narrowed with the mapper deletion (C-39, PR #42). The mapper-coverage dimension is gone with the mapper (`tests/test_mapping.py` deleted; the determinism/cache/shapefile/`ThreadPoolExecutor` gaps no longer exist). Two manager-side gaps remain: the standalone `_validate()` replica and the missing enrich→validate end-to-end test.

---

---

### C-43: ADR-011 enrichment swap shipped without its output-equivalence proof — and the proof is now unrecoverable — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-43 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by `tests/test_gaul_lookup_fidelity.py` (18 tests, committed in #141) — which is precisely what this entry named as its own closing condition:** *"C-43 closes when `tests/test_gaul_lookup_fidelity.py` is committed and green — the entry should then cite the test, not the session."* It now cites the test. Verified 2026-08-02: `pytest -q tests/test_gaul_lookup_fidelity.py` → **18 passed**. The residual this entry stayed open over — that the forward-check was a one-off session result rather than a standing guarantee — is discharged: the always-on half pins gid uniqueness, region-set equality, the coordinate formula and the absence of nulls and `-1` sentinels against the committed artifact, and the datafactory-gated half compares all seven GAUL columns against the producer's parquets. **Scope is unchanged and load-bearing — see the SCOPE paragraph below.** This closes **transcription fidelity**, not **assignment correctness**; the latter is views-datafactory#387 and is not this repo's to close. The entry sat under Open with its own stated condition met — the drift class that prompted S2 (#183) to make closing conditions machine-checkable. **Cluster K.** |
| Tier | 2 |
| Source | `manual` (2026-06-26) — user-flagged rigor loss on accepting option A; verified against git history (`eba1df8` / PR #42) |
| Trigger | **This trigger has FIRED — see the 2026-07-31 update.** Forward-looking replacement: when FAO or faoapi reports geographic metadata that looks wrong for specific cells, **or** before the next global delivery — forward-check a sample of `land_gaul` assignments against views-datafactory's GAUL parquet. The protective pre-go-global gate this entry originally described has passed. |
| Location | `views_postprocessing/unfao/enrichment.py` (`GaulLookupEnricher`); `views_postprocessing/unfao/managers/unfao.py:129` (`_append_metadata`), `:147-172` (`_validate` — the 9-column NULL gate, checks presence not correctness); umbrella #20 / issues #21, #23, #24 (the baseline+diff procedure, now unrunnable); deleted in `eba1df8` (PR #42): `mapping.py` + both ADR-011 diff scripts |

ADR-011 swapped FAO geo-enrichment from the runtime geopandas mapper to the GAUL lookup enricher (commit `65635b6`). The swap's own plan (umbrella #20) required an **output-equivalence proof** before trusting it in production: Stage 0 (#21) run the OLD mapper on real `africa_me_legacy` data to archive a ground-truth baseline; Stage 2 (#23) diff the new enricher against it with *"zero unexplained differences."* That proof was **never produced** — no `baseline_schema.md` or baseline parquet was ever committed — and on 2026-06-24 the old mapper **and both diff scripts** were deleted (`eba1df8`, PR #42, C-39). So the equivalence check is now **unrecoverable** short of `git revert`-ing the mapper back.

The accepted path forward (**option A**) is a single smoke-test delivery: "the run is green and the output looks sane," which proves the path *runs*, not that it produces the *same / correct* values the trusted mapper did. The manager's `_validate` enforces only that the 9 GAUL columns are **non-null** — it does not check value correctness — so a latent bug in the lookup build or the merge-by-gid (wrong join key, stale `lookup_version`, gid misalignment) would ship **wrong-but-non-null** geographic metadata to FAO with **no error signal**.

**Why not Tier 1:** the lookup is built from views-datafactory's authoritative area-majority GAUL parquets — the canonical *producer* source (D-07). The new path sources from the gold standard; the old mapper was the *less*-trusted path being retired (C-31, C-23). So the missing diff is a lost cross-check, not "unverified code," and the Stage-1 enricher unit tests + coverage guards (C-30/C-34) cover part of the build. **Why Tier 2:** the residual silent-wrong-value path is real, the null gate cannot catch it, the one guard that would have is gone for good, and the trigger (go-global to 64k cells) is concrete and imminent.

**Mitigation if assurance is wanted before go-global** (cheaper than reverting the mapper): forward-check a sample of `land_gaul` cell assignments directly against the datafactory GAUL parquet, or add a lightweight value-level assertion into the enricher path (a forward check against the producer source — *not* a resurrection of the deleted old-mapper diff).

**TRIGGER FIRED 2026-07-27 — the risk changed tense (review-rr 2026-07-31).** Run-0 delivered the first FAO global-land forecast: `region=land_gaul`, 64,742 cells, 28,356,996 historical rows, 108 arrow shards + sidecar + manifest committed to `unfao_bucket`. The go-global run this entry was written to warn about **has happened**, and it happened with **no value-level equivalence check** — exactly as predicted. The concern is therefore no longer "risk of shipping unverified enrichment" but **"unverified enrichment has shipped, at global scale, and the forward-check is outstanding."**

This is the most important consequence of the run-0 cluster (Cluster H). Run-0 discharged the *availability* half of the go-global debt — the path runs, memory is bounded (C-32: 5.6 GB), coverage is proven (C-30: 64,742 correct). It discharged **none of the correctness half**, because proving the path *runs* at scale was never what C-43 asked for. **This entry now stands alone and un-gated**, with delivered data in the partner store and `_validate`'s null gate still checking presence rather than value. Tier held at 2: the lookup is still built from views-datafactory's authoritative area-majority parquets (the gold-standard producer), which is why this is a lost cross-check rather than unverified code.

**Recommended action (unchanged, now overdue rather than pre-emptive):** forward-check a sample of delivered `land_gaul` cell assignments directly against the datafactory GAUL parquet — cheap, and it is the mitigation this entry proposed from the start. Folds naturally into #131 q1 (run-0 delivery-integrity verification).

---

**TRANSCRIPTION FIDELITY DISCHARGED 2026-07-31 (`expert-code-review`) — the forward-check was run, offline, against committed artifacts. Four checks, zero mismatches:**

| Link in the chain | Ground truth | Result |
|---|---|---|
| Coordinate formula (`gaul_schema.xcoord`/`ycoord`) | views-datafactory `data/raw/priogrid/shapefile/priogrid_cell.dbf` — **all 259,200 cells** | **max abs error 0.00e+00**, 0 mismatches |
| Lookup values, all 7 GAUL columns | the 7 `data/raw/gaul_admin/*.parquet` | **0 mismatches** across 64,742 cells |
| Lookup gid set + key uniqueness | `src/datafactory_query/land_gaul_pgids.json` | **exactly equal**; 64,742 unique of 64,742 |
| **The delivered run-0 sidecar** (`rusty_bucket_forecasting_20260727_095355__sidecar.parquet` — the real bytes on FAO's shelf) | the lookup | **0 mismatches** on all 9 columns; SHA-256 matches the manifest's declaration |

The chain producer → lookup → delivered bytes is verified end to end. Note the leading hypothesis going in — that the gid→lat/lon formula might be flipped or off-by-one, producing wrong-but-non-null coordinates on *every* cell, invisible to every existing gate — was **falsified**: the formula is exact for the entire global grid.

**SCOPE — what this does and does not prove** (the Kleppmann-vs-Nygard split in the 2026-07-31 review, adjudicated to *both, scoped*)**.** It proves **transcription fidelity**: this repo faithfully carries the producer's area-majority GAUL assignment through to the partner. It does **not** prove **assignment correctness** — if views-datafactory's area-majority join puts a cell in the wrong country, every check above still passes and FAO still receives a confidently wrong label. That is a separate concern belonging to **views-datafactory** — the degree-based (square-degree) area math its area-majority join uses, which distorts by up to ~2× at 60°N and could flip the winning polygon for high-latitude border cells now that the region is global. This distinction must survive retelling: C-43 was registered as *a lost old-vs-new cross-check inside this repo*, and that is what has been discharged.

**⚠ CORRECTION, same day (2026-07-31).** This paragraph originally asserted the upstream half was *"a separate, already-registered concern (C-08, relocated to views-datafactory)."* **That was false and is corrected here.** Verified by direct inspection: views-datafactory's register carries 32 concerns and mentions "area-majority" nine times, but has **no entry** for the degree-based area calculation. C-08 was resolved *here* on 2026-06-24 with the note *"Tracked there, not here"* — and nobody ever opened it there. **The concern has been untracked platform-wide since that date**, and run-0 shipped the affected high-latitude cells to FAO on 2026-07-27.

Filed upstream as **views-platform/views-datafactory#387** so it is tracked where the code and the geopandas toolchain actually live. This repo cannot verify it: the forward-check above confirms faithful *transcription* of the producer's answer and is structurally incapable of judging whether that answer is right.

This is a textbook instance of **C-42**'s registered hazard (acting on a mis-stated cross-repo state) and of **Cluster I** — and it was reproduced *while writing the very paragraph describing it*. Concrete lesson for the "relocated" convention added to the Register Conventions this same day: **relocation is not complete until the destination issue or entry exists and is cited by number.** A relocation note naming only a repo is an assumption, not a handoff.

**Residual (why this entry stays open):** the verification was a one-off session result, not a standing guarantee. Nothing in CI re-runs it, so a future lookup rebuild against a wrong or stale datafactory would ship silently exactly as before. **C-43 closes when `tests/test_gaul_lookup_fidelity.py` is committed and green** — the entry should then cite the test, not the session. Tracked as **Cluster K**; the same test discharges C-59 and C-61.

See also C-03 (the sibling enrich→validate test-coverage gap — RESOLVED 2026-08-02; its manager-orchestration residual relocated to #18), C-22 (no post-delivery correction/recall process — **now acute: the consequence path is live**), C-39 / C-31 / C-23 (the resolved mapper-deletion cluster this emerged from), C-30 (coverage — discharged by the same run that left this standing), C-32 / C-34 (RESOLVED — the go-global scale risks that fired cleanly), D-08 (the swap-to-lookup-first decision whose verification debt this is), #131 (run-0 delivery-integrity verification).

---

---

### C-59: The GAUL lookup build asserts no key uniqueness — a duplicate gid silently inflates the legacy delivery — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-59 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by the mitigation this entry already recorded as landed; nothing was outstanding, the entry simply never moved.** Verified 2026-08-02: `scripts/build_gaul_lookup.py` carries **zero** bare `assert` statements and raises an explicit `LookupBuildError` on a non-unique index, and both named guards exist and pass — `tests/test_gaul_lookup_fidelity.py::test_builder_rejects_a_duplicate_gid` (the builder refuses a duplicate) and `::test_lookup_key_is_unique` (the committed artifact is clean). The Tier 2→3 recalibration recorded below stands: the production `--region land_gaul` path de-duplicates before the guard is reached, so the explicit raise protects the `--region all` path and refuses to absorb a producer defect silently. **Cluster K.** |
| Tier | 3 — **recalibrated from 2 the same day, see the correction below.** A duplicated key would multiply rows through the legacy pandas merge invisibly to every gate, but reaching the artifact requires `--region all`: the production `--region land_gaul` path de-duplicates first. Unguarded fragility on a non-default code path, not present corruption. |
| Source | `expert-code-review` (2026-07-31) — Kleppmann lens; verified empirically in the same pass |
| Trigger | When views-datafactory regenerates the `gaul_admin` parquets, or when `build_gaul_lookup.py` is re-run against a new datafactory version — verify the resulting lookup index is unique before committing the artifact; nothing checks it today |
| Location | `scripts/build_gaul_lookup.py:146-154` (the invariant block, which checks nulls and `-1` but never uniqueness); consumed at `views_postprocessing/unfao/enrichment.py:117` (pandas left-merge — the inflating path), `unfao/historical.py:60` and `unfao/wire/sidecar.py:56` (deterministic-pick paths) |

`build(...)` sets `df.index = df.index.astype("int64")`, names it `priogrid_gid`, sorts, and then asserts only that no nulls and no `-1` sentinels survive. It never asserts `df.index.is_unique`. The seven source parquets are joined via `pd.DataFrame({...})` over gid-indexed Series (`build_gaul_lookup.py:59-73`), so uniqueness is inherited from upstream data rather than enforced here.

Downstream, `GaulLookupEnricher.enrich_dataframe_with_pg_info` does `base.merge(self._lookup, left_on=pg_id_col, right_index=True, how="left")`. A duplicated key produces **N rows per affected cell**. The delivery then carries more rows than cells, with every metadata value present and correct — invisible to the null gate, invisible to the distinct-cell coverage gate, and invisible to the `country_iso_a3` proxy at `enrichment.py:122`.

**⚠ TIER RECALIBRATED 2 → 3, same day (2026-07-31), on empirical evidence.** Registering this at Tier 2 assumed a duplicate could reach the committed artifact through the normal build. Mutation-testing the builder showed it cannot, on the production path: `build()` applies `src.loc[src.index.intersection(sorted(region_gids))]` (`build_gaul_lookup.py:114-116`), and pandas' `Index.intersection` **de-duplicates**, so an injected duplicate is silently removed before the invariant block ever sees it. The guard is reachable only with `--region all`, which bypasses that filter — verified: it raises there, and raises under `python -O` too.

Two consequences, both kept: the explicit raise still earns its place, because the de-duplication is an *accidental pandas behaviour* rather than a declared guard (and silently absorbing upstream duplication is itself undesirable — it hides a producer defect); and the tier drops to 3, because the realistic exposure is a non-default flag, not routine regeneration. *Recalibrated during the same session that registered it — the original Tier 2 rationale was written from code reading before the mutation test was run.*

**Mitigation — landed 2026-07-31:** explicit `LookupBuildError` on a non-unique index in `build_gaul_lookup.py` (not `assert`, per C-61), pinned by `tests/test_gaul_lookup_fidelity.py::test_builder_rejects_a_duplicate_gid`, plus a standing uniqueness check on the committed artifact (`test_lookup_key_is_unique`).

Cross-refs: C-43 (the value-correctness debt this shares a fix with), C-61 (the same invariant block's strippable asserts), C-30 (the distinct-cell coverage gate that cannot see this), C-40 (the legacy pandas path whose deletion would remove the inflating consumer), **Cluster K**.

---

---

### C-61: The lookup build's hard invariants are bare `assert`s — stripped under `python -O`, and `-1` sentinels are caught nowhere else — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-61 |
| Resolved | 2026-08-02 |
| Resolution | **Closed by the mitigation this entry already recorded as landed; nothing was outstanding, the entry simply never moved.** Verified 2026-08-02: all three invariants in `scripts/build_gaul_lookup.py` are explicit `LookupBuildError` raises, which `python -O` cannot strip, and both named guards pass — `tests/test_gaul_lookup_fidelity.py::test_a_sentinel_code_is_dropped_rather_than_shipped` (the cell is excluded, so it later fails loud as *absent* rather than shipping wrong-but-non-null) and `::test_lookup_carries_no_sentinel_codes` (the committed artifact). The deliberate non-test of the `-1` raise stands as recorded: reaching it requires stubbing pandas internals, and a test that fragile is worse than the invariant it guards. **Cluster K.** |
| Tier | 3 |
| Source | `expert-code-review` (2026-07-31) — Feathers lens |
| Trigger | When `build_gaul_lookup.py` is run under `python -O` (or from a wheel/CI step that sets `PYTHONOPTIMIZE`), or when the build is wrapped in any tooling that optimizes bytecode — verify the invariant block still executed; a stripped run writes an unvalidated lookup that looks identical |
| Location | `scripts/build_gaul_lookup.py:152-154` (`assert df.isna().sum().sum() == 0`, `assert (df[c] != -1).all()`) |

The builder's docstring and the enricher both rely on the lookup being "clean by construction" — no nulls, no `-1` sentinels. That guarantee is enforced by three bare `assert` statements, which Python removes entirely under `-O`.

The asymmetry the original registration leaned on: **nulls have a downstream backstop** (`_validate`, `historical.assert_metadata_complete`) but **`-1` codes have none** — `-1` is non-null, so it would pass every delivery gate, which is the resolved **C-35** defect (invalid country codes shipped to FAO for Somaliland cells) returning through a different door.

**⚠ EXPOSURE CORRECTED, same day (2026-07-31), on empirical evidence.** That framing overstated the risk. Mutation-testing the builder showed the **primary protection against `-1` is not the `assert` at all** — it is the completeness filter at `build_gaul_lookup.py:125-131` (`complete &= df[c].notna() & (df[c] != -1)`), which drops sentinel rows outright. That filter is **plain code, untouched by `python -O`**, so the strippable-assert exposure never applied to the `-1` case. In practice the `assert` was unreachable: no ordinary input can get past the filter to reach it.

What remains true, and why the entry stays open at Tier 3: the invariant block was the only *explicit statement* of "this artifact is clean," it was strippable, and the same block also carried the null and (now) uniqueness checks where the argument does bite. Stating invariants in a form the interpreter can delete is the defect; the `-1` severity was not.

**Mitigation — landed 2026-07-31:** all three invariants converted from bare `assert` to explicit `LookupBuildError` raises with diagnostic messages. The `-1` raise is retained deliberately as a backstop should the filter ever change, and is **deliberately left untested** — reaching it requires stubbing pandas internals, and a test that fragile is worse than the invariant it guards. What *is* pinned is the behaviour that actually protects the partner: `tests/test_gaul_lookup_fidelity.py::test_a_sentinel_code_is_dropped_rather_than_shipped` (the cell is excluded, so it later fails loud as *absent* rather than shipping as wrong-but-non-null) and `test_lookup_carries_no_sentinel_codes` on the committed artifact.

Cross-refs: C-35 (RESOLVED — the `-1` defect class this guards against), C-59 (same invariant block), C-43 (the fidelity test that would catch a bad artifact regardless), **Cluster K**.

---

---

### C-47: Stale untracked `reconciliation/__pycache__/` survives the module's retirement and misrepresents the package tree `[backlog]` — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-47 |
| Resolved | 2026-08-01 |
| Resolution | **Resolved by #177 (2026-08-01).** `views_postprocessing/reconciliation/` and its stale bytecode are deleted. The directory had survived the module's retirement in #62 (2026-06-26) and had already misled one in-session inspection into reporting the migration unfinished — which is the harm this entry recorded. Surfaced for action by the `/falsify` audit that disproved "there is nothing more to do in this repo"; it had been known and walked past for six weeks. |
| Tier | 4 — pure hygiene: not importable (no `__init__.py`, no sources), untracked, no correctness or reliability impact; its only effect is misleading humans and tools that inventory the tree |
| Source | `manual` (2026-07-19) — maintainer question "I thought reconciliation had moved out?" during the ADR-013 read-through; directory listing showed a phantom `reconciliation/` package |
| Trigger | When the D-12 repo-rename assessment (or any repo-structure audit / fresh assimilation) next inventories `views_postprocessing/` and takes the phantom `reconciliation/` dir as evidence the module still lives here — as happened in-session 2026-07-19 |
| Location | `views_postprocessing/reconciliation/__pycache__/` (untracked bytecode leftovers; sources deleted in #62 / PR #63, `6af2020`) |

The reconciliation retirement (C-42 cutover leg C2) deleted all tracked sources, but the untracked `__pycache__/` bytecode directory survived on the working machine. Directory listings therefore still show a `views_postprocessing/reconciliation/` package, which already misled one in-session inspection into reporting the migration unfinished. Deletion is a one-liner (`rm -rf views_postprocessing/reconciliation`) deferred by maintainer decision; tracked as a GitHub issue. Resolves on deletion (verify `git status` stays clean and the vpp suite green — trivially expected).

Cross-refs: C-42 (RESOLVED — the migration this is residue of), D-12 (the rename assessment it could mislead), issue #103 (the live tracker).

**Verified still present 2026-07-31 (review-rr):** `views_postprocessing/reconciliation/__pycache__/` holds 6 stale `.pyc` files (`proportional`, `grouping`, `module`, `frames`, `validation`, `__init__` — all `cpython-310`). Directory listings still show a phantom `reconciliation/` package. **Tagged `[backlog]`:** Tier 4, one-line fix, already tracked as issue #103 — kept here for completeness, not active risk management. Resolves on deletion.

---

### C-63: A launch config that omits `wire_contract` silently routes into retired code instead of failing — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-63 |
| Resolved | 2026-08-01 |
| Resolution | **Resolved by #149 (epic #148), and this entry simply never moved.** The fix landed on 2026-07-31: the manager carries **zero** `configs.get("wire_contract")` branches and **two** `launch_config.assert_*` calls, so an incomplete launch config is refused by name rather than routed into retired code. Verified against the tree during the 2026-08-01 `review-rr` pass. The entry sat under Open for a day with its defect already gone — a drift class `test_register_integrity.py` cannot catch, because that guard checks whether a *heading* says RESOLVED, not whether the *code* is fixed. |
| Tier | 2 — the repo that authored ADR-003 ("authority of declarations over inference") infers its own delivery mode from the *absence* of a config key. A clone, a config refactor, or a typo selects the retired pandas path with no signal; that path's uploads also discard their failure result (#145), so the second failure is silent too. Not Tier 1: the retired path still produces a valid artifact, so this is wrong-path-taken, not wrong-data-shipped. |
| Source | `repo-assimilation` (2026-07-31) — clone-readiness pass |
| Trigger | When writing the launch config for **views-crafdapi** or **views-productionapi**, or when refactoring views-models' `config_meta.py` — verify the manager *raises* on a missing `wire_contract`/`data_format` rather than falling back. It does not today. |
| Location | `views_postprocessing/unfao/managers/unfao.py:233`, `:294`, `:323`, `:409`, `:520` (the `wire_contract` forks); `:130` (the `data_format` fork); views-models `postprocessors/un_fao/configs/config_meta.py:26-27`, `config_queryset.py:62` (the only place both are declared) |

Two **independent** dispatch axes give four theoretical delivery modes, of which production uses exactly one: `declared_data_format(queryset) == "feature_frame"` (`:130`) selects the frame-native historical read, and `configs.get("wire_contract")` (five sites) selects the ADR-013 contract delivery. Production declares both. **Omitting either silently selects the retired half** — `.get()` returning `None` is indistinguishable from a deliberate `False`.

This is the inference this repo's own ADR-003 forbids, in the manager that orchestrates the delivery. The correct shape is one path plus a loud refusal naming the missing key.

Cross-refs: **C-40** (the manager this lives in), **#145** (the retired path's silent upload failures — the second half of the same hazard), **D-11** (the concrete-siblings-and-delete decision whose "delete" step is outstanding), **Cluster L**.

---

### C-09: Publish workflow validates version against wrong PyPI package — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-09 |
| Resolved | 2026-08-01 |
| Resolution | **Fully fixed 2026-08-01 (release PR #168).** This entry recorded that the publish workflow compared the local version against **views-pipeline-core**'s PyPI release rather than this package's. That half was fixed earlier (branch `fix/publish-version-check-10`), but the fix introduced a second, sharper defect that nobody could have hit yet: querying an **unpublished** package returns HTTP 404 with body `{"message": "Not Found"}`, `jq -r .info.version` prints the literal string `null` and exits 0, and `packaging.version.parse('null')` raises `InvalidVersion`. **The first-ever release of this package was therefore guaranteed to fail its own version gate** — with an error reading like a version-parsing bug rather than "not published yet". Surfaced by the `/code-review` pass on the release merge, verified concretely rather than inferred (the 404 body, jq's exit code and output, and `parse('null')` were each checked). Fixed with `jq -r '.info.version // empty'` plus an explicit first-release branch that logs and skips the comparison. Note the merge to `main` *changed the failure mode* — main's version compared against a published package and failed cleanly with `AssertionError`; the post-fix-pre-this-PR state crashed instead. |
| Tier | 4 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When publishing a new release of `views-postprocessing`, the version check may incorrectly pass or fail because it compares against `views-pipeline-core` on PyPI |
| Location | `.github/workflows/publish_package.yml:33` |

The "Validate Version" step fetches the latest version from `https://pypi.org/pypi/views-pipeline-core/json` instead of `https://pypi.org/pypi/views-postprocessing/json`. This compares the local `views-postprocessing` version against `views-pipeline-core`'s PyPI version, which is a different package entirely. The check may incorrectly block a valid release or allow a version that collides with an existing `views-postprocessing` release.

---

### C-29: Manager reads fetch result via disk side-channel instead of return value — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-29 |
| Resolved | 2026-08-01 |
| Resolution | **Resolved by deletion (#149, epic #148).** The side-channel was `_read_historical_data`'s pandas leg — `get_data()`'s return value discarded, the dataframe re-read from `cached_data_path`. That leg was retired when the frame-native read became the only read: `_read_historical_frame` takes `get_feature_frame`'s **return value** directly. There is no longer a disk hand-off between pipeline-core and this repo, so the failure this entry described (a caching change upstream silently serving a stale previous parquet) has no path. |
| Tier | 2 — under a realistic pipeline-core caching refactor, the postprocessor silently reads a stale previous parquet and enriches outdated data |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When views-pipeline-core changes caching behavior (format, filename template, skip-write optimization), verify `_read_historical_data` still reads what `get_data()` just produced — the return value is discarded and the dataframe re-read from `cached_data_path` |
| Location | `views_postprocessing/unfao/managers/unfao.py:134` (`get_data(...)` return discarded), `:141` (`cached_data_path` re-read); views-pipeline-core `modules/dataloaders/dataloaders.py:1490-1494` |

`get_data()` returns `(df, alerts)`; the manager discards it and re-reads from `self._data_loader.cached_data_path`, a property set as a side effect of the fetch. Two sources of truth for "the data just fetched," coupled by an undocumented convention. If pipeline-core ever skips the disk write for `use_saved=False` (a legitimate optimization from its perspective), the manager reads a stale previous file silently — or crashes if none exists. The convention has already drifted once: the loader docstring (dataloaders.py:1466-1471) still documents `{partition}_viewser_df` naming while the code now formats `{partition}_{source}_df` (line 1490). Fix is one line: consume the return value. Related to views-pipeline-core register entries C-59/C-60 (cache filename convention).

**Update 2026-07-31 (review-rr — scope narrowed to the legacy branch):** since #126 the historical path run-0 used is `_read_historical_frame` (`get_feature_frame`, `:101-124`), which returns a `FeatureFrame` **directly** and has no disk side-channel. The side-channel survives only in the legacy `_read_historical_data` branch (`:134`/`:141`), whose retirement is the named post-run-0 follow-up. Tier held at 2 while the branch exists and remains reachable; resolves with the branch.

---

### C-67: ADR-012 misdescribes the system in two load-bearing ways — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-67 |
| Resolved | 2026-08-01 |
| Resolution | **Corrected, and the load-bearing claims are now mechanically checked (#154, epic #148).** Both false claims are true again — the manager is 406 lines (from 636) and pandas has exactly one importer (`contract/enrichment.py`, from three) — but being true is not the fix; being *checkable* is. ADR-012's ontology table was rewritten against the three-package structure, ADR-002's layering illustration replaced (it still named `unfao/extraction.py`, deleted in #151), and the manager CIC updated (it documented `_historical_dataframe`, `LEGACY_FORECAST_FILTERS` and a `ForecastIdentityError` that no longer exist). Four guards added to `tests/test_doc_accuracy.py`: pandas has exactly one importer, `views_pipeline_core` has exactly one importer, the manager stays under 450 lines, and `contract/` does not import the partner. Each was **mutation-tested** — a deliberate violation was introduced and confirmed to fail — because a doc test that cannot fail is not a test. The next drift fails CI instead of waiting for an audit, which is the same remedy that closed the C-48–C-55 ADR-013 series. |
| Tier | 3 |
| Source | `repo-assimilation` (2026-07-31) |
| Trigger | When the **views-crafdapi**/**views-productionapi** authors read ADR-012 as the specification for what to copy — both false claims describe exactly the structures a clone must decide about |
| Location | `docs/ADRs/012_revised_ontology.md` — the "Pipeline Manager" and "Representation Seam" rows of the ontology table |

Two claims no longer hold:

1. **"the thin `UNFAOPostProcessorManager`"** — it is **636 lines**, 25% of the package, holding two read strategies, two save strategies, an inner port class, provenance formatting, coverage orchestration and env assembly (**C-40**).
2. **"the *single* pandas-aware module (`unfao/extraction.py`)"** — pandas is imported by **three** modules: `extraction.py`, `enrichment.py`, and `managers/unfao.py:14` (**C-65**).

Both drifted the same way and for the same reason: the ADR describes the intended end state of a migration that then stopped one step short. Same disease as the C-48–C-55 ADR-013 series, which was fixed by pinning prose to mechanically-checked facts.

Cross-refs: **C-40**, **C-65**, **C-64**, **Cluster I** (governance-artifact drift), C-48–C-55 (the precedent and its remedy).

---

### C-70: `METADATA_COLS` serves three contracts at once — reordering it silently changes delivered bytes — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-70 |
| Resolved | 2026-08-01 |
| Resolution | **The column contract is declared as data (#153, epic #148).** `gaul_schema.COLUMNS` states each column's `(name, role, wire_dtype)` once; `METADATA_COLS`, `CODE_COLS`, `NAME_COLS`, `COORD_COLS` and the new `WIRE_DTYPE` map are all **derived** from it. The three `if col in CODE_COLS` branches now read a stated policy rather than re-deriving one positionally. The docstring says plainly what the old comment did not: **reordering `COLUMNS` is a wire change** (ADR-013 §5.1 order is normative, §10 byte-pins it), and two new tests in `test_wire_naming.py` pin the derivation and spell the normative order out literally — so a reorder fails with a readable diff rather than only as a fixture byte mismatch. Landed with C-69's move because `gaul_schema` is partner-neutral machinery and this was the one time it was being handled. |
| Tier | 3 — no current defect (the byte-parity fixture catches a reorder loudly), but the list carries three independent meanings with only one of them named, so a reasonable edit for one purpose silently changes the other two |
| Source | `expert-code-review` (2026-07-31) — Kleppmann and Hickey lenses, clone-readiness pass |
| Trigger | When adding, removing or reordering a GAUL metadata column — for a new partner product, or under #89 — verify the wire column order is deliberate rather than inherited from the manager's selection order |
| Location | `views_postprocessing/unfao/gaul_schema.py:14-24` (`METADATA_COLS`, `CODE_COLS`, `NAME_COLS`, `COORD_COLS`); consumed as an *ordering* contract at `unfao/wire/sidecar.py:62`, `unfao/historical.py:76`, and as a *set* contract at `managers/unfao.py:277`, `unfao/historical.py:50,90` |

One list encodes three things: **which** columns exist (set membership), **in what order** they appear on the wire (§5.1 declares column order normative, pinned by the golden fixture), and **which** the null-gate covers. Its docstring names only the first — *"the 9-column contract (manager selection order)"* — so the wire-order meaning is undocumented at the definition site.

Separately, the *type* policy is re-derived positionally from three sibling lists via `if col in CODE_COLS` branches in **three** modules (`build_gaul_lookup.py:139-144`, `wire/sidecar.py:64-71`, `unfao/historical.py:78-83`). The concept "a code column is float64 on the wire" is scattered rather than declared once.

**Why it is only Tier 3:** the ADR-013 §10 golden fixture pins the bytes, so a reorder fails loudly in CI rather than shipping. The risk is cost-of-change and the trap a clone walks into, not silent corruption.

**Mitigation (not urgent, and cheap when the packaging split happens):** declare the column contract as data — one table of `(name, role, wire_dtype)` — and derive `METADATA_COLS`, the role lists, the cast branches and the wire order from it. Naturally folded into the partner/machinery separation (**C-69**), since `gaul_schema.py` is partner-neutral machinery.

Cross-refs: **C-69** (the packaging split this rides along with), **C-59**/**C-61** (the same file's build-time invariants), **#89**, ADR-013 §5.1 (the normative order), **Cluster L**.

---

### C-69: The `unfao/` package binds partner-neutral machinery to one partner's name — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-69 |
| Resolved | 2026-08-01 |
| Resolution | **The boundary is drawn (#153, epic #148).** `views_postprocessing/` now has three top-level packages, each answering a different question: `delivery/` (what makes a delivery valid — the invariants), **`contract/` (how a delivery is built — the ADR-013 machinery, NEW)**, and `unfao/` (who a delivery is for — reduced to `product.py`, `appwrite_env.py` and `managers/`). ~800 lines moved out from under the partner's name. The move surfaced a real coupling that was invisible while everything shared a package: **`wire/sink.py` imported `unfao.product`** — not in its logic, but as *default argument values* for `upload_enabled`, `consumer_name` and `s_min`. The parameters already existed (DIP was satisfied); the defaults reached into the partner. They are now required arguments the manager supplies explicitly, so the mechanism declares what it needs and the partner provides it. `contract/` contains no code reference to `unfao`; #155 makes that mechanical rather than conventional. |
| Tier | 3 |
| Source | `repo-assimilation` (2026-07-31) — clone-readiness pass |
| Trigger | When **views-crafdapi** or **views-productionapi** is cut — the clone must import `unfao.wire`, `unfao.frames`, `unfao.gaul_schema` and `unfao.track_a_source` to get machinery that has nothing to do with FAO, or fork them and start a third copy |
| Location | `views_postprocessing/unfao/` — partner-**specific**: `product.py`, `appwrite_env.py` (`UNFAO_ENV`), `managers/unfao.py`. Partner-**neutral**: `wire/*` (7 modules, 466 lines), `frames.py`, `frame_extraction.py`, `gaul_schema.py`, `track_a_source.py`, `historical.py`, `source_metadata.py` |

`delivery/` got this right — its `__init__.py:3` states "Partner-agnostic: FAO and the coming UN-agency deliveries reuse these", and nothing in it names FAO. `unfao/` did not: roughly 800 of its 1,001 lines are partner-neutral and sit under a partner's name.

**Update 2026-07-31 (`expert-code-review`, Martin lens) — partner identity has THREE homes, which is the same boundary problem stated at field level.** "Who is this delivery for" is declared in three unrelated places: `unfao/product.py:34` (`CONSUMER_DOCUMENT_NAME`), `unfao/appwrite_env.py:31-38` (the `UNFAO_*` env names), and `unfao/wire/sink.py:162` (`consumer_name`, correctly a *parameter*). The third is the right shape and proves the machinery is already parameterisable; the first two are declarations that a clone must find and replace. The separation below should consolidate them, not merely move them.

This is a **CRP** violation (things not reused together forced together) with a concrete cost: the clone takes the FAO name to get the wire contract, or forks it. `product.py` is already the right shape for the partner-specific half — 4 declared constants — but nothing separates it structurally from the machinery.

Distinct from **D-12**(1), which proposes renaming the *repository*; this is the *package interior*, and it bites first because the clone is cut before any rename.

Cross-refs: **D-12** (the repo rename), **C-40**, **#96** (the rename issue), **#97** (second-store scoping), views-appwrite's clone preconditions.

---

### C-68: `_DEFAULT_LOOKUP` — a private name imported across three module boundaries — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-68 |
| Resolved | 2026-07-31 |
| Resolution | **Promoted to a public declared name (#152, epic #148).** `_DEFAULT_LOOKUP` became `gaul_lookup.LOOKUP_PATH` — the artifact's identity now has a home of its own rather than living behind an underscore in the enricher that happened to consume it. `enrichment.py` keeps a `_DEFAULT_LOOKUP` alias pointing at it so `GaulLookupEnricher`'s own default is unchanged, and its `_read_version` delegates rather than duplicating. The manager no longer imports either private name. Guarded by `test_gaul_lookup_access.py::test_the_manager_reads_the_lookup_once_and_threads_it`. |
| Tier | 4 |
| Source | `repo-assimilation` (2026-07-31) |
| Trigger | When splitting `enrichment.py` under #89, or when a clone needs the lookup path without the pandas enricher — the underscore says "internal", so a refactor is entitled to move or rename it and would break two live call sites |
| Location | Defined `views_postprocessing/unfao/enrichment.py:33`; imported `views_postprocessing/unfao/managers/unfao.py:18`; used `:460`, `:612` |

The contract path depends on the lookup *path constant* but not on the *enricher class* that owns it. The dependency is real and load-bearing; the leading underscore declares the opposite. Promoting it to a public name — or better, moving the artifact path to `product.py` where declarations live — costs one line and removes the trap.

Cross-refs: **C-66**, **C-65**, **#89**, **Cluster L**.

---

### C-66: The GAUL lookup is loaded three times per run, once into an object production never uses — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-66 |
| Resolved | 2026-07-31 |
| Resolution | **One artifact, one read (#152, epic #148).** The eager `GaulLookupEnricher()` is gone from the manager's `__init__` — it existed only to supply `lookup_version`, which was a `@staticmethod` that never touched the instance, i.e. a fact about the *artifact*. That fact now lives in a new `unfao/gaul_lookup.py` alongside the artifact's path and a single `load()`. `_save_contract` reads the table **once** and threads it to both consumers, each of which already took it as a parameter (DIP). Net: three reads per delivery → one, and the pandas enricher leaves the delivery path entirely. Pinned by `tests/test_gaul_lookup_access.py` — including a source-scan asserting exactly one `gaul_lookup.load()` in the manager, and a signature check that both consumers still *accept* the table rather than fetching it. |
| Tier | 4 — startup cost and confusion, no correctness impact |
| Source | `repo-assimilation` (2026-07-31) |
| Trigger | When profiling delivery startup, or when the lookup grows beyond `land_gaul` (a multi-region product would multiply the waste) |
| Location | `views_postprocessing/unfao/managers/unfao.py:98` (`self._enricher = GaulLookupEnricher()` — eager, unconditional, unused in contract mode), `:460` and `:612` (`pq.read_table(_DEFAULT_LOOKUP)`) |

`__init__` eagerly constructs `GaulLookupEnricher`, which reads the 888 KB parquet into pandas at `enrichment.py:48`. The contract path never uses that instance — it reads the same file twice more through pyarrow. So every production run pays three reads of one artifact, one of them into a representation the delivery no longer uses.

Cross-refs: **C-65** (same retired-seam cluster), **C-68** (the private-name import used for two of the three reads), **Cluster L**.

---

### C-65: `unfao/extraction.py` is four-fifths unreachable and duplicates `frame_extraction.py` — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-65 |
| Resolved | 2026-07-31 |
| Resolution | **One seam, and it is the frame-native one (#151, epic #148).** `unfao/extraction.py` is deleted. Its four frame readers (`cells_of`, `months_of`, `drop_months_above`, `unmapped_cell_count`) became unreachable when #149 retired the pandas delivery and were already implemented frame-natively in `frame_extraction.py`. Its one surviving function, `file_metadata`, was never extraction at all — it unpacks a *store document* and touches no representation — so it moved to a new `unfao/store_metadata.py`, sibling of `source_metadata.py` (producer facts / store facts), leaving each module with one concept. Tests followed the code rather than being deleted: `test_extraction.py` → `test_store_metadata.py`; `test_frame_extraction.py`'s seam-vs-seam **parity** assertions became **absolute** assertions of the same expected values, since parity has nothing left to compare against; `test_input_integrity_e2e.py` now feeds the invariants **primitives directly**, which is how the delivery actually calls them — it had been building pandas fixtures to reach representation-free rules. `test_input_integrity_design_contract.py` ① updated and now asserts both halves: the seam exists **and** its retired pandas sibling has not come back. |
| Tier | 3 |
| Source | `repo-assimilation` (2026-07-31) |
| Trigger | When #89 (numpy/pyarrow keyed gather) or #90 lands, or when a clone copies the representation seam — decide which of the two extraction modules is *the* seam rather than carrying both |
| Location | `views_postprocessing/unfao/extraction.py` (103 lines; only `file_metadata` is contract-reachable, via `managers/unfao.py:48`); the legacy-only functions `months_of`, `drop_months_above`, `cells_of`, `unmapped_cell_count` are called at `:383`, `:393`, `:417`, `:589`, `:633`, `:634`; frame-native equivalents live in `views_postprocessing/unfao/frame_extraction.py` (`:116`, `:122`, `:584`, `:600`) |

ADR-012 designates `extraction.py` as **"the single pandas-aware module"** — the one place a representation change lands. In practice the representation change already landed *beside* it: `frame_extraction.py` implements the same four operations frame-natively and is what production calls. `extraction.py` retains one live function and four dead ones.

Two seams for one concept is the CRP violation D-11 predicted: WET-before-DRY was correct during the migration and expires when the migration completes.

Cross-refs: **C-40** (which calls these the "retired-in-place legacy seams"), **D-11**, **C-67**, epic **#85** / **#89** / **#90**, **Cluster L**.

---

### C-25: Forecast input selected by category-only filter — newest file wins regardless of producer — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-25 |
| Resolved | 2026-07-31 |
| Resolution | **Superseded by mechanism (#150, epic #148) — not merely mitigated.** This entry's hazard was "newest `category=forecast` upload wins regardless of producer". Its recorded mitigation was `delivery.identity.assert_forecast_identity`, which #150 retired. The hazard nonetheless cannot occur: since #149 the contract path is the only path, and it selects by **run manifest** — a commit marker whose contents are hash-verified — so recency-based selection is not an operation the code can perform. Declared identity is additionally checked per shard header at `wire/source_selection.py:73-81`. Closed as structurally impossible rather than guarded.<br><br>**⚠ CORRECTION 2026-08-01 — this resolution overclaimed, and the overclaim is recorded rather than rewritten.** *"Recency-based selection is not an operation the code can perform any more"* is **false**: `contract/wire/source_selection.py:106` calls `store.latest_file_id(dict(HOP_A_MANIFEST_FILTERS))` — it selects the **newest** manifest over a filter matching every manifest ever published. What manifest selection actually solved is the **producer-identity** half of this entry's hazard: the manifest declares its ensemble and every shard header is verified against it (`:73-81`), so another producer's run cannot be selected. The **recency** half was not solved — it moved from newest-payload-file to newest-manifest. That half is now **C-73**, which is live and Tier 2. This entry stays resolved for the identity hazard it was written about; do not read it as covering run vintage. |
| Tier | 2 |
| Source | `cross-repo-investigation` (2026-06-12) |
| Trigger | When any new producer uploads to the prod_forecasts bucket with `category: "forecast"`, verify the postprocessor still picks up the intended ensemble's file — selection is newest-`$createdAt`-wins with no loa, model-name, or run-id filter |
| Location | `views_postprocessing/unfao/managers/unfao.py:247` (legacy selection, `LEGACY_FORECAST_FILTERS` at `:34`), `:260` (identity assertion); contract path selects by manifest instead — `unfao/wire/source_selection.py:39`; views-pipeline-core `modules/datastore/datastore.py:475-511` |

`_read_forecast_data()` calls `download_latest_file(filters={"category": "forecast"})`. "Latest" is resolved by sorting metadata documents on `$createdAt` descending and taking the first (datastore.py:475-511). There is no filter on `loa`, `name`, `targets`, or any run identifier. Today only the production ensemble uploads with this category, so the newest file is the right file by circumstance, not by contract. If a second model, a test run, or a backfill ever uploads to the same bucket with `category: "forecast"`, the postprocessor silently enriches and ships the wrong predictions to FAO. The same single-filter pattern exists downstream: views-faoapi selects from the unfao_bucket by category only (views-faoapi `api.py:488`), so a stray upload there reaches FAO directly. Compounding factor: Appwrite has no retention — every historical upload remains a candidate forever; correctness depends entirely on upload discipline.

This concern became visible during the cross-repo investigation (`docs/cross_repo_integration_report.md` §2.4, §4.2); it was previously implicit in the C-13 narrative (timeouts) but is a distinct failure mode: C-13 is "the call hangs," C-25 is "the call succeeds with the wrong file."

**Mitigation landed (S3, 2026-06-26, `sprint/fao-input-integrity`):** `_read_forecast_data` now resolves the file id, fetches its metadata, and asserts identity (`delivery/identity.assert_forecast_identity`) against the configured ensemble (`{name: ensemble_path_manager.model_name, loa: "pgm"}`) **before** download — a stray `category="forecast"` upload now fails loud instead of shipping silently. **Residual (verify before relying on it):** the guard assumes the producer's uploaded `name`/`loa` equal `model_name`/`"pgm"`; this is checked against pipeline-core's code but **not a live Appwrite upload**. If the contract differs, the guard fails loud on *every* run — caught at the first smoke-test delivery (option A / S6 #57), **not** silently — so the residual is an availability / false-positive risk, not a corruption one. Confirm the field match at the option-A run; until then C-25 stays open.

**Update 2026-07-31 (`repo-assimilation`) — the registered mitigation is LEGACY-ONLY; the live path is protected differently.** The identity assertion recorded above (`delivery/identity.assert_forecast_identity`) is called at `unfao.py:260`, inside the **legacy** `_read_forecast_data` leg. Production runs the contract path, which selects by **run manifest** (`unfao/wire/source_selection.py`) and never calls it. That is a *stronger* guarantee — a manifest is a commit marker with hash-verified contents, not a metadata field match — so the concern is better mitigated than this entry states, but **not by the mechanism this entry names**. Re-read accordingly; and note the mitigation's stated residual ("confirm the field match at the option-A run") is now moot for the live path. See **C-64**.

See also C-13 (no timeout on the same calls), C-15 (upload metadata lacks provenance to detect this downstream), C-43 (the same "verify at the first live run" debt pattern on the enrichment swap).

---

### C-64: `delivery/identity.py` is an authoritative delivery invariant that production never calls — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-64 |
| Resolved | 2026-07-31 |
| Resolution | **Retired, by decision rather than by side effect (#150, epic #148).** `delivery/identity.py` was deleted along with `tests/test_identity.py` and the two S3 cases in `test_input_integrity_e2e.py`. The rule survives in a stronger form: `unfao/wire/source_selection.py:73-81` checks **every shard header's declared `provenance.ensemble`** against the launched ensemble inside `TargetLease.load()`, so identity is established from the artifact's own content rather than one store document's metadata field, and per shard rather than once per run. Covered by `test_wire_source_selection.py::test_wrong_declared_ensemble_refuses_at_load`. Recorded as a dated amendment to ADR-012, whose "Delivery Invariants" row had listed forecast identity as authoritative — the entry existed precisely to stop that row silently describing deleted code. |
| Tier | 3 |
| Source | `repo-assimilation` (2026-07-31) |
| Trigger | When **views-crafdapi**/**views-productionapi** copy `delivery/` as the reusable invariant core — verify whether the identity rule is enforced on the path the clone actually uses, or inherited as documentation only |
| Location | `views_postprocessing/delivery/identity.py` (53 lines); sole caller `views_postprocessing/unfao/managers/unfao.py:260` — inside the **legacy** `_read_forecast_data` leg; `docs/ADRs/012_revised_ontology.md` (lists it under "Delivery Invariants — Authoritative") |

`assert_forecast_identity` verifies that a selected forecast document's `name`/`loa` match the configured ensemble before download. It is reachable **only** from the legacy reader. The contract path selects by **manifest** (`wire/source_selection.py`) and never consults it — which is a *stronger* guarantee, not a gap. The risk is the mismatch between ADR-012 naming it authoritative and the code never running it: a clone inherits a rule that looks enforced and is not.

**This also updates C-25's status** — that entry's registered mitigation *is* this function, so the mitigation applies to the legacy path only. C-25's actual protection on the live path is manifest selection, which is why the entry should be re-read rather than assumed still-mitigated-as-written.

Cross-refs: **C-25** (whose mitigation this is), **C-67** (the ADR-012 drift this instantiates), **Cluster L**.

---

### C-56: Run-0 was OOM-killed at 23.8 GB — the pandas delivery path could not fit global volume on the 31 GB host — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-56 |
| Resolved | 2026-07-27 |
| Resolution | Fixed by changing **representation**, not by tuning. Two stacked causes were measured: the pandas historical path (~6–10 GB of intermediate copies over 28.3M rows) and the contract forecast leg holding all three targets plus download transients in memory at once (~12 GB). **Part A — streaming delivery:** `source_selection.fetch_run` split into a cheap `resolve_run` (manifests only, shard file-ids pinned at resolve so later fetches are race-free) plus per-target `TargetLease.load`; `sink.deliver_run` now consumes one target at a time (load → §6 no-collapse gate → month shards → release), accumulating records incrementally. **Part B — frame-native historical (#126):** `_read_historical_frame` fetches a `views_frames.FeatureFrame` via pipeline-core's `get_feature_frame` (this repo is its first production consumer) and `unfao/historical.py` builds the artifact through pyarrow, pandas-free; the uploaded parquet stays byte-reader-identical for faoapi, proven against a legacy characterization golden (`tests/fixtures/historical_golden/`). Shipped across PRs #115–#129. **Re-run 2026-07-27: peak RSS 5.6 GB, 28,356,996 rows at 64,742 cells, clean exit, no OOM** — the delivery that had been impossible succeeded. |

Registered retrospectively during review-rr (2026-07-31) as **incident memory**: this was the most consequential production event in the repo's history — it blocked the first-ever FAO global-land delivery — and it had no register entry, so a future reader would find the fix (frame-native, streaming) with no record of the failure that forced it. The plan file's closeout step required this entry and it was never written.

**Why it matters beyond the fix:** the register **predicted this**. C-32 (RESOLVED) named it a year-quarter early — *"verify peak memory of joining 9 metadata columns onto ~28M rows — four string columns as pandas object dtype cost roughly 8–20 GB at this scale"* — and its proposed mitigation (categorical dtype) would have bought perhaps 10× on the string columns but left the object-dtype container in place; the actual fix was to leave pandas entirely. C-40 had independently identified the representation as the root cause and pandas retirement as the gate. **The register worked; the entry was simply not acted on before the run.**

**Live residual (not a defect — a budget):** peak memory is now a load-bearing operational constraint. 5.6 GB against a 31 GB host is comfortable at S=1 point forecasts and 3 targets × 36 months. It is **not** self-evidently comfortable at the next deliverable's scale — the UN-agency product carries ~1024 pooled draws (cf. the C-38 memory analysis, relocated to views-frames), and the forecast leg's per-target streaming bounds one axis but not the sample axis. **Re-measure peak RSS before the first sample-bearing delivery** rather than assuming this headroom persists; ADR-013 §4.6 carries the capacity math.

Cross-refs: C-32 (RESOLVED — the entry that predicted this, discharged by the same re-run), C-40 (the representation coupling whose pandas gate this lifted), C-30 (the coverage guard the same run exercised), C-43 (the correctness debt the same run did **not** discharge), C-38 (RESOLVED/relocated — the sample-axis memory analysis this residual points at), issues #126, #131.

---

### C-42: Reconciliation migration is stranded across three repos; production runs the old path and the migration-state was mis-stated — RESOLVED

**RESOLVED 2026-07-31 (review-rr) — disposition settled at this entry's own request.** The entry asked for exactly this adjudication: *"This entry can move to Resolved once C-43 is filed (it is); kept open here only pending a /review-rr relocation."* It also contained a **direct internal contradiction** — that sentence against a closing paragraph saying *"C-42 stays open as a thin tracker until #198 lands."* Adjudication: the registered **hazard** — acting on a mis-stated cross-repo migration state — is resolved and independently verified (all three cutover legs landed; no unguarded importer of `views_postprocessing.reconciliation` remains anywhere). The **residual** (pipeline-core's `views_reporting.statistics.ForecastReconciler` re-export) is, by this entry's own reasoning, owned by **pipeline-core #198** and *"no separate vpp entry warranted (would duplicate #198)."* A tracker that duplicates another repo's issue is not a vpp risk. Closed; vpp **#40** remains the local waiting-on marker.

| Field | Value |
|-------|-------|
| ID | C-42 |
| Tier | 3 |
| Source | `manual` (2026-06-26) — cross-repo verification on `origin/development` |
| Trigger | When a cross-repo agent next acts on reconciliation (merges pipeline-core PR #217, repoints any consumer, **deletes vpp's copy**, or builds a new reconciliation feature), confirm which copy it targets against `origin/development` first — do **not** assume #217 is merged, the cycle is broken, or vpp's copy is unused (views-models imports it live; deletion is hard-gated on C1) |
| Location | pipeline-core `origin/development`: `managers/ensemble/ensemble.py:747`, `managers/ensemble/dataframe_ensemble.py:921`, `modules/reconciliation/__init__.py:4` (live `views_reporting.reconciliation` imports); `views-models/reconciliation/reconciler_factory.py:54` (**unguarded live import of `views_postprocessing.reconciliation`** — ADR-014 composition root); `views_postprocessing/reconciliation/` (parity-proven, **consumed by views-models**); the plan file + issue #39 (carried the false "merged" premise) |

Verified 2026-06-26 on `origin/development`: pipeline-core **still imports `views_reporting.reconciliation`** (3 sites above) — the pipeline-core↔views-reporting reconciliation **cycle is live**, and production reconciliation still runs through views-reporting (torch). **PR #217** (the DIP port + adapter that would decouple it, #195) is **OPEN/unmerged** — the port `domain/reconciliation.py` exists on dev but the adapter does not. So **three reconciler copies are in flight**: views-reporting (live via pipeline-core), vpp (parity-proven, PR #30), views-frames (now SHIPPED — v1.7.0 on PyPI 2026-06-26).

**CORRECTION 2026-06-26 (exploration-verified): vpp's `reconciliation/` is NOT "unused/stranded."** `views-models/reconciliation/reconciler_factory.py:54` does an **unguarded** live import `from views_postprocessing.reconciliation import ReconciliationModule` (the ADR-014 composition root, constructed at runtime by reconciling ensembles). The earlier "unused by any production consumer" wording here was wrong — and it was itself an instance of this entry's own hazard (state-drift that could prompt an unsafe action). **Deletion-safety consequence:** deleting vpp's `reconciliation/` **hard-breaks views-models** unless C1 (repoint views-models → `views_frames_reconcile`) lands and goes green **first**. All other importers are guarded (`pytest.importorskip`): views-frames `test_reconcile_head_to_head.py`, views-models `test_reconciliation_factory.py`. pipeline-core / views-reporting do not import vpp. The hazard remains **acting on a false state** (e.g. merging the throwaway #217 port, or deleting a copy that is in fact a live dependency). No silent data corruption (the production path works; it is just the old one) → **Tier 3** (coordination / state-drift / cost-of-change).

**Mitigation:** do **not** merge #217 as a throwaway bridge. The "release" leg is complete (v1.7.0 on PyPI). Cutover order: **repoint** (views-models#191 = C1; pipeline-core#221 = collapse the port, parallel) → **delete** (vpp #62 = C2, only after C1 green) → retire views-reporting reconciliation (vpp #40 / views-reporting#72, after #221).

**Update 2026-06-26 (cutover landed — the mis-stated-state hazard has resolved):** all three legs are done and verified on `origin/development`. **release** — views-frames v1.7.0 on PyPI. **repoint** — views-models **PR #202** merged (`reconciler_factory.py` imports `views_frames_reconcile`); **pipeline-core chose Decision K, not C** — **PR #217 merged** (`6427b9d`): it reconciles via its `Reconciler` DIP port with `views_frames_reconcile.ReconciliationModule` injected (the C-cutover issue #221 was closed unused). **delete** — vpp's copy removed in **#62 / PR #63** (merged to `development`, `c9e38402`). A full cross-repo sweep confirms no unguarded importer of `views_postprocessing.reconciliation` anywhere. The original hazard (acting on a *mis-stated* migration state) is **resolved** — every actor was verified against `origin/development` before acting. **The one residual is split out as C-43:** pipeline-core still imports `views_reporting.statistics.ForecastReconciler`, so the pipeline-core↔views-reporting edge is not fully severed and views-reporting retirement (#40 / views-reporting#72) is still blocked. This entry can move to **Resolved** once C-43 is filed (it is); kept open here only pending a /review-rr relocation.

See also C-37 / C-38 (the reconciler concerns — relocating to views-frames with the code), views-platform/views-frames#131 (the final home), #62 (retire vpp's copy), views-platform/views-models#191 (repoint), pipeline-core PR #217 (the merged DIP port, Decision K).

**Residual tail (verified 2026-06-26 — already tracked cross-repo, no new vpp entry):** pipeline-core still imports `views_reporting.statistics.ForecastReconciler` (`modules/statistics/__init__.py:5`), so the pipeline-core↔views-reporting edge is not yet fully severed and views-reporting's `reconciliation/` + `torch` retirement (#40 / views-reporting#72) is still blocked. But this is **not an untracked hazard**: the re-export is explicitly marked *"remove after downstream consumers update"*; `ForecastReconciler`'s only pipeline-core consumers are the transitional **golden-output equivalence tests** (#119 / #196, "new frames-native == old torch"); and **pipeline-core #198** already owns the removal — its scope note names *"the `reconciliation/` package **and** the `ForecastReconciler` class"* and it triggers vpp **#40** / views-reporting#72. Blocked on pipeline-core #197 (views-postprocessing/views-frames must be "default and stable") first. So C-42 stays open as a thin tracker until #198 lands; no separate vpp entry warranted (would duplicate #198). *(A speculative residual-coupling entry was drafted then withdrawn here after verification showed it was a duplicate of pipeline-core #198.)*

---

### C-45: `unfao/frames.py` is an unused views-frames conformance adapter carried on no live path — RESOLVED

**RELOCATED 2026-07-31 (review-rr — placement fix only, no change of substance).** Marked RESOLVED 2026-07-20 but never moved out of `## Open Concerns`; with C-19 it caused the header count mismatch corrected in this pass. Re-verified in code 2026-07-31: `frames.build_prediction_frame` is live on the contract path — imported at `unfao/track_a_source.py:35` (used at `:105` and `:152`) and `unfao/frame_extraction.py:73`. The conformance scaffolding became the load-bearing constructor exactly as intended.

| Field | Value |
|-------|-------|
| ID | C-45 |
| Tier | 4 |
| Source | `repo-assimilation` (2026-06-27) |
| Trigger | When the C-40 representation migration (pandas → views-frames) begins — confirm whether `frames.py` becomes the live conversion seam or should be removed; or when a contributor assumes it is on the delivery path (its own docstring says it is not) |
| Location | `views_postprocessing/unfao/frames.py` (the only `views_frames` importer); exercised solely by `tests/test_views_frames_conformance.py` |

`unfao/frames.py` (`to_prediction_frame` / `to_target_frame`) converts the repo's pandas tables into views-frames `PredictionFrame`/`TargetFrame` `(N, 1)` value objects to prove they satisfy the published views-frames contract. It is the **only** module importing `views_frames`, and **no live path calls it** — its sole consumer is the conformance test (the module's own docstring states "nothing in the live delivery path calls it yet"). It is forward-looking scaffolding for the C-40 frame migration: harmless, but a maintenance/confusion surface (a reader can mistake it for an active code path, and it hardcodes `S=1`, i.e. point-only, which will need revisiting for the draws/uncertainty work). No correctness or reliability impact → **Tier 4**.

**Partly addressed by S1 (epic #85 / #86, 2026-06-28).** `frames.py` was reworked to the declare-don't-guess design (D-11): it now exposes `build_prediction_frame` / `build_target_frame` over **declared primitives** (a 2-D `(N, S)` array + `(time, unit)`), supports **S>1** (the `S=1` hardcode is gone), is **pandas-free** (no longer the lone pandas importer — it sits alongside `delivery/`), and fails loud rather than inferring/reshaping. So the *S=1-hardcode*, *inference-risk*, and *pandas-coupling* dimensions are resolved. **Residual (entry stays open):** the module is still **not called by the live delivery path** — that wiring is S3 (#88, forecast convert-at-the-door). C-45 resolves when S3 lands (or, if S3 is abandoned, when the module is removed).

**RESOLVED 2026-07-20 (epic #105, S6/S7 — the wiring landed):** `frames.build_prediction_frame` is now on the live contract path — `track_a_source` constructs every interior frame through it, called by `wire/source_selection.fetch_run`, which the manager's declared contract mode invokes (`_read_forecast_data_contract`). The conformance scaffolding became the load-bearing constructor exactly as intended. (#88 was superseded by #105/#111; the wiring shipped there.)

See also C-40 (the pandas gate this adapter anticipates), #45 (the draws carrier that will need the `S>1` version), epic **#85** / **#86** (the S1 rework) / **#88** (the S3 wiring that closes this), **D-11** (the declare-don't-guess decision).

---

### C-38: Reconciliation grouping is O(groups × N) and materializes the whole grid frame — RESOLVED (compute fixed; residual relocated to views-frames)

**RESOLVED HERE 2026-07-31 (review-rr) — compute fixed, residual relocated.** Two dispositions in one entry, both already recorded below: the **compute** half was genuinely fixed (per-group `np.nonzero` → group-by-sort, O(N log N), parity bit-exact, scale guard added), and the **memory** residual (holding the whole pgm frame; chunk-by-time obligation) **left this repo with the code** in #62 / PR #63 and is now a consumer-side obligation at reconciliation-wiring time (pipeline-core#200/#221). The entry's own text already said *"no further vpp action."* Additionally its trigger referenced *"wiring at S7 (#39)"* — **#39 is CLOSED** with different scope, so the trigger was unsatisfiable as written. Closed here; the memory obligation remains live in views-frames / pipeline-core.

| Field | Value |
|-------|-------|
| ID | C-38 |
| Tier | 2 |
| Source | `expert-code-review` (2026-06-24) |
| Trigger | Before the first global / `land`-region reconciliation run — i.e. before wiring at S7 (#39) — benchmark `ReconciliationModule.reconcile` runtime and peak memory on global-volume frames; nothing above the 39-row fixture has been measured |
| Location | `views_postprocessing/reconciliation/grouping.py:69-79` (per-group `np.nonzero(inverse == gi)`); `views_postprocessing/reconciliation/module.py` (holds the full pgm frame; `np.empty_like` copy) |

`reconcile_pgm_to_cm` groups grid rows with `np.unique` (good) but then loops over unique `(time, country)` groups doing `np.nonzero(inverse == gi)` **per group** — an O(groups × N_pg) full-array scan. At global scale (~86k groups × ~28M pgm rows) that is ~10¹² comparisons plus 86k full-size boolean masks. Separately, the module holds the **entire** pgm frame at once (28M rows × S samples × 4 bytes ≈ 11 GB at S=100, **>100 GB at S=1000**) and `np.empty_like` doubles it — the original views-reporting code processed per-country subsets, never materialized the global frame, and used `ProcessPoolExecutor` for exactly this scale. **Parity is unaffected** (the result is identical); only runtime/memory blow up. Mitigation: replace the per-group `nonzero` with a single `argsort(inverse)` + contiguous slices (O(N log N)); budget/measure peak memory on a global-volume dry run and chunk by time or country if needed — both **before** wiring. Same enumerable-vs-discovered-at-scale pattern as C-31/C-32.

Tier 2: structural fragility under the realistic change of wiring to global, with a clear trigger; not Tier 1 (no silent corruption — parity is exact; this is a runtime/memory failure). See also C-31 (mapper scale), C-32 (enricher memory), C-37 (the algorithm), epic #31 / views-reporting#72.

**Update 2026-06-24 — compute RESOLVED.** The per-group `np.nonzero(inverse == gi)` was replaced with **group-by-sort** (`argsort(inverse)` + contiguous slices from `np.unique` counts, O(N log N), one index array). Parity stays **bit-exact** (`tests/test_reconciliation_grouping.py`, `test_reconciliation_e2e_parity.py` → 0.0) and a scale guard (`tests/test_reconciliation_scale.py`) protects against regression. **Residual (relocated with the code):** the module holds the whole pgm frame in memory at once; at global volume the **caller must chunk by time** (reconciliation is independent across months). The reconciler — and this chunk-by-time obligation — **left vpp**: the algorithm now lives in `views_frames_reconcile` and the vpp `ReconciliationModule` CIC was retired (#62 / PR #63, merged to `development` 2026-06-26). The global-volume verification is now a **consumer-side obligation at reconciliation-wiring time** (pipeline-core#200/#221), not a vpp concern. Tracked cross-repo via C-42; no further vpp action.

**Update 2026-06-24 (reframe — residual now near-term):** the memory residual is no longer "verify someday." The upcoming UN-agency deliverable reconciles **frames with ~1024 pooled draws** — squarely in the >100 GB-at-global regime. When pipeline-core's `PredictionFrameEnsembleManager` wires probabilistic reconciliation (pipeline-core#200, under epic #193), the **caller must chunk by time** (reconciliation is independent across months) and **measure peak memory on a global-volume dry-run** as part of that work. The reconciler code itself is unchanged (compute already O(N log N)); this is a consumer-side obligation.

---

### C-37: Reconciliation uses a pragmatic per-draw approximation, not principled probabilistic reconciliation — RESOLVED (relocated to views-frames)

**RESOLVED HERE 2026-07-31 (review-rr) — subject relocated to views-frames.** The reconciler (`proportional.py`, `grouping.py`, `module.py`) left this repo in **#62 / PR #63** and now lives in `views_frames_reconcile`; the vpp `ReconciliationModule` CIC was retired with it. Verified 2026-07-31: no `reconciliation/` sources exist under `views_postprocessing/` (only stale bytecode — C-47). The **methodological concern is unresolved and remains live in views-frames** (Epic 11 / views-platform/views-frames#131): the per-draw scaling is still a pragmatic approximation, the sample-alignment precondition still needs verifying against real pooled draws before reconciled uncertainty is consumed, and the Tier-2 escalation on wiring (pipeline-core#200) still applies **there**. Closed here because no vpp action can satisfy its trigger; **track it in views-frames.**

| Field | Value |
|-------|-------|
| ID | C-37 |
| Tier | 3 |
| Source | `manual` (2026-06-24) — phase-2 reconciliation migration |
| Trigger | When reconciliation is wired into a delivery and its uncertainty is consumed (intervals, scores), verify the method is the principled one — the current per-draw scaling can distort the joint predictive distribution |
| Location | `views_postprocessing/reconciliation/proportional.py` |

`reconcile_proportional` is a faithful numpy port of views-reporting's `ForecastReconciler.reconcile_forecast`: **top-down disaggregation using forecast proportions** (FPP3), applied **per posterior draw**. It rescales each marginal draw independently to hit that draw's country total, which implicitly assumes the grid and country samples are index-aligned joint draws. This is a pragmatic approximation, **not** principled joint probabilistic reconciliation (the IJF paper, PII `S0169207023001097` — exact title TBC; cf. FPP3 §reconciliation), under which the reconciled draws would be coherent samples from a single reconciled joint distribution (e.g. MinT-style projection on samples). The migration deliberately preserves the existing method first (parity proven bit-for-bit against the untouched views-reporting oracle, `tests/test_reconciliation_parity.py`); the upgrade is **gated behind** completing the move and wiring (slices 2-3) so behaviour change and relocation never mix. Until then, treat reconciled uncertainty as approximate.

See also the migration plan (reconciliation slices 2-4) and views-reporting issue #72 (the relocation).

**Update 2026-06-24 (expert-code-review, Kleppmann lens):** the per-draw index-pairing is only *valid* if the production cm and pgm forecasts are the **same joint posterior draws**. If they come from independent models (separate posteriors), pairing draw *s* of the grid with draw *s* of the country is arbitrary and the reconciled uncertainty is meaningless — and the parity fixture cannot detect this, because it manufactures aligned draws. **At S7 (#39) wiring, verify the sample-alignment assumption against the real pipeline as a hard precondition** (or escalate the C-37 upgrade). This is a correctness precondition distinct from the "is the method principled" question.

**Update 2026-06-24 (reframe — now near-term, not deferred):** this is no longer a someday concern. FAO (`rusty_bucket`) sidesteps reconciliation entirely (pure-grid ensemble aggregated *up* — sums by construction), but the **next UN-agency deliverable** is an FAO-like grid ensemble that **does** reconcile against a CM model, with **full pooled draws (~1024)** → **probabilistic** reconciliation. The reconciler is already probabilistic-ready (fully vectorized over samples), so the open question is purely C-37's: does that deliverable reconcile grid draws to a country **point total** (well-defined, no alignment needed) or to country **draws** (needs a defined draw-alignment — and today CM models are point-only / independently trained, so no aligned draws exist)? **This decision gates the probabilistic-reconciliation-on-`PredictionFrameEnsembleManager` work** (pipeline-core#200, under epic #193); resolve it once the UN models / CM target are defined.

**Calibration note (review-rr 2026-06-24):** stays **Tier 3 while unwired**, but **escalate to Tier 2 the moment reconciliation is wired into a delivery** — at that point a wrong sample-alignment assumption silently delivers *meaningless uncertainty* (a correctness risk, not maintainability). The wiring (pipeline-core#200) is the escalation trigger.

**Update 2026-06-26 (home change):** the reconciler (`proportional.py`, `grouping.py`, `module.py`) is relocating from this repo to the **`views_frames_reconcile` sibling** in the views-frames distribution (Epic 11, views-platform/views-frames#131) — its correct foundation home (CRP/SDP: a frame operation belongs in the frames family, not bolted onto FAO delivery). **C-37 and C-38 move with it** — track them in views-frames going forward. vpp's copy is deleted in #62 once views-frames v1.7.0 ships (release → repoint views-models#191 → delete).

---

### C-34: Spatial coverage has no contract — no assertion of expected cell count anywhere — MERGED into C-30

| Field | Value |
|-------|-------|
| ID | C-34 |
| Resolved | 2026-07-31 (merged) |
| Resolution | **Merged into C-30 during review-rr (2026-07-31); ID retained as a forwarding stub so existing cross-references resolve.** C-34 registered the absence of any expected-cell-count assertion, with the coverage decision split across three repos (views-models region string → views-datafactory cell-set → consequences here). Both C-34 and C-30 are now implemented by **one module** (`delivery/coverage.py`: `EXPECTED_CELLS_BY_REGION`, `EXCLUDED_GIDS_BY_REGION`, wired into the manager's `_check_coverage`) and were discharged by **one event** — run-0 on 2026-07-27 reported 64,742 distinct cells / 28,356,996 rows for `land_gaul`, exercising both guards end-to-end at global scale for the first time. Tracking them separately doubled maintenance without adding signal. C-34's distinctive contribution — that the real trigger is an *upstream* region/cell-set change in either of two other repos — is carried verbatim into C-30's rewritten trigger and Location. **See C-30.** |

---

### C-32: Unbudgeted memory at global enrichment volume — RESOLVED (measured in run-0)

**RESOLVED 2026-07-27 — measured, not merely deferred (recorded review-rr 2026-07-31).** The trigger read *"Before the first global historical run, verify peak memory of joining 9 metadata columns onto ~28M rows… roughly 8–20 GB at this scale."* That estimate proved right for the pandas path — run 0's first attempt was **OOM-killed at 23.8 GB** on the 31 GB host. The fix was representational rather than the categorical-dtype mitigation proposed below: the historical path went frame-native (#126, `get_feature_frame` → `views_frames.FeatureFrame`, artifact built via pyarrow in `unfao/historical.py`) and the forecast leg streams per target. **Re-run 2026-07-27: peak RSS 5.6 GB across 28,356,996 rows at 64,742 cells, no OOM, clean exit.** The concern is empirically discharged. Memory remains a live *budget* on the 31 GB host — see the Blind Spots note in the review-rr report of 2026-07-31 recommending an incident entry for the OOM chain, which is **not** registered by this pass.

| Field | Value |
|-------|-------|
| ID | C-32 |
| Tier | 2 — realistic MemoryError mid-`_transform` on the planned global run; fails after the fetch succeeded, late in the pipeline |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | Before the first global historical run, verify peak memory of joining 9 metadata columns onto ~28M rows (64,818 cells × ~432 months) — four string columns as pandas object dtype cost roughly 8–20 GB at this scale |
| Location | `views_postprocessing/unfao/managers/unfao.py:154-163` (the metadata join); any replacement enricher |

Object-dtype strings (`admin1_gaul0_name`, `admin1_gaul1_name`, `admin2_gaul2_name`, `country_iso_a3`) broadcast to 28M rows dominate memory. Mitigation is cheap and should be built into any new enricher from day one: pandas categorical dtype for the string columns (~10× reduction; the underlying uniques number in the low thousands). A full-volume dry run (fetch → enrich → validate → local parquet, no upload) before delivery day is the verification.

---

### C-19: Systematic ADR-008 non-compliance — 23 of 24 raises lack preceding log — RESOLVED

**RELOCATED 2026-07-31 (review-rr — placement fix only, no change of substance).** This entry was marked RESOLVED on 2026-06-28 but was never physically moved out of `## Open Concerns`; it and C-45 are the sole cause of the header count mismatch corrected in this pass (Open 25→27 actual, now 19 after all relocations). Re-verified in code 2026-07-31: log-before-raise holds at `enrichment.py:46/53/106` and `extraction.py:46`. The field table below retains its original Tier/Trigger/Location rows for provenance.

| Field | Value |
|-------|-------|
| ID | C-19 |
| Resolved | 2026-06-28 |
| Resolution | Every live-path structural raise now logs-before-raise. The mapper portion (20 raises) went with the deleted runtime mapper (C-39); the 3 `unfao.py` manager raises were fixed in #13; and the residual `enrichment.py` (`:42,:50,:103`) + `extraction.py` (`:39`, a module logger was added) raises got `logger.error`-then-raise in the tech-debt-cleanup pass (2026-06-28). The only raises now lacking a preceding log are in `unfao/frames.py` (the views-frames conformance adapter), which is **not on the live delivery path** and is tracked separately by **C-45**. ADR-008 compliance holds across the live path. |
| Tier | 3 |
| Source | `falsification-audit` (2026-06-02) |
| Trigger | When a structural failure occurs in `GaulLookupEnricher` (lookup missing/incomplete, or an absent gid column) or in the `extraction` seam and the operator searches logs for context, verify the exception was preceded by a `logger.error` — these raises currently have none |
| Location | `views_postprocessing/unfao/enrichment.py:42,50,103`; `views_postprocessing/unfao/extraction.py:39` |

ADR-008 requires structural failures to be both logged persistently AND raised explicitly. Three validation methods in mapping.py and the C-01 fix in unfao.py were fixed with log-before-raise. 20 raises in mapping.py and 3 in unfao.py remain unfixed.

Part of Cluster B (expanded scope).

**Update 2026-06-24:** the mapper portion (20 of the 23 raises, in `mapping.py`) is gone with the deleted runtime mapper (C-39); the **3 raises in `unfao.py`** remain (tracked by issue #13). Narrowed to the manager.

**Update 2026-06-28 (re-scoped after `review-base-docs`):** the `unfao.py` residual is **resolved** — the 3 manager raises got log-before-raise in #13 (`unfao.py:72,84,293`), and the `FileNotFoundError` at `:112` is logged by its enclosing `_read_forecast_data` try/except. So both historical locations (mapper, manager) are now clear. **The live ADR-008 residual moved to two modules the original audit never covered:** `enrichment.py` (`:42` lookup-missing, `:50` lookup-missing-columns, `:103` absent gid column) and `extraction.py:39` (the seam's index/column `KeyError`) — these raise without a preceding `logger.error`. Practical risk is low (the raises are loud, not swallowed — the messages are descriptive); the gap is uniform log-before-raise convention in live code. Tier 3 (observability/maintainability, no silent corruption). *(This residual was then fixed the same day — see the Resolution field above.)*

---

### C-08: Planar area calculation on geographic (degree-based) coordinates — RESOLVED (relocated to views-datafactory)

**RELOCATED / RESOLVED HERE 2026-07-31 (review-rr).** This entry's own 2026-06-24 update already concluded: *"this repo's mapper area-math is deleted (C-39); no degree-based area math runs in this repo anymore… a cross-repo views-datafactory concern. Tracked there, not here."* Verified 2026-07-31: zero degree-based area computation exists in `views_postprocessing/` — enrichment is a keyed gather against the precomputed ADR-011 lookup, and geopandas/shapely are absent from the dependency tree. The high-latitude distortion question is real but is **views-datafactory's**, in the area-majority script that builds the GAUL parquets this repo consumes. Kept open here for 5 weeks as a ghost tracker with an orphaned trigger (no vpp action could satisfy it). Closed here; **the concern itself remains live in the views-datafactory register.**

| Field | Value |
|-------|-------|
| ID | C-08 |
| Tier | 3 |
| Source | `repo-assimilation` (2026-06-02) |
| Trigger | When processing PRIO-GRID cells above 55°N or below 55°S (e.g., Russia-Ukraine border, Nordic countries), verify that country/admin assignment is correct for cells straddling boundaries |
| Location | `views_postprocessing/unfao/mapping/mapping.py:649-650,920,1192,1428` |

All overlap ratio calculations use `.area` on EPSG:4326 geometries, which produces values in square degrees. At the equator, 1° longitude ≈ 1° latitude in distance. At 60°N, 1° longitude ≈ 0.5° latitude in distance, distorting area by up to 2x. For border cells at high latitudes, this distortion could theoretically cause incorrect assignment to the wrong country/admin region. In practice, most VIEWS conflict prediction zones are equatorial/mid-latitude, limiting the impact. No projection to equal-area CRS is performed before area calculations.

**Update 2026-06-12 (expert-code-review):** The "equatorial/mid-latitude, limiting the impact" rationale dies with the planned global coverage — Russia, Scandinavia, and Canada (55°N+) enter scope when the region switches to `"land"`. Mitigating consideration: within a single 0.5° cell, all candidate polygon intersections sit at the same latitude band, so the cos(lat) distortion multiplies all candidates roughly equally and largely cancels in the *ranking* — this applies to both this repo's mapper and the datafactory's area-majority script. Required action before global delivery: one falsification probe on ~20 border cells above 55°N comparing degree-based assignment against an equal-area-projected computation. See C-31 (mapper unverified at global scale).

**Update 2026-06-24 (narrowed to the datafactory dimension):** this repo's mapper area-math (`mapping.py:649-650,920,1192,1428`) is deleted (C-39); no degree-based area math runs in this repo anymore. The remaining concern is the **views-datafactory** area-majority script's degree-based area math at high latitudes — a cross-repo views-datafactory concern (this repo now consumes the lookup built from those parquets, so any distortion is upstream). Tracked there, not here.

---

### C-55: ADR-013 §10/§11 — vendoring mechanism leaned on the README; two verification vehicles conflatable; stale guard tense — RESOLVED same day; AUDIT SERIES COMPLETE

| Field | Value |
|-------|-------|
| ID | C-55 |
| Tier | 4 — doc-only: §10.1 commanded cross-repo vendoring without defining the root-hash mechanism or naming the fixture path (both lived in the README/Post-adoption record); §11.1's skeleton S=8 and the fixture's S=4 invited conflation; §11.4 said the legacy guards "can ship" when both had already merged. No correctness impact. |
| Source | `falsify` (2026-07-19) — audits of "§10 / §11 are sufficient and unambiguous"; both **CONTESTED (0 hard, 2 soft each)** |
| Trigger | (historical) A vendoring implementer reconstructing the root-hash mechanism from the README instead of the contract; a reader taking S=8 vs S=4 as a contradiction |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §10.1, §11.1, §11.4 |

**RESOLVED 2026-07-19 (same day):** §10.1 self-contains the mechanism (path, per-file `SHA256SUMS`, root hash = SHA-256 of `SHA256SUMS`); §11.1 distinguishes the two vehicles; §11.4 re-tensed (both guards merged 2026-07-15; Hop-B production deploy rides **views-faoapi C-161**). Enforcement: `tests/test_falsify_adr013_s10_11.py`.

**Series closure:** with this entry, every section of ADR-013 (§0–§11) has been independently falsification-audited (C-48–C-55): 5 FALSIFIED, 3 CONTESTED, 2 sections SURVIVED outright (§1, §9); every finding fixed same-day; 40 permanent guards enforce the fixes. Recurring root cause across the series: the golden fixture silently carried spec the prose drifted from — now everywhere the prose names the fixture as its executable pin.

---

### C-54: ADR-013 §7/§8 — stale cross-repo status claims and a dangling hardening intent (§1/§9 survived audit) — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-54 |
| Tier | 4 — doc-only staleness: a completed duty still commanded (§7c — faoapi#100 was already retitled), an undated env-fix claim superseded by newer seat forensics (§7b), and a "to be filed" hardening intent with no tracking issue (§8). No correctness impact; the drift class is the register's known doc-vs-reality disease (C-42/C-47). |
| Source | `falsify` (2026-07-19) — batched audit of "§1/§7/§8/§9 are sufficient and unambiguous"; verdicts: §1 SURVIVED, §9 SURVIVED (the series' first clean sections), §7 CONTESTED (2 soft), §8 CONTESTED (1 soft) |
| Trigger | (historical) Acting on §7's prerequisites list as a to-do — re-doing the completed retitle, or hunting the stale collection-id framing instead of the four known env values |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §7(b), §7(c), §8 |

**RESOLVED 2026-07-19 (same day):** §7(b) re-dated with the views-models seat's 2026-07-19 forensics (four `APPWRITE_PROD_FORECASTS_*` values still absent; correct values known: db `file_metadata`, collection `production_forecasts`); §7(c) marked done with verification; §8's mmap/ordering hardening intent filed as **views-frames#199** and pointed. §9 gained a since-shipped marker on #269 (observation-level). Enforcement: `tests/test_falsify_adr013_s789.py`. Cross-refs: C-48–C-53 (audit series).

---

### C-53: ADR-013 §6 — NaN semantics and wiring status absent from the contract prose (code already correct) — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-53 |
| Tier | 4 — doc-only: the module (`delivery/draws.py`) was correct, tested, and documented both gaps itself; the contract prose lagged it. A §6-only reader could wrongly assume the gate screens NaN payloads (it deliberately doesn't) or that it is already wired (it isn't). No correctness impact. |
| Source | `falsify` (2026-07-19) — audit of "§6 is sufficient and unambiguous"; verdict **CONTESTED (0 hard, 2 soft)** — the series' first section with no hard finding: all four rules match the code exactly |
| Trigger | (historical) Relying on §6 alone to conclude NaN payloads are caught, or that the gate already runs in the delivery |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §6 |

**RESOLVED 2026-07-19 (same day):** NaN note added (NaN rows count as non-degenerate — collapse detection only; null screening belongs to the null gates); wiring status dated (module merged PR #98; upload wiring lands with #91). Enforcement: `tests/test_falsify_adr013_s6.py`. Cross-refs: C-48–C-52 (audit series).

---

### C-52: ADR-013 §5 — sidecar column count wrong in prose; data-dependent dtype rule — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-52 |
| Tier | 3 (at finding) — a faithful reading of §5.1 produced a nonconformant file (priogrid_id as index instead of first column: the canonical file has 10 columns, prose said 9), and the dtype rule made the schema a function of the data (int64 vs float64 depending on whether a run contains a missing-geography cell) — a consumer type-handling trap at the vpp/faoapi boundary. Not Tier 2: the fixture parity test catches both divergences loudly before anything ships. |
| Source | `falsify` (2026-07-19) — maintainer-commissioned audit of "§5 is sufficient and unambiguous"; verdict FALSIFIED (2 hard, 4 soft) |
| Trigger | (historical) Building the #91 sidecar writer or the faoapi sidecar reader from §5 prose without diffing against the fixture bytes |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §5.1–§5.2 |

Hard: (P1) 10-column file with `priogrid_id` as first column vs prose "keyed by …, exactly these 9 columns"; (P2) data-dependent code dtype ("int64 when complete; float64 where NaN"). Soft: data source unnamed (P3); "preserved with NaN" imprecise for string nulls (P4a); **views-faoapi C-146** bare insider ref (P4b — foreign register, namespaced during review-rr 2026-07-31); "extended to the sidecar" future work in present tense (P5); column/row order pinned only in fixture bytes (P6).

**RESOLVED 2026-07-19 (same day):** §5.1 rewritten — 10-column truth with `priogrid_id` as a real first column; **dtype ruling (MINOR): `*_code` columns always float64** (one stable schema, matches canonical bytes); column order + ascending row order declared normative (§10 pins both); source named (ADR-011 `gaul_lookup.parquet`, datafactory area-majority); null-vs-NaN precision; **views-faoapi C-146** glossed; §5.2 re-tensed as future #91 work. Enforcement: `tests/test_falsify_adr013_s5.py` (7 guards, green). Recorded in the Post-adoption record.

Cross-refs: C-48–C-51 (the audit series), C-45 (the #91 wiring these rules land in), D-12.

---

### C-51: ADR-013 §4 — unpinned run-manifest, sidecar outside the commit ordering, and a phantom views-faoapi C-71 upload obligation — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-51 |
| Tier | 3 (at finding) — one protocol gap (sidecar outside the manifest-last commit ordering contradicted §4.2's torn-runs-invisible guarantee — an outage-shaped hole, loud not silent) and one factually wrong obligation ("views-faoapi C-71 approval fields" that do not exist in faoapi's mechanism) sat directly in the path of the #91 sink-adapter implementation. Not Tier 2: the hash-verification chain made every failure mode loud, and no implementation had yet built on the wrong text. |
| Source | `falsify` (2026-07-19) — maintainer-commissioned audit of "§4 is sufficient and unambiguous"; verdict FALSIFIED (4 hard, 2 soft) |
| Trigger | (historical) Building the #91 sink adapter from §4 prose — uploading the sidecar after the manifest, or hunting for nonexistent approval fields |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §4.1–§4.5 |

Hard: (P1) run-manifest fields unpinned; prose understated the canonical bytes (sidecar *object* with name+sha256, per-shard `target`/`time_id`); (P3) Hop-B file-name templates absent + document-`name`-vs-file-name duality unexplained; (P8) **sidecar outside the commit-marker ordering**; (P6) **"views-faoapi C-71 approval fields present" ground-truthed as nonexistent** — faoapi's C-71 is consumer-side env file-id lists (`APPWRITE_UNFAO_QUARANTINED_FILE_IDS` / `APPWRITE_UNFAO_APPROVED_FILE_IDS`, `prediction.py:17-38`); the clause imposed a phantom uploader duty. Soft: cell-count ruling not inherited (P2); §4.5(b) raw-table-read mechanics unstated (P5). §4.3 selection and §4.6 capacity math survived.

**RESOLVED 2026-07-19 (same day):** §4.2 rewritten around a field table matching the fixture bytes; §4.1b added (three Hop-B name templates + the two-names clarification); **ordering clarified (MINOR): manifest uploads only after every shard AND the sidecar**; **the views-faoapi C-71 upload obligation deleted with a dated correction** (mechanism documented as it actually is, composing with §4.4's manifest-as-control-point); §3.2's cell-count ruling inherited verbatim; §4.5(b) mechanics note added. faoapi seat notified on #100. Enforcement: `tests/test_falsify_adr013_s4.py` (6 guards, green). Recorded in the Post-adoption record.

Cross-refs: C-48/C-49/C-50 (the audit series — same fixture-carries-the-spec root cause), **views-faoapi C-161** (the deploy gate the #91 leg still waits on — foreign register, namespaced during review-rr 2026-07-31).

---

### C-50: ADR-013 §3 mis-described the Hop-A manifest and left the cell-count scope ambiguous across the producer/consumer boundary — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-50 |
| Tier | 3 (at finding) — the prose asserted a manifest field ("store file-ids") the canonical bytes never carried, and `expected_cell_count`'s scope (per-shard N vs per-target total) was undecidable exactly where two repos implement against each other; a divergent producer reading would have failed run 0 on a spec ambiguity. Not Tier 2: both shipped implementations were verified to have independently converged on the same reading before any live run — the divergence was possible, not present. |
| Source | `falsify` (2026-07-19) — maintainer-commissioned audit of "§3 is sufficient and unambiguous"; verdict FALSIFIED (2 hard, 4 soft) |
| Trigger | (historical) A seat re-implementing or reviewing the Hop-A manifest from §3 prose — writing `file_id` fields, or an `expected_cell_count` totalled across months |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §3.1–§3.3 |

Hard: (P1) "store file-ids" prose contradiction vs the fixture manifest (name + sha256, no file-id) + no manifest field names pinned; (P6) `expected_cell_count` scope ambiguity. Soft: `identifiers.npz` member names/dtypes unpinned (P2); hash algorithm/coverage unstated (P3); manifest store-document fields unspecified (P5); `.tap` unexplained (P7). Root cause: same as C-49 — the fixture silently carried the spec and the prose drifted, here into outright error.

**RESOLVED 2026-07-19 (same day):** §3.2 rewritten around a field table matching the fixture bytes exactly; the file-id claim corrected in place with a dated marker; **scope ruling pinned: `expected_cell_count` = per-shard N, uniform across the run's months, ragged run malformed** — pinned only after verifying both shipped implementations agree (pipeline-core `sampled_forecast_publisher.py:261-268` enforces equal cells/month; vpp `track_a_source` checks per-shard); `time.npy`/`unit.npy`/int64, SHA-256-of-whole-zip, manifest store-doc fields, and `.tap` = Track A Package all pinned. Convergence note posted on pipeline-core PR #276. Enforcement: `tests/test_falsify_adr013_s3.py` (6 guards, green). Recorded in the Post-adoption record.

Cross-refs: C-48/C-49 (same audit series and disease class), C-42/C-47 (prior doc-vs-reality drift).

---

### C-49: ADR-013 §2 under-specified its own header fields; key order load-bearing but ungoverned — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-49 |
| Tier | 3 (at finding) — the header spec every implementing repo writes/validates against left run_id/generated_at/sharding/time_id semantics and enum values to guesswork, and omitted the key-order rule that §10's byte-pinned fixture makes load-bearing: two independent implementers could both believe themselves conformant and disagree (spec-level declare-don't-infer violation across repos). Not Tier 2: the golden fixture existed as executable ground truth, bounding the divergence in practice. |
| Source | `falsify` (2026-07-19) — maintainer-commissioned audit of "§2 is sufficient and unambiguous"; verdict FALSIFIED (2 hard, 3 soft) |
| Trigger | (historical) A seat in pipeline-core or faoapi writing a header writer/reader from §2 prose alone, without diffing against the fixture bytes |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §2 |

Hard: (P1) field semantics underdefined — `run_id` minting/uniqueness, `generated_at` format, `sharding` scheme/index/count, `time_id`-to-shard relation, `frame_type`/`representation` enums; (P2) key order ungoverned while §10 pins the header byte-for-byte. Soft: (P3) §2.1 "open to additions" vs §2.2 "provenance exactly three keys" collision for nested keys; (P5) §2 named neither §7a nor §10 — its formats were silently outsourced to an unnamed fixture; (P6) "gid/id epic" insider jargon. Root cause: §2 specified rules-*about*-the-header well but not the fields themselves.

**RESOLVED 2026-07-19 (same day):** per-field table added to §2 (type, format, minting, closed-object markers); key-order note (writers emit the pinned order, readers MUST NOT depend on it, §10 is why); "fixture governs" note; **clarification adopted (MINOR, §2.1): rule-1 openness is top-level only — `id_semantics`/`provenance`/`sharding` sub-objects are closed**; §7a/§10 cross-referenced; gid/id epic glossed. Enforcement: `tests/test_falsify_adr013_s2.py` (5 audit stubs → permanent guards, green). Recorded in the ADR's Post-adoption record.

Cross-refs: C-48 (same disease class in §0, same audit day), C-42/C-47 (prior doc-vs-reality drift).

---

### C-48: ADR-013 §0 misled on operational status and omitted core flow semantics — RESOLVED same day

| Field | Value |
|-------|-------|
| ID | C-48 |
| Tier | 3 (at finding) — a governance document read by all four repos' seats stated "FAO's exists now" with no execution-status information, inviting cross-repo readers to believe the contract flow was live while the sink leg was unbuilt, the Hop-B guard undeployed (**views-faoapi C-161**), and FAO serving empty. Misleading a seat into acting on that (e.g. uploading before the guard) was the realistic harm. Not Tier 2: the §11.4 constraint existed elsewhere in the same document. |
| Source | `falsify` (2026-07-19) — maintainer-commissioned audit of the claim "§0 alone suffices to understand the flow"; verdict FALSIFIED (2 hard, 5 soft) |
| Trigger | (historical) A cross-repo seat reading §0 as its only source before acting on the wire |
| Location | `docs/ADRs/013_sampled_forecast_wire_contract.md` §0 |

Hard: (P4) no current-execution-status anywhere in §0 + "FAO's exists now" misdirection; (P2) complete-or-invisible/commit-marker semantics absent. Soft: PFE/Hop A/Hop B undefined in §0 (P1b); no-collapse gate unexplained (P3); historical bypass absent (P6); undated "today" ×2 (P5b + one more found at fix time); §0.2-vs-row-6 preconditions tension (P7). Root cause: §0 grew as an ownership section, then was asked to be a flow summary.

**RESOLVED 2026-07-19 (same day):** §0.2a "Execution status" block added (dated, points at the Post-adoption record as the running log; states plainly what is built, unbuilt, undeployed, and that FAO serving is currently empty); commit-marker sentence in role 1; no-collapse gloss, legacy-vs-contract clarification, and historical-bypass note in role 2; §0.2/role-5 tension reconciled in place; PFE + hops anchored in the table legend; both undated "today"s dated. Enforcement: `tests/test_falsify_adr013_s0.py` — the 5 audit stubs converted to permanent guards, all green.

Cross-refs: **views-faoapi C-161** (the deploy constraint §0.2a now surfaces — foreign register, namespaced during review-rr 2026-07-31), C-42/C-47 (prior doc-vs-reality drift instances), D-12 (§0.3 generalization work in the same section).

---

### C-35: Invalid `-99` country code shipped to FAO for Somaliland cells — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-35 |
| Resolved | 2026-06-24 |
| Resolution | The mapper that sourced `country_iso_a3` from Natural Earth (emitting the `-99` sentinel for Somaliland, N. Cyprus, Kosovo, …) was deleted (C-39, PR #42). Enrichment now uses the GAUL lookup, which has **zero `-99` codes** across all 64,742 global cells (Somaliland → `SOM`, matching FAO's GAUL). The defect is eliminated as a side effect of the engine swap. |

---

### C-31: Runtime mapper unverified and unverifiable at global scale — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-31 |
| Resolved | 2026-06-24 |
| Resolution | The runtime mapper (`mapping.py`) was deleted (C-39, PR #42), so a global run *via the mapper* can no longer happen — this entry's hazard is moot. The enricher-path global-scale concerns are tracked separately (C-30 coverage, C-32 memory, C-34 coverage contract). D-08 (the swap-to-lookup-first decision this entry argued for) was executed. |

---

### C-23: Algorithmic divergence — area-based vs centroid-based GAUL mapping across VIEWS platform — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-23 |
| Resolved | 2026-06-24 |
| Resolution | The platform mapping divergence was resolved upstream (views-datafactory area-majority, 2026-06-12), and the residual ISO-code difference disappeared when ADR-011's GAUL lookup replaced the runtime mapper (C-39, PR #42). The lookup (built from the factory's GAUL parquets) is now the single enrichment source — no second algorithm remains to diverge from. |

---

### C-41: Vestigial Git LFS config breaks routine git operations (no git-lfs installed) — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-41 |
| Resolved | 2026-06-24 |
| Resolution | Retired Git LFS (C-41 fix, this PR): removed the all-shapefile `.gitattributes` LFS rules (matched zero files after C-39) and unwired the local LFS filter config + the four `.git/hooks` LFS hooks. Verified: `git commit`/push now run with no `--no-verify` and no `git-lfs: not found` error. No LFS-tracked files remain in the repo. |

---

### C-10: Manager-to-Mapper coupling via module-level global state — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-10 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the module-level `_DEFAULT_MAPPER` global and `get_default_mapper()` coupling this concern describes no longer exist (the manager now uses `GaulLookupEnricher`). |

---

### C-04: Inconsistent forward/reverse mapping breaks expected bijection — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-04 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-02: Module-level side effect blocks package import on shapefile failure — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-02 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-05: Multiple methods crash when disk caching is active — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-05 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-06: Massive code duplication across disk/memory cache branches — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-06 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-11: PriogridCountryMapper is a god class bridging 3 architectural concerns — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-11 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-12: Silent wrong-country assignment when geometry intersection fails — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-12 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-14: Stale disk cache returns outdated mappings after shapefile update — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-14 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-16: Thread-unsafe caches under concurrent enrichment — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-16 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-17: Implicit column naming contract between mapper and manager — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-17 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-20: ZeroDivisionError on degenerate zero-area cells — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-20 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-21: Batch enrichment failures produce incomplete DataFrames (observability-only fix) — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-21 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### C-39: Dead geopandas runtime mapper + 1.3 GB shapefiles — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-39 |
| Resolved | 2026-06-24 |
| Resolution | Deleted the dead mapper cluster on branch `chore/remove-dead-geopandas-mapper`: `unfao/mapping/` (3,171 lines), the 1.3 GB `shapefiles/` bundle, the mapper tests + `conftest.py`, the two ADR-011 diff scripts, and the CIC — **45 files / ~5,069 deletions**. **geopandas + shapely are now gone from the codebase** (zero references); `cachetools` dropped from pyproject (mapper-only). Verified: deletion broke nothing (keep-tests green). **Dissolves the old-mapper concern cluster** — C-02, C-05, C-06, C-11, C-12, C-14, C-16, C-17, C-19, C-20, C-21 and D-01, D-02 describe code that no longer exists; they are superseded by this deletion and should be relocated to Resolved in a register-curation pass. (C-08's high-latitude-area note also dies on the mapper side; its datafactory dimension stays under C-31.) |

---

### C-01: Silent upload of incomplete geographic metadata to UN FAO — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-01 |
| Resolved | 2026-06-02 |
| Resolution | Re-enabled null validation in `_validate()`. Nulls logged at ERROR and raise `ValueError`. |

---

### C-18: Global warning suppression hides correctness signals — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-18 |
| Resolved | 2026-06-02 |
| Resolution | Removed `warnings.filterwarnings("ignore")` from module scope (line 26). Replaced with targeted `warnings.catch_warnings()` in `_load_priogrid()` scoped to the CRS centroid warning only. All other Python warnings are now active process-wide. D-03 decision applied to code. |

---

### C-36: Permanently-red test suite makes the CI/ship-it gate unable to detect new regressions — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-36 |
| Resolved | 2026-06-22 |
| Resolution | Converted the 43 permanently-failing tests to `xfail(strict=True)` so the suite is green-when-healthy: **119 passed / 43 xfailed / 0 failed**. The 40 falsification probes carry module-level `pytestmark` (plus a per-function mark on `r3_03`); the 3 cross-repo gates in `test_datafactory_deploy_readiness.py` are `xfail(strict)` tracked upstream as **views-datafactory#223** (provenance omits `admin_digest` → stale served grid) and **views-datafactory#224** (development version `1.3.0` collides with released tag). A real regression now surfaces as a `failed` (distinct from the expected xfails), and any probe/gate that *starts passing* flips to a strict failure forcing promotion. Residual (accepted): the pure-`assert False` probes don't test the live condition, so a fixed finding won't auto-flip — inherent to marker-style tests; the deploy gates, being conditional, do auto-flip. |

---

## Resolved Disagreements

### D-07: Historical data route — keep pipeline-core dispatcher vs call datafactory directly — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-07 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Ousterhout/Hickey: the postprocessor uses ~20% of `ViewsDataLoader`'s services (it passes `use_saved=False, validate=False, self_test=False`) while paying 100% of the seven-hop indirection — call `datafactory_query.load_dataset()` directly and own the three renames. Martin/GoF/Feathers: the dispatcher seam absorbed the viewser→datafactory migration with zero consumer changes and will absorb the next one; bypassing it re-couples the postprocessor to the current backend. |
| Location | `views_postprocessing/unfao/managers/unfao.py:44-59`; views-pipeline-core `modules/dataloaders/dataloaders.py:1088-1224` |
| Status | Open. Review recommendation: keep the pipeline-core route, but pass explicit `month_first/month_last` instead of partition semantics, consume `get_data()`'s return value (C-29), and re-enable validation once it supports datafactory sources. Decide alongside ADR-011 since both touch the same manager. |

**Resolved (2026-06-26) — maintainer's data-sourcing principle.** *Data-related facts — data, metadata, validity dates, country/admin codes — come from the **producer** (views-datafactory, or viewser until phased out), **not** routed through pipeline-core. pipeline-core is the orchestration framework, not a data pass-through; depending on it for data facts couples the delivery to an unstable, mid-migration hub (SDP) and risks cycles (ADP).*

Concretely: **(1)** producer-published facts (e.g. `last_valid_month_id`, region cell-counts) are read **directly from the producer** — pipeline-core must not be a lossy intermediary that drops them. First instantiated in S2 (#52): `views_postprocessing/unfao/source_metadata.py` reads `last_valid_month_id` straight from datafactory's `.zattrs`, never via the loader that discards it. **(2)** This decides the disagreement toward the Ousterhout/Hickey side **for facts**, but does **not** mandate ripping out the dispatcher wholesale: its source-abstraction (viewser↔datafactory routing) retains value for the **bulk data fetch** during the viewser phase-out. The principle is *'don't route through pipeline-core just for the sake of it / don't depend on it for what it merely passes through or drops'* — not *'never use the dispatcher.'* The earlier review recommendations for the bulk fetch (explicit month range; consume `get_data()`'s return value — C-29) still stand. Net: **the producer is the source of truth for data + facts; pipeline-core orchestrates.**

---

### D-10: The 82 GAUL-uncovered cells — exclude, crash, or negotiate with FAO — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-10 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Fail-loud purism: let validation crash and force the conversation — never silently drop cells. Pragmatic exclusion: drop with a named, count-asserted, logged exclusion list. Diplomatic: ask FAO before shipping anything. |
| Location | `views_postprocessing/unfao/managers/unfao.py:188-221`; the 82 gids enumerated in C-30 |
| Status | **Resolved direction (2026-06-12): fix upstream in views-datafactory.** User decision, superseding the review's exclusion-list adjudication. A new bundled curated region (`land ∩ gaul0_code != -1`, 64,736 cells — e.g. `land_gaul`) is added to `datafactory_query` alongside `land` and `africa_me_legacy`, with generation script, provenance, and a count-pinning test. The postprocessor keeps zero spatial knowledge; its invariant simplifies to "every arriving cell must enrich completely — any null crashes" (the existing `_validate()` gate, unchanged). The `land` region itself is NOT redefined (other consumers depend on its physical-land semantics). Forecast-path residual: unmatched gids null→crash via left merge + validation; pin with one test. FAO disclosure of the 82 excluded sub-Antarctic cells still required in the release note. Closes the postprocessor side of C-30; C-34's coverage test becomes "100% completeness for the configured region." |

---

### D-08: Global delivery path — scale up the runtime mapper vs swap to the precomputed lookup first — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-08 |
| Source | `expert-code-review` (2026-06-12) |
| Perspectives | Feathers' instinct: the mapper is production-proven and the region change is one config line — don't swap components days before a deadline. Kleppmann/Nygard/Ousterhout: the mapper is *unverifiable at global scale before running it* (C-31: unknown null count, runtime, memory; C-08 newly in scope), while the lookup's complete global failure set is exactly 82 named cells, verified locally (C-30). |
| Location | `views_postprocessing/unfao/managers/unfao.py:154-160`; `mapping.py`; views-datafactory `data/raw/gaul_admin/*.parquet` |
| Status | Open — user decision pending. Review adjudication: **swap to the lookup first, then go global.** The "don't swap before a deadline" rule assumes the old part is known-good for the new job; here it is known-good only for a job 5× smaller and cannot be tested for the new job until the moment it matters. Enumerable risk beats discoverable risk on a deadline. Prerequisite: shadow diff old-vs-new on africa_me (13,110 cells) on the production machine. |

**Resolved by events (2026-06-24):** the swap was executed — the runtime mapper was deleted (C-39, PR #42) and `GaulLookupEnricher` is the enrichment path. The review adjudication ('swap to the lookup first, then go global') is now the shipped state.

---

### D-05: Strategic direction — eliminate runtime mapper vs keep area-based algorithm — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-05 |
| Source | `manual` (2026-06-02) — external assessment |
| Perspectives | Path A: area-based is a FAO requirement → precompute lookup table. Path B: centroid-based acceptable → eliminate mapping.py entirely. Both eliminate 774 MB shapefiles, geopandas, and 3,100-line mapper. |
| Resolution | **Resolved (2026-06-02): Path A confirmed.** FAO-FSFC provided written confirmation (Release Note 02, `summary.tex`) agreeing to area-majority allocation as the locked aggregation rule: "Each PRIO-GRID cell is assigned to a single country using an area-majority rule." The area-based algorithm is a contractual requirement, not a historical accident. Path B (centroid-based) is off the table. Next step: build a one-time precomputed area-based lookup table (~65K rows, Parquet) and replace the 3,100-line runtime mapper with a dictionary lookup. This still eliminates geopandas, the shapefile bundle, and the runtime spatial operations — but preserves the area-majority assignment rule. |
| Update 2026-06-12 | **Upstream resolution deployed.** views-datafactory shipped area-majority GAUL assignment (issue #115 → PR #127, ADR-039 there, v1.2.28/29). All 7 GAUL parquets (codes + names + iso3) regenerated June 11 as area-majority, 259,200 rows each, mutually consistent (13,105/13,110 africa_me cells fully attributed; 5 pure-ocean cells unassigned). The precomputed lookup table can now be built by joining the factory parquets — no LFS, no shapefiles, no this-repo mapper run needed. The platform-level mapping divergence (centroid in factory vs area-majority here) no longer exists. See `docs/cross_repo_integration_report.md` and ADR-011 assessment §10. |

---

### D-01: Cache strategy refactoring — extract now vs. characterize first — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-01 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### D-02: Thread safety fix — lock caches vs. remove threading — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-02 |
| Resolved | 2026-06-24 |
| Resolution | The `PriogridCountryMapper` runtime mapper was deleted (C-39, PR #42); the code this concern describes no longer exists. |

---

### D-03: Warning suppression — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-03 |
| Resolved | 2026-06-02 |
| Resolution | Beck/Ousterhout consensus applied to code: targeted `warnings.catch_warnings()` for CRS centroid warning only. Global suppression removed. |

---

### D-04: Geometry correction — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-04 |
| Resolved | 2026-06-02 |
| Resolution | Kleppmann/Feathers consensus applied to code: `make_valid()` called in `_load_and_preprocess_naturalearth`, `_load_priogrid`, `_load_admin_data`. |

---

### D-06: C-24 schema divergence — RESOLVED

| Field | Value |
|-------|-------|
| ID | D-06 |
| Resolved | 2026-06-03 |
| Resolution | **Possibility B confirmed.** Investigation of views-faoapi (`/home/simon/Documents/scripts/views_platform/views-faoapi/`) shows that `FAOApiManager` downloads from Appwrite, wraps in `FAO_PGMDataset`, and serves via HTTP with NO column renaming. `dataframe_to_dict()` (api.py:182-191) passes columns through as-is. `_METADATA_COLS` in handlers.py:1146-1156 lists the postprocessor's exact column names. The column renaming from postprocessor names to FAO contract names (Release Note 01 Topic C) was never implemented. FAO receives `country_iso_a3`, `admin1_gaul1_code`, `pg_xcoord` — not UN M49, `ADM1_CODE`, `lat`. This is a genuine schema mismatch between contract and implementation, but it is NOT this repo's responsibility to fix — the renaming belongs in views-faoapi. The postprocessor should keep its current column names. |

---

## Register Conventions

- **ID format:** `C-xx` for concerns, `D-xx` for disagreements. IDs are permanent — gaps in numbering indicate merged or resolved entries
- **Sources:** `repo-assimilation`, `expert-review`, `test-review`, `falsification-audit`, `clean-architecture-review`, `pr-review`, `tech-debt-audit`, `incident`, `manual`
- **Resolution:** Move to "Resolved Concerns" or "Resolved Disagreements" with date and summary. **Moving is physical** — an entry whose body says RESOLVED must not remain under `## Open Concerns` (this drift caused the 2026-07-31 header mismatch)
- **Relocated (added 2026-07-31):** when the *code* an entry describes leaves this repo, resolve the entry **here** with a forwarding pointer to the owning repo — do not keep it open as a ghost tracker with a trigger no local action can satisfy. The concern stays live in the destination register. Precedent: C-08 → views-datafactory, C-37/C-38 → views-frames
- **Merged (added 2026-07-31):** when two entries share one implementation *and* one verification event, merge into the lower ID and leave the higher as a forwarding stub in Resolved, so existing cross-references still resolve. Precedent: C-34 → C-30
- **Foreign register IDs (added 2026-07-31):** always namespace IDs belonging to another repo's register — `views-faoapi C-161`, `views-pipeline-core C-59` — never a bare `C-161`, which a reader will search for in this file and not find
- **`[backlog]` tag (added 2026-07-31):** Tier 4 entries kept for completeness rather than active risk management, typically mirrored by a GitHub issue. Skip them when prioritising
- **Expired triggers (added 2026-07-31):** a trigger whose event has already occurred is worse than a vague one — it reads identically to a pending trigger and silently misreports state. On firing, rewrite the trigger and re-tier in the same pass
- **Header counts:** Manually maintained — update whenever a concern is added, merged, relocated or resolved. Verify Open + Resolved = Total against the actual `### C-` counts per section
- **Governed by:** ADR-010
