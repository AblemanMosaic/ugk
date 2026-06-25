# GRBSA v0.1.0 — Publication Manifest

Release label: **v0.1.0-grbsa** (overlay on UGK substrate v0.1.0, re-baselined r17a → r46).

## Invariants (verified)
- **PRIMARY continuity authority: Proof Model B (`ContinuityB`).** Substrate continuity across the
  lineage is governed by the intrinsic behavioral-continuity predicate `ContinuityB`
  (spec: `PROOF_MODEL_B.md`; gate: `proof_model_b.py`; declared surface: `continuity_surfaces.json`).
  Byte-identity is **only** the sufficient shortcut (clause S) *inside* `ContinuityB` — it is no
  longer a proof concept or a parallel authority. The composed release continuity claim is
  `ContinuityB(r17a→r46) ∧ ContinuityB(r46→r49) ∧ ContinuityB(r49→r54) ∧ ContinuityB(r54→r59) ∧ ContinuityB(r59→r60) ∧ ContinuityB(r60→r61) ∧ ContinuityB(r61→r62) ∧ ContinuityB(r62→r63) ∧ ContinuityB(r63→r64) ∧ ContinuityB(r64→r65) ∧ ContinuityB(r65→r66) ∧ ContinuityB(r66→r67) ∧ ContinuityB(r67→r68) ∧ ContinuityB(r68→r69) ∧ ContinuityB(r69→r70)`, each decided by the behavioral basis (B1–B4),
  verified directly (not by transitivity). Byte-identity baseline re-anchored r17a → r46 (the
  original "ugk/ byte-identical to r17a" invariant is superseded by the authorized hardening
  evolution); the shortcut is removed, the continuity is not.
- **Constitutional frame unmoved across r17a → r46 → r49.** Frame triad all stable:
  law_hash `546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820`,
  legend_hash `a7e2a9c9fdc2e73c403f5b191a3e84fcda06071dc2790606d8f0e2e4516552ff` (M2.3 freeze held),
  schema_hash `7ef925e063a3f402928de74a874142dba1da0c0828fb0bbfad6d47eb2bb10354`.
- **Surface re-established directly** on each candidate (not inherited by transitivity): full
  conformance batch 78/78, scale 7/7, AL clean; all 9 GRBSA behavioral gates pass; hardening gates pass.
- All GRBSA *additions* remain confined to tools/grbsa/. Inherited-substrate modifications outside
  that path are disclosed below.

## Continuity reconciliation (r17a → r46)

Authorized substrate evolution from r17a to r46 changed exactly **5 ugk/ files, 0 removed**:
  - `ugk/cli.py`            — B5/B5a (governed authority-model mutation + CLI enforcement activation), B3 (keygen creation provenance), schema_hash frame display
  - `ugk/ops.py`            — B5 (declared Tier-2 `authority_model_set`)
  - `ugk/kernel.py`         — schema_hash read-only snapshot exposure (frame binding)
  - `ugk/storage/store.py`  — B4a (single-writer RLock serialization of the receipt-append RMW), schema_hash startup fingerprint
  - `ugk/conformance/projection_continuity_gate.py` — Resolution C (constitutional-vocabulary boundary: universal/kernel ops require frozen-legend membership; deployment APPLICATION_OPS exempt, uncompressed fallback)

GRBSA establishes continuity of constitutional behavior across this re-baseline on behavioral
grounds: (1) the law is byte-identical (law_hash invariant); (2) the legend ("meaning") and
schema ("structure") frame legs are also unmoved; (3) the GRBSA behavioral attestations (G1–G5,
category-separation, separation+symmetry) hold directly on r46; (4) the substrate conformance
surface is re-established directly on r46 (78/78 + 7/7 + AL clean) rather than inherited; (5) the
changes are confined to enforcement activation, provenance, write-serialization, frame-observation,
and a gate-invariant refinement — none altering governed gate/receipt/execution semantics. Byte
identity is sufficient-but-not-necessary for behavioral continuity; the re-baseline removes the
shortcut, not the continuity. Forward continuity is composed link-by-link from the r46 anchor on the
behavioral basis (Proof Model B), not inherited by transitivity.

This reconciliation is no longer prose-only: it is **formalized and machine-checked by Proof Model B**
(`ContinuityB`, clause B), which evaluates frame-triad stability, the behavioral gates, conformance,
and change confinement directly on each candidate. The same predicate extends the lineage to
`r46 → r49` (B2 governed schema migration; `ugk/` surface confined to `ugk/storage/store.py`). Run
`python3 tools/grbsa/proof_model_b.py --compose` to reproduce the composed verdict.

## Inherited-substrate modifications (disclosed)
Pre-GRBSA release-script fixes (unchanged): (1) verify_release.sh — broken import fix (r28) +
isolated/pre-founded genesis (r38); (2) tests/README.md — stale gate count 63 → 78 (r36).

