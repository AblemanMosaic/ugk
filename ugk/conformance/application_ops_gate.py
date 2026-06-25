"""ugk/conformance/application_ops_gate.py — Phase 12: APPLICATION_OPS deployer pattern."""


def run():
    from ugk.schema import GOVERNANCE_OPS
    from ugk.kernel import GovernanceKernel, EffectAtomicity
    from ugk.governance.warrant import WarrantStore
    fails = []

    # Inject a demo APPLICATION_OPS entry (Tier 2)
    test_op = "_test_app_op_phase12"
    GOVERNANCE_OPS[test_op] = {
        "description": "Phase 12 APPLICATION_OPS smoke test",
        "authority":   "agent",
        "tier":        2,
    }

    try:
        ws = WarrantStore()
        k = GovernanceKernel()
        k._ceremony(); k.open_session()
        k.set_warrant_store(ws)

        result = {}
        k.execute(
            op=test_op,
            authority="app_ops_gate_agent",
            parameters={"gate_test": True},
            gate=lambda: True,
            effect=lambda: result.update({"ran": True}),
            warrant_basis=[1008, 1010], effect_atomicity=EffectAtomicity.NON_ATOMIC,
        )

        if not result.get("ran"):
            fails.append("Effect did not execute for APPLICATION_OPS entry")

        receipts = k.store.receipts_by_op(test_op)
        if not receipts:
            fails.append(f"No receipt for op {test_op!r}")

        if not k.store.verify_stream_hash():
            fails.append("Chain broken after APPLICATION_OPS execute")

        # Warrant produced
        warrants = ws.all_warrants()
        if not warrants:
            fails.append("No warrant produced for APPLICATION_OPS execute with warrant_basis")

        k.close_session()
        summary = k.last_summary
        if summary is None:
            fails.append("No SessionSummary after close_session()")

    finally:
        GOVERNANCE_OPS.pop(test_op, None)

    ok = not fails
    return ok, (
        "Phase 12: APPLICATION_OPS deployer pattern works — op declared, "
        "executed with gate+effect+warrant_basis, receipt produced, "
        "chain intact, SessionSummary produced." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"application_ops_gate: {'PASS' if ok else 'FAIL'}  {detail}")
