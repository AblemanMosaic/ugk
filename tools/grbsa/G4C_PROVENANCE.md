# GRBSA Phase G4c — Canonical Archive Provenance (r23) — ExplainAdapter

> **SUPERSEDED MECHANISM NOTE (r28/r29):** This provenance records the ORIGINAL mechanism, in which the
> adapter obtained reusable logic by loading the CGProj gate script (read-only module load). That
> mechanism was REMOVED in r28/r29: the adapter now sources from import-clean `ugk.projections` library
> surfaces and reconstructs the predicate in-lane, executing NO gate script; fidelity is validated by an
> import-clean bounded fixture. Read "reuse … directly / read-only module load" below as historical, not
> current. Current behavior: see migration_receipt_*.json and RELEASE_GRBSA.md (r28–r33).

## Lineage
- r21 (G4a) 43b0c802… -> r22 (G4b ProjectionAdapter) 9345fd87… -> r23 (G4c: ExplainAdapter)

## What G4c proved
The THIRD distinct success predicate and the load-bearing one. ExplainAdapter wraps the existing
CGProj explain surface as a receipt-bound continuation; success = NON-INVENTION + object-level
COMPLETENESS + non-vacuity. Rule (verbatim from CGProj 5b): explain may OMIT, may REPHRASE, may NOT
INVENT. Proven equivalent to the legacy 5b explain checks.

GRBSA now demonstrates all THREE distinct success predicates inside ONE receipt-bound continuation
shape: gate=anti-vacuity, projection=fidelity, explain=non-invention+completeness.

## DEFECT FOUND AND FIXED DURING G4c (hard-stop did its job)
First G4c run: the load-bearing injected-invented-claim control FAILED to fire (violations=0); the
gate HARD-STOPPED rather than launder a false non-invention proof. Diagnosis: the negative-control
INJECTION SEAM was malformed — it appended a mis-cased extra line ("Primitives: …"), but the real
checker cited_primitives reads the FIRST lowercase "primitives: " line, ' | '-delimited. The checker
never saw the injection. Defect was in the test seam ONLY — not the ExplainAdapter success semantics,
not the CGProj checker. Surgical fix: append the invented primitive to the EXISTING "primitives: "
line in the real ' | '-delimited format. Re-run: violations=1 through the UNMODIFIED checker; equiv +
success FAIL as required. No change to 5b gate, ugk/, explain semantics, or success predicate.

## What G4c delivered (additive; ugk/ untouched, 5b gate + explain.py unmodified)
- tools/grbsa/grbsa_runtime/explain_adapter.py — ExplainAdapter + ExplainReceipt/ExplainResultEnvelope
  + explain_success() predicate. REUSES 5b invention_violations + corpus truth sets + explain surface
  DIRECTLY (read-only module load: argv neutralized, SystemExit swallowed) — no reimplementation. [ORIGINAL mechanism — superseded r28/r29; adapter now reconstructs in-lane, no gate-script load]
- tools/grbsa/grbsa_runtime/__init__.py — additive exports.
- tools/grbsa/grbsa_runtime/migration_receipt_explain.json — dual-run equivalence.
- tools/grbsa/g4c_explain_adapter_gate.py — the G4c gate (load-bearing control = hard stop).
Diff vs r22 (ignoring __pycache__): only the four items above. ugk/ byte-identical to r22. CGProj
phase5b_explain_gate.py + ugk/projections/explain.py UNMODIFIED. law_hash unchanged.

## Ratified scope (split cadence) + Q1/Q2
- ExplainAdapter ONLY. Category-Separation Gate is the next step (now meaningful: 3 adapter domains).
- Q1 [ORIGINAL — superseded r28/r29]: reuse 5b's checks via the same read-only module load used in G4b. No copy/reimplementation; 5b
  gate not modified.
- Q2: completeness is OBJECT-LEVEL (explain_keys vs corpus pattern:/domain: key set). Within-object
  omission allowed. Field-level completeness NOT required.
- No new explain semantics, no live routing, no retirement, no ugk/ change.

## Object model (Explain domain)
- ExplainReceipt = Receipt Core + {explain_identity, corpus_signature}  (WHY admissible; corpus_signature
  = sorted corpus_keys, the object set explain is accountable to)
- ExplainResultEnvelope = Envelope Core + {invention_violations, covered_keys, missing_keys}  (WHAT found)
- explain_success(receipt, envelope) = no invention_violations AND covered == corpus_signature AND no
  missing AND >=1 corpus object. A PREDICATE over receipt+envelope, in NEITHER core nor extension.

## Equivalence (Receipt Sufficiency, NOT receipt-hash identity)
identical invention-violation set + identical corpus coverage (covered + missing) + identical overall
verdict. Detail/prose excluded (rephrasing allowed). Receipt-hash NOT asserted (chain hash binds ts).

## G4c ExplainAdapter Gate — PASS (negative controls fire through the real adapter path)
- equivalence: identical invention set + coverage + overall verdict (legacy == adapter; 12 objects).
- success semantics = non-invention + completeness (honest corpus passes; 0 violations, 0 missing).
- NBER-1: receipt minted before explain continuation (order: receipt_minted, effect_ran).
- category boundary: invention/coverage findings in ResultEnvelope, not Receipt.
- reuse (ORIGINAL, superseded r28/r29): adapter then loaded 5b invention_violations; NOW reconstructs non-invention in-lane from import-clean ugk.projections.{explain,patterns,domain_mappings}, no gate-script execution.
- NEG-i receipt-after-effect FAILS NBER-1.
- NEG-ii LOAD-BEARING: injected invented claim -> violations=1 through unmodified checker -> equiv +
  success FAIL. (This is the control that hard-stopped the first run; now fires correctly.)
- NEG-iii dropped corpus object FAILS completeness/equivalence (missing=1).
- NEG-iv posture op REFUSED.
- NEG-v zero-object vacuous is NOT success.
- legacy CGProj 5b explain gate still PASSES standalone (unmodified).

## Migration posture (strangler — unchanged)
MigrationReceipt(explain) records dual-run equivalence. Legacy 5b gate REMAINS source of truth;
explain unit ELIGIBLE (not required) for routing only after G4c passes from clean extraction. No live
routing. Nothing retired.

## No regression / behavior invariance
- ugk/ byte-identical to r22; CGProj 5b gate + ugk/projections/explain.py UNMODIFIED; 5b passes standalone.
- All 7 GRBSA gates PASS; scale 7/7; AL 22/22; batch 78/78.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/g4c_explain_adapter_gate.py . (PASS),
  plus g1..g4b gates; confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ unchanged.

## Status
GRBSA G4c complete: ExplainAdapter proven equivalent with NON-INVENTION + COMPLETENESS success
semantics; load-bearing control fires. Three adapter domains now exist. NEXT: Category-Separation Gate.
