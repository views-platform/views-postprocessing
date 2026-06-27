# Role & seams: what views-postprocessing is, and how it fits

> **Read this first.** If you are new to this repo — or you've worked here a while and
> still aren't sure where its job ends and pipeline-core's or faoapi's begins — this is
> the orientation document. It explains *what this repo is*, *its place in the platform*,
> and *its internal seams*. The README is install + quickstart; this is the mental model.

---

## 1. One sentence

views-postprocessing takes finished VIEWS forecasts, **enriches them with geographic
metadata, guards their integrity, and delivers them to a partner store** — it is a
**post-forecast delivery layer**, not a spatial-mapping library and not a statistical
post-processor.

The only live consumer today is the **UN FAO** delivery (`views_postprocessing/unfao/`).

---

## 2. Where it sits in the platform

The platform is a one-way pipeline. Data and dependencies both flow **down**:

```
views-datafactory        produces the data (features, actuals) as frames/parquet
        │
        ▼
views-pipeline-core      the FRAMEWORK: lifecycle, data loader, dataset container,
        │                Appwrite/datastore tools, ensemble + forecasting managers
        ▼
views-postprocessing     THIS REPO: post-forecast delivery + input-integrity
        │                (a concrete pipeline-core postprocessor)
        ▼
views-faoapi             the SERVING API: reads the delivered store, collapses draws,
                         serves FAO
```

- **views-models** is the *runner / composition root*: its `postprocessors/un_fao/main.py`
  constructs this repo's manager and calls `.execute()`.
- **Dependency direction is strictly down.** This repo `import`s pipeline-core; **pipeline-core
  does not import this repo** (verified: zero imports — the only mentions in pipeline-core are
  comments asserting "no cross-repo cycle"). So this repo is a *consumer/extension* of
  pipeline-core, never a dependency of it.

---

## 3. What this repo *is* — a pipeline-core postprocessor

`UNFAOPostProcessorManager` **subclasses** two pipeline-core base classes
(`PostprocessorManager`, `ForecastingModelManager`). This is the **Template Method**
pattern:

- pipeline-core's base defines the **skeleton**: `execute()` calls the lifecycle steps
  `_read → _transform → _validate → _save` in order.
- this repo **fills in the steps** for the FAO path (the `_read*/_transform/_validate/_save`
  overrides in `unfao/managers/unfao.py`).
- pipeline-core also **provides the tools** the steps use: `ViewsDataLoader`, `PGMDataset`,
  `DatastoreModule`, `AppwriteConfig`, the path managers.

So the runtime control flow is *inverted* ("don't call us, we'll call you"): views-models
calls `manager.execute()`, which lives in **pipeline-core's base**, which calls back into
**this repo's** overridden hooks. pipeline-core "runs this repo's code" only by dispatching
into a subclass instance it was handed — not by depending on it.

**Consequence to internalise:** because this repo *is-a* pipeline-core postprocessor, it
**inherits pipeline-core's data representation** (pandas). It does not get to pick its own.
That single fact explains most of section 5.

---

## 4. What it does to the data (and what it deliberately does not)

The post-forecast slot, for the FAO path, is **delivery + integrity** — not statistics:

| Stage | Method(s) | What actually happens |
|-------|-----------|-----------------------|
| Read | `_read_historical_data`, `_read_forecast_data` | Historical actuals from datafactory (via the inherited loader); the forecast file from the Appwrite prediction store. |
| Transform | `_transform` → `_append_metadata` | **Joins GAUL metadata** onto each frame (`GaulLookupEnricher`, a parquet lookup). It does **not** transform prediction values. |
| Validate | `_validate`, `_check_coverage` | Null-gate on the 9 metadata columns; region coverage + excluded-cell guards. |
| Clip | `_clip_observed_history` | Drops fabricated zero-padded tail months from the *historical* actuals (the forecast is untouched). |
| Save | `_save` | Writes parquet, uploads to the FAO bucket with structured provenance. |

**The statistics live downstream — by design:**
- **Draw collapse** (MAP / HDI / scenario summaries) happens in **views-faoapi**
  (`views_frames_summarize`), once, at the edge.
- **Reconciliation** lives in `views_frames_reconcile` (the views-frames sibling) — it is
  not in this repo (see `docs/reconciliation_migration.md`).

