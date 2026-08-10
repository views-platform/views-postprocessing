# ADR-016: Which sibling repositories CI downloads

**Status:** Accepted
**Date:** 2026-08-10
**Decider:** Simon Polichinel von der Maase
**Scope:** repositories CI **can** download — that is, public ones. What to do when a
repository **cannot** be downloaded is a different decision, taken in
[ADR-017](017_facts_across_a_private_boundary.md) and accepted alongside this one.
**Related:** [ADR-014](014_claims_and_the_guards_that_carry_them.md) §2 (a guard nobody has
watched fail is decoration) and §4 (a deferral names a trigger and an owner)

---

## The decision in three sentences

A few of this repository's tests read **other** repositories to check that things we say
about them are still true. Those tests only work when the other repository is on disk, so
they ran on a developer's laptop and skipped in CI. **CI now downloads the repositories
those tests need**, and a test fails if CI stops downloading one that the code says it
should.

*Throughout, a "sibling" is another repository in the views-platform organisation that sits
beside this one in a developer's folder — never a dependency we install.*

## What this document does not cover

Downloading a repository requires being able to read it, so **everything here applies only
to repositories that are public.** A private one cannot be downloaded by our CI at all,
and no amount of workflow configuration changes that.

That is not a gap in this decision; it is a different problem with a different answer, and
that answer is [ADR-017](017_facts_across_a_private_boundary.md). This document stops at
the boundary and says so, rather than implying a coverage it does not have.

---

## Context

### §1 What these tests actually do

Most tests here check our own code. A few check something different: whether a **claim
this repository makes about a different repository** is still true.

The clearest example. Each partner's `appwrite_env.py` says, in effect, *"we were written
against edition 1.4.4 of the shared configuration registry."* That registry lives in
another repository. A test opens that repository and checks the edition is still 1.4.4.

This is not hypothetical housekeeping. On 2026-08-05 that test failed — the registry had
moved to a new edition while nobody here was looking. Two days earlier, the same family of
checks fired **twice in one day**.

### §2 Why they were not running

A test like that needs the other repository present. On a laptop all the platform
repositories sit in one folder, so it runs. A GitHub Actions job gets **one** repository,
so it skipped.

The result: **CI verified less than a laptop did, exactly on the checks that span two
repositories** — the ones no single repository can replace.

### §3 Why nobody noticed for so long

Which repositories CI could download was recorded in a **comment** in the workflow file.
That comment said `views-appwrite` was private, so its seven checks were assumed to need
an access credential nobody had issued.

It had gone public on **2026-08-08**. The comment had not changed with it. Seven checks
stayed switched off for no reason at all, and the first draft of this very document
proposed issuing a credential to reach them — written one day after the thing that
justified it stopped being true.

**That is the whole lesson.** A fact about another repository, written in prose, with
nothing able to check it, will eventually be wrong and nobody will find out.

---

## Decision

### §4 The list of siblings is code, not a comment

`tests/conftest.py` holds one entry per sibling repository, and each entry says:

- **`env`** — the environment variable that overrides where to find it;
- **`ci_checkout`** — whether CI downloads it;
- **`note`** — why not, when the answer is no.

That is all. It replaces a comment with something a test can read.

### §5 CI downloads exactly what that list says, and a test enforces it

The workflow downloads every sibling marked `ci_checkout=True`.
`tests/test_ci_sibling_coverage.py` fails if the workflow and the list disagree — in
either direction: a repository the list expects and CI does not fetch, or one CI fetches
that the list never mentions.

Six rules, and each exists because of something that has actually gone wrong:

| | rule | the incident behind it |
|---|---|---|
| G1 | a listed repository is downloaded, and the tests are pointed at it | the tests looked in the wrong place and skipped silently |
| G2 | anything CI downloads appears in the list | the list is the thing people read; CI is not |
| G4 | a repository we skip says why, and **every** note names a record | silent non-coverage reads as "nothing to see here" — and a note nothing points at is the prose this file replaces, whether it explains an exclusion or a temporary inclusion |
| G5 | a download step may not be marked "ignore failures" | one setting and a failed download stops failing the build |
| G6 | downloads land in `_siblings/` | a sibling put elsewhere made the linter report 745 errors in someone else's code |
| G7 | download the sibling's `main` branch | a sibling's default branch is not ours to rely on — views-appwrite's was `development` as of 2026-08-10, and is theirs to change again |

