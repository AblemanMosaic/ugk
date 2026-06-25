# GRBSA Substrate Interface — Naming Specification (G2)

**Spec-only naming layer.** Names the shared substrate services the Governed Scale Kernel provides,
over EXISTING `ugk/scale/` machinery. **G2 routes no work, changes no scheduling behavior, expands no
authority, and adds no `ugk/` runtime object.** Shared source of truth for prose + gate:
`service_map.json` (same directory).

## The 9 named services → existing call sites

| Service | Existing site(s) | What it is |
|---|---|---|
| scheduling / bounded execution | `GovernedScheduler.schedule` / `.independence_set` | independent-set + priority-within-set + capacity/backpressure |
| progress events | `I5Log.emit` over closed `SCALE_OPS` | receipted scheduler control ops |
| timeout handling | `GovernedScheduler.schedule` (backpressure path) | **G2: = bounded-execution/backpressure refusal** (see note) |
| evidence capture | `I5Log.why` / `GovernedScheduler.reconstruct_why` | reconstruct "why" from receipts alone |
| result hashing | `scale.Receipt.rhash` (field) / `I5Receipt.rhash()` | hash minted at append |
| receipt emission | `CommitLane.commit_and_effect` → `Chain.append` | receipt BEFORE effect (NBER-1) |
| result-envelope assembly | `CommitLane.commit_and_effect` (effect_result) | the "what happened" payload, distinct from the receipt |
| lineage tracking | `Chain.tip` / `.append` / `Receipt.prior_hash` / `.pos` / `.produces_effects` | append-only canonical lane |
| summary / verdict reporting | `GovernedScheduler.schedule` return / `I5Log.all` | committed list + full decision log |

## Timeout handling — explicit scope note (ratified Q1)
In G2, **"timeout handling" means the existing bounded-execution / backpressure refusal path.**
A distinct **wall-clock timeout is NOT yet a separate service and is not invented here.** Should one
ever be added, it is a later, separately-authorized service and, per the **Receipt Identity
Principle**, must not leak wall-clock time into receipt determinism.

## Authority boundary
Named services **schedule and observe** only. No named service is a posture/authority op
(`POSTURE_OPS`); the emitted-ops vocabulary is exactly the existing **closed** `SCALE_OPS`. Naming the
substrate grants it no constitutional authority. (Mirrors "the Kernel may schedule and observe; it
does not grant authority.")

## NBER-1 (recorded, not implemented)
`CommitLane.commit_and_effect` already enforces receipt-before-effect: `chain.append` (receipt
durable) precedes `effect_fn` (effect). G2 records this existing ordering as the substrate's
receipt-emission contract; it changes nothing.

## Scope (G2)
Naming only. No routing through the interface (that is G3, the GateAdapter beachhead). No `ugk/`
runtime change. No new object. `law_hash` unchanged.
