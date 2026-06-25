"""ugk/a1_verifier.py — A1 candidate (Plan 1G), set-valued authority verifier.

NEW module on the candidate copy. Touches NO existing file. Implements:
  - non-committed Claim(e) metadata (a plain dict, never hashed into a leaf);
  - opt-in A1 AuthorityModel posture (a1_enabled flag);
  - faithful cut-set reconstruction (re-run admissibility with candidate removed);
  - v1/v2 routing by canonicalization id;
  - fail-closed unknown-version handling;
  - multi-authority semantics via the EXISTING authority_chain list (no new
    committed key);
  - NO committed staging (stage metadata, if present, is non-committed verifier input).

Constraints honored: does not edit invariants.py, does not move law_hash, adds no
committed Claim(e) key, no temporal-PROV, no phi-zero, no master-theory change.

Failure modes surface as GateRefusal(op, reason=<A1-code>) per Plan 1C.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

try:
    from ugk.kernel import GateRefusal
except Exception:  # pragma: no cover - kernel import shape varies in isolation
    class GateRefusal(Exception):
        def __init__(self, op=None, reason=None):
            self.op = op; self.reason = reason
            super().__init__(f"GateRefusal: op={op!r} reason={reason!r}")

# Known canonicalization versions for the c_c admissibility leaf.
KNOWN_CC_VERSIONS = {"c_c.v1", "c_c.v2"}


@dataclass
class A1Posture:
    """Opt-in AuthorityModel posture (Config-layer; ADR_10). A1 verification runs
    only when enabled; default off preserves substrate neutrality."""
    a1_enabled: bool = False


@dataclass
class EffectClaim:
    """Non-committed Claim(e): the authority set a receipt ASSERTS produced e.
    This is verifier metadata only — NOT a committed leaf, never hashed."""
    claimed_authorities: tuple = field(default_factory=tuple)
    cc_version: str = "c_c.v1"
    stage_authorities: dict = field(default_factory=dict)  # non-committed staging


def route_version(cc_version: str) -> str:
    """v1/v2 routing with fail-closed on unknown (Plan 1C §7)."""
    if cc_version == "c_c.v1":
        return "v1-rule"
    if cc_version == "c_c.v2":
        return "v2-rule"
    return "FAIL-CLOSED"


def reconstruct_auth(effect_id, authority_chain, admissibility_fn) -> set:
    """Faithful cut-set reconstruction (Governor ruling 1): A in Auth(e) iff
    removing A ablates e. admissibility_fn(chain) -> bool (is e admitted under
    this chain). A is a cut-set iff admission FAILS when A is removed."""
    auth = set()
    for A in authority_chain:
        reduced = [x for x in authority_chain if x != A]
        if not admissibility_fn(reduced):   # e does NOT survive without A
            auth.add(A)                       # => A is a genuine cut-set
    return auth


def verify_a1(op, effect_id, authority_chain, claim: EffectClaim,
              admissibility_fn, posture: A1Posture):
    """A1.3 verification. Returns 'legit' or raises GateRefusal(reason=<A1-code>).
    No-op-equivalent to v1.0 on the single-authority case."""
    # Opt-in: if A1 posture off, this verifier does nothing (substrate-neutral).
    if not posture.a1_enabled:
        return "a1-disabled"

    # v1/v2 routing + fail-closed unknown version.
    route = route_version(claim.cc_version)
    if route == "FAIL-CLOSED":
        raise GateRefusal(op=op, reason="A1-UNKNOWN-CANON-VERSION")

    # Reconstruct ACTUAL Auth(e) faithfully.
    actual = reconstruct_auth(effect_id, authority_chain, admissibility_fn)
    claimed = set(claim.claimed_authorities)

    # v1 single-authority path: reduces to the v1.0 check.
    if route == "v1-rule":
        # single authority: |chain|==1 expected; the lone authority must be a cut-set.
        if len(authority_chain) == 1:
            A = authority_chain[0]
            if A not in actual:
                raise GateRefusal(op=op, reason="A1-NONCUTSET-CLAIM")
            return "legit"
        # a v1-routed receipt with multi-authority chain is itself a routing error
        raise GateRefusal(op=op, reason="A1-VERSION-MISMATCH")

    # v2 set-meet path (A1.1/A1.3).
    # Omitted authority: actual cut-set not acknowledged in claim.
    omitted = actual - claimed
    if omitted:
        raise GateRefusal(op=op, reason="A1-OMITTED-AUTHORITY")
    # Non-cut-set / padded claim: claimed authority that is not actually a cut-set.
    padded = claimed - actual
    if padded:
        raise GateRefusal(op=op, reason="A1-NONCUTSET-CLAIM")
    # Meet: every actual authority legit (here: every cut-set acknowledged) => legit.
    return "legit"
