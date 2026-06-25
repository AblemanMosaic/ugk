# GRBSA Phase G4b — Canonical Archive Provenance (r22) — ProjectionAdapter

> **SUPERSEDED MECHANISM NOTE (r28/r29):** This provenance records the ORIGINAL mechanism, in which the
> adapter obtained reusable logic by loading the CGProj gate script (read-only module load). That
> mechanism was REMOVED in r28/r29: the adapter now sources from import-clean `ugk.projections` library
> surfaces and reconstructs the predicate in-lane, executing NO gate script; fidelity is validated by an
> import-clean bounded fixture. Read "reuse … directly / read-only module load" below as historical, not
> current. Current behavior: see migration_receipt_*.json and RELEASE_GRBSA.md (r28–r33).

## Lineage
- r20 (G3) 37c55239… -> r21 (G4a) 43b0c802… -> r22 (G4b: ProjectionAdapter, success=FIDELITY)

## What G4b proved
The FIRST adapter whose success semantics is NOT anti-vacuity. The ProjectionAdapter wraps the
existing CGProj fidelity surface as a receipt-bound continuation; success = FIDELITY (no content_hash
drift + every per-artifact fidelity_ok + >=1 artifact). Proven equivalent to the legacy CGProj
fidelity gate. This is the real test that the domain boundary IS the success semantics, generalized
beyond the gate predicate.

## What G4b delivered (additive; ugk/ untouched, CGProj gate unmodified)
- tools/grbsa/grbsa_runtime/projection_adapter.py — ProjectionAdapter + ProjectionReceipt/
  ProjectionResultEnvelope extensions + projection_success() predicate. REUSES CGProj fidelity_compare
  DIRECTLY (read-only module load: argv neutralized, SystemExit swallowed) — no reimplementation. [ORIGINAL mechanism — superseded r28/r29; adapter now reconstructs in-lane, no gate-script load]
- tools/grbsa/grbsa_runtime/__init__.py — additive exports.
- tools/grbsa/grbsa_runtime/migration_receipt_projection.json — dual-run equivalence.
- tools/grbsa/g4b_projection_adapter_gate.py — the G4b gate.
Diff vs r21 (ignoring __pycache__): only the four items above. ugk/ byte-identical to r21. CGProj
phase4_fidelity_gate.py UNMODIFIED. law_hash unchanged.

## Ratified scope (split cadence) + Q1/Q2
- ProjectionAdapter ONLY. No ExplainAdapter (G4c). No Category-Separation gate yet (post-G4c).
- Q1: reuse tools/cgproj/phase4_fidelity_gate.py's fidelity_compare DIRECTLY (no copy/reimplementation).
- Q2: content_hash from the live ugk.projections.hash.content_hash() anchor; each artifact's embedded
  hash must match it (exactly the CGProj fidelity rule).
- No new projection semantics, no live routing, no retirement, no ugk/ change.

## Object model (Projection domain)
- ProjectionReceipt = Receipt Core + {projection_identity, content_hash}  (WHY admissible to verify)
- ProjectionResultEnvelope = Envelope Core + {per_artifact:[(name, fidelity_ok)], content_hash}  (WHAT found)
- projection_success(receipt, envelope) = envelope.content_hash == receipt.content_hash (no drift)
  AND all per-artifact fidelity_ok AND len(per_artifact) >= 1. A PREDICATE over receipt+envelope,
  in NEITHER core nor extension.

## Equivalence (Q3; Receipt Sufficiency, NOT receipt-hash identity)
identical content_hash + identical per-artifact fidelity verdicts (dict mapping; drop/add can't hide)
+ identical overall verdict. Detail excluded. Receipt-hash NOT asserted (chain hash binds ts).

## G4b ProjectionAdapter Gate — PASS (negative controls fire through the real adapter path)
- equivalence: identical content_hash + per-artifact verdicts + overall verdict (legacy == adapter).
- success semantics = fidelity predicate (content_hash + per-artifact), not trivially true.
- NBER-1: ProjectionReceipt minted before the fidelity continuation (order: receipt_minted, effect_ran).
- category boundary: per-artifact verdicts in ResultEnvelope, not Receipt.
- reuse (ORIGINAL, superseded r28/r29): adapter then loaded CGProj fidelity_compare; NOW reconstructs fidelity in-lane from import-clean ugk.projections.{generate,hash}, no gate-script execution.
- NEG-i receipt-after-effect FAILS NBER-1; NEG-ii content_hash drift FAILS equivalence AND success;
  NEG-iii suppressed per-artifact verdict FAILS equivalence; NEG-iv posture op REFUSED;
  NEG-v zero-artifact vacuous is NOT success.
- legacy CGProj fidelity gate still PASSES standalone (unmodified).

## Migration posture (strangler — unchanged)
MigrationReceipt(projection) records dual-run equivalence. Legacy fidelity gate REMAINS source of
truth; projection unit ELIGIBLE (not required) for routing only after G4b passes from clean
extraction. No live routing. Nothing retired.

## No regression / behavior invariance
- ugk/ byte-identical to r21; CGProj phase4 gate + ugk/projections/ UNMODIFIED; phase4 passes standalone.
- All 6 GRBSA gates PASS; scale 7/7; AL 22/22; batch 78/78.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/g4b_projection_adapter_gate.py . (PASS),
  plus g1..g4a gates; confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ unchanged.

## Status
GRBSA G4b complete: ProjectionAdapter proven equivalent with FIDELITY success semantics. STOPPED
before G4c (ExplainAdapter) as scoped.
