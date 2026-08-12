# Post-Mortem — The Guards That Did Not Guard

**Period:** 2026-08-11 → 2026-08-12 (two execution days; PR #239 merged 19:16 on the 11th, PR #240 — the release — merged 20:31 on the 12th).

**Scope:** Build a cross-repository guard surface that detects drift between this repository and its siblings; discover through independent review that most of that surface did not do what it claimed; repair it; ship. Covers PRs #239, #252–#255 and the release #240, plus epic #241 (stories #242–#250) and the risk-register range **C-89…C-97**.

**Final stats:** 6 PRs merged · 44 commits on `main` · 9 new register entries (97 total, 24 open) · 3 ADR errata across ADR-016/ADR-017 · 2 cross-repository issues filed (views-faoapi#390, views-crafdapi#55) · `tests/*.py` 9,200 → 9,308 against a package of 2,998 lines · **zero delivered bytes changed** (`CONTRACT_VERSION` 1.5 on both sides, `tests/fixtures/` byte-identical).

---

## Why this effort

Three problems arrived together.

**The registry drift check was blocking releases.** It compared this repository's pinned edition *label* against views-appwrite's current one. That registry moved five editions in four days, four of them recording console observations that obliged nobody. Every move reddened this repository, and merging to `main` is the release to the UN FAO. Registered as **C-86**.

**Two consumer-facing checks were owed** — issue #238's D3 and D4: verify each partner's delivery label against the public coordinate registry, and retire the check that read the consumer's own source once that consumer checked itself.

**And the failure mode underneath both is invisible by construction.** If the name this repository uploads under and the name the consumer filters on drift apart, the upload succeeds, the file is stored and billed, the consumer's endpoint returns empty, and nothing raises anywhere. ADR-013 §4.1a calls it *"invisible to the consumer, not merely degraded."* It is the one failure this platform most needs a machine to notice.

PR #239 addressed all three. It was reviewed twice before merging, and merged green.

**Then a post-merge review found fifteen defects in it, and every one reproduced.**

---

## Timeline

| Time (CEST) | PR / commit | What happened |
|---|---|---|
| 08-11 19:16 | **#239** | Registry check rewritten to match on rows rather than the edition label; #238's D3/D4 land. Two review rounds before merge. |
| 08-12 ~10:00 | — | Post-merge `/code-review max`. **Fifteen defects, all reproduced.** Registered C-89…C-93. |
| 08-12 ~11:00 | — | `/expert-code-review` on seven standing decisions. Finds that ADR-017's integration-test prohibition is **conditional** and *grants* read-only preflight — a mechanism believed closed for weeks because the register cited the wrong þing verdict. C-94…C-96. |
| 08-12 ~12:00 | **#241** | Epic opened, nine stories, three gates. Re-scoped an hour later after the maintainer's intervention (below) from nine stories of widening into mostly deletion. |
| 08-12 15:07 | **#252** | **#242** — the no-copy guard printed the value it exists to hide. **Four iterations.** |
| 08-12 16:13 | **#253** | **#245** — delete the arrival check. Three iterations. |
| 08-12 19:55 | **#254** | **#248** — delete both consumer source-reads. **Twelve commits.** |
| 08-12 20:24 | **#255** | **#243** — pair-matching and the corpus stopping rule. Five commits. |
| 08-12 20:31 | **#240** | **Release.** 61 commits to `main`. Verified after: 415 passed, ruff clean, `CONTRACT_VERSION` unchanged. |

---

## What we did

### The three defects that would have shipped

| | |
|---|---|
| **The guard against publishing a coordinate value printed it.** | `tests/test_env_declaration.py`'s scan had two reporting branches. One was taught on 08-11 not to interpolate the value; the other was not, and went on doing it for a day. It fires only when a coordinate has actually been copied — so on the single event it exists for, into a world-readable CI log, it published the thing it forbids. |
| **The drift check subscribed us to another repository's changelog.** | Its arrival half compared every row of every table this package depends on. Measured: each partner reads **13 of 25** rows; **6 belong to no repository here**. An API key issued upstream for an unrelated consumer would redden this repository and block a release — C-86's own failure class, arriving through the guard written to reduce it. |
| **Fifteen of twenty-nine markdown assignment forms escaped the no-copy scan.** | The author proposed thirteen forms and proved all thirteen caught. An independent review proposed twenty-nine. |

### The remedy was deletion three times out of five

| Story | Change | Net |
|---|---|---|
| #242 | value removed from the reporter's signature; behavioural guard replaces a source-reading one | +55 then −140 |
| #245 | **delete** the arrival half; keep the row differential | deletion |
| #248 | **delete** both consumer source-reads and the sibling fetch they justified | −95 lines |
| #243 | **delete** the parser; match the pair. Stopping rule becomes a test | +~100 (five closed mutations) |

### The cross-repository outcome

The source-reading check broke **twice in twenty-four hours** — views-faoapi on the 11th, views-crafdapi on the 12th — each time because that repository refactored `APIPathManager("literal")` into `APIPathManager(CONSUMER_DOCUMENT_NAME)`. Verified: commits `8615574` and `0c493ae` each introduce that constant **and** add that repository's registry-binding test. **The improvement and the breakage were one edit.**

We deleted the mechanism rather than repairing it a third time, registered the residual as **C-92**, and filed the ask where the fact lives: **views-faoapi#390** and **views-crafdapi#55**, both asking each consumer to prove its *query* uses the name it declares.

---

## What we learned

**1. A guard must be pointed at the thing it claims to guard.** This recurred three times in two days. A guard asserting that findings were *routed* through one formatter (routing is not safety — the value could be smuggled through either parameter). A silence guard calling the helper *underneath* the check it named (re-adding the deleted arrival half left the suite green). A rotation proof calling `_describe_changes` rather than the check. Each read plausibly; each watched the wrong subject.

**2. A mutation proof written by the author of the guard tests the author's imagination.** Thirteen forms proposed, thirteen caught; twenty-nine proposed independently, fifteen missed. The proof was real and every case genuinely passed. *"Proven against N mutations"* reads as a statement about the guard when it is a statement about N. Registered as **C-93**.

**3. Measure before building.** The plan called for excluding registry values spelled like this repository's own code. Measured against what the AST branch actually sees — non-docstring string *constants* — **the collision does not exist**. The exclusion would have narrowed a security scan for a problem that branch does not have. Built, measured, deleted.

**4. A check that reads another repository's source is not a check this repository builds.** Not a preference — a measurement. Two breakages in a day, both caused by the other repository improving itself.

**5. The register's own conventions are load-bearing.** An amendment heading was written as *"Mitigated"*, which is neither of the two phrasings the register declares. It passed `test_register_integrity` by **evading the string match** rather than by complying — the identical escape ADR-014 §5 records C-15 making.

**6. A permission can hide inside a prohibition.** The register cited "þing-02 D2" for the ban on integration tests against the production Appwrite project. The ruling is **þing-01 D2**, it is conditional (*"until the operator creates one"*), and it explicitly **grants** read-only preflight validation. A whole class of mechanism — the producer-side findability check that would close C-94 — was believed closed for weeks because a citation pointed at the wrong document.

---

## Process — what did not work

This is the section that matters, and the honest summary is: **the review loop worked; the rate at which the author generated new defects did not.**

### The cost, measured

| | |
|---|---|
| Commits per story | #242 **7** · #245 **7** · #248 **12** · #243 **5** |
| Lines added to code | **341** |
| Lines added to docs and register | **452** |

**One and a third lines of prose for every line of code.** And nearly every defect the reviews found lived in the prose, not the code.

### Four failures of process, in order of seriousness

**1. A governance rule was repealed on a false claim about another repository.** The first ADR-017 §5 erratum stated the sequencing constraint *"dissolved rather than being satisfied"* and that views-crafdapi#53 *"has not landed."* #53 closed at **12:15**; the commit was **18:18** — six hours later. Both partners' gates had been met. The deletion was still correct, on §7's grounds, but the reason written into a permanent decision record was untrue. Writing a repeal into ADR-017 on a false claim about another repository is §3's failure inside §5's own text.

**2. Each remediation introduced a defect of the same class as the one it fixed.** A tautological assertion added in the commit that fixed *"nothing proves this check fires"*. A cry-wolf helper (`_carries`, an 8-character window) added to defeat an adversarial mutation nobody writes by accident — and it was **strictly worse than plain `in`**, condemning a bare, safe file path. Two directional pointers ("further down this entry", "the rotation proof below") that both pointed the wrong way, in the same commit.

**3. Numbers were quoted from memory rather than measured.** A line-budget figure was posted wrong in the tracking issue, corrected — and the correction's per-file figures were also wrong. Twice in consecutive comments. A mechanical rule was adopted mid-sprint: *no number reaches a comment, commit message or ADR unless a command produced it in the same turn.* It should have been the rule from the start.

**4. A review was reported as running when nothing had been launched.** Caught by the maintainer asking.

### The root cause, and it is not the guards

The initial diagnosis was *"the guard surface is bloated"* — 9,200 test lines against 2,998 package lines, with the largest test file 45% meta-tests. That diagnosis produced the wrong acceptance criterion (`wc -l tests/*.py` must end lower), and it was wrong.

The measured diagnosis is narrower. **The prose was bloated; the guards were mostly missing.** Three of the four things #243 closed were holes, not decorations. Every line added after #242 exists because a *measured mutation survived* — not one was speculative.

And the specific engine of the prose cost is architectural: **ADR-016 and ADR-017 contain descriptions of current implementation** — *"this is the shape the registry check now has"*, *"today the check still reads the consumer's source"*. An ADR records a decision. The moment it also describes the code, it becomes a second copy of the code, and it rots on every change. Most of #248's twelve commits were repairing implementation descriptions that should never have been in an ADR.

### What was changed mid-sprint, and what it bought

The maintainer's intervention — *"things that you have created have become so complicated and heavy with technical debt that you are not even able to maintain it. Then no one can."* — was the turning point, and it was correct. It produced:

- a re-scoped epic: nine stories of widening became mostly deletion, with **#240 shipping after three issues instead of nine**;
- the **one-home rule**: the reasoning lives in the register, docstrings point at it, ADRs are touched only when the *decision* changes.

The rule was applied for the first time in #243. **#248 took twelve commits; #243 took five.** That is one data point, not a trend, but it is the only intervention that moved the number.

### What worked

- **Independent review.** Five parallel reviewers on #242 found what four rounds of self-review had not. The adversarial mutation reviewer — briefed only to supply mutants the author had not thought of — was the single highest-value input of the arc.
- **Deletion as the default remedy.** Three of five stories were net deletions, and each closed its defect more completely than a repair would have.
- **Refusing to chase.** Five surviving mutations were explicitly declined in writing rather than fixed: four routed to the story that owned the scope, one declared infinite regress. Writing down what is *not* being chased, with the reason, prevented a sixth round.

---

## What remains

Four stories, none blocking anything, all opened by this arc's own reviews:

| | |
|---|---|
| **#246** | A tautological mutation proof; `registry_current` — the function `tests/seam_registry.py` exists to provide — has no test. |
| **#247** | Three legibility fixes: a stale clone produces four errors and three explanations; `rows()` raises `AttributeError` on a shape the live registry already has; a scratch repo that can hang the suite under `commit.gpgsign`. |
| **#249** | Eight stale claims, plus the þing-01/þing-02 mis-citation. |
| **#250** | Two short ADR amendments — what a check may rest on, and what *mutation-proven* is allowed to mean — **plus the rule that an ADR records a decision and never current implementation state.** The highest-leverage item left. |

**Operator-owned and now unblocked:** cut a tag (views-models#364 and views-crafdapi#43 are waiting); make `test` a required status check (read C-86 first — `protect_main` has zero bypass actors); views-appwrite#86, whose gates are both met.

**Deferred with triggers, not omitted:** the producer-side read-only findability preflight (**C-94** — legal under þing-01 D2, needs a read credential in the launcher); adopting `[edition].obliges_consumers`; extracting a platform declarations module (**C-88**); consolidating the leak guards into `tests/test_redaction_guard.py`.

---

## The one-sentence version

We built a large guard surface, discovered through independent review that a substantial part of it verified facts this repository is not entitled to know — and therefore could only be proven against its author's imagination — deleted most of that part, and shipped; the lasting lesson is that **a check may rest on a fact we own, on a fact another repository has declared, or on an outcome we can observe, and never on another repository's implementation.**
