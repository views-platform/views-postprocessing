# ADR-015: Why this repository imports another project's Appwrite client

**Status:** Accepted
**Date:** 2026-08-04
**Decider:** Simon Polichinel von der Maase
**Arises from:** issue [#146](https://github.com/views-platform/views-postprocessing/issues/146),
recorded at the request of the þing-02 ratification
**Related:** [ADR-002](002_topology_and_dependency_rules.md) (dependency direction),
[ADR-009](009_boundary_contracts_and_configuration_validation.md) (boundary contracts),
[ADR-014](014_claims_and_the_guards_that_carry_them.md) §4 (a deferral needs a trigger),
register **C-40**

---

## Context

Each partner manager in this repository begins with two imports it would rather not have:

```python
from views_pipeline_core.modules.appwrite.file import AppwriteConfig
from views_pipeline_core.modules.datastore import DatastoreModule
```

They reach into another project's Appwrite client — its auth handling, its provisioning
behaviour, its error semantics — and run it under this repository's identity and this
repository's API key. When that client does something surprising, it surprises FAO's
delivery, and the fix is in a repository this team does not own.

This is knowingly kept. It has been raised repeatedly: register **C-40** carries it as a
Tier-2 concern, a cross-repository assembly examined it in July 2026 and told the platform
not to export the surface, and issue #146 tracks the eventual removal. None of that has
changed the code, and it should not have — but the *reason* has been recorded only in a
GitHub issue and in a deliberation folder outside this repository. A closed issue is not
where architectural reasoning survives. That is what this ADR is for, and writing it was
the condition attached when the deferral was ratified.

**The word "deferred" is doing real work here and is easy to misread.** It does not mean
*not done yet*. It means: examined, decided, and held — with a stated condition under which
the decision is revisited. The distinction matters because the two read identically in an
issue tracker and completely differently to someone deciding whether they may change it.

---

## Decision

### §1 The import stays, because there is nothing to unwind to

The obvious alternative is to write our own thin Appwrite client and drop the dependency.
We do not, for a reason that is about the platform rather than about this repository:
**a third copy of that client is the disease, not the cure.**

Two hand-written copies already exist across the platform, and the defect that prompted the
cross-repository examination was common to both — not a divergence between them, but the
same mistake made twice. Adding a third copy here would multiply the surface the platform
is trying to shrink, and would do it in the repository that talks to the partner.

The upstream project declines to export a supported client surface, and that refusal is
deliberate: exporting the current one would bless a shape its own maintainers have recorded
as needing decomposition. So the honest position is that the seam to unwind *to* has not
been built yet, by anyone, and building it unilaterally here would be worse than waiting.

### §2 What bounds the blast radius while it stays

A dependency kept on purpose still has to be contained, and this one is:

- **Only the partner managers import it.** `tests/test_doc_accuracy.py` pins the importer
  set to an explicit allowlist, so a third importer fails CI. Every other module —
  the whole of `contract/` and `delivery/` — is free of it, proven in a fresh interpreter
  by `tests/test_clone_readiness.py`.
- **The store is behind a port.** `_ContractStorePort` wraps the client in four methods, so
  the wire modules never see Appwrite types. That is the dependency-inversion half of
  C-40's prescribed mitigation, and it is the half that landed.
- **The framework contract is asserted.** `tests/test_framework_contract.py` checks that the
  hooks we override still match upstream, that the classes remain instantiable, and that
  every inherited attribute resolves — so an upstream change is found here rather than on a
  delivery run.

None of that removes the coupling. It makes the coupling *one file per partner wide* and
*visible when it moves*, which is the most that can be true while §1 holds.

### §3 The condition under which this is revisited

Two independent things can move, and they were ratified as a pair:

- **Demand** — a second incident whose root cause is auth or provisioning handling in
  duplicated client code, whether from divergence between copies or from a defect common to
  them.
- **Supply** — the upstream project carving the auth and configuration seam out of its
  Appwrite module, so that something exists to depend on.

**Either one alone means revisit. Both together mean do it.** The deferral is tied to that,
explicitly *not* to this team's convenience — which is the wording the assembly chose, and
it is worth keeping because "when we get round to it" is how a deferral becomes a decision
nobody made.

### §4 Where supply actually stands, which is not where the record says

The verdict was written when the upstream Appwrite module was a single 3,064-line file. As
of the version this repository now pins, that has **partially** moved: provisioning has been
relocated to its own module, transport (including the request timeout this repository
depended on) to another, and an audit package now exists alongside. The main file is 2,841
lines.

**So the supply half has started and has not fired.** What we import is still there, and
there is still no exported client to depend on instead. But "no movement" would be the wrong
thing to believe, and a reader checking this in six months should check the module list
rather than trust this paragraph.

### §5 Scope: this is two files now, not one

The deferral was written when one manager held the import. The CRAF'd partner package added
a second, and it is a near-verbatim copy of the first. So the adapter to unwind is two
adapters with identical contents, and any fix must be applied twice or neither.

That is not an argument to unwind sooner — it is the same bounded surface duplicated, and
register **C-33** already carries the duplication with its own trigger. It is recorded here
so that whoever eventually does the work is not surprised by the second file.

---

## Consequences

**What this costs.** Upstream changes land in FAO's delivery without this repository owning
the fix; the managers cannot be instantiated without the framework; and the platform's most
central package remains a hard dependency of the thing that talks to the partner.

**What it buys.** No third client copy. The whole of `contract/` and `delivery/` stays
framework-free and reusable, which is what let a second partner be added as a package rather
than a fork.

**Where this will go wrong first.** Someone reading issue #146 will see "deferred", read it
as "not done yet", and either do it — writing the third copy §1 exists to prevent — or treat
the import as unexamined and add a third importer. The allowlist test catches the second.
Nothing catches the first except this document.

---

## Alternatives considered

**Write our own thin client now.** Rejected in §1: it is the third copy, and it puts the
duplication in the repository with the partner relationship.

**Wait silently and leave the reasoning in the issue.** This is what was happening, and it is
what the ratification objected to. An issue is a work item; it is not read by someone
deciding whether a rule applies to them.

**Bound it with a test and consider it closed.** The allowlist and the port genuinely reduce
the risk, and it is tempting to call that the end. Rejected because containment is not
removal — C-40 stays open on exactly the residual this ADR describes, and closing it would
mean the next reader finds a bounded coupling with no record of why it is tolerated.

---

## Appendix — the record this replaces

The reasoning above was previously recorded only in issue
[#146](https://github.com/views-platform/views-postprocessing/issues/146) and in the
platform's deliberation folder (`views_platform/þingit/`), which is outside this repository
and not on any contributor's path.

Two related facts, verified 2026-08-04 and recorded here because they are otherwise only in
that folder:

- **The sibling obligation from the same verdict is discharged.** The assembly also required
  this repository's legacy delivery path to be guarded or retired before 2026-11-30. It was
  retired in #149 — the manager carries no such path, and register C-63 is resolved. The
  deadline is moot here, and nobody had recorded that it was met.
- **`C-221` is the upstream project's register entry, not an issue number.** Issue #221 in
  that repository is unrelated and closed. The entry is Tier 4 and describes the
  decomposition need in §3's supply component. Cross-repository identifiers in this
  repository are namespaced for exactly this reason
  (`tests/test_register_integrity.py` enforces it), and the verdict's own shorthand is not.
