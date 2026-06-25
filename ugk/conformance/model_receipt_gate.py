"""ugk/conformance/model_receipt_gate.py — CM-S-04. GATE_GROUP = "integration" """
def run():
    import json
    from ugk.authority.authority_model import AuthorityModel
    from ugk.kernel import GovernanceKernel
    fails=[]
    k=GovernanceKernel(); k._ceremony()
    model=AuthorityModel.alt_trace(k._law_hash,k._mosaic_root)
    k.set_authority_model(model); k.open_session()
    rs=[r for r in k.store.all_receipts() if r.op=="session_open"]
    if not rs: return False,"No session_open receipt"
    params=rs[-1].parameters
    if isinstance(params,str): params=json.loads(params or "{}")
    if "authority_model_hash" not in (params or {}): fails.append("authority_model_hash absent from session_open")
    elif params["authority_model_hash"]!=model.model_hash: fails.append("model_hash mismatch on receipt")
    stored=k._store.get_authority_model(model.model_hash)
    if stored is None: fails.append("Not in authority_model_archive")
    elif not stored.verify_hash(): fails.append("Stored model hash invalid")
    if not k.store.verify_stream_hash(): fails.append("Chain broken")
    ok=not fails
    return ok,("CM-S-04: model_hash on session_open receipt; stored in archive; chain intact." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"model_receipt_gate: {'PASS' if ok else 'FAIL'}  {detail}")
