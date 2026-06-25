# CGProj Phase 3 — Canonical Archive Provenance (r12)

## Archive lineage
- r9-clean baseline: b98108e93f41cd9e83ebd24088ead9c534f853ccdfac26b70fb0694d63d04aa0
- r10 (Phase 1 CGProj files): a866d79443d2275eee3bb6f8b94b714cb99bfd417ecede0480f31dfe7737f6b2
- r11 (r10 + authorized lazy ugk/__init__.py): 37d426ad016d0168608cfe3b89acf479c9d1b5b5b725a04a9e6498ae8f0370cb
- r12 (this archive: r11 + Phase 3 deterministic renderer + hash): sha in detached record

## Files added in r12 (additive only; no execution-jurisdiction file modified)
- ugk/projections/render.py  — pure deterministic renderer (metadata -> markdown bytes)
- ugk/projections/hash.py    — canonical payload/json + content_hash + render_hash + PROJECTION_IDENTITY
- tools/cgproj/phase2_execution_removability_gate.py — Phase 2 standing gate (carried into tree)
- tools/cgproj/phase3_determinism_gate.py            — Phase 3 standing gate
Diff vs r11 (ignoring __pycache__): exactly the four files above. law_hash unchanged.

## law_hash
- preserved, unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820

## Standing gates — all PASS against this tree
- Phase 1 Structural Validity: PASS
- Phase 2 Execution Removability / Non-Authority: PASS (non-authority + removability; behavioral
  equivalence across full named surface; receipt-hash identity NOT claimed — see PHASE2 report)
- Phase 3 Determinism: PASS (repeat-run, cross-process under varied PYTHONHASHSEED, shuffle
  order-independence + unsorted-renderer negative control, hash separation, purity)

## Phase 3 hashes (recorded)
- PROJECTION_IDENTITY = cgproj/patterns+domain_mappings/v1
- content_hash = 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
- render_hash  = dd76089ac116fd4e32e3a1126ace84c1c5f53a89dafe40b14b4737ef028b497a

## Scope held (Phase 3)
render.py + hash.py + standing gate only. NO docs written, NO checked-in generated artifacts, NO
explain integration, NO fidelity gate, NO completeness gate, NO Phase 4/5 work, NO renderer
features beyond determinism. render.py and hash.py import only ugk.projections.* + stdlib; Phase 2
isolation still holds (import ugk.projections loads zero execution).

## How to test by extraction (canonical archive, not loose files)
- extract; from repo root run each standing gate:
    python tools/cgproj/phase1_structural_validity_gate.py .
    python tools/cgproj/phase2_execution_removability_gate.py .
    python tools/cgproj/phase3_determinism_gate.py .
- confirm ugk/invariants.py law_hash is 546a9e90… ; confirm import ugk.projections loads no execution.

## Status
Phase 3 deterministic projection function established and integrated. Held for Phase 4 authorization.
