"""ugk/conformance/constitutive_probe_gate.py — ALT-I-01. GATE_GROUP = "unit" """
def run():
    from ugk.gate_probe import probe_constitutive,CONSTITUTIVE,CEREMONIAL,UNPROBED
    fails=[]
    r1=probe_constitutive("t",None,refusing_inputs=[])
    if r1.status!=UNPROBED: fails.append(f"No inputs: expected UNPROBED got {r1.status}")
    if not r1.verify_hash(): fails.append("UNPROBED hash invalid")
    r2=probe_constitutive("t",None,refusing_inputs=[{"__gate__":lambda:False}])
    if r2.status!=CONSTITUTIVE: fails.append(f"Refusing gate: expected CONSTITUTIVE got {r2.status}")
    if not r2.verify_hash(): fails.append("CONSTITUTIVE hash invalid")
    r3=probe_constitutive("t",None,refusing_inputs=[{"__gate__":lambda:True}])
    if r3.status!=CEREMONIAL: fails.append(f"Always-True: expected CEREMONIAL got {r3.status}")
    if not r3.verify_hash(): fails.append("CEREMONIAL hash invalid")
    ok=not fails
    return ok,("ALT-I-01: UNPROBED/CONSTITUTIVE/CEREMONIAL all content-addressed; CEREMONIAL is located gap." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"constitutive_probe_gate: {'PASS' if ok else 'FAIL'}  {detail}")
