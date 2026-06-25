"""ugk/conformance/alt_instance_gate.py — ALT-I-02/03/04. GATE_GROUP = "integration" """
def run():
    import json
    from ugk.kernel import GovernanceKernel,GateRefusal
    from ugk.intent import IntentDeclaration,IntentStore
    from ugk.gate_probe import phi_score,CONSTITUTIVE,ConstitutiveProbeResult
    from ugk.schema import GOVERNANCE_OPS
    from ugk.storage.binding import canonical_json as _cj
    import hashlib,time
    fails=[]
    # ALT-I-02: authority_set annotation
    op="_test_alti_p16"
    GOVERNANCE_OPS[op]={"description":"test","authority":"agent","tier":2}
    try:
        k=GovernanceKernel(); k._ceremony(); k.open_session()
        k.execute(op=op,authority="test",parameters={},authority_set=["w1","w2"])
        rs=[r for r in k.store.all_receipts() if r.op==op]
        p=rs[-1].parameters
        if isinstance(p,str): p=json.loads(p or "{}")
        if "authority_set" not in (p or {}): fails.append("authority_set absent from receipt")
        elif set(p["authority_set"])!={"w1","w2"}: fails.append("authority_set mismatch")
        k.execute(op=op,authority="test",parameters={})
        p2=k.store.all_receipts()[-1].parameters
        if isinstance(p2,str): p2=json.loads(p2 or "{}")
        if "authority_set" in (p2 or {}): fails.append("authority_set present when not supplied")
    finally: GOVERNANCE_OPS.pop(op,None)
    # ALT-I-03: require_scoped_intent
    op2="_test_alti2_p16"
    GOVERNANCE_OPS[op2]={"description":"test","authority":"agent","tier":2}
    try:
        ws=IntentStore(); k2=GovernanceKernel(); k2._ceremony(); k2.open_session()
        k2.set_will_store(ws,require_intent=True,require_scoped_intent=True)
        ws.declare(IntentDeclaration.create([op2],authority=k2._mosaic_root,scope_ref=""))
        try: k2.execute(op=op2,authority="test",parameters={}); fails.append("Open-scope should not cover")
        except GateRefusal: pass
        ws2=IntentStore(); k3=GovernanceKernel(); k3._ceremony(); k3.open_session()
        k3.set_will_store(ws2,require_intent=True,require_scoped_intent=True)
        ws2.declare(IntentDeclaration.create([op2],authority=k3._mosaic_root,scope_ref=k3._session_dkn))
        k3.execute(op=op2,authority="test",parameters={})  # should succeed
    finally: GOVERNANCE_OPS.pop(op2,None)
    # ALT-I-04: phi computation
    if phi_score({})!=0.0: fails.append("phi(empty)!=0.0")
    test_gops={"_a":{"description":"","authority":"","tier":2},"_b":{"description":"","authority":"","tier":2}}
    if phi_score(test_gops)!=1.0: fails.append("phi(all unprobed)!=1.0")
    ts=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    body={"all_refused":True,"op":"_a","refusing_inputs_tested":1,"status":CONSTITUTIVE,"timestamp":ts}
    rh=hashlib.sha256(_cj(body)).hexdigest()
    probe_a=ConstitutiveProbeResult(result_hash=rh,op="_a",status=CONSTITUTIVE,refusing_inputs_tested=1,all_refused=True,timestamp=ts)
    phi_h=phi_score(test_gops,{"_a":probe_a})
    if abs(phi_h-0.5)>0.01: fails.append(f"phi(one constitutive)={phi_h}, expected 0.5")
    ok=not fails
    return ok,("ALT-I-02/03/04: authority_set receipted; scoped_intent excludes open-scope; φ correct." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"alt_instance_gate: {'PASS' if ok else 'FAIL'}  {detail}")
