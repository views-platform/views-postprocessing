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

Two partner deliveries live here: the **UN FAO** one
(`views_postprocessing/unfao/`), delivering to FAO-FSFC since 2026-07-27, and
**CRAF'd** (`views_postprocessing/crafd/`), added 2026-08-03 with its upload interlock
still closed. They are peers — one producer, one partner package each.

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
- pipeline-core also **provides the tools** the steps use: `ViewsDataLoader`,
  `DatastoreModule`, `AppwriteConfig`, the path managers.
  (`PGMDataset` was on this list until #149 retired the pandas delivery path; this repo no longer references it — see Seam B.) <!-- legacy-ok: retirement record -->

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
| Read | `_read_historical_data`, `_read_forecast_data` | Historical actuals as a `views_frames.FeatureFrame` from datafactory; the forecast **resolved** from the prediction store — manifests and pinned shard ids only, no heavy bytes. Both refuse a launch config that has not declared them. Fabricated tail months are clipped here, at the read. |
| Transform | `_transform` | **A deliberate no-op.** Geography is not joined into either payload: the historical artifact attaches it at build time, and the forecast ships it as the §5 GAUL sidecar. The hook stays so the Template Method's phases remain truthful. |
| Validate | `_validate`, `_check_coverage` | Asserts the read produced what the save needs, then region coverage + excluded-cell guards. The metadata null-gate fires at artifact build (`historical.assert_metadata_complete`); the forecast's guarantees are the wire's own verified chain. |
| Save | `_save` | Streams the run one target at a time — shards, sidecar, then the manifest **last** as the commit marker — plus the historical artifact. |

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
  pure rule that raises or passes: `coverage.py`, `draws.py`, `parity.py`,
  `observed_range.py`, `provenance.py`, `findability.py`.
- `views_postprocessing/contract/frame_extraction.py` — **the representation seam**. It
  turns a `views_frames` frame into the primitives the invariants consume.

The manager **calls** the invariants; it never makes them methods of itself. The pattern is
always `extract (seam) → call invariant → raise`. This is why the guards are testable
without the framework, and why they survive a representation change untouched.

**And they did survive one.** This seam was `unfao/extraction.py` (pandas) until #151. <!-- legacy-ok: retirement record -->
When the pandas delivery was retired, the invariants needed **no change at all** — only
which module fed them. That is the design working exactly as this section claims, and it is
the evidence for the claim rather than a restatement of it. `delivery/identity.py` was also <!-- legacy-ok: retirement record -->
retired (#150): the forecast-identity rule now lives in the wire layer, checked per shard <!-- legacy-ok: retirement record -->
header against declared provenance — see §5 Seam C. <!-- legacy-ok: retirement record -->

### Seam B — the inherited pandas base, and the C-40 gate

Because this repo *is-a* pipeline-core postprocessor (section 3), three **concrete** pandas
pieces are inherited, not chosen:

1. the input loader (`ViewsDataLoader` → parquet → pandas),
2. the dataset container (`PGMDataset`, a pandas `DataFrame` with object-dtype cells), <!-- legacy-ok: describes the pre-2026-07-27 state, as this section states -->
3. the prediction-store parquet I/O.

**This section described the state until 2026-07-27; it is no longer true and is kept
because the shape of the fix is worth reading.** A views-frames frame now flows end-to-end:
historical actuals arrive as a `FeatureFrame` via pipeline-core's `get_feature_frame`
(#126 — this repo was its first production consumer), the forecast interior is
`PredictionFrame`, and `contract/frames.py` is the **live constructor** every interior frame
is built through — not the unused adapter it was when this was written, and it supports
`S > 1`. pandas is gone from the package entirely since #90 retired the last module holding it (register C-75); what remains is on the
build/verification path.

What **remains** of **register C-40** is narrower than this paragraph implies: the manager is
still a concrete pipeline-core subclass, and that de-inheritance is gated on pipeline-core
3.0.0. The representation half is done. The half
is a one-seam change.

### Seam C — points vs draws (uncertainty)

The delivery is moving from **point estimates** to **predictions-with-uncertainty** (S
samples per cell). This is where representation matters most:

- views-frames stores a distribution natively as a contiguous `(N, S)` float32 array (sample
  axis explicit; a point is just `S=1`).
- pandas `PGMDataset` stores it as **object-dtype list-in-cell** — a separate numpy array <!-- legacy-ok: comparative reasoning for the frame-native path -->
  boxed in each of N cells. Cost scales ~linearly with S (memory, an encode/decode tax at
  every parquet/API boundary, a silent resize on mismatched sample counts).

Today this repo ships **point-shaped** data (`pred_*_best` / `pred_*_prob`); its
`contract/frames.py` constructor takes a declared `(N, S)` array and refuses to infer or reshape — `S=1` is the caller's declaration of a point, not a hardcode. Carrying real `(N, S)` draws **uncollapsed**
is tracked as **#45** (the producer half), and it is gated by Seam B (C-40). The uncertainty
requirement is the strongest reason to close C-40.

---

## 6. Quick map

```
views_postprocessing/
├── delivery/            representation-free invariants (primitives; no pandas)
│   ├── coverage.py        region cell-count + excluded-cell guards
│   ├── draws.py           the §6 no-collapse gate
│   ├── parity.py          sidecar covers exactly the forecast's cells
│   ├── observed_range.py  fabricated-month decision
│   ├── provenance.py      structured upload provenance
│   └── findability.py     does the consumer's own query find THIS run? (C-94)
├── contract/            HOW A DELIVERY IS BUILT — partner-neutral, reusable by a clone
│   ├── wire/              the ADR-013 contract (header, shard, sidecar, run_manifest,
│   │                        sink, source_selection, naming)
│   ├── frames.py          PredictionFrame / TargetFrame constructors (LIVE)
│   ├── frame_extraction.py  THE representation seam (Seam A)
│   ├── track_a_source.py  Hop-A archive → frame
│   ├── historical.py      the historical artifact, built pandas-free
│   ├── gaul_lookup.py     the GAUL asset: path, version, one read per delivery
│   ├── gaul_schema.py     the 9-column contract, declared as data
│   ├── source_metadata.py producer (datafactory) facts, e.g. last_valid_month_id
│   ├── store_metadata.py  prediction-store facts
│   └── launch_config.py   the delivery mode the launcher must declare
├── unfao/               WHO A DELIVERY IS FOR — the FAO-specific code, and only that
│   ├── product.py         targets, consumer document name, S_MIN, upload interlock
│   ├── appwrite_env.py    the declared store coordinates
│   └── managers/unfao.py  UNFAOPostProcessorManager
├── crafd/               WHO A DELIVERY IS FOR — the CRAF'd-specific code (same three
│   │                      files, same shape; register C-33 on why it is a copy)
│   ├── product.py
│   ├── appwrite_env.py
│   └── managers/crafd.py  CRAFDPostProcessorManager
│                          the two managers are the ONLY importers of
│                          views_pipeline_core — one per partner, allowlisted by test
└── data/gaul_lookup.parquet   the precomputed GAUL lookup (ADR-011)
```

---

## 7. Where to go next

- **What was decided and why** → `docs/ADRs/` (esp. ADR-011 mapper→lookup; ADR-012 ontology).
- **Per-class contracts** → `docs/CICs/` (`UNFAOPostProcessorManager`).
- **Live risks / open constraints** → the technical risk register (C-40 the pandas gate,
  C-25/C-30/C-15 the delivery guards).
- **The frame/draws future** → #45 (delivery-side draw carrier) and C-40.
