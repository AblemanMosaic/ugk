# CGProj Phase 6 — Canonical Release-Candidate Provenance (r17)

## Archive lineage (final)
- r9-clean b98108e9… -> r10 a866d794… -> r11 37d426ad… -> r12 54e1b299… -> r13a 7db95bbb…
  -> r14a c33b1a9a… -> r15a 02d17ced… -> r16a 33ba422f… -> r17 (v0.1.0-cgproj RELEASE CANDIDATE)

## Objective
Prove the whole release is intact with CGProj present; reconcile against r9-clean; emit the final
candidate tarball. No runtime/projection code change in Phase 6 (validation + repackage only).

## Phase 6 Full Validation Gate — PASS (21 components; anti-vacuous)
Projection gates (all ran + passed): P1 structural, P2 non-authority, P3 determinism, P4 fidelity,
  P4.5 jurisdiction, P5a docs+Boundary(7.3), P5b explain+Explain-Fidelity(7.5)+Completeness(7.6).
Existing UGK surface: 78/78 conformance · 39/39 M2 vectors · A1 7/7 · rho fixtures 14 ALL PASS ·
  scale conformance 7/7 · scale AL 22/22 · batch completes (no hang).
law_hash: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820 (unchanged).
Anti-vacuity: each component asserted to have RUN (verdict produced), and a negative control
  (--self-fail-demo) flips the aggregate to FAIL — teeth confirmed.

## execute() equivalence — OPTION B (ratified conditional A->B; claim NOT widened)
Receipt-hash identity was attempted non-invasively and is NOT provable without an execution-surface
change, therefore NOT claimed:
  - Receipts embed timestamp = time.time() (ugk/storage/store.py:344), AND
  - the chain hash semantic_hash = dm_s03(...) binds `ts` as a hashed field (ugk/storage/binding.py:84).
  => receipt-hash IDENTITY between a baseline run and a CGProj run is not well-defined non-invasively
     (each run differs by wall clock); making it well-defined would require excluding/freezing `ts` in
     receipt emission = execution-surface change (forbidden). Per the ratified conditional, fell back
     to Option B. NO execution code was changed.
WHAT IS PROVEN (Option B): execute()-bearing surface (the 78-gate batch exercises execute() across
  governed ops) passes IDENTICALLY (78/78) with CGProj present AND with ugk/projections/ DELETED —
  behavioral PASS-equivalence. Receipt-hash identity remains DEFERRED to a separately authorized
  mechanism (would require a deterministic/clamped-ts receipt mode); it is not claimed here.

## Reconciliation vs r9-clean (b98108e9…)
Additive-only: added=38 paths, ALL under {ugk/projections/, docs/patterns/, docs/domain-mappings/,
  tools/cgproj/}; 0 disallowed additions; 0 removals.
Changed vs r9-clean = exactly 2 files:
  - ugk/__init__.py — the ratified lazy-init (the SINGLE authorized runtime delta; law_hash unchanged).
  - README.md — Phase 5a positioning sentence + "Where this applies" (docs/positioning only).
No other runtime file differs from r9-clean. Candidate = validated core + ratified CGProj additions.

## Hygiene
Packaged tree clean: no .pyc/.egg-info; __pycache__ excluded from the deterministic tarball
(--sort=name --owner=0 --group=0 --numeric-owner, __pycache__/*.pyc/.git/*.egg-info excluded).

## Standing artifacts
tools/cgproj/: execution_jurisdiction.py + phase{1,2,3,4,4_5,5a,5b,6}_*.py gates +
  PHASE{1,3,4,4_5,5A,5B,6}_PROVENANCE.md. All 8 gates pass from clean extraction.

## Narrow claim (final, exactly supported)
CGProj is integrated additively as a NON-AUTHORITATIVE constitutional projection jurisdiction:
deterministic, fidelity-checked, jurisdiction-independent of execution (regeneration-independent),
with docs+explain surfaces that may omit/rephrase but not invent, complete across both surfaces. The
whole release passes its full validation surface with CGProj present; law_hash unchanged. execute()
behavioral pass-equivalence proven; receipt-hash identity NOT claimed (deferred, reason recorded).

## Stop condition status
No regression in the existing surface (78/78, vectors, A1, rho, scale, law_hash all intact). The core
is not compromised by CGProj. Release candidate stands.

## How to test by extraction
- extract; from repo root run: python tools/cgproj/phase6_full_validation_gate.py . --r9 <r9-clean tgz>
  (and each standing gate phase1..phase5b). Confirm law_hash 546a9e90 and import ugk loads no execution.

## Status
Phase 6 complete. v0.1.0 CGProj integration COMPLETE pending Governor sign-off. No post-v0.1.0 hardening.

## Release-hygiene: explicit clean-exit verification (from clean extraction)
Every standing gate was run from a clean extraction of the release candidate, timeout-bounded to
catch hangs, and checked for EXIT CODE (not merely a printed PASS line):
  phase1_structural_validity_gate      exit=0   (~0.4s)
  phase2_execution_removability_gate   exit=0   (~16s)
  phase3_determinism_gate              exit=0   (~0.3s)
  phase4_fidelity_gate                 exit=0   (~0.1s)
  phase4_5_jurisdiction_gate           exit=0   (~4.5s)
  phase5a_docs_integration_gate        exit=0   (~3.5s)  -- confirmed: exits cleanly, no hang after PASS
  phase5b_explain_gate                 exit=0   (~4.1s)
  phase6_full_validation_gate          exit=0   (~35s)
A hang would have produced exit=124 (timeout); none did. Phase 5a spawns the batch runner for the
carried no-stale (law_hash pin) check and returns cleanly. All gates exit 0.
