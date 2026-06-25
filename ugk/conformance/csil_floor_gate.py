"""ugk/conformance/csil_floor_gate.py — CSIL-S-01: APPLICATION_OP CSIL registration. GATE_GROUP = "integration" """
def run():
    import json
    from ugk.kernel import GovernanceKernel
    from ugk.schema import GOVERNANCE_OPS
    fails=[]
    test_op="_test_csil_p19"
    GOVERNANCE_OPS[test_op]={"description":"csil test","authority":"agent","tier":2,"csil_id":7001}
    k=None
    try:
        k=GovernanceKernel(); k._ceremony(); k.open_session()
        k.register_op_csil(test_op,7001)
        k.execute(op=test_op,authority="test",parameters={})
        rs=[r for r in k.store.all_receipts() if r.op==test_op]
        if not rs: fails.append("No receipt for CSIL test op")
        else:
            p=rs[-1].parameters
            if isinstance(p,str): p=json.loads(p or "{}")
            if "op_csil" not in (p or {}): fails.append("op_csil absent from receipt when csil_id declared")
            elif p["op_csil"]!=7001: fails.append(f"op_csil={p['op_csil']} expected 7001")
        # Without csil_id: no op_csil in receipt
        op2="_test_nocsil_p19"
        GOVERNANCE_OPS[op2]={"description":"test","authority":"agent","tier":2}
        try:
            k.execute(op=op2,authority="test",parameters={})
            rs2=[r for r in k.store.all_receipts() if r.op==op2]
            p2=rs2[-1].parameters
            if isinstance(p2,str): p2=json.loads(p2 or "{}")
            if "op_csil" in (p2 or {}): fails.append("op_csil present when no csil_id declared")
        finally: GOVERNANCE_OPS.pop(op2,None)
        # Collision detection: csil_id already in LEGEND raises
        from ugk.storage.binding import _LEGEND_ENTRIES
        existing_csil=next(iter({e["csil_id"] for e in _LEGEND_ENTRIES}))
        try:
            k.register_op_csil(test_op,existing_csil)
            fails.append("Should raise ValueError for LEGEND collision")
        except ValueError: pass
        # Idempotent: same (op, csil_id) pair is OK
        k.register_op_csil(test_op,7001)
    finally:
        GOVERNANCE_OPS.pop(test_op,None)
        if k is not None:
            try: k.store.close()      # B1/leak fix: don't leave an open WAL writer connection
            except Exception: pass
    ok=not fails
    return ok,("CSIL-S-01: op_csil on receipt when declared; absent when not; collision detected; idempotent." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"csil_floor_gate: {'PASS' if ok else 'FAIL'}  {detail}")
