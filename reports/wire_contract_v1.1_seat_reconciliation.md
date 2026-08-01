# Wire Contract v1.1 — seat reconciliation (producer × consumer)

| | |
|---|---|
| **Date** | 2026-07-13 |
| **Reconciles** | `views-pipeline-core/reports/wire_contract_v1.1_producer_seat_response.md` (producer seat, 2026-07-13) × `views-faoapi/reports/expert_reviews/2026-07-13_wire_contract_v1.1_consumer_response.md` (consumer seat, 2026-07-13) |
| **Independence** | The two responses were written without reading each other (producer seat confirmed; both dated the same day against the same draft). Convergences below are therefore independent replications, not echoes. |
| **Bottom line** | **Both seats approve v1.1; zero conflicting instructions to the author.** One finding was independently discovered by both seats (manifest cardinality — unanimous priority #1 for v1.2). One **new cross-seat finding** emerged from reconciliation itself (R1: the consumer seat's D3 transition hazard generalizes to Hop A — verified in code today). Merged v1.2 checklist below: 5 substantive + 1 editorial batch. |

---

## 1. Verdict alignment

| | Producer seat (views-pipeline-core) | Consumer seat (views-faoapi) |
|---|---|---|
| Verdict | APPROVE; 2 substantive + 3 editorial deltas | Sign-off-ready; 4 deltas, "none architectural" |
| Disposition of own v1 findings | all addressed faithfully or deferred with sound substitute | all four required amendments satisfied; all recommendations adopted |
| Blocking items | none | none |

Both seats also independently praised the same two draft properties: the finding-traceability
changelog, and the mechanism/policy split (§3.4/§4.5 vs §6).

## 2. Convergences (independent replication — treat as high-confidence)

**2.1 Manifest cardinality / multi-target torn runs — producer Δ1 ≡ consumer D1.**
Both seats independently found that per-(run, target) manifests reopen the torn-run hole
*across the target axis* ("newest manifested run" is ill-defined when a run has three commit
markers; the expected target set lives nowhere on the wire). The producer seat posed the choice
(per-target independence vs run-level completion); the consumer seat resolved it with
consumer-side evidence: **Hop-B manifest = one per run, spanning all (target, month) shards;
Hop A keeps per-(run, target)** since views-postprocessing can await all targets before
translating. *Reconciled position: adopt the consumer seat's fix verbatim, plus one residual
clause the producer seat's framing still requires —* **name the owner of the expected-target-set
knowledge at Hop A** (views-postprocessing configuration; it is the anti-corruption layer and
already owns the §6 policy), so "await all three" is grounded in something written down.

**2.2 Manifest as the run's operational control point — producer Δ3-2 ≡ consumer §3.2.**
The producer seat asked for "rollback = delete the manifest" to be stated; the consumer seat
independently discovered the stronger form: **quarantining the single manifest fileId (C-71
blocklist) atomically rolls the consumer back to the previous manifested run** — per-run rollback
from per-file machinery. *Reconciled clause for §4.3/§4.4: the manifest is the run's operational
control point — quarantine or delete it to roll back a run; operators act on manifests, never on
shards. (Runbook line when faoapi#100 lands.)*

## 3. New finding from reconciliation itself

**R1 — The consumer seat's D3 transition hazard generalizes to Hop A (verified 2026-07-13).**
D3 established that the deployed faoapi selects newest-`category="forecast"` with no `type`
awareness, so Hop-B contract artifacts must not precede the type-aware consumer. Reconciling
that against the producer seat's knowledge of who reads `production_forecasts` today:
the **legacy views-postprocessing manager has the same selection shape at Hop A** —
`views_postprocessing/unfao/managers/unfao.py:110`:
`get_latest_file_id(filters={"category": "forecast"})`, newest-wins, no `type` filter.
The first pipeline-core#269 upload wave (shards + manifest, all `category="forecast"`) would
therefore become "the newest forecast" to the legacy Hop-A reader. **Mitigating backstop,
also verified:** the legacy manager asserts the selected file's identity against the configured
ensemble (`unfao.py:107-123`, `identity.assert_forecast_identity`) — so the failure is a **loud
legacy-path outage**, not silent mis-serving. Still a production incident if sequencing is wrong.
*Reconciled clause for §11: the D3 sequencing rule applies at **both** hops — at each store, the
type-aware consumer (or at minimum a type-guard in the legacy reader) deploys before the first
contract artifact is uploaded there. For Hop A that means: views-postprocessing's source adapter
(its #85 S3+) or a one-line type filter in `unfao.py:110` lands before #269's first live upload.*

## 4. Complementary deltas (no overlap, no conflict — all carry into v1.2)

| From | Delta | Note |
|---|---|---|
| Consumer §3.1 + D2 | Pin the **literal `name`** for Hop-B store documents + full field table (`name` is load-bearing for visibility: faoapi always injects the name filter — documents with the wrong `name` are *invisible*, not degraded) | Producer seat has no stake; endorses. Hop-A `name` templates (§3.3) unaffected. |
| Consumer D4 | Assign hash verification: views-postprocessing verifies Hop-A hashes on read; faoapi SHOULD verify Hop-B hashes at ingest (add to §4.5's list) | Producer computes hashes into the manifest (§3.2, already specified); no new producer burden. |
| Producer Δ2 | Golden-fixture **distribution mechanism** (vendored copies + pinned content-hash equality test; hash is the cross-repo contract) + producers accept **injectable `run_id`/`generated_at`** for byte-parity | Consumer seat adopted the fixture but didn't cover distribution; endorse into §10. |
| Producer Δ3-1 | §3.4 wording: emission assert inspects **staged files pre-zip** at runtime; the zip step is covered by #269's CI round-trip test | One sentence. |
| Producer Δ3-3 | Mark the §6-check-2 / §4.5(a) redundancy as intentional (policy gate re-validates its own input) | One sentence; pre-empts a future "simplification." |

## 5. Conflicts

**None.** The single point where the seats could have collided — manifest cardinality — is a
choice-point the producer seat left open and the consumer seat resolved with evidence; the
producer seat accepts the resolution (§2.1). No clause in either response contradicts the other.

## 6. Merged v1.2 checklist for the author (ranked)

1. **Manifest cardinality** (§3.2/§4.2/§4.3): Hop-B = one manifest per run spanning targets;
   Hop-A = per-(run, target); + expected-target-set owner named (views-postprocessing config).
   *(Both seats, unanimous #1.)*
2. **Hop-B store-document schema** (§4.1/§4.2): field table with the **literal `name` pinned**,
   `type` enum incl. `sampled_forecast_sidecar`. *(Consumer D2/§3.1.)*
3. **Transition sequencing at both hops** (§11): type-aware consumer (or legacy type-guard)
   deploys before the first contract upload at each store — Hop B (faoapi, D3) **and** Hop A
   (legacy `unfao.py:110`, finding R1); skeleton ordering becomes consumer-guards → producer
   legs → run 0.
4. **Fixture distribution + injectable provenance** (§10). *(Producer Δ2.)*
5. **Hash-verification assignment** (§3.2/§4.5). *(Consumer D4.)*
6. **Editorial batch:** manifest-as-operational-control-point (quarantine-or-delete = run
   rollback; §4.3/§4.4); staged-files emission-assert wording (§3.4); intentional-redundancy
   clause (§6). *(Convergence 2.2 + producer Δ3.)*

After v1.2 folds these in, both seats are on record as sign-off-ready → the §0.2 adoption act
(maintainer sign-off on views-models#149, enacted by landing the durable views-postprocessing
ADR) is the only remaining step.

---

*Reconciled by the producer seat (views-pipeline-core session), 2026-07-13. R1's code claims
verified against views-postprocessing `development` at reconciliation time (`unfao.py:96-123`).*
