"""ugk/rho_hardened.py — Hardened Temporal-PROV ρ candidate (EXPERIMENTAL, copy-only).

Hardens the ρ probe against the three operational premises the red-team located:
  E1 (P3) boundary VALIDITY: ρ structurally checks a presented reuse boundary
     (t1>t0, binding of effect/authority at t0, t1 references it). Fail-closed on
     malformed. Boundary-set COMPLETENESS remains an enumerator precondition (C1).
  E2 (P2) freshness MATCH: admissibility input must carry an evaluation-position
     stamp; ρ requires stamp == t1. Fail-closed on mismatch/missing. Stamp HONESTY
     remains an attested precondition (C2).
  E3 (P1) canonical-ID USE: authority inputs must be canonical IDs (carry .canonical
     marker); ρ refuses raw handles. The removal test is over CanonicalID(A) so aliases
     are removed with A. Identity ASSIGNMENT remains upstream (C3).

Design: every premise gap becomes a LOUD fail-closed refusal, never a silent verdict.
NON-CORE, opt-in, copy-only. No Grundnorm/kernel/committed-surface change.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

try:
    from ugk.kernel import GateRefusal
except Exception:  # pragma: no cover
    class GateRefusal(Exception):
        def __init__(self, op=None, reason=None):
            self.op = op; self.reason = reason
            super().__init__(f"GateRefusal: op={op!r} reason={reason!r}")


@dataclass
class RhoPosture:
    rho_enabled: bool = False   # opt-in; dormant by default (non-core)


@dataclass
class CanonicalAuthority:
    """An authority referenced by its canonical ID (E3/C3). 'canonical=True' attests
    the ID was assigned by the upstream canonical-ID machinery (SCIT/invariant_core).
    A raw handle has canonical=False and ρ refuses it."""
    canonical_id: str
    canonical: bool = False
    aliases: tuple = field(default_factory=tuple)  # known aliases folded into [A]


@dataclass
class AdmissibilityStamp:
    """An admissibility RESULT stamped with the chain position it was evaluated at
    (E2/C2). 'attested_honest' models C2: whether the evaluator attests it truly
    used live S_t. ρ checks position match (E2) and requires the honesty attestation
    flag to be present (refuses if absent); it cannot verify honesty itself."""
    reachable_without_A: bool
    evaluated_at_position: int
    attested_honest: bool = False


@dataclass
class ReuseBoundary:
    """A presented reuse boundary. binding_at_t0 records whether the chain actually
    has a binding of (effect, authority) at t0 (E1 structural input)."""
    effect_id: str
    authority: CanonicalAuthority
    t0: int
    t1: int
    binding_at_t0: bool          # does a binding exist at t0? (chain fact)
    t1_references_t0: bool       # does the t1 invocation reference the t0 binding?


# ---- E1: boundary validity --------------------------------------------------
def _check_E1_boundary_validity(b: ReuseBoundary):
    if not (b.t1 > b.t0):
        raise GateRefusal(op="rho:E1", reason="E1-BOUNDARY-NONMONOTONIC")
    if not b.binding_at_t0:
        raise GateRefusal(op="rho:E1", reason="E1-NO-BINDING-AT-T0")
    if not b.t1_references_t0:
        raise GateRefusal(op="rho:E1", reason="E1-T1-DOES-NOT-REFERENCE-T0")
    return True


# ---- E2: freshness match ----------------------------------------------------
def _check_E2_freshness(b: ReuseBoundary, stamp: AdmissibilityStamp):
    if stamp is None:
        raise GateRefusal(op="rho:E2", reason="E2-NO-ADMISSIBILITY-STAMP")
    if stamp.evaluated_at_position != b.t1:
        raise GateRefusal(op="rho:E2", reason="E2-STALE-STAMP")  # evaluated at != t1
    if not stamp.attested_honest:
        raise GateRefusal(op="rho:E2", reason="E2-STAMP-UNATTESTED")  # C2 not discharged
    return True


# ---- E3: canonical-ID use ---------------------------------------------------
def _check_E3_canonical(b: ReuseBoundary):
    if not b.authority.canonical:
        raise GateRefusal(op="rho:E3", reason="E3-RAW-AUTHORITY-HANDLE")  # not canonicalized
    return True


def rho_hardened(boundary: ReuseBoundary, stamp: Optional[AdmissibilityStamp],
                 posture: RhoPosture):
    """Hardened ρ verdict. Enforces E1, E2, E3 (each fail-closed). Then applies the
    O3 cut-set test over the canonical authority. Returns 'admit' / raises GateRefusal.
    """
    if not posture.rho_enabled:
        return "rho-disabled"
    # Enforcement order: structural (E1) -> freshness (E2) -> identity (E3).
    _check_E1_boundary_validity(boundary)
    _check_E2_freshness(boundary, stamp)
    _check_E3_canonical(boundary)
    # O3 cut-set test over CanonicalID(A) (aliases folded in by the canonical ID):
    if stamp.reachable_without_A:
        # e reachable without [A] (and its aliases) at t1 => off-current-warrant
        raise GateRefusal(op="reuse:" + boundary.effect_id, reason="TEMPORAL-STALE-REUSE")
    return "admit"
