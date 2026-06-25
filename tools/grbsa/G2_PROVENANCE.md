# GRBSA Phase G2 — Canonical Archive Provenance (r19)

## Lineage
- r17a (v0.1.0-cgproj RC) 4d080a4b… -> r18 (G1 core spec) eb16c6d1… -> r19 (G2 substrate naming)

## What G2 delivered (spec-only naming layer; NO runtime object, NO behavior change)
- tools/grbsa/SUBSTRATE_INTERFACE.md  — 9 named substrate services -> existing ugk/scale call sites
- tools/grbsa/service_map.json        — machine-readable map (shared source for prose + gate)
- tools/grbsa/g2_substrate_naming_gate.py
Full diff vs r18 (ignoring __pycache__): ONLY the three files above added under tools/grbsa/.
ugk/ byte-identical to r18. law_hash unchanged.

## Ratified decisions applied
- Q1 (timeout): "timeout handling" = the existing bounded-execution/backpressure refusal path.
  Recorded EXPLICITLY that wall-clock timeout is NOT yet a separate service and was NOT invented.
- Q2 (naming home): spec-only in tools/grbsa/ over ugk/scale/. NO ugk/ shim in G2. A runtime
  interface module earns its place only at G3+ when actual routing begins.

## Service map (all 9 symbols verified present in the tree)
scheduling/bounded-exec -> GovernedScheduler.schedule/.independence_set
progress events         -> I5Log.emit + closed SCALE_OPS
timeout handling        -> GovernedScheduler.schedule (backpressure path) [wall-clock timeout absent]
evidence capture        -> I5Log.why / GovernedScheduler.reconstruct_why
result hashing          -> scale.Receipt.rhash (dataclass FIELD) / I5Receipt.rhash() (method)
receipt emission        -> CommitLane.commit_and_effect -> Chain.append (receipt BEFORE effect)
result-envelope assembly-> CommitLane.commit_and_effect (effect_result = 'what happened')
lineage tracking        -> Chain.tip/.append + Receipt.prior_hash/.pos/.produces_effects
summary/verdict report  -> GovernedScheduler.schedule return + I5Log.all

## STOP-or-proceed handling (proceed justified)
Every named service symbol was verified to resolve in the real tree BEFORE recording the map. One
symbol (scale.Receipt.rhash) was a dataclass FIELD, not a method — the gate's resolver handles fields,
constants, and methods, so the mapping is faithful. No service required invention; the STOP condition
(a service with no existing symbol) did NOT trigger.

## G2 Substrate-Naming Gate — PASS (negative controls fire through the real gate path)
- existence: all 9 services resolve to symbols present in the tree (real import/inspection).
- no authority expansion: no named service is a posture op (POSTURE_OPS); emitted vocab IS the closed
  SCALE_OPS. Being named grants no constitutional authority.
- NBER-1 present: at CommitLane.commit_and_effect, chain.append precedes effect_fn (source-order:
  append@557 < effect@702). Recorded, not implemented.
- no new object: no GovernedSchedulerV2/ChainV2/CommitLaneV2/SubstrateInterface class under ugk/.
- NEG: non-existent symbol rejected; injected posture op detected; effect-before-append fails NBER-1;
  new-scheduler-class marker detected.

## No regression / behavior invariance
- ugk/ byte-identical to r18 (naming lives only in tools/grbsa/).
- scale conformance 7/7; scale AL 22/22 (unchanged). conformance batch 78/78. G1 gates still PASS.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## Scope held (G2)
Naming only. No routing through the interface (that is G3). No adapter. No ugk/ runtime change. No
new object. No law_hash change. No scheduling change.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/g2_substrate_naming_gate.py . (PASS),
  plus the G1 gates; confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ unchanged.

## Status
GRBSA G2 complete (substrate interface naming). STOPPED before G3 (GateAdapter beachhead) as scoped.
