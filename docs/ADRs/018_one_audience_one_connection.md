# vpp_018 (ADR-018): One audience, one connection — and never a fallback to the shelf

**Status:** Accepted

> **Cite this as `vpp_018` outside this repository.** Several sibling repositories number
> their own ADRs in the same range, so a bare "ADR-018" resolves to the wrong document for
> a reader sitting in one of them. This repository has been bitten by exactly that: a
> dependency comment here cited "ADR-047", which names no document in this repository and
> already resolves to views-datafactory's in our own risk register.

**Date:** 2026-11-27
**Decider:** Simon Polichinel von der Maase
**Scope:** how a delivery addresses the two Appwrite projects it touches — the shared store
it reads from, and the partner's own store it writes to — and what happens when that
addressing is wrong.
**Related:** [ADR-003](003_authority_of_declarations_over_inference.md) (declarations over
inference), [ADR-008](008_observability_and_explicit_failure.md) (log *and* raise),
[ADR-009](009_boundary_contracts_and_configuration_validation.md) (configuration
validation), [ADR-012](012_revised_ontology.md) (which package this belongs in),
[ADR-014](014_claims_and_the_guards_that_carry_them.md) §2 (a guard must be able to fail).
Issue #327; registry edition v1.9.1 at views-appwrite `a251cb8`.

---

## The decision in one sentence

**A delivery holds two separate connections — one per Appwrite project — and if the
partner's own connection cannot be proven distinct from the shared one, the delivery
refuses rather than writing anywhere.**

---

## Context

### §1 Two stores, and for ten days one project

A delivery reads a finished forecast run out of a store shared by the whole platform, and
writes the partner's copy into a store belonging to that partner. Until 2026-11-11 both
lived in the same Appwrite project, so "two stores" meant two buckets and one connection
was enough.

On 2026-11-11 the operator created a project of its own for the CRAF'd audience, and the
consuming API, `views-crafdapi`, was pointed at that project and only that project. This
repository was not changed. So the code held one connection, addressing the shared project,
and would have written the partner's copy into a place the partner could not read.

Nothing would have reported it. The upload succeeds, the metadata row is written, the
delivery's own verification reads back the file it just wrote — in the wrong project —
and three separate surfaces agree the delivery is missing: the consuming API's empty
response, the platform's liveness monitor, and an operator looking in the bucket they
expect. All three correct about the symptom and none of them naming the cause.

### §2 The shape an absence check cannot see

Every coordinate this repository reads is already checked for being declared and non-empty.
That check cannot see the failure that actually happens, which is **two coordinates both
present and both holding the same value** — because the partner's slot was filled with the
shared project's value, or because a launcher exported one name and not the other and
whoever fixed it reached for the nearest match.

That is a fallback with nothing missing. It is indistinguishable from a working
configuration at every later step, and it puts one partner's data where another partner's
key can read it.

---

## The decision

### §3 Two connections, declared separately

A connection is **an endpoint, a project id and a credential**. Each project this
repository addresses gets its own named triple in `<partner>/appwrite_env.py`, and the
names are minted by the platform's coordinate registry, never invented here.

A credential belongs to exactly one connection. An Appwrite API key authenticates against
exactly one project, so sharing one credential across two connections is not an economy —
one of the two connections cannot work.

### §4 No fallback, ever

If the partner's project id is absent, blank, or equal to the shared project's — or if the
two credentials are equal — the delivery **refuses before any byte moves**. It does not
fall back to the shared project, and it does not degrade to a warning.

This is the whole decision, and the reason it is a decision rather than a preference: a
fallback is the failure. Writing to the shared project *is* what we are trying to prevent,
so a fallback that writes there converts a refusal into the exact outcome.

### §5 A refusal names the coordinate and prints no value

The refusal names the **coordinate names** the operator must compare, the consumer whose
delivery stopped, and nothing else. Project ids are not secrets, but this repository is
public and its CI logs are world-readable, so no value is printed — not the ids, and
certainly not the credentials, whose comparison needs no printing.

Every refusal is **logged at ERROR and raised** (ADR-008). Neither substitutes for the
other: the raise halts the run, the log is what survives in the launcher's output after the
process is gone. Without both, a mis-wired connection leaves a *quieter* trace than a
working one.

### §6 The rule is checked where the client is built, not only in a unit

The rule lives in partner-neutral machinery under `contract/` — ADR-012 puts *how a
delivery is built* there, and nothing has been delivered when this refuses. It takes
strings and a name, so it is testable with no environment and no Appwrite client, and a
second partner gets it for free.

**That is not sufficient, and the first implementation proved it.** The rule shipped with
nine passing unit tests and no test asserting the configuration the manager actually built.
Deleting the call from the manager, transposing its two project ids, or repointing the
built client at the shared project each left the whole suite green. A rule nothing binds to
its call site is a rule the next refactor removes silently — this repository's register
calls that *"a guard that cannot fail"*.

So the binding requirement is: **assert on the object that carries the decision.** For this
rule that means the built client configuration, and the test must fail when the call is
removed. Every parameter is keyword-only for the same reason — four same-typed strings from
four similarly spelled coordinates can be transposed, and a symmetric equality check passes
when they are.

---

## Consequences

**A partner costs one more declaration.** Cloning a delivery for a new audience adds a
second connection triple to that partner's declarations, and the rule itself is reused
unchanged. `docs/CLONING.md` carries the step.

**A delivery cannot be armed against the shared store even deliberately.** There is no
flag and no override. If a future delivery genuinely needs to write to the shared project,
that is a change to this document first.

**Two projects means two expiries.** Each connection's credential is a separate key with
its own lifetime, and the expiry tripwire must name the path each one carries — otherwise
the first warning sends the operator to rotate a key that has not expired.

**The container coordinates are reused across both connections.** Bucket, collection and
metadata-database names are the same strings in either project; only the project moves.
That is deliberate and it is also the one claim in this decision that is *not* enforced by
anything here: whether those containers exist under the partner's project is a fact about
the other side, and it is established by the coordinate registry recording a measurement,
not by this repository.
