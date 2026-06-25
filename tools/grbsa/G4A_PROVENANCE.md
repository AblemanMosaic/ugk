# GRBSA Phase G4a — Canonical Archive Provenance (r21) — GateAdapter generality

## Lineage
- r19 (G2) 5c38a84c… -> r20 (G3 GateAdapter) 37c55239… -> r21 (G4a: second gate proof)

## What G4a proved
The GateAdapter is NOT a1-specific. It wraps a SECOND, structurally-DIFFERENT conformance gate —
`determinism_gate`, whose native result is a (ok, detail) verdict tuple (NOT a1's GateResult per-check
triples) — as a receipt-bound continuation, equivalent to its legacy runner, with the SAME discipline
as G3. The SAME GateAdapter still wraps a1 (GateResult shape) equivalently.

## What G4a delivered (additive; ugk/ untouched, legacy gates unmodified)
- tools/grbsa/grbsa_runtime/gate_adapter.py — ADDITIVE: result-shape NORMALIZER seam
  (default = .checks-style for a1; verdict_tuple_normalizer for (ok,detail) gates). a1 path preserved
  byte-for-behavior (G3 gate still PASS).
- tools/grbsa/grbsa_runtime/__init__.py — export verdict_tuple_normalizer.
- tools/grbsa/grbsa_runtime/migration_receipt_determinism.json — dual-run equivalence for determinism.
- tools/grbsa/g4a_adapter_generality_gate.py — the G4a gate.
Diff vs r20 (ignoring __pycache__): only the four items above (g4a gate added; adapter+init additively
extended; new migration receipt). ugk/ byte-identical to r20. law_hash unchanged.

## Ratified scope (split cadence)
G4a = second GateAdapter proof ONLY. Narrow: prove generality on one additional deterministic
structured gate. No ProjectionAdapter (G4b), no ExplainAdapter (G4c), no Category-Separation yet
(needs >=2 adapter DOMAINS; G4a stays in the gate domain). No live routing, no retirement, no ugk/
change.

## Equivalence basis (unchanged; Receipt Sufficiency Principle, NOT receipt-hash identity)
Relation: unique check names + same count + identical (name,ok) mapping + identical verdict; detail
strings excluded; receipt-hash NOT asserted (chain hash binds ts).
The result-shape normalizer maps each legacy runner's NATIVE output into the canonical [(name,ok)]
findings WITHOUT re-deriving the gate: determinism's single (ok,detail) verdict -> one synthetic
check 'determinism:verdict'. No per-check structure invented beyond the gate's own verdict.

## G4a Adapter-Generality Gate — PASS (negative controls fire through the real adapter path)
- target gate has a DIFFERENT result shape than a1 ((ok,detail), not GateResult).
- verdict + per-check equivalence: legacy == adapter (via verdict-tuple normalizer).
- NBER-1: receipt minted before continuation (honest order: receipt_minted, effect_ran).
- success semantics = anti-vacuity predicate over receipt+envelope.
- category boundary: findings in ResultEnvelope, not Receipt.
- SAME GateAdapter still wraps a1 (GateResult shape) equivalently (7 checks).
- NEG-i receipt-after-effect FAILS NBER-1; NEG-ii dropped check FAILS equivalence (count+mapping);
  NEG-iii posture op REFUSED; NEG-iv zero-check vacuous run NOT success.

## Migration posture (strangler — unchanged)
MigrationReceipt(determinism) records dual-run equivalence. Legacy runner REMAINS source of truth;
determinism gate ELIGIBLE (not required) for routing only after G4a passes from clean extraction.
No live routing. Nothing retired. (a1 likewise still only eligible, per G3.)

## No regression / behavior invariance
- ugk/ byte-identical to r20; legacy determinism_gate + a1 gate UNMODIFIED, both pass standalone.
- G3 gate still PASS (a1 path preserved under the additive normalizer default).
- scale 7/7; AL 22/22; batch 78/78; G1/G2/G3 gates PASS.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/g4a_adapter_generality_gate.py . (PASS),
  plus g1/g2/g3 gates; confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ unchanged.

## Status
GRBSA G4a complete: GateAdapter proven general across two result shapes. STOPPED before G4b
(ProjectionAdapter) as scoped.
