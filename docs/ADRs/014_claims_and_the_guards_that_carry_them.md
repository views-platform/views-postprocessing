# ADR-014: Claims, and the guards that carry them

**Status:** Accepted
**Date:** 2026-08-02
**Decider:** Simon Polichinel von der Maase
**Arises from:** epic [#181](https://github.com/views-platform/views-postprocessing/issues/181)
**Related:** [ADR-003](003_authority_of_declarations_over_inference.md) (declarations over
inference), [ADR-005](005_testing_as_mandatory_critical_infrastructure.md) (testing as
infrastructure), [ADR-010](010_technical_risk_register.md) (the register)

---

## Context

Over two days in August 2026, this repository found **seven** places where it said one
thing and did another. *(An eighth arrived the day after this ADR was accepted, and the
count is left at seven deliberately — see the note at the end of this section.)* None was a bug in the delivery. All were claims that had outlived
what they described:

- three register entries filed as open with their own stated closing conditions met
  (C-43, C-59, C-61) — one of them saying, in its own body, *"closes when
  `tests/test_gaul_lookup_fidelity.py` is committed and green"*, with the file committed
  and green;
- two issues closed with their work partly undone (#154, #158) — #158's rename also
  broke a URL by find-and-replacing a filename inside it;
- a test file asserting *"the logic tested matches `unfao.py:_validate()` exactly"* about
  a method it had stopped resembling seven weeks earlier, while running 43 cases against
  a function it defined itself;
- a security-adjacent guard scanning **6 files where it declared 17**, because four of
  its five declared roots had been moved and `rglob` on a vanished directory returns
  silence rather than an error.

The pattern is not carelessness. Each was written accurately and became false when
something else moved. What they share is that **nothing was attached to them that would
notice**.

**The eighth, and why the count above stays at seven.** On 2026-08-03 — the day after
this ADR was accepted — PR #211 added a second partner package and found that *eight*
guards were scoped to the first partner by name, so the new one landed exempt from all of
them, including the þing-01 `load_dotenv` prohibition. Register **C-78** records it. The
count above is deliberately not incremented: an ADR that renumbers itself every time the
pattern recurs becomes a changelog, and the argument does not depend on the number. What
the eighth case adds is §2's sharpest form — *a guard's declared scope is part of what
must be mutation-proven, not just its matching.*

ADR-003 already forbids inferring what should be declared. This ADR is that rule applied
one level up: **a declaration that nothing validates is an inference with better
grammar.**

---

## Decision

### §1 A guarantee is attached to a check, or it is not a guarantee

When this repository asserts something a reader would rely on — in code, in a docstring,
in an ADR, in the register — the assertion is accompanied by something that fails when it
stops being true. If no such check is possible, §4 applies.

This extends to the repository's own governance artefacts. The register is checked by
`tests/test_register_integrity.py`; the living docs by `tests/test_doc_accuracy.py`; the
package boundary by `tests/test_clone_readiness.py`. **A governance artefact is not exempt
from the rule it exists to enforce.**

### §2 A guard is mutation-proven, or it is decoration

A new guard is demonstrated to **fail on the defect it was written for**, and that
demonstration is recorded in the pull request. A guard that has never been watched fail is
a guard whose shape nobody knows.

Two failure modes, both observed here, and both must be considered:

- **too narrow** — the þing-01 redaction guard passed while covering a third of its
  declared surface;
- **too broad** — a first draft of the coordinate-copy check flagged a *function name* in
  this repository as a leaked value.

Where a guard's inputs are declared (a path list, a module list, a set of names), **assert
that the inputs are real**. `rglob` on a nonexistent directory yields nothing rather than
raising; a list of paths that no longer exist does not fail a scan, it empties it.

### §3 Prefer a false negative to a false alarm

A guard that cries wolf gets deleted, and then the rule it carried is unguarded — which is
strictly worse than the narrow guard that would have caught most cases. When a guard fires
on something legitimate, **the first question is whether the matching is wrong, not
whether the scope is too wide.** In the one instance where scope was narrowed instead, the
result missed the shape the defect would actually take.

Corollary, learned expensively: **existence is not reachability.** A cross-repo pin was
verified to exist, its files were verified to exist at it, and every check written at the
time passed — but it sat on an unmerged branch, declared a version never ratified, and was
withdrawn. Where a claim is about what another repository *says*, check reachability from
that repository's `main`.

### §4 A deferral is attached to a trigger and an owner, or it is not a deferral

Deliberate duplication, an unbuilt fix, an unanswered question: each is recorded with the
**named event** that should reopen it. Not "later", not "when convenient" — a thing that
will observably happen.

Worked examples now in force: the two entry-validation modules stay duplicated until *a
third one is written*; sidecar version-stamping waits for *the next ADR-013 version bump*;
scheduled cross-repo checks wait until *an upstream change reaches the partner through
this repo without anyone noticing first*.

The counter-example is why this clause exists. Epic #148's retired code path was kept
"until run 0 proves the contract path live" — a real condition, with no owner and no
trigger. Run 0 happened on 2026-07-27 and nobody opened the box; the cleanup took a
subsequent epic.

### §5 A change that names a record disposes of that record in the same change

If a pull request cites a register entry, an issue, a CIC or an ADR as the thing it
addresses, it updates that artefact **in the same pull request**. Not in a follow-up, not
at closeout, not from memory.

**No test enforces this in general, though two partial guards exist and are green.**
`tests/test_register_integrity.py` carries
`test_no_open_entry_names_a_closing_artifact_that_already_exists` and
`test_no_open_entry_claims_its_mitigation_has_landed` — both added by S2 in this same
arc. They catch the two mechanisable shapes: an entry naming a file that now exists, and
one whose body says a mitigation landed while its header says Open.

What resists mechanisation is the general case: no expression reliably separates *"this
entry describes work that is done"* from prose, and a guard that guesses is one that gets
deleted (§3). So the clause is mostly a habit, and it is written down because it is the
rule here least amenable to a test — which makes it the one most likely to lapse.

*(Corrected 2026-08-03. This paragraph said "none is proposed" and the Alternatives
section called widening the guard "attempted and abandoned", while the widened guard was
already shipping in the same branch. And the guards' reach is genuinely partial: C-15 sat
Open claiming a mitigation had landed via a method that no longer exists, and escaped
`test_no_open_entry_claims_its_mitigation_has_landed` because it phrased the claim
without the em-dash the guard matches. Partial is worth saying; absent was wrong.)*

The evidence that it does lapse is this epic's own record. C-71 was fixed on the morning of
2026-08-02 and sat filed open for the rest of the day while eight further stories shipped.
The CIC lagged the change in **three consecutive stories** and was corrected by review each
time, never by anything mechanical.

---

## Consequences

**Cost.** Every guard now carries a mutation demonstration, which is roughly a third again
of the work of writing it. Every deferral needs an argued trigger, which is harder than
writing "later" and is meant to be: if no trigger can be named, the deferral is probably a
decision being avoided.

**What this does not license.** Not every statement needs a test. §1 is about assertions a
reader would *rely on* — a contract, a boundary, a count, a closing condition. Prose that
explains reasoning is not a claim in this sense, and three times during this epic a guard
fired on the very sentence describing it. The fix each time was to name the thing without
spelling it, **never to weaken the guard** — three weakenings would have left nothing.

**Where it will be violated first.** §5, because it is the only clause a contributor can
break while every test passes.

---

## Alternatives considered

**Write nothing; the guards teach themselves.** Genuinely tempting for §1–§3: a
contributor who violates the register's closing-condition convention gets a failure naming
the exact strings and the fix, at the moment of violation — better teaching than an ADR
nobody opens. Rejected because it leaves §4 and §5 unrecorded, and those are the two
clauses no test carries. An ADR that exists for the mechanisable rules would be ceremony;
one that exists for the *un*-mechanisable ones is the only vehicle available.

**A checklist in the PR template instead.** Cheaper and closer to the moment of work.
Rejected as a replacement, not as a supplement: a checklist records what to do and not why,
and the reasoning is what survives a contributor deciding the rule does not apply to them.
Worth adding later, pointing here.

**Widen `test_register_integrity` to catch §5.** Partially done — see §5. Two shapes are
mechanised and green; the general case resists. Recorded so the next person neither
re-attempts the general case nor assumes there is nothing there.
