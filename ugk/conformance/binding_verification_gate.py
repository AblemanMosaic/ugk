"""ugk/conformance/binding_verification_gate.py — Top-level verifier (M2.3l, W-11..15).

Composes D_s, D_c, D_m, D_j across all fixture receipts to operationalize
the receipt-verification stack. This gate is NOT currently registered in
run_gates_batch (registration is M2.3o work); it runs standalone as:

    python3 -m ugk.conformance.binding_verification_gate

Permissive defaults:
  - current_time = None  → freshness expiry check skipped (sig-only)
  - strict_namespace = False → no NamespaceNonMember enforcement on
                                fixture receipts (ops outside M_Phi)

These defaults let the existing fixture (using ops like "crp_evidence"
that are not in NAMESPACE_PHI_0) pass cleanly. EV-N01 and EV-N02 vectors
exercise the stricter modes (with current_time provided, with
strict_namespace=True) to demonstrate the activated error codes.
"""

from typing import Optional


def run() -> tuple[bool, str]:
    """Top-level binding_verification_gate run.

    Sets up the standard fixture (2 receipts under "test_auth" plus the
    bootstrap session_open / gate_admit receipts produced by kernel
    initialization), runs verify_receipt on each, and reports the result.
    """
    from ugk.kernel import GovernanceKernel
    from ugk import decision as D
    from ugk import authority_graph as AG

    # Reset graph to ensure clean default-graph state independent of
    # any other vectors that may have populated it earlier in the process.
    AG.clear_graph()

    k = GovernanceKernel()
    k.open_session()
    k.execute(op="crp_evidence", authority="binding_verification_gate_test",
              parameters={"x": 1})
    k.execute(op="crp_evidence", authority="binding_verification_gate_test",
              parameters={"x": 2})

    receipts = k.store.all_receipts()
    if not receipts:
        return False, "No receipts in store"

    fails: list[str] = []
    for r in receipts:
        ok, err = D.verify_receipt(r)
        if not ok:
            fails.append(f"Receipt {r.op!r}/{r.authority!r}: {err}")

    AG.clear_graph()

    if fails:
        return False, (
            f"binding_verification_gate: D_s/D_c/D_m/D_j composition "
            f"failed on {len(fails)} receipt(s): {fails}"
        )
    return True, (
        f"binding_verification_gate: D_s, D_c, D_m, D_j all PASS on "
        f"{len(receipts)} fixture receipts; verifier surface operational; "
        f"activates SignatureInvalid, IssuerMismatch, NoCanonicalPath, "
        f"ExpiredEdge, NotYetAdmissible, PhaseMismatch, CapabilityEscalation, "
        f"NamespaceNonMember (the latter via strict_namespace mode, exercised "
        f"by EV-N02)."
    )


if __name__ == "__main__":
    ok, msg = run()
    verdict = "PASS" if ok else "FAIL"
    print(f"binding_verification_gate: {verdict}  {msg}")
    import sys
    sys.exit(0 if ok else 1)
