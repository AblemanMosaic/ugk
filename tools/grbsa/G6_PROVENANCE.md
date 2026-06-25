# GRBSA Phase G6 — Canonical Archive Provenance (r26→r32) — Aggregate Validation, Remediation & Release

## Lineage (full GRBSA arc)
- r17a (CGProj RC) 4d080a4b… -> r18 G1 -> r19 G2 -> r20 G3 -> r21 G4a -> r22 G4b -> r23 G4c
  -> r24 Category-Separation -> r25 G5 -> r26 G6 (aggregate validation milestone; release head later advanced, see RELEASE_GRBSA.md)

## What G6 delivered
- tools/grbsa/g6_aggregate_validation_gate.py — runs the full GRBSA matrix + existing surface,
  verifies all 5 MigrationReceipts, reconciles the GRBSA surface vs r17a, with an anti-vacuity control.
- Regenerated migration_receipt_projection.json + migration_receipt_explain.json (see DEFECTS below).
- This provenance; the canonical release archive for this arc (current head + full lineage in GRBSA_MANIFEST.md / RELEASE_GRBSA.md).
Diff vs r25 (ignoring __pycache__): g6 gate added + the two regenerated receipts. ugk/ byte-identical
to r25 (and to r17a for all ugk/ files). law_hash unchanged.

## Option A (ratified): two independent reconciliations
GRBSA owns its OWN reconciliation vs r17a (admits ONLY tools/grbsa/; ugk/ byte-identical incl
kernel.py). The ratified CGProj Phase-6 gate is NOT modified and is NOT treated as a should-pass
component on the combined tree — it correctly FAILS by-design on the combined tree because GRBSA is
out-of-CGProj-scope. That failure is a SCOPE STATEMENT, not a regression. The GRBSA aggregate gate is
the authority for the combined surface.

## DEFECTS FOUND BY THE AGGREGATE GATE AND FIXED (release-integrity; gate did its job)
1. Corrupt MigrationReceipts (projection, explain): during G4b/G4c generation, the nested CGProj gate
   (loaded read-only) printed to STDOUT, polluting the receipt files so they were INVALID JSON
   (shipped corrupt in r22/r23, inherited to r25). The underlying adapter equivalence was real, but
   the persisted artifacts were malformed. FIX: regenerated both from the REAL adapters with nested
   stdout suppressed (contextlib.redirect_stdout); both now parse as JSON with evidence.equivalent=true.
2. Malformed G6 anti-vacuity control: used a bad repo PATH as the broken-component trigger, but gates
   resolve ugk via PYTHONPATH so a bad path does not break them (control could not fire). FIX: replaced
   with a temporary failing gate STUB (exit 1) + a passing stub (exit 0), exercising the SAME
   subprocess/exit-code path the aggregate uses. Control now fires: broken_exit=1, ok_exit=0.
Neither fix touched adapters, predicates, equivalence relations, CGProj gates, ugk/, or kernel.py.

## G6 Aggregate Validation Gate — PASS
- all 9 GRBSA gates run and exit 0.
- all 5 MigrationReceipts present and equivalent:true (a1, determinism, projection, explain, execution).
- existing surface: scale 7/7, AL 22/22, batch 78/78; CGProj component gates pass (P6 reconciliation
  excluded per Option A).
- law_hash unmoved (546a9e90…).
- GRBSA reconciliation vs r17a: added=32 (bad=0), changed=0 (ugk=0), removed=0 — only tools/grbsa/
  added; ugk/ byte-identical; kernel.py unchanged.
- anti-vacuity: a failing gate stub is detected via exit code (broken=1, ok=0).

## The GRBSA arc — what was proven
The receipt-bound continuation model (proposal -> admissibility -> receipt -> result-envelope ->
continuation) holds across FOUR domains with DIFFERENT success predicates, all on the Receipt
Sufficiency Principle (never receipt-hash identity):
- gate        -> anti-vacuity                 (G3 beachhead, G4a generality across result shapes)
- projection  -> fidelity (content_hash)      (G4b, reuses CGProj fidelity_compare read-only)
- explain     -> non-invention + completeness (G4c, reuses CGProj 5b checks read-only)
- execution   -> admit + not-failed + receipted (G5, founded authority-bearing execute(), non-invasive)
Category-Separation: each domain's success predicate rejects every other domain's receipt/envelope
pair with CLEAN False (explicit domain tag), across all 4 domains.
Throughout: ugk/ byte-identical (incl kernel.py); law_hash unchanged; legacy runners remain source of
truth (strangler — nothing retired); per-unit MigrationReceipts record dual-run equivalence.

## How to test by extraction
- extract; from repo root (writable UGK_GENESIS_DIR) run:
  python tools/grbsa/g6_aggregate_validation_gate.py . --r17a <r17a.tgz>   (PASS)
  This transitively exercises all 9 other GRBSA gates + the existing surface + reconciliation.

## Status
GRBSA arc COMPLETE. r26 was the G6-aggregate milestone; the release head has since advanced through post-review remediation (r27-r33) — see RELEASE_GRBSA.md / GRBSA_MANIFEST.md for the current canonical archive. Strict superset of the r17a CGProj RC;
CGProj surface unchanged; GRBSA added under tools/grbsa/; ugk/ and kernel.py byte-identical; law_hash
unchanged.
