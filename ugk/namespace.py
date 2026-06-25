"""ugk/namespace.py — M_Phi namespace + mosaic_root binding (Roadmap W-10).

M2.3k replaces the M2.2-era `mosaic_root="0"*64` placeholder in H_j with
a real cryptographic commitment to the M_Phi namespace structure. The
namespace (the set of name_keys valid in the phase) is declared
constitutionally in invariants.NAMESPACE_PHI_0; the mosaic_root is
SHA-256 of canonical JSON of the sorted name_key list.

Public surface:
  compute_mosaic_root(namespace) → str
      SHA-256(canonical_json(sorted(namespace))) — 64-hex.

  MOSAIC_ROOT_PHI_0: str
      The mosaic_root computed from invariants.NAMESPACE_PHI_0 at module
      load. This is the value bound into H_j for receipts produced under
      phase Φ_0.

  is_member(name_key, namespace=NAMESPACE_PHI_0) → bool
      Membership predicate.

  validate_name_keys(name_keys, namespace=NAMESPACE_PHI_0) → (ok, err)
      Batch validation: returns (True, None) if all entries are members,
      else (False, "NamespaceNonMember") with the offending key context.
      M2.3l decision procedures will use this for receipt verification.

Determinism: pure SHA-256 over canonical JSON. Same NAMESPACE_PHI_0 →
same MOSAIC_ROOT_PHI_0 across all processes. Adding/removing entries
in invariants.NAMESPACE_PHI_0 moves law_hash (constitutional change)
and moves MOSAIC_ROOT_PHI_0 in lockstep.

Boundary at M2.3k (vs M2.3l, M2.3m):
  - M2.3k provides: namespace declaration + cryptographic root commitment
                    + membership query API
  - M2.3l (ratified) added: receipt-side NamespaceNonMember enforcement
                            via decision.D_j (strict_namespace mode).
                            EV-N02 demonstrates activation.
  - M2.3m (ratified) added: witness opening for selective disclosure
                            via witness.construct_witness / verify_witness.
                            Namespace members can be opened with merkle
                            inclusion proofs against mosaic_root in the
                            same shape as other strict-mode leaves.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Optional

from ugk.invariants import NAMESPACE_PHI_0


# ─────────────────────────────────────────────────────────────────────────────
# Mosaic-root computation
# ─────────────────────────────────────────────────────────────────────────────

def _canonical_json_bytes(obj) -> bytes:
    """JCS-style canonical JSON encoder (mirrors freshness module)."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def compute_mosaic_root(namespace: Iterable[str]) -> str:
    """SHA-256 over canonical JSON of sorted name_key list.

    The sort ensures byte-deterministic output regardless of input
    iteration order (frozensets, sets, lists with arbitrary ordering
    all produce the same root for the same content).
    """
    sorted_names = sorted(set(namespace))
    return hashlib.sha256(_canonical_json_bytes(sorted_names)).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Derived constant — bound into H_j for receipts under phase Φ_0
# ─────────────────────────────────────────────────────────────────────────────

MOSAIC_ROOT_PHI_0: str = compute_mosaic_root(NAMESPACE_PHI_0)


# ─────────────────────────────────────────────────────────────────────────────
# Membership / validation
# ─────────────────────────────────────────────────────────────────────────────

def is_member(name_key: str, namespace: Optional[Iterable[str]] = None) -> bool:
    """Predicate: is `name_key` in the given namespace (default: NAMESPACE_PHI_0)?"""
    if namespace is None:
        namespace = NAMESPACE_PHI_0
    return name_key in namespace


def validate_name_keys(
    name_keys: Iterable[str],
    namespace: Optional[Iterable[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Batch validation: all name_keys must be members of namespace.

    Returns (True, None) on success.
    Returns (False, "NamespaceNonMember") on the first non-member key.

    Reuses the existing NamespaceNonMember error code (ERROR_CODES,
    M2.3a — previously unused at the receipt layer). M2.3l decision
    procedures will use this function during receipt verification.
    """
    if namespace is None:
        ns = NAMESPACE_PHI_0
    else:
        ns = frozenset(namespace)
    for key in name_keys:
        if key not in ns:
            return (False, "NamespaceNonMember")
    return (True, None)


__all__ = [
    "compute_mosaic_root",
    "MOSAIC_ROOT_PHI_0",
    "is_member",
    "validate_name_keys",
]
