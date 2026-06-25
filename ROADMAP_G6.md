# ROADMAP — G6 checkpoint-aware verifier architecture (tooling lane)

Project: UGK v0.1.0 — canonical head **r134** (`2a1a96e0…`)
Lane: G6 checkpoint-aware verifier architecture + implementation. Tooling-only,
frame-stationary. No law/schema/legend/registry/ledger move; no governance semantics;
no typed-effect law leg; no D_cap enforcement; no DEFER/CRISIS; no GCNL/GCML/CPVM.
Roadmap version: GOVLOG-1.

## Architecture (accepted, re-grounded from r134 archive)

- G6 is **not** an orchestrator. In bounded mode it must not spawn the GRBSA/conformance
  forest, must not found posture, must not create `genesis/` contamination.
- `certify_release.py` is the canonical release-cert orchestrator: it owns gate execution,
  founds ephemerally under isolated posture, and emits a structured release-cert **bundle**.
  It invokes G6 only **after** the bundle exists, as a final bundle verifier — G6 is not one
  of the checks it validates.
- G6 consumes the bundle: validates identities/counts/verdicts, hygiene/no-drift,
  GRBSA + MigrationReceipt summaries, and the incremental continuity frontier.
- Incremental continuity: trust the rolling attestation checkpoint; recompute only the
  unattested frontier. Full genesis→head compose is full-audit only (archival, non-blocking).
- Expectation source: conformance expectations derive from live
  `ugk.conformance.run_gates_batch.GATES`. No second hardcoded universe; mismatch fails closed.

## Phase G6 — checkpoint-aware verifier (ACTIVE — authorized lane + batching instruction)

- [x] T1 `tools/grbsa/proof_model_b.py`: add `PROOF_MODEL_VERSION`; expose B1–B4 tuple from
      `evaluate_link`; add `--full-audit` alias. (verification-surface scaffolding; ugk/ untouched)
- [x] T2 `tools/grbsa/g6_proof_cache.py` (NEW): per-link fail-closed cache + incremental frontier
      verifier (HOLD/FAIL/UNFINISHED) + full-audit helper (may RESOURCE_TIMEOUT).
- [x] T3 `tools/grbsa/g6_bundle.py` (NEW): release-cert bundle schema + pure bundle verifier
      (no subprocess gate spawning; binds expectations to live GATES).
- [x] T4 `tools/grbsa/g6_aggregate_validation_gate.py`: refactor bounded mode → pure bundle
      consumer + read-only genesis-contamination scan; heavy orchestration only behind
      explicit `--full-audit` (non-blocking).
- [x] T5 `tools/release/certify_release.py`: add `bundle` phase — found ephemerally, run GRBSA
      gates + MigrationReceipts + conformance (live GATES) + hygiene/no-drift + incremental
      frontier, emit structured bundle, invoke G6 as final bundle verifier.
- [x] T6 `tools/grbsa/g6_incremental_gate.py` (NEW): focused self-test proving cache/checkpoint/
      bundle/frontier fail-closed + HOLD + UNFINISHED + recompute behaviors.
- [x] T7 `tools/release/mint_release.sh`: exclude `*g6_proof_cache.json` (regenerable artifact).
- [x] D-G6-3 legacy callers: `verify_deep.sh` (G6 leg → 9 GRBSA leaf gates direct + G6 self-test);
      `tools/grbsa/verifier_gate.py` C11 (faithfulness vs 9 GRBSA leaf gates, not removed G6 orchestrator).

## Known environmental boundary (surfaced, not a halt)

The r134 archive's shipped `CONTINUITY_ATTESTATION.json` attests r17a..**r133** (HOLD);
`continuity_surfaces.json` declares one unattested frontier link **r133->r134** (amendment,
schema-leg). Behaviorally recomputing it needs both `ugk-r133.tar.gz` and `ugk-r134.tar.gz`.
Only r134 is present in this session, so the LIVE r134 frontier verdict is **UNFINISHED**
(honest bounded verdict, never a false PASS). The HOLD path is proven on controlled fixtures.

## Governance Log

