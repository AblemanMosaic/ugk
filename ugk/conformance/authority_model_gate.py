"""ugk/conformance/authority_model_gate.py — CM-S-01/02/03. GATE_GROUP = "unit" """
def run():
    from ugk.authority.authority_model import AuthorityModel
    from ugk.kernel import GovernanceKernel, KernelInternalOp
    from ugk.governance.warrant import WarrantStore
    from ugk.schema import GOVERNANCE_OPS
    fails=[]
    auth="mosaic_"+"a"*40
    # CM-S-01: content-addressed, presets correct
    m1=AuthorityModel.alt_prevention("l"*64,auth)
    if not m1.verify_hash(): fails.append("verify_hash failed")
    m2=AuthorityModel.alt_trace("l"*64,auth)
    if m1.model_hash==m2.model_hash: fails.append("Different presets same hash")
    if not (m1.require_gate and m1.require_warrant and m1.require_intent): fails.append("alt_prevention flags wrong")
    m3=AuthorityModel.trace_only("l"*64,auth)
    if any([m3.require_gate,m3.require_warrant,m3.require_intent]): fails.append("trace_only flags wrong")
    # CM-S-02: require_gate
    test_op="_test_cm_p15"
    GOVERNANCE_OPS[test_op]={"description":"test","authority":"agent","tier":2}
    try:
        k=GovernanceKernel(); k._ceremony(); k.open_session()
        model=AuthorityModel.create("custom",True,False,False,"t","t",k._law_hash,k._mosaic_root)
        k.set_authority_model(model)
        try: k.execute(op=test_op,authority="test",parameters={}); fails.append("require_gate: should raise")
        except KernelInternalOp: pass
        k.execute(op=test_op,authority="test",parameters={},gate=lambda:True)
        stored=k._store.get_authority_model(model.model_hash)
        if stored is None: fails.append("AuthorityModel not in store")
    finally: GOVERNANCE_OPS.pop(test_op,None)
    # CM-S-03: require_warrant
    test_op2="_test_cm2_p15"
    GOVERNANCE_OPS[test_op2]={"description":"test","authority":"agent","tier":2}
    try:
        k2=GovernanceKernel(); k2._ceremony(); k2.open_session()
        model2=AuthorityModel.create("custom",False,True,False,"t","t",k2._law_hash,k2._mosaic_root)
        k2.set_authority_model(model2)
        try: k2.execute(op=test_op2,authority="test",parameters={}); fails.append("require_warrant: should raise")
        except KernelInternalOp: pass
        k2.set_warrant_store(WarrantStore())
        k2.execute(op=test_op2,authority="test",parameters={},warrant_basis=[1001])
    finally: GOVERNANCE_OPS.pop(test_op2,None)
    ok=not fails
    return ok,("CM-S-01/02/03: content-addressed, presets correct, require_gate+require_warrant enforced." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"authority_model_gate: {'PASS' if ok else 'FAIL'}  {detail}")
