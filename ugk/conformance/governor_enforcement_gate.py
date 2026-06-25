"""ugk/conformance/governor_enforcement_gate.py — Phase 2: Governor interposition enforcement."""


def run():
    """Prove the Governor interposition mechanism:
      - With require_governor_sig=True, Tier 2 APPLICATION ops need a valid
        Governor Ed25519 signature or GovernorSignatureRequired is raised.
      - With a valid signature, the op is admitted.
      - Universal ops (Tier 1) are never gated by require_governor_sig.
    """
    from ugk.kernel import (
        GovernanceKernel, GOVERNOR_PUBKEY_HEX, STATUS_ACTIVE,
    )
    from ugk.governance.governor import GovernorSignatureRequired, sign_as_governor
    from ugk.storage.binding import canonical_json
    from ugk import ops as _ops_module, schema as _schema
    fails = []

    priv_hex = "cb181d9a650b7605b94602d0d6a2640a38fa1a0f1086c4896f98e40c21766857"  # dev fixture

    # Setup: declare a Tier 2 APPLICATION op
    original = dict(_ops_module.APPLICATION_OPS)
    _ops_module.APPLICATION_OPS["_enf_test_op"] = {"description": "enforcement test", "tier": 2}
    _schema.GOVERNANCE_OPS["_enf_test_op"] = {"description": "enforcement test", "tier": 2}

    try:
        k = GovernanceKernel()
        from ugk.conformance._fixture import unfounded as _unfounded
        from ugk.kernel import GovernanceNotFounded as _GNF
        if _unfounded():
            # Unfounded posture: interposition is moot — governance cannot be
            # founded at all. Prove fail-closed and return (typed, non-silent).
            try:
                k._ceremony()
                fails.append("sentinel ceremony ADMITTED — enforcement surface reachable unfounded")
            except _GNF:
                pass
            k.open_session()  # Tier-1 lawful
            try:
                k.execute(op="_enf_test_op", authority="test", parameters={"x": 1})
                fails.append("Tier-2 op ADMITTED on unfounded kernel")
            except _GNF:
                pass
            ok = not fails
            return ok, (
                "governor_enforcement_gate (unfounded): ceremony refused; Tier-2 refused; "
                "fail-closed proven — interposition proofs run on founded deployments."
                if ok else "; ".join(fails)
            )
        k._ceremony()
        k.open_session()
        assert k.status == STATUS_ACTIVE

        # --- Enable Governor interposition ---
        k._require_governor_sig = True

        # Without signature → GovernorSignatureRequired
        try:
            k.execute(op="_enf_test_op", authority="test", parameters={"x": 1})
            fails.append("No GovernorSignatureRequired raised when sig absent")
        except GovernorSignatureRequired as e:
            if e.op != "_enf_test_op":
                fails.append(f"GovernorSignatureRequired.op is {e.op!r}")
        except Exception as e:
            fails.append(f"Wrong exception: {type(e).__name__}: {e}")

        # With wrong signature → GovernorSignatureRequired
        try:
            k.execute(op="_enf_test_op", authority="test", parameters={"x": 1},
                      governor_sig="ab" * 64)
            fails.append("No GovernorSignatureRequired raised for bad sig")
        except GovernorSignatureRequired:
            pass
        except Exception as e:
            fails.append(f"Wrong exception for bad sig: {type(e).__name__}: {e}")

        # With valid signature → admitted
        params = {"x": 1}
        msg = canonical_json({"op": "_enf_test_op", "parameters": params})
        valid_sig = sign_as_governor(priv_hex, msg)
        try:
            k.execute(op="_enf_test_op", authority="test", parameters=params,
                      governor_sig=valid_sig)
        except Exception as e:
            fails.append(f"Valid signature rejected: {type(e).__name__}: {e}")

        # Universal ops (crp_evidence) are never gated
        try:
            k.execute(op="crp_evidence", authority="test", parameters={"u": True})
        except GovernorSignatureRequired:
            fails.append("crp_evidence (Tier 1) was gated by require_governor_sig (wrong)")
        except Exception as e:
            fails.append(f"crp_evidence raised unexpected: {type(e).__name__}: {e}")

        # Disable interposition → Tier 2 admitted without sig
        k._require_governor_sig = False
        try:
            k.execute(op="_enf_test_op", authority="test", parameters={"x": 2})
        except Exception as e:
            fails.append(f"Tier 2 op rejected after disabling interposition: {e}")

    finally:
        _ops_module.APPLICATION_OPS.clear()
        _ops_module.APPLICATION_OPS.update(original)
        _schema.GOVERNANCE_OPS.pop("_enf_test_op", None)

    ok = not fails
    return ok, (
        "governor_enforcement_gate: absent/invalid sig raises GovernorSignatureRequired; "
        "valid sig admitted; Tier 1 never gated; disabling flag allows Tier 2." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"governor_enforcement_gate: {'PASS' if ok else 'FAIL'}  {detail}")
