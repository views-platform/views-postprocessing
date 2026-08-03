# Correcting a delivery that has already reached the UN FAO

**Read this when a delivered value is suspect.** It is a runbook, not an argument — a
person following it at 22:00 after a bad delivery should not have to read three other
documents first. Where a step needs background, the link is inline and optional.

Register **C-22**. Supersedes issue #15, whose procedure described the pre-2026-07
delivery (disk caches, shapefiles) and no longer applies to anything.

> **Status: steps 1–3 and 5 are executable today. Step 4 is executable but incomplete.**
> *Who* contacts the UN FAO is decided — Simon Polichinel von der Maase, by direct email
> (§4). What is **not** decided is whether those are the right recipients, what
> notification period FAO expects, and whether FAO wants a withdrawal or a supersession.
> Those are put to FAO as Pre-Release Note 07, Topic B. **Follow §4 as written rather
> than improvising** — an inconsistent first message to a partner is harder to correct
> than a slow one.
>
> *(Corrected 2026-08-03: this banner said nobody had decided who makes contact, while
> §4 twenty lines below already named the responsible person. The guard in
> `tests/test_doc_accuracy.py` asserts §4's sentence exists and never read the banner
> beside it.)*

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

Two fields identify a delivery — and **they are not on the same artifact.** Know this
before you try to join them, because you cannot.

| field | what it answers | where it lives | where it does NOT |
|---|---|---|---|
| `run_id` | *which run* | the manifest, every shard's header, each store document's filename | the historical artifact (its filename is `historical_dataset_<timestamp>.parquet`) |
| `lookup_version` | *which GAUL build produced its geography* | the historical artifact's store-document `description` (a compact JSON provenance record) | the manifest, the shards, **and the GAUL sidecar** |

`lookup_version` has the form `land_gaul@f74d3b2b` — region, then the digest of the
views-datafactory ingestion the lookup was built from. **It cannot silently be
`"unknown"`**: since register C-60 the reader raises rather than degrading, so a stamp
you can read is a stamp you can trust.

**Two consequences you will hit immediately.**

1. **There is no key joining a `run_id` to a `lookup_version`.** The historical artifact
   carries the geography stamp and no run id; the manifest carries the run id and no
   geography stamp. In practice you correlate them by **upload timestamp proximity**
   within the bucket. Say so in your incident notes rather than implying a join.
2. **The forecast leg carries no geography stamp at all.** The §5 GAUL sidecar has no
   version field (ADR-014 §4 defers stamping it to the next ADR-013 version bump). So a
   *geography* fault can be scoped precisely on the historical leg and only by timestamp
   on the forecast leg. If that is the fault you have, quarantine generously — the cost
   of withdrawing one run too many is a re-publish; the cost of leaving one is FAO
   serving wrong geography.

*(Corrected 2026-08-03: this section said both fields were "on it by construction",
which reads as though they sit on one artifact. They never have.)*

**To enumerate affected runs:**

1. If the fault is in **geography** (a wrong country, admin unit or coordinate), the
   blast radius is *every delivery sharing the suspect `lookup_version`*. Compare the
   stamp on each delivered run's provenance record.
2. If the fault is in **forecast values**, the blast radius is the runs whose manifest
   names the affected producer run — the manifest carries `run_id` and `targets`.
3. If the fault is in **coverage** (missing or extra cells), the manifest's
   `expected_cell_count` and the provenance record's `actual_cell_count` bound it
   without opening a single parquet.

Establish scope before you *correct* — a correction whose scope you have not
established is a second incident. **But withdraw first** (§3): quarantine is reversible
and costs seconds, and scoping while wrong data serves is the expensive order. Withdraw
generously, then narrow.

---

## 2. Reproduce and confirm, offline

**Do not re-run the pipeline to investigate.** The committed artifacts are enough, and
re-running changes the thing you are diagnosing.

```
pytest -q tests/test_gaul_lookup_fidelity.py
```

24 tests. **What runs without a views-datafactory checkout** — key uniqueness, cell
count, exclusion-set disjointness, coordinate correctness, and the absence of nulls and
`-1` sentinels, all against the committed lookup.

**What does NOT run without one**, and this matters if you are on a laptop: the
comparison of all seven GAUL columns against the producer's own parquets, region-set
equality, the coordinate-dtype wire-stability check, and the per-cell coordinate-formula
check — four tests in all. The dtype one touches only the committed lookup and is gated
more strictly than it needs to be. Those tests **skip**, they do not fail. Check the pytest summary
line for `skipped` before concluding you have verified the geography — a green run with
skips is a weaker statement than a green run without them.

*(Corrected 2026-08-03: this said "26 tests" — a count that was never true — and listed
region-set equality in the always-on half when it is gated.)*

