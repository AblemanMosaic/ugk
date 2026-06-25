"""ugk/will.py — WillChecker: R_int coverage fixpoint (Grundnorm 444).

WILL-S-02: R_int is the least fixpoint of declared ops under admissible
           production_edges. Terminates on finite op graph. Deterministic.
WILL-S-03: Coverage is fail-closed when require_intent=True:
           no active intent → WL-005; op outside R_int → WL-001.

Coverage posture (Design Decision 1, Phase 13):
  conservative_fallback (default): ops proceed without intent_ref.
  fail_closed: activated by kernel.set_will_store(ws, require_intent=True).
  Will coverage applies to APPLICATION_OPS only (KERNEL_OPS and UNIVERSAL_OPS
  are exempt — DI-WILL-09 analog: infrastructure cannot be subject to will
  coverage without infinite regress).

The R_int fixpoint (will_closure_ref.py, ALT codex_will):
  covered = {ops declared in active_declarations}
  repeat:
      new = {product(t) for t in production_edges if t.source in covered}
      covered |= new
  until fixpoint

closure_depth=None  →  full re-derivable closure (ALT §18-faithful)
closure_depth=0     →  literal match (Policy-Zones mode)
closure_depth=N     →  cost-bounded re-derivation
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ugk.intent import (
    IntentDeclaration, WL_001, WL_002, WL_003, WL_004, WL_005,
)

COVERED = "COVERED"
OUTSIDE = "OUTSIDE"


@dataclass(frozen=True)
class CoverageOutcome:
    """Result of WillChecker.covers()."""
    status:       str            # COVERED | OUTSIDE
    refusal_code: Optional[str]  # WL_001..005 when OUTSIDE; None when COVERED
    intent_ref:   Optional[str]  # declaration_hash when COVERED; None when OUTSIDE


class WillChecker:
    """Computes intent-coverage for a given op against active IntentDeclarations.

    Deterministic monotone fixpoint over the finite APPLICATION_OPS graph.
    production_edges: deployer-declared in 644 tier. Default: {} (literal set).
    """

    def covers(
        self,
        op:                   str,
        active_declarations:  list[IntentDeclaration],
        production_edges:     Optional[dict[str, set]] = None,
        depth:                Optional[int] = None,
    ) -> CoverageOutcome:
        """Compute R_int and check op coverage.

        Check order (WILL-CC-01 precedence):
          WL-002 (resolves?) → WL-003 (not revoked?) → WL-004 (scope valid?)
          → WL-005 (any active intent?) → WL-001 (this op covered?)

        For UGK usage active_declarations are already filtered (revoked=0),
        so WL-002 and WL-003 are pre-cleared by IntentStore.active_declarations().
        """
        edges = production_edges or {}

        # Seed: all ops declared in active (unrevoked) declarations
        seed: set[str] = set()
        for decl in active_declarations:
            seed.update(decl.declared_ops)

        # WL-005: no active intent at all
        if not seed:
            return CoverageOutcome(OUTSIDE, WL_005, None)

        # Compute R_int (monotone fixpoint, DI-WILL-02)
        covered = self._closure(seed, edges, depth)

        # WL-001: op not in closure
        if op not in covered:
            return CoverageOutcome(OUTSIDE, WL_001, None)

        # COVERED: find the smallest covering declaration (for intent_ref)
        cover_hash = self._find_cover(op, active_declarations, edges, depth)
        return CoverageOutcome(COVERED, None, cover_hash)

    def _closure(
        self,
        seed:  set[str],
        edges: dict[str, set],
        depth: Optional[int],
    ) -> set[str]:
        """Deterministic monotone fixpoint. Terminates on finite graph."""
        covered = set(seed)
        steps = 0
        while depth is None or steps < depth:
            new: set[str] = set()
            for src, targets in edges.items():
                if src in covered:
                    new.update(targets)
            new -= covered
            if not new:
                break
            covered |= new
            steps += 1
        return covered

    def _find_cover(
        self,
        op:           str,
        declarations: list[IntentDeclaration],
        edges:        dict[str, set],
        depth:        Optional[int],
    ) -> str:
        """Return the declaration_hash of the smallest covering declaration."""
        # Prefer direct cover (depth=0) over closure-derived cover
        for decl in sorted(declarations, key=lambda d: len(d.declared_ops)):
            if op in decl.declared_ops:
                return decl.declaration_hash
        # Closure-derived cover
        for decl in sorted(declarations, key=lambda d: len(d.declared_ops)):
            closure = self._closure(set(decl.declared_ops), edges, depth)
            if op in closure:
                return decl.declaration_hash
        return ""


__all__ = ["WillChecker", "CoverageOutcome", "COVERED", "OUTSIDE"]
