"""ugk/conformance/refusal_warrant_gate.py — DW-S-03: refusal warrants symmetric with admission."""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal
    from ugk.governance.warrant import WarrantStore, RESULT_REFUSE, RESULT_ADMIT
    fails = []

    ws = WarrantStore()
    k = GovernanceKernel()
    k._ceremony(); k.open_session()
    k.set_warrant_store(ws)

    # Execute with gate that fails + warrant_basis → refusal warrant produced
    try:
        k.execute(
            op="crp_evidence",
            authority="refusal_test",
            parameters={},
            gate=lambda: False,   # always refuse
            warrant_basis=[1008, 1010, 1003],
        )
    except GateRefusal:
        pass   # expected
    except Exception as e:
        fails.append(f"Unexpected exception: {type(e).__name__}: {e}")

    refusal_warrants = [w for w in ws.all_warrants() if w.result == RESULT_REFUSE]
    if not refusal_warrants:
        fails.append("No refusal warrant in WarrantStore after gate failure with warrant_basis")

    # Admission warrant also present (from ceremony path)
    # Execute with passing gate + warrant_basis → admission warrant
    k.execute(
        op="crp_evidence",
        authority="refusal_test",
        parameters={"admit": True},
        gate=lambda: True,
        warrant_basis=[1008, 1010],
    )
    admit_warrants = [w for w in ws.all_warrants() if w.result == RESULT_ADMIT]
    if not admit_warrants:
        fails.append("No admission warrant after successful gate with warrant_basis")

    # Verify refusal warrant fields
    rw = refusal_warrants[0]
    if not rw.verify_hash():
        fails.append("Refusal warrant hash does not verify")
    if set(rw.constitutional_basis) != {1003, 1008, 1010}:
        fails.append(f"Refusal warrant basis wrong: {rw.constitutional_basis}")

    # Execute without warrant_basis + gate failure → GateRefusal, no new warrant
    count_before = ws.warrant_count()
    try:
        k.execute(op="crp_evidence", authority="no_basis",
                  parameters={}, gate=lambda: False)
    except GateRefusal:
        pass
    if ws.warrant_count() != count_before:
        fails.append("Warrant written for refusal without warrant_basis (should not happen)")

    ok = not fails
    return ok, (
        f"DW-S-03: refusal warrant produced on gate failure with warrant_basis; "
        f"warrant.result=RESULT_REFUSE; hash verifies; no warrant without warrant_basis." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"refusal_warrant_gate: {'PASS' if ok else 'FAIL'}  {detail}")