**If those pass and a value is still wrong, the fault is upstream, not here.** That
distinction is register C-43's and it is load-bearing: this repository is verified to
carry views-datafactory's answer faithfully; whether that answer is *right* — in
particular the degree-based area-majority join at high latitudes — is
**views-datafactory#387**. Do not correct a delivery to compensate for a producer
defect; fix the producer and rebuild.

---

## 3. Correct on the wire

### DO THIS FIRST: withdraw the bad run. It takes one environment variable.

**Corrected 2026-08-03.** This section previously said withdrawal had no mechanism and
there was no rollback. That was wrong, and following it cost hours: it sent you to fix
the cause and republish an entire corrected run while the wrong data stayed live.

views-faoapi ships an operator quarantine (`f1a59bf`, on its `main`,
`managers/prediction/quarantine.py`). It is a comma-separated list of **store-document
file-ids**; selection drops anything on it *before* choosing.

**⚠ A run has TWO selection entry points, and quarantining one does not withdraw the other.** (A run is ~112 files — §0. What matters here is that the consumer reaches them through two independent doors.)

| leg | what to quarantine | how the consumer selects it |
|---|---|---|
| forecast | the run **manifest**'s file-id | newest manifest, then the shards it names |
| historical actuals | the **historical parquet**'s own file-id | newest document with `category="historical"` — **it never looks at the manifest** |

```
APPWRITE_UNFAO_QUARANTINED_FILE_IDS=<manifest file-id>,<historical file-id>
```

Quarantining only the manifest leaves the historical artifact serving. That is the wrong
way round for a **geography** fault: `lookup_version` lives *only* on the historical
document (§1), so the leg you can identify precisely is the leg you would have left
live. When in doubt, quarantine both — the cost of withdrawing one document too many is
a re-publish.

Both legs go through the same filter (`prediction/manager.py:145-156`, inside
`get_predictions_by_metadata` — which the forecast path reaches via `get_latest_file_id`
and the historical path via `get_latest_provenance`), so one variable covers both. Read at selection time — **no redeploy**. Nothing is deleted, so it is reversible:
unset the variable and the run is selectable again. Whitespace around entries is
tolerated; quotes are not stripped, so do not quote the ids.

There is a matching allowlist, `APPWRITE_UNFAO_APPROVED_FILE_IDS`, which restricts
selection to explicitly approved files (unset or empty = unrestricted).

**These names are FAO's.** Each partner's consumer reads its own — CRAF'd's is
`APPWRITE_CRAFD_QUARANTINED_FILE_IDS`. Setting the wrong partner's variable is a
**silent no-op**: nothing errors, and the data keeps serving.

**Withdraw first, then diagnose.** Steps 1–4 below are the correction; the quarantine is
the stop-the-bleeding move that precedes them, and it is what makes the rest unhurried.

### Then correct: withdrawal vs supersession

- **Withdrawal** — the intended policy (operator decision, 2026-08-02): data known to be
  wrong should not stay retrievable. **Available now**, via the quarantine above.
- **Supersession** — what the *wire itself* does: manifest-last ordering means a run is
  replaced by publishing a new complete run, and the old one stays in the bucket.

The two compose: quarantine withdraws immediately, publishing supersedes durably. Put to
FAO as **Pre-Release Note 07, Decision Point B.2**, which asks whether they have an audit
or reproducibility requirement arguing *against* withdrawal.

> ⚠ **Note 07 Topic B.2 needs correcting before it goes to FAO.** It presents withdrawal
> as *"Not available today. Requires a change to the delivery contract … and
> corresponding work in the API layer."* That is false — see above. The decision FAO is
> being asked to make is real, but the cost framing given to them is not.

### Publishing the correction

With the bad run withdrawn, this part is unhurried:

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

views-faoapi resolves **the newest manifest matching a broad filter** — its own
`src/views_faoapi/managers/prediction/manager.py::get_latest_manifest`, minus anything
quarantined. So a corrected run is picked up because it is *newer*, not because it is
*correct*. Two consequences:

*(Corrected 2026-08-03: this cited `wire/source_selection.py`. That file is **this**
repo's Hop-A **inbound** selector — how we consume pipeline-core forecasts — not how FAO
selects. views-faoapi has no `wire/` package at all.)*

- **Publishing the correction is what switches the consumer over.** There is no
  "activate" step in the *publishing* path — but there IS a rollback: quarantine the
  bad run's documents (above) and the consumer falls back to the previous ones.
  Republishing an old run, by contrast, would mean publishing it again under a new id.
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

A withdrawal that destroys the evidence makes the post-mortem impossible — which is
why quarantine is the right instrument: it removes the run from *selection* without
removing it from the bucket. Keep, at
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
`views_postprocessing/contract/wire/source_selection.py` (how **this repo** chooses its
Hop-A input — *not* how FAO chooses; that is views-faoapi's
`managers/prediction/manager.py`) ·
register **C-22**, **C-43**, **C-60**, **C-73** · issues **#15**, **#131**, **#133**,
views-datafactory **#387**
