# GRBSA Phase G3 — Canonical Archive Provenance (r20) — GateAdapter beachhead

## Lineage
- r18 (G1 core spec) eb16c6d1… -> r19 (G2 substrate naming) 5c38a84c… -> r20 (G3 GateAdapter)

## What G3 delivered (first real routing; adapter in tools/grbsa/, ugk/ untouched)
- tools/grbsa/grbsa_runtime/  — GateAdapter + GateReceipt/GateResultEnvelope extensions + ReceiptCore/
  ResultEnvelopeCore records + gate_success() predicate (imports ugk READ-ONLY; no ugk/ object)
- tools/grbsa/grbsa_runtime/migration_receipt_a1.json — dual-run equivalence evidence for a1
- tools/grbsa/g3_adapter_equivalence_gate.py — first fail-closed GRBSA routing gate
Full diff vs r19 (ignoring __pycache__): ONLY tools/grbsa/grbsa_runtime/ + g3 gate added.
ugk/ byte-identical to r19. legacy a1_conservativity_gate UNMODIFIED. law_hash unchanged.

## Beachhead target: a1_conservativity_gate
Chosen for lowest risk: deterministic, standalone (no founding), already structured (GateResult with
.passed + 7 (name, ok, detail) checks). Wrapped as a receipt-bound continuation:
  proposal -> admissibility -> GateReceipt (minted BEFORE effect) -> gate runs -> GateResultEnvelope.

## Ratified tightenings applied
- Q1: adapter under tools/grbsa/grbsa_runtime/, ugk/ read-only, ugk/ byte-identical. No ugk/ shim.
- Q2: equivalence = unique check names + same count + identical (name,ok) MAPPING + identical .passed.
  Detail strings excluded. (Dict mapping, not a raw set — catches duplicate/dropped checks.)
- Wording: the dropped-check negative control is "dropped/swallowed failing check" (a1 has no
  explicit internal negative controls); principle unchanged — the adapter cannot discard/coerce a
  finding and still pass equivalence.

## Equivalence basis (Receipt Sufficiency Principle; NOT receipt-hash identity)
Legacy a1.run_gate() and the GateAdapter agree on admissibility + success semantics + lineage shape.
Receipt-hash identity is intentionally NOT asserted (chain hash binds ts; Receipt Identity Principle).

## G3 Adapter-Equivalence Gate — PASS (negative controls fire through the real adapter path)
- verdict+per-check equivalence: legacy == adapter (unique names, same count=7, same mapping, same .passed).
- NBER-1: GateReceipt minted before the gate continuation runs (honest order: receipt_minted, effect_ran).
- success semantics = anti-vacuity predicate over receipt+envelope (in neither core nor extension).
- category boundary: findings live in ResultEnvelope, not the Receipt.
- authority boundary: honest adapter run originates no posture op.
- NEG-i:  receipt-after-effect variant FAILS NBER-1 (order: effect_ran, receipt_minted).
- NEG-ii: dropped/swallowed check FAILS equivalence (count + mapping differ).
- NEG-iii: adapter attempting a posture op is REFUSED at admissibility.
- NEG-iv: zero-check (vacuous) run is NOT success (anti-vacuity teeth).

## Migration posture (strangler — retires nothing)
MigrationReceipt (migration_receipt_a1.json) records the dual-run equivalence. Legacy runner REMAINS
source of truth. a1 is ELIGIBLE (not required) for adapter routing only after this gate passes from
clean extraction. Routing the broader suite is G4+, separately gated.

## No regression / behavior invariance
- ugk/ byte-identical to r19; legacy a1 gate unmodified; a1 still passes standalone.
- scale conformance 7/7; scale AL 22/22; conformance batch 78/78; G1/G2 gates still PASS.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## Scope held (G3)
ONE gate wrapped + equivalence proven + MigrationReceipt. No ugk/ change, no legacy-gate change, no
routing of the broader suite, no law_hash change. The model's first real test PASSED.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/g3_adapter_equivalence_gate.py . (PASS),
  plus G1/G2 gates; confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ unchanged.

## Status
GRBSA G3 complete: an existing conformance gate wrapped as a receipt-bound continuation, proven
equivalent to its legacy runner with NBER-1 + anti-vacuity + authority boundaries intact. STOPPED
before G4 as scoped.
