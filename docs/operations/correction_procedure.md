# Correcting a delivery that has already reached the UN FAO

**Read this when a delivered value is suspect.** It is a runbook, not an argument — a
person following it at 22:00 after a bad delivery should not have to read three other
documents first. Where a step needs background, the link is inline and optional.

Register **C-22**. Supersedes issue #15, whose procedure described the pre-2026-07
delivery (disk caches, shapefiles) and no longer applies to anything.

> **Status: steps 1–3 and 5 are executable today. Step 4 is not** — nobody has decided
> who contacts the UN FAO, or whether FAO expects a retraction or a supersession. Those
> are the operator's calls and are stated in §4 exactly as they need to be answered.

---

## 0. What a delivery is, in one paragraph

A delivery is one **run**, identified by a `run_id` such as
`rusty_bucket_forecasting_20260727_095355`. It consists of arrow **shards** (one per
target per month), one GAUL **sidecar**, one **historical artifact**, and one **run
manifest** — uploaded **last**, deliberately, because it is the *commit marker*
(ADR-013 §4). A run whose upload died halfway has no manifest and is **invisible to
consumers**, which is the contract's atomicity mechanism and the first thing to
understand before touching anything.

---

## 1. Which deliveries are affected?

Two fields identify a delivery, and both are on it by construction:

| field | what it answers | where it lives |
|---|---|---|
| `run_id` | *which run* | the manifest, every shard's header, and each store document's filename |
| `lookup_version` | *which GAUL build produced its geography* | the historical artifact's store-document `description` (a compact JSON provenance record) |

`lookup_version` has the form `land_gaul@f74d3b2b` — region, then the digest of the
views-datafactory ingestion the lookup was built from. **It cannot silently be
`"unknown"`**: since register C-60 the reader raises rather than degrading, so a stamp
you can read is a stamp you can trust.

**To enumerate affected runs:**

1. If the fault is in **geography** (a wrong country, admin unit or coordinate), the
   blast radius is *every delivery sharing the suspect `lookup_version`*. Compare the
   stamp on each delivered run's provenance record.
2. If the fault is in **forecast values**, the blast radius is the runs whose manifest
   names the affected producer run — the manifest carries `run_id` and `targets`.
3. If the fault is in **coverage** (missing or extra cells), the manifest's
   `expected_cell_count` and the provenance record's `actual_cell_count` bound it
   without opening a single parquet.

Do this before touching the store. A correction whose scope you have not established
is a second incident.

---

## 2. Reproduce and confirm, offline

**Do not re-run the pipeline to investigate.** The committed artifacts are enough, and
re-running changes the thing you are diagnosing.

```
pytest -q tests/test_gaul_lookup_fidelity.py
```

26 tests. The always-on half checks the committed lookup for key uniqueness, region-set
equality, coordinate correctness, and the absence of nulls and `-1` sentinels. With a
views-datafactory checkout present (`VIEWS_DATAFACTORY`), the second half compares all
seven GAUL columns against the producer's own parquets.

**If those pass and a value is still wrong, the fault is upstream, not here.** That
distinction is register C-43's and it is load-bearing: this repository is verified to
carry views-datafactory's answer faithfully; whether that answer is *right* — in
particular the degree-based area-majority join at high latitudes — is
**views-datafactory#387**. Do not correct a delivery to compensate for a producer
defect; fix the producer and rebuild.

---

## 3. Correct on the wire

**The intended policy is WITHDRAWAL. What is implemented is SUPERSESSION.** That gap is
deliberate, recorded, and you need to know about it before you act.

- **Intended** (operator decision, 2026-08-02): a delivery found to be materially wrong
  should be *removed or blocked* so it can no longer be served. Data known to be wrong
  should not stay retrievable through the production interface.
- **In force**: supersession. The manifest-last commit ordering means a run is replaced
  by publishing a *new complete run*; the old one stays in the bucket and remains
  retrievable by a client that asks for it specifically.

