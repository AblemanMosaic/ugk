"""ugk/authority_graph.py — G_c authority graph machinery (Roadmap W-07).

M2.3h replaces the M2.2-era single-element `authority_chain = [authority]`
proxy with a real governed graph-derived canonical path through G_c. Each
edge in the graph is a Governor-signed AuthorityEdge artifact carrying:
  - the issuer (parent authority name)
  - the subject (child authority name)
  - a capability_set (forward-compat slot; M2.3i adds attenuation logic)
  - issuance time and expiry
  - Governor signature

The canonical path from the Governor (root) to a target authority is the
list of edges that admit that authority. canonical_path becomes the
authority_chain input to H_c (via c_c).

Per Governor ruling on R-14 (M2.3e): single Governor key signs all
artifacts. AuthorityEdge inherits this — edges are signed with the same
Ed25519 key as EpochIssuance and Policy. Per-authority Ed25519 keypair
issuance is forward-compatible (issuer_key_id slot already accommodates
real per-authority pubkeys) but not added at this subphase.

Public surface:
  AuthorityEdge          — frozen dataclass; signed artifact
  AuthorityGraph         — graph object holding edges and parent map
  sign_authority_edge    — construct + sign a single edge
  verify_authority_edge  — Ed25519 signature + expiry verification
  GOVERNOR_AUTHORITY     — string label for the graph root
  canonical_path_for(name) — convenience: list[AuthorityEdge] from root to `name`
  canonical_path_as_dicts(name) — same but as list[dict] for c_c canonicalization
  verify_canonical_path  — full path verification with expiry
  register_edge          — explicit graph mutation (test/admin)
  clear_graph            — reset (test only)

Determinism: signing and lookup are deterministic across processes.
default-edge signatures are byte-stable; same authority name → same
canonical path → same H_c contribution.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Iterable

from ugk.vendor.ed25519 import sign as _ed25519_sign, verify as _ed25519_verify
from ugk.freshness import (
    DEFAULT_TEST_PRIVKEY_HEX as _DEFAULT_PRIV,
    DEFAULT_TEST_PUBKEY_HEX as _DEFAULT_PUB,
)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

# Root authority label. Edges with issuer == GOVERNOR_AUTHORITY are the
# "first hop" out of the root and constitute well-rooted canonical paths.
GOVERNOR_AUTHORITY: str = "Governor"

# Wide-window default expiry for default-derived edges (matches the
# default_epoch valid_until). Real production edges would carry narrower
# windows reflecting governance lifecycle.
_DEFAULT_VALID_UNTIL: int = (1 << 63) - 1


def _canonical_json_bytes(obj) -> bytes:
    """JCS-style canonical JSON encoder (mirrors freshness module)."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# AuthorityEdge artifact
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AuthorityEdge:
    """Governor-signed authorization edge from `issuer` to `subject`.

    Fields per Governor directive (M2.3h):
      issuer          — parent authority identifier (name or future key id)
      subject         — child authority identifier
      capability_set  — ordered tuple of capability identifiers; FORWARD-
                        COMPAT SLOT at M2.3h — present in canonicalization
                        but not enforced (M2.3i adds attenuation rules)
      edge_time       — epoch counter when edge was issued
      valid_until     — inclusive expiry (epoch counter)
      issuer_key_id   — Governor pubkey hex ("signer")
      signature       — Ed25519 signature hex (128 chars) over the unsigned
                        payload

    Signature covers: canonical_json({issuer, subject, capability_set,
    edge_time, valid_until, issuer_key_id}). The `signature` field itself
    is excluded from the signing payload but included in id(edge).
    """
    issuer:         str
    subject:        str
    capability_set: tuple
    edge_time:      int
    valid_until:    int
    issuer_key_id:  str
    signature:      str

    def unsigned_payload(self) -> bytes:
        """Canonical bytes that get signed."""
        return _canonical_json_bytes({
            "issuer":         self.issuer,
            "subject":        self.subject,
            "capability_set": list(self.capability_set),
            "edge_time":      self.edge_time,
            "valid_until":    self.valid_until,
            "issuer_key_id":  self.issuer_key_id,
        })

    def to_canonical_dict(self) -> dict:
        """Full canonical dict (including signature) for JCS canonicalization
        as part of the authority_chain input to c_c."""
        return {
            "issuer":         self.issuer,
            "subject":        self.subject,
            "capability_set": list(self.capability_set),
            "edge_time":      self.edge_time,
            "valid_until":    self.valid_until,
            "issuer_key_id":  self.issuer_key_id,
            "signature":      self.signature,
        }


