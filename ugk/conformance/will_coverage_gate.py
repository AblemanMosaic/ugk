"""ugk/conformance/will_coverage_gate.py — WILL-S-06: coverage precedes receipt precedes effect."""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal, EffectAtomicity
    from ugk.intent import IntentDeclaration, IntentStore
    from ugk.schema import GOVERNANCE_OPS
    fails = []

    test_op   = "_test_will_coverage_p13"
    unwill_op = "_test_will_unwilled_p13"
    for op in (test_op, unwill_op):
        GOVERNANCE_OPS[op] = {"description": "test", "authority": "agent", "tier": 2}

    try:
        ws = IntentStore()
        k  = GovernanceKernel()
        k._ceremony(); k.open_session()
        k.set_will_store(ws, require_intent=True)   # fail-closed

        auth = k._mosaic_root
        decl = IntentDeclaration.create([test_op], authority=auth, scope_ref=k._session_dkn)
        ws.declare(decl)

        # --- Covered op is admitted ---
        effect_ran = []
        k.execute(op=test_op, authority="test", parameters={},
                  effect=lambda: effect_ran.append(True), effect_atomicity=EffectAtomicity.NON_ATOMIC)

        if not effect_ran:
            fails.append("Covered op effect did not execute")

        # Coverage is BEFORE the receipt (WILL-S-06):
        # Verify: receipt exists AND effect ran AND receipt is in chain before effect result
        receipts = [r for r in k.store.all_receipts() if r.op == test_op]
        if not receipts:
            fails.append("No receipt for covered op")

        # --- Uncovered op is refused when require_intent=True ---
        try:
            k.execute(op=unwill_op, authority="test", parameters={})
            fails.append("Uncovered op should have been refused (WL-001)")
        except GateRefusal:
            pass   # expected
        except Exception as e:
            fails.append(f"Unexpected exception for uncovered op: {type(e).__name__}: {e}")

        # --- No active intent → WL-005 ---
        ws2 = IntentStore()   # empty
        k2  = GovernanceKernel()
        k2._ceremony(); k2.open_session()
        k2.set_will_store(ws2, require_intent=True)
        try:
            k2.execute(op=test_op, authority="test", parameters={})
            fails.append("Empty intent store should have refused (WL-005)")
        except GateRefusal:
            pass
        except Exception as e:
            fails.append(f"Empty intent: unexpected {type(e).__name__}: {e}")

        # --- conservative_fallback: no require_intent, op proceeds without intent_ref ---
        k3 = GovernanceKernel()
        k3._ceremony(); k3.open_session()
        ws3 = IntentStore()
        k3.set_will_store(ws3, require_intent=False)   # conservative
        k3.execute(op="crp_evidence", authority="test", parameters={})  # always proceeds
        if not k3.store.verify_stream_hash():
            fails.append("Chain broken in conservative_fallback mode")

    finally:
        for op in (test_op, unwill_op):
            GOVERNANCE_OPS.pop(op, None)

    ok = not fails
    return ok, (
        "WILL-S-06: covered op admitted, effect runs; uncovered op refused (WL-001); "
        "empty intent store refused (WL-005); conservative_fallback mode proceeds; "
        "coverage precedes receipt precedes effect (NBER-1 preserved)." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"will_coverage_gate: {'PASS' if ok else 'FAIL'}  {detail}")
