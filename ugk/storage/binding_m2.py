"""ugk/binding_m2.py — Phase M2.1 M2 binding primitives (THR-conformant).

ISOLATED FROM EXISTING binding.py BY DESIGN.

Phase M2.1 scope (per M2-DESIGN-PACK-REV3 §Deliverable 8):
  - c_s, c_c, c_m, c_j canonicalization functions (§Deliverable 1)
  - merkle_root_v1 tree construction (§Deliverable 2)
  - compute_H_r final root (§Deliverable 2)
  - commitment_minimality_gate predicate (§Deliverable 3)
  - freshness_check (used by EV-N05; §Deliverable 1 boundary algorithm)
  - CANONICALIZATION_DOMAINS, PRINCIPLED_REDUNDANCY_REGISTRY (§Deliverable 3)

OUT OF M2.1 SCOPE — DO NOT TOUCH:
  - existing binding.py (still has dm_s03, CHC_DIMENSIONS, SEP — removed at M2.3)
  - invariants.py (CHC-S-01/02/03 rewrite + CHC-S-04 add — M2.3)
  - kernel.py / store.py (Receipt schema migration — M2.2)
  - any other UGK file

This module is a pure-function implementation. No Receipt dataclass dependency,
no SQL, no global state, no I/O beyond hash computation. Vectors invoke these
functions with primitive arguments.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Domain separators (REV3 §Deliverable 1 + §Deliverable 2)
# ─────────────────────────────────────────────────────────────────────────────

DS_S            = b"UGK-CIS-c_s-v1"
DS_C            = b"UGK-CIS-c_c-v1"
DS_M            = b"UGK-CIS-c_m-v1"
DS_J            = b"UGK-CIS-c_j-v1"

DS_R            = b"UGK-RECEIPT-ROOT-v1"
DS_LEAF         = b"UGK-MERKLE-LEAF-v1"
DS_NODE         = b"UGK-MERKLE-NODE-v1"
DS_SINGLELEAF   = b"UGK-MERKLE-SINGLE-v1"

# ─────────────────────────────────────────────────────────────────────────────
# Version identifiers
# ─────────────────────────────────────────────────────────────────────────────

ID_C_S          = "c_s.v1"
ID_C_C          = "c_c.v1"
ID_C_M          = "c_m.v1+sigma_0"   # includes regime per §Deliverable 1
ID_C_J          = "c_j.v1"
ID_ROOT         = "root.v1"

# ─────────────────────────────────────────────────────────────────────────────
# Type tags for leaf encoding (REV3 §Deliverable 2)
# ─────────────────────────────────────────────────────────────────────────────

TAG_H_S         = 0x01
TAG_H_C         = 0x02
TAG_H_M         = 0x03
TAG_H_J         = 0x04
TAG_ID_P        = 0x05
TAG_ID_SIGMA    = 0x06
TAG_ID_PHI      = 0x07

LEAF_NAME_BY_TAG = {
    TAG_H_S:        "H_s",
    TAG_H_C:        "H_c",
    TAG_H_M:        "H_m",
    TAG_H_J:        "H_j",
    TAG_ID_P:       "id_P",
    TAG_ID_SIGMA:   "id_Sigma",
    TAG_ID_PHI:     "id_Phi",
}

# ─────────────────────────────────────────────────────────────────────────────
# Constitutional declarations (REV3 §Deliverable 3 / CHC-S-04)
# ─────────────────────────────────────────────────────────────────────────────
# M2.3c: CANONICALIZATION_DOMAINS and PRINCIPLED_REDUNDANCY_REGISTRY are
# imported from ugk.invariants — the canonical constitutional source. Prior
# to M2.3c these declarations were duplicated here; the dual-registry was
# eliminated as part of the H_m domain reconciliation subphase.

from ugk.invariants import (  # noqa: E402 — constitutional import
    CANONICALIZATION_DOMAINS,
    PRINCIPLED_REDUNDANCY_REGISTRY,
    ID_SIGMA_0,
    ID_PHI_0,
)

# ─────────────────────────────────────────────────────────────────────────────
# Primitives
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(*parts: bytes) -> bytes:
    """Deterministic SHA-256 over concatenated byte parts. Returns 32 bytes."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()