Each rule is a plain function, so each is also run against a deliberately broken example
to prove it objects. A rule only ever tried against a correct file is a rule nobody has
watched fail.

**One of these downloads is temporary, and it is worth knowing which.** `views-crafdapi` is
fetched for exactly one test. [ADR-017](017_facts_across_a_private_boundary.md) §7 replaces
that test with one that reads a public declaration instead — at which point this download
buys nothing and goes. That has been decided and is not yet done; it waits on the
declaration landing in the registry. That is a decision this document cannot make on its own, which
is why it is recorded there and cross-referenced here.

### §6 A repository CI expects but cannot find turns the build red

Skipping is right on a laptop, where a missing sibling is normal. It is wrong in CI once
we have said the repository should be there — a silent skip puts us back in §2 while
looking fixed. So CI names the repositories explicitly, and a missing one is a failure.

That guard existed already
(`tests/test_env_declaration.py::test_no_sibling_override_points_at_a_missing_path`) and
had a hole, closed here: it treated a variable set to an **empty string** as unset, which
is exactly what a mis-typed CI setting produces. So the likeliest misconfiguration was the
one case it could not see.

### §7 A broken sibling can block merging here, and that is accepted

This is the real cost, and it should not be buried. CI now depends on two other
repositories. If one of them changes in a way that fails a check — say the configuration
registry moves again — **this repository's builds go red and merges are blocked until
someone updates the pin.** Since merging to `main` here *is* the release to FAO, that
matters.

It is accepted for two reasons:

1. The problem being fixed was that these checks were **invisible**. A check that reports
   but cannot block is invisible again, just more politely.
2. A red build in that situation is *correct*. It says "re-pin before you ship", and the
   fix is a small edit rather than an investigation.

**A third reason was offered and withdrawn, because it was not true.** An earlier draft
said the maintainer administers this repository and can therefore merge over a failing
check when something is genuinely urgent. Two external reviewers challenged it, and it does
not survive measurement: the `protect_main` ruleset lists **zero bypass actors**, and a
ruleset applies to everyone except the actors named there — so administrator status confers
no exemption. There is no classic branch protection either, hence no `enforce_admins` route.

So **there is currently no escape hatch**, and the coupling here is accepted without one.
That is defensible — the two reasons above stand on their own — but it should be a chosen
position rather than a surprise on the day it matters. Adding a bypass actor is a console
change and would restore the third reason; it has not been made. And an override of that
kind would be one person's judgement, available only while that person is — the same
habit-dependence this document criticises in its own alternatives.

### §7a How often this actually bites

*"A small edit"* reads differently at once a quarter than at once a day, so the rate
belongs here rather than in a reader's imagination.

views-appwrite reports its registry moved through **five editions in four days** — v1.4.0
on 2026-08-02 through v1.4.4 on 2026-08-05. **Four of the five were observation-driven**,
recording what a console showed or correcting a key's scopes, and carried no obligation for
any consumer. Under this section each would have reddened this repository and blocked a
release until someone re-pinned.

That is not an argument against the decision; it is the honest size of it. It also points
at a better shape, which that repository has volunteered to make usable: pin against the
contract **version** and treat observation-only bumps as non-blocking, rather than pinning
a commit and blocking on every edit — the upstream amendment log already marks which bumps
carry obligations. **Not adopted here**, because it needs the upstream side first and this
document should not decide another repository's format.

### §7b Two kinds of coupling, and only one is a tripwire

A reader could take G7 as *"always track the moving tip of `main`"*, which would sit oddly
beside the rest of the platform, where consumers pin the seam contract by tag and never by
branch. Both live here, and they answer different questions:

- **Drift tripwires** read the sibling's `main` *because* movement is the signal. The
  registry-edition check is one: if the registry moved and our pin did not, we want to know,
  and a red build is the entire point.
