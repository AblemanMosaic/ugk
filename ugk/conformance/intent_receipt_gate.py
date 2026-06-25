"""ugk/conformance/intent_receipt_gate.py — WILL-S-05: receipt.intent_ref tamper-evident in chain."""


def run():
    from ugk.storage.binding import dm_s03
    from ugk.intent import IntentDeclaration, IntentStore
    from ugk.kernel import GovernanceKernel
    from ugk.schema import GOVERNANCE_OPS
    fails = []

    # dm_s03 is sensitive to intent_ref (D_I dimension)
    base = dict(
        state_hash="s" * 64, parent="p" * 64, intent="crp_evidence",
        authority="system", jurisdiction="session", confidence="high",
        session_id="dkn", agent_id="dkn", ts="1700000000.0",
        law_hash="l" * 64, legend_hash="g" * 64,
    )
    h_no_intent  = dm_s03(**base)
    h_with_intent = dm_s03(**base, intent_ref="i" * 64)
    h_diff_intent = dm_s03(**base, intent_ref="j" * 64)

    if h_with_intent == h_no_intent:
        fails.append("Adding intent_ref to dm_s03 did not change semantic_hash")
    if h_with_intent == h_diff_intent:
        fails.append("Different intent_ref values produced same semantic_hash")

    # Kernel writes intent_ref onto receipt via conservative_fallback
    test_op = "_test_will_receipt_p13"
    GOVERNANCE_OPS[test_op] = {"description": "test", "authority": "agent", "tier": 2}
    try:
        ws = IntentStore()
        k = GovernanceKernel()
        k._ceremony(); k.open_session()
        k.set_will_store(ws, require_intent=False)

        auth = k._mosaic_root
        decl = IntentDeclaration.create([test_op], authority=auth, scope_ref=k._session_dkn)
        ws.declare(decl)

        k.execute(op=test_op, authority="test", parameters={})
        receipts = [r for r in k.store.all_receipts() if r.op == test_op]
        if not receipts:
            fails.append(f"No {test_op!r} receipt found")
        else:
            r = receipts[-1]
            if not r.intent_ref:
                fails.append("Receipt has empty intent_ref despite covered operation")
            elif r.intent_ref != decl.declaration_hash:
                fails.append(f"Receipt intent_ref {r.intent_ref[:8]!r}… != declaration_hash")
            # Chain remains intact with intent_ref in dm_s03
            if not k.store.verify_stream_hash():
                fails.append("Chain broken after write with intent_ref in dm_s03")
    finally:
        GOVERNANCE_OPS.pop(test_op, None)

    ok = not fails
    return ok, (
        "WILL-S-05: dm_s03 is intent_ref-sensitive (D_I); "
        "receipt.intent_ref records covering declaration_hash; "
        "chain intact with intent_ref in CHC." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"intent_receipt_gate: {'PASS' if ok else 'FAIL'}  {detail}")