def _canonical_json(obj: Any) -> bytes:
    """RFC 8785 JCS-compatible canonical JSON.

    For M2.1 we use json.dumps with sort_keys=True and separators=(',', ':'),
    which gives stable ordering and no whitespace. NFC normalization applied to
    all string values for Unicode determinism.

    Rejects: cycles (json raises ValueError), non-UTF-8 strings, non-finite
    floats (allow_nan=False raises ValueError).
    """
    def normalize(x: Any) -> Any:
        if isinstance(x, str):
            return unicodedata.normalize("NFC", x)
        if isinstance(x, dict):
            return {normalize(k): normalize(v) for k, v in x.items()}
        if isinstance(x, list):
            return [normalize(v) for v in x]
        if isinstance(x, tuple):
            return [normalize(v) for v in x]
        return x

    normalized = normalize(obj)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _length_prefix_be(n: int) -> bytes:
    """4-byte big-endian length prefix."""
    if n < 0 or n > 0xFFFFFFFF:
        raise ValueError(f"length out of range: {n}")
    return n.to_bytes(4, byteorder="big")


# ─────────────────────────────────────────────────────────────────────────────
# Canonicalization functions c_i (REV3 §Deliverable 1)
# Each c_i is a deterministic, byte-stable, versioned function from typed
# domain to bytes. Each returns canonical bytes; the H_i hash applies DS_i.
# ─────────────────────────────────────────────────────────────────────────────

class NonCanonical(ValueError):
    """Raised when input fails canonicalization (THR Appendix B: NonCanonical)."""


def c_s(op_name: str, inputs: dict) -> bytes:
    """State canonicalization. Domain: (op_name, inputs)."""
    if not isinstance(op_name, str):
        raise NonCanonical("op_name must be str")
    if not isinstance(inputs, dict):
        raise NonCanonical("inputs must be dict")
    try:
        return _canonical_json({"op": op_name, "inputs": inputs})
    except (ValueError, TypeError) as e:
        raise NonCanonical(f"c_s canonicalization failed: {e}") from e


def c_c(
    authority_chain: list,
    policy_id: str,
    capabilities: list,
    warrant_basis: list,
    parent_H_r: str,
    freshness: dict,
) -> bytes:
    """Admissibility canonicalization. Domain per REV3 §Deliverable 1."""
    if not isinstance(authority_chain, list):
        raise NonCanonical("authority_chain must be list")
    # Compute a deterministic root over the authority_chain (placeholder for
    # full G_c root in M2.1 isolation — full G_c semantics arrive at later phases).
    G_c_root = _sha256(_canonical_json(authority_chain)).hex()
    try:
        return _canonical_json({
            "G_c_root":     G_c_root,
            "policy_id":    policy_id,
            "capabilities": capabilities,
            "warrant_basis": warrant_basis,
            "parent":       parent_H_r,
            "freshness":    freshness,
        })
    except (ValueError, TypeError) as e:
        raise NonCanonical(f"c_c canonicalization failed: {e}") from e


def c_m(
    intent: str,
    intent_ref: str,
    legend_hash: str,
    semantic_lineage: list,
) -> bytes:
    """Meaning canonicalization. Domain: meaning_artifact_0 tuple under Sigma_0."""
    try:
        # For M2.1 isolation, parse_L and r* are identity-on-tuple (the
        # meaning_artifact_0 tuple is already in canonical form; deeper regime
        # transformations land at M2.2+). Canonical encoding is JCS over the tuple.
        return _canonical_json({
            "intent":           intent,
            "intent_ref":       intent_ref,
            "legend_hash":      legend_hash,
            "semantic_lineage": semantic_lineage,
        })
    except (ValueError, TypeError) as e:
        raise NonCanonical(f"c_m canonicalization failed: {e}") from e


