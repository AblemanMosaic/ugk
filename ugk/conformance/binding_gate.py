"""ugk/conformance/binding_gate.py — CHC-S-01 (M2 form): THR binding structure on receipts.

Phase M2.3b — bridge surface that restores invariant_registry_gate by providing
a gate file for the gate name referenced by CHC-S-01's rewritten statement.

What this gate exercises (no new runtime machinery — only observes M2.2 output):
  1. Every receipt produced by the kernel carries the M2 binding block
     populated (h_s, h_c, h_m, h_j, h_r, parent_h_r, mode, version).
  2. Each per-commitment hash is a 64-character lowercase hex string
     (SHA-256 output).
  3. H_r recomputes byte-identically from the stored Receipt body using the
     same field-to-c_i mapping that store.write() uses (verifier round-trip).
  4. Mode defaults to "strict" (per REV3 §Deliverable 4).
  5. The legacy CHC block (state_hash, semantic_hash, prior_receipt_hash)
     also remains populated — side-by-side integration invariant from M2.2.

Coexistence with chc_gate:
  This gate observes the M2 binding block. chc_gate observes the legacy CHC
  block. Both pass on the same receipts post-M2.2 because the side-by-side
  integration populates both blocks. The two will be reconciled at a later
  M2.3 subphase (chc_gate retirement coupled with schema clean-break).
"""

from __future__ import annotations
import dataclasses


