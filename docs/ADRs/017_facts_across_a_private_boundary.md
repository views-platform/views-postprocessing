# vpp_017 (ADR-017): Facts shared with a repository we cannot read

**Status:** Accepted

> **Cite this as `vpp_017` outside this repository.** views-models and views-crafdapi each
> have their own ADR-017 (*Forecast Sources, Composition, and Delivery*, and *Reference Data
> in Repository*), so a bare "ADR-017" resolves to the wrong document for a reader sitting
> in either of them (#264). The number is unchanged and every existing citation stays valid
> — the prefix is additive.
**Date:** 2026-08-10
**Decider:** Simon Polichinel von der Maase
**Scope:** what this repository does when it depends on a fact held in a repository it
cannot download — today because that repository is private, and in principle for any
reason. The companion decision, [ADR-016](016_ci_read_access_to_private_siblings.md),
covers repositories we *can* download.
**Related:** [ADR-003](003_authority_of_declarations_over_inference.md) (declarations over
inference), [ADR-013](013_sampled_forecast_wire_contract.md) §4.1a (the field in question),
[ADR-014](014_claims_and_the_guards_that_carry_them.md) §1 and §4

---

## The decision in one sentence

**A fact shared across a boundary we cannot see through is declared in a public place both
sides read, and neither side reads the other's source code.**

---

## Context

### §1 The failure this is about

When this repository delivers forecasts, it uploads each file with a label — a store
document field called `name`. The consuming API filters every one of its queries on that
label.

If our label and their filter ever stop matching:

- the upload **succeeds**;
- the file is stored, and paid for;
- the consumer's endpoint returns **empty**;
- **nothing, anywhere, raises an error.**

ADR-013 §4.1a states it plainly: a document uploaded under the wrong name is *"invisible to
the consumer, not merely degraded."* Every system involved reports success while the
partner receives nothing.

This is the failure mode that most deserves an automatic check, precisely because no human
or machine downstream will notice it.

### §2 Who owns the label, which is not what you would guess

ADR-013 §4.1a also says: the name is **"Config-owned by views-faoapi; changing it is a
contract amendment, not a deploy detail."**

So the consuming API owns the value. This repository holds a **copy** of it — the constant
`CONSUMER_DOCUMENT_NAME` in each partner's `product.py`, which is what we actually write
onto every upload.

That direction matters for everything below. The question is not *"can we see into their
repository"*. The question is **"they own a fact, we keep a copy, and how do we know the
copy is still right?"**

**One honest limit on that claim.** ADR-013 states the ownership only for the FAO API — its
table names *"the literal faoapi model name"*, and the CRAF'd partner arrived later and is
not mentioned there at all. So consumer-ownership is written down for one partner and
merely assumed for the other. §7 treats them the same, which is almost certainly right, but
"almost certainly" is not a citation. **Settling that is part of the registry work**: a
declaration naming both partners makes the ownership explicit for both, which is a second,
smaller reason to do it.

### §3 How we check it today, and why that stops working

The existing check opens the consumer's source, finds the name their API filters on, and
compares it with our copy.

That works when the consumer's code is on the same machine — true on a maintainer's laptop,
where all the platform repositories sit in one folder. It is impossible in continuous
integration when the consumer is private, because a CI job cannot download a private
repository without a credential.

So the check runs when someone happens to run it, and not on the change that would break
it.

### §4 Why this is a standing category and not a one-off

Two consuming APIs exist. `views-crafdapi` is public; `views-faoapi` is private. Across the
whole organisation, **15 of 33 repositories are private** — private is ordinary, not
exceptional.

The maintainer's instruction is explicit: `views-faoapi` may or may not become public one
day, but **there will be one or more private APIs at any given time**. So this document
must decide for the category, not for today's instance.

---

## Decision

### §5 The rule

> **A fact shared across a public/private boundary is declared in the public contract
> surface. Each side verifies itself against that declaration. Neither side reads the
> other's source code.**

The same thing as a picture:

```
                views-appwrite
             the registry (public)
                   "un_fao"

            ▲                     ▲
            │                     │
  views-postprocessing      views-faoapi
     writes the name        reads the name

        these two never read each other
```

**The arrow that is missing is the point.** Neither repository reads the other, so it does
not matter that one of them is private, and no credential is needed by anyone. Both arrows
point at a third place that is public to everybody.

Who does what, once and in one table:

| repository | its role | what it checks | needs access to |
|---|---|---|---|
| **views-appwrite** | holds the fact | nothing — it is the authority | — |
| **views-postprocessing** (here) | writes the name onto every upload | its own copy against the registry | the registry only |
| **views-faoapi** (private) | opens files with that name | its own served name against the registry | the registry only |

Concretely, for the delivery label:

1. The value is declared once, in the platform's public coordinate registry
   (`views-appwrite`, `docs/ADRs/platform/coordinate_registry.toml`) — **subject to
   views-appwrite accepting the registry as the home; the request is views-appwrite#75.**
   A store-document name is a contract fact rather than a coordinate, so admitting it
   widens that registry's charter, and that is not this repository's call to make. (That
   seat has since reviewed this document and agreed to implement it. The wording stands
   anyway: the decision should rest on its own reasoning, not on assent presumed in
   advance.)
2. **This repository checks its copy against that declaration.** No access to the consumer
   is required, so the check runs in CI on the change that could break it.
3. **The consuming API checks its own code against the same declaration.** It needs no
   access to us either — **because the registry is public**, not because this repository
   is. The consumer never reads us at all, which is the symmetry the rule is really about:
   neither side reads the other; both read a public third place.

### The order these land in is part of the decision, not an afterthought

**The obvious sequence has a hole, and it is green.** If step 1 lands, then step 2 replaces
the source-reading check with a registry read, and step 3 has not happened yet, the state
is: the registry declares a string a human typed; we check our copy against that string and
pass; the consumer checks nothing; and the check that *did* consult the consumer's real
source has been deleted. The build is green and what it proves is that **two values this
platform authored agree with each other.** That is strictly weaker than today, and it is
precisely the objection ADR-016 raises against copies — during that window the registry is
not an authority, it is a third copy, and nothing closes the loop.

So the sequence is constrained: **step 2 adds the registry check but does not remove the
source-reading one. The source-reading check is removed only when step 3 lands**, and until
then it keeps running wherever it can — in CI for the public partner, on a maintainer's
machine for the private one. Slightly redundant for a while, and redundancy is the correct
price for not having a window where the only thing verifying a delivery label is our own
typing.

**Erratum, 2026-08-12. The sequence above was followed, and the check was still the wrong
mechanism. Both facts belong here, and an earlier draft of this erratum got the first one
backwards.**

Both partners' step 3 landed. views-faoapi#379 closed on 11 August (commit `8615574`);
views-crafdapi#53 at 12:15 on the 12th (commit `0c493ae`). So the constraint stated above was **satisfied**, not
bypassed — and the first version of this erratum claimed the opposite, that "neither
partner's step 3 is what removed them". That was false when written, six hours after the
second one landed. It is corrected here rather than quietly, because an ADR that repeals
its own rule on a false claim about another repository is §3's failure inside §5's text.

**What actually happened is more useful than what that draft said, and it is checked
rather than asserted.** In both repositories the commit that satisfied step 3 was *the
same commit* that broke our source-reading check — verified: `8615574` and `0c493ae` each
introduce the named constant and add that repository's registry-binding test: each consumer, while binding its served name to the registry, tidied
`APIPathManager("literal")` into `APIPathManager(CONSUMER_DOCUMENT_NAME)`. The improvement
and the breakage were one edit. Twice, a day apart.

That is the argument for removing the check, and it is **§7's argument, not §5's**: we were
never entitled to depend on another repository's file layout, and a mechanism that a
consumer breaks by improving itself will keep breaking. The ordering rule above did its
job; the thing it was ordering was not worth having.

So the ordering constraint is not repealed — it is **discharged**, and superseded for this
class by a plainer rule: **a check that reads another repository's source is not a check
this repository builds.** The residual window is now permanent rather than temporary,
registered as **C-92**, and what closes it is each consumer proving its query uses the name
it declares — asked for in views-faoapi#390 and views-crafdapi#55, because that is a fact
only the consumer can hold.

**One assumption worth stating rather than relying on.** The registry is versioned, so the
two sides could in principle read it at different editions and both pass while disagreeing.
That is not a live risk here because the label is contract-immutable — changing it is an
amendment, which produces a new edition both sides re-pin to, and our pin's reachability is
already checked. Recorded because an unstated assumption carrying a silent-failure mode is
what §1 is about. *(Until 2026-08-12 the check also read the consumer's source and
skipped in CI; see the erratum above — that half is gone and its residual is C-92.)* The order the three land in, and what is blocked on what, is
Appendix B. Said here because a decision record that reads as a description of the code is
how this repository has repeatedly ended up believing work was done.

**"But you rejected copying."** [ADR-016](016_ci_read_access_to_private_siblings.md) turns
down keeping a local copy of the shared registry, on the grounds that a test reading a copy
compares a thing to itself. This is not that, and the difference is the whole point.

We keep a copy of the label because we have to — it is written onto every upload, so it
must exist in our code. What ADR-016 forbids is a copy that is *also the thing we check
against*. Here the copy is checked against an authority held elsewhere, which is what makes
the check mean something. A copy nobody verifies is the failure; a copy verified against a
declared authority is just a value with a source.

### §6 Why the coordinate registry, rather than somewhere new

Four reasons, and the fourth is the one that makes this cheap:

- **It is the right kind of place.** The registry already holds cross-repository facts
  about the delivery seam, already distinguishes secret entries from non-secret ones, and
  already records which repository consumes what.
- **It is public**, so a private consumer can read it without anyone granting anything.
- **It has a change process** and an amendment log, so a change to the label is a recorded
  contract amendment — which is what ADR-013 §4.1a already says it should be.
- **This repository's CI already downloads and reads that file on every run.** Adding this
  check costs no new machinery, no credential, and no new dependency.

A label is not a secret. Knowing that documents are named `un_fao` grants no access to
anything; access is controlled by keys held elsewhere. So this belongs with the non-secret
coordinates and must never be placed among the secret entries.

### §7 The rule applies to both partners, not only the private one

`views-crafdapi` is public, so our check *can* read its source, and does today. It will
move to the registry anyway.

The reason is not tidiness. If only the private case moves, the platform ends up with two
mechanisms doing one job — one reading a declaration, one reading source code — and a
future contributor has to know which partner uses which. One mechanism, applied uniformly,
is the point of having a rule at all.

It also means this repository stops reading any consumer's source, which removes a
dependency on another repository's *file layout* — something we were never entitled to
depend on.

**And it retires a download.** [ADR-016](016_ci_read_access_to_private_siblings.md) has CI
fetch `views-crafdapi`, and measurement shows that fetch serves **exactly one test** — this
one. Once the check reads the registry instead, that download buys nothing, and
`views-crafdapi` should be marked as not fetched, with a note saying why. Stated here
because a download that has quietly stopped earning its place is how the previous version
of all this went wrong, and because ADR-016 cannot know it: the decision that obsoletes it
is this one.

### §7a What a check in this repository may rest on

The rule §7 arrives at for one case generalises, and it is worth stating on its own,
because every defect this document's arc produced sat on the wrong side of it.

> **A check here may rest on a fact we own, on a fact another repository has *declared* in
> the public registry, or on an *outcome* we can observe. It may never rest on another
> repository's implementation.**
>
> Where a needed fact is none of those three, the check is not built here. It is requested
> as a declaration, requested as a consumer obligation, or registered as an accepted gap
> with a named owner and trigger.

[ADR-003](003_authority_of_declarations_over_inference.md) already says declarations over
inference. It was applied rigorously to the product and not at all across the repository
boundary, and that asymmetry is where the cost landed.

**The evidence, because this is a rule bought with two days.** The source-reading check
broke twice in twenty-four hours — views-faoapi on 11 August, views-crafdapi on the 12th
— each time because that repository refactored a literal argument into a named constant.
Verified: commits `8615574` and `0c493ae` each introduce that constant *and* add that
repository's registry-binding test. **The improvement and the breakage were one edit.**
A mechanism a consumer breaks by improving itself will keep breaking.

The corollary is the one that costs something to accept: when a fact is none of the three,
the honest move is to say so and register it, not to build a proxy. The delivery-label
composition is exactly that — see §8 and register C-92.

### §7b An ADR records a decision, and never the current state of the code

This document and [ADR-016](016_ci_read_access_to_private_siblings.md) both described what
the code did at the moment of writing — *"this is the shape the registry check now has"*,
*"today the check still reads the consumer's source"*. Every such sentence needed an
erratum the first time the code moved, and between them they produced nine stale claims in
two days, one of which repealed a rule in this document on a premise that was false by six
hours.

> **An ADR states a decision, its reasoning, and what would reverse it. It does not
> describe the current implementation.** Where a reader needs to know what the code does
> now, the ADR names the test or module that answers, and the answer lives there.

A decision record that doubles as a description of the code is a second copy of the code,
and it rots on a schedule nobody is watching. This clause is written into ADR-017 rather
than ADR-000 because it was learned here; if it survives contact with a second document it
belongs in the ADR conventions.

### §8 What this does **not** verify, stated plainly

This checks **our copy against the declaration**. It does **not** check the consumer's code
against the declaration.

So if the registry says `un_fao`, and we write `un_fao`, and the consuming API quietly
starts filtering on something else — our check passes, and the delivery is still invisible.

That half is genuinely the consumer's to verify, and cheap for it — it is the third item in §5's list, and needs no access to us because this repository is public. But it is
outside this repository's control, and there is a case where it may never exist: **a
private API operated by a third party**, who has no obligation to run any test of ours.

**In that case the fact is not verifiable from here, and must be recorded as such** — an
accepted blind spot with a named owner, not a check that quietly covers nothing. Pretending
otherwise would be the exact failure ADR-014 §1 exists to prevent.

### §9 What is deliberately not built

- **No access credential** — no personal access token, no machine account, no GitHub App.
  A credential solves one repository at a time and must be maintained forever, for a
  category that grows. It is the wrong shape of answer to a standing problem, and it puts a
  rotation obligation on one person.
- **No moving our checks into another repository's test suite.** It looks attractive —
  the private side can read us for free — but it fails on its own extension case: a
  third-party-operated API will not run our tests, and we would have no lever. A rule that
  breaks on its second instance is not a rule.
- **No new file, service, or endpoint.** If a fact does not fit the existing registry, that
  is information about the fact, not a reason to build a second surface.
- **No abstraction over "how to reach a private repository."** There is one such
  repository, and the decision above is that we do not reach it.

**Scope of the prohibition, narrowed after review.** Everything above is about **declarable
facts** — short values that can sit in a registry row. There is a second kind of shared
thing this rule does not reach: agreement about **behaviour**, such as whether two
independently written readers interpret a reserved entry the same way. You cannot put a
program's behaviour in a row, so §5's mechanism does not transfer, and a blanket "never a
credential" would leave that case with no answer at all.

The rule does extend, but one level up: **declare the semantics rather than the code** —
state in the contract what a reader must do, and each repository tests its own reader
against that statement. Still no repository reads another's source, and still no
credential. That question is live elsewhere as views-models#327 / D-05, and this document is
an argument for settling it there rather than here.

### §10 When to revisit

- **A shared fact that genuinely cannot go in the registry** — for instance one that is
  itself sensitive. Then this rule has met a case it does not cover, and the case is the
  evidence needed to decide the next thing.
- **A third-party-operated private API becomes a real consumer**, making §8's blind spot
  concrete rather than hypothetical.
- **The registry stops being public**, which would invalidate §6 entirely.

**Owner:** the maintainer. None of these is a deadline; each is an event.

---

## Consequences

**What this buys.** The check that guards the invisible failure runs automatically, on the
change that could cause it, for every partner — with no credential, now or ever, however
many private APIs appear. Adding partner number three costs one registry row.

**What it costs.** A change to a delivery label now requires editing a file in a third
repository. That is slower than editing a constant here, and deliberately so: ADR-013
already calls this a contract amendment rather than a deploy detail, and this makes the
process match the words.

**A dependency moves rather than disappearing.** We stop depending on the consumer's file
layout and start depending on the registry. That is a better dependency — declared,
versioned, public, with a change process — but it is not nothing, and if the registry
becomes unreliable this check inherits that.

**Where this will go wrong first.** Someone changes the label in the consuming API and not
in the registry. Our check keeps passing, because our copy still matches the declaration,
and the delivery goes invisible exactly as before. **That is §8, and it is the whole
residual risk of this design.** It is why the consumer-side check is part of the rule and
not an optional extra.

---

## Alternatives considered

### Issue an access credential so our CI can read the private repository

**Rejected.** It works, and it keeps both halves of the check in one place — genuinely its
strongest property.

But the brief is a permanent category. A token is tied to a person, expires, and must be
re-scoped for each new private repository; a GitHub App is a substantially larger piece of
infrastructure to own. Either way the cost recurs per repository and per rotation, forever,
to verify a handful of short strings. And when it lapses, the checks skip and the build
stays green — the exact failure the whole of ADR-016 was written to end.

### Move our check into the private repository's test suite

**Rejected**, though it was the leading candidate for some time.

The private repository can read this public one for free, so the check would cost no
credential and would fire in a real pipeline. Attractive, and correct today, when one
person maintains both.

It fails on the case that defines the category. A private API operated by a **third party**
will not run a conformance test on our behalf, and we would have no way to require it. The
rule would then hold only for repositories we happen to operate — which is not a rule about
private APIs, it is a rule about our own repositories wearing a general-sounding name.

### Accept the gap and check nothing

**Rejected as the destination, though it is the honest description of where we are until
the registry entry lands.** The failure it leaves uncovered is the invisible one, and this
repository has already delivered an artifact nobody could find once.

Worth stating because it is the fallback if the registry route stalls: the position would
then be *"this is not verified, here is the failure mode, here is who owns it"* — an
accepted blind spot, recorded. Never a check that appears to cover it and does not.

---

## Appendix A — the facts behind §4

Measured 2026-08-10. Counts drift; the commands do not.

```
gh repo list views-platform --limit 60 --json name,visibility
```
returned 33 repositories, 15 of them private.

Consuming APIs: `views-crafdapi` public, `views-faoapi` private. `views-productionapi` and
`views-publicapi` are named in platform records but do not exist yet, so no default
visibility can be inferred for future APIs.

## Appendix B — the work this decision requires, and in what order

1. **views-appwrite** — declare the label for each partner in the coordinate registry.
   Filed as views-appwrite#75. Nothing here can proceed before it.

   **Superseded 2026-08-11 — both rows now exist and both are in force.** This step used
   to say the CRAF'd label was "not a value anyone has decided yet" and should follow its
   data contract. views-appwrite declared both rows in v1.5.0, and the CRAF'd row states
   the correction itself: *"Both sides already use this value in code today — this row
   DECLARES a standing fact, it does not decide a new one."* It cites both sides' source.

   So step 1 is **done for both partners**, and step 2 covers both. What remains split is
   step 3, which is per-partner and is what step 2's retirement half waits on.
2. **views-postprocessing** — switch the check to read the registry rather than the
   consumer's source, for both partners. Ours, blocked on step 1.

   **Erratum, 2026-08-11 — this step used to say "in the same change, stop fetching
   `views-crafdapi` in CI", and that contradicted §5.** §5 constrains the order: a
   partner's source-reading check is removed only once *that partner's* consumer-side
   check exists. The crafd source-read is the sole consumer of the crafd fetch, so
   retiring the fetch retires the check — before views-crafdapi#53 has landed. The
   instruction and the constraint could not both be followed.

   Corrected: **retirement is per partner, and follows that partner's step 3.** For FAO
   that is now met (views-faoapi#379 merged 2026-08-11), so the FAO source-read goes. For
   CRAF'd it was not yet, so the crafd source-read stayed — and with it the crafd fetch.

   *(Superseded 2026-08-12. views-crafdapi#53 closed at 12:15 that day, and the crafd
   source-read was deleted anyway — not because the gate opened, but because the mechanism
   was wrong. Both fetch and check are gone; `tests/conftest.py`'s note records it. See the
   §5 erratum.)*
3. **views-faoapi** — verify its own served label against the declaration; §8's other half.
   Filed as views-faoapi#379, and the consumer-side maintainer has accepted it.

4. **views-crafdapi** — the same self-check for the other partner. Landed as
   views-crafdapi#53 (closed 2026-08-12), with the *query*-side ask filed the same day as
   views-crafdapi#55 alongside views-faoapi#390.

   The reasoning that made this leg necessary still stands: §7 retires the crafdapi fetch,
   so without it the CRAF'd label would be checked against a registry row that nobody
   checks against CRAF'd's actual code — no verification against reality at all, which is
   worse than the status quo. §7 argues the rule must apply uniformly; uniform application
   means uniformly filing the third leg.

**Step 3 was a precondition for removing the old check**, though never for adding the new
one — see the sequencing note in §5. The order was safe to interrupt at any point: until
step 3 landed for a partner, that partner's source-reading check stayed, so no window
existed in which the label was verified only against our own typing.

**That last sentence stopped being true on 2026-08-12, deliberately.** Both source reads
were deleted once the mechanism — not the ordering — was found wanting, so the window is
now permanent and carried as **C-92**. See the §5 erratum for why the constraint was
discharged rather than repealed.
