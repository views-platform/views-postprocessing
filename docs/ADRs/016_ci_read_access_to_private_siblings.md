# ADR-016: Cross-repository checks in CI, and how siblings declare their visibility

**Status:** Accepted
**Date:** 2026-08-10
**Decider:** Simon Polichinel von der Maase
**Arises from:** register **C-46**, **C-57**, **C-81**, which all carried the same standing
residual: the cross-repository drift detectors ran only on a maintainer's laptop
**Related:** [ADR-003](003_authority_of_declarations_over_inference.md) (declarations over
inference), [ADR-014](014_claims_and_the_guards_that_carry_them.md) §2 (a guard nobody has
watched fail is decoration) and §4 (a deferral names a trigger and an owner)

---

## Context

### §1 Some of this repository's tests are about other repositories

Most tests here check our own code. A few check something else: whether **claims this code
makes about other repositories are still true**.

The clearest case is the shared Appwrite coordinate registry. Each partner's
`appwrite_env.py` declares, in two constants, which edition of that registry it was written
against. That is a claim about a *different repository*. A test opens that repository, reads
the real edition, and compares.

This is not theoretical maintenance. On 2026-08-05 the check failed: the registry had moved
from v1.4.1 to v1.4.4 while nobody here was looking. Two days earlier, the same family of
checks fired **twice in one day**. A claim about another repository goes stale at *that*
repository's pace, and nothing in this repository's own code can notice.

### §2 They only run where the other repository is on disk

`tests/conftest.py::sibling_repo` resolves a sibling by a declared environment variable and
falls back to the conventional `../<name>` directory. When neither resolves it returns
`None` and the test **skips** — correctly, because on a laptop a missing sibling is normal.

A GitHub Actions job gets a checkout of **one** repository. So in CI they skipped, and
**continuous integration verified strictly less than a laptop did, precisely on the checks
that cross a repository boundary**.

### §3 Why they stayed dark, which is the more interesting failure

Four siblings, and until now the decision about which ones CI could fetch lived in a
**comment** in the workflow file. That comment said `views-appwrite` was private.

It is not. It was made public on **2026-08-08** — a deliberate, recorded act in that
repository (`views-appwrite@9d80b75`, *"docs: record going public"*). The comment did not
change with it, so seven checks went on skipping in CI for no reason whatsoever.

The first draft of this very document, written on 2026-08-09, proposed issuing a credential
to reach those seven — **one day after the fact that justified it had ceased to be true**.
That is not an embarrassing footnote to the decision below; it *is* the argument for it. A
fact about another repository, recorded in prose, with no date and nothing able to check it,
will be wrong and nobody will find out.

---

## Decision

### §4 Every sibling is declared, and the declaration separates fact from decision

`tests/conftest.py` declares each sibling repository with four fields:

| field | kind | meaning |
|---|---|---|
| `env` | declaration | the environment variable that overrides its location |
| `public` | **fact** | its visibility on GitHub — not ours to decide |
| `public_checked` | **fact** | the ISO date that visibility was last verified |
| `ci_checkout` | **decision** | whether CI fetches it |
| `note` | reasoning | why not, required whenever `ci_checkout` is false |

Separating `public` from `ci_checkout` is the point. One is a fact about the world, the
other is a choice we make; §3 is what happens when a single sentence tries to be both. And
`public_checked` is not decoration — every measured claim in this repository carries a date,
and a bare boolean is a fact with no expiry.

### §5 CI fetches exactly what the declaration says, and a test enforces the agreement

`.github/workflows/run_pytest.yml` checks out every sibling declared `ci_checkout=True`, into
`_siblings/`, pointed at by the declared environment variable.

`tests/test_ci_sibling_coverage.py` fails when the workflow and the declaration disagree **in
either direction** — a declared checkout that is missing, or a checkout nobody declared. Each
rule is a pure function of `(workflow, siblings)` so it can be run against a synthetic broken
world; a rule that can only be demonstrated by editing CI is one nobody ever watches fail.

Today that means `views-appwrite` and `views-crafdapi` are fetched. `views-datafactory` is
public but is **not** fetched: its checks need raw GAUL parquet files that are not in its git
repository, so checking it out replaces an honest skip with a crash — measured, tried and
reverted. `views-faoapi` is the one genuinely private sibling.

### §6 A missing sibling that CI declared must turn the build red

Skipping is right on a laptop and wrong in CI once we have declared the repository should be
there. If a checkout silently fails, the checks skip, the build stays green, and we are back
to §2's blindness while looking fixed.

The mechanism already existed:
`tests/test_env_declaration.py::test_no_sibling_override_points_at_a_missing_path` fails when
a declared variable is set but resolves to nothing. Because the workflow sets those variables
unconditionally, a failed checkout is a **red build**. Naming it here so nobody deletes it
believing it to be tidiness.

