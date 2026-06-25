"""ugk/conformance/refusal_gate.py — ESA-S-01: GateRefusal is first-class, receipted before raising."""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal
    fails = []

    k = GovernanceKernel()
    k.open_session()
    count_before = k.store.receipt_count()

    try:
        k.execute(op="crp_evidence", authority="ref_test", parameters={"x": 1},
                  gate=lambda: False)
        fails.append("GateRefusal was not raised")
    except GateRefusal as e:
        # gate_refuse receipt must be in the store BEFORE the exception propagated
        refuse_receipts = k.store.receipts_by_op("gate_refuse")
        if not refuse_receipts:
            fails.append("gate_refuse receipt missing after GateRefusal")
        else:
            # The receipt must have failed=True
            last = refuse_receipts[-1]
            if not last.failed:
                fails.append("gate_refuse receipt has failed=False, expected True")
            # Receipt must reference the refused op
            if last.parameters.get("op") != "crp_evidence":
                fails.append(
                    f"gate_refuse receipt op param is {last.parameters.get('op')!r}, "
                    f"expected 'crp_evidence'"
                )
        # GateRefusal must carry the op name
        if e.op != "crp_evidence":
            fails.append(f"GateRefusal.op is {e.op!r}, expected 'crp_evidence'")
    except Exception as e:
        fails.append(f"Unexpected exception: {type(e).__name__}: {e}")

    # Verify refusal_count() reflects it
    if k.store.refusal_count() == 0:
        fails.append("refusal_count() is 0 after a refusal (Cap-2 not working)")

    ok = not fails
    return ok, ("ESA-S-01: GateRefusal produces structured gate_refuse receipt (failed=True) "
                "before raising; refusal_count() incremented." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"refusal_gate: {'PASS' if ok else 'FAIL'}  {detail}")
