# Technical Risk Register

| Register Info     | Details                              |
|-------------------|--------------------------------------|
| Project           | views-postprocessing                 |
| Owner             | Dylan Pinheiro / PRIO MD&D Team      |
| Last Updated      | 2026-08-21                           |
| Total Concerns          | 112                                   |
| Open Concerns           | 32                                   |
| Resolved Concerns       | 80                                   |

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
**Fix strategy:** the thin-shell de-inheritance C-40 prescribes — and which is **half-built**: the sink side landed (`_ContractStorePort`, moved to `<partner>/store_port.py` 2026-08-14 by C-99) and the invariants are already pipeline-core-free modules the manager calls (`delivery/*`, `unfao/historical.py`, `unfao/wire/`). The remaining half is the **input** side (loader + `PGMDataset`), gated on pipeline-core Epic #186/#207.
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
**Fix strategy:** this repo already solved this disease once — the ADR-013 audit series ended with a **permanent guard suite** (`tests/test_falsify_adr013_*.py` — `pytest --collect-only -q tests/test_falsify_adr013*.py` for the count, which moves), and the same pattern now guards the þing-01 invariants (`tests/test_env_declaration.py`, `tests/test_redaction_guard.py` — the latter briefly **only over the roots that still existed**, see C-74, resolved: a guard is only as good as the assertion that its inputs are real, and it now carries that assertion). There is **no equivalent for the register**. A small `tests/test_register_integrity.py` — header counts match section counts; no RESOLVED body under `## Open Concerns`; every `C-\d+`/`D-\d+` reference resolves or is namespaced to a foreign register — would make this class self-detecting.
**Resolution scope:** Full for the mechanical half.

**Succeeded by Cluster N.** This cluster's disease was governance prose drifting out of step with cross-repo state; its mechanical half is guarded now. What replaced it is broader and is tracked as **Cluster N, "This repository cannot see itself"** — the same surface, including the parts no guard reaches.

**✅ CLOSED 2026-08-21 (review-rr triage).** Every entry cited above is resolved, and the cluster's own prescription landed: it asked for *"a small `tests/test_register_integrity.py` — header counts match section counts; no RESOLVED body under `## Open Concerns`; every `C-\d+`/`D-\d+` reference resolves or is namespaced"*. That file exists and does exactly those three things, plus five more; it is green, and it caught two real errors during this week's registrations (a header count off by one, and a views-pipeline-core `C-241` written without its namespace).

**The residual, and it is this cluster's disease one level up.** The guard covers entries. It does **not** cover the Causal Clusters section — which is how this cluster sat with nine resolved entries and no closure marker until a triage read it by hand, and how Cluster J went on calling a resolved C-22 *"acute"*. **C-109** records the same shape for `Location` line numbers. Nothing is proposed here: the honest position is that the mechanical half is done and the prose half is checked by reading, which is what triage is for.