def c_j(
    phase_code: str,
    mosaic_root: str,
    session_id: str,
    authority_key: str,
) -> bytes:
    """Locality canonicalization. Domain per REV3 §Deliverable 1.

    Builds id(Phi) = H(DS_Φ ∥ id(P) ∥ id(Σ) ∥ H(roots) ∥ params ∥ version ∥ map_root?)
    per THR §9. For M2.1 isolation, id(Phi) is a stand-in over the available fields;
    full Phi structure lands at M2.2+ alongside Receipt-schema integration.
    """
    try:
        id_phi = _sha256(
            b"UGK-PHI-v1",
            _canonical_json({
                "phase_code":    phase_code,
                "mosaic_root":   mosaic_root,
                "session_id":    session_id,
            }),
        ).hex()
        return _canonical_json({
            "phi":           id_phi,
            "authority_key": authority_key,
        })
    except (ValueError, TypeError) as e:
        raise NonCanonical(f"c_j canonicalization failed: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# Per-commitment hashes H_i
# H_i := H(DS_i ∥ id(c_i) ∥ c_i(...))   (REV3 §Deliverable 1)
# ─────────────────────────────────────────────────────────────────────────────

def H_s(op_name: str, inputs: dict) -> bytes:
    return _sha256(DS_S, ID_C_S.encode("utf-8"), c_s(op_name, inputs))


def H_c(
    authority_chain: list,
    policy_id: str,
    capabilities: list,
    warrant_basis: list,
    parent_H_r: str,
    freshness: dict,
) -> bytes:
    return _sha256(
        DS_C,
        ID_C_C.encode("utf-8"),
        c_c(authority_chain, policy_id, capabilities, warrant_basis,
            parent_H_r, freshness),
    )


def H_m(
    intent: str,
    intent_ref: str,
    legend_hash: str,
    semantic_lineage: list,
    semantic_regime_id: str,
) -> bytes:
    """H_m := H(DS_m ∥ id(c_m) ∥ c_m(x) ∥ semantic_regime_id_bytes)

    M2.3c: signature extended with `semantic_regime_id` to align with REV3 D1
    formula which includes id(Σ_0). Prior to M2.3c the regime was not
    materially bound into H_m, making the id_Sigma → H_m principled-redundancy
    registry entry unreachable in the runtime predicate.
    """
    return _sha256(
        DS_M,
        ID_C_M.encode("utf-8"),
        c_m(intent, intent_ref, legend_hash, semantic_lineage),
        semantic_regime_id.encode("utf-8"),
    )


def H_j(
    phase_code: str,
    mosaic_root: str,
    session_id: str,
    authority_key: str,
) -> bytes:
    return _sha256(
        DS_J,
        ID_C_J.encode("utf-8"),
        c_j(phase_code, mosaic_root, session_id, authority_key),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Strict-mode context-pin hashes (the strict-mode additional leaves)
# Treated as separate leaves under H_r when mode == "strict".
# Each is just a domain-separated commitment to the identifier value.
# ─────────────────────────────────────────────────────────────────────────────

def H_id_P(policy_id: str) -> bytes:
    return _sha256(b"UGK-id_P-v1", policy_id.encode("utf-8"))


def H_id_Sigma(semantic_regime_id: str) -> bytes:
    return _sha256(b"UGK-id_Sigma-v1", semantic_regime_id.encode("utf-8"))


def H_id_Phi(phase_code: str) -> bytes:
    return _sha256(b"UGK-id_Phi-v1", phase_code.encode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# Merkle tree construction (REV3 §Deliverable 2)
# ─────────────────────────────────────────────────────────────────────────────

def _leaf_encoding(type_tag: int, h_i: bytes) -> bytes:
    """leaf_i := DS_leaf ∥ type_tag (1B) ∥ length(H_i) (4B BE) ∥ H_i (32B)"""
    if not (0x01 <= type_tag <= 0xFF):
        raise ValueError(f"type_tag out of range: {type_tag}")
    if len(h_i) != 32:
        raise ValueError(f"H_i must be 32 bytes, got {len(h_i)}")
    return DS_LEAF + bytes([type_tag]) + _length_prefix_be(len(h_i)) + h_i


def merkle_root_v1(leaves: list[bytes]) -> bytes:
    """Deterministic domain-separated binary merkle root over leaf-encoded bytes.

    `leaves` is the list of leaf_encoding(tag, H_i) outputs in canonical order
    (ascending type_tag).

    Per REV3 §Deliverable 2:
      - 0 leaves  → ValueError (M2 requires at least H_s, H_c, H_m)
      - 1 leaf    → H(DS_singleleaf ∥ leaf)
      - n leaves  → recursive pair-hash with duplicate-last padding for odd levels;
                    each internal node = H(DS_node ∥ left ∥ right)
    """
    if len(leaves) == 0:
        raise ValueError("empty leaf set — receipt requires at least H_s, H_c, H_m")
    if len(leaves) == 1:
        return _sha256(DS_SINGLELEAF, leaves[0])
    return _merkle_level(leaves)


def _merkle_level(nodes: list[bytes]) -> bytes:
    if len(nodes) == 1:
        return nodes[0]
    pairs: list[bytes] = []
    for i in range(0, len(nodes), 2):
        left = nodes[i]
        right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]  # duplicate-last
        pairs.append(_sha256(DS_NODE, left, right))
    return _merkle_level(pairs)


def build_inclusion_proof(
    leaves: list[tuple[int, bytes]],
    target_tag: int,
) -> tuple[bytes, list[tuple[bytes, str]]]:
    """Build a merkle inclusion proof for the leaf with the given type_tag.

    Returns (target_leaf_encoded, path) where path is a list of
    (sibling_hash, side) pairs from leaf level up to (but not including) root.
    `side` is "L" if the sibling is on the left, "R" if on the right.

    Used by EV-AV-001 to demonstrate selective disclosure: a verifier with
    only H_r + this proof + the claimed leaf encoding can verify that the
    claimed leaf is in the tree, without seeing the other leaves' contents.

    Per REV3 §Deliverable 2 "Proof opening (selective disclosure)".
    """
    sorted_leaves = sorted(leaves, key=lambda x: x[0])
    encoded = [_leaf_encoding(tag, h_i) for tag, h_i in sorted_leaves]

    # Find target's index in the sorted list
    target_idx = None
    for i, (tag, _) in enumerate(sorted_leaves):
        if tag == target_tag:
            target_idx = i
            break
    if target_idx is None:
        raise ValueError(f"target_tag {target_tag} not present in leaves")

    target_leaf_encoded = encoded[target_idx]
    path: list[tuple[bytes, str]] = []

    nodes = list(encoded)
    idx = target_idx
    while len(nodes) > 1:
        # Pair up; if odd, last node is duplicated
        new_nodes: list[bytes] = []
        for i in range(0, len(nodes), 2):
            left = nodes[i]
            right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
            new_nodes.append(_sha256(DS_NODE, left, right))
        # Record sibling for our target
        sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1
        if sibling_idx >= len(nodes):
            sibling_idx = idx  # duplicate-last case: sibling is self
        sibling = nodes[sibling_idx]
        side = "R" if idx % 2 == 0 else "L"  # which side sibling is on relative to us
        path.append((sibling, side))
        idx = idx // 2
        nodes = new_nodes
    return target_leaf_encoded, path


def verify_inclusion_proof(
    H_r: bytes,
    target_leaf_encoded: bytes,
    path: list[tuple[bytes, str]],
) -> bool:
    """Verify that target_leaf_encoded is in the tree producing H_r.

    Verifier holds: H_r (from a chain reference, cache, or attestor) and a
    proof supplied by the prover. The verifier reconstructs the path to root
    and confirms the final root matches H_r.

    Used by EV-AV-001 to demonstrate that a consumer holding H_r alone
    (without witnesses) can verify a strict-mode context leaf's value via
    this proof, without consulting any other witness.
    """
    # The target is itself a leaf-encoded blob. The first hash to fold is
    # over (DS_node, left, right) — handle the single-leaf base case.
    if len(path) == 0:
        # 1-leaf tree
        candidate = _sha256(DS_SINGLELEAF, target_leaf_encoded)
        return _sha256(DS_R, ID_ROOT.encode("utf-8"), candidate) == H_r

    current = target_leaf_encoded
    for sibling, side in path:
        if side == "L":
            current = _sha256(DS_NODE, sibling, current)
        else:
            current = _sha256(DS_NODE, current, sibling)
    return _sha256(DS_R, ID_ROOT.encode("utf-8"), current) == H_r


def compute_H_r(leaves: list[tuple[int, bytes]]) -> bytes:
    """Final receipt root.

    Inputs: list of (type_tag, H_i) pairs. Must include at minimum
    (TAG_H_S, H_s), (TAG_H_C, H_c), (TAG_H_M, H_m). Optional: TAG_H_J, and
    strict-mode leaves TAG_ID_P/TAG_ID_SIGMA/TAG_ID_PHI.

    H_r := H(DS_r ∥ id(root_v1) ∥ root(leaf_encoded leaves in canonical order))
    """
    # Sort by type_tag (canonical order, ascending) — REV3 §Deliverable 2
    sorted_leaves = sorted(leaves, key=lambda x: x[0])
    # Validate required leaves are present
    tags_present = {tag for tag, _ in sorted_leaves}
    required = {TAG_H_S, TAG_H_C, TAG_H_M}
    missing = required - tags_present
    if missing:
        missing_names = sorted(LEAF_NAME_BY_TAG[t] for t in missing)
        raise ValueError(f"compute_H_r missing required leaves: {missing_names}")
    # Validate no duplicate tags (each leaf appears at most once)
    if len(tags_present) != len(sorted_leaves):
        raise ValueError("compute_H_r: duplicate type_tag in leaves")
    # Encode each leaf and compute root
    encoded = [_leaf_encoding(tag, h_i) for tag, h_i in sorted_leaves]
    root = merkle_root_v1(encoded)
    return _sha256(DS_R, ID_ROOT.encode("utf-8"), root)


# ─────────────────────────────────────────────────────────────────────────────
# Commitment Minimality gate (REV3 §Deliverable 3)
# Mechanical predicate over CANONICALIZATION_DOMAINS + PRINCIPLED_REDUNDANCY_REGISTRY.
# Does NOT judge threat-class novelty at runtime (that is Governor ADR protocol).
# ─────────────────────────────────────────────────────────────────────────────

def commitment_minimality_gate(
    present_leaves: set[str],
    *,
    domains: dict[str, frozenset[str]] | None = None,
    registry: dict[str, tuple[str, str]] | None = None,
) -> tuple[bool, str | None]:
    """Runtime gate: no committed leaf may be recoverable from receipt body
    or witnesses without that leaf's own witness, except via principled redundancy
    registered with a documented carrier and threat class.

    `present_leaves` is the set of leaf names ({"H_s", "H_c", "H_m", "H_j",
    "id_P", "id_Sigma", "id_Phi"}) that appear under H_r for this receipt.

    Production callers omit `domains`/`registry` and the constitutional globals
    are consulted. Vectors (e.g. EV-CM-02) pass extended `domains` to exhibit
    rejection of hypothetical unregistered redundancies. The override surface
    does not change runtime semantics — it is for test isolation only.

    Predicate: for each pair (L_i, L_j) of distinct present leaves, if
    domain(L_i) ⊆ domain(L_j), then L_i is recoverable from L_j's witness.
    Such redundancy is admissible only if (L_i, L_j) is registered with
    L_j as the carrier.

    Returns (ok: bool, reason: str | None). Decidable from present_leaves
    and constitutional declarations alone.
    """
    _domains = domains if domains is not None else CANONICALIZATION_DOMAINS
    _registry = registry if registry is not None else PRINCIPLED_REDUNDANCY_REGISTRY

    # Validate all present leaves have declared domains
    unknown = present_leaves - set(_domains.keys())
    if unknown:
        return (False, f"unknown leaves: {sorted(unknown)}")

    for L_i in present_leaves:
        D_i = _domains[L_i]
        for L_j in present_leaves:
            if L_i == L_j:
                continue
            D_j = _domains[L_j]
            if D_i.issubset(D_j):
                # Redundancy detected. Check registry.
                if L_i in _registry:
                    expected_carrier, _threat_class = _registry[L_i]
                    if L_j == expected_carrier:
                        continue  # registered principled redundancy
                return (
                    False,
                    f"leaf {L_i} (domain {sorted(D_i)}) is recoverable from "
                    f"leaf {L_j} (domain {sorted(D_j)}); "
                    f"not registered as principled with carrier {L_j}",
                )
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# Freshness check (REV3 §Deliverable 1)
# Used by EV-N05 for NotYetAdmissible boundary verification.
# ─────────────────────────────────────────────────────────────────────────────

def freshness_check(
    freshness_claim: dict,
    current_epoch: int,
    current_phase_code: str,
) -> tuple[bool, str | None]:
    """Verifier-side boundary check.

    freshness_claim is the FreshnessClaim dict with keys:
      phase_code, epoch_counter, valid_from, valid_until, window_sig

    Returns (ok: bool, error: str | None).
    Error codes per REV3 §Deliverable 1: PhaseMismatch, NotYetAdmissible,
    ExpiredEdge.

    NOTE: window_sig verification is OUT of M2.1 scope (requires Governor key
    integration). The signature is structurally accepted here; cryptographic
    verification arrives at M2.3 / Phase-Governance integration.
    """
    if freshness_claim["phase_code"] != current_phase_code:
        return (False, "PhaseMismatch")
    if current_epoch < freshness_claim["valid_from"]:
        return (False, "NotYetAdmissible")
    if current_epoch > freshness_claim["valid_until"]:
        return (False, "ExpiredEdge")
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# Public surface summary (for tooling discovery)
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # canonicalization functions
    "c_s", "c_c", "c_m", "c_j",
    # per-commitment hashes
    "H_s", "H_c", "H_m", "H_j",
    "H_id_P", "H_id_Sigma", "H_id_Phi",
    # merkle tree
    "merkle_root_v1", "compute_H_r",
    "build_inclusion_proof", "verify_inclusion_proof",
    # gates / checks
    "commitment_minimality_gate", "freshness_check",
    # constitutional declarations
    "CANONICALIZATION_DOMAINS", "PRINCIPLED_REDUNDANCY_REGISTRY",
    # type tags
    "TAG_H_S", "TAG_H_C", "TAG_H_M", "TAG_H_J",
    "TAG_ID_P", "TAG_ID_SIGMA", "TAG_ID_PHI",
    # version ids
    "ID_C_S", "ID_C_C", "ID_C_M", "ID_C_J", "ID_ROOT",
    # exceptions
    "NonCanonical",
]
