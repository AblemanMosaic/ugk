# GRBSA — Category-Separation Gate — Canonical Archive Provenance (r24)

## Lineage
- r22 (G4b) 9345fd87… -> r23 (G4c ExplainAdapter) a43014b7… -> r24 (Category-Separation)

## What this phase proved
The anti-collapse property across all three adapter domains: NO domain's success predicate validates
another domain's (receipt, envelope) pair. Gate (anti-vacuity), Projection (fidelity), and Explain
(non-invention+completeness) share the receipt-bound continuation shape and cores, but their success
predicates are CATEGORY-CONFINED.

## Design decision (ratified Option B) — principled separation, not accidental
Empirical probe (pre-implementation) showed separation already held but ONLY by accidental field-shape
mismatch: cross-feeds raised AttributeError because each predicate touched fields a foreign envelope
lacked. Per ratification, this is NOT the mature boundary. Option B adopted:
- ADDITIVE `domain` tag on every receipt/envelope extension ('gate'/'projection'/'explain'),
  defaulted so all existing construction sites are unaffected.
- Each *_success predicate checks the tag FIRST and returns a CLEAN False on mismatch (Q2: rejection
  must be clean False, never 'False or raises').

## What this delivered (additive; ugk/ untouched)
- gate_adapter.py / projection_adapter.py / explain_adapter.py — ADDITIVE `domain` field on the two
  extensions each + a tag guard (clean-False) at the top of each predicate. No other logic changed.
- tools/grbsa/category_separation_gate.py — the new gate.
Diff vs r23 (ignoring __pycache__): only the three adapter files (additive tag+guard) + the new gate.
ugk/ byte-identical to r23. law_hash unchanged.

## Category-Separation Gate — PASS
- 3 native positives: gate/projection/explain _success each accepts its OWN honest pair (separation
  is non-vacuous; predicates do not reject everything).
- 6 cross-pair rejections (CLEAN False, no exception): gate_success rejects projection+explain;
  projection_success rejects gate+explain; explain_success rejects gate+projection.
- NEG (tag guard does the work): a Gate envelope MIS-TAGGED 'projection' (all fields still valid) is
  caught by gate_success -> clean False. Symmetric mis-tagged RECEIPT also caught. Proves separation
  is by TAG, not by field-shape accident.
- control: correctly-tagged native gate pair still passes (guard not over-rejecting).
- every receipt/envelope carries an explicit domain tag.

## No regression / behavior invariance
- ALL prior equivalence gates still PASS with the additive tag: G3, G4a, G4b, G4c (verified — the tag
  is non-breaking because those gates exclude receipt-hash and compare only domain findings).
- ugk/ byte-identical to r23; CGProj gates + ugk/projections/ unmodified.
- All 8 GRBSA gates PASS; scale 7/7; AL 22/22; batch 78/78.
- law_hash unchanged: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820.

## Structural argument now closed
Cores shared (G1) | extensions domain-specific (G3/G4b/G4c) | predicates domain-confined (this gate).
Combined with G1 Receipt!=Envelope separation/symmetry, the receipt/envelope category structure is
fully separated: a receipt admissible-and-successful in one category is not silently honored by another.

## How to test by extraction
- extract; from repo root run: python tools/grbsa/category_separation_gate.py . (PASS),
  plus g1..g4c gates; confirm scale 7/7 + AL 22/22 + batch 78/78 + law_hash 546a9e90 + ugk/ unchanged.

## Status
GRBSA Category-Separation complete: three domains proven category-confined by explicit tag with clean-
False rejection. STOPPED before G5 as scoped.