This repo must **preserve** the forecast values uncollapsed and hand them on. A "fat"
statistical postprocessor here would be the bug, not the goal.

---

## 5. The seams (the part that's easy to get lost in)

There are three seams worth holding in your head.

### Seam A — invariants vs representation

The input-integrity guards are split into **two homes** on purpose:

- `views_postprocessing/delivery/` — **representation-free invariants**. Primitives only
  (sets of ints, numpy arrays, scalars, dicts). **No pandas, no views_frames.** Each is a
  pure rule that raises or passes: `coverage.py`, `identity.py`, `observed_range.py`,
  `provenance.py`.
- `views_postprocessing/unfao/extraction.py` — **the representation seam**. The *only*
  pandas-aware module the invariants are fed from. It turns the pandas frame into the
  primitives the invariants consume.

The manager **calls** the invariants; it never makes them methods of itself. The pattern is
always `extract (seam) → call invariant → raise`. This is why the guards are testable
without the framework, and why they survive a representation change untouched (only the seam
changes — see Seam B).

### Seam B — the inherited pandas base, and the C-40 gate

Because this repo *is-a* pipeline-core postprocessor (section 3), three **concrete** pandas
pieces are inherited, not chosen:

1. the input loader (`ViewsDataLoader` → parquet → pandas),
2. the dataset container (`PGMDataset`, a pandas `DataFrame` with object-dtype cells),
3. the prediction-store parquet I/O.

So **a views-frames frame cannot flow end-to-end through this repo today.** Data enters as
parquet→pandas and leaves as parquet. The only views-frames code here is
`unfao/frames.py` — an *unused conformance adapter* (it converts pandas → frame to prove
the data satisfies the views-frames contract, but the live path never calls it).

This is **register C-40**. Closing it is upstream epic work in pipeline-core (a frame input
loader, a frame container, frame store I/O) — not something this repo can do alone. The half
*this* repo owns is keeping the invariants representation-free (Seam A), so the eventual swap
is a one-seam change.

### Seam C — points vs draws (uncertainty)

The delivery is moving from **point estimates** to **predictions-with-uncertainty** (S
samples per cell). This is where representation matters most:

- views-frames stores a distribution natively as a contiguous `(N, S)` float32 array (sample
  axis explicit; a point is just `S=1`).
- pandas `PGMDataset` stores it as **object-dtype list-in-cell** — a separate numpy array
  boxed in each of N cells. Cost scales ~linearly with S (memory, an encode/decode tax at
  every parquet/API boundary, a silent resize on mismatched sample counts).

Today this repo ships **point-shaped** data (`pred_*_best` / `pred_*_prob`); its
`unfao/frames.py` adapter even hardcodes `S=1`. Carrying real `(N, S)` draws **uncollapsed**
is tracked as **#45** (the producer half), and it is gated by Seam B (C-40). The uncertainty
requirement is the strongest reason to close C-40.

---

## 6. Quick map

```
views_postprocessing/
├── delivery/            representation-free invariants (primitives; no pandas)
│   ├── coverage.py        region cell-count + excluded-cell guards (S1/S4)
│   ├── identity.py        forecast-file identity guard (S3)
│   ├── observed_range.py  fabricated-month decision (S2)
│   └── provenance.py      structured upload provenance (S5)
├── unfao/               FAO-specific delivery
│   ├── extraction.py      THE pandas→primitives seam (Seam A)
│   ├── enrichment.py      GaulLookupEnricher (the GAUL metadata join)
│   ├── gaul_schema.py     the 9-column contract
│   ├── source_metadata.py producer (datafactory) data-facts, e.g. last_valid_month_id
│   ├── frames.py          views-frames conformance adapter (UNUSED by the live path)
│   └── managers/unfao.py  UNFAOPostProcessorManager (the thin pipeline-core subclass)
└── data/gaul_lookup.parquet   the precomputed GAUL lookup (ADR-011)
```

---

## 7. Where to go next

- **What was decided and why** → `docs/ADRs/` (esp. ADR-011 mapper→lookup; ADR-012 ontology).
- **Per-class contracts** → `docs/CICs/` (`UNFAOPostProcessorManager`, `GaulLookupEnricher`).
- **Live risks / open constraints** → the technical risk register (C-40 the pandas gate,
  C-25/C-30/C-15 the delivery guards).
- **The frame/draws future** → #45 (delivery-side draw carrier) and C-40.
