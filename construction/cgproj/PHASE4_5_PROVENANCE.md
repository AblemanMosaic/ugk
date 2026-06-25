# CGProj Phase 4.5 — Canonical Archive Provenance (r14)

## Archive lineage
- r9-clean: b98108e93f41cd9e83ebd24088ead9c534f853ccdfac26b70fb0694d63d04aa0
- r10 (Phase 1): a866d79443d2275eee3bb6f8b94b714cb99bfd417ecede0480f31dfe7737f6b2
- r11 (lazy __init__): 37d426ad016d0168608cfe3b89acf479c9d1b5b5b725a04a9e6498ae8f0370cb
- r12 (Phase 3 renderer+hash): 54e1b29999d38ad9b0e36ab09600c9ce46de9779e9973fc4e5d493d46c3b5921
- r13a (Phase 4 fidelity, corrected): 7db95bbbfb2e28b9685638347ee161cbb9e54224dacd96c95172c04e57a53f6c
- r14 (this archive: r13a + Phase 4.5 Jurisdiction Gate): sha in detached record

## Full additive diff vs r13a (ignoring __pycache__) — exactly these three changes:
- ADDED  tools/cgproj/execution_jurisdiction.py  — SINGLE authoritative execution-jurisdiction set
- ADDED  tools/cgproj/phase4_5_jurisdiction_gate.py — the Jurisdiction Gate
- CHANGED tools/cgproj/phase2_execution_removability_gate.py — refactored to consume the shared set
  (authorized; behavior unchanged, re-verified PASS with 98 files scanned)
- ADDED  tools/cgproj/PHASE4_5_PROVENANCE.md — this file
The ugk/ tree is UNCHANGED (Phase 4.5 touched only tools/cgproj/). No runtime/projection file added
or modified. law_hash unchanged.

## law_hash
- preserved, unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820

## Standing gates — all PASS against this tree
- Phase 1 Structural Validity: PASS
- Phase 2 Execution Removability / Non-Authority: PASS (now consuming the shared execution set;
  receipt-hash identity still NOT claimed)
- Phase 3 Determinism: PASS
- Phase 4 Fidelity: PASS
- Phase 4.5 Jurisdiction: PASS

## Phase 4.5 — the full triangle, held in one invocation
- Leg 1: execution surface passes with ugk/projections/ DELETED (carried from Phase 2).
- Obligation A — metadata-sensitivity (Projection -> Documentation EXISTS):
    A1 mutation propagates to predicted place (marker present only after mutation)
    A2 distinct mutations -> outputs EACH containing its own mutated value and not the others
       (causal linkage formal, per Governor adjustment)
    A3 content_hash tracks the mutation
- Obligation B — execution-independence (Execution -> Documentation does NOT exist):
    B1 regeneration under a PROVEN-ACTIVE execution barrier (sentinel + positive/negative import
       controls) is byte-identical to baseline
    B2 regeneration with 14 execution paths physically DELETED is byte-identical to baseline
- Static corroboration: render/hash/generate import only ugk.projections.* + stdlib.

## Anti-vacuity (both obligations proven to have teeth)
- Obligation B teeth: a renderer with INJECTED hidden execution dependence (import ugk.kernel) ->
  B1 and B2 FAIL -> GATE FAIL. (metadata-sensitivity alone cannot catch this; only B does.)
- Obligation A teeth: a metadata-INSENSITIVE renderer (constant output, ignores its argument) ->
  A1 and A2 FAIL -> GATE FAIL. (defeats self-comparison and echo-of-stored-copy.)
The two failure modes are orthogonal and each is independently caught.

## Canonical execution-jurisdiction set (anti-drift)
Phase 2 and Phase 4.5 now consume ONE definition: tools/cgproj/execution_jurisdiction.py
(EXECUTION_MODULE_PREFIXES + EXECUTION_MODULE_FILES + helpers + barrier source). The boundary cannot
drift between gates. Prefixes: ugk.kernel, ugk.invariants, ugk.module_registry, ugk.storage,
ugk.governance, ugk.authority, ugk.scale, ugk.schema, ugk.transport, ugk.core, ugk.conformance.

## Narrow claim (what is demonstrated)
The gate demonstrates PROJECTION-DRIVEN REGENERATION IS INDEPENDENT OF EXECUTION — the
renderer/generate path reproduces artifacts identically with execution barred (B1) and removed (B2).
This is the exact property tested and must NOT be generalized to a broader 'Projection is
independent of Execution' claim beyond regeneration (same discipline as the Phase 2 receipt-hash
narrow claim). Leg 1 (execution survives without projection) and metadata-sensitivity (A) are the
other demonstrated properties; together they establish mutual independence FOR REGENERATION.

## Future hardening (non-blocking, recorded)
Metadata-sensitivity currently demonstrates propagation through a SELECTED mutation path (a pattern
title). A later hardening phase could expand into field-class coverage (title, boundary, primitive,
seam, domain mapping) if broader sensitivity evidence is ever needed. Watch item only; not built here.

## Result (recorded, not acted on)
On the demonstrated regeneration-independence + sensitivity + removability, the third jurisdiction is
established as a NON-AUTHORITATIVE CONSTITUTIONAL JURISDICTION: Law / Execution / Projection, authority
flowing Law->Execution and Law->Projection, never Projection->Execution. Status rests on standing
gates 7.1-7.6, not on authority.

## Scope held (Phase 4.5 only)
Jurisdiction Gate + shared execution set + authorized Phase 2 refactor. NO Phase 5 integration, NO
Explain Fidelity (7.5), NO Corpus Completeness (7.6), NO renderer expansion, NO execution-surface
change. ugk/ unchanged; gates are standing test artifacts under tools/cgproj/.

## How to test by extraction
- extract; from repo root run each standing gate:
    python tools/cgproj/phase1_structural_validity_gate.py .
    python tools/cgproj/phase2_execution_removability_gate.py .
    python tools/cgproj/phase3_determinism_gate.py .
    python tools/cgproj/phase4_fidelity_gate.py .
    python tools/cgproj/phase4_5_jurisdiction_gate.py .
- confirm ugk/invariants.py law_hash is 546a9e90… ; confirm import ugk.projections loads no execution.

## Status
Phase 4.5 jurisdiction triangle established. STOPPED before Phase 5 as authorized.