def id_authority_edge(edge: AuthorityEdge) -> str:
    """id(AuthorityEdge) := SHA-256(canonical_json(full edge))."""
    return hashlib.sha256(_canonical_json_bytes(edge.to_canonical_dict())).hexdigest()


def sign_authority_edge(
    *,
    issuer:         str,
    subject:        str,
    capability_set: Iterable[str] = (),
    edge_time:      int = 0,
    valid_until:    int = _DEFAULT_VALID_UNTIL,
    issuer_key_id:  str = _DEFAULT_PUB,
    signer_privkey_hex: str = _DEFAULT_PRIV,
) -> AuthorityEdge:
    """Construct and sign an AuthorityEdge with the Governor's private key.

    M2.3i: capability_set is normalized to a sorted tuple before signing,
    so equivalent capability sets produce byte-identical signatures
    regardless of input ordering.
    """
    cs = tuple(sorted(capability_set))
    unsigned = _canonical_json_bytes({
        "issuer":         issuer,
        "subject":        subject,
        "capability_set": list(cs),
        "edge_time":      edge_time,
        "valid_until":    valid_until,
        "issuer_key_id":  issuer_key_id,
    })
    sig = _ed25519_sign(unsigned, signer_privkey_hex)
    return AuthorityEdge(
        issuer=issuer, subject=subject, capability_set=cs,
        edge_time=edge_time, valid_until=valid_until,
        issuer_key_id=issuer_key_id, signature=sig,
    )


