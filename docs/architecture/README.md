# Documentation architecture

This directory holds the **orientation documentation** for views-postprocessing — the
docs that explain *what this repo is, how it relates to the rest of the platform, and
where its internal seams are*.

This file is the **S1 decision record** for the documentation truth-up epic
(views-postprocessing#70). It fixes two things once, so the downstream stories (S2–S5)
don't each re-decide them.

---

## 1. Information architecture — what each document is for

Each kind of knowledge has **one** home. No document repeats another's job.

| Document | Single responsibility | Story |
|----------|----------------------|-------|
| `README.md` (repo root) | Install + quickstart + a short "what is this" + **pointers** out to the docs below. Not the place for deep role/seams explanation. | S3 (#73) |
| `docs/architecture/role_and_seams.md` | The repo's **role vs the sibling repos** (datafactory → pipeline-core → vpp → faoapi) and its internal **seams** (`delivery/` invariants vs `unfao/extraction.py`; the inherited pandas base & C-40; the draws/frames contract). The doc a newcomer reads first. | S2 (#72) |
| `docs/ADRs/` | **Decisions + rationale** (immutable records). What was decided, why, what it supersedes. | S4 (#74) |
| `docs/CICs/` | **Class-level contracts** (intent, guarantees, failure modes) for non-trivial classes. Already current (refreshed in #66/#68). | — |
| `docs/architecture/` (this dir) | Cross-cutting orientation that is not a single decision (role, seams, package map) and this index. | S2/S5 |

Anything that does not fit one of these has no home yet — add it deliberately, don't
wedge it into an existing doc.

---

## 2. ADR-supersession policy (decided 2026-06-27)

**Decision:** when an Accepted ADR is invalidated by a later change, **write a new
superseding ADR** rather than rewriting the old one. The old ADR stays intact as a
historical record with its status changed to `Superseded by ADR-NNN`.

**Rationale:** ADRs are immutable decision records (ADR-000). Rewriting an Accepted ADR
in place destroys the historical "what we believed then and why" that makes the record
useful. `ADR-004` ("rules for evolution and stability") is Deferred, so this record sets
the convention in the interim.

**Application (S4 / #74):**
- `ADR-001` (ontology) — invalidated by `ADR-011` (mapper → lookup). Leave its text
  intact; set status to **`Superseded by ADR-012`**.
- Write **`ADR-012`** with the *current* ontology (the categories that actually exist:
  the `delivery/` representation-free invariants, the `unfao/extraction.py` seam, the
  manager as a thin pipeline-core subclass, the GAUL lookup asset, derived parquet
  outputs). `ADR-012` records `Supersedes: ADR-001`.
- `ADR-002` (topology) is **extended in place** (not superseded) — it was incomplete,
  not wrong: add the sibling-repo topology + dependency direction + a pointer to
  `role_and_seams.md`.

---

## 3. What the downstream stories produce

- **S2 (#72)** → `docs/architecture/role_and_seams.md`
- **S3 (#73)** → rewritten `README.md`
- **S4 (#74)** → `ADR-001` status change + new `ADR-012` + `ADR-002` extension + ADR index note
- **S5 (#75)** → refreshed `unfao/managers/README.md` + a package/module map
- **S6 (#76)** → a doc-accuracy guardrail so none of the above silently re-stales
