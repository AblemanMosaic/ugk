# Receipted Reuse Boundary — Canonical Doctrine (ALT + UGK)
SETTLED doctrine. Three-tier claim geometry for temporal reuse.

## ALT-doctrine layer (abstract claim geometry)
A provenance system partitions reuse claims into three regions:
  Tier A — guaranteeable: observable AND enforceable.
  Tier B — conditional: observable but guaranteed only under an adopted posture (promotable to A).
  Tier C — disclaimed: below the observation/receipting horizon.
This generalizes the §13 / PROV horizon idea; it is the abstract geometry, doctrine-level.

## UGK-doctrine layer (concrete instantiation)
  Tier A — receipted ∧ execute-mediated ∧ posture-adopted (rho guarantee, relative to
           C2 stamp-honesty ∧ C3 canonical-ID).
  Tier B — receipted but not execute-mediated, or posture not adopted (declared precondition).
  Tier C — below the receipting floor: CR-02 (CPython), CR-03 (SQLite WAL), CR-04 (effect
           internals), scope-blind cross-session replay. Disclaimed.
The hard limit is the receipting floor (observability), NOT ADR_10/neutrality.

## Status
SETTLED. Doctrine artifact in BOTH ALT (abstract) and UGK (concrete). Not code.
Derivation records retained in the canonical archive (docs/canonical/).