That guard had a hole, closed in the same change: it treated a variable set to the **empty
string** as unset, which is exactly what a YAML interpolation resolving to nothing produces —
so the likeliest CI misconfiguration was the one case it could not see. (`Path("").exists()`
is `True`, so the obvious fix makes it worse.)

### §7 `public` is verified by CI doing it, not by a test — and two rules keep that true

No test in this suite touches the network. That is a deliberate convention, not an oversight:
what these tests locate is a working copy on disk.

So `public` is verified by **the checkout itself**. The default `GITHUB_TOKEN` is scoped to
this repository, so a tokenless fetch of a sibling declared public *fails the build* if it is
actually private.

Two rules exist solely to keep that argument load-bearing, and both look like fussiness until
you see what they protect:

- a checkout of a **public** sibling must **not** pass a credential — add one to dodge a rate
  limit and the field silently becomes an unchecked claim;
- no sibling checkout may carry `continue-on-error` — one key and a failed fetch stops
  failing the build.

**The reverse case is not detected.** A private sibling that quietly becomes public will go on
being declared private, and nobody here will notice. That is stated rather than papered over;
it costs a stale `note` and an unnecessary skip, not a wrong result.

### §8 The credential for the one private sibling is deferred

`views-faoapi` is private, and reaching it needs a credential. That is **not** done here.

The cost/benefit is thin: it is **one** test. It is, admittedly, the most valuable single one
— it checks that our delivery is filed under the name the consumer actually filters for, and
that failure produces *no error anywhere*: the upload succeeds, storage is paid for, and the
consumer's endpoint is simply empty. But one test does not justify a credential tied to one
person, with an expiry somebody must track, while a better answer is pending.

**The better answer being pursued:** asking FAO to consent to that repository being made
public, which removes the need entirely. An audit of its full history found no credentials of
any kind and no partner staff email addresses; it already carries an MIT licence. Two items
remain open — internal storage identifiers appear in 21 tracked files, and whether GAUL 2024's
terms permit redistribution.

**Named trigger (ADR-014 §4).** Issue the credential when **either**: FAO declines, or a
**second** private sibling appears. **Owner:** the maintainer. Should it ever be issued, the
scope floor is one repository, read-only, with a deliberately chosen expiry — the default of
30 days would put this repository back in the dark within a month, with a green build
throughout.

---

## Consequences

**What this buys.** Seven cross-repository checks move from *"run when a maintainer happens to
run them"* to *"run on every change"*. Two of them fired in anger in the week before this was
written. One test also changes character: the scan refusing registry **values** in this public
repository's markdown now runs on every pull request rather than only on a maintainer's
machine — worth having, since README.md carried four such values once already.

**What it costs.** CI now depends on two other repositories being fetchable, so an outage or a
visibility change there turns this repository's build red. That is the intended trade: a red
build is the honest signal, and §6 exists to make sure it is what happens.

**Where this will go wrong first.** Somebody debugging a red CI adds `continue-on-error` to a
sibling checkout, or a `token:` to make a rate limit go away. Either quietly dismantles §7.
Both are rules in `test_ci_sibling_coverage.py` for that reason.

**Second most likely.** A sibling checkout is added to a different workflow file and escapes a
rule scoped to `run_pytest.yml`. The declaration check scans every workflow, not one.

---

## Alternatives considered

**Leave it, and rely on running the suite by hand.** The status quo, and what registers C-46
and C-57 carried as an open residual for weeks. It works exactly as well as one person's
habits, which is not a property a safety check should have.

**Vendor the facts instead of reading them.** Copy the registry edition into this repository
and check the copy. Rejected outright: copies of that registry were the platform's original
failure, and the standing rule is that it is referenced by pinned URL and never copied. A test
reading a local copy compares a thing to itself.

**Check `public` against the GitHub API from a test.** Rejected. It would be the only network
call in the suite, would need a credential to answer for private repositories — the very thing
under discussion — and would be flaky in exactly the conditions where a green build matters.
Verification-by-doing (§7) is weaker but honest, and its limits are written down.

**Issue the credential now and fetch all four siblings.** Rejected on the arithmetic in §8: it
buys one test, and a decision that may make it unnecessary is outstanding.

---

## Appendix — reproducing the measurement

Counts drift as tests are added; the command does not. From the repository root:

```
pytest -q
VIEWS_APPWRITE=/nonexistent pytest -q -rs
```

The first, with the sibling repositories present, is the full suite. The second is what CI
would see without the checkout — and it must **fail**, not merely skip. That is §6.
