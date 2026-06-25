"""ugk/conformance/posture_gate.py — CGP-S-01. GATE_GROUP = "unit" """
def run():
    from ugk.governance.posture import GovernancePosture
    from ugk.kernel import GovernanceKernel
    fails=[]
    k=GovernanceKernel(); k._ceremony(); k.open_session(); k.execute(op="crp_evidence",authority="test",parameters={})
    p=GovernancePosture.compute(k)
    if not p.verify_hash(): fails.append("verify_hash() failed")
    # Content-addressing: two computes at different times may differ (timestamp) but structure is consistent
    if p.phi<0.0 or p.phi>1.0: fails.append(f"phi out of range: {p.phi}")
    if p.disjunct_a not in ("covered","partial","absent"): fails.append(f"disjunct_a invalid: {p.disjunct_a}")
    if p.receipt_count<1: fails.append("receipt_count should be >= 1")
    if not p.chain_intact: fails.append("chain_intact should be True")
    # JSON format
    rpt=p.report("json")
    import json; d=json.loads(rpt)
    for key in ["posture_hash","authority_model","phi","disjuncts","chain","matrix"]:
        if key not in d: fails.append(f"JSON report missing {key!r}")
    ok=not fails
    return ok,("CGP-S-01: GovernancePosture content-addressed; fields valid; JSON report complete." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"posture_gate: {'PASS' if ok else 'FAIL'}  {detail}")
