# Changelog

What changed **for a consumer** — the launcher that pins this package, and the partner
that receives its artifacts. Not a commit log: entries here name behaviour someone
outside this repository can observe, in particular **behaviour that can turn a
previously-passing run into a failing one**.

This file exists because the version number was the only signal a consumer got
(register C-111). Releases before 1.2.0 are summarised from their tags rather than
reconstructed in detail.

## 1.3.0 — 2026-09-19

**No new failure modes.** A launcher that ran 1.2.0 sees nothing new stop. This release
moves two dependencies across a major version and picks up a statistics fix; the delivered
bytes are unchanged.

### Dependencies a launcher will resolve differently

- **views-frames `>=2.0.0,<3`** (was `<2`). views-frames 2.0.0 is that package's first
  MAJOR: its frame constructors now type-check `index` and raise `TypeError` on a non-index
  where they previously constructed silently. This repository passes real indexes and is
  unaffected. **Delivery bytes are identical** — shards emitted through `views_frames.io.arrow`
  hash the same under 1.10.2 and 2.0.0 at the pinned toolchain, and the ADR-013 §10
  byte-parity fixtures pass under 2.0.0 in CI. Not a contract change.
- **views-pipeline-core resolves to 3.3.0** on a locked install (was 3.0.1). The declared
  range `>=3.0.0,<4.0.0` did not change; 3.3.0 is what lifted its own `views-frames <2` cap
  and made the move above possible. A `pip install` from the tag already resolved the newest
  3.x, so a launcher installing from git sees no difference here.
- **pyarrow stays at 16.1.0.** The `<17` ceiling is deliberate and owned by #174.

### Fix picked up from upstream

- views-frames 1.11.0 corrected the published MAP-containment law, which was wrong on
  **tied draws** — failing roughly 6% of rows on zero-inflated integer count posteriors,
  this platform's primary data shape. Moving past 1.10.2 brings it in. This repository
  volunteered to take that fix first.

### Documentation a reader of the code will notice

- Both products' `UPLOAD_ENABLED` docstrings previously named a precondition that had
  already been met — faoapi's C-161 closure notice (delivered 2026-07-20) and the
  views-crafdapi selection guard (deployed 2026-08-12). They now name the gate that actually
  holds: the non-production Appwrite decision, views-appwrite#171. **The interlock itself is
  unchanged and still closed.** Nothing uploads.
- `CRAFDPostProcessorManager` has an intent contract (`docs/CICs/`), stated as a delta
  against the UN-FAO one. The README and `docs/architecture/role_and_seams.md` list every
  `delivery/` module again, and a test now keeps them complete.

### Upgrading

Nothing to change in a launcher. Environments that hold `views-frames <2` for another
reason — views-evaluation's `[frames]` extra caps it — will refuse to resolve; this
repository requests neither that package nor that extra.

## 1.2.0 — 2026-08-26

**A previously-passing delivery can now fail in three new ways. All three are
deliberate, and each replaces a silent failure with a loud one.**

### New failure modes that escape into the launcher

- **`views_postprocessing.delivery.findability.DeliveryNotFindableError`** — after
  upload, the delivery now asks the store the same question the consumer asks: *is
  the newest document under the consumer's name the one this run just uploaded?* If
  it is not, the run raises. **Previously a delivery whose artifacts landed somewhere
  the consumer could not see reported success.** (C-94)

- **`…findability.FindabilityUnverifiedError`** — raised when the check itself could
  not run, e.g. the store errored on the read-back. Deliberately distinct from
  `DeliveryNotFindableError`: "could not ask" is not "asked and got nothing".

- **`views_postprocessing.contract.source_metadata.ProducerClientUnavailable`** —
  reading the producer's `last_valid_month_id` now raises if `datafactory_query`
  cannot be loaded, whether it is absent or raises on import. **Previously a broken
  environment degraded open and shipped unobserved months as observed history.**
  A producer that publishes no boundary is still handled as before — that is a normal
  older store, and a different condition. (C-103)

- **`views_postprocessing.contract.wire.sink.TornRunError`** — a failure partway
  through uploading a run now raises a refusal naming the run, every object confirmed
  uploaded, and the object that failed. It does **not** delete anything; a torn run
  still leaves orphans, but it no longer leaves them undocumented. Note this is a
  `RuntimeError`, not a `SinkError` — `SinkError` means do-not-retry, and a torn run
  may be retried. (C-105)

### Changed data reaching the partner

- **Delivered artifacts carry a new provenance field, `observed_through`.** It records
  the producer boundary the observed-range clip used, or `null` when the boundary
  could not be read and the clip was therefore **skipped** — meaning unobserved months
  may be present. Carried in the file's `description` metadata, which is a JSON string;
  consumers that treat that field as opaque text are unaffected. (#297)

### Changed internals a direct caller would notice

- `unfao.store_port` / `crafd.store_port` `upload()` now **returns the uploaded file
  id** instead of discarding it. Required by the findability read-back above.
- `delivery.provenance.build_provenance()` gained a **required** keyword argument,
  `observed_through`. Required rather than optional because a caller that omits it is
  the failure being fixed.

### Documentation

- ADR-013 gains **§5.1a**, recording that nullable int64 GAUL code columns were
  considered and rejected, with the measured pandas round-trip behaviour that decided
  it. No `contract_version` change: the wire bytes are untouched. (#278)

### Upgrading

Nothing to change in a launcher. The three new exceptions surface conditions that were
already wrong and already silent — if one fires after upgrading, it is reporting a
pre-existing problem, not creating a new one.

## 1.1.1 — 2026-08-15

Fixes C-99. Consumers on 1.1.0 should move; see views-models#403.

## 1.1.0 — 2026-08-13

Adds the CRAF'd producer package alongside UN-FAO, and the observed-range clip that
drops months above the producer's declared boundary.

## 1.0.0 — 2026-08-01

First released version.