## tools/grbsa/ surface inventory
  tools/grbsa/CATEGORY_SEPARATION_PROVENANCE.md
  tools/grbsa/G1_PROVENANCE.md
  tools/grbsa/G2_PROVENANCE.md
  tools/grbsa/G3_PROVENANCE.md
  tools/grbsa/G4A_PROVENANCE.md
  tools/grbsa/G4B_PROVENANCE.md
  tools/grbsa/G4C_PROVENANCE.md
  tools/grbsa/G5_PROVENANCE.md
  tools/grbsa/G6_PROVENANCE.md
  tools/grbsa/GRBSA_MANIFEST.md
  tools/grbsa/README.md
  tools/grbsa/RECEIPT_CORE_SPEC.md
  tools/grbsa/RELEASE_GRBSA.md
  tools/grbsa/SUBSTRATE_INTERFACE.md
  tools/grbsa/category_separation_gate.py
  tools/grbsa/core_mapping.json
  tools/grbsa/g1_core_shape_gate.py
  tools/grbsa/g1_separation_symmetry_gate.py
  tools/grbsa/g2_substrate_naming_gate.py
  tools/grbsa/g3_adapter_equivalence_gate.py
  tools/grbsa/g4a_adapter_generality_gate.py
  tools/grbsa/g4b_projection_adapter_gate.py
  tools/grbsa/g4c_explain_adapter_gate.py
  tools/grbsa/g5_execution_adapter_gate.py
  tools/grbsa/g6_aggregate_validation_gate.py
  tools/grbsa/grbsa_runtime/__init__.py
  tools/grbsa/grbsa_runtime/execution_adapter.py
  tools/grbsa/grbsa_runtime/explain_adapter.py
  tools/grbsa/grbsa_runtime/gate_adapter.py
  tools/grbsa/grbsa_runtime/migration_receipt_a1.json
  tools/grbsa/grbsa_runtime/migration_receipt_determinism.json
  tools/grbsa/grbsa_runtime/migration_receipt_execution.json
  tools/grbsa/grbsa_runtime/migration_receipt_explain.json
  tools/grbsa/grbsa_runtime/migration_receipt_projection.json
  tools/grbsa/grbsa_runtime/projection_adapter.py
  tools/grbsa/service_map.json

## Per-phase canonical archive lineage (shas)
  r17a CGProj RC          4d080a4bcd4abfae0862fb5b2e7de5bcc3c03557419567ecbd3c6bb93b56d487
  r18  G1 core spec       eb16c6d16f6786383feea8979e76a8f1e017983088d79204f848e61a41672148
  r19  G2 substrate name  5c38a84c9979bb437942e454fac0d3f4d8f37654016384b0749c3797e2bf3483
  r20  G3 GateAdapter     37c552390dd4b70a529a4415f53472b4d76aa80dd3e0f11debc0374b527723ce
  r21  G4a generality     43b0c80240a6814b8f5dd5abd6c5aeed87a9fdc0d417cdcba4d8d94eb6eb32fe
  r22  G4b ProjectionAd.  9345fd87206abe814c81fc3625fd7e8d49388e47eb74006015fefbd5a8d30c32
  r23  G4c ExplainAdapter a43014b74af612c3bdb079b72ab95ea79aa4512c9bd75c9ab80887a10cffab7f
  r24  Category-Sep       655db9e4f64e374426be3f2f54f5bb8f6ab71a44a3c20e881d92f9ed150a7dda
  r25  G5 ExecutionAd.    f669ac702e49a71b47e226ad0289027f760890466fe6643e6f24030a651cfa70
  r26  G6 aggregate       ad6dfd0fb80c8a376100a47b4728b874c9f06157d955bfefedfac7129143f9b0
  r28  remediation        (de-tangled adapter runtime paths + verify_release.sh fix)
  r29  validation hygiene  (G4b/G4c validation paths de-entangled from CGProj gate scripts)
  r30  G6 batch-once + dead-code removal
  r31  anti-vacuity + robustness sweep
  r32  docs/provenance stale-language cleanup
  r33  grandchild-proof runner + consistency guard + doc sweep
  r34  G6 stops re-running substrate conformance (surface GREEN by transitivity; --full opt-in re-runs scale/AL/batch)
  r35  docs-only polish: release-notes wording aligned to r34 default/--full behavior
  r36  presentation truth/polish: manifest scope claim corrected; inherited-substrate boundary + known-issues disclosed; CLI semantics documented; tests/README 63->78
  r37  genesis/key hygiene (superseded): reconciliation-exclude approach
  r38  genesis/key ROOT-FIX: reconciliation REFUSES genesis founding artifacts; SECURITY guard fails on any key material; verify_release.sh + --full isolate+pre-found genesis (no contamination, no hang); packaging guard (this archive)

## Verification
  python tools/grbsa/g6_aggregate_validation_gate.py . --r17a <ugk-v0.1.0-cgproj-rc-r17a.tar.gz>
  Expect: GRBSA G6 AGGREGATE VALIDATION GATE: PASS

## Scope boundary
  The ratified CGProj Phase-6 gate is unmodified and validates only the CGProj surface. It fails
  by-design on the combined GRBSA tree (scope statement, not regression). The GRBSA G6 aggregate gate
  is the authority for the combined surface.