def run():
    from ugk.kernel import GovernanceKernel
    from ugk.storage import binding_m2 as m2

    fails = []

    k = GovernanceKernel()
    k.open_session()
    k.execute(op="crp_evidence", authority="binding_gate_test", parameters={"x": 1})
    k.execute(op="crp_evidence", authority="binding_gate_test", parameters={"x": 2})

    receipts = k.store.all_receipts()
    if not receipts:
        return False, "No receipts in store"

    # ── (1) M2 block populated on every receipt ──
    for r in receipts:
        if not r.h_s:
            fails.append(f"Receipt {r.op!r}: h_s empty")
        if not r.h_c:
            fails.append(f"Receipt {r.op!r}: h_c empty")
        if not r.h_m:
            fails.append(f"Receipt {r.op!r}: h_m empty")
        if r.h_j is None or not r.h_j:
            fails.append(f"Receipt {r.op!r}: h_j empty (strict mode requires H_j)")
        if not r.h_r:
            fails.append(f"Receipt {r.op!r}: h_r empty")
        if not r.mode:
            fails.append(f"Receipt {r.op!r}: mode empty")
        if not r.version:
            fails.append(f"Receipt {r.op!r}: version empty")

    # ── (2) Per-commitment hashes are 64-char lowercase hex ──
    def _is_sha256_hex(s: str) -> bool:
        return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)

    for r in receipts:
        for name, val in [("h_s", r.h_s), ("h_c", r.h_c), ("h_m", r.h_m),
                          ("h_j", r.h_j or ""), ("h_r", r.h_r)]:
            if not _is_sha256_hex(val):
                fails.append(f"Receipt {r.op!r}: {name} not valid SHA-256 hex: {val!r}")

    # ── (3) H_r round-trips from stored body (independent verifier) ──
    # Uses the same field-to-c_i mapping declared constitutionally in
    # CANONICALIZATION_DOMAINS (invariants.py) and implemented in store.write().
    # M2.3d: regime and phase identifiers sourced from invariants.ID_SIGMA_0
    # and invariants.ID_PHI_0 instead of placeholder string literals.
    # M2.3e: FreshnessClaim is constructed from a signed default EpochIssuance.
    # M2.3g: policy_id and id_P leaf derived from a signed Policy artifact.
    # M2.3f: authority_key derived from the authority-key registry.
    # M2.3h: authority_chain derived from canonical path through G_c.
    # M2.3i: capabilities is the attenuated effective set at the terminal
    # authority, computed from the canonical path via capabilities.compute_
    # effective_capabilities.
    # M2.3j: semantic_lineage reconstructed from receipt sequence — each
    # receipt's lineage references its predecessor's H_m via the
    # parent_h_r → (h_m, intent_ref) lookup map built below.
    # M2.3k: mosaic_root sourced from namespace.MOSAIC_ROOT_PHI_0
    # (cryptographic commitment to NAMESPACE_PHI_0).
    from ugk import invariants as inv
    from ugk import freshness as F
    from ugk.governance import policy as P
    from ugk import authority_keys as AK
    from ugk import authority_graph as AG
    from ugk import capabilities as CAP
    from ugk import lineage as L
    from ugk import namespace as NS

    _default_freshness = F.build_freshness_claim_from_epoch(
        F.default_epoch(inv.ID_PHI_0)
    )

    # M2.3j — lineage lookup: receipt's H_r → (H_m, intent_ref). Allows
    # reconstructing the semantic_lineage flowing into H_m from the
    # parent_h_r linkage on each receipt.
    _lineage_lookup: dict[str, tuple] = {
        r.h_r: (r.h_m, r.intent_ref or "") for r in receipts
    }

    def _recompute_H_r(rcpt) -> str:
        freshness = _default_freshness
        policy_id_v = P.lookup_policy_id(rcpt.jurisdiction)
        authority_key_v = AK.lookup_authority_key(rcpt.authority)
        authority_chain_objs = AG.canonical_path_for(rcpt.authority)
        authority_chain_v = AG.canonical_path_as_dicts(rcpt.authority)
        eff_caps, cap_err = CAP.compute_effective_capabilities(authority_chain_objs)
        if cap_err is not None:
            raise ValueError(f"capability escalation in recompute: {cap_err}")
        capabilities_v = sorted(eff_caps)
        # M2.3j — reconstruct lineage from parent_h_r lookup
        if rcpt.parent_h_r in _lineage_lookup:
            parent_h_m, parent_intent_ref = _lineage_lookup[rcpt.parent_h_r]
            semantic_lineage_v = L.lineage_as_dicts(
                L.build_lineage(parent_h_m, parent_intent_ref)
            )
        else:
            # Root receipt (parent_h_r == GENESIS or unknown) → empty lineage
            semantic_lineage_v = L.lineage_as_dicts(L.build_lineage(None))
        h_s = m2.H_s(rcpt.op, rcpt.parameters)
        h_c = m2.H_c(
            authority_chain=authority_chain_v,
            policy_id=policy_id_v,
            capabilities=capabilities_v,
            warrant_basis=([rcpt.warrant_id] if rcpt.warrant_id else []),
            parent_H_r=rcpt.parent_h_r,
            freshness=freshness,
        )
        h_m = m2.H_m(rcpt.intent, rcpt.intent_ref, rcpt.legend_hash,
                     semantic_lineage_v,
                     semantic_regime_id=inv.ID_SIGMA_0)
        h_j = m2.H_j(freshness["phase_code"], NS.MOSAIC_ROOT_PHI_0,
                     rcpt.session_dkn, authority_key_v)
        leaves = [
            (m2.TAG_H_S, h_s), (m2.TAG_H_C, h_c),
            (m2.TAG_H_M, h_m), (m2.TAG_H_J, h_j),
            (m2.TAG_ID_P,     m2.H_id_P(policy_id_v)),
            (m2.TAG_ID_SIGMA, m2.H_id_Sigma(inv.ID_SIGMA_0)),
            (m2.TAG_ID_PHI,   m2.H_id_Phi(inv.ID_PHI_0)),
        ]
        return m2.compute_H_r(leaves).hex()

    for r in receipts:
        recomputed = _recompute_H_r(r)
        if recomputed != r.h_r:
            fails.append(
                f"Receipt {r.op!r}: H_r round-trip mismatch — "
                f"stored {r.h_r[:16]}... vs recomputed {recomputed[:16]}..."
            )

    # ── (4) Mode defaults to strict per REV3 §Deliverable 4 ──
    for r in receipts:
        if r.mode != "strict":
            fails.append(f"Receipt {r.op!r}: mode={r.mode!r}, expected 'strict' default")

    # ── (5) RT-3 (E5b): body↔H_r tamper-evidence on the M2 surface (replaces the retired legacy
    #        CHC block). Perturbing a bound body field changes the recomputed H_r. ──
    if receipts:
        _r0 = receipts[-1]
        _tampered = dataclasses.replace(_r0, intent=_r0.intent + "_TAMPER")
        if _recompute_H_r(_tampered) == _r0.h_r:
            fails.append("RT-3: body tamper (intent) did not change recomputed H_r (M2 not tamper-evident)")

    ok = not fails
    n = len(receipts)
    return ok, (
        f"CHC-S-01 (M2 form): THR binding structure present and verifiable on "
        f"all {n} receipts; H_r round-trips from stored body; body tamper changes "
        f"recomputed H_r. M2 binding sound." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"binding_gate: {'PASS' if ok else 'FAIL'}  {detail}")
