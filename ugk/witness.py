"""ugk/witness.py — Witness opening / selective disclosure (Roadmap W-16).

M2.3m provides the receipt-level witness abstraction layered on top of
binding_m2.build_inclusion_proof / verify_inclusion_proof. A Witness
opens ONE commitment leaf of a receipt — the prover reveals the c_i
input that produced the leaf hash, plus the merkle path from leaf to
H_r. A verifier holding only H_r + the Witness can verify that ONE
commitment without seeing the rest of the receipt body.

Strict-mode vs context-external mode (REV3 §Deliverable 4):
  - Strict mode (default): 7-leaf merkle tree includes id_P, id_Sigma,
    id_Phi self-describing identity leaves. Witnesses can open any of
    the 7 leaves. EV-AV-001 demonstrates this catches identity substitution.
  - Context-external mode: 4-leaf tree (H_s, H_c, H_m, H_j only). The
    identity leaves are missing; without them, witnesses for context
    (recovery witness) and collapse (collapse witness) become required
    to maintain integrity guarantees. UnderRecordedCollapse fires when
    a context-external receipt is presented WITHOUT these witnesses.

M2.3m delivers:
  - Witness dataclass (leaf_tag, opened_input, inclusion_path, h_r_claimed)
  - construct_witness(receipt, leaf_tag) — build a witness from a receipt
  - verify_witness(witness) — verify witness against its claimed H_r
  - verify_well_recorded(mode, witnesses) — UnderRecordedCollapse check
    for context-external mode

Activates ERROR_CODES: UnderRecordedCollapse (M2.3a, previously unused
at the verification layer).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Union

from ugk.storage import binding_m2 as m2
from ugk import invariants as inv
from ugk import freshness as F
from ugk.governance import policy as P
from ugk import authority_keys as AK
from ugk import authority_graph as AG
from ugk import capabilities as CAP
from ugk import lineage as L
from ugk import namespace as NS


# ─────────────────────────────────────────────────────────────────────────────
# Mode constants
# ─────────────────────────────────────────────────────────────────────────────

MODE_STRICT: str = "strict"
MODE_CONTEXT_EXTERNAL: str = "context_external"


# ─────────────────────────────────────────────────────────────────────────────
# Witness dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Witness:
    """A merkle witness opening ONE commitment leaf of a receipt.

    Fields:
      leaf_tag        — which leaf this witness opens (TAG_H_S etc.)
      opened_input    — the c_i input that re-canonicalizes to the leaf hash
                        (structure varies by leaf; see _recompute_leaf_hash)
      inclusion_path  — list of (sibling_hash, side) pairs from leaf level
                        upward, as produced by build_inclusion_proof
      h_r_claimed     — hex of the receipt H_r this witness opens against

    Verification: re-compute leaf hash from opened_input → verify
    inclusion_path produces a root matching h_r_claimed.
    """
    leaf_tag:       int
    opened_input:   dict
    inclusion_path: list  # list[tuple[bytes, str]]; bytes are non-hashable so we store the list
    h_r_claimed:    str


# ─────────────────────────────────────────────────────────────────────────────
# Receipt → leaf inputs reconstruction
# ─────────────────────────────────────────────────────────────────────────────
#
# To construct a witness for a leaf, we need to know what `c_i` input
# produced the leaf hash. This requires re-running the receipt-construction
# field mapping (the same mapping store.write and binding_gate use).

def _reconstruct_leaves_for(receipt) -> list[tuple[int, bytes]]:
    """Reconstruct the full leaf list for a receipt's H_r computation.

    Mirrors store.write's field-to-c_i mapping (M2.3a..M2.3k). Used to
    build inclusion proofs against a known H_r.
    """
    freshness_dict = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))
    policy_id_v = P.lookup_policy_id(receipt.jurisdiction)
    authority_key_v = AK.lookup_authority_key(receipt.authority)
    authority_chain_objs = AG.canonical_path_for(receipt.authority)
    authority_chain_v = AG.canonical_path_as_dicts(receipt.authority)
    eff_caps, cap_err = CAP.compute_effective_capabilities(authority_chain_objs)
    if cap_err is not None:
        raise ValueError(f"capability escalation in witness reconstruction: {cap_err}")
    capabilities_v = sorted(eff_caps)
    # Lineage from the receipt body — None at root, else reconstructed via
    # parent_h_r → (h_m, intent_ref); for standalone witness reconstruction
    # we assume root receipt (lineage = []). Full cross-receipt lineage
    # requires receipt-store access (matches binding_gate's _lineage_lookup).
    semantic_lineage_v = []  # acceptable for root or unknown-parent receipts

    h_s = m2.H_s(receipt.op, receipt.parameters)
    h_c = m2.H_c(
        authority_chain=authority_chain_v,
        policy_id=policy_id_v,
        capabilities=capabilities_v,
        warrant_basis=([receipt.warrant_id] if receipt.warrant_id else []),
        parent_H_r=receipt.parent_h_r,
        freshness=freshness_dict,
    )
    h_m = m2.H_m(receipt.intent, receipt.intent_ref, receipt.legend_hash,
                 semantic_lineage_v, semantic_regime_id=inv.ID_SIGMA_0)
    h_j = m2.H_j(freshness_dict["phase_code"], NS.MOSAIC_ROOT_PHI_0,
                 receipt.session_dkn, authority_key_v)
    return [
        (m2.TAG_H_S, h_s), (m2.TAG_H_C, h_c),
        (m2.TAG_H_M, h_m), (m2.TAG_H_J, h_j),
        (m2.TAG_ID_P,     m2.H_id_P(policy_id_v)),
        (m2.TAG_ID_SIGMA, m2.H_id_Sigma(inv.ID_SIGMA_0)),
        (m2.TAG_ID_PHI,   m2.H_id_Phi(inv.ID_PHI_0)),
    ]


def _opened_input_for(receipt, leaf_tag: int) -> dict:
    """Return the c_i input that re-canonicalizes to the leaf hash.

    The opened_input is the structured value the prover discloses; the
    verifier re-runs the appropriate H_i function on it to recompute the
    leaf hash, then walks the inclusion path.
    """
    freshness_dict = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))
    policy_id_v = P.lookup_policy_id(receipt.jurisdiction)
    authority_key_v = AK.lookup_authority_key(receipt.authority)
    authority_chain_v = AG.canonical_path_as_dicts(receipt.authority)
    authority_chain_objs = AG.canonical_path_for(receipt.authority)
    eff_caps, _ = CAP.compute_effective_capabilities(authority_chain_objs)
    capabilities_v = sorted(eff_caps)

    if leaf_tag == m2.TAG_H_S:
        return {"op": receipt.op, "parameters": receipt.parameters}
    if leaf_tag == m2.TAG_H_C:
        return {
            "authority_chain": authority_chain_v,
            "policy_id":       policy_id_v,
            "capabilities":    capabilities_v,
            "warrant_basis":   [receipt.warrant_id] if receipt.warrant_id else [],
            "parent_H_r":      receipt.parent_h_r,
            "freshness":       freshness_dict,
        }
    if leaf_tag == m2.TAG_H_M:
        return {
            "intent":             receipt.intent,
            "intent_ref":         receipt.intent_ref,
            "legend_hash":        receipt.legend_hash,
            "semantic_lineage":   [],  # root-receipt assumption
            "semantic_regime_id": inv.ID_SIGMA_0,
        }
    if leaf_tag == m2.TAG_H_J:
        return {
            "phase_code":     freshness_dict["phase_code"],
            "mosaic_root":    NS.MOSAIC_ROOT_PHI_0,
            "session_id":     receipt.session_dkn,
            "authority_key":  authority_key_v,
        }
    if leaf_tag == m2.TAG_ID_P:
        return {"policy_id": policy_id_v}
    if leaf_tag == m2.TAG_ID_SIGMA:
        return {"semantic_regime_id": inv.ID_SIGMA_0}
    if leaf_tag == m2.TAG_ID_PHI:
        return {"phase_code": inv.ID_PHI_0}
    raise ValueError(f"unknown leaf_tag: {leaf_tag}")


def _recompute_leaf_hash(leaf_tag: int, opened_input: dict) -> bytes:
    """Re-canonicalize opened_input via the appropriate H_i function to
    recover the leaf hash. The verifier's primary check.
    """
    if leaf_tag == m2.TAG_H_S:
        return m2.H_s(opened_input["op"], opened_input["parameters"])
    if leaf_tag == m2.TAG_H_C:
        return m2.H_c(
            authority_chain=opened_input["authority_chain"],
            policy_id=opened_input["policy_id"],
            capabilities=opened_input["capabilities"],
            warrant_basis=opened_input["warrant_basis"],
            parent_H_r=opened_input["parent_H_r"],
            freshness=opened_input["freshness"],
        )
    if leaf_tag == m2.TAG_H_M:
        return m2.H_m(
            opened_input["intent"],
            opened_input["intent_ref"],
            opened_input["legend_hash"],
            opened_input["semantic_lineage"],
            semantic_regime_id=opened_input["semantic_regime_id"],
        )
    if leaf_tag == m2.TAG_H_J:
        return m2.H_j(
            opened_input["phase_code"],
            opened_input["mosaic_root"],
            opened_input["session_id"],
            opened_input["authority_key"],
        )
    if leaf_tag == m2.TAG_ID_P:
        return m2.H_id_P(opened_input["policy_id"])
    if leaf_tag == m2.TAG_ID_SIGMA:
        return m2.H_id_Sigma(opened_input["semantic_regime_id"])
    if leaf_tag == m2.TAG_ID_PHI:
        return m2.H_id_Phi(opened_input["phase_code"])
    raise ValueError(f"unknown leaf_tag: {leaf_tag}")


# ─────────────────────────────────────────────────────────────────────────────
# Witness construction + verification
# ─────────────────────────────────────────────────────────────────────────────

def construct_witness(receipt, leaf_tag: int) -> Witness:
    """Build a Witness opening `leaf_tag` against the receipt's H_r.

    Reconstructs the full leaf list, computes the inclusion proof for
    the requested leaf, extracts the opened c_i input for that leaf,
    and returns a Witness bundle.
    """
    leaves = _reconstruct_leaves_for(receipt)
    target_leaf_encoded, path = m2.build_inclusion_proof(leaves, leaf_tag)
    opened_input = _opened_input_for(receipt, leaf_tag)
    return Witness(
        leaf_tag=leaf_tag,
        opened_input=opened_input,
        inclusion_path=path,
        h_r_claimed=receipt.h_r,
    )


def verify_witness(witness: Witness) -> tuple[bool, Optional[str]]:
    """Verify a witness against its claimed H_r.

    Steps:
      1. Re-canonicalize opened_input → leaf hash
      2. Encode leaf with type tag (matches binding_m2._leaf_encoding)
      3. Walk inclusion_path → reconstruct H_r
      4. Compare to claimed H_r

    Returns (True, None) on full verification success;
    Returns (False, "NonCanonical") if any step fails — the merkle
    integrity guarantee subsumes more specific error codes here.
    """
    try:
        leaf_hash = _recompute_leaf_hash(witness.leaf_tag, witness.opened_input)
    except (KeyError, ValueError, TypeError):
        return (False, "NonCanonical")
    # Encode leaf the same way compute_H_r does (DS_LEAF + tag + h_i)
    target_leaf_encoded = m2._leaf_encoding(witness.leaf_tag, leaf_hash)
    try:
        claimed_h_r_bytes = bytes.fromhex(witness.h_r_claimed)
    except ValueError:
        return (False, "NonCanonical")
    ok = m2.verify_inclusion_proof(claimed_h_r_bytes, target_leaf_encoded,
                                    witness.inclusion_path)
    if not ok:
        return (False, "NonCanonical")
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# UnderRecordedCollapse — context-external mode check
# ─────────────────────────────────────────────────────────────────────────────
#
# Per REV3 §Deliverable 4: a context-external mode receipt has only 4
# leaves (H_s, H_c, H_m, H_j) — no self-describing identity leaves. To
# preserve admissibility guarantees, such receipts must carry witnesses
# externally. Specifically, they must carry both:
#   - a "recovery witness" — opens enough of the context to detect
#     identity substitution (e.g., a witness for id_P or id_Sigma or id_Phi)
#   - a "collapse witness" — anchors the receipt to a parent receipt or
#     external attestation
#
# UnderRecordedCollapse fires when a context-external receipt is presented
# missing both witnesses. Strict-mode receipts don't need external witnesses
# because the identity leaves are in-tree.

def verify_well_recorded(
    mode: str,
    witnesses: Optional[dict] = None,
) -> tuple[bool, Optional[str]]:
    """Check that a receipt presentation is well-recorded for its mode.

    Args:
      mode — MODE_STRICT or MODE_CONTEXT_EXTERNAL
      witnesses — dict with optional keys "recovery" and "collapse",
                  each mapping to a Witness instance (or None)

    Returns:
      (True, None) if well-recorded
      (False, "UnderRecordedCollapse") if context-external mode missing
                                        both witnesses
    """
    if mode == MODE_STRICT:
        return (True, None)
    if mode == MODE_CONTEXT_EXTERNAL:
        ws = witnesses or {}
        has_recovery = ws.get("recovery") is not None
        has_collapse = ws.get("collapse") is not None
        # Per REV3 §4.5: "context-external receipt omits BOTH recovery
        # witness AND collapse witness" — UnderRecordedCollapse fires
        # only when neither is present.
        if not has_recovery and not has_collapse:
            return (False, "UnderRecordedCollapse")
        return (True, None)
    raise ValueError(f"unknown mode: {mode!r}")


__all__ = [
    "Witness",
    "MODE_STRICT", "MODE_CONTEXT_EXTERNAL",
    "construct_witness", "verify_witness",
    "verify_well_recorded",
]