- **Reachability checks** verify that a *pinned* commit is an ancestor of the sibling's
  `main`. Here movement is noise; what matters is that what we pinned was ratified rather
  than taken from someone's unmerged branch.

G7 makes both read `main` rather than a default branch. It does not make either of them
track the tip for its own sake.

---

This section overrides an earlier internal recommendation not to couple per-pull-request CI
to another repository at all. That recommendation's stated objection was coupling to another
repository's *default branch* — which G7 removes, by naming `main` explicitly instead of
accepting whatever default the other repository happens to be set to. The coupling that
remains is real, and is the trade described above.

### §8 One repository stays out, and why that is not this document's problem

`views-faoapi` is private. Our CI cannot download it, so the one check that reads it does
not run here.

**No credential is issued to work around that**, and that is a decision rather than an
omission. Where that question *is* decided is
[ADR-017](017_facts_across_a_private_boundary.md): the fact gets declared somewhere public
that both sides can read, so that neither needs access to the other.

**That decision is accepted but not yet implemented** — it depends on a declaration being
added to the platform registry, which is another repository's work. Until then the affected
check runs on a maintainer's machine and not in CI, and the sibling's `note` says so.

Until that declaration exists, the affected check runs on a maintainer's machine and not
in CI. That is stated in the sibling's `note`, which rule G4 requires and which must name
the record that owns it.

---

## Consequences

**What this buys.** Seven cross-repository checks move from *"run when someone happens to
run them"* to *"run on every change"*. Two of them fired in earnest the week this was
written. Separately, the scan that refuses configuration **values** in this public
repository's documentation now runs on every pull request rather than only on a
maintainer's machine — worth having, since the README carried four such values once.

**What it costs.** §7: another repository can block merging here. And the list of siblings
is now something a contributor must keep in step with the workflow, enforced by tests they
may not have read.

**Where this will go wrong first.** Someone debugging a red build marks a download step
"ignore failures", or moves it out of `_siblings/`. Both are rules for that reason.

---

## What was tried and removed

An earlier version of this design also recorded, for each sibling, whether it was
**public** and the date that was last checked — with a rule pairing visibility against
whether the download used a credential.

A review found the pair circular. The `public` field was read by exactly one rule, and
that rule existed to protect the `public` field's verifiability.

**This is why §5's table runs G1, G2, G4, G5, G6, G7 with two numbers missing.** The
removed rules were **G3** (visibility must match whether a credential was used) and **G8**
(the date must be a plausible one). The remaining rules keep their original names rather
than being renumbered, so that anything written about "G6" still means G6. Nothing else consulted
either. Both were deleted on 2026-08-10 and no behaviour changed. The date field was worse
than useless: nothing could confirm the check had happened, so it manufactured confidence
rather than recording a fact.

Visibility now lives in a sibling's `note` — prose, where it belongs, because no test here
can verify it in any case. What still holds without the flag is simpler and needs no
field: a repository CI cannot read fails to download, and G5 keeps that failure loud.

Recorded because the removed design is more tempting than it looks, and because this
document once argued for it.

---

## Alternatives considered

**Leave it and rely on running the suite by hand.** The status quo for weeks. It works
exactly as well as one person's habits, which is not a property a safety check should have.

**Copy the facts here instead of reading them.** Rejected outright: copies of that
configuration registry were the platform's original failure, and the standing rule is that
it is referenced and never copied. A test reading a local copy compares a thing to itself.

**Ask GitHub whether a repository is public, from a test.** Rejected. It would be the only
network call in the suite, would need a credential to answer for private repositories —
the very thing in question — and would be unreliable exactly when a green build matters.

**Issue an access credential and download the private one too.** Rejected, and the
reasoning is [ADR-017](017_facts_across_a_private_boundary.md) §9 rather than anything here:
a credential is the wrong shape of answer to a standing category, and there is a route that
needs no credential at all.

---

## Appendix — checking it yourself

```
pytest -q
```

with the sibling repositories present is the full suite. Then:

```
VIEWS_APPWRITE=/nonexistent pytest -q
```

is what CI would see without the download — and it must **fail**, not merely skip. That is
§6.
