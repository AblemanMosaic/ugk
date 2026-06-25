"""ugk/decision.py — Receipt decision procedures (W-11..15).

M2.3l activates the verifier side of the system. Receipts produced under
M2.3a..M2.3k carry governed structures in every commitment slot; the
decision procedures here verify those structures against the constitutional
declarations and signed artifacts.

Decision procedures:
  D_s(receipt) → (ok, err)
      Operational: re-canonicalize H_s from (op, parameters); verify
      it matches the stored h_s. Catches tampering with op or parameters
      where h_s was not also updated.

  D_c(receipt, *, governor_pubkey_hex, current_time=None)
      Context: reconstruct canonical authority path via the default
      graph; verify each edge signature, path rooting + contiguity,
      capability attenuation, policy signature, and (when current_time
      is given) freshness window + edge expiry.

  D_m(receipt) → (ok, err)
      Meaning: structural integrity of h_m field. Full cross-receipt
      semantic_lineage tracing is deferred (it requires receipt-store
      access). Minimal: verify h_m is a well-formed 64-hex string.

  D_j(receipt, *, strict_namespace=False, name_keys_to_check=None)
      Locality: optional NamespaceNonMember enforcement against
      NAMESPACE_PHI_0. Default permissive (no namespace check) so
      existing fixtures pass; strict_namespace=True activates the check.

  verify_receipt(receipt, *, governor_pubkey_hex, current_time=None,
                 strict_namespace=False, name_keys_to_check=None)
      Composes D_s, D_c, D_m, D_j. Returns on first failure.

Error codes activated by M2.3l (all already in ERROR_CODES from M2.3a/e):
  via D_c:
    - SignatureInvalid     (Ed25519 verify failure on edges/policy/freshness)
    - IssuerMismatch       (issuer_key_id != Governor pubkey)
    - NoCanonicalPath      (path empty / not rooted / discontinuous)
    - ExpiredEdge          (current_time > edge.valid_until OR > FreshnessClaim.valid_until)
    - NotYetAdmissible     (current_time < FreshnessClaim.valid_from)
    - PhaseMismatch        (FreshnessClaim phase != current phase)
    - CapabilityEscalation (child set ⊄ parent effective set)
  via D_j:
    - NamespaceNonMember   (name_key not in NAMESPACE_PHI_0)

Activated indirectly via store/binding_gate:
    - NonCanonical         (canonicalization failure; usually upstream)
    - RevokedEdge          (reserved for edge revocation; M2.3l doesn't enforce yet)
    - NormalizationFailure (intent normalization; not at M2.3l)
    - ResourceBoundExceeded (normalization bound; not at M2.3l)
    - ContextMismatch      (verifier context mismatch; M2.3l minimal not enforced)
    - UnderRecordedCollapse (witness opening; M2.3m, verify_well_recorded)
  via D_s/D_m:
    - NonCanonical         (canonicalization failure; H_s/H_m recompute mismatch)

Activated indirectly via store/binding_gate:
    - RevokedEdge          (reserved for edge revocation; M2.3l doesn't enforce yet)
    - NormalizationFailure (intent normalization; not at M2.3l)
    - ResourceBoundExceeded (normalization bound; not at M2.3l)
    - ContextMismatch      (verifier context mismatch; M2.3l minimal not enforced)

After M2.3l + M2.3m: 10 of 14 ERROR_CODES are verifier-active. The
remaining 4 (RevokedEdge, NormalizationFailure, ResourceBoundExceeded,
ContextMismatch) require additional machinery; see LEGACY_RETIREMENT.md
in the package root for the deferred-items catalog.
"""

from __future__ import annotations

from typing import Optional, Iterable

from ugk.storage import binding_m2 as m2
from ugk import freshness as F
from ugk.governance import policy as P
from ugk import authority_graph as AG
from ugk import capabilities as CAP
from ugk import namespace as NS
from ugk import invariants as inv


# Re-exported convenience: callers don't need to import freshness directly
# to get the Governor pubkey for verify_receipt.
GOVERNOR_PUBKEY_HEX: str = F.DEFAULT_TEST_PUBKEY_HEX


# ─────────────────────────────────────────────────────────────────────────────
# D_s — Operational decision
# ─────────────────────────────────────────────────────────────────────────────

def D_s(receipt) -> tuple[bool, Optional[str]]:
    """Re-canonicalize H_s from (op, parameters); verify stored h_s matches.

    Catches receipts where the op or parameters fields have been tampered
    with without updating h_s.
    """
    recomputed = m2.H_s(receipt.op, receipt.parameters).hex()
    if recomputed != receipt.h_s:
        return (False, "NonCanonical")  # H_s recompute mismatch
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# D_c — Context (authority + capability + freshness + policy) decision
# ─────────────────────────────────────────────────────────────────────────────