Supersession is in force **because it is what the wire does**, not because it was chosen.
Withdrawal has no mechanism today: it needs an ADR-013 amendment and matching work in
views-faoapi. Put to FAO as **Pre-Release Note 07, Decision Point B.2**, which also asks
whether they have an audit or reproducibility requirement that would argue *against*
withdrawal — that answer decides whether the amendment is worth building.

1. Fix the cause — the lookup, the producer, or the code — and land it.
2. Rebuild any affected artifact. For the lookup:
   `PYTHONPATH=. python scripts/build_gaul_lookup.py --datafactory <path> --region land_gaul`
   The builder now **refuses** to produce an artifact it cannot stamp, so a rebuild is
   either traceable or it fails.
3. Re-run the delivery. It publishes a new `run_id`, shards → sidecar → **manifest last**.
4. **Do not delete the superseded run's files before the consumer has moved.** The old
   manifest is what makes the old run selectable; removing shards while it stands
   produces a run that resolves and then fails to load, which is worse than a wrong
   value because it looks like an outage.

### What the consumer will actually pick up — read this before assuming

views-faoapi resolves **the newest manifest matching a broad filter**
(`wire/source_selection.py`). So a corrected run is picked up because it is *newer*, not
because it is *correct*. Two consequences:

- **Publishing the correction is what switches the consumer over.** There is no
  "activate" step and no rollback — republishing the old run would mean publishing it
  again under a new id.
- **Recency-based selection is register C-73**, open, and fixed upstream in
  views-pipeline-core 3.0.0 but not yet taken here. **#133** would have the manifest
  declare `{maturity, source, required-schema-version}` so a consumer could select on
  intent rather than on timestamp. Until then, do not publish a *test* or *partial*
  correction to the production bucket — the consumer cannot tell it from the real one.

---

## 4. Telling the UN FAO

**Simon Polichinel von der Maase is responsible for making contact.** Not an automated
alert — a correction needs judgement about scope and impact that an automated message
cannot carry.

**Recipients and channel are recorded outside this repository.** This repo is **public**,
and publishing named FAO staff members' email addresses in it is not something to do by
default. The contacts are in the FAO-02 project materials
(`brain/2_projects/fao02/…/prerelease_notes/fao_02_pre_release_note_07/`, Decision
Point B.1) and in the operator's address book.

**Send as soon as the scope of the error is established** — not after a correction has
been prepared. The partner's ability to act is time-sensitive and independent of our
remediation timeline.

### Still awaiting FAO's answer

Two things are proposed but not confirmed, and both are put to FAO in **Pre-Release
Note 07, Topic B**:

1. **Are those the right recipients, and is there an expected notification period?** A
   named individual on leave is a single point of failure in exactly the situation where
   delay is costly. FAO may prefer a shared address or a rota.
2. **Does FAO expect a correction notice for *every* error, or only one material to
   published outputs?** A wrong admin label on a handful of cells and a wrong forecast
   across a region are different events; treating them alike either floods them with
   immaterial notices or buries a serious one.

Until FAO answers, follow what is written above. Do not improvise a different channel —
an inconsistent first message to a partner is harder to correct than a slow one.

## 5. Preserve the evidence

A retraction that destroys the evidence makes the post-mortem impossible. Keep, at
minimum:

- the superseded run's `run_id`, its manifest, and its provenance record
- the `lookup_version` in force at the time, and the lookup artifact that produced it
  (it is committed to this repo, so the git history already holds it)
- what was wrong, how it was found, and which check failed to catch it

The last one is the point. Every silent-failure entry in
`reports/technical_risk_register.md` exists because something shipped that no gate
objected to. A correction that does not record *which gate was missing* buys a fix and
leaves the hole.

---

## See also

`docs/ADRs/013_sampled_forecast_wire_contract.md` §4 (commit ordering), §11 (transition
rules) · `views_postprocessing/delivery/provenance.py` (the fields a delivery carries) ·
`views_postprocessing/contract/wire/source_selection.py` (how the consumer chooses) ·
register **C-22**, **C-43**, **C-60**, **C-73** · issues **#15**, **#131**, **#133**,
views-datafactory **#387**
