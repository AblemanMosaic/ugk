"""ugk/capabilities.py — Capability attenuation over G_c (Roadmap W-08).

M2.3i replaces the M2.2-era `capabilities=[]` empty-list proxy in H_c
with a real attenuated capability set computed from the canonical path
through G_c. Each AuthorityEdge.capability_set declares what the issuer
grants to the subject; attenuation rules require that a child's set be
a subset of the issuer's effective set at every hop.

The Governor (root of G_c) is treated as holding the full
CAPABILITY_VOCABULARY (constitutional declaration in invariants.py).
Walking the canonical path applies edge capability_sets in order; any
edge whose capability_set escapes the parent's effective set fails with
CapabilityEscalation (M2.3a ERROR_CODES, previously unused).

Public surface:
  attenuates(parent_set, child_set) → bool
      Pure predicate: True iff child_set ⊆ parent_set.

  compute_effective_capabilities(path) → (frozenset|None, error|None)
      Walks the path, applying attenuation. Returns the effective
      capability set at the path's terminus, or (None, "CapabilityEscalation")
      on the first attenuation violation.

  default_capability_set() → tuple[str, ...]
      The sorted tuple form of CAPABILITY_VOCABULARY, used by
      authority_graph._ensure_default_edge_for to populate default
      Governor→authority edges with the full grant.

  verify_authority_chain_with_capabilities(...) → (effective|None, error|None)
      End-to-end check: structural path verification (sigs, expiry,
      rooting, contiguity) AND attenuation. Combines verify_canonical_path
      with compute_effective_capabilities.

Determinism: effective capabilities are returned as frozenset; callers
that need stable order should sort. The default capability set is a
sorted tuple, so default-edge signatures are byte-stable across processes.
"""

from __future__ import annotations

from typing import Optional, Iterable

from ugk.invariants import CAPABILITY_VOCABULARY


# ─────────────────────────────────────────────────────────────────────────────
# Attenuation predicate
# ─────────────────────────────────────────────────────────────────────────────

def attenuates(parent_set: Iterable[str], child_set: Iterable[str]) -> bool:
    """True iff child_set ⊆ parent_set (capability attenuation predicate).

    Accepts any iterable; converts to frozenset internally. Out-of-vocabulary
    identifiers are detected naturally: the Governor's effective set is
    CAPABILITY_VOCABULARY, so any child containing an identifier outside
    the vocabulary fails this predicate at the first hop.
    """
    return frozenset(child_set) <= frozenset(parent_set)


# ─────────────────────────────────────────────────────────────────────────────
# Effective-capability computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_effective_capabilities(
    path,  # list[AuthorityEdge]; not type-annotated to avoid circular import
) -> tuple[Optional[frozenset], Optional[str]]:
    """Walk the canonical path, applying capability attenuation at each hop.

    Initial state: Governor's effective set = CAPABILITY_VOCABULARY.
    For each edge in path (root→terminus order):
      - Let child_set = frozenset(edge.capability_set)
      - If child_set ⊄ effective: return (None, "CapabilityEscalation")
      - effective := child_set

    Empty path (target == GOVERNOR_AUTHORITY): returns (CAPABILITY_VOCABULARY, None).

    Returns:
      (effective_set, None) on success — the capability set held by the
                                          terminal authority
      (None, "CapabilityEscalation") on the first attenuation violation
    """
    effective: frozenset = CAPABILITY_VOCABULARY
    for edge in path:
        child_set = frozenset(edge.capability_set)
        if not (child_set <= effective):
            return (None, "CapabilityEscalation")
        effective = child_set
    return (effective, None)


# ─────────────────────────────────────────────────────────────────────────────
# Default-capability-set factory
# ─────────────────────────────────────────────────────────────────────────────

def default_capability_set() -> tuple:
    """Return the sorted-tuple form of CAPABILITY_VOCABULARY.

    Used by authority_graph._ensure_default_edge_for to populate default
    Governor→authority edges with the full vocabulary (Governor grants
    everything by default; attenuation along configured multi-hop chains
    restricts subsequently).

    The sorted-tuple form is signing-stable: same vocabulary → same
    canonical_json → same Ed25519 signature.
    """
    return tuple(sorted(CAPABILITY_VOCABULARY))


# ─────────────────────────────────────────────────────────────────────────────
# Combined structural + attenuation verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_authority_chain_with_capabilities(
    path,  # list[AuthorityEdge]
    *,
    governor_pubkey_hex: str,
    current_time: Optional[int] = None,
) -> tuple[Optional[frozenset], Optional[str]]:
    """End-to-end verification: structural + cryptographic + attenuation.

    Combines verify_canonical_path (signature, expiry, rooting, contiguity)
    with compute_effective_capabilities (attenuation along the chain).

    Returns:
      (effective_set, None) on full success
      (None, error_code)    on the first failure encountered

    Error codes:
      - Structural / cryptographic: NoCanonicalPath, SignatureInvalid,
        IssuerMismatch, ExpiredEdge (from verify_canonical_path)
      - Attenuation: CapabilityEscalation (from compute_effective_capabilities)
    """
    # Late import to avoid module-load cycle (authority_graph → capabilities
    # is OK; capabilities → authority_graph at call-time is OK)
    from ugk import authority_graph as AG
    ok, err = AG.verify_canonical_path(
        path,
        governor_pubkey_hex=governor_pubkey_hex,
        current_time=current_time,
    )
    if not ok:
        return (None, err)
    return compute_effective_capabilities(path)


__all__ = [
    "attenuates",
    "compute_effective_capabilities",
    "default_capability_set",
    "verify_authority_chain_with_capabilities",
]