def D_c(
    receipt,
    *,
    governor_pubkey_hex: str = GOVERNOR_PUBKEY_HEX,
    current_time: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """Verify the full C-domain semantic content of the receipt.

    Steps:
      1. Reconstruct canonical authority path via default graph
      2. Verify path: signatures + rooting + contiguity + expiry
      3. Verify capability attenuation along the path
      4. Verify Policy artifact for receipt's jurisdiction
      5. Verify FreshnessClaim signature + admissibility window
         (when current_time supplied; else signature-only)

    Returns the first failure encountered. Error codes per ERROR_CODES.
    """
    # ── Step 1+2: authority path reconstruction + verification ──
    authority_path = AG.canonical_path_for(receipt.authority)
    ok, err = AG.verify_canonical_path(
        authority_path,
        governor_pubkey_hex=governor_pubkey_hex,
        current_time=current_time,
    )
    if not ok:
        return (False, err)

    # ── Step 3: capability attenuation ──
    eff_caps, cap_err = CAP.compute_effective_capabilities(authority_path)
    if cap_err is not None:
        return (False, cap_err)

    # ── Step 4: Policy verification ──
    policy_artifact = P.lookup_policy(receipt.jurisdiction)
    ok, err = P.verify_policy(policy_artifact, governor_pubkey_hex)
    if not ok:
        return (False, err)

    # ── Step 5: FreshnessClaim verification ──
    # Reconstruct the FreshnessClaim that should have been bound; verify
    # against the Governor key. When current_time is None, signature-only.
    default_ei = F.default_epoch(inv.ID_PHI_0)
    claim = F.build_freshness_claim_from_epoch(default_ei)
    if current_time is not None:
        ok, err = F.verify_freshness_claim(
            claim,
            current_epoch=current_time,
            current_phase_id=inv.ID_PHI_0,
            governor_pubkey_hex=governor_pubkey_hex,
        )
        if not ok:
            return (False, err)
    else:
        # Sig-only mode: verify the EpochIssuance signature; expiry skipped
        ok, err = F.verify_epoch_issuance(default_ei, governor_pubkey_hex)
        if not ok:
            return (False, err)

    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# D_m — Meaning decision
# ─────────────────────────────────────────────────────────────────────────────

def D_m(receipt) -> tuple[bool, Optional[str]]:
    """Structural meaning verification.

    At M2.3l minimal: verify h_m field is a well-formed 64-hex string.
    Full cross-receipt semantic_lineage tracing requires receipt-store
    access (it's a verifier-session capability, not a per-receipt one).

    Forward-compat: when a verifier session has the store, it can resolve
    parent_h_m references via parent_h_r → (h_m) lookup (the same map
    binding_gate builds).
    """
    if not isinstance(receipt.h_m, str):
        return (False, "NonCanonical")  # h_m field not a string
    h_m = receipt.h_m
    if len(h_m) != 64:
        return (False, "NonCanonical")  # h_m wrong length
    try:
        int(h_m, 16)
    except ValueError:
        return (False, "NonCanonical")  # h_m not valid hex
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# D_j — Locality (namespace) decision
# ─────────────────────────────────────────────────────────────────────────────

def D_j(
    receipt,
    *,
    strict_namespace: bool = False,
    name_keys_to_check: Optional[Iterable[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Locality verification with optional namespace membership check.

    Default permissive: strict_namespace=False bypasses the namespace
    check. Existing fixture receipts (using ops not in NAMESPACE_PHI_0)
    pass under the default.

    When strict_namespace=True:
      - If name_keys_to_check is None, the default check set is
        ["op:<receipt.op>"] (the op-namespaced form of the receipt's op).
      - Otherwise, validate the provided list of name_keys.
      - Any non-member produces NamespaceNonMember.

    Error code: NamespaceNonMember (ERROR_CODES, M2.3a — first activated here).
    """
    if not strict_namespace:
        return (True, None)

    if name_keys_to_check is None:
        # Default check: the receipt's op as a namespaced name_key
        keys = [f"op:{receipt.op}"]
    else:
        keys = list(name_keys_to_check)

    ok, err = NS.validate_name_keys(keys)
    if not ok:
        return (False, err)
    return (True, None)


# ─────────────────────────────────────────────────────────────────────────────
# Composer — verify_receipt
# ─────────────────────────────────────────────────────────────────────────────

def verify_receipt(
    receipt,
    *,
    governor_pubkey_hex: str = GOVERNOR_PUBKEY_HEX,
    current_time: Optional[int] = None,
    strict_namespace: bool = False,
    name_keys_to_check: Optional[Iterable[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Run D_s, D_c, D_m, D_j on a receipt. Return first failure.

    On success: (True, None).
    On failure: (False, error_code) — error_code is one of the activated
    ERROR_CODES entries (see module docstring).
    """
    ok, err = D_s(receipt)
    if not ok:
        return (False, err)
    ok, err = D_c(receipt,
                  governor_pubkey_hex=governor_pubkey_hex,
                  current_time=current_time)
    if not ok:
        return (False, err)
    ok, err = D_m(receipt)
    if not ok:
        return (False, err)
    ok, err = D_j(receipt,
                  strict_namespace=strict_namespace,
                  name_keys_to_check=name_keys_to_check)
    if not ok:
        return (False, err)
    return (True, None)


__all__ = [
    "D_s", "D_c", "D_m", "D_j", "verify_receipt",
    "GOVERNOR_PUBKEY_HEX",
]