### Cluster J: Delivery aftercare has no mechanism
**Root cause:** the delivery pipeline is write-only — nothing exists downstream of upload for correction, recall, or provenance audit.
**Entries:** C-15, C-24, C-105 (added 2026-08-16 — a torn upload attempt is aftercare the write-only path has no answer for) — plus **C-22, RESOLVED**, which this line called *"acute"* until 2026-08-21
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
| **C-43, C-59, C-61** Cluster K's build-time guarantees | S2 | `tests/test_gaul_lookup_fidelity.py` — one file discharged three entries |
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
2. **The CI question is decided in writing but not implemented.** Three gated cross-repo checks run nowhere automatic. *(Largely implemented 2026-08-10 — ADR-016. Two of the three groups now run in CI; the datafactory group still cannot, because it needs raw data absent from that repository's git, which no CI change can supply.)* C-46's residual carries the argued recommendation — *do not couple per-PR CI to another repo's default branch; if wanted, a weekly scheduled check that opens an issue on divergence* — with a named trigger. **It is a decision awaiting an owner, not a task awaiting effort.**
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

### Cluster N: This repository cannot see itself
**Root cause:** the guards here are unusually good at checking code against a declaration, and absent wherever the subject is the repository's own prose, its own records, or its relationship to anything outside. Every entry below was filed separately; together they are one class.
**Entries:** C-109 (`Location` line numbers rot faster than the review cycle), C-107 (docstrings sit outside the doc-accuracy scan), C-95 (a verdict mis-cited in three places), C-110 (a release block this repo scheduled for itself, documented nowhere a releaser looks), C-111 (a release changes delivery behaviour and only the version number says so), C-112 (nothing observes what consumers actually run) — plus **C-81**, whose own headline number was falsified by PR #280 and stood stale for four days.
**Highest tier:** 2 (C-81)
**Fix strategy:** **not more guards.** C-109 records why the obvious mechanical check fails — content assertions need a second declaration that can itself go stale, which is ADR-014 §2's warning. What works is a *reading* pass: this cluster was assembled by `/review-rr strategic` on 2026-08-21, and four of its seven members were found by reading rather than by any test. Schedule the reading; do not build a linter for prose.
**Resolution scope:** Partial and by nature. C-107 and C-109 are closable as conventions (scan the docstrings; cite by symbol). C-111 and C-112 are closable as artifacts (a changelog; a pin check). C-95, C-110 and C-81 are closable only by someone re-reading what the register says and comparing it to what is true — which is the activity, not a deliverable.

**Why this cluster was late.** Six of its seven entries arrived between 2026-08-16 and 2026-08-21, during one sprint, each filed as an unrelated finding. The register had no cluster for them because the clusters describe *delivery* risks — inherited surface, go-global debt, aftercare, the lookup artifact. Nothing described the governance layer as a risk surface of its own, even though the register is the artifact four repositories read.

## Open Concerns

### C-98: A tripwire on another repo's release history watched our own pin, and reported two days late

| Field | Value |
|-------|-------|
| ID | C-98 |
| Tier | 3 — the guard worked and the claim it protected was corrected within the hour, so nothing was published wrong. What is registered is the *observation channel*, which was the wrong one and would be wrong again in the same shape. |
| Source | CI failure on PR #266, 2026-08-13 |
| Trigger | A guard is written whose subject is an event in another repository — a release, a tag, a published artifact — and the value it actually reads lives in this one. |
| Location | `tests/test_falsify_adr013_s2.py` (the retired `test_e3s_claim_about_unreleased_behaviour_is_still_true`); `docs/ADRs/013_sampled_forecast_wire_contract.md`, Erratum E3 |

ADR-013's Erratum E3 stated that a views-pipeline-core fix — an editable install reporting `"unknown"` instead of a stale version — was *"not yet in any released version."* That is a dated claim about someone else's release history, so a tripwire was attached to it: if the installed pipeline-core is a released distribution past 3.0.0, E3's wording is stale.

**The tripwire fired, in CI, exactly as designed, and E3 was wrong.** views-pipeline-core 3.0.1 was uploaded to PyPI on **2026-08-11 13:40 UTC** and does contain the fix — verified at the tag, not assumed: at 3.0.0 `_pipeline_core_version()` is `return version("views_pipeline_core")` with no editable detection; at 3.0.1 it reads `direct_url.json` and returns `"unknown"` when `dir_info.editable` is set. E3 now records the discharge.

**The defect is that it fired on 2026-08-13 and not on 2026-08-11.** The guard observed *our* installed distribution, so it could not see 3.0.1 until this repository's lockfile moved to it. For two days E3 carried a false claim about a released artifact and every check was green. The guard caught it only because the lock bump and the release inspection happened in the same change — had the bump come later, the staleness would have waited for it.

This is the same shape as vpp_017 §7a, arrived at from the other side: a check may rest on a fact we own, on a fact another repository has declared in the public registry, or on an outcome we can observe. Our pin is a fact we own, but it was standing in for *pipeline-core's release feed*, which is none of the three. The guard measured a proxy and reported the proxy's date.

**What replaces it is smaller on purpose.** E3 now says the lift is in force for producers running 3.0.1 or later, and no future release falsifies that — there is no expiry left to watch, so re-pointing the tripwire at 3.0.1 would be inventing one. The successor checks only that E3 does not regain the superseded sentence and still names the release that discharged it, mutation-proven on three branches. Related: C-86 (upstream editions), C-97.

---

### C-100: The "four-method port" has three used methods and a dead third module behind it

| Field | Value |
|-------|-------|
| ID | C-100 |
| Tier | 4 — no correctness impact; the code is unreachable, not wrong. Registered because deleting it is a decision (the second store, #97) rather than a cleanup, and because an unreachable method inside a seam four documents describe is the kind of thing that gets maintained forever by accident. |
| Source | Reading the whole port while fixing C-99, 2026-08-14 |
| Trigger | The second partner store (#97) is scoped, or anyone proposes deleting `contract/store_metadata.py` — at which point this entry says what it costs and what moves with it. |
| Location | `views_postprocessing/{unfao,crafd}/store_port.py` (`file_metadata`); `views_postprocessing/contract/store_metadata.py` |

`_ContractStorePort.file_metadata` has **no caller in the package**. Measured: `latest_file_id` is called three times and `download` three times, both in `contract/wire/source_selection.py`; `upload` three times — `contract/wire/sink.py:164` plus each partner's historical artifact at `managers/<partner>.py:325`; `file_metadata` is called by nothing. Its only body is a call to `contract/store_metadata.py:file_metadata`, whose own module docstring says *"the one caller is `_ContractStorePort.file_metadata`"* — true, and the chain terminates there. The module has tests (`tests/test_store_metadata.py`) and no production reader.

The "four methods" the docs describe (`docs/ADRs/015_the_pipeline_core_appwrite_import.md:70`, both `store_port.py:5`, `tests/test_store_port.py:20`) are not wrong — the port really does define four. What none of them says, because nobody had counted, is that three of them run and the fourth is reachable only from a test.

**Not fixed here on purpose.** C-99's change was a correctness fix on a live delivery path; deleting a public-ish port method and a contract module in the same commit would have mixed a refusal with a removal. It is also not obviously a deletion: the second prediction store (#97) is scoped to be sample-bearing and multi-target, and reading a selected file's identity metadata is the kind of thing that partner may need. The decision is "delete it or give it a caller", and it belongs with #97 rather than with a download bug.

Cross-refs: **C-99** (the fix that surfaced it), **C-97**, **C-33** (the same symbol exists twice by design).

---

### C-97: Coordinate values sit in docstrings and comments, where the scan deliberately does not look

| Field | Value |
|-------|-------|
| ID | C-97 |
| Tier | 3 — a decided position, not an accident, and the decision is defensible. It is registered because the decision was taken before anyone counted, and because a docstring is printed by pytest in a way a code constant is not. |
| Source | `/code-review max` on #242, 2026-08-12; count reproduced here |
| Trigger | **Either.** (a) A check whose failing function contains one of these values starts firing in CI. (b) Someone proposes widening the no-copy scan to docstrings — at which point this entry is the measurement that says what that would cost. |
| Owner | This repository. |
| Location | **Counting distinguishable coordinates only** — i.e. excluding the two whose declared values are this package's own directory names, which appear everywhere and are not evidence of anything. On that basis, measured across `git ls-files '*.py'`: **25 standalone occurrences in 8 files** (re-confirmed 2026-08-13; 2026-08-12, down from 33 in 9 when filed — #242 cleared the no-copy scan's own docstring and #248 cleared `tests/test_product.py`). Includes `views_postprocessing/{unfao,crafd}/managers/`, `contract/store_metadata.py`, `contract/wire/sink.py`. **The count moves whenever prose is edited; re-measure rather than cite it — and state which basis you used.** Counting *all* values including the package-name collisions gives 139 in 31 files on the same tree; an audit that did not know the basis reported 75 in 24 and read as a contradiction. The number was never wrong; the method was never written down. |

The no-copy scan compares string **constants** and excludes docstrings outright. That exclusion is C-57's recorded lesson: an early draft fired on refusal labels and on docstrings naming which store a function serves, and *"a guard that fails on `def file_metadata(record)` gets deleted — after which the real rule is unguarded"* (ADR-014 §3).

The position is still right. What was not known when it was taken is the count, and one consequence:

**A value in a docstring is printed by pytest that a value in a constant is not.** When any test fails, `--tb=auto` prints the failing function's source. So a registry value in the docstring of a *test* reaches a world-readable CI log on that test's next failure — which is how #242 found that the no-copy scan's own docstring carried three. That one is fixed. The others sit in functions that fail less predictably.

**Three of the values cannot be distinguished from ordinary code at all.** Measured: two are this repository's own package directory names, and one is the name of a function in `contract/store_metadata.py`. Exact-string matching cannot separate a copy from a coincidence for these, which is the same measurement #243 needs for the ban-set — recorded here once rather than twice.

**What is deliberately not proposed:** scanning docstrings. It would fire on every sentence naming a store, which is the false-alarm class that gets guards deleted. The honest options are to leave it (current), to scan only *test* docstrings (where the traceback amplification is), or to stop writing values in prose going forward without rewriting history. None is urgent.

Cross-refs: **C-57** (the exclusion and why), **C-89** (the traceback amplification, found here), **C-86**, issues #242, #243.

---

### C-96: The registry table that says which live checks this package may build is classified as none of our business

| Field | Value |
|-------|-------|
| ID | C-96 |
| Tier | 4 — no defect follows from it directly. It is here because it concealed an available mechanism for weeks, which is a cheap mistake to make again. |
| Source | `/expert-code-review` of the standing decisions, 2026-08-12 |
| Trigger | Anyone asks whether a live check against the production Appwrite project is permitted. |
| Owner | This repository. |
| Location | `tests/test_env_declaration.py:509` (`_TABLE_ROLE["test_environment"] = "IGNORED"`). |

`[test_environment]` is classified `IGNORED` with the reason *"a fact about the platform, not about this package"*. It is in fact the clause that governs **what live checks this package is permitted to build**:

> `status = "none"` — *"No non-production Appwrite project exists (þing-01 S23). Until the operator creates one: integration tests against the production project are FORBIDDEN by the seam contract; **read-only preflight validation is the only permitted live check**."*

The second half is a **permission**, and this repository spent weeks believing the whole clause was a prohibition. Reclassify and read it, or record why a permission that changes what we may build is not a fact we depend on.

**Partly addressed 2026-08-12 (#249).** The classification stays `IGNORED` — nothing here reads the table, and its rows are bare strings rather than sub-tables, so feeding it to `rows()` would raise (C-91). What changed is the *reason*: the comment said "a fact about the platform, not about this package", which is what let a permission read as a prohibition. It now says the table governs which live checks this package may build, and points at C-95 and C-96. Reading it mechanically waits on C-91.

Cross-refs: **C-94** (the mechanism this permission authorises), **C-95** (the mis-citation that compounded it), **C-91** (why it is not read yet), issue #249.

---

### C-95: The integration-test prohibition is cited to the wrong verdict, in three places

| Field | Value |
|-------|-------|
| ID | C-95 |
| Tier | 3 — a citation error, but one that closed off a design option. Namespacing across six repositories and two þings is a known hazard here; this is it landing. |
| Source | `/expert-code-review` of the standing decisions, 2026-08-12 |
| Trigger | Anyone reasons from the integration-test prohibition — for a preflight, a drill, or a new ADR. |
| Owner | This repository. |
| Location | `reports/technical_risk_register.md` (three sites, corrected 2026-08-12 in #249); `tests/test_store_construction.py` and `docs/CICs/UNFAOPostProcessorManager.md` (two more, **found 2026-08-13 and corrected then** — the #249 claim of "all three sites" counted only the register). Remaining mentions of `þing-02 D2` are this entry's own narration. |

This register cites **þing-02 D2** for the ruling that integration tests against the production Appwrite project are forbidden. þing-02 D2 is about identity and key separation. The ruling is **þing-01 D2** (`þingit/01_identity_secrets_config/orð_dómr.md:53-61`), and it differs from the paraphrase in two ways that matter: it is **conditional** (*"until the operator creates one"*), and it **grants** read-only preflight validation as the permitted live check. It also records that creating a test project is **assigned to the operator** and gates the provisioning-path drill — an open assignment, not a closed door.

Cross-refs: **C-94**, **C-96**, þing-01 `orð_dómr.md` D2, issue #249.

---

### C-94: No mechanism anywhere detects an invisible delivery at the time it happens

| Field | Value |
|-------|-------|
| ID | C-94 |
| Tier | 2 — the failure mode is invisible by construction and lands on the live FAO path: upload succeeds, storage is billed, the consumer's endpoint returns empty, nothing raises anywhere. ADR-013 §4.1a's *"invisible to the consumer, not merely degraded."* |
| Source | `/expert-code-review` of the standing decisions, 2026-08-12 |
| Trigger | **Re-specified twice on 2026-08-13; the first attempt was not exclusive and its own worked example matched two arms.** (a) A delivery is reported empty **and an upload occurred after the bucket reached the state under investigation** — that is what the preflight below would catch, and the time bound is what the first attempt omitted. (b) `APPWRITE_READ_API_KEY` is provisioned, at which point the deferral has no remaining cost. *(A third arm — "reported empty with no upload since" — was drafted and withdrawn: it is not observable from this repository, which the amendment says four lines on, and ADR-014 §4 requires a trigger someone can notice. It is a gap, and is stated as one below rather than dressed as a trigger.)* **Rewritten 2026-08-18, because arm (b) expired without firing** (register conventions: a trigger whose event has already occurred reads identically to a pending one). The preflight was built *without* `APPWRITE_READ_API_KEY`, so "it is provisioned" can no longer arm anything. What remains live is arm (a), now narrowed: **a delivery is reported empty, an upload occurred since, and the preflight did NOT raise** — that combination means the check is looking in the wrong place, and it is the only arm this repository can still be surprised by. |
| Owner | This repository, for the mechanism. The credential is the operator's. |
| Location | `views_postprocessing/contract/wire/sink.py` (the upload path, where nothing verifies); `views_postprocessing/delivery/`. |

Every mechanism this platform has aimed at invisible delivery is a **CI-time proxy** for it: we check our label against the registry, the consumer checks their constant against the registry, and — until this week — we parsed their source. None of them observes the outcome. Grepping the sink and the delivery package finds no read-back, no findability check, no assertion that what was uploaded can be retrieved by the name the consumer will query.

**The mechanism that would close it is known and is legal.** A producer-side **read-only findability preflight**: after upload, query the store read-only for a document whose `name` equals the declared `CONSUMER_DOCUMENT_NAME`; assert non-empty; log at ERROR and raise (ADR-008); remedy is the existing operator quarantine. It is authorised by the seam contract (see **C-96**), the `APPWRITE_READ_API_KEY` slot is already declared, and it is the only mechanism that survives a **third-party-operated private consumer**, because it asks nothing of them.

**Why it is deferred, stated honestly.** It needs a read credential wired into the launcher — an operator action, not a code change — and it adds a live network call to the delivery path. ~~Delivery works today.~~ Building it now would be building the right thing at the wrong time. That is a deferral with a trigger and an owner (ADR-014 §4), not an omission.

**⚠ THE ORIGINAL TRIGGER FIRED ON 2026-08-12, WHILE THIS ENTRY WAS BEING WRITTEN — and the mechanism it defers would not have caught it.** Both halves of that matter.

FAO emailed at **09:15 UTC** that `faoapi.viewsforecasting.org` returned no data and that a listing of the partner bucket showed **0 files**. In faoapi's words: *"They found it by hand and emailed us; nothing on our side paged."* That is trigger (a) as originally worded, verbatim. The struck sentence above — *"Delivery works today"* — was false at the moment it was written, and it was the entire justification for deferring.

**But the cause was not an invisible delivery.** faoapi's post-mortem (`views-faoapi/reports/post_mortems/2026-08-13_fao_empty_bucket_unannounced_migration.md`) records that *"the seam coordinates match (the producer writes to the FAO bucket under the declared document name; the consumer reads exactly that — the ADR-017 invisible-delivery work held)"*, and that the empty bucket was *"the migration + no-delivery-since state, not a producer/seam/credential failure"* — a deliberate destructive migration upstream, with no run executed since. **No upload occurred**, so a post-upload findability check would have observed nothing and reported nothing.

**So the trigger was mis-specified, not the mechanism.** "A delivery is reported empty" names a symptom with at least two causes, and this entry's preflight addresses only one of them.

**Partial mitigation, 2026-08-18 — the preflight is built.** After both legs are uploaded, each manager asks the partner store the question the consumer asks — `name == product.CONSUMER_DOCUMENT_NAME`, `category ∈ {forecast, historical}` — and refuses a falsy answer (`delivery/findability.py`, `DeliveryNotFindableError`). The two legs are checked separately on purpose: a run whose forecast landed and whose historical did not is invisible in exactly one half, and the historical leg is the one that actually stranded in run-0 (C-79).

**Two decisions inside it that a later reader should not have to re-derive:**

1. **It runs on the existing key, not the registry's `APPWRITE_READ_API_KEY` slot.** Verified in the Appwrite console 2026-08-18: the live `VIEWS Pipeline Core` key already carries `documents.read`, `rows.read`, `buckets.read` and `files.read`. A separate read credential would buy no isolation here, because the preflight runs *inside the delivery process*, which already holds the write key it just uploaded with. C-96's permission is about the operation being read-only, and it is. The registry slot stays `planned` for a preflight that runs **outside** the delivery, where the isolation would be real.
2. **It queries through a store with pipeline-core's automatic `name == model_name` filter suppressed** (`_build_partner_read_store`). `get_latest_file_id` delegates to `get_predictions_by_metadata`, which merges the path manager's model name into every query — so without the suppression the check would verify the views-models *directory* name, which equals the declared consumer name only by coincidence (**C-77**). Verifying the coincidence rather than the contract would leave this green while a rename took the delivery dark, which is the precise failure it exists to see.

**The read-back is scoped to THIS run, and that is the whole guard.** The first implementation asked *"is there any document under the consumer's name for this category"* — a question the **previous** delivery already answers yes to. Documents accumulate across runs (that is what makes "latest" meaningful to the consumer), so from delivery 2 onward the check could never fail: run-2's upload reports success, its metadata document is never created — the exact C-79 shape — the query returns run-1's document, and the preflight logs *"passed"* while the consumer goes on serving run-1. Caught by `/code-review high` before merge. `_ContractStorePort.upload` now returns the uploaded `file_id` (it was discarding it), the sink carries the manifest's id out — it is uploaded last, so it is the newest `category="forecast"` document — and the check asserts the newest document the consumer would find **is the one this run put there**. The refusal distinguishes "nothing found" from "found the previous run's", because those are different operator situations.

**A failed read-back is not an invisible delivery.** `findability.unverified` names that separately (`FindabilityUnverifiedError`): a store error after a successful upload means the delivery is UNVERIFIED, not known invisible, and quarantining on it would be an outage the guard manufactured. Same distinction C-103 draws between a missing producer client and a producer that publishes no boundary, and C-99 between an unrecognised store result and a real one — three instances now of the same rule, that *could not ask* and *asked and got nothing* call for different operator actions.

**A note on which pipeline-core you read, because it changed a review's conclusion.** The same review reported that `unverified()` was dead code, on the grounds that `get_predictions_by_metadata` swallows a failed search and returns `[]` — so a store error would arrive as `None` and be reported as an invisible delivery. That is true of **2.3.0**, which is what the drifted developer venv holds (C-104). It is false of **3.0.1**, which `poetry.lock` pins and CI installs: there the method **raises `MetadataSearchIncomplete`**, with a comment in pipeline-core saying why — *"Returning [] here would tell every caller 'no predictions match', which is a statement about the shelf rather than about the lookup… a false negative to an external counterparty"* (views-pipeline-core C-241, its Cluster J). Verified 2026-08-19 by reading `3.0.1` from the views-pipeline-core checkout rather than the installed package. So the split holds where it runs. **This is C-104's hazard in its most expensive form yet**: not a wall of red, but a confident and wrong conclusion about production drawn from a stale environment.

**The tier does not move, and the reason it does not is the point.** The Tier 2 rationale was *"upload succeeds, storage is billed, the consumer's endpoint returns empty, nothing raises anywhere."* For that cause, something now raises. What holds the entry at 2 is the two causes below, which this does not touch and which remain invisible — the tier now rests on the gaps rather than on the mechanism.

**Two uncovered causes, stated as gaps rather than dressed as triggers.** Neither is observable from here, so neither can be a trigger under ADR-014 §4 — a trigger nobody can notice is a wish:

1. *The bucket is empty because nothing was delivered.* This repository is not told when a delivery is due and has no view of whether the last one is still present. That is the 2026-08-12 case.
2. *The bucket is not empty but what is served is stale.* faoapi's own post-mortem records a warm per-key cache that can serve stale historical over an emptied bucket — so "reported empty" would not even be the symptom.

Both belong to whoever can see delivery cadence, which is not this seat. Recorded here so the next reader does not mistake the trigger's narrowness for coverage.

**The preflight is still not built**, and the reason is now sharper than "delivery works today": the case that fired is not the case it catches, and `[secret.APPWRITE_READ_API_KEY]` on the live registry still reads `status = "planned — operator issues (D4)"`.

**What it would not cover, so nobody over-reads it later:** it proves the document is findable by that name in the store. It does not prove the consumer's code queries by that name. That last link is theirs, and issues asking each consumer to bind their *query* to their constant are filed under #248.

Cross-refs: **C-92** (the check we deleted rather than replaced), **C-87** (the broader residual), **C-96** (the permission), ADR-013 §4.1a, ADR-017 §5/§8, issue #248.

---

### C-89: The guard against publishing a coordinate value publishes it — in one branch of three, proven on one side of two

| Field | Value |
|-------|-------|
| ID | C-89 |
| Tier | 2 — a confidentiality exposure on a public repository with no signal that it happened. It fires on exactly the event the guard exists to catch, and CI logs are world-readable and are not retroactively redactable. |
| Source | `/code-review max` on PR #239 post-merge, 2026-08-11; every element verified in this repository |
| Trigger | A literal coordinate value is committed into a `.py` under `views_postprocessing/` — the violation the scan exists for — on any branch whose CI runs. |
| Owner | This repository. |
| Location | `tests/test_env_declaration.py` — `test_no_coordinate_value_is_copied_into_this_repo` (both reporting branches and the `secret` exemption in `scanned_sections`), `test_the_drift_check_would_catch_a_rotation_that_names_and_classes_cannot`. **Function names, not line numbers**: this entry has now cited stale ones twice, because each fix moved them. |

The no-copy scan exists because README.md once carried four real coordinate values, two lines below the sentence promising they are never copied, in a public repository. It has three parts and they do not agree with each other about the one rule that matters.

**The Python branch prints the value.** `copied.append(f"{source}:{node.lineno} = {node.value!r}")`. The markdown branch sixty-eight lines below was rewritten on 2026-08-11 to stop doing precisely this, and `_describe_changes` was added in the same change with a docstring whose entire subject is that a rotated coordinate must never reach a public log. The invariant was stated, applied to one branch, and left off the other. When this guard fires it does the thing it was built to prevent.

**The `secret` table is exempted by an inline literal.** `scanned_sections` filters `_TABLE_ROLE` for `CONSUMED` and then subtracts `secret` by name, two lines under a comment claiming the scope comes from the declared partition and not from an inline list, and with no reason recorded anywhere. Measured against views-appwrite's current registry: `[secret]` has seven rows and none carries a `value`, so the clause removes zero entries today and the `isinstance(..., str)` filter on the next line already does its work. The day a secret row gains any value, the one table class whose leak matters most is silently outside the scan.

**The rotation proof checks one side.** `assert "value:" in changed[canary] and "at-the-pin" not in changed[canary]` asserts the *pinned* value is absent. The freshly rotated value — the more damaging one, and the one the fixture already names — is never asserted absent. A regression that digests one side and interpolates the other passes this proof.

The three share a cause: the no-print rule lives in prose and in one implementation, and nothing asserts it about the guard as a whole.

**Partial mitigation 2026-08-12 (#242) — the leak is closed; the scan's scope is not.**

*(The heading matters. An earlier draft of this paragraph said "Mitigated", which is neither of the two phrasings this register declares — `Mitigation — landed` and `Partial mitigation`, enforced by `tests/test_register_integrity.py`. Inventing a third phrasing passes that guard by evading its string rather than by complying, which is the identical escape ADR-014 §5 records C-15 making. This entry is partial by its own next sentence.)*

Two of the three are fixed, and the third moved:

1. **Both branches name the coordinate, never the value.** Each builds its own sentence — two f-strings, deliberately not one shared formatter — and neither has the value in hand. They name **all** coordinates declaring that value: measured, two pairs share one (the prod-forecasts bucket and collection share both id and name), so a `value -> name` map would have named the wrong coordinate half the time in the message a maintainer uses to find the copy.
2. **The rotation proof asserts both sides absent**, taken from the fixture's own variables rather than from two literals a rename would quietly orphan. Mutation-proven: leaking the post-rotation side while keeping the pinned side digested fails now and **passed before** — the more damaging half, unchecked.
3. **The rule is asserted behaviourally**, by `test_the_scan_reports_where_a_copy_is_and_never_what_it_is`: plant a value in a fixture tree, run the real scan, read the finished message.

**And the third one took two attempts, which is the part worth recording.** The first version asserted that every finding was *routed* through `_report_a_copy` — an AST walk over the scan's own source. Five independent reviewers were run against it and **routing turned out not to be safety**: the value could be smuggled through either of that helper's two parameters, appended with `extend` or `+=`, or reported from a renamed accumulator. Six of eight mutations survived, and one legitimate refactor *failed* it — a guard that misses the thing and fires on the innocent, which is C-82's shape and ADR-014 §3's deletion criterion at once. The docstring's claim that a caller "cannot print one however it is written" was false when written.

Reading the finished message instead makes the whole class unreachable: it does not matter how a finding is built, which branch builds it, or what the final assertion interpolates. All five surviving mutations are now caught, including one that leaked the entire ban-set through the assertion message rather than through a finding.

**A third pass, from an adversarial mutation review that ran 14 mutations against the second.** Twelve survived. Seven were leak channels the message test could not see, and all seven are now closed:

- `print()` or `logging.warning()` beside the append — the message stayed clean while pytest published the value under *Captured stdout* / *Captured log call*. The behavioural test now reads `capsys` and `caplog` too. A stray debug print is an ordinary accident, not an adversarial one.
- **`_describe_changes`'s rotation proof was one-sided** — it asserted only the pinned value absent, never the rotated one, which is the more damaging half. Now both, taken from the fixture's own variables.

**A malformed package module published itself, and the first fix for it did not work.** `ast.parse` raises with the source as its own frame's argument, and pytest renders that in full — so a package file that both fails to parse and carries a value printed itself. This entry previously said *"it takes a `Path` now and reads inside"*; **measured, that changes nothing**, because the text still reaches `ast.parse`. The fix is a shared `_parsed(path)` that refuses by path and line with `raise ... from None` — `from None` is the load-bearing part, since the chained `SyntaxError` carries the same text. Applied at **both** parse sites: fixing one and not the other is this entry's own shape.

**A fourth pass deleted most of the third, and that is the entry's real lesson.** Four commits and five reviews had grown this file by **+195 lines**, of which **+95 was prose restating this register** and **every one of the 149 new function-body lines was a test of another test in the same file**. Two of those additions were themselves defective:

- `test_the_drift_report_never_carries_a_value_in_any_recoverable_form` claimed to drive `_describe_changes`'s `appeared`/`removed` branches. It did not: those branch on `was is None`, and the fixtures passed `_ABSENT`, a sentinel object. It ran one branch three times while asserting three — an ADR-014 §1 defect inside the fix for an ADR-014 §1 defect — and the branches it named return constant strings and cannot leak. **Deleted.**
- `_carries`, an eight-character-window "recoverability" predicate, is **strictly worse than plain `in`**: the window degrades to exact match below eight characters, and this package's two directory names are five-character declared values. Measured, `_carries("views_postprocessing/unfao/leaky.py …", "unfao")` is `True` — it condemns a bare, safe file path while claiming a leak. **Deleted**; both call sites use plain `not in`, the vocabulary already at `test_the_environment_refusal_logs_names_and_never_values`.

Net **−140 lines**, leaving the file **+55 over its pre-story size** rather than +195. What the +55 buys: one behavioural guard, the rotation proof's second side, the value→coordinate map, and the shared parse refusal.

**What is deliberately NOT chased.** Four surviving mutations narrow the scan's *scope* — a length floor, a dropped section, a swallowed `SyntaxError`, a `break` after the first finding — and none is visible to a test that plants its own fixture. They are **#243**'s subject and are routed there. A fifth deletes the no-print assertion itself: infinite regress, carried here instead. Two residuals stand: the markdown branch's output is not behaviourally proven (it holds no value by construction), and a leak shorter than the planted fixture would pass. Chasing either is the whack-a-mole this epic exists to refuse.

4. **The scan's own docstring carried four registry values**, and pytest prints the failing function's source — so the guard would have published them on exactly the event it exists to catch. The message was clean; the traceback was not. Now it names coordinates. **The wider finding is registered separately as C-97**: standalone values sit in docstrings and comments across several files (**25 in 8** as of 2026-08-13 — C-97 owns the number and the counting basis; do not cite it from here), production modules included, and the AST scan excludes docstrings by a deliberate C-57 decision taken before anyone counted them.

**Deliberately still open, and moved rather than closed:** the `secret` exemption at `:1042` and the ban-set's package-name collision are the *scope* of the scan, not its reporting, and belong with the matcher rewrite in **#243**. This entry stays open until they land, because closing it now would close a Tier 2 on two-thirds of its content.

**⚠ The stated closing condition IS met, and this entry stayed open anyway — 2026-08-13.** It said it would stay open "until [the `secret` exemption and the ban-set collision] land" with #243. **#243 closed 2026-08-12 and both landed**: the exemption is gone (`scanned_sections` now filters `_TABLE_ROLE` for `CONSUMED` with no subtraction), and the collision cannot arise because the markdown branch is a NAME=VALUE pair matcher. The length floor went too.

What actually keeps it open is neither of those — it is the two deferrals below, **whose triggers fired while nobody was watching them**:

- Deferral 1's trigger is *"when #243 finishes touching `tests/test_env_declaration.py`"*. #243 finished. The leak guards are still in that file; `tests/test_redaction_guard.py` is only cross-referenced.
- Deferral 2 was *"routed to #243"* — and #243 closed without it. `test_the_drift_check_would_catch_a_rename` still rebuilds its subject's comparison with its own comprehension rather than driving the checked function.

Both were unowned, which is worse than deferred — filed as **#265**, and **both discharged 2026-08-14**. *(An earlier draft of this amendment named the problem and left it there, which under ADR-014 §4 converts two compliant deferrals into two non-compliant items. Naming is not rehoming.)*

**Deferral 2 is fixed as filed.** The comparison the gated check ran inline is now `_name_and_class_drift`, called by both it and the proof, so the proof drives its subject instead of a copy of it. Mutation-proven: making that function return `([], {})` now fails the proof for both partners, where before it stayed green. *(The sibling defects were repaired by driving the real check under `monkeypatch` instead; here the comparison is a pure function of two dicts that both callers want whole, so sharing it is the same guarantee with less machinery.)* It also gained an assertion that the report names *both* sides of a mismatch — what this package expects and what the registry declares — since a reader who cannot tell which moved cannot act on it.

**Deferral 1 is answered "no", with the reason recorded rather than deferred a third time.** The coordinate-value scan **stays in `tests/test_env_declaration.py`**. Its subject is `_EXPECTED_NAMES`, derived from `_PARTNER_ENV` — the declaration of what each partner reads, which is the substance of that module. Moving a guard away from the declaration it guards, so that a filename reads better, trades a real coupling (CCP) for a filing convenience, and would require exporting a private name from one test module into another.

What *was* misfiled moved instead: `registry_at` / `registry_current` / `rows` are the shared **reader**, not this package's environment declarations, and their five refusal tests plus `_scratch_repo` are now `tests/test_seam_registry.py`. That is the boundary that was actually wrong: **109 lines of test code moved out**, no shared private state left behind — the new module imports only from `tests/seam_registry.py`. `test_env_declaration.py` is 1406 lines against 1503 before this change — the split removed more than that and the shared comparison above put some back.

**Two deferrals, both with triggers (ADR-014 §4).**

1. **The leak guards belong in `tests/test_redaction_guard.py`**, which already owns "what stops us leaking" and which `test_the_environment_refusal_logs_names_and_never_values` already points readers to. The concern is currently split across two files with no shared vocabulary. Not moved here, because moving code while fixing bugs in it is how the next defect arrives. **Trigger: when #243 finishes touching `tests/test_env_declaration.py`.** Owner: this repository.
2. **`test_the_drift_check_would_catch_a_rename` re-types its subject's comparison inline** rather than calling it, so blanking that subject's assertions leaves the proof green — the same defect its two siblings had repaired. Pre-existing, found while reading for this change. **Routed to #243**, which is already in this file.

Cross-refs: **C-57** (the scan's own entry and its history), **C-93** (why the author's own proof did not find this), **C-90** (the sibling defect in the drift checks), ADR-014 §1, issues #242, #243.

---

### C-92: Nothing here checks that a consumer SELECTS by the delivery label — for either partner

| Field | Value |
|-------|-------|
| ID | C-92 |
| Tier | 2 — the failure mode is invisible by construction and is on the live FAO path. Upload succeeds, storage is billed, the consumer's endpoint returns empty, nothing raises anywhere. |
| Source | `/code-review max` on PR #239 post-merge, 2026-08-11 |
| Trigger | **Either consumer** changes how it selects — to a category, a metadata field, a query builder — without touching its served-name constant. Also live: `manager.py:117` in both drops the name filter entirely when `model_name` is falsy. |
| Owner | Shared: views-faoapi owns the check; this repository owns noticing it does not exist. |
| Location | `views_postprocessing/<partner>/product.py::CONSUMER_DOCUMENT_NAME`; `tests/test_product.py::test_the_declared_consumer_name_matches_the_registry` (what remains); ADR-017 §5/§7. Function names, not line numbers. |

PR #239 retired the FAO half of the source-reading check on the strength of views-faoapi#379. That was the right sequencing — §5 requires the consumer-side check to land first, and it had. **But the two checks are not the same check.**

views-faoapi#379 binds their *served-name constant* to the registry row. The assertion this repository deleted was `'filters["name"] = self.model_path.model_name'` — that they still *query* on it. So views-faoapi can refactor its selection mechanism, leave its name constant untouched, pass #379, pass our registry comparison, and serve an empty endpoint. The deleted assertion carried that exact sentence: *"the name may still match while the consumer filters on something else entirely — same invisibility, different cause."* Nothing carries it now.

**Verified 2026-08-12, and the state is good — which is why this is a risk and not an incident.** Read at `views-faoapi@origin/development`: their `CONSUMER_DOCUMENT_NAME` — moved since to `src/views_faoapi/seam_contract.py`, a dedicated module — reaches `APIPathManager(...)` in `managers/api.py`, and `managers/prediction/manager.py` still filters on it at `:117` and `:435`. Their D2 test — views-faoapi's `tests/test_seam_contract_binding.py` — imports the constant from the production module rather than re-typing it, which is better than it had to be. **The composition is what nothing asserts**: constant↔registry is checked by them, query↔constant was checked by us and is not any more. Also worth recording: their D2 check was on `development` while `main` sat 22 commits behind; **as of 2026-08-13 that gap is 2 commits**, so the caveat has all but expired.

**C-87 is not this.** C-87 records that we verify our copy against the declaration rather than the consumer's code against it. This is narrower and worse: for one partner we briefly had the second check and gave it up for something that does not cover the same failure.

**~~A second, structural half.~~ MOOT 2026-08-12 (#248)** — `_CONSUMER_SELF_CHECK_PENDING`, `test_the_pending_list_is_not_empty` and the `SIBLINGS` note it describes were all deleted with the mechanism. Left visible because the reasoning still applies to any future map of this shape: `_CONSUMER_SELF_CHECK_PENDING` is asserted non-empty and asserted to name only real partners — never asserted to *cover* them. Every other partner map here is two-sided against `PARTNER_PACKAGES`; this one is not, so a third partner is silently exempt from the source read the day it lands. And `SIBLINGS["views-crafdapi"].note` says the fetch "buys nothing and should be removed" once the registry read exists — which PR #239 landed — while ADR-017 §5 forbids retiring that partner's source read until views-crafdapi#53 lands. A maintainer following the note does the thing the ADR forbids, and `test_the_pending_list_is_not_empty` does not object because the map stays non-empty.

**Resolved as far as it can be here, 2026-08-12 (#248) — the check is gone, the gap is permanent, and the ask is filed.**

Both source reads are deleted. Not because the sequencing constraint was satisfied — it **dissolved**: the reads broke twice in twenty-four hours, views-faoapi on 11 August and views-crafdapi on the 12th, each time because that repository refactored a literal argument into a named constant. Their code got better and our test went red. ADR-017 §7 said we were never entitled to depend on another repository's file layout; two breakages in a day is the evidence, and repairing the regex a third time would have been repairing the wrong thing. ADR-017 §5 carries the erratum.

**The gap is now permanent and unguarded here, by choice.** Nothing in this repository verifies that a consumer's query uses the name it declares. The chain reads:

| link | owner | held by |
|---|---|---|
| we upload with name N | us | construction |
| N == the registry row | us | `test_product.py::test_the_declared_consumer_name_matches_the_registry` |
| their constant == the registry row | them | views-faoapi's `tests/test_seam_contract_binding.py`; views-crafdapi's equivalent |
| **their query == their constant** | **them** | **nothing** |

**Filed where the fact lives:** views-faoapi#390 (under their seam-verification epic #383, whose flagship this is) and views-crafdapi#55. Both carry `file:line` evidence, both note that `manager.py:117` applies the name filter *conditionally* so a falsy name broadens the query rather than failing, and both say plainly that we are not prescribing their internals.

**Verified intact at the time of writing** — the constant reaches the path manager and the manager still filters on it, in both consumers. This is a risk, not an incident.

**Trigger** is now theirs to clear and ours to notice: when either issue lands, this entry closes for that partner. Until then the honest statement is that a delivery is verified by two values this platform authored agreeing with each other, plus the consumer's own word.

Cross-refs: **C-87** (the broader residual this sharpens, not duplicates), **C-94** (the producer-side preflight that would close it without asking anyone), ADR-017 §5/§7/§8/Appendix B, views-faoapi#390, views-crafdapi#55.

---

### C-88: The platform declarations live in pytest's fixture file, so nothing outside the test tree can reach them

| Field | Value |
|-------|-------|
| ID | C-88 |
| Tier | 3 — no correctness risk and nothing silent. It is a boundary that has already forced one duplication for structural rather than design reasons, and it will force the next one the same way. |
| Source | `falsify` against the SOLID / component-principle lens, 2026-08-11 |
| Trigger | **Either.** (a) A second non-test consumer needs one of these declarations and has to copy it. (b) A fifth declaration is added to `tests/conftest.py` — the file is at four, and the threshold for "dumping ground" is not a number but the moment nobody can say in one sentence what the file is for. |
| Owner | Whoever adds the next declaration, or the next non-test consumer. Not urgent; it gets more expensive slowly. |
| Location | `tests/conftest.py` (grew again this week; `wc -l` for the number, which moves); `scripts/build_gaul_lookup.py:73`; ADR-016 §4. |

`tests/conftest.py` is pytest's fixture file. It currently holds **four unrelated groups**: the package taxonomy (`PARTNER_PACKAGES`, `MACHINERY_PACKAGES`), the sibling repositories (`Sibling`, `SIBLINGS`, and three resolver functions), the consumer mapping (`CONSUMER_REPO`), and two git helpers (`git_output`, `commit_is_on_main`). None of those is a test fixture. They are declarations about the platform that happen to be consumed by tests.

**The concrete cost, which has already been paid once.** `scripts/build_gaul_lookup.py` needs the same sibling-location fact and cannot have it: *"a script must not import from `tests/` — that is the dependency direction backwards."* So it hardcodes `"VIEWS_DATAFACTORY"` at `:73` while `SIBLINGS` declares the same string in `conftest.py`.

That duplication is **defended on WET grounds and the defence is sound** — the two contracts genuinely differ (the script returns a `Path` even when the checkout is absent so it can raise its own message; the test helper returns `None` because a missing sibling is a normal skip), and a guard asserts the two resolve to the same place. This entry does not ask for that to be merged.

**What it records is that the choice was not free.** The script could not have reused the declaration even if reuse had been right, because of where the declaration lives. A structural constraint and a design decision reached the same answer, and only one of them was examined.

**Why this is Tier 3 and not higher.** Nothing is wrong today. Every guard works, the duplication is guarded, and moving the declarations would touch a dozen imports for no immediate gain. The risk is the slope: `conftest.py` is where a declaration goes when nobody asks where it belongs, and each addition makes the next one more natural.

**What "fixed" would look like**, when the trigger fires: a small module that owns the platform declarations — importable by tests, scripts and, if ever needed, package code — with `conftest.py` reduced to what pytest actually needs from it. That is the shape, not a commitment; the point of the trigger is that the second incident tells you whether it is right.

Cross-refs: **C-46** (which records the builder's separate resolver and the guard that they agree), ADR-016 §4, ADR-002 (dependency direction).

---

### C-86: The release path depends on another repository, and there is no way past a red build

| Field | Value |
|-------|-------|
| ID | C-86 |
| Tier | 2 — no wrong data ships and nothing is silent. What is at risk is the ability to *ship at all* on a day when someone else's repository has moved, on the path that is this project's production release. **Live since 2026-08-13 04:51 CEST**; latent before that. |
| Source | External review of ADR-016 by the views-appwrite and views-faoapi seats (#231, #233), 2026-08-10 |
| Trigger | **Two, and the first is the one to watch.** (a) A status check becomes required on `main` — at that moment this stops being latent. (b) An upstream merge to a sibling's `main` reddens this repository while a delivery fix is waiting. |
| Owner | Simon. Both available responses are console actions: add a bypass actor to `protect_main`, or accept the coupling as written. |
| Location | `.github/workflows/run_pytest.yml` — the views-appwrite checkout step inside job `test`; the `protect_main` ruleset; ADR-016 §7, §7a, §7b. |

ADR-016 has CI check out `views-appwrite` and `views-crafdapi` so that cross-repository checks run on every change rather than on a maintainer's habits. That is the right trade and the entry does not dispute it. What it records is the cost, which was accepted in the ADR on a justification that turned out to be false.

**The false justification.** ADR-016 §7 originally said the maintainer could merge over a failing check when something was urgent. Two reviewers challenged it independently. Measured 2026-08-10: `protect_main` lists **zero bypass actors**, and a GitHub ruleset applies to everyone except the actors it names — so administrator status confers no exemption. There is no classic branch protection either, so no `enforce_admins` route. The claim is withdrawn in the ADR; the risk it papered over is this entry.

**⚠ THE TRIGGER HAS FIRED. This entry is live, not latent, from 2026-08-13 04:51 CEST.**

`protect_main` ruleset version `46391648` added `required_status_checks: [{context: "test"}]`. The version before it, `45955166` (in force from 2026-08-08), carried no such rule — so the "latent" assessment below was true right up to that instant, and is superseded rather than mistaken.

The coupling is now unbypassable: `bypass_actors: []`, and the API reports `current_user_can_bypass: "never"` for an account with `admin = true`. That is stronger evidence for "administrator status is not an exemption" than this entry's original argument from ruleset semantics. There is no classic branch protection either — `branches/main/protection` returns 404 — so no `enforce_admins` route exists.

The required context is the job id `test`, which contains the views-appwrite checkout step, and the workflow sets no `continue-on-error`. **So a merge to `main` — the release to FAO — now requires views-appwrite to be reachable.**

*(An earlier draft of this paragraph offered PR #262 as "observed working: it sat at BLOCKED until CI went green." That does not survive its own evidence and is withdrawn. The required `test` check was never red on #262; the only failing check was `check-branch`, which is **not** required and blocks by a different mechanism. What the record does support: the requirement was in force before #262 opened, and the merge landed 21 seconds after `test` reported success.)*

**What this epic did to the exposure, stated accurately.** An earlier draft said CI checked out two sibling repositories a week ago and one now. Measured: on 2026-08-06 it checked out **one** — views-crafdapi. views-appwrite was added 2026-08-10 once it went public, and views-crafdapi was removed 2026-08-12. **The count is unchanged at one; what changed is which repository, and what the check does with it.** The two-sibling window lasted about two and a half days. The real reduction is in the matching: the check that was in force a week ago compared `meta.version` and fired on any upstream edit; it now compares the 13 rows each partner declares, out of 25 in the tables it reads.

**The open choice, stated so it is not rediscovered during an outage.** This entry lists three responses in order of preference. The first — views-appwrite#76's machine-readable obligation flag — **landed** as registry v1.6.0 and is recorded below. The second is a bypass actor; there is none. The third is that the coupling stands as ADR-016 §7 describes, *"defensible but should be chosen rather than discovered"*.

**Recommendation (mine), pending the operator's assent:** take the third. A bypass actor added in advance is a permanent hole against a hypothetical; added during an incident it is a console action taking under a minute. This paragraph is what makes that a two-minute decision rather than a discovery. **Not recorded as settled** — `Owner` above makes both responses console actions, and those are the operator's.

**Original assessment, superseded 2026-08-13 and left visible because it was true when written and correctly named both the mechanism and the moment:**

**Why this is latent rather than live.** `protect_main` currently requires **no status check at all** (C-81's enforcement half). So today a red build blocks nothing and this coupling costs nothing. The instant a required check is added — which C-81 asks for, correctly — the coupling becomes real and unbypassable in the same change. **Two open items that each look independently sensible combine into something neither of them says.**

**The rate is not hypothetical.** views-appwrite reports five registry editions in four days (v1.4.0 2026-08-02 through v1.4.4 2026-08-05), **four of them observation-driven** — recording console facts, correcting a key's scopes — carrying no obligation for any consumer. Each would have reddened this repository and blocked a release.

**What would resolve it, in order of preference:** views-appwrite#76 makes the obligation-carrying distinction machine-readable, so observation-only bumps stop firing the check at all — filed, and that seat volunteered it. Failing that, a bypass actor restores the escape. Failing both, the coupling stands as ADR-016 §7 describes, which is defensible but should be chosen rather than discovered. *(⚠ "filed" is stale as of 2026-08-11 — #76 has **landed**, as registry v1.6.0. See the amendment at the end of this entry; the sentence is left as written because what it asked for and what arrived are worth comparing.)*

Cross-refs: **C-81** (the enforcement half, whose fix activates this), **C-46** (whose recommendation against per-PR sibling checkouts this overrode, with the reasoning recorded there), ADR-016 §7/§7a/§7b, views-appwrite#76.

**Partial mitigation 2026-08-11 — the false-alarm rate, not the coupling.** The check that
kept firing compared registry *version strings*. It has been replaced by three that match
on the facts this repository actually declares: the pinned commit must declare the pinned
version; every top-level table upstream must be classified here; and no row we read may
differ between the pinned edition and the current one.

Measured across the window that prompted this entry — v1.4.4 → v1.5.2, three editions in a
week — the new checks are **green**, because none of those editions touched a row this
package reads. Under the old check every one of them was a red build blocking a release.

**This does not close the entry, and the distinction matters.** C-86 is about CI depending
on another repository with no way past a red build. That dependency is untouched: the
sibling checkout still happens, `protect_main` still has zero bypass actors, and a change
upstream that *does* touch a row we read will still redden this repository and block a
merge — correctly, and that is the point. What changed is that it now fires for reasons
that carry an obligation.

~~The entry's trigger is unchanged and remains a console action: **a status check becomes
required on `main`**, at which moment the coupling stops being latent.~~ **That happened on
2026-08-13 — see the amendment at the top of this entry.**

**Amended 2026-08-11 — the first-preference resolution has LANDED, and this entry found out
from a guard rather than from a notification.** views-appwrite#76 shipped as registry
**v1.6.0**: a new `[edition."x.y.z"]` table marking each edition `obliges_consumers =
true|false`, which is exactly the machine-readable distinction the paragraph above asks for.
The sentence *"filed, and that seat volunteered it"* was true when written and is now stale.

Two things are worth recording about how it arrived. The partition check added the same day
went red on it unprompted, on its first live encounter with an upstream table nobody here
had classified — which is the whole reason that check is directional. And the row-level
drift check stayed **correctly silent**, because a new table this package does not read is
not drift in anything it depends on. The two behaved exactly as designed on data neither
was tested against.

**Adoption is a follow-up, not part of the change that noticed it.** `[edition]` is
classified `IGNORED` in `tests/test_env_declaration.py::_TABLE_ROLE` — declared, not
silently unseen. Nothing here reads `obliges_consumers` yet, so the false-alarm rate is
still carried by the row-level differential rather than by upstream's own flag.

**⚠ The re-pin deferral below is DISCHARGED, 2026-08-13, by upstream rather than by us.** The registry now publishes `obliges_consumers_since = "1.5.2"` — *"the number a consumer should pin against"* — and both `appwrite_env.py` modules already pin exactly `1.5.2`. So the pin is conformant by upstream's own new rule and the "re-pin is **due**" urgency below is withdrawn. Re-pinning further forward is now hygiene with no safety consequence, which is what the deferral originally said before the trigger fired.

**Deferral, with the trigger ADR-014 §4 requires** — this was carried in a pull-request
description, where deferrals go to be forgotten:

- **What:** re-pin `SEAM_CONTRACT_VERSION` / `SEAM_CONTRACT_COMMIT` in both
  `views_postprocessing/{unfao,crafd}/appwrite_env.py` (currently v1.5.2 / `c7b597e`), and
  read `[edition].obliges_consumers` so an observation-only edition cannot fire anything.
- **Trigger — both halves have now FIRED:** the partition fired on v1.6.0 (2026-08-11), and
  views-appwrite#76 landed. The re-pin is therefore **due**, not deferred; what remains
  deferred is reading the new flag.
- **Owner:** whoever next touches an `appwrite_env.py`. Re-pinning is hygiene with no
  safety consequence now that the differential exists — which is precisely why it needs a
  written trigger rather than a good intention.

Cross-refs for this amendment: **C-57** (the drift detector this rides on), ADR-016 §7a/§7b,
views-appwrite#76 (**delivered**, registry v1.6.0).

**⚠ CORRECTED 2026-08-12, and PARTLY RESOLVED the same day (#245).** The paragraph
beginning *"Partial mitigation 2026-08-11"* claimed the replacement checks "match on the
facts this repository actually declares". **Two of the three did not**, and an earlier
draft of this correction said one — the review that caught it is the reason this paragraph
is longer than it wants to be.

**The first, now fixed.** The drift check's arrival half ran over every row of every table
this package depends on, with no filter for the names it reads. Measured on the live
registry: each partner reads **13 of 25** rows, and **6 belong to no repository here** —
three caller keys for other consumers, and three platform key slots still marked
`status = "planned"`, one of which names *"un_fao delivery"* among the identities it would
be issued for. C-90's original wording was "belong to no repository here"; an earlier draft
of this paragraph upgraded it to "other repositories entirely", which is the same
overstatement this paragraph exists to correct, two sentences from correcting it. The other two rows this package does not
read are its own delivery labels — both declare `producer = "views-postprocessing"` — and
they are covered by `tests/test_product.py`, not by this check. *An earlier draft of this
paragraph said "8 belong to no repository here", which upgraded a careful claim in C-90
into a false one and propagated it to four places.*

**And it never actually fired in anger.** Measured: **zero rows have arrived in the
depended-on tables since the pin** — the arrival half was green on every real edition it
ever saw, from its introduction on 2026-08-11 to its deletion on 2026-08-12. An earlier
draft said an upstream key "reddened this repository and blocked a release". That is a
mutation result written in the past tense. What is true: a mutation shows it *would* fire,
and it *would* block once C-81's required check lands — `protect_main` carried
`deletion, non_fast_forward, pull_request` and no required status check **until 2026-08-13
04:51 CEST**, which was this entry's "latent rather than live" paragraph while it held.

**The arrival half is now deleted** (#245). The drift check fires on exactly one condition —
a row this partner declares differs between the pinned edition and the sibling's `main` —
and that stopping rule is written above the check itself. Its self-defence turned out to be
false: it claimed `[contract.*]` *"arrived exactly this way and nothing else here would have
seen it"*, but `[contract]` is a top-level **table**, caught by the partition check directly
above it.

Mutation-proven both ways against the live registry: an unrelated API key and a third
partner's contract row are now **silent**; a rotation and a removal of a row this partner
reads still **fire**. A new test asserts the silence direction, so a third widening meets
an objection rather than a paragraph.

*(That silence test needed two attempts, and the first is worth recording because it is
this entry's own disease. It called `_describe_changes` directly — the helper underneath
the check — and was worthless: re-adding the deleted arrival half to the real check left
the whole suite green, because that half never lived in the helper the test was asking.
The "mutation proof" offered for it was invalid too: it mutated the test rather than the
code, which proves nothing. It now drives the real check through monkeypatched readers,
and re-adding the arrival half fails it. **A guard must be pointed at the thing it claims
to guard**, which is the sentence this whole entry keeps re-learning.)*

**The second inaccuracy stands, and is this entry's remaining rate risk.** *"Every
top-level table upstream must be classified here"* fires on any new table regardless of
whether this repository declares anything about it — and **it has already fired for exactly
that reason**: `[edition]` arrived at v1.6.0, an edition the registry's own `[meta]` calls
*"additive and opt-in; obliges nobody"*, and it reddened this repository. That event is
recorded **earlier** in this entry — the partition "went red on it unprompted", "which is
the whole reason that check is directional" — and that record is true of the *detection*
and silent about the *cost*. Adopting `[edition].obliges_consumers` is the deferral that
would fix it, and its trigger is below.


**A second source of redness, and it is ours — see C-110.** From 2026-10-18 `tests/test_credential_expiry.py` fails by design, so this entry's no-bypass finding starts applying to a block this repository scheduled for itself rather than one a sibling caused.

---

### C-87: The delivery label will be checked against a declaration, and nothing will check the declaration against the consumer

| Field | Value |
|-------|-------|
| ID | C-87 |
| Tier | 2 — the failure mode is invisible by construction. The upload succeeds, the storage is paid for, the consumer's endpoint returns empty, and nothing anywhere raises. That is the shape ADR-013 §4.1a calls *"invisible to the consumer, not merely degraded"*. |
| Source | ADR-017 §8, sharpened by external review (#232, #234), 2026-08-10 |
| Trigger | **Either half going missing.** (a) ~~`views-faoapi#379` or `views-crafdapi#53` is closed without the check being written.~~ **Both closed WITH the check written** (2026-08-11, 2026-08-12). The live trigger is now (a') either consumer's *query* stops using its declared constant — see **C-92**, and views-faoapi#390 / views-crafdapi#55. (b) A private API operated by a **third party** becomes a consumer — at which point the second half cannot be required at all and this becomes permanent. |
| Owner | The consumer-side seats own the check; this repository owns noticing that it exists. |
| Location | `views_postprocessing/<partner>/product.py::CONSUMER_DOCUMENT_NAME`; the check in `tests/test_product.py`; ADR-017 §5, §8, Appendix B. |

ADR-017 decides that the delivery label is declared in the public coordinate registry and that each side verifies **itself** against that declaration, so neither repository reads the other's source. That is the right rule and this entry does not dispute it.

Its residual is stated plainly in §8 and belongs here rather than only in a document: **we will verify our copy against the declaration, not the consumer's code against it.** If a consumer quietly starts filtering on something else, our check passes and the delivery is invisible exactly as before.

**Why this is a risk and not merely a note.** The second half is real work in repositories this project does not control. `views-faoapi#379` has a willing owner. `views-crafdapi#53` is blocked on that partner's data contract and could sit for a long time. Both have now landed. The label's agreement with reality **no longer rests on any source-reading check**: both were deleted on 2026-08-12, not because those gates opened but because a consumer improving its own code broke the mechanism twice in a day (ADR-017 §5 erratum). What remains is C-92 — a consumer's word that its query uses the name it declares.

**What was already prevented, and then accepted.** A reviewer caught that the obvious sequence created a window where the source-reading check was deleted before the consumer-side check existed, leaving a green build proving only that two values this platform authored agreed with each other. ADR-017 forbade that ordering, and the ordering was in fact honoured — both partners' consumer-side checks landed before their source-read was removed. The window exists anyway, permanently, because the source-reads were then deleted on their own demerits. This entry exists so that history has a home outside the document that states it.

Cross-refs: **C-77** (the same field's producer-side half, resolved), ADR-013 §4.1a, ADR-017 §5/§8/Appendix B, views-appwrite#75, views-faoapi#379, views-crafdapi#53.

**⚠ AMENDED 2026-08-12 — one partner's residual got worse, not better.** This entry says the label's agreement with reality "rests on the source-reading check … which someone could remove believing the registry check replaced it." PR #239 removed the FAO half on the strength of views-faoapi#379 — correct sequencing under ADR-017 §5, and still the wrong outcome, because **#379 and the deleted check do not cover the same failure.** #379 binds their served-name constant to the registry; the deleted assertion was that they still *query* on it. Registered separately as **C-92**, because it is narrower and more acute than the residual recorded here: not "we never checked the consumer's code" but "we checked it, for one partner, and stopped."

---

### C-85: A cross-repo ask is adopted on its stated terms without anyone measuring the current state

| Field | Value |
|-------|-------|
| ID | C-85 |
| Tier | 3 — no delivery is affected and no wrong data ships. What is at risk is spending a coordinated three-repository change on work that is already done, which is expensive in exactly the currency this platform has least of. |
| Source | #133 execution (2026-08-05) — the ask was re-measured before implementing it |
| Trigger | The next time an issue filed by another repository's seat is picked up for implementation. Before writing code, check what this repository already delivers and what the consumer already reads — the two are stated in the issue and were both wrong last time. |
| Owner | Whoever implements a cross-repo issue. This is a habit, not a mechanism; see below for why no guard is proposed. |
| Location | Not a code defect. #133; ADR-013 §2.2a. |

#133 asked for three declared fields — `maturity`, `source`, a required schema version — and said `_save_contract` ships the forecast run only. It was filed in good faith by the views-faoapi seat, accepted, and carried on the backlog for weeks. Measured on 2026-08-05, before writing anything:

| the ask | the measured state |
|---|---|
| stamp `source`, *"`source="unknown"` is what's live today"* | **already delivered** as `provenance.ensemble`, and views-faoapi reads exactly that key |
| declare a required schema version | **already delivered** as `contract_version` — on the run manifest and in every shard header |
| stamp `maturity` on the run manifest | genuinely missing — but it belongs in the **shard header**, which is where the consumer reads it, and it is **not this repository's to stamp** |
| *"the global historical is not uploaded"* → decide whether FAO stops receiving it | **false.** `_save_contract` uploads it, `category="historical"`, under the same interlock as the forecast. There was no decision to make |

**Two of three fields already shipped, and the decision had no premise.** Had the issue been implemented as written, the cost would have been a `contract_version` bump — which is written *inside* the header bytes that §10 pins — and therefore a rebuild of the golden fixture and a coordinated re-vendor across all three implementing repositories, in order to add two fields that were already there.

**Why the request was wrong is more useful than that it was wrong.** It was not careless. It was written against the **run manifest**, which is the artifact whose name suggests it carries run-level facts. The consumer reads them from the **shard header's `provenance`**, because that is where the producing pipeline's identity travels. Both seats were describing a real need and neither was describing the same object. A cross-repo ask names an artifact in the other repo's vocabulary, and vocabulary is exactly what does not survive the trip.

**No guard is proposed, deliberately.** There is no mechanical check for "is this request still true", and inventing a ceremony — a template, a checklist field — would be process theatre that decays into an unread heading. What made the difference here was reading the consumer's source before writing any, and that is a habit worth writing down rather than automating. Registered so the next person has the worked example instead of the rule.

Cross-refs: **C-72** (the re-vendor this would have triggered, and the trigger A2 now rides on), **C-77** (the historical leg whose correctness is what makes the co-delivery premise false), ADR-013 §2.2a, ADR-014 §4 (the deferral's named trigger), #133, views-faoapi ADR-033 and its register C-169.


**⚠ This entry has no closing condition, and that is the finding — 2026-08-13.** Its Trigger is a habit (*"check what this repository already delivers before writing code"*), it states *"No guard is proposed, deliberately"*, and its Location says *"Not a code defect."* **No evidence in any tree can ever satisfy it**, so it cannot be closed, only carried — which is what a register is not for.

It is a worked example wearing a risk's clothes. **Give it a real trigger or move it to a lessons artifact**; the post-mortem at `reports/post_mortems/2026-08-12_the_guards_that_did_not_guard.md` is the natural home. Left open here only because relocating a record is itself a change that should be deliberate rather than done in a truth pass (Register Conventions: a relocation is not complete until the destination exists and is cited by number).

---

### C-84: Every identity this repo delivers under dies on 2026-11-17, within 3h35m of the other

| Field | Value |
|-------|-------|
| ID | C-84 |
| Tier | 2 — not silent. The delivery fails loudly and completely, which is the correct behaviour and also the whole problem: there is no degraded mode, no fallback identity, and the date is known in advance. A foreseeable total outage that nobody has scheduled work against is a structural risk, not an operational surprise. |
| Source | views-appwrite coordinate registry v1.4.3/v1.4.4 — operator console read, 2026-08-05 (þing-02 A3(i)) |
| Trigger | **A date, unusually — 2026-11-17.** The registry records `VIEWS Pipeline Core` expiring 12:35 and `UN FAO` 16:10 that afternoon. Act when the un_fao delivery is next scheduled within a month of it, or when anyone plans a rotation, whichever is first. **Since 2026-08-19 the first arm fires by itself**: `tests/test_credential_expiry.py` goes red from 2026-10-18, so the date no longer depends on anyone remembering it. |
| Owner | Simon, and only Simon — issuing and installing keys is a console action. This entry exists so the date is visible from *this* repo's planning surface rather than only from the platform's. |
| Location | `views_postprocessing/{unfao,crafd}/appwrite_env.py` — the declared coordinates; the values live in the environment and the registry, never here. |

The FAO delivery authenticates with the `UN FAO` key. That key expires **2026-11-17 16:10**, and the platform's other key three and a half hours earlier. Read from the console rather than inferred, and recorded in the registry this repo pins.

**Why the gap is the finding and not the dates.** Three and a half hours is not a stagger — it is close enough that the two keys cannot cover for one another under any realistic response, and both are on the same seam. After 16:10 that afternoon every identity on it is dead at once: model and ensemble writes, the un_fao delivery, the CRAF'd delivery, all preflights, and FAO's own read access. A rotation that assumes one key can carry traffic while the other is replaced has no such window.

**What this repo can and cannot do.** It cannot rotate anything; it holds no credentials and must not (þing-01 D3). What it can do is fail early and legibly rather than mid-delivery — and it does not currently. `appwrite_env.py` validates that the declared variables are *present*, which an expired key still is. An expired key is indistinguishable from a valid one until the first request comes back unauthorised, by which point a delivery is part-way through.

**Deliberately not fixed here, and the reason is C-84's own shape.** A preflight that checks key validity means an authenticated call at startup, and the only project to make it against is production — which **þing-01 D2** forbids for tests and this would not quite be — and which that verdict explicitly permits as *read-only preflight validation*, so the obstacle here is the authenticated call, not the prohibition (see C-95). The honest position is that this is a *date to act on*, not a mechanism to build, and inventing a mechanism would be building the wrong thing to feel busy. Registered so the date is not discovered by an outage.

**The trigger now fires on its own (2026-08-19), and this is not the mechanism above.** The first arm of the trigger — *"act when the un_fao delivery is next scheduled within a month of it"* — was a trigger nobody could notice: it fired in someone's memory or not at all, which is the same defect that withdrew the third arm of C-94's trigger and which ADR-014 §4 exists to forbid. `tests/test_credential_expiry.py` declares the two expiries and fails from 30 days out, naming the dates, the 3h35m gap, who owns the rotation (operator; views-appwrite#12, key split views-faoapi#338), and the three ways to make it pass — rotate and update the constant, update the constant if a key was replaced early, or set `ACKNOWLEDGED_UNTIL`. **The third is the only one available to someone without console access**, which is most people who will meet this gate; omitting it here would reproduce the merge-queue-hostage outcome the acknowledgement exists to prevent.

**It is emphatically not the key-validity preflight this entry rejected.** No authenticated call, no credential, no network — a calendar and two declared datetimes. The rejection above stands and is unaffected: what was wrong was building a mechanism to *discover* a fact already known; what was missing was making the known fact impossible to forget. **The acknowledgement is the load-bearing part, and the first draft did not have it.** `/code-review high` found two design faults that would each have ended with the test deleted. (a) A literal pin on the two datetimes made the tripwire's own prescribed remediation — *rotate, then update `KEY_EXPIRY`* — fail a second test whose message said not to adjust the constant. A guard that refuses its own documented fix is worse than no guard, and it would have landed on the one person who could not route around it. The pin is gone. (b) From 2026-10-18 the gate would have been red for **every unrelated pull request**, clearable only by an operator console action the repository cannot perform — which is precisely what `pyproject.toml` says about ruff, citing ADR-014 §3: *a gate that starts red gets switched off*. `ACKNOWLEDGED_UNTIL` is the in-repo escape: a declared, reviewed, dated edit meaning *seen, and being acted on*, which **cannot be set on or after the expiry** — so it postpones attention and can never replace it.

Four companion tests keep it honest rather than decorative: the firing branch is exercised against a probe **derived from** `KEY_EXPIRY` (**C-102** — a guard that has never run is unproven; deriving it rather than hardcoding means the proof survives a rotation instead of quietly expiring with it); an acknowledgement past the expiry is refused; `LEAD_DAYS` is floored, because shaving a week off the warning neuters the guard while leaving it looking present; and the outage-day text is checked, since the first draft would have told an operator the keys expired *"in -3 days"* while the seam was down. All verified by mutation.

Cross-refs: **C-81** (the same operator session's other half — branch protection and the CI token), **C-27** (no rotation mechanism for a secret value upstream), **C-57** (the pinned-registry detector, which is how this arrived here at all — it demanded the v1.4.4 bump and the bump is what surfaced the expiry), þing-02 A3(i), views-appwrite C-65 and C-66.

**The tripwire gates the release path, which this entry did not say when it was added — see C-110.** From 2026-10-18 it reddens `test`, which `protect_main` makes a required check with zero bypass actors, so no release can be tagged until the keys rotate or `ACKNOWLEDGED_UNTIL` is set.

---

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
| Tier | ~~1~~ → **2**, re-tiered 2026-08-13 by this entry's own rule once its Tier-1 gate was answered (see the amendment below). Original rationale, which applied while the gate was open:  silent data fabrication with no error signal: absence of evidence becomes evidence of absence in FAO-delivered values |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When changing the historical fetch path, or when bumping views-pipeline-core's dataloader — verify whether the **currently active** path (`get_feature_frame`, since #126) zero-fills missing months/cells, and that any fill count is logged rather than silent |
| Location | views-pipeline-core `modules/dataloaders/dataloaders.py:1208` (`fillna(0.0)`, legacy pandas fetch); consumed at `views_postprocessing/unfao/managers/unfao.py:125-147` (`_read_historical_data`, legacy branch). Frame-native branch: `:101-124` (`_read_historical_frame` → `get_feature_frame`) |

`_fetch_data_from_datafactory()` applies `df.fillna(0.0)` unconditionally to all features. For `lr_ged_sb/ns/os`, a datafactory assembly gap (unharvested month, failed source) flows to FAO as "zero fatalities" rather than failing. The postprocessor's `_validate()` checks only the 9 metadata columns for nulls (`unfao.py:188-221`), never the feature columns — so the fabricated zeros pass every gate. There is no fill-count logging, so the corruption is unquantified and undetectable after the fact. The zarr exposes `last_valid_month_id` in its attributes, which would permit bounded filling (fill only outside the declared valid range, fail on fills inside it), but it is not consulted.

Location is in views-pipeline-core, but the impact lands on this repo's FAO delivery; registered here because the consuming call and the delivery responsibility are here.

**Filed upstream 2026-08-01 as views-pipeline-core#366**, carrying the open question this entry could not answer from this seat: **does `get_feature_frame` inherit the same unconditional `fillna(0.0)`, or does the frame-native fetch propagate NaN?** That decides whether C-26 is live (run-0 shipped 28.4M historical rows through the frame path) or historical (it describes only the branch #149 retired). The entry stays Tier 1 until answered — deliberately not downgraded on a guess.

See also C-25 (same data path, wrong-file variant), C-15 (upload provenance would aid post-hoc detection).

**OPEN VERIFICATION QUESTION (review-rr 2026-07-31) — tier held at 1 pending an answer.** `fillna` has **zero occurrences in this repo**; the fabrication site is entirely upstream. Since #126, the historical path run-0 actually used is `get_feature_frame` (`_read_historical_frame`), **not** the pandas `get_data` branch that reaches `dataloaders.py:1208`. It could not be verified from this seat (views-pipeline-core is deliberately absent from test environments, per repo convention). **Question for the pipeline-core seat: does `get_feature_frame` inherit the same unconditional `fillna(0.0)`, or does the frame-native fetch propagate NaN?** If it propagates NaN, this Tier 1 now describes only the legacy branch (retirement is the named post-run-0 follow-up) and should be re-tiered. **Do not downgrade on inspection of this repo alone** — the deliverable ran through the unverified path at global scale on 2026-07-27.


**⚠ The Tier-1 gate is ANSWERED, and the answer is no — 2026-08-13.** This entry says it is Tier 1 *until* someone establishes whether `get_feature_frame` inherits the `fillna(0.0)`. **views-pipeline-core#366 closed 2026-08-04**, and at the version this repository now installs the loader states the opposite in its own docstring: *"no silent `fillna(0.0)` — NaN policy belongs to the engine boundary."*

By this entry's own re-tier rule, Tier 1 is no longer justified.

**Three further claims are now false**, and each would send a reader to the wrong place:
1. The Location points at a legacy branch in `unfao.py` that **no longer exists** — `_read_historical_data` refuses any queryset not declaring `feature_frame` and calls only `_read_historical_frame`.
2. *"There is no fill-count logging"* — false upstream; the fill now logs total and per-column counts before substituting.
3. *"The zarr exposes `last_valid_month_id` … but it is not consulted"* — false here; it is read via `source_metadata.last_valid_month_id`, fabricated months are dropped, and it degrades open with a log line.

**What genuinely survives is upstream and different:** views-datafactory pre-fills its grids with `fill_value=0.0` per its ADR-047, tracked as **views-datafactory#420 (OPEN)**. That is the live risk; the mechanism this entry describes is not.

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

**Filed upstream 2026-08-13 as views-pipeline-core#471.** Two years of this entry sitting here with two named fix sites and **no issue filed anywhere** is the finding. The neighbouring entries C-26 and C-27 were filed upstream on 2026-08-01 and **both closed within three days** — so the expected cost of filing was three days and the expected cost of not filing was this entry's whole lifetime.

Cross-referenced there to their **#248 / #347** (the same defect class on the Appwrite call path, already fixed) and **#168**. The fix sites are in their tree: this repository calls `get_feature_frame` and has no view of the transport.

**A second argument the entry did not have when filed.** On 2026-08-12 FAO reported empty endpoints, and it took a day to establish the cause was an unannounced migration with no delivery since. A hung run and a run nobody started are indistinguishable from outside — a deadline turns the second into a loud failure. See **C-94**.

---

### C-30: GAUL-uncovered land cells crash or corrupt global delivery (absorbs C-34: the coverage contract)

| Field | Value |
|-------|-------|
| ID | C-30 |
| Tier | 2 — the exclusion manifest and cell-count contract are pinned in code and were exercised live at global scale in run-0; residual is upstream-regression risk, not an unguarded silent-corruption path |
| Source | `expert-code-review` (2026-06-12), verified by direct data inspection; **merged with C-34** (`expert-code-review` 2026-06-12) during review-rr 2026-07-31 |
| Trigger | When a region's expected cell count or exclusion manifest changes upstream — a views-datafactory region redefinition (`regions.py`, the bundled `*_pgids.json`), a new GAUL curation like ADR-043, or a region-string change in views-models `config_queryset.py` — verify `EXPECTED_CELLS_BY_REGION` and `EXCLUDED_GIDS_BY_REGION` are re-derived from the live producer rather than trusted as frozen |
| Location | `views_postprocessing/delivery/coverage.py:56` (`land_gaul: 64_742`), `:92` (`EXCLUDED_GIDS_BY_REGION`), `:99`; `views_postprocessing/unfao/managers/unfao.py::_check_coverage`, `:300` (`_validate`); views-models `postprocessors/un_fao/configs/config_queryset.py`; views-datafactory `src/datafactory_query/regions.py` |

Verified 2026-06-12: of the datafactory's 64,818 `land`-region cells, 64,736 have complete area-majority metadata; exactly 82 are unassigned across all 7 GAUL fields — all remote sub-Antarctic islands FAO's GAUL 2024 boundaries do not cover (Macquarie, Auckland Islands, Prince Edward; sample gids 51078, 51798, 53979, 62356, 94776, 99027). The mitigation must be a named exclusion-list constant with the gids, count-asserted in both the enricher and a test, logged at WARNING, and disclosed to FAO — not a generic `code != -1` filter, which would silently absorb future coverage regressions. Generalizes the previously documented "5 ocean cells" of africa_me_legacy (those 5 are among the excluded set).

**Count drift corrected 2026-06-26 (the frozen-list tripwire working as designed):** deriving the exclusions from the live producer (datafactory **v1.4.0**) gives **64,742** complete + **76** excluded, *not* the 64,736 / 82 verified on 2026-06-12. Cause: datafactory **#163 (ADR-043)** supplemented **6 Azorean cells** (gids 182470, 183190, 183909, 183910, 186058, 186778) into `land_gaul` — they are now covered, not excluded. vpp's *own* built lookup (`data/gaul_lookup.parquet`) already ships 64,742, so the old 64,736 pin would have false-positived against our own artifact. NB the authoritative exclusion source is the **region complement** `land − land_gaul` (76), not the raw `gaul0_code == -1` (82) — the latter does not reflect the ADR-043 curation.

**Mitigation landed (S4, 2026-06-26, `sprint/fao-input-integrity`):** the 76 excluded gids are pinned as a frozen manifest in `delivery/coverage.py` (`EXCLUDED_GIDS_BY_REGION`), the count is corrected to 64,742, `assert_no_excluded_cells` is wired into the manager's `_check_coverage` **region-gated** (a no-op for unpinned `africa_me_legacy`, so its 5 ocean cells are unaffected), the 76 are disclosed in `docs/fao_excluded_cells.md`, and a test cross-checks the manifest against the datafactory sibling when present (drift tripwire). **Residual:** still Tier 1 until the live `land_gaul` run (views-platform/views-models#127) exercises it end-to-end — the guard is unit-proven but not yet run against a real global delivery.

**The tripwire now runs in the gate, and it did not until 2026-08-17.** *"When present"* meant a developer laptop: views-datafactory was not fetched in CI, so `test_manifest_matches_datafactory_land_minus_land_gaul` skipped on every pull request. That mattered more than it looked, because on 2026-08-17 this repository told FAO in writing that the exclusion list *"is frozen in code and asserted against the producer in our test suite, so it cannot drift without failing loudly"* — a guarantee the gate was not carrying. The sibling is now fetched (see C-46 for why the earlier attempt was reverted and why that reason did not survive checking), and the tripwire reads `src/datafactory_query/{land,land_gaul}_pgids.json`, both of which views-datafactory tracks.

This does **not** move the tier. The residual above is unchanged: the guard is now enforced continuously rather than incidentally, but what holds C-30 at Tier 1 is the absence of a real global delivery exercising it end-to-end, and no CI wiring supplies that.

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
| Location | `views_postprocessing/<partner>/managers/<partner>.py` — the module-level `_build_prod_forecasts_store`, `_build_partner_store`, `_partner_appwrite_config` (methods until 2026-08-05), and the four hardcoded `os.getenv("APPWRITE_<PARTNER>_*")` names inside the last of those; declared names in each partner's `appwrite_env.py`. **Symbols, not line numbers** — see the note under the measurement below. |

Mitigation: a small `DeliveryProfile` (bucket/collection/database ids, category, targets) passed to the manager — one manager class, N store configs. Scheduled **after** the FAO global delivery ships (D-09); the only immediate action is deleting the commented-out config blocks at lines 80-107, which are a mis-uncomment hazard during deadline work.

**Update 2026-07-31 (review-rr — two stale facts corrected, and the deferral has expired):**
1. **The dead config blocks are gone.** `unfao.py:80-107` is now the class definition and `__init__`; the commented-out alternative `AppwriteConfig` blocks no longer exist. That immediate action — and D-09's first named exception — is **discharged**.
2. **"273-line manager" is stale**: `unfao.py` is now **636 lines**, so the copy-paste-per-store cost this entry warns about has roughly doubled.
3. **Partially mitigated by þing-01 #134.** `unfao/appwrite_env.py` now declares the env **names** centrally (`CONNECTION_ENV`, `PROD_FORECASTS_ENV`, `UNFAO_ENV`) and validates them fail-loud before every `AppwriteConfig` construction, following the PLATFORM-001 coordinate registry. Names are no longer scattered string literals. **What is still hardcoded is store *identity*** — which names apply to which store, the targets list, and the category strings — so the `DeliveryProfile` case stands. Tier held at 2.
4. **The deferral condition has expired**: D-09 scheduled this "after the FAO global delivery ships." It shipped 2026-07-27. Ready for the "calm 1-day job" whenever #97 scoping lands.

**Update 2026-08-14 — the extraction trigger has now fired, twice, and this is the record of it.**

This entry's remaining trigger reads: *"a **third** in-repo partner package, **or** the first bug that must be hand-patched identically in both manager files — whichever comes first."* The second arm has fired twice. C-79 (2026-08-05) fixed `_ContractStorePort.upload`'s fail-open result check by hand in both partners. C-99 (2026-08-14) fixed the identical fault in `download`, again by hand in both.

**The decision is still to duplicate, and the reason has changed.** It is no longer "no second incident has shown the shape" — one has. It is that the shape the incidents showed is not the one this entry proposes extracting. C-33's mitigation is a `DeliveryProfile` carrying store identity, and neither C-79 nor C-99 was about store identity; both were a result-shape check that happens to live in a duplicated file. Extracting a `DeliveryProfile` would not have prevented either.

**What has changed is that the duplication is now mechanically held.** `tests/test_store_port.py::test_the_two_partners_ports_have_not_drifted` fails if the two `store_port.py` files differ. Note precisely what that does *not* buy: it would not have caught C-79 or C-99, because both files stayed byte-identical throughout while carrying the defect in the untreated method. It closes the partner-vs-partner axis; the method-vs-method axis is closed by `tests/test_store_port.py` covering all four methods, which it now does for three and records the fourth as C-100.

The `DeliveryProfile` extraction stays where D-09 put it: with the second store's scoping (#97). What is discharged here is the pretence that nobody had hit the trigger.

**Update 2026-08-03 (PR #211) — the thing this entry warned about has happened, and it is being kept on purpose.**

This entry's own Tier-2 rationale was that the design *"forces copy-pasting a 273-line manager per store."* PR #211 added `views_postprocessing/crafd/` — a second partner package whose `managers/crafd.py` is a **line-for-line copy** of `unfao/managers/unfao.py`. Measured with

    diff views_postprocessing/unfao/managers/unfao.py \
         views_postprocessing/crafd/managers/crafd.py | grep -c '^[<>]'

**26** — thirteen differing lines on each side (re-run 2026-08-13 with the command above; it read **32**/sixteen when filed, and the drift is itself the entry's point). Substitute every form of the partner name (case-insensitively, including `un_fao`/`un_crafd` and `faoapi`) and it falls to **2**: one line per side.

The **thirteen** are, by category *(the breakdown below was written for the sixteen and has not been re-derived — treat the count above as authoritative and re-run the command rather than this list)*: one import, one class name, two partner-named method definitions, their two call sites, one refusal-message string, one line that is *both* the `*_ENV` tuple reference and the store label, the four env-name literals, and four lines of prose.

**None of the difference is behaviour, but "byte-identical" is too strong for one method.** `_read`, `_transform`, `_validate`, `_check_coverage` and `_build_historical_artifact` are byte-identical. `_save_contract` is not: **four** of the thirteen fall inside it (lines 356, 367, 368, 371) — two comments, the refusal string, and one call argument. The datastore construction at :355 is **byte-identical**. All four are partner-name substitutions; none changes what the method does. *(An earlier correction updated "sixteen"→"thirteen" without re-checking this sentence, and left "five … the datastore call" — both wrong.)*

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
| Location | `views_postprocessing/<partner>/managers/<partner>.py` — the `class <PARTNER>PostProcessorManager(PostprocessorManager, ForecastingModelManager)` statement (double inheritance); `_build_prod_forecasts_store`, `_build_partner_store`, `_partner_appwrite_config` (env/AppwriteConfig/DatastoreModule — moved OFF the class 2026-08-05, see the update below); `_validate` and `_check_coverage`; the DIP sink adapter `_ContractStorePort`. **Since 2026-08-03 all of it exists twice** — `unfao` and `crafd` are the same file with the partner name changed (C-33). Symbols rather than lines, deliberately: an earlier version of this row was invalidated by a comment edit four lines long. |

`UNFAOPostProcessorManager` subclasses **two concrete** pipeline-core base classes (`PostprocessorManager`, `ForecastingModelManager`) and **interleaves infrastructure** (env reading, `AppwriteConfig` construction, `DatastoreModule`, path resolution) with the FAO **business logic** (GAUL enrichment, the 9-column null gate) inside the lifecycle hooks. Consequences: (a) the FAO logic cannot be instantiated or unit-tested without the full framework + Appwrite env + viewser; (b) **pandas cannot leave the delivery path** because the inherited data loader and `PGMDataset` are pandas — gated on pipeline-core's own DataFrame retirement; (c) **SDP exposure** — heavy *inheritance* coupling to a pipeline-core that is itself unstable (mid-migration), so upstream changes break far from their cause (cf. C-27, C-29); (d) it's the repo's only composition-over-inheritance violation. The dependency itself is correct (`unfao.py` genuinely *is* a pipeline-core postprocessor) — the issue is its **blast radius**. Mitigation (does **not** fight the Template-Method framework): keep the subclass as a **thin shell** but extract `enrich` + `validate` + the 9-column contract into a pipeline-core-free core object the manager *calls*, and wrap the Appwrite I/O behind a small delivery-sink adapter (DIP). This makes the FAO logic testable standalone and insulates it from pipeline-core churn.

**Update 2026-07-27 — the pandas gate (consequence b) has LIFTED, and the mitigation shape largely landed via ADR-013:** pipeline-core shipped its frame-native fetch (`get_feature_frame`, tested, previously zero consumers), and this repo became its **first production consumer** (#126 / PR #129): the historical path now fetches a `views_frames.FeatureFrame` and builds the artifact pandas-free (`unfao/historical.py`), reader-parity-proven against a legacy characterization golden. The forecast path is frame-native end-to-end (wire/ + streaming leases, PRs #115–#129). Pandas remains ONLY on the legacy forecast branch (kept until run 0 proves the contract path live; its deletion is the named post-run-0 follow-up) and in the retired-in-place `enrichment.py`/`extraction.py` legacy seams. The double-inheritance shell (consequences a/c/d) still stands — the residual scope of this entry.

**Priority raised by the samples/uncertainty requirement (2026-06-27).** The delivery is moving from point estimates to **predictions-with-uncertainty (S samples per cell)**. This makes the pandas gate (consequence b) materially worse, not just cosmetic:
- **views-frames** stores a distribution as a native contiguous `(N, S)` float32 array (sample axis always explicit; point = S=1). **pandas `PGMDataset`** stores it as **object-dtype list-in-cell** — each of N cells holds a separate length-S numpy array (`_ViewsDataset._convert_to_arrays` / `_check_prediction_samples` in pipeline-core `data/handlers.py`).
- Cost of the object-dtype representation scales ~linearly with S: memory blow-up (this is pipeline-core's own OOM, **#181/#189** — "~18 GB, kills runs" off list-in-cell DataFrames), an encode/decode tax at every parquet/API boundary (faoapi's inverse `_convert_to_arrays`), and a silent `np.resize` pad on mismatched sample counts (feature path).
- At S=1 the penalty is invisible; at S≈1000 it dominates → the uncertainty work is the strongest driver for the frame migration.

**Concrete pipeline-core gate (what "DataFrame retirement" actually requires).** vpp inherits three *concrete* pandas pieces (the abstract `PostprocessorManager` base is fine): the input loader (`ViewsDataLoader.get_data` → parquet→pandas), the container (`PGMDataset`/`_ViewsDataset`, object-dtype cells), and the prediction-store parquet I/O. Closing the gate = pipeline-core **Epic #186 + #207** landing: frame-native input loader (**#161**, gated on the datafactory↔core output contract **#162/#136**), a frame container replacing/re-backing `PGMDataset` (**#159**), frame/arrow store I/O, and retiring the legacy pandas report path (**#211**, the #181 OOM source). It is an epic, not a PR. The half **vpp owns and can do now** (unblocked): the thin-shell de-inheritance above — extract enrich/validate into a pipeline-core-free core the manager *calls*, so the eventual frame swap is a one-seam change. Dependency direction confirmed: pipeline-core does **not** import vpp; vpp **is-a** pipeline-core postprocessor (Template-Method subclass), so it inherits pipeline-core's representation rather than choosing its own.

**Migration backlog (2026-06-28):** the full pandas→views-frames map + sequenced, parity-preserving removal plan is now tracked as epic **#85** ("Push pandas to the seams") with stories #86–#92 and tracking #93. The unilateral arc (S1–S3: generalize `frames.py` to S>1, frame-native extraction siblings, forecast convert-at-the-door) makes vpp's interior carry `(N,S)` behind frozen wires; S6 (#91, outbound arrow wire) is gated on faoapi #45, and S7 (#92, historical inbound) is gated on this entry's pipeline-core gate above.

**Wire contract posted (2026-07-03) — the S6/#45 circular wait is dissolved.** A three-way audit (pipeline-core / producers / consumer+substrate, all on `origin/development` + maintainer-authored issues) established: (i) there are **two wire hops** (producer→store; vpp→faoapi) and the roadmap's arrow work covered only the second; (ii) **no publish path from PFE to the prediction store exists at all** — models#143's "no pipeline-core change required" is **falsified** (PFE's `use_prediction_store` is stored then only logged, `prediction_frame_ensemble.py:141/:799`; `PredictionIOManager._upload_to_prediction_store` raises `NotImplementedError`, `io.py:117`); (iii) full global draws ≈ **9.5 GB/target**, so the wire mandates per-month sharding; (iv) the "platform ADR-046" cited as the format authority **does not exist** (phantom). **ADOPTED 2026-07-15 as ADR-013** *(post-adoption: F1 invisibility confirmed live — six stranded orange_ensemble forecast docs in unfao_bucket, forecast serving has been empty all along; both §11.4 legacy guards merged same day, Hop-B guard must reach production before vpp's first contract upload — **views-faoapi C-161**)* after five reviewed iterations (two seat reviews, reconciliation, owner-ratified F1) — maintainer sign-off on views-models#149. The v1 proposal history: Hop A = Track A zip archive per (run,target,month) + manifest-last commit marker (new **pipeline-core#269**); Hop B = per-month `views_frames.io.arrow` (#91/faoapi#100); interior = per-target 2-D `PredictionFrame`; the 9 GAUL columns move to a **gid-keyed sidecar**; the **#149 no-collapse boundary is named: vpp `delivery/draws.py`** (a new invariant, sibling of coverage/identity — follow-on vpp work with the durable vpp ADR after explicit sign-off); target vocabulary **decided: `lr_ged_sb/ns/os`**, producers rename at publish (models#146).

**Update 2026-07-31 (review-rr — the prescribed DIP mitigation has half landed, uncredited).** This entry's mitigation was: "*keep the subclass as a thin shell but extract `enrich` + `validate` + the 9-column contract into a pipeline-core-free core object the manager calls, and wrap the Appwrite I/O behind a small delivery-sink adapter (DIP).*" The **sink half exists**: `_ContractStorePort` (`<partner>/store_port.py` since 2026-08-14 — it lived at `unfao.py:37-78` when this was written) wraps the store client behind a four-method port (`latest_file_id` / `file_metadata` / `download` / `upload`), and the contract delivery path drives the store through it. The **invariant half also largely exists** as pipeline-core-free modules the manager calls: `delivery/coverage.py`, `identity.py`, `draws.py`, `parity.py`, `provenance.py`, `observed_range.py` (the package docstring pins them representation-free), plus `unfao/historical.py` and `unfao/wire/`. **Residual scope of this entry is now the input side and the shell itself:** the double inheritance at `:80` (consequences a/c/d), the inherited `ViewsDataLoader`/`PGMDataset` on the legacy branch, and the fact that the FAO logic still cannot be instantiated without the framework. Tier held at 2 — the blast radius argument is unchanged for what remains. This is the root of **Cluster G**.

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

**Update 2026-08-05 — the stated gate was wrong, and the source half of the mitigation has now landed.**

*The gate first, because it is what kept this entry parked.* The line below said the residual was *"gated on views-pipeline-core 3.0.0, which is a release signal rather than engineering work"*. 3.0.0 shipped on 2026-08-03 and nothing became possible. Two different gates had been conflated:

- **Consequence (b), the pandas gate** — genuinely gated on pipeline-core's DataFrame retirement, which is an epic (#186/#207), not a version number. It lifted on its own on 2026-07-27 when the frame-native fetch shipped, and 3.0.0 had nothing to do with it.
- **The de-inheritance** — never gated on any pipeline-core release. **It is gated on views-models**, which is the thing nobody had written down. `postprocessors/un_fao/main.py:27` constructs `UNFAOPostProcessorManager(...)` directly, and the framework's Template Method drives `_read`/`_transform`/`_validate`/`_save`. **The inheritance *is* the integration contract with views-models.** Removing it means writing a different launcher there, so it is a two-repository change and an operator decision — not, as this entry implied for two days, unblocked work waiting on nobody.

*What landed.* This entry's own prescribed mitigation was to wrap the Appwrite I/O behind a DIP adapter. The **outbound** half landed in July as `_ContractStorePort`. The **inbound** half never did: `_prod_forecasts_datastore`, `_<partner>_datastore` and `_<partner>_appwrite_config` were still methods on the manager, constructing `AppwriteConfig` and `DatastoreModule` inline. They are now module-level functions taking declared arguments — `_build_prod_forecasts_store`, `_build_partner_store`, `_partner_appwrite_config`.

That is a smaller change than it sounds and a bigger one than it looks. Smaller: no delivered byte moves, and the three functions are the same code with their inputs declared. Bigger: **consequence (a) is substantially discharged for this surface.** Store construction, its refusals and their ordering are now testable with no manager instance, no views-models path manager and no Appwrite environment — `tests/test_store_construction.py`, 14 tests, which could not have been written at any price a day ago. That is the first time any part of the manager seam has been reachable without the framework.

*Two things found while in there.* `self.ensemble_path_manager` was assigned in `__init__` and in the store builder, read exactly once four lines after being set, and read nowhere else in either partner package or in views-models — a method-local value wearing the costume of manager state. And a `loa = "pgm"` assignment followed by `if not loa: raise`, an unreachable branch guarding a variable never used again, beside a commented-out block that had computed it for real. Both gone.

*Measured.* The manager **class** went 351 → **272 lines** (16 → 14 methods); both partner files are 440 lines against a 450 directory budget. A new ratchet, `test_the_manager_class_itself_stays_thin`, bounds the class at 300 — added because the existing budget counts the *directory*, so it cannot see a class re-absorbing logic, and this refactor is precisely the shape it is blind to. Both bounds now stand; neither was relaxed.

**Residual scope, stated honestly.** The double inheritance itself, and with it consequences (c) SDP exposure and (d) composition-over-inheritance. Not unilaterally actionable, and arguably not a defect: this entry has always conceded that *"the dependency itself is correct — `unfao.py` genuinely **is** a pipeline-core postprocessor"*, and ADR-015 §1 argues there is nothing to unwind to. What remains is exposure to an upstream that moves, which 3.0.0 demonstrated by moving.

**Trigger, corrected.** Not a pipeline-core release. Revisit when **views-models changes how postprocessors are launched** — at which point de-inheritance becomes a one-repo change rather than two — or when an upstream base-class change actually breaks a delivery, which `tests/test_framework_contract.py` now catches here rather than on the partner's run.

Tier held at 2: the blast-radius argument is unchanged for what remains, and containment is not removal.

*Did not:* the double inheritance (the `class UNFAOPostProcessorManager(...)` statement — this row cited `unfao.py:80` when written, and that number has moved twice since) stands, and so do consequences (a) — the FAO logic still cannot be instantiated without the framework — and (c)/(d). **This entry remains open on exactly that scope.** ~~Its remaining fix is gated on views-pipeline-core's 3.0.0 (C-44/C-62), which is a release signal rather than engineering work.~~ **Refuted by the 2026-08-05 update twenty lines above**, which records that 3.0.0 shipped on 2026-08-03 and nothing became possible — the gate is views-models, not a release. Struck 2026-08-13 because it was the last sentence in the entry and therefore the one a reader leaves with.

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

**(b) The re-vendor obligation is stronger than "our fixture changes".** ADR-013 §10 is explicit: *"All three implementing repos' test suites consume the same bytes … The other two repos **vendor a copy** and carry a **pinned root-hash equality test** … A change to the fixture is a change to the contract."* Verified — faoapi's copy is at `tests/forecast/golden/wire_contract/SHA256SUMS`, pinned by views-faoapi's `tests/forecast/test_wire_golden_fixture.py`. So the upgrade is a **coordinated three-repo re-vendor**, and it carries an undecided question: whether it bumps `contract_version` (the payload schema does not change, only the encoder's bytes — §10 says a fixture change *is* a contract change).

**Filed, so the relocation is complete rather than assumed** (the C-08 lesson): **views-postprocessing#174** (the coordinating issue), **views-faoapi#348** (heads-up + two questions only their seat can answer), and a comment on **views-pipeline-core#280** adding the security dimension and the non-uniform-ceiling finding.

Cross-refs: **C-62** (the transitive dependency drag; the other 31 alerts), **C-46** (the datafactory version-state coupling), ADR-013 §10 (the byte-pinned fixture), views-pipeline-core **#280** (the platform pyarrow ceiling), views-faoapi **#348** (the reading half), **#174**.

---

### C-81: What actually gates `main` is weaker than it looks — CI verifies 2 fewer tests than local; the enforcement half is discharged

| Field | Value |
|-------|-------|
| ID | C-81 |
| Tier | 2 — the guards this arc built to catch cross-repo drift do not run where drift happens, and the branch they protect has no required check. Both halves are structural and both have fired-in-practice evidence. |
| Source | `code-review max` (2026-08-03) — development→main sync audit |
| Trigger | **Coverage half, re-specified again 2026-08-21 — the previous wording is now false.** It read *"its 8 gated tests are the whole remaining gap and none of them runs in CI"*. PR #280 added the views-datafactory checkout, so four of those now run in the gate. The live trigger is what remains: **the next time a change to a views-datafactory artifact that is NOT in its git repository would break a delivery** — the producer-comparison half of `test_gaul_lookup_fidelity` and the two `test_datafactory_deploy_readiness` gates still skip in CI, because the GAUL parquets and `data/assembled/` are untracked upstream (C-46, C-108). ~~*Original: when the Appwrite Seam Contract registry next moves, nothing in CI will notice.*~~ **That trigger is false** and has been since 2026-08-10: CI checks out views-appwrite at `ref: main` and sets `VIEWS_APPWRITE`, so every registry-drift detector runs there. ~~**Enforcement half:** the first time someone merges a red PR to `main`~~ — **DISCHARGED 2026-08-13**: `protect_main` now requires the `test` check (see C-86). |
| Owner | Simon — both halves need operator action. The coverage half needs a token for two private repositories; the enforcement half is a GitHub console/ruleset change. Neither is engineering work. |
| Location | `.github/workflows/run_pytest.yml`; the `protect_main` ruleset; `tests/conftest.py::sibling_repo` |

**⚠ RE-MEASURED 2026-08-21: the headline number was 8 and is now 2, and this entry did not notice for four days.**

| environment | result |
|---|---|
| CI-shaped (both siblings, tracked files only) | **468 passed, 5 skipped** |
| full local (both siblings complete) | **470 passed, 3 skipped** |

PR #280 fetched views-datafactory in CI, moving four checks from skipped to running — C-30's exclusion-manifest tripwire, C-46's release gate, the region-set check and the wire-cast dtype check. The gap it measures closed by three-quarters and the entry went on stating the old figure, in the one place a reader goes to find out how strong the gate is.

**That is not an aside.** This entry exists to measure the distance between what CI checks and what a laptop checks. Carrying a stale number is the same defect one level up, and it is why the "This repository cannot see itself" cluster names this entry alongside C-109 and C-107.

**Coverage.** Measured in an isolated clone, not estimated — **402 collected in every run**, so the whole delta is skips:

| environment | result |
|---|---|
| local, all siblings present | 362 passed / 40 xfailed / **0 skipped** |
| CI as it was | 347 passed / **17 skipped** / 38 xfailed |
| CI with the views-crafdapi checkout added | 348 passed / **16 skipped** / 38 xfailed |

*(**This table was wrong twice, and the second time it refuted itself.** Draft one said 361/40 and "same 401" — measured before the same change added a test. Draft two fixed the collected figure to 402 and did not re-derive the rows, so both rows summed to 401 beside an assertion that 402 was collected. The cause of the second error is worth recording: the measurement was taken on a `git clone` of the branch, and a clone carries **committed** state — the new tests were still uncommitted in the working tree. Measuring a claim about your own change requires applying your own change. This is the entry about miscounted tests.)* `sibling_repo` resolves `$VIEWS_<NAME>` else `../<name>`; in a one-repo checkout neither exists and the tests skip. Skipping is correct behaviour — a missing sibling *is* normal — but the consequence is that **CI verifies strictly less than a developer's laptop, precisely on the assertions that cross a repository boundary.**

Nine of the seventeen are **new in this arc**, including both registry-drift detectors (pinned edition, commit-reachable-from-`main`) for both partners. Those detectors have a demonstrated drift rate: they fired **twice on 2026-08-03**, hours apart. A detector for a fault that recurs twice in a day, running only on one machine, is most of the way to not existing.

Where each sibling stands, after trying them:
- **views-crafdapi** — public; its check read source text. Checked out in CI from 2026-08-10, recovering **one** test; **that checkout was removed on 2026-08-12** when the check it served was deleted (ADR-017 §5 erratum, C-92): the cross-seam consumer-document-name pin for CRAF'd.
- **views-datafactory** — public, but its eight tests need the producer's raw GAUL parquets, which are **not in its git repository**. Checking it out converts an honest skip into a `FileNotFoundError`; tried and reverted.
- **views-appwrite** — was private when this was written; **made public 2026-08-08** (`views-appwrite@9d80b75`) and **now checked out in CI**, recovering **seven** tests including both registry-drift detectors. No credential was needed for any of them, and none was ever the obstacle after 2026-08-08 — the obstacle was that this line went on saying "private" for two days after it stopped being true.
- **views-faoapi** — **private**, and the only one. Its single check is dark. Closing it needs either a credential or FAO's consent to make that repository public; the second is being pursued, and ADR-016 §8 carries the trigger for falling back to the first.

**Enforcement.** `main` is **not branch-protected**: `gh api .../branches/main/protection` returns `404 Branch not protected`, and `gh api .../rules/branches/main` returns `[]`. The `protect_main` ruleset exists and is `active`, but its `ref_name` include-list is **empty**, so it matches nothing — and it declared no `required_status_checks` rule. **A red `Run Pytest` would not block a merge to `main`.**

*(⚠ The include-list half of that was **wrong when written**, and only the second half carried the finding. The ruleset's own version history has two entries: `45955166` from 2026-08-08 and `46391648` from 2026-08-13. The 2026-08-08 version already reads `ref_name.include: ["~DEFAULT_BRANCH"]` — so on 2026-08-10, when this was measured, the ruleset **did** match `main`. What was true, and what actually mattered, is that it carried no `required_status_checks` rule: `deletion`, `non_fast_forward`, `pull_request` and nothing else. The conclusion stands on that alone. Found 2026-08-13 while verifying C-86's amendment against the same history endpoint.)*

*(All of the above was true when measured and is now superseded. As of 2026-08-13 04:51 CEST the ruleset targets `~DEFAULT_BRANCH` and requires the `test` context — ruleset version `46391648`. A red `Run Pytest` **does** block a merge to `main`. The xfail probe that carried this question was deleted in the same change: it asserted `False` unconditionally, so it could never flip when the finding was fixed — the residual C-36 already records for marker-style probes. The fact now lives here and in C-86, established by API measurement, because this suite makes no network calls and cannot see GitHub settings.)*

The two compound: a suite that checks less than you think, and no requirement that even that much passes. Neither is caused by this sync — both are pre-existing — but this sync is the first time `main` receives an epic whose value is largely the guards themselves.

Cross-refs: **C-46** and **C-57** (both RESOLVED; this is the residual each recorded as *"a CI-cost and cross-repo-coupling decision"* and *"worth deciding once for both"* — it now has a live home and a concrete answer per sibling), **C-80** (the other verification gap found in the same audit), #188.

**Partial mitigation 2026-08-10 (ADR-016) — the coverage half is mostly closed; the enforcement half is untouched.**

The coverage half rested on a claim nobody could check. This entry, and the workflow comment it drew on, said `views-appwrite` was **private**, so its seven checks needed a credential. It went public on **2026-08-08** (`views-appwrite@9d80b75`, a deliberate and recorded act), and the claim here went on being made for two days afterwards. No credential was required, and none had been the obstacle since that date.

CI now checks that repository out and those seven run on every pull request — including both registry-drift detectors, which is what this entry called *"the most valuable of the lot"*. **Measured on the merge run, not derived:** CI went from 16 skips to **9** (`398 passed / 9 skipped / 38 xfailed`, PR #229), the remainder being 8 views-datafactory and 1 views-faoapi. One test also changes character rather than merely un-skipping: the scan refusing registry **values** in this public repository's markdown now runs on the merge rather than only on a maintainer's machine.

**What remains, and it is two different things:**

1. **~~One dark check.~~ CLOSED 2026-08-11, and not by a credential.** This read: *"views-faoapi is genuinely private — the consumer-name pin is still laptop-only. That is one test, and it is the one whose failure mode is invisible rather than loud."* ADR-017 moved that check onto the public coordinate registry, so it runs in CI for every partner and needs no access to any private repository. The credential ADR-016 §8 deferred was never issued and is no longer the route. What remains of this half is CRAF'd's consumer-side check (views-crafdapi#53), which is the other repository's work, not a dark check here.
2. **The enforcement half is entirely untouched.** `protect_main`'s ref-name include-list was empty; it now targets the default branch, but **no status check is required**, so a pull request with a red CI can still be merged to `main`. Since merging to `main` *is* the production release, this is the half that matters most and the half that has not moved.

**And it no longer stands alone — read C-86 before closing this.** Measured 2026-08-10: `protect_main` also lists **zero bypass actors**, so once a status check *is* required, nobody can merge past it, administrator or otherwise. Meanwhile ADR-016 made this repository's CI depend on another repository. Adding the required check therefore does two things at once: it closes this entry, and it makes an unbypassable external dependency live on the release path. Both are defensible; doing them in one unremarked step is not. If the escape is wanted, a bypass actor is the same console session.

**Both happened on 2026-08-13, in one step.** The check was made required; no bypass actor was added. So this entry's enforcement half is discharged and C-86 went live in the same instant — exactly the "one unremarked step" this paragraph warned against, and it is remarked here rather than left to be discovered.

**The lesson this entry should carry.** The blocker was not a missing credential. It was a fact about another repository recorded in prose, with no date, that nothing could check — and it survived a console session, an ADR draft and a register entry, all of which repeated it. ADR-016 replaces the prose with a declaration carrying the date it was verified, and a test that fails when CI and the declaration disagree.

**Update 2026-08-05 — the operator session happened, and neither half of this entry moved.** Simon read the Appwrite console that morning (views-appwrite v1.4.4). It answered two *other* þing-02 questions definitively — there is **no non-production project**, and both platform keys expire 2026-11-17 (now **C-84**) — but the console read is a different action from issuing a token and a different console from GitHub's. So both halves stand: the two private siblings still have no CI credential, and `protect_main`'s ref-name include-list is still empty.

Recorded rather than left implicit because "the operator did a console session" is exactly the kind of adjacent fact that gets mistaken for progress on this entry. It is not. What it does establish is that the session is a thing that happens, and these two items are small enough to ride along with the next one.


---

### C-103: The clip that keeps fabricated months off the wire depends on a package this repo does not declare, and its absence is swallowed

| Field | Value |
|-------|-------|
| ID | C-103 |
| Tier | **3** — re-tiered down from 2 on 2026-08-17, when the verification question below was answered and the premise did not hold. The residual is real but narrower: not "the dependency is missing", which a different guard already refuses, but "any failure to read the boundary degrades open". |
| Source | `/repo-assimilation` (2026-08-16), measured |
| Trigger | When a delivery logs *"last_valid_month_id could not be read; skipping the observed-range clip"* — that is now the only route to an unclipped delivery, and it is a real one (a network failure or a reshaped `.zattrs` reaches it). Decide then whether degrade-open is still the right side for that case, or whether the partner should be told the tail is unverified. |
| Owner | This repository, for the swallow and the declaration. The producer owns the fact itself. |
| Location | `views_postprocessing/contract/source_metadata.py::last_valid_month_id` (the classification); `views_postprocessing/{unfao,crafd}/managers/*.py::_read_historical_frame` (the two branches). **Not `pyproject.toml`** — the original entry listed it as a risk site on the assumption the dependency was undeclared everywhere; it is the launcher's to declare and both launchers do, so there is nothing to add here. **Cited by symbol, not by line (2026-08-21).** The line numbers went stale twice in four days — both times because a later change in the same branch moved them, and the second time the entry carried an explicit *"re-read"* claim that was false by the time it merged. A citation that decays faster than the review cycle is worse than a vaguer one that does not. |

`source_metadata.last_valid_month_id` lazily imports `datafactory_query.defaults`. Measured 2026-08-16: that package is in neither `pyproject.toml` nor `poetry.lock`, and `import datafactory_query` raises `ModuleNotFoundError` in the project venv. Its only caller wraps the call in `except Exception: lv = None` and then returns the historical frame **unclipped**, logging one WARNING — so "the dependency is missing" and "the producer publishes no boundary attribute" leave through the same branch with the same outcome, and that outcome is unobserved zero-padded months shipping to the partner as observed history. The lazy import states its own reason — *"so this module loads without the heavy datafactory dependency present (e.g. in unit-test environments)"* — but nothing at the call site distinguishes a unit-test environment from a delivery.

**ANSWERED 2026-08-17, and the answer moves the tier.** The question was whether the production launcher supplies `datafactory_query`. It does, twice over:

- views-models `postprocessors/un_fao/requirements.txt` and `postprocessors/un_crafd/requirements.txt` both pin **`views-datafactory>=1.9.0,<2.0.0`**, which is what ships the `datafactory_query` module (there is no separate distribution — `pip download datafactory-query` finds nothing; it is one of nine packages in views-datafactory's wheel).
- More decisively, the postprocessor's `config_queryset.py` imports `datafactory_query.defaults` **at module scope** and raises a `RuntimeError` naming the fix if it is absent. A missing client therefore makes `get_queryset()` return `None`, which `launch_config.assert_queryset_was_importable` turns into a refusal (**C-83**) *before* `_read_historical_frame` is ever reached.

So the scenario this entry was filed on — a missing dependency silently shipping fabricated months on the live path — **cannot occur**. It was already guarded, by a check written for a different reason. The Tier 2 rested on a premise measured only in *this* repository's venv, and the instruction it borrowed from C-26 (*"do not downgrade on inspection of this repo alone"*) was the right instruction: the resolution came from reading the launcher, not from reading here.

**What is genuinely left, and it is why this stays open at Tier 3.** The `except Exception` was never only about the import. A network failure, an auth error, a reshaped `.zattrs`, a timeout — all still leave through one branch, log one WARNING, and deliver the unobserved tail as observed history. That is the recorded C-26 degrade-open decision applied far more broadly than C-26 argued for.

**Partial mitigation, 2026-08-17.** `source_metadata` now raises `ProducerClientUnavailable` instead of letting the import failure fall into the caller's broad `except`, and both managers re-raise it rather than degrading. Defence in depth for the paths `assert_queryset_was_importable` does not cover — a direct caller, a future launcher, a partner not going through the same queryset. The module also gained its first tests (`tests/test_source_metadata.py`, 7, mutation-proven against both the pre-fix return-`None` and a manager that collapses the two branches back into one); it had **none** before, which is how "return None like everything else" ever looked reasonable. The broad degrade-open is deliberately unchanged — narrowing it is a decision about what to tell the partner, not a refactor.

**C-60 is this shape, and it was resolved by deleting the degradation.** There, a provenance stamp reached into the producer's ledger schema inside a bare `except … pass` and returned `"unknown"`; the fix was to raise. The difference here is that the degradation is deliberate and documented ("degrade-open, C-26") — which makes the question *whether the open side is still the right one*, not whether someone forgot.

Cross-refs: **C-26** (the fabrication this clip exists to prevent), **C-07** (undeclared runtime dependencies, the same class, resolved), **C-60** (bare-except degradation, resolved by raising), **C-27** (a swallowed failure surfacing far from its cause), **D-07** (the decision that data facts come from the producer, which created this import).

---

### C-104: A stale virtualenv turns 25 tests red, and 20 of them are the only tests that import either manager

| Field | Value |
|-------|-------|
| ID | C-104 |
| Tier | 3 — no production impact. The cost is that a red suite stops carrying signal, on precisely the two modules with the thinnest coverage. |
| Source | `/repo-assimilation` (2026-08-16), measured |
| Trigger | When `pytest` reports failures in `tests/test_framework_contract.py` or `tests/test_store_construction.py`, check `pip show views-pipeline-core` against `poetry.lock` before reading them as defects. |
| Owner | This repository. |
| Location | `tests/test_framework_contract.py`, `tests/test_store_construction.py` (20 failures); `tests/test_wire_shard.py`, `tests/test_wire_sidecar.py`, `tests/test_hop_b_sink_e2e.py` (5 failures); `poetry.lock` versus the project venv |

Measured 2026-08-16 in the project venv: 458 collected, **433 passed, 25 failed**, 39 xfailed, in 14.85s. The venv holds `views-pipeline-core 2.3.0` and `pyarrow 23.0.1`; `poetry.lock` pins **3.0.1** and **16.1.0**. The pyarrow half is known and predicted: 5 byte-parity failures reporting *"pinned toolchain violated: byte-parity oracle requires pyarrow 16.1.0, found 23.0.1"*, exactly what `tests/fixtures/wire_contract/README.md` says will happen under **C-72**. The pipeline-core half is documented nowhere: `ModuleNotFoundError: No module named 'views_pipeline_core.modules.dataloaders.datafactory_contract'`, raised at import of both managers, which takes out every test that constructs or inspects one.

The consequence is that in a drifted checkout the two largest modules in the package — 387 lines each, 21% of the source — are not merely under-covered but **entirely unexercised**, and the suite reports that in a form indistinguishable from a real break. CI runs `poetry install` and gets the locked versions, so this is a local condition rather than a CI one — **C-81**'s asymmetry running in the other direction, with the laptop the weaker seat rather than the stronger. **C-36** is the precedent for what a suite that is red for a known reason costs: it stops being read.

**Partial mitigation, 2026-08-17.** `tests/test_locked_environment.py` compares the installed versions of the runtime dependencies **declared in `pyproject.toml`** (read from there, not hardcoded) against `poetry.lock`, and fails with one message naming each drifted package, both versions, the command to run, and — the part that matters — that the other failures in the run are consequences rather than defects. Verified against the live drift: it reports `views-pipeline-core installed=2.3.0 locked=3.0.1` and `pyarrow installed=23.0.1 locked=16.1.0`. A second check owns the other direction — declared in `pyproject.toml` but absent from the lock — and the version check *skips* names it cannot find rather than reporting them as `locked=None`, so a stale lock is diagnosed once, correctly, instead of twice with one of the two sending the reader at their virtualenv.

Three things it deliberately does not treat as drift: dependencies gated by `optional`, `python` or `markers` (legitimately absent from a given environment — reporting one as "run `poetry install`" would be advice that cannot work), name spellings that differ only by case or separator (both sides are PEP 503-normalized, so `PyYAML` and `views_frames` match their lock entries), and dev-group tools. The failure text names only the packages that actually drifted: the 2026-08-16 incident was pipeline-core and pyarrow, a future one will not be, and a diagnosis describing the wrong packages is the failure this file exists to remove.

It does **not** fix the drift and does not skip. The 25 failures remain until someone runs `poetry install`; what changes is that a contributor can now tell in one line which kind of problem they have. That is the whole of the entry's cost — the failures were never wrong, they were unreadable — so the entry stays open only until the environment is actually reconciled, which is a machine action rather than engineering work.

Dev-group tools are deliberately out of scope: `ruff`'s reported version varies with how it was installed, and the thing that actually broke CI on 2026-08-03 was its *rule set*, which `pyproject.toml` already pins explicitly.

Cross-refs: **C-72** (owns the pyarrow half — that half is not re-registered here), **C-81** (CI-versus-local coverage asymmetry), **C-36** (a permanently-red suite cannot detect new regressions), **C-102** (the same argument in the other direction: a guard that never runs proves nothing, and a failure nobody can read is not a signal).

---

### C-105: A run is uploaded file-by-file with no rollback and no idempotency — a mid-run failure leaves orphans and the retry adds more

| Field | Value |
|-------|-------|
| ID | C-105 |
| Tier | 3 — no delivered value is corrupted. The store accumulates unreferenced objects that no artifact describes, in a bucket with no named retention owner. |
| Source | `/repo-assimilation` (2026-08-16) |
| Trigger | When the upload interlock is first opened for a live run (`wire_upload_enabled: True`), or when the retention owner D-12 defers is named — whichever comes first — decide what a torn attempt leaves behind and who removes it. |
| Owner | This repository for the mechanism; the operator for retention. |
| Location | `views_postprocessing/contract/wire/sink.py::deliver_run` (the upload phase) and `::_torn_run_error` |

`deliver_run` uploads every shard, then the sidecar, then the run manifest, each through `_ContractStorePort.upload`, which raises on anything but explicit success (**C-79**). A raise at shard *k* of *n* is therefore correct in the one dimension the contract governs — no manifest means the run is invisible to the consumer, which is the §4.2 commit-marker design working — and silent in every other: the *k* uploaded objects remain, nothing records that they exist, and nothing removes them. Re-running the delivery re-uploads all *n* under the same names, and whether that supersedes or duplicates is a store semantic this repository asserts nowhere. At run-0 scale that is roughly 110 objects per attempt.

`docs/operations/correction_procedure.md` covers the *wrong value* case — the contract has no retraction primitive, so a correction is a new complete run, manifest last. A torn attempt is a different case and is not covered by it.

**Partial mitigation, 2026-08-19 — the tear is now documented, not removed.** `deliver_run` keeps an in-memory ledger of what it has uploaded, and a failure anywhere in the upload phase raises `TornRunError` naming the run, how many of how many objects were *confirmed* uploaded, and what is true about the consumer. Tested in `tests/test_torn_run.py` (8), mutation-proven three ways.

**Three corrections `/code-review high` made to the first draft, each of which would have sent an operator the wrong way.** (a) The object that FAILED was omitted, and it is the likeliest orphan of the whole run: `_ContractStorePort.upload` raises precisely when the store returns failure *with the file already uploaded* (the C-79 shape), so the refusal now names it as a separate thing to go and look for. (b) File ids were truncated to five in the message and recorded nowhere else, so at run-0 scale ~104 ids existed only in a string nobody kept — the log ledger now carries `file_id` per upload and is the persistent record. (c) A failure on the *first* upload printed an empty list and a dangling period while telling the operator to audit a bucket. The message also no longer asserts categorically that the consumer cannot see the run: a manifest upload can fail after the store committed the document, and steering a re-run on a false certainty duplicates every object.

The refusal says three things an operator otherwise has to establish by hand: the consumer **cannot see this run** (the manifest is the commit marker and never landed, so nothing partial is being served — §4.2 working as designed); the objects listed are **still there and were NOT removed**; and a re-run will upload all of them again under the same names, with supersede-or-duplicate being a store semantic this repository does not assert.

**Remaining scope, found by `/review-diff` on the fix itself: the historical leg is not covered.** `TornRunError` wraps the upload phase inside `deliver_run`. The historical artifact uploads *after* the wire run is committed, from the manager, so a failure there raises unwrapped — and its consequence is different rather than smaller: the manifest already landed, so the consumer sees a **complete, visible forecast run** sitting next to the *previous* run's historical artifact. Not corrupt (the historical is a full snapshot, so the older one is valid, just one run stale) and the delivery does report failure — but it is the one tear where "the consumer cannot see this run" is false, and the wrapper's message would be wrong if it fired there. It does not fire there. Left uncovered deliberately rather than widening this change; the manager is at 434/450 of its line budget and the fix belongs with whoever takes the deletion decision below.

**What is deliberately NOT done: deletion.** Removing objects from a partner bucket is irreversible and an operator decision rather than a delivery-path one, and the neighbouring delete surface is its own open question (**C-58**, views-pipeline-core #333, blocked on a test key). So this entry stays open: the mess is now legible, and it is still a mess. Closing it needs a decision about who cleans up and whether the store supersedes — neither of which is engineering work here.

Cross-refs: **C-94** (nothing observes the outcome of an upload at the time it happens), **C-79** (the single-file orphan this generalises), **C-58** (the delete surface deletion would have to go through), **D-12** (the unnamed retention owner this compounds with). Part of causal cluster: **Cluster J — Delivery aftercare has no mechanism**.

---

### C-106: The §2 header builder — the module that owns the contract version — is reachable only from tests `[backlog]`

| Field | Value |
|-------|-------|
| ID | C-106 |
| Tier | 4 — unreached, not wrong. Registered because the identical shape has been closed four times here by deletion, and because this instance sits in a module whose *other* export is live on every delivery. |
| Source | `/repo-assimilation` (2026-08-16), measured |
| Trigger | When someone proposes changing `CONTRACT_VERSION`, or when this repository first acts as a Hop-A *producer* rather than only a consumer — at that point `build_header` acquires the caller it was written for and this entry is discharged. |
| Owner | This repository. |
| Location | `views_postprocessing/contract/wire/header.py::build_header`; `views_postprocessing/contract/gaul_schema.py::colrow` |

Measured: `build_header` is called from `tests/test_wire_header.py` and `tests/test_wire_shard.py`, and nowhere else. On the delivery path the sink re-embeds the producer's Hop-A header untouched (`contract/wire/sink.py:111-113`, §10.2 *"the sink mints nothing"*), so the builder never runs in a delivery. The module is half-reached rather than dead: `CONTRACT_VERSION = "1.5"` is imported by `contract/wire/run_manifest.py:19` and written into every run manifest, so deletion is not the question — what `build_header` is *for* is. Separately, `gaul_schema.colrow` has zero callers anywhere, tests and build scripts included. Neither is a defect; both are surface a reader must make a decision about, and neither currently has one recorded.

Cross-refs: **C-100** (the live sibling — a four-method port with three used methods), **C-64**, **C-75**, **C-45** (three prior instances of unreached declared surface, all resolved by deleting).

---

### C-107: The doc-accuracy scan reads markdown only, so a docstring pointing at a moved file rots unwatched — two already have

| Field | Value |
|-------|-------|
| ID | C-107 |
| Tier | 4 — navigational, with no correctness or reliability impact. Registered because this repository's stated discipline is that a docstring points at the one home of a fact, which makes a broken pointer a failure of the discipline rather than a typo. |
| Source | `/repo-assimilation` (2026-08-16), measured |
| Trigger | When the next module moves under `views_postprocessing/`, check its inbound docstring references as well as its markdown ones — or when someone proposes widening `tests/test_doc_accuracy.py`'s corpus, at which point C-97's objection applies and this entry states what the gap actually is. |
| Owner | This repository. |
| Location | `tests/test_doc_accuracy.py:76-78,133-134` (the scanned corpus); `views_postprocessing/delivery/coverage.py:5`; `views_postprocessing/delivery/observed_range.py:6` |

`test_doc_accuracy` scans `README.md`, `docs/architecture/*.md`, package `README.md` files, ADRs and CICs. Python docstrings are outside that corpus. Two are already stale, and both point at files that moved in exactly the refactors whose *markdown* fallout the same test was extended to catch: `delivery/coverage.py` sends the reader to `views_postprocessing/unfao/extraction.py`, deleted in #151, and `delivery/observed_range.py` to `views_postprocessing/unfao/source_metadata.py`, moved to `contract/` in #153.

**This is not a proposal to scan docstrings.** C-97 measured what that costs for the no-copy scan and argued it down under ADR-014 §3 — a guard that fires on ordinary prose gets deleted, after which the real rule is unguarded. The two scans are not the same (a deleted symbol or a repo-relative module path is a far narrower pattern than a store name in a sentence), so the objection is not decisive here — but it is the reason this is registered as a measured gap rather than fixed on sight.

Cross-refs: **C-80** (the same guard, the adjacent corpus gap, resolved by widening), **C-97** (why widening a scan into docstrings is not automatic).

---

### C-108: Two `xfail(strict=True)` deploy gates have never evaluated their own assertions — anywhere

| Field | Value |
|-------|-------|
| ID | C-108 |
| Tier | 4 — no delivery correctness depends on them. Registered because `xfail(strict=True)` *reads* as an armed tripwire, and a future maintainer will believe views-datafactory#223 is being watched when nothing is watching it. |
| Source | `/code-review high` on PR #280, 2026-08-17 (finding 2), extended by measurement |
| Trigger | When views-datafactory#223 is closed, or when anyone cites these gates as evidence that the served artifact is being tracked — check they are not skipping first. |
| Owner | This repository for the gate; views-datafactory for the artifacts. |
| Location | `tests/test_datafactory_deploy_readiness.py` — `TestServedArtifactMatchesBranch::test_assembled_grid_not_older_than_gaul_parquets`, `TestServedArtifactProvenanceTracksGaul::test_provenance_includes_admin_digest` |

Both gates read `data/assembled/grid.npy`, `data/assembled/provenance.json` and the GAUL parquets from the views-datafactory checkout. **None of those is tracked upstream, and `data/assembled/` is empty in the maintainer's own checkout** (measured 2026-08-17). So the tests were failing on a missing file, `xfail(strict=True)` was recording that as an expected failure, and the report read green. The staleness comparison and the `admin_digest` assertion — the things the gates exist to make — have never once been evaluated.

The strict flip is the entire mechanism: when views-datafactory#223 is fixed the test should XPASS and turn the build red, forcing someone to look. A test that can only ever fail on `FileNotFoundError` can never XPASS, so the flip could not fire. ADR-014 §1 — a guarantee is attached to a check, or it is not a guarantee — and C-102's lesson recurring in a form that is harder to see, because here the guard *runs*.

**Partially addressed in the same PR**, and deliberately only partially: both tests now `pytest.skip()` when their inputs are absent, so the state is visible in the report instead of disguised as a passing xfail. That converts a false green into an honest skip. It does **not** make the gate work — closing that needs the assembled artifacts reachable from CI, which is the same blocker as C-46's producer-comparison half and is not this repository's to solve.

Cross-refs: **C-46** (the untracked-artifact blocker these share), **C-102** (a guard that has never run is unproven), **C-36** (the gates' original home).


---

### C-109: Register `Location` line numbers decay faster than the review cycle, and nothing checks them

| Field | Value |
|-------|-------|
| ID | C-109 |
| Tier | 4 — no correctness impact. Registered because `Location` is the field a reader trusts to find the thing an entry describes, and a wrong one sends them to unrelated code with no signal that it is wrong. |
| Source | `/code-review max` on the release branch, 2026-08-21, then measured across the open set |
| Trigger | When an entry's `Location` is used to find code and the code is not there — or when anyone proposes a guard over the register's citations, at which point this entry says what such a guard would have to check and why the obvious version does not work. |
| Owner | This repository. |
| Location | `reports/technical_risk_register.md` — the `Location` field of every open concern that cites a line. |

**Measured 2026-08-21.** Eleven of the 28 open entries cited a `file.py:line` in `Location`; converting four leaves **eight of 29**. Spot-checking six of the original eleven against the working tree, **three were already stale**: C-105's `sink.py:167-171` (written four days earlier) landed on `staging.mkdir`, C-106's `gaul_schema.py:87` on a section comment, and C-30's `unfao.py:397` on `return summary`. All three drifted because a *later change in the same week* moved the lines — nothing about the entries themselves changed.

C-103 is the sharp case, and the reason this is a class rather than three typos: its `Location` went stale **twice in four days**, both times from a subsequent commit in the same branch, and the second time the entry carried an explicit *"line numbers re-read"* claim that was already false when it merged. A citation that decays faster than the review cycle is worse than a vaguer one that does not, because it is confidently wrong.

**Converted rather than corrected, where the target is a function.** C-103, C-105, C-106 and C-30 now cite `path::symbol`. A symbol survives edits above it, which is the entire failure mode here. Line numbers remain where the target genuinely is a line — a specific literal, a table row — and those are the ones any future guard would have to cover.

**Why the obvious guard does not work, stated so it is not proposed again cheaply.** Checking that a file has at least that many lines catches nothing: every stale citation above points at a real line. Checking *content* requires the entry to declare what it expects to find there, which is a second declaration that can itself go stale — the shape ADR-014 §2 warns about. The cheap and durable move is the convention (`::symbol`), not a test.

Cross-refs: **C-103** (twice stale in four days — the case that made this visible), **C-95** (a verdict mis-cited in three places — the same defect in prose rather than in a line number, and the nearest sibling), **C-107** (docstrings outside the doc-accuracy scan; the same "nothing checks the prose" family), **C-82** (governance prose carrying numbers nothing checks, resolved).

---

### C-110: The release path will block itself from 2026-10-18, and nothing tells the person it blocks

| Field | Value |
|-------|-------|
| ID | C-110 |
| Tier | 3 — the ability to ship is interrupted on a known date, but the escape is in-repo and reachable. That is what separates it from **C-86**'s Tier 2, where the only responses are console actions by one person. If the acknowledgement were ever removed, or the tripwire made unconditional, this becomes C-86's tier. |
| Source | `/falsify` release-readiness audit, 2026-08-21 (probe P5) |
| Trigger | A release is cut on or after **2026-10-18**, or anyone reports a red `test` check on `main` they cannot explain — read `tests/test_credential_expiry.py` before diagnosing anything else. |
| Owner | This repository for the documentation; the operator for the rotation that removes the cause. |
| Location | `tests/test_credential_expiry.py::test_the_platform_keys_are_not_about_to_expire`; the `protect_main` ruleset; `docs/operations/` (where the runbook that would say this does not exist). |

Measured 2026-08-21 against the live ruleset: `protect_main` is **active**, the `test` job is a **required status check**, and `bypass_actors` is **empty** — C-86's finding, re-confirmed. `test_credential_expiry` fails from 30 days before the 2026-11-17 expiry, i.e. **2026-10-18**. From that date the required check is red, so no pull request merges to `main` and no release can be tagged.

**This entry exists because it falls between two records and is in neither.** C-84 registers the expiry and the tripwire and does not mention the release path or required checks. C-86 registers that a red build cannot be bypassed and does not mention the tripwire. The interaction — *the guard we added will redden the check that cannot be bypassed, on a date we chose* — is the product of the two, and was not noticed when the tripwire was added four days earlier. The ruleset was never queried at the time; the audit queried it.

**The escape is real and was verified, which is why this is Tier 3.** A pull request that sets `ACKNOWLEDGED_UNTIL` is green on its own branch (measured: `1 failed` → `6 passed`), so the block is not a trap and the fix is not gated behind the thing it fixes. What is missing is that **nothing tells a releaser any of this**. There is no release runbook in `docs/operations/`, and the failure message names `ACKNOWLEDGED_UNTIL` without saying that a release is what it is blocking.

**Closing this is documentation, not code.** Either a release runbook that names the interaction, or a cross-reference in C-84 and C-86 so that whoever reads one meets the other.

Cross-refs: **C-84** (the expiry and the tripwire), **C-86** (no way past a red build; zero bypass actors), **C-81** (what actually gates `main`).

---

### C-111: A release can change whether a delivery fails, and the version number is the only thing that says so

| Field | Value |
|-------|-------|
| ID | C-111 |
| Tier | 3 — nothing is silent and nothing corrupts; the cost lands on a consumer who takes a version that changes their pipeline's outcome with no notice, and on whoever then diagnoses it across two repositories. |
| Source | `/falsify` release-readiness audit, 2026-08-21 (discovered during execution, not predicted) |
| Trigger | The next version is cut — write what changed for a consumer, or record why the number alone is enough. |
| Owner | This repository. |
| Location | The repository root — there is no `CHANGELOG.md`, no `docs/operations/release_notes.md`, and no release notes on the existing tags. |

The delta since tag `1.1.1` adds three exception types that can escape into a launcher: `delivery.findability.DeliveryNotFindableError` and `FindabilityUnverifiedError` (C-94), and `contract.source_metadata.ProducerClientUnavailable` (C-103). The first is the sharp one — **a delivery whose artifacts land somewhere the consumer cannot see previously succeeded silently and now raises.**

That is the intended behaviour and the entire point of C-94. It is still a change a consumer must be told about, and the only signal views-models receives is a MINOR version bump in `VIEWS_POSTPROCESSING_PIN`. Nothing in this repository states that a previously-passing run can now fail.

**The asymmetry is the finding.** This repository is unusually careful about telling *contributors* things — a register, ADRs, CICs, guards that refuse with paragraph-long explanations. It tells *consumers* nothing but an integer. views-models#403 is the shape of the consequence in the other direction: launchers sat on `1.1.0` for eight days after `1.1.1` fixed a defect that had already killed a delivery, because nothing made the difference legible.

**Deliberately not proposed: a full changelog discipline.** What is needed is a line per release naming behaviour a consumer can observe. Whether that lives in `CHANGELOG.md`, in the GitHub release body, or in the pre-release notes FAO already receives is a choice, not a requirement.

Cross-refs: **C-94** and **C-103** (the new failure modes), **C-112** (the inbound half — nothing checks whether a consumer took the release either; the two compound), **views-models#403** (the same gap costing eight days in the other direction), **C-24** (a consumer-facing contract divergence nobody surfaced).

---

### C-112: Nothing here can see what production actually runs, and it ran a defect we had already fixed for eight days

| Field | Value |
|-------|-------|
| ID | C-112 |
| Tier | 3 — nothing is silent: the defect that made this visible failed loudly and killed a delivery. What is missing is any signal about **version lag**, so work landing here does not reach production and no one on this side can tell. Coordination cost, not corruption. |
| Source | Cross-repo issue sweep, 2026-08-21 — prompted by the question *"have you checked all gh issues related to this repo?"*, which had not been done in this repository at all |
| Trigger | A release is cut here, **or** a delivery fails in a way this repository has already fixed — before diagnosing, read what `views-models`' launchers pin. If it is behind the newest tag, that is the first hypothesis, not the last. |
| Owner | This repository for the visibility; views-models for the pin itself. |
| Location | No file — that is the finding. `views-models` `postprocessors/{un_fao,un_crafd}/run.sh` hold `VIEWS_POSTPROCESSING_PIN`, and nothing in this repository reads them. |

**Measured 2026-08-21.** Both launchers pin **1.1.0**. This repository's newest tag is **1.1.1**, published eight days earlier, and 1.1.0 carries the `_ContractStorePort.download` fail-open — register **C-99**, the defect that killed the first `un_crafd` delivery attempt on 2026-08-13. So production has been running a known-defective build of this package, on the FAO leg as well as CRAF'd, for over a week, and **nothing on this side could see it**. views-models#403 was filed for it and is open.

At the same time, `main` carries **29 commits since 1.1.1** — every guard from this week's work, including the C-94 findability preflight and the C-105 torn-run ledger. None of it is in production either.

**Two gaps, one shape: this repository cannot see the distance between what it declares and what anyone runs.** It does not know what consumers pin, and nothing compares its declared version against what is published. `tests/test_release_version.py` compares `pyproject` to the git tag — both facts *inside this repository* — which is why a version bump that is never tagged, or a tag no consumer ever takes, is invisible to it.

**Why this is not C-111.** That entry is the outbound half — we change delivery behaviour and tell consumers nothing but an integer. This is the inbound half — we do not look at whether they took it. They compound: 1.1.1 fixed a delivery-killing defect, nothing announced it, and nothing checked whether it landed.

**The obvious fix has a known cost, and it is already registered.** CI checks out sibling repositories so cross-repo assertions run (ADR-016); views-models is not among them. Adding it, plus a check that the launchers' pin is not behind the newest tag, would be the same shape as the existing drift checks. It would also add a fifth repository whose `main` can redden this build — **C-86**, no bypass actors. That trade is a decision, not a cleanup, which is why nothing is proposed here.

**The wider observation, recorded once so it is not rediscovered.** Eighty-four open issues across the organisation mention `views-postprocessing`; this repository tracks none of them and had never been swept. Most are informational, several were filed *by* this seat, and a few carry live asks (views-faoapi#390, views-crafdapi#55, views-models#362). No mechanism is proposed for that either — but a sweep belongs in the next repo-assimilation rather than being found by accident at the end of a sprint.

Cross-refs: **C-111** (the outbound half), **C-99** (the defect production is still running), **C-86** (the cost of adding another sibling to CI), **C-81** (what actually gates `main`), views-models#403.

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

**Adjudication: B — but conditionally, and the condition is now named.** B is only correct *if the legacy forecast branch is actually deleted*. It had no scheduled deletion PR when this was adjudicated — #149 deleted it on 2026-07-31, which is what made B correct rather than merely preferable — only a "named post-run-0 follow-up" (C-40). If it lingers, three-way duplication becomes the permanent shape and Position A wins retroactively. **Re-open trigger: if the legacy forecast branch still exists when #89 (numpy/pyarrow keyed gather) lands, unify all three consumers onto one fail-loud gather primitive as part of that story rather than deferring again.** Cross-refs C-59 (the duplicate-key hazard that lands differently in each of the three), C-40, #89.

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

### C-102: A guard that has never run is unproven, however carefully it was written — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-102 |
| Tier | 4 — caught before it ran anywhere, so nothing was affected. Registered for the shape, which this repository keeps rediscovering. |
| Source | `/code-review medium` on PR #275, 2026-08-15 |
| Trigger | *(closed)* Any dormant check being switched on — a skipped test made live, a gate moved from advisory to required, a guard whose environment finally satisfies its precondition. |
| Location | `tests/test_release_version.py` (`test_the_newest_release_tag_is_not_ahead_of_the_declared_version`); `.github/workflows/run_pytest.yml` |

`tests/test_release_version.py` was written on 2026-08-13 after tag `1.1.0` was cut while `pyproject.toml` still said `1.0.0`. It was correct, mutation-proven, and **had never executed anywhere except a maintainer's laptop**: CI checked out with no `fetch-depth`, so no tags were fetched and both of its tests skipped. Verified in a real CI log — run `31844578627` shows `tests/test_release_version.py ss`.

PR #275 made it live by fetching tags. Review then found that switching it on would have **broken honest branches on its first day**: the check read `git tag -l`, which lists tags on every branch, so it asked *"has a release been cut anywhere"* rather than *"has one been cut from this line of history without the bump"*. With `1.1.1` tagged on the release line, a branch still declaring `1.1.0` — a long-lived feature branch, a hotfix cut from `1.1.0` — fails with *"the newest release tag is 1.1.1 but pyproject.toml declares 1.1.0"*, having done nothing wrong.

Reproduced in a clone before changing anything: tags anywhere `1.0.0 1.1.0 1.1.1`, tags reachable from the honest branch `1.0.0 1.1.0`, old check fails, `git tag --merged HEAD` passes — while on the tagged line both guards still bite when `pyproject.toml` is set back.

**The lesson is not about tags.** Mutation-proving establishes that a guard *can* fail; it says nothing about whether the guard has ever been *asked*. This one's logic was fine in the only environment it had run in, and its defect lived entirely in the environment it had never seen. ADR-014 §2 requires a guard to be mutation-proven; this entry adds that a guard which has only ever run in one environment is proven in one environment. C-98 is the same family from the other side — a guard that ran, but watched a proxy.

**Fixed in the same change**, and the check now asks about reachable history. ADR-014 §3 was the deciding rule: a guard that reddens honest work is one someone deletes, so a false negative is the better failure.

Cross-refs: **C-98** (a guard measuring a proxy), **C-89**, **C-90**, **C-93** (guards that could not fail), ADR-014 §2 and §3.

---

### C-101: Assembling a target held three copies of it — measured, then bounded — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-101 |
| Tier | 2 — no incorrect output, but the forecast leg needed roughly three times the memory its product occupies, and the failure mode is an OOM kill mid-delivery rather than a refusal. |
| Source | views-postprocessing#269, filed from the views-crafdapi seat 2026-08-14 after the first `un_crafd` delivery attempt |
| Trigger | *(closed)* Any run large enough that three copies of one target's frame did not fit — which on 2026-08-13 meant a machine with 15 GB already in use. |
| Location | `views_postprocessing/contract/track_a_source.py` (`frames_for_target`); `views_postprocessing/contract/wire/source_selection.py` (`TargetLease.load`) |

**Measured before anything was changed**, because the issue's own diagnosis named one cause and there turned out to be three. A synthetic run through the real `TargetLease.load` — producer-format `.tap.zip` shards, real `read_shard`, `tracemalloc` and peak RSS agreeing to within 2% — at 36 shards x 20,000 cells x 200 samples:

| | before | after |
|---|---|---|
| peak, tracemalloc | **3.06x** the delivered frame | **1.13x** |
| peak, RSS delta | 3.02x | 1.06x |

The 3x was **three roughly equal thirds**, and the issue named only the first:

1. every shard's bytes, resident together — the dict comprehension completed before the first shard was decoded;
2. every decoded per-shard frame, held for the stack;
3. the `np.concatenate` result, allocated while (2) was still alive.

The ratio held at 12 and 36 shards, so it is the shape and not the scale. Fixing only (1), as the issue proposed, would have taken 3.06x to about 2x.

**The fix is one loop.** `frames_for_target` now takes `fetch_shard_bytes(name)` instead of a filled dict, drops each shard's bytes the moment they are decoded, and writes each shard into a manifest-sized buffer instead of stacking and concatenating. Peak is now the finished frame plus a **fixed overhead of roughly 4.5 shard-widths** — the raw shard, its decoded array, and the intermediate copies `read_shard` makes unzipping and `np.load`-ing it. Because that overhead is constant while the frame grows with the shard count, the *ratio* falls as 1/n: measured 1.36x at 12 shards, 1.19x at 24, 1.13x at 36, with the absolute overhead steady at about 70 MB throughout. *(An earlier draft of this entry called the residual `2/n_shards`; review pointed out that fits none of its own numbers — 2/12 is 0.17 against a measured 0.36. Re-measured at three shard counts to get the constant above.)*

*What makes the buffer safe.* Its slots are sized from `expected_cell_count`, a declaration this function already enforced per shard, and the enforcement runs **before** anything is written — so a shard whose row count disagrees is refused rather than straddling two months' slots.

*What proves the product did not change — corrected, because the first answer was wrong.* This entry originally cited `tests/test_wire_fixture.py`. **That file does not reference the assembly at all**: it round-trips static artifacts against checked-in bytes and never calls `frames_for_target` or `TargetLease.load`. The real end-to-end proof is `tests/test_hop_b_sink_e2e.py::test_e2e_byte_parity_with_the_fixture`, which drives the whole inbound chain and compares delivered bytes to the golden fixture — but **its fixture has one shard**, so `position * expected_cell_count` never ran with a position above zero.

The core of the rewrite was therefore unverified, and the interleaving guard could not have caught it either: its three shards are byte-identical copies, so any ordering bug would survive. `test_a_multi_shard_run_assembles_in_manifest_order_with_every_row_written` now assembles three shards with distinct values, months and units and asserts the result equals `np.concatenate` in manifest order. Mutation-proven three ways: reversing the slot index, an off-by-one in `stop`, and leaving the identifiers unwritten all fail it.

**At production scale.** 64,742 cells x 36 months, at ADR-013 **§0**'s *"~1000 samples per cell"* — the sample count is the one input here taken from the contract rather than measured — one target's frame is **8.68 GB**, so peak fell from about **26.6 GB to 9.8 GB per target**, roughly **16.8 GB** saved. For scale, run-0's OOM kill recorded `anon-rss:23778224kB` (#126); that incident's root cause was pandas on the *historical* leg and is not this, but the magnitude says this leg alone would have exhausted the same box.

**The manager's historical frame is not the elephant, so it is not being chased.** #269 notes `_historical_frame` is held from `_read` through `_save`. By its own declared dimensions — 64,742 cells x 438 months = 28,356,996 rows — that is about **108 MB** at one float32 column, **1.2%** of a single forecast target frame. **Filed as #273**, carrying the measurement so it cannot be picked up under the impression that it is comparable — and because #269 listed *"the historical frame is released, or not held"* as an acceptance criterion of its own, which this change does not meet. Closing #269 while quietly leaving that unmet was the alternative, and it is not one.

*One refusal added, because the fix moved a constraint.* The buffer's width is fixed by the first shard, so a run whose shards disagree on draws per cell is now this function's constraint rather than an incidental one. Left to the assignment it surfaced as `could not broadcast input array from shape (6,2) into shape (6,4)` — no shard named, no mention of draws. The stacking it replaced was no better, only wordier. It now refuses in its own words, mutation-proven by deleting the check and watching the bare numpy error return.

*Guarded.* `tests/test_track_a_source.py::test_shards_are_fetched_one_at_a_time_not_all_up_front` asserts the fetch/decode interleaving rather than a byte count — a memory threshold in a test is a flake on a busy machine, while "fetch, decode, fetch, decode" is exactly the property that bounds the peak. Mutation-proven: restoring the up-front dict produces `['fetch','fetch','fetch','decode','decode','decode']` and it fails.

Cross-refs: **C-99** (the other defect the same delivery attempt found), **C-75** (the pandas retirement that #126 landed on the historical leg), views-postprocessing#269, views-postprocessing#126.

---

### C-99: `_ContractStorePort.download` failed open where `upload` refuses — C-79's untreated sibling — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-99 |
| Tier | 2 — no silent corruption, but an unreadable failure on the live FAO delivery leg, in the one place that knows which file it was. |
| Source | views-postprocessing#268, filed from the views-crafdapi seat 2026-08-14 after the first `un_crafd` delivery attempt |
| Trigger | *(closed)* Any failed download — a yanked file, an expired key, a rate limit, a network blip — on either partner's contract path. |
| Location | `views_postprocessing/{unfao,crafd}/store_port.py` (`download`); previously `managers/{unfao,crafd}.py:38-41` |

`download` chained `.get()` onto an unvalidated store result:

```python
self._dsm.download_prediction(file_id).to_dict().get("data", {}).get("file_bytes", None)
```

When `data` is **present and null**, the `{}` default never applies and the next `.get` raises `AttributeError: 'NoneType' object has no attribute 'get'` — from inside a dict comprehension over pinned ids in `TargetLease.load`, three frames from the port, naming neither the `file_id` nor the fact that a download had failed. views-crafdapi spent an evening ruling out an OOM kill (there was one in `dmesg`, three minutes later, on a different pid) before finding it.

**It was C-79 with the method name changed.** C-79 fixed exactly this polarity on `upload`, in the same class, on 2026-08-05, and recorded the specification in its own resolution note: *"an unrecognised result should be refused and named, not adapted to silently."* That note was never applied a second time. Nine days later the untreated method cost another repo an evening.

*Why nothing caught it.* `tests/test_store_port.py` was written for C-79 with five parametrised tests across both partners, including `test_an_unrecognised_result_is_refused_rather_than_assumed_good`. It mentioned `download` **zero times**. And `contract/store_metadata.py` already wrote `.get("data", {}) or {}` — the guard `download` lacked, one file away, unapplied.

**Fixed 2026-08-14.** `download` now refuses anything that is not non-empty bytes, naming the `file_id`, that a *download* failed, and the types it actually got. Empty bytes are refused with the rest: no shard, sidecar or manifest is ever zero-length, so `b""` is a failed download wearing a valid type. Byte-identical in both partners, as C-79 chose for `upload` (C-33). Mutation-proven on three mutants — restoring the original one-liner fails 18 of the module's tests, accepting empty bytes fails exactly 2, dropping the `file_id` from the message fails exactly 2.

**It also moved.** The refusal pushed `managers/` to 469 lines against epic #148's 450 bound, and that guard's instruction is to move something out rather than raise the number. `_ContractStorePort` is not the manager, so it went to `{partner}/store_port.py` — 388 lines now, 62 of headroom. The port stopped naming `DatastoreModule` in its constructor on the way: a DIP seam whose stated purpose is that nothing downstream sees the client's types should not name one, and a new module that mentioned `views_pipeline_core` would have widened C-40's blast radius past the two files `test_views_pipeline_core_is_confined_to_the_partner_managers` pins.

**Amendment, same day — the move was right and the way it was reported was not.** The first version of this change moved `_ContractStorePort` out of `managers/` and recorded "388 lines, 62 of headroom" as though the budget had been satisfied. Review measured what actually happened: the counted number fell from **441 to 388** while each partner package grew from **441 to 488**. The guard counts `managers/`, and the code moved to a sibling *of* `managers/`, so 47 lines left the budget's view rather than the codebase.

The budget's own docstring had already named this failure — *"an 800-line helper module beside a 406-line manager was previously unbudgeted, which is the same regrowth wearing a different filename"* — and had closed it one level in. The evasion simply happened one level out. This is C-98's shape again: a guard that watches a proxy reports on the proxy, and the number it prints is true and irrelevant.

`test_the_partner_package_stays_within_its_line_budget` now bounds the whole partner package at 700 (measured 2026-08-14: unfao 626, crafd 635), mutation-proven by dropping a 200-line module beside the manager — the exact evasion — and watching it fire. The extraction itself stands: a store adapter is not the manager, and the inner budget's instruction is to move something out.

Cross-refs: **C-79** (the same defect on `upload`, resolved), **C-100** (the dead fourth method, found while reading this one), **C-33**, **C-40**.

---

### C-27: Loader construction failures swallowed — surface as remote AttributeError — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-27 |
| Tier | 2 — structural fragility: any dependency or config breakage is converted into a misleading crash far from its cause |
| Source | `expert-code-review` (2026-06-12) |
| Trigger | When bumping views-pipeline-core, or changing this postprocessor's queryset/config — verify a `ViewsDataLoader` construction failure surfaces its real exception rather than a downstream `AttributeError`; today it is caught bare, logged as "No Queryset detected" with `exc_info=False`, and replaced with `self._data_loader = None` |
| Location | views-pipeline-core `managers/model/model.py` (`_initialize_data_loader`); crash sites `views_postprocessing/unfao/managers/unfao.py::_read_historical_frame` and `::_read_historical_data`. Function names, not line numbers — the cited `:105`/`:134` had already moved to `:183`/`:207`. |

**RESOLVED 2026-08-13 — fixed upstream, and this repository was installing the version without the fix.**

views-pipeline-core#367 landed in **3.0.1** (released 2026-08-11): `managers/model/model.py` now logs with `exc_info=True` and **re-raises**, with a comment naming this repository's `AttributeError` as the symptom it produced.

`pyproject.toml` already allowed it (`>=3.0.0,<4.0.0`), but `poetry.lock` still resolved **3.0.0** — so CI installed the unfixed version for two days after the fix shipped. Bumped with `poetry update views-pipeline-core --lock`: exactly one package moved in the lockfile, and nothing else — `Requires-Dist` is identical between the two releases, so no sub-dependency changed.

**The local suite does not verify this, and saying it did would be the defect this pass exists to remove.** This machine resolves `views_pipeline_core` to an editable checkout, not to either release, so the 422 passed proves nothing about 3.0.1. **CI is the only real test** — it runs `poetry install` and takes what the lock says. Note also that a patch bump is not a small payload here: 3.0.1 changes ~20 files and splits a module (their #431). Nothing this repository imports moved, which is the check that matters.

*Verification note, because the obvious check is misleading:* `grep -c "exc_info=True"` returns **6 in both tags**. The fix is identifiable only by the comment naming #367 — present in 3.0.1, absent in 3.0.0. A count that looks decisive and is not.

**What this leaves.** The trigger stands as written for the next bump: a version constraint that permits a fix is not the same as a lockfile that installs it, and nothing here compares the two. That is a general gap, not this entry's — noted rather than built.

**Filed upstream 2026-08-01 as views-pipeline-core#367**, cross-referenced to their **#168** (views-pipeline-core C-166, narrow Appwrite exception handling) as the same defect class on a different call path — catch broadly, guess at the cause, discard the evidence — worth deciding once rather than twice.

`_initialize_data_loader()` catches bare `Exception`, discards the traceback, and nulls the loader. The failure then surfaces as `AttributeError: 'NoneType' object has no attribute 'get_data'` in `_read_historical_data` — the operator debugs the postprocessor while the cause (import error, malformed config, path issue) was erased at construction time. Cost is time-to-diagnosis during exactly the runs where time matters.

---

---

### C-91: The git plumbing this arc added turns ordinary developer states into hard errors, bare tracebacks, and one possible hang — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-91 |
| Tier | 3 — no wrong data and nothing silent. It taxes every contributor who does not already have the exact sibling checkout this repository assumes, and it does so with diagnoses that point at the wrong cause. |
| Source | `/code-review max` on PR #239 post-merge, 2026-08-11 |
| Trigger | Any of: a contributor clones views-appwrite shallow, single-branch, or before the pinned commit; a table classified `CONSUMED` upstream is written as flat keys rather than sub-tables; a contributor has `commit.gpgsign` or a global `core.hooksPath` set. |
| Owner | This repository. |
| Location | `tests/seam_registry.py:71` (refusal diagnoses), `:150` (`rows`), `tests/test_env_declaration.py:820` (the scratch repo). |

**A stale clone produces four errors carrying the wrong explanation.** The reader the extraction replaced read the file off disk, so an older checkout simply read an older file. Now a clone that predates the pinned commit — or is shallow, or was made `--single-branch`, which matters because views-appwrite's default branch is not `main` — raises *"does not resolve to a commit … an empty ref reads the index and a branch reads a moving tip"*. That names neither cause and does not say `git fetch`. Meanwhile `test_the_pinned_commit_is_reachable_from_the_contract_repos_main` detects the identical root cause and *skips* with the right remedy. One condition, one skip, four errors, three explanations.

**`rows()` raises a bare `AttributeError` on a shape the live registry already has.** It guards a null section and not a scalar row. Verified: views-appwrite's `[test_environment]` holds `status` and `fact` as top-level strings. That table is `IGNORED`, so nothing breaks today — but when the partition check fires on a new upstream table, its own message instructs the maintainer to classify it `CONSUMED` or `MIRRORED`, and doing so for a table written that way returns a traceback pointing into a dict comprehension. From the module whose docstring says a helper justified by failing legibly must not hand back a bare traceback.

**The scratch repo inherits the developer's global git config and has no timeout.** `test_the_pinned_reader_refuses_every_way_a_baseline_can_be_wrong` sets `user.name` and `user.email` and stops. With `commit.gpgsign = true` it fails with a bare `CalledProcessError` — `capture_output=True` swallows git's explanation. With a passphrase-protected key it blocks on pinentry with no `timeout`, hanging the whole run; `conftest.git_output`, which this helper bypasses, caps at 30 seconds. The leak was anticipated for identity and not for the setting that blocks.

**RESOLVED 2026-08-12 (#247) — all three.**

**One condition, one diagnosis.** A ref this clone cannot see and a ref that is not a frozen commit used to share a message that named neither cause and never said `git fetch`. They are now separate branches with separate remedies, and a third — an empty pin — is called what it is: a defect in the pin, not the checkout. The bogus-sha case is deliberately classified as *"this clone cannot see it"*, because that is the truth: the reader cannot tell a bad pin from a missing fetch, and the message says so rather than guessing.

**`rows()` refuses a scalar row by name.** `[test_environment]` on the live registry is top-level strings; classifying such a table CONSUMED — which the partition check's own remediation message invites — used to return an `AttributeError` from a dict comprehension, in the module whose justification is failing legibly.

**The scratch repositories are hermetic.** All three now run git with `-c commit.gpgsign=false -c core.hooksPath=/dev/null` and an explicit timeout. Verified by running the suite under a `HOME` whose `.gitconfig` sets `commit.gpgsign = true` and points `core.hooksPath` at a nonexistent directory: four tests pass where they would previously have failed opaquely or blocked on pinentry with no timeout.

Mutation-proven three ways, each reverted: removing the scalar-row refusal, the missing-object branch, and the empty-pin branch.

Cross-refs: **C-90** (the same module's untested core), **C-88** (why the module exists outside `conftest.py`), ADR-008 (explicit failure), issue #196.

---

---

### C-90: A mutation proof that cannot fail, and the untested function a module was extracted to create — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-90 |
| Tier | 2 — this is the entry PR #239 was written to close, reopened by the code that closed it. It reinstates release-blocking false alarms on the path that is this project's production release, and it does so under a docstring saying the opposite. |
| Source | `/code-review max` on PR #239 post-merge, 2026-08-11; verified by direct measurement against views-appwrite `origin/main` |
| Trigger | **Both remaining halves are proof defects, not runtime ones.** (a) Someone mutates `_unclassified_tables` or `_TABLE_ROLE` and believes the tautological proof covers it. (b) Someone changes `registry_current` — the reason `tests/seam_registry.py` exists — and the suite stays green. *(The original trigger, an unrelated coordinate arriving upstream, died with `arrived` in #245.)* |
| Owner | This repository. |
| Location | `tests/test_env_declaration.py` — `test_the_table_partition_would_catch_a_new_table_and_a_vanished_one` (the tautology); `tests/seam_registry.py::registry_current` (untested). Function names, not line numbers: this entry has cited stale ones before. |

**~~`arrived` is not filtered by the names this package reads.~~ RESOLVED 2026-08-12 (#245) — deleted; see the mitigation below. Left visible because the reasoning it prompted is the entry's most useful part.** `changed` is; `arrived` is computed over every row of every table this package depends on. Measured on the live registry: **25 rows, 8 of which this package never reads** — six of them keys and callers belonging to other repositories. So views-appwrite issuing one more key for an unrelated repo turns both partner parametrizations red here, with a message demanding a `SEAM_CONTRACT` re-pin for a coordinate this package cannot use.

That is the exact failure class C-86 records and that PR #239 was written to remove, and the same test's docstring seven lines above says **"Silent through: prose edits, `[meta]` bumps, and rows belonging to anyone else."** The prose describes the check that was designed; the code implements a wider one.

There is a real question underneath, and it should be decided rather than inherited: a *new* coordinate in a table we read may be one we must adopt. That argues for table-granularity on arrival and row-granularity on change. **They cannot both stand.**

**DECIDED 2026-08-12 (#245): the docstring won, and the cost is real.** The arrival half was deleted. A coordinate views-appwrite issues *for this package* — or a second `[contract.*]` row for a future partner such as views-productionapi — is now **silent** until a human reads the registry: no test, no run-time assert, nothing. `assert_env_declared` cannot see it, because it iterates the names this package already declares. That is the accepted price of not being reddened by every unrelated row, and it is recorded here rather than left to be discovered. *(The half's own defence — that `[contract.*]` "arrived exactly this way and nothing else here would have seen it" — was false at table granularity, where the partition check catches it, and true at row granularity, which is exactly the cost now accepted.)*

**The partition's mutation proof cannot fail.** `assert not _unclassified_tables(base)` where `base = {name: {} for name in _TABLE_ROLE}` reduces to `set(_TABLE_ROLE) - set(_TABLE_ROLE)`, empty for every possible input. Its message — *"the real registry's tables must all classify"* — asserts a fact about a file this test never opens. It is decoration inside the test whose own docstring is about removing decoration.

**`registry_current` has no test.** The module `tests/seam_registry.py` was extracted for one reason: two copies of the reader disagreed about whether to read the sibling's `main` or its working tree, and reading the working tree is issue #196 verbatim. The function that settles it is called by five tests and is the subject of none. Replacing its body with `rev-parse HEAD` — the defect it exists to prevent — leaves the suite at its exact baseline. Three of its error branches are executed by nothing.

**Partial mitigation 2026-08-12 (#245) — the false-alarm half is gone; the two proof defects are not.**

`arrived` is **deleted**. Measured before deleting: each partner reads 13 of the 25 rows in the tables this package depends on, and 8 of those rows belong to no repository here — so the check subscribed this repository to another repo's changelog. Mutation-proven after: an unrelated API key and a third partner's contract row are silent; a rotation and a removal still fire. The docstring and the code now agree, and the stopping rule sits above the check.

**RESOLVED 2026-08-12 (#246) — both proof defects closed.**

The tautology is gone. `assert not _unclassified_tables(base)` where `base` was built from `_TABLE_ROLE` reduced to `set(x) - set(x)`, empty for every possible input, while claiming *"the real registry's tables must all classify"* about a file the test never opens. The silent direction is now asserted against an input the function did not derive from itself, and mutation-proven by making `_unclassified_tables` report everything.

`registry_current` has tests — three of them, plus two for `registry_at`'s refusal branches that nothing reached. The scratch repository differs on `main`, on `origin/main` and on disk, so preferring the wrong one is visible. Mutation-proven four ways: reading `HEAD` (issue #196's defect, which used to leave the suite green), preferring `main` over `origin/main`, dropping the unreadable-blob refusal, and dropping the TOML-parse wrapper. All four now fail.

The scratch repository also runs git with `-c commit.gpgsign=false -c core.hooksPath=/dev/null`, which is C-91's third item arriving early: a contributor's global signing config would otherwise fail opaquely or block on pinentry with no timeout.

Cross-refs: **C-86** (whose partial-mitigation paragraph this falsifies), **C-89** (the sibling defect in the no-copy scan), **C-93**, **C-91**, ADR-014 §1/§2, issue #196.

---

---

### C-93: A mutation proof written by whoever wrote the guard tests that author's imagination, not the guard — RESOLVED

| Field | Value |
|-------|-------|
| ID | C-93 |
| Tier | 3 — no defect of its own. It is the reason several of the defects below survived three reviews, and it changes what "mutation-proven" is allowed to mean in this codebase. |
| Source | `/code-review max` on PR #239 post-merge, 2026-08-11, corroborated by measurement |
| Trigger | The next time a guard is defended in a pull-request description as "mutation-proven" against a list of cases the same change authored. |
| Owner | Whoever writes the next guard; the standard belongs in ADR-014 §2. |
| Location | ADR-014 §2; `tests/test_env_declaration.py::test_no_coordinate_value_is_copied_into_this_repo`; every `_MUTANTS`-style proof in `tests/`. |

ADR-014 §2 says a guard is mutation-proven or it is decoration. That is right, and it is not sufficient. **A mutation proof is only as good as the mutant list, and a mutant list written by the author of the guard covers the cases the author already had in mind — which are, by construction, the cases the guard already handles.**

Measured, on the guard that protects a public repository from publishing a coordinate value. Its author (this assistant) proposed thirteen input forms, proved all thirteen caught, and wrote that result into C-57 and into a commit message. An independent review then proposed twenty-nine forms. **Fifteen missed.** The thirteen were not a sample of how people write markdown; they were a sample of what the author had thought of, and every one of them happened to share the property the guard depended on.

This is not the same as ADR-014 §2 failing. The proof was real, it was executed, and every case in it genuinely passed. The gap is that "proven against N mutations" reads as a statement about the guard when it is a statement about N.

**RESOLVED 2026-08-12 (#250) — ADR-014 §2 amended.**

The rule landed is a **diagnostic**, not a process: *if a guard can only be proven against inputs you invented, that is the signal the guard is on the wrong side of a boundary — it is verifying a fact you do not own.* Prefer moving the check to where the fact lives, or anchoring the mutant list in something real — this repository's corpus, the registry's rows, an observable outcome. The no-copy scan's stopping rule is the worked example and shipped in #243.

Two cheap obligations where that is impossible: the mutant list is a declared artifact in the test file, not a paragraph in a pull request; and a proof must be able to fail.

**Deliberately not adopted:** requiring an independent mutant author for every guard. The friction would exceed the disease for a single maintainer. Independent mutants are worth buying only for the silent-failure class — a leak, an invisible delivery — and the arc that produced this entry is the evidence for both halves: five parallel reviewers found what four rounds of self-review had not, and that cost was proportionate exactly once.

Cross-refs: **C-57** and **C-89** (the guard this was measured on), **C-90** (a proof that proved nothing at all), ADR-014 §2.

---

---

### C-82: Governance-artifact prose carries numbers and statuses that nothing checks — RESOLVED 2026-08-05

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

**Self-contradiction elsewhere.** Four were named: Cluster I arguing for a `tests/test_register_integrity.py` that already existed with ten green tests; Cluster J naming closed issue **#15** as its fix strategy; D-11 saying a branch *"currently has no scheduled deletion PR"* two paragraphs after recording its deletion; D-09's `Status` row reading *"Open … after delivery"* above prose recording the deferral expired.

Three were already corrected by the passes that followed, and only **D-11** survived to this one — measured, not assumed: each was grepped for on 2026-08-05 and Clusters I and J and D-09 returned zero hits. That matters more than the count. The instances got fixed one at a time by whoever tripped over them, which is exactly the failure mode this entry describes: **the register self-heals where someone happens to look and rots everywhere else.** D-11 sat contradicting itself for five days in a section nobody had cause to re-read.

**Numbers, and this entry's own numbers rotted while it sat open.** It read: *"the count appears as 26 twice and as 18 twice more; the actual is 24."* Since then #90 added a test and the actual became 25, so the entry describing stale counts had a stale count. That is not irony worth savouring — it is the argument. **A count nothing checks is a claim with a half-life**, and the fix is not a more careful re-count.

Resolved by removing the volatile numbers rather than correcting them, which is the precedent C-33 was forced into after its measurement was wrong five times: publish the **command**, not the result. `40 permanent guard tests` became the collect-only command; the fidelity count became *"one file discharged three entries"*, which is the claim that mattered and does not move. Historical counts inside dated closure records are left alone — *"18 tests, committed in #141"* was true at #141 and is a record, not a claim about now.

**CIC front matter.** `GaulLookupEnricher.md` said *Last reviewed 2026-06-18* and `UNFAOPostProcessorManager.md` *2026-06-02* while both bodies carried 2026-08 content — calibrating a reader's trust wrong in the safe direction, which is luck rather than design. The first document was deleted with its class (#90/B3b). The second is corrected, and the field is now checked against the document's own dated content by `test_a_cic_review_date_is_not_older_than_its_own_content` — git could not answer this, because git records when a line was touched and this field claims when someone read the whole thing.

*The general fix is C-80's, not a re-count:* prose that states a number is a claim, and a claim needs a check. Where a number cannot be checked, the honest move is to state the command that produces it — which is what C-33 was forced into after its measurement was wrong five times.

Cross-refs: **C-80** (the same disease in ADRs and CICs, and the mechanism that would catch both), **C-72** and **C-44** (the bump this mis-scopes), **C-33** (the worked example of publishing the command instead of the result), ADR-014 §1.

**Resolved 2026-08-05 (B6).** Every named instance is disposed of, and two guards now stand where the prose was unchecked:

- `test_test_files_named_by_live_entries_exist_or_name_their_repo` — a live entry may not name a test file that does not exist unless it names the repo that owns it. Scoped to Open Concerns and Disagreements on purpose: eleven such mentions exist register-wide and nine are resolved entries correctly recording what discharged them, so a blanket check would cry wolf and be deleted within a day (ADR-014 §3).
- `test_a_cic_review_date_is_not_older_than_its_own_content` — a CIC's `Last reviewed` header may not predate dates in its own body.

**The first draft of the first guard was itself the bug it was written to catch,** and this is the part worth keeping. Its foreign-repo exemption reused `_FOREIGN_PREFIXES` — the list that namespaces *identifiers* — over a sixty-character window. That list holds ordinary English: `models`, `frames`, `pipeline-core`. A mutation planting a vanished file in a live entry left it green, because a sentence three words earlier said *"pinned pipeline-core-free"*. It had found its two real defects by luck of their neighbouring words. Rebuilt to require the owning repo **immediately abutting the path**, and re-proven against three mutations including the one that defeated the draft. A guard nobody has watched fail is decoration (ADR-014 §2) — and a guard watched failing on the *wrong* mutation is worse, because it has a proof attached.

**What is deliberately not fixed.** The general case — arbitrary prose asserting an arbitrary number — is not mechanisable and this entry does not claim it is. What is mechanised is the shape that recurred: a claim naming an artifact, checked by asking whether the artifact exists. Numbers that could not be guarded were removed in favour of the command that produces them, per C-33.

*Verify:* `pytest -q tests/test_register_integrity.py tests/test_doc_accuracy.py`

---

### C-80: The doc-accuracy scan exempts ADRs and CICs — the two artifact classes that define the contracts — RESOLVED

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

**RESOLVED 2026-08-05 (B5).** ADRs and CICs are now scanned, and the design was chosen by measurement rather than by argument.

**What the measurement said.** A path-resolution check over ADRs would have fired **29** times, and inspecting them showed most were correct history, other repositories' files, or paths inside URLs — the cry-wolf outcome this entry predicted, confirmed before building it. The curated deleted-symbol list was the narrower instrument: **22** hits over ADRs, **0** over CICs. Fourteen of the 22 were in ADR-011 alone.

**Three of those hits were real.** ADR-013 still cited `unfao/historical.py`, `unfao/wire/` and `unfao/wire/source_selection.py` — all moved to `contract/` by #153, all fixed here. Three genuine defects hiding among five markable ones is a workable ratio, and it is the ratio that justified turning the scan on.

**Two escapes, both declared rather than inferred.** Line-scoped `legacy-ok` for an isolated historical mention; a new file-level `<!-- legacy-ok-file: … -->` for a document whose *subject* is a retirement. ADR-011 is the case that earned it — it **is** the decision to remove the runtime mapper, so its subject appears fourteen times, correctly. A second guard pins the set of file-level exemptions to that one document, so adding another shows up in a diff.

**And a check nothing else could have made.** `test_a_cic_does_not_name_a_collaborator_its_class_never_calls` asserts that a class a CIC names is actually referenced by the class it documents — the `GaulLookupEnricher` failure, which no path check and no symbol list would have caught at the time, because the class existed and the paths resolved. Exception types are excluded: a *collaborator* is something the class reaches for, an *exception* something that passes through, and the first draft flagged three exceptions the manager legitimately propagates.

**The mutation campaign found a miss in the previous change.** Reintroducing the exact `GaulLookupEnricher` sentence did **not** fail — the collaborator check only sees classes that still exist, and #90/C-75 had deleted that one. The real gap was that the deletion never extended the deleted-symbol list, which that list's own comment demands in as many words: *"A deletion PR that does not extend this regex has not finished."* Extended here; the reintroduction now fails. Four further historical mentions written yesterday were flagged by the extension and marked.

Cross-refs: **C-75** (the retirement whose CIC error motivated this, and whose PR the mutation test caught short), **C-74** and **C-78** (guards narrower than their declared surface), **C-82** (the register's own prose, still unscanned), ADR-014 §2 and §3.

---

### C-83: A queryset that fails to import is reported as a queryset that declares the wrong format — RESOLVED

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

**RESOLVED 2026-08-05 (B4).** `launch_config.assert_queryset_was_importable(queryset)` now runs **before** the format check, and both managers read the queryset once and reuse the value.

The refusal says what actually happened — *"the postprocessor's config_queryset could not be imported … This is NOT a declaration problem: do not edit data_format until the module imports"* — and steers the operator toward the traceback pipeline-core logged, and toward a missing sibling checkout or dependency. It logs before it raises (ADR-008).

**Three guards, because order is the fix.** One proves the refusal fires and names the real fault; one proves an importable queryset passes (the format question belongs to the *next* check, and keeping them separate is the whole point); one asserts, per partner, that `get_queryset()` is called exactly once and that importability is checked first. Mutation-proven by deleting the check and by reversing the order — both fail.

**What is not fixed here, deliberately.** Upstream still returns `None` for any import exception, so the ambiguity exists at its source; we simply stopped passing it into a function whose contract is to default. Raising upstream would be better and is not ours to do — and waiting for it would have left the misleading message on the live FAO path meanwhile.

---

### C-79: `_ContractStorePort.upload`'s result check is called "the whole mechanism" and has no test, and it fails open — RESOLVED

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

**RESOLVED 2026-08-05 (B4).** Two changes, and the second is the one that mattered.

**Polarity.** `if success is False` became `if success is not True`. The old form failed **open**: a result that was `None`, or lacked the attribute, or carried a non-bool, sailed through as though the upload had worked. The dead `to_dict()` fallback went with it — an unrecognised result should be refused and *named*, not adapted to silently. The refusal now reports what it actually received, because `success=None` (a moved contract) and `success=False` (a reported failure) are different faults and send an operator to different places.

**Tests, where there were none.** `tests/test_store_port.py` — 16 tests over both partners: the happy path, a reported failure carrying the store's own error, four unrecognised-result shapes, and the field list the port forwards. Mutation-proven by reverting the polarity, which fails four of them.

**The standing excuse never applied here.** Manager-side facts are source-scanned because the managers need Appwrite env and a views-models path manager to instantiate. `_ContractStorePort` needs neither — it takes a store object and calls four methods on it. A fake store was always enough; nobody had tried.

**Its trigger fired two days before this and nobody noticed.** The entry read *"the 3.0.0 bump is the next occasion"*; the bump landed 2026-08-03, C-44 was closed with a wheel-level verification of the suite, and the return contract was never re-read. `test_register_integrity.py` cannot catch that — its checks are structural and none evaluates whether a named external event has occurred. That gap is C-82's.

---

### C-75: `GaulLookupEnricher` has no production caller, and now implements a second copy of the delivery path's keyed gather — RESOLVED

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

**RESOLVED 2026-08-04 — retired, as the decision recorded above required.** `views_postprocessing/contract/enrichment.py` and its 39 tests are deleted, along with `docs/CICs/GaulLookupEnricher.md`.

**No coverage of shipping code was lost.** The two tests elsewhere that imported the class both asserted only that its `lookup_version` agreed with `gaul_lookup.version()` — two readers of one fact, checked against each other. They now read the fact through the declared reader the delivery itself uses, which is the half that was ever load-bearing. The gather it duplicated is `contract/historical.py`'s, covered independently by four test files.

**One guard was deleted rather than kept.** `test_gaul_lookup_access.py` asserted `"GaulLookupEnricher" not in` the manager source. With the class gone that assertion cannot fail, and a test that cannot fail is decoration (ADR-014 §2). What it protected — one lookup read per delivery — is the first assertion in the same function and still bites.

**Fifteen files, and the sweep is the point.** The module, its tests, its CIC, the CIC index, two test files that imported it, the machinery list, the pandas-importer assertion, `README.md`'s dependency table and package tree, `role_and_seams.md`'s tree and contract list, ADR-012's ontology row and its pandas claim, and two module docstrings. Every one of those was a live claim about a class that no longer exists — which is the argument for C-80: none of the ADR or CIC references would have been caught by any guard.

**What it makes true.** `grep -rn "^import pandas\|^from pandas" views_postprocessing/ scripts/` now returns nothing at all — not a runtime import, not a type-only one. Epic **#85**'s claim, *pandas pushed to the seams*, is finally literal rather than nearly-true, and #85 and #93 close with this.

---

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
| Location | `views_postprocessing/unfao/store_port.py` (`_ContractStorePort` — all four contract-path store calls; it was `managers/unfao.py:37-64` until 2026-08-14), `:247` (legacy selection), `:560`, `:571` (legacy uploads) |

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

**Overridden 2026-08-10 (ADR-016), and the objection was designed around rather than dismissed.** Sibling checkouts *were* added to the per-PR workflow. The recommendation's argument was specific — *"it couples this repo's CI to another repo's **default branch**, so an unrelated upstream commit turns this repo red"* — and every sibling checkout declares **`ref: main`** for exactly that reason. A commit on someone's feature branch, or on a default branch that is not `main` (views-appwrite's default is `development`), cannot reach us. `test_ci_sibling_coverage.py` makes `ref: main` a rule rather than a habit.

**What is genuinely accepted, and should not be glossed:** a change merged to a sibling's `main` — a registry edition bump, say — *can* turn this repository red and block merges here until someone re-pins. That is not a defect being tolerated; it is the drift detector working, and the alternative is the state this entry was open about, where the drift was noticed only when a maintainer happened to run the suite. The cost is real and the trade is deliberate.

**The last residual closed 2026-08-17, and the reason it stayed open for two weeks is the finding.** ADR-016 added sibling checkouts but fetched only views-appwrite, so this entry's own subject — the deploy gate — still ran nowhere but a laptop. The stated blocker was that views-datafactory's GAUL parquets are untracked, so a checkout would turn honest skips into `FileNotFoundError`; that was tried on 2026-08-03 and reverted. **The observation was right and the diagnosis was wrong.** `test_gaul_lookup_fidelity` gated on `data/raw/gaul_admin/` being a *directory*, and that directory **is** tracked — it holds `supplement_azores.geojson` — while the seven parquets beside it are not. So a checkout satisfied the gate, the comparison ran, and it died. The sibling was never the problem; the gate was asking whether a folder existed when it needed to ask whether the files it reads existed.

Reproduced 2026-08-17 against a tracked-files-only worktree (`git worktree add --detach`, which contains exactly what `actions/checkout` produces): `1 failed, 37 passed, 1 skipped`, the failure being `FileNotFoundError: .../gaul0_code.parquet`. After re-gating on the seven parquets themselves: no failures. views-datafactory is now fetched in `run_pytest.yml` and declared `ci_checkout=True`.

**A second, larger instance of the same mistake was found while fixing the first.** All four sibling-aware tests in `test_gaul_lookup_fidelity.py` shared **one** gate keyed to the parquets — including two that read no parquet and one that reads no sibling at all. So they sat dark in CI for no reason anybody had chosen:

| test | actually reads | was gated on |
|---|---|---|
| `test_lookup_values_match_the_producer_parquets` | the 7 GAUL parquets (untracked) | parquets — correct |
| `test_lookup_gid_set_equals_the_declared_region` | `land_gaul_pgids.json` — **tracked** | parquets |
| `test_coordinate_formula_matches_every_priogrid_cell` | `priogrid_cell.dbf`, and self-skips on it | parquets |
| `test_coord_dtypes_are_wire_stable` | **only the committed lookup** | parquets |

The last one matters beyond tidiness: it is the check that `CODE_COLS` survive the §5.1 int64→float64 wire cast losslessly (`abs(v) < 2**53`) — the property ADR-013 §5.1a and the 2026-08-17 mail to FAO both rest on — and it needs no sibling whatsoever. Each test now gates on the artifact it reads.

Measured across the whole change, CI goes from **426 passed / 6 skipped** to **430 passed / 3 skipped**: four checks move from skipped to running — C-30's exclusion tripwire, this entry's `TestReleaseGate::test_land_gaul_commit_is_in_a_release_tag`, the region-set check, and the wire-cast dtype check. The producer-comparison half still skips, honestly, and still needs the parquets published somewhere fetchable.

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

**Residual — RESOLVED 2026-08-10 (ADR-016).** The gated half did not run in CI, which needed a views-appwrite checkout in the workflow. It has one: that repository went public on 2026-08-08 and the workflow now fetches it, so these checks run on every pull request. That was recorded here and in **C-46** as *"a CI-cost and cross-repo-coupling decision, not a code fix … worth deciding once for both"*, and it sat as a residual on two RESOLVED entries, which is where residuals go to be forgotten. It now has a live entry with a measured cost, a per-sibling answer, and an owner: **C-81**. *(As written this said "17 tests, 9 of them new in this arc" and that views-appwrite is private and needs a token. Both are superseded: views-appwrite went public on 2026-08-08 and is fetched by CI, and the gap is now **8 tests, all views-datafactory** — no credential closes it. See C-81.)*

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

**⚠ AMENDED 2026-08-11 — the value-copy scan was blind in this repository's own house style, twice, and the second time is the general lesson.**

The scan was extended to tracked markdown during the development→main sync, because README.md had carried four real coordinate values. Two reviews later, it was still missing two whole classes of copy — both of them ordinary markdown, both proven by injecting real registry values and watching the guard stay green:

| form | why it was invisible | fixed |
|---|---|---|
| `NAME=value   # comment` | `(.+?)\s*$` swallowed the comment into the captured value, so nothing compared equal. **README.md's own Configuration block is written in exactly this form.** | 2026-08-11 (iteration 2) |
| `` - `NAME=value` ``, `` \| NAME=value \| ``, `` set `NAME=value` before … `` | the pattern anchored the coordinate name at `^\s*`, so it saw only an assignment that *starts a line* | 2026-08-11 (iteration 3) |

The shared cause is not a regex bug. **The pattern described one way of writing markdown — the way this repository happens to write it today — and a guard against publishing a value has to survive the next contributor writing a bullet instead of a fenced block.** The name may now be preceded by anything that is not part of an identifier, and the value ends at whatever terminates it in prose: a comment, a closing backtick, or a table pipe. Thirteen forms are proven caught; the four legitimate mentions that must stay silent are proven silent.

**The residual, which is deliberate and should not be "fixed".** This remains a *syntax* match. A value merely named in a sentence — "the six stranded documents in `<bucket>`" — is not a copy and does not fire. An earlier draft that matched any occurrence fired on a dozen documents, and the lesson recorded above applies to itself: a guard that cries wolf gets deleted, after which the real rule is unguarded (ADR-014 §3). The class this cannot catch is a value pasted into prose with no assignment syntax anywhere near it. That is accepted, because the alternative has been tried and was worse.

**Mitigation — landed 2026-08-12 (#243). The parse is gone; the scan matches the pair.**

The scan no longer parses a line and compares what it captured. It knows both halves before it starts — the declared names and the declared values — so it matches `NAME = VALUE` directly, with `findall` rather than one match per line. Every blindness recorded above came from the parse: the swallowed comment, the missing terminator, the six-character lookbehind, the second assignment on a table row. None is expressible now.

The two halves need not correspond: `APPWRITE_X=<value declared for APPWRITE_Y>` is the ordinary copy-paste slip and is reported as a copy, naming the coordinate that *declares* the value rather than the one the line assigns.

**The `secret` exemption is gone.** It was an inline name literal under a comment saying the scope came from the declared partition and not from an inline list. Measured, `[secret]` carries no values today, so removing it changes nothing now and closes the hole the day one gains a value.

**The stopping rule is a test, not a paragraph.** `test_the_scan_understands_every_assignment_form_this_repo_writes` enumerates every line in this repository's own tracked markdown that assigns a declared coordinate, and fails if the matcher cannot read one. So the form list is derived from the corpus: a form no document here uses is not a gap, and a new form is added in the same change as the document that introduces it. That is what stops the fifth widening.

**The four scope mutations routed from #242 are all closed**, by one richer fixture rather than four tests: two copies, in two sections, one short, one in markdown. Each element defeats a specific narrowing — stopping at the first finding, reading only `target`, reinstating a length floor, skipping the markdown branch. Plus one small test for a package module that does not parse, which must be refused rather than stepped over. All five measured surviving before, all five caught after.

**And an exclusion list was built and then deleted**, which is the useful part. The plan called for excluding values spelled like this repository's own code. Measured against what the AST branch actually sees — non-docstring string constants — **the collision does not exist**: the only registry values appearing that way are the two `contract` rows, and `contract` is MIRRORED rather than CONSUMED, so it is never in the scanned set. The list narrowed a security scan for a problem this branch does not have. The residual is latent and recorded in C-97: the day someone writes a package directory name as a bare string constant, the scan will fire on it.

**Why this belongs on C-57 rather than in a new entry.** It is the same guard, the same failure direction, and the same lesson this entry already records one layer down: the earlier amendment found the scan's *scope* was never mutation-proven (it named `unfao` and missed `crafd`); this one finds its *matching* was never proven against the file formats it scans. Scope, matching, and now syntax-variant — three ways for a mutation-proven guard to be proven against the wrong thing.

**⚠ CORRECTED 2026-08-12, and the correction is the same mistake one level up.** The amendment immediately above claims "thirteen forms are proven caught" and cites `` set `NAME=value` before … `` as evidence the mid-sentence class is covered. An independent review supplied twenty-nine forms and **fifteen missed**, including the *unbackticked* form of that very example: `set NAME=value before running` captures `'value before running'`. The cited case passes only because of its backticks. Measured, not argued.

Two distinct defects sit under those fifteen, and both are the pattern-describes-one-dialect cause this entry already names:

1. **The unquoted value has no whitespace terminator.** It ends only at `#`, a backtick or `|`, so any value followed by prose escapes. And `search` is called once per line, so on a two-variable table row every assignment after the first is invisible.
2. **The boundary is an allow-list, not a predicate.** The comment above it says the name may be preceded by "anything that is not part of an identifier"; the code is a six-character lookbehind. A quoted, parenthesised or colon-prefixed assignment produces no match at all — so the pattern can *parse* a quoted value but cannot *see* a quoted assignment.

**And a fourth failure direction, opposite to the other three.** Removing the six-character floor admitted the registry's two shortest values into the ban-set. Measured: **they are this repository's own package directory names — the exact contents of `PARTNER_PACKAGES`** — matched by exact string equality against every non-docstring string constant under `views_postprocessing/`. The justification given, "measured, removing it keeps the suite green", measured today's source and not the next commit's. The next `logging.getLogger(<partner>)` or `Literal[<partner>, …]` fails a security guard for code that copied nothing, and this entry's own doctrine says what happens next. It also hands views-appwrite a way to redden this repository by declaring any short ordinary word as a value — which is **C-86**'s coupling, arriving through the guard that was supposed to reduce it.

Registered as **C-89** (the leak half) and tracked with this entry's remediation. **C-93** records why the author's own proof did not find any of it.

Cross-refs: C-74 (the guard this paragraph vouched for), C-33 (store identity still hardcoded per store — the same env surface, different concern), C-58 (what happens when a coordinate is wrong rather than missing), C-44 (the pipeline-core version coupling that would carry a registry change), **C-86** (the drift checks this scan sits beside), issues #134/#135/#138 (this repo's discharged þing-01 obligations), #104 (README env block placeholders).

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

**Residual 2 — the enrich→validate end-to-end test — RELOCATED to #18**, per the Register Conventions' relocation rule (a relocation is not complete until the destination exists and is cited by number). Every *leg* is now covered — enrichment (**no longer a leg**: `GaulLookupEnricher` and `test_enrichment.py` were deleted in #90/B3b, the lookup join having moved into the frame build; recorded here because the closure above was argued from a list this deletion shortened), artifact build (`test_historical_builder.py`, 7), reader parity (`test_historical_parity.py`, 3), the invariants on primitives (`test_input_integrity_e2e.py`, 8), the wire end to end (`test_hop_b_sink_e2e.py`, 6), the null-gate (`test_validation.py`, 14). What remains uncovered is **the manager orchestrating them**, which needs views-pipeline-core and a production-like Appwrite environment — and **þing-01 D2** forbids integration tests against the production project while no non-production one exists (see C-95 — the ruling is conditional, and creating that project is an open operator assignment).

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