---
### GOVLOG-1 · 2026-06-21
**Phase:** G6 — checkpoint-aware verifier
**Intent:** Open the G6 verifier lane roadmap. Records the accepted architecture (G6 as bundle
consumer; certify_release as orchestrator; incremental frontier over a rolling attestation
checkpoint; live-GATES expectation source) and the seven implementation tasks T1–T7. This is a
`testing contract change` and a `governance scope change` to the certification *substrate*
(release-cert bundle boundary) — tooling-only, frame-stationary, no kernel/law/schema/legend move.
**Changed section:** `## Phase G6 — checkpoint-aware verifier`
**SHA-256:** (computed at write; see emission command in chat)
---
### GOVLOG-2 · 2026-06-21
**Phase:** G6 — checkpoint-aware verifier (CLOSEOUT)
**Intent:** Record completion of the G6 verifier lane (T1–T7 + legacy callers), the closeout evidence
pack, and two findings surfaced under evidence-first discipline.

**Architecture decision (ratified, implemented, frame-stationary tooling):**
- G6 bounded mode is a **bundle verifier**, not a subprocess gate-forest orchestrator. Two modes:
  bounded consumer (`--bundle`+`--extract`) and non-blocking archival `--full-audit`; neither → fail-closed.
- `certify_release.py` is the canonical orchestrator: owns gate execution, founds **ephemerally** in a
  temp `UGK_GENESIS_DIR` (never the extract, never the repo cwd — verified no `genesis/` contamination),
  emits a structured release-cert **bundle**, and invokes G6 only as the **final** bundle verifier.
- Incremental continuity frontier over a rolling attestation checkpoint is the bounded continuity
  substrate; full genesis→head compose remains `--full-audit` (archival, non-blocking, may RESOURCE_TIMEOUT).
- Conformance expectations bind to the **live** `run_gates_batch.GATES` (107); no second hardcoded universe.
- Cache identity + fail-closed behavior (tamper, stale, recompute) are explicitly tested by the new
  `g6_incremental_gate.py` self-test (17/17 cases PASS; req 4,5,6,7,8,9,10,11,12,13,15,16).
- Legacy callers rebound off the removed orchestrator: `verify_deep.sh` (→ 9 GRBSA leaf gates direct +
  G6 self-test), `verifier_gate.py` C11 (→ faithfulness vs 9 leaf gates).

**Retraction:** the prior-session "verify_release marker bug" is **RETRACTED**. Evidence:
`_verdict_from_rc(0, "ALL PASS", verify_release_log)` → PASS, because the conformance batch summary
line ("107/107 passed … ALL PASS …") contains the literal marker. No fix was warranted; none was made.

**In-lane fix (closeout):** `run_bundle_phase` wrote `--emit-bundle`/`--manifest` without ensuring the
parent dir existed (FileNotFoundError on a non-existent output dir). Fixed with `os.makedirs(...,
exist_ok=True)` at both write sites (robustness of the authorized deliverable; no new semantics).

**New pre-existing finding (FLAGGED, NOT FIXED — outside lane):** `certify_release.check_attestation`
compares `composed == "HOLD"` exactly, but the shipped (byte-identical to pristine r134)
`CONTINUITY_ATTESTATION.json` carries `composed = "ContinuityChain[r17a..r128] composed=HOLD"`. The
**pristine** r134 `check_attestation` returns FAIL on the pristine extract — so `--phase quick/deep`
aggregate FAILs on attestation at baseline, independent of this lane. Proposed (unapplied) fix: compare
`"HOLD" in str(composed)` or defer to `proof_model_b._verify_attestation` (per-link HOLD + content
chaining), which the G6 frontier verifier already uses and which PASSes. `verify_release.sh` is unaffected.

**Frame stationarity:** `ugk/` and `construction/` byte-identical to pristine r134 (0 diffs); ledger 17;
all changes confined to `tools/grbsa/`, `tools/release/`, `verify_deep.sh`, and this roadmap doc.

**Certification limitation:** the live r134 continuity frontier is **UNFINISHED** (behavioural r133→r134
recompute needs both `ugk-r133.tar.gz` and `ugk-r134.tar.gz`; only r134 is present). HOLD is proven on
controlled fixtures (self-test shortcut-S). r135 mint must run where both archives are present so the
frontier resolves to HOLD. **Not minted in-session** (incomplete corpus).
**Changed section:** `## Phase G6 — checkpoint-aware verifier`
**SHA-256:** (computed at write; see emission command in chat)
---
