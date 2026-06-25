# CGProj Phase 5a — Canonical Archive Provenance (r15a) — COMPLETE

## Archive lineage
- r9-clean b98108e9… -> r10 (P1) a866d794… -> r11 (lazy) 37d426ad… -> r12 (P3) 54e1b299…
  -> r13a (P4) 7db95bbb… -> r14a (P4.5) c33b1a9a… -> r15a (P5a complete): sha in detached record

## Phase 5a deliverables — COMPLETE (held items resolved by Governor)
- ugk/projections/docs.py — single docs-surface producer (per-object; pure; metadata->docs only)
- docs/patterns/<id>.md (7) + docs/domain-mappings/<id>.md (5) — per-object docs (Q1), each embedding
  corpus content_hash; domain docs cross-link to their pattern docs
- README.md — positioning sentence added near top ("UGK is not an application framework for any
  specific industry; it is a constitutional governance substrate…") + "Where this applies" section
  (workflow/system shapes, NOT industry claims)
- tools/cgproj/phase5a_docs_integration_gate.py — standing gate

Full diff vs r14a (ignoring __pycache__): README.md (changed), docs/patterns/, docs/domain-mappings/,
ugk/projections/docs.py, tools/cgproj/phase5a_docs_integration_gate.py, PHASE5A_PROVENANCE.md.
ugk/ runtime tree otherwise unchanged. law_hash unchanged.

## Held-item resolutions (Governor)
- M1 (applications/ rename): ACCEPTED — no applications/ dir exists; docs/domain-mappings/ created
  fresh; no rename.
- M2 (no-stale-claims): ACCEPTED — no doc-claims linter exists; 5a no-stale obligation = re-assert
  the existing staleness_gate / law_hash pin via the batch harness (PASS). No new linter invented.
- M3 (CGP->Platform rename): RESOLVED — no CGP-as-umbrella usage exists; CGP references are the
  observability-surface feature (README) and runtime identifiers (ugk/cgp/, cgp/verification/).
  NO rename performed. Runtime identifiers untouched. Observability surface NOT relabeled "Platform".
  README CGP references unchanged (3, same as r14a); observability-surface description intact.
  Only the README positioning deliverable was performed.

## Phase 5a Docs Integration Gate — PASS (negative controls have teeth)
- Boundary (7.3): 5/5 domain docs have front-loaded boundary with required negations.
    neg-control: checker rejects empty / after-content / missing-negation.
- Link-integrity: 20 relative cross-links resolve. neg-control: dangling target caught.
- Docs-fidelity: 12/12 docs byte-match the single producer + embed content_hash 09a63ebe…
    neg-control: body tamper breaks byte-match. (Source-of-truth rule enforced.)
- Anti-entanglement: no projection-source module reads checked-in docs (metadata->docs only).
- No-stale (carried): existing staleness/law_hash pin passes via batch harness (staleness_gate=PASS).
End-to-end teeth (verified earlier): corrupting a domain doc boundary -> Boundary + Docs-fidelity
FAIL -> GATE FAIL.

## law_hash
- preserved, unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820
- all six standing gates (P1, P2, P3, P4, P4.5, P5a) PASS against r15a.

## Scope held (Phase 5a only)
Docs surface + README positioning + 5a gate. NO 5b (explain) work. NO CGP rename. NO runtime
identifier change. NO render_all behavior change. ugk/ runtime unchanged.

## How to test by extraction
- extract; from repo root run each standing gate (phase1..phase5a); confirm law_hash 546a9e90 and
  import ugk.projections loads no execution.

## Status
Phase 5a COMPLETE. Held items M1/M2/M3 resolved per Governor. STOPPED before 5b (explain) as authorized.
