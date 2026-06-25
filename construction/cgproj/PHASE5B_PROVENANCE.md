# CGProj Phase 5b — Canonical Archive Provenance (r16a) — barrier hardening

## Archive lineage
- r9-clean b98108e9… -> r10 a866d794… -> r11 37d426ad… -> r12 54e1b299… -> r13a 7db95bbb…
  -> r14a c33b1a9a… -> r15a 02d17ced… -> r16 (P5b, superseded) 24301eac… -> r16a (P5b, barrier-hardened)

## Why r16a supersedes r16 (harness hardening — claim unchanged)
The Phase 5b E4 (and the shared Phase 2 / Phase 4.5) barrier relied on a startup `sitecustomize`,
which can be SHADOWED by an earlier `sitecustomize` already on the path in some environments. When
shadowed, the barrier is not installed (sentinel absent, import not barred), so the
execution-independence proof was not portable — it passed in a clean venv but not under a competing
`sitecustomize`. FIX: the barrier is now installed via a SAME-PROCESS PRELUDE executed before
`runpy.run_module(...)` / before the rendered code runs, in `execution_jurisdiction.py`
(`barrier_prelude`, `run_module_under_barrier`, `run_code_under_barrier`). It does not depend on
sitecustomize ordering. The sentinel + positive/negative controls are preserved and now prove the
barrier active in the SAME process that ran the target.

This is a PROOF-HARNESS change only. No runtime/projection code changed; law_hash unchanged; the
claim is unchanged. ugk/ tree is byte-identical to r16.

## Files changed vs r16 (harness only; ugk/ runtime identical)
- tools/cgproj/execution_jurisdiction.py — sitecustomize barrier replaced with same-process prelude
  + runpy-based runners (run_module_under_barrier / run_code_under_barrier).
- tools/cgproj/phase2_execution_removability_gate.py — Check B uses the prelude (bars ugk.projections).
- tools/cgproj/phase4_5_jurisdiction_gate.py — Obligation B1 uses the prelude; B2 regen reference fixed.
- tools/cgproj/phase5b_explain_gate.py — E4b/E4 neg-control use the prelude.
(ugk/ runtime tree identical to r16; law_hash unchanged.)

## Portability evidence (the fix actually works)
All SEVEN standing gates PASS in BOTH:
  - a normal environment, AND
  - an environment with a COMPETING sitecustomize on the path (the review-env failure condition).
Under the competing sitecustomize, the barriers are still PROVEN ACTIVE:
  Phase 2 Check B: sentinel=True, import barred, import-succeeds-without-bar=True.
  Phase 4.5 B1: barrier_active=True (sentinel=True bar_raises=True bar_is_cause=True), identical=True.
  Phase 5b E4b: sentinel=True bar_raises=True bar_is_cause=True identical=True.

## law_hash
- preserved, unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820

## Standing gates — all PASS (7/7), normal AND competing-sitecustomize env
P1 Structural · P2 Non-Authority · P3 Determinism · P4 Fidelity · P4.5 Jurisdiction ·
P5a Docs Integration · P5b Explain.

## Phase 5b proof obligations (unchanged from r16; now portable)
E1 determinism+purity · E2 non-invention (omit ok / rephrase ok / invent fails) · E3 explain/doc
agreement · E4 bidirectional independence (now via portable same-process barrier) · E5 corpus
completeness. All negative controls fail through the real gate path.

## Narrow claim (unchanged)
Explain is a deterministic, non-inventing projection of the corpus, mutually independent of
execution, complete across docs+explain.

## How to test by extraction
- extract; from repo root run each standing gate (phase1..phase5b); confirm law_hash 546a9e90.
- portability: prepend a dir containing a trivial sitecustomize.py to PYTHONPATH and re-run the
  barrier gates (P2, P4.5, P5b) — they still PASS with barriers proven active.

## Status
Phase 5b barrier hardened and portable. STOPPED before Phase 6 as authorized.