def verify_authority_edge(
    edge: AuthorityEdge,
    governor_pubkey_hex: str,
    *,
    current_time: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """Verify edge signature and (if current_time given) expiry.

    Returns (ok, error_code) per ERROR_CODES (M2.3a/e):
      "IssuerMismatch"   — issuer_key_id != governor_pubkey_hex
      "SignatureInvalid" — Ed25519 verify failed
      "ExpiredEdge"      — current_time > edge.valid_until
    """
    if edge.issuer_key_id != governor_pubkey_hex:
        return (False, "IssuerMismatch")
    try:
        sig_ok = _ed25519_verify(edge.unsigned_payload(), edge.signature,
                                 governor_pubkey_hex)
    except Exception:
        return (False, "SignatureInvalid")
    if not sig_ok:
        return (False, "SignatureInvalid")
    if current_time is not None and current_time > edge.valid_until:
        return (False, "ExpiredEdge")
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# AuthorityGraph
# ─────────────────────────────────────────────────────────────────────────────

class AuthorityGraph:
    """Single-parent authority tree rooted at GOVERNOR_AUTHORITY.

    Edges are stored as a dict keyed by subject (each subject has at most
    one incoming edge — single-parent tree). M2.3h's tree restriction is
    a structural simplification; multi-parent DAGs become possible in a
    later subphase if governance requires (the data model accommodates).
    """

    def __init__(self) -> None:
        # subject_name → AuthorityEdge admitting that subject
        self._edges: dict[str, AuthorityEdge] = {}

    def add_edge(self, edge: AuthorityEdge) -> None:
        """Register an edge. The subject's prior incoming edge (if any)
        is replaced (key rotation / edge revocation semantics)."""
        self._edges[edge.subject] = edge

    def has_subject(self, subject: str) -> bool:
        return subject in self._edges

    def get_edge_for(self, subject: str) -> Optional[AuthorityEdge]:
        """Return the incoming edge for `subject`, or None if absent."""
        return self._edges.get(subject)

    def canonical_path(self, target: str) -> list[AuthorityEdge]:
        """Return the list of edges from GOVERNOR_AUTHORITY to `target`.

        If `target` is the root, returns []. If `target` has no incoming
        edge in the graph, raises ValueError. Walks parents upward and
        reverses to produce root→target order.
        """
        if target == GOVERNOR_AUTHORITY:
            return []
        path: list[AuthorityEdge] = []
        cursor = target
        seen: set[str] = set()
        while cursor != GOVERNOR_AUTHORITY:
            if cursor in seen:
                raise ValueError(f"cycle detected at {cursor!r}")
            seen.add(cursor)
            edge = self._edges.get(cursor)
            if edge is None:
                raise ValueError(f"no incoming edge for {cursor!r}")
            path.append(edge)
            cursor = edge.issuer
        path.reverse()
        return path

    def __len__(self) -> int:
        return len(self._edges)

    def clear(self) -> None:
        self._edges.clear()


def verify_canonical_path(
    path: list[AuthorityEdge],
    *,
    governor_pubkey_hex: str,
    current_time: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """Verify a canonical path end-to-end.

    Checks:
      - Path is non-empty
      - First edge is rooted at GOVERNOR_AUTHORITY
      - Each edge's signature verifies under the Governor key
      - Each edge's expiry passes (if current_time supplied)
      - Edge contiguity: path[i].subject == path[i+1].issuer

    All path-structure failures collapse to "NoCanonicalPath" (M2.3a
    ERROR_CODES); cryptographic / expiry failures use the existing
    SignatureInvalid / IssuerMismatch / ExpiredEdge codes.
    """
    if not path:
        return (False, "NoCanonicalPath")
    if path[0].issuer != GOVERNOR_AUTHORITY:
        return (False, "NoCanonicalPath")
    for i, edge in enumerate(path):
        ok, err = verify_authority_edge(edge, governor_pubkey_hex,
                                        current_time=current_time)
        if not ok:
            return (False, err)
        if i > 0 and path[i - 1].subject != edge.issuer:
            return (False, "NoCanonicalPath")
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# Default graph + per-authority lookup
# ─────────────────────────────────────────────────────────────────────────────
#
# Receipt construction in store.write() asks for the canonical path from
# Governor to the receipt's authority. The default graph builds a direct
# Governor→authority edge on first lookup (parallel to policy/auth_key
# cache pattern). Multi-hop chains are opt-in via explicit register_edge.

_DEFAULT_GRAPH = AuthorityGraph()


def _ensure_default_edge_for(authority_name: str) -> None:
    """Ensure the default graph has an incoming edge for `authority_name`.

    If absent, builds a Governor→authority_name edge with wide validity
    and the full CAPABILITY_VOCABULARY (M2.3i: Governor grants everything
    by default; explicit multi-hop chains via register_edge can carry
    attenuated capability sets). Idempotent.
    """
    if authority_name == GOVERNOR_AUTHORITY:
        return
    if _DEFAULT_GRAPH.has_subject(authority_name):
        return
    # Late import: capabilities → authority_graph is a runtime call but
    # at module-load time capabilities imports CAPABILITY_VOCABULARY from
    # invariants, which is fine. Importing capabilities here at call-time
    # avoids any potential import-order surprise.
    from ugk import capabilities as _CAP
    edge = sign_authority_edge(
        issuer=GOVERNOR_AUTHORITY,
        subject=authority_name,
        capability_set=_CAP.default_capability_set(),
        edge_time=0,
        valid_until=_DEFAULT_VALID_UNTIL,
    )
    _DEFAULT_GRAPH.add_edge(edge)


def canonical_path_for(authority_name: str) -> list[AuthorityEdge]:
    """Return the canonical path through the DEFAULT graph for `authority_name`.

    Builds default Governor→authority edges as needed (idempotent cache).
    For multi-hop chains, register intermediate edges via register_edge
    before calling this.
    """
    if authority_name == GOVERNOR_AUTHORITY:
        return []
    _ensure_default_edge_for(authority_name)
    # If intermediate authorities exist in the graph (e.g., registered by
    # tests), walk parents to root.
    return _DEFAULT_GRAPH.canonical_path(authority_name)


def canonical_path_as_dicts(authority_name: str) -> list[dict]:
    """Same as canonical_path_for but converted to list[dict] for JCS
    canonicalization as authority_chain input to c_c."""
    return [e.to_canonical_dict() for e in canonical_path_for(authority_name)]


def register_edge(edge: AuthorityEdge) -> None:
    """Add an edge to the default graph (test/admin surface).

    Useful for constructing multi-hop chains: register edges
    Governor→A, A→B, B→C ... then canonical_path_for("C") returns the
    full chain.
    """
    _DEFAULT_GRAPH.add_edge(edge)


def clear_graph() -> None:
    """Reset the default graph (test surface only)."""
    _DEFAULT_GRAPH.clear()


def default_graph() -> AuthorityGraph:
    """Return a reference to the module-level default graph (for inspection)."""
    return _DEFAULT_GRAPH


__all__ = [
    "GOVERNOR_AUTHORITY",
    "AuthorityEdge", "AuthorityGraph",
    "id_authority_edge",
    "sign_authority_edge", "verify_authority_edge",
    "verify_canonical_path",
    "canonical_path_for", "canonical_path_as_dicts",
    "register_edge", "clear_graph", "default_graph",
]
