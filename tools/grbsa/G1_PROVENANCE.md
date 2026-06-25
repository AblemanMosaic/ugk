# GRBSA Phase G1 — Canonical Archive Provenance (r18)

## Lineage
- r17a (v0.1.0-cgproj RC) 4d080a4b… -> r18 (GRBSA G1 — receipt+envelope core semantic spec)

## What G1 delivered (semantic specification only; NO runtime object, NO behavior change)
- tools/grbsa/RECEIPT_CORE_SPEC.md   — the two closed cores as projections over existing fields
- tools/grbsa/core_mapping.json      — machine-readable manifest (shared source for prose + gates)
- tools/grbsa/g1_core_shape_gate.py
- tools/grbsa/g1_separation_symmetry_gate.py
Full diff vs r17a (ignoring __pycache__): ONLY tools/grbsa/ added. ugk/ byte-identical to r17a.
law_hash unchanged.

## Mapping faithfulness (the STOP-or-proceed condition — proceed was justified)
Every Receipt Core field (6) and ResultEnvelope Core field (5) maps to a field VERIFIED PRESENT in
the current tree by importing the real classes (not asserted from prose):
  Receipt Core   <- ugk.storage.store.Receipt (29 fields) + ugk.scale.oracle.Receipt (10 fields)
  Envelope Core  <- ugk.testing.headless_runner.ScenarioResult / BatchResult
No core field required invention; the STOP condition (a field with no real source) did NOT trigger.

## G1 gates — PASS (negative controls fire through the real gate path)
Core-Shape Gate:
  - Receipt Core has exactly 6 fields; Envelope Core exactly 5.
  - every mapped source field exists in the tree (real-class inspection).
  - G1 introduced no second receipt/envelope runtime object under ugk/.
  - NEG: extra core field rejected; non-existent source field rejected.
Separation + Symmetry Gate:
  - no result/outcome source leaks into the Receipt core (separation).
  - Envelope core closed + both extension seams declared (symmetry).
  - success semantics is a predicate, in neither core nor extension.
  - NEG: result source injected into receipt core detected; success-verdict field in a core detected;
    extra domain field in the Envelope core breaks closure.

## No regression in the existing surface
- conformance batch 78/78; all 7 CGProj projection gates PASS; ugk/ runtime byte-identical to r17a.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## Scope boundary note (CGProj Phase 6 aggregate vs GRBSA)
The CGProj phase6_full_validation_gate reconciliation allows additions ONLY under the CGProj prefixes
{ugk/projections/, docs/patterns/, docs/domain-mappings/, tools/cgproj/}. It therefore (correctly)
flags tools/grbsa/ as a non-CGProj addition. This is NOT a UGK regression — it is that ratified gate
asserting the CGProj release surface. Per discipline, the ratified CGProj Phase 6 gate was NOT
modified to admit GRBSA; GRBSA gets its OWN aggregate gate at G6, whose reconciliation will admit
tools/grbsa/. For G1 the relevant facts hold: existing CGProj surface non-regressed (78/78 + 7 gates
green, ugk/ byte-identical) and both G1 gates pass.

## Scope held (G1)
Spec + manifest + two read-only gates. No substrate naming (G2). No adapter (G3). No runtime object.
No scheduling. No law_hash change. No success-predicate implementation.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/g1_core_shape_gate.py .
  and python tools/grbsa/g1_separation_symmetry_gate.py . ; confirm both PASS, law_hash 546a9e90,
  and the existing CGProj gates + 78/78 still green.

## Status
GRBSA G1 complete (receipt+envelope core semantic specification). STOPPED before G2 as scoped.
