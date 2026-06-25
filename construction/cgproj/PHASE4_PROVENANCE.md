# CGProj Phase 4 — Canonical Archive Provenance (r13)

## Archive lineage
- r9-clean baseline: b98108e93f41cd9e83ebd24088ead9c534f853ccdfac26b70fb0694d63d04aa0
- r10 (Phase 1 CGProj files): a866d79443d2275eee3bb6f8b94b714cb99bfd417ecede0480f31dfe7737f6b2
- r11 (lazy ugk/__init__.py): 37d426ad016d0168608cfe3b89acf479c9d1b5b5b725a04a9e6498ae8f0370cb
- r12 (Phase 3 renderer+hash): 54e1b29999d38ad9b0e36ab09600c9ce46de9779e9973fc4e5d493d46c3b5921
- r13 (this archive: r12 + Phase 4 fidelity verification): sha in detached record

## Files added in r13 (additive only; no execution-jurisdiction file modified)
- ugk/projections/generate.py                          — single artifact producer (header + render)
- ugk/projections/generated/patterns.generated.md      — checked-in artifact, embeds content-hash
- ugk/projections/generated/domain_mappings.generated.md — checked-in artifact, embeds content-hash
- tools/cgproj/phase4_fidelity_gate.py                 — Phase 4 standing Fidelity Gate
- tools/cgproj/PHASE4_PROVENANCE.md                    — this file
Full additive diff vs r12 (ignoring __pycache__) — exactly these four paths, nothing else:
  - ugk/projections/generate.py
  - ugk/projections/generated/   (the two artifacts)
  - tools/cgproj/phase4_fidelity_gate.py
  - tools/cgproj/PHASE4_PROVENANCE.md
Of these, the runtime/projection subset is ugk/projections/generate.py + ugk/projections/generated/;
the tools/cgproj files are the standing gate + this provenance (non-runtime). No file modified;
law_hash unchanged.

## law_hash
- preserved, unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820

## Standing gates — all PASS against this tree
- Phase 1 Structural Validity: PASS
- Phase 2 Execution Removability / Non-Authority: PASS (receipt-hash identity NOT claimed)
- Phase 3 Determinism: PASS
- Phase 4 Fidelity: PASS (positive + 3 negative controls + vacuity guard, one shared comparator)

## Phase 4 fidelity claim (what IS proven)
Each checked-in artifact byte-matches the freshly-rendered output AND embeds a content-hash equal
to content_hash(current metadata). Source of truth is ALWAYS the governed metadata; artifacts are
never read back as source. content_hash embedded = 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b.

## Anti-vacuity (the controls have teeth)
Shared comparator fidelity_compare() used by the real check AND every control:
- positive: real artifacts byte+hash match -> PASS
- neg-1 body tamper (real on-disk byte flip) -> byte-match FAIL
- neg-2 hash tamper (one hex char) -> embedded-hash-match FAIL (header still wellformed)
- neg-3 stale-metadata drift (mutated metadata vs unchanged disk, mutation confirmed to change
  expected output) -> byte-match FAIL
- vacuity guard: >=1 artifact present and compared, each embedded hash present and 64-hex

## Scope held (Phase 4 only)
generate.py + 2 artifacts + Fidelity Gate. NO explain integration, NO corpus completeness, NO
Jurisdiction Gate (4.5), NO documentation-surface integration (Phase 5), NO renderer capability
expansion, NO execution-surface change. Artifacts live under ugk/projections/generated/ (NOT docs/)
to stay self-contained and Phase-5-independent. generate.py imports only ugk.projections.* + stdlib;
Phase 2 isolation still holds (import ugk.projections loads zero execution; generated .md files are
inert, imported by nothing).

## How to test by extraction (canonical archive, not loose files)
- extract; from repo root run each standing gate:
    python tools/cgproj/phase1_structural_validity_gate.py .
    python tools/cgproj/phase2_execution_removability_gate.py .
    python tools/cgproj/phase3_determinism_gate.py .
    python tools/cgproj/phase4_fidelity_gate.py .
- confirm ugk/invariants.py law_hash is 546a9e90… ; confirm import ugk.projections loads no execution.

## Status
Phase 4 fidelity verification established and integrated. STOPPED before Phase 4.5 (Jurisdiction
Gate) as authorized. No Phase 4.5/5/explain/completeness work performed.
