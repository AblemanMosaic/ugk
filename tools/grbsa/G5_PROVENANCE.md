# GRBSA Phase G5 — Canonical Archive Provenance (r25) — ExecutionAdapter (highest-risk)

## Lineage
- r23 (G4c) a43014b7… -> r24 (Category-Separation) 655db9e4… -> r25 (G5 ExecutionAdapter)

## What G5 proved
The receipt-bound continuation model holds for REAL authority-bearing execution. ExecutionAdapter
wraps the kernel W/G/E reactor execute() as an OBSERVER — proven equivalent to a direct execute() call
— WITHOUT editing kernel.py, originating authority, founding the kernel, or minting a parallel
receipt. This is the highest-risk phase: founded kernel, real authority, real durable-chain receipts.

## Critical posture: execute() ALREADY owns NBER-1 + authority; GRBSA records, does not add
execute() documents/enforces steps 5-7 (gate_admit receipt -> success receipt -> effect; "the receipt
is load-bearing"), plus founding (GovernanceNotFounded), declaration (BS-01), gate refusal, governor
interposition. The ExecutionAdapter is a thin observer that maps the SINGLE real receipt execute()
writes into ExecutionReceipt/ExecutionResultEnvelope shape. It adds none of execute()'s guarantees.

## What G5 delivered (additive; ugk/ AND kernel.py byte-identical)
- grbsa_runtime/execution_adapter.py — ExecutionAdapter + ExecutionReceipt/ExecutionResultEnvelope
  (domain-tagged 'execution') + execution_success() predicate. OBSERVES execute()'s receipt via
  store.receipt_count()/all_receipts(); mints nothing.
- grbsa_runtime/__init__.py — additive exports.
- grbsa_runtime/migration_receipt_execution.json — dual-run equivalence.
- g5_execution_adapter_gate.py — the G5 gate.
- category_separation_gate.py — EXTENDED to the 4th domain (execution): 12 cross-pairs + 4 positives.
Diff vs r24 (ignoring __pycache__): only the items above. ugk/ byte-identical to r24; kernel.py
UNMODIFIED. law_hash unchanged.

## Ratified Q1/Q2/Q3
- Q1: target op='crp_evidence' (existing conformance-style, gate=True, trivial deterministic effect);
  no extra authority invented. (crp_evidence is a universal op; founding exercised separately via a
  Tier-2 op in neg-ii.)
- Q2: adapter OBSERVES and maps the single real receipt(s) execute() writes; mints NO parallel
  receipt. Equivalence on shape+semantics, never receipt-hash.
- Q3: gate refusal is first-class — refused execution is a valid ExecutionReceipt with
  execution_success=False, not an adapter error.

## Object model (Execution domain — 4th)
- ExecutionReceipt = Receipt Core + {op, authority_ref, gate_outcome, domain:'execution'}
- ExecutionResultEnvelope = Envelope Core + {effect_result_ref, failed, receipts_written, domain:'execution'}
- execution_success = domain match + gate_outcome=='admit' + not failed + receipts_written>=1.

## G5 Execution-Adapter Gate — PASS (negative controls fire through the real path)
- equivalence: direct execute() == adapter (admit + failed + receipts-written shape; written=2 = gate_admit+outcome).
- execution_success on honest founded path.
- adapter mints NO parallel receipt (observed count == direct count).
- NBER-1: receipt observed before effect (execute() owns the order).
- category boundary: failed/receipts_written in Envelope, not Receipt.
- NEG-i gate refusal first-class (valid receipt, success=False); NEG-ii unfounded Tier-2 op refused
  identically (adapter does NOT found the kernel); NEG-iii authority-origination REFUSED; NEG-iv
  posture op REFUSED; NEG-v zero-receipt vacuous NOT success.

## Category-Separation extended to 4 domains — PASS
12 cross-pair CLEAN-False rejections (gate/projection/explain/execution) + 4 native positives + mis-tag
negative controls. execution_success rejects gate/projection/explain pairs and vice versa.

## Migration posture (strangler — most conservative)
MigrationReceipt(execution) records dual-run equivalence. Legacy execute() REMAINS the ONLY execution
path and source of truth. Execution is NOT made routable even in the eligible sense without a separate
later ratification (authority is involved). Nothing retired.

## No regression / behavior invariance
- ugk/ byte-identical to r24; kernel.py UNMODIFIED; all CGProj + ugk/projections unmodified.
- All 9 GRBSA gates PASS; scale 7/7; AL 22/22; batch 78/78. (G5 founds a kernel IN-TEST only, as
  existing execute()-touching conformance gates do — not a runtime change.)
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## How to test by extraction
- extract; from repo root (with a writable UGK_GENESIS_DIR) run:
  python tools/grbsa/g5_execution_adapter_gate.py .  (PASS), plus g1..g4c + category_separation;
  confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ (incl kernel.py) unchanged.

## Status
GRBSA G5 complete: ExecutionAdapter proven equivalent over real founded execute(), non-invasively,
with authority/founding/refusal controls. Four domains separated. NEXT: G6 (aggregate validation + repackage).
