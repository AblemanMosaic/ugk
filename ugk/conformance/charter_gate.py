"""ugk/conformance/charter_gate.py — CHARTER-S-01, CHARTER-S-02. GATE_GROUP = "integration" """
def run():
    import json, subprocess, sys, tempfile, os
    from ugk.charter import DeploymentManifest, write_charter_artifacts
    from ugk.kernel import GOVERNOR_PUBKEY_HEX
    fails=[]

    # CHARTER-S-01: content-addressed, derived fields correct
    m=DeploymentManifest.create(GOVERNOR_PUBKEY_HEX,"test-phase","test-juris","trace_only")
    if not m.verify_hash(): fails.append("verify_hash failed")
    if not m.verify_derived_fields(): fails.append("verify_derived_fields failed")
    m2=DeploymentManifest.create(GOVERNOR_PUBKEY_HEX,"other-phase","test-juris","trace_only",timestamp=m.timestamp)
    if m.manifest_hash==m2.manifest_hash: fails.append("Different phase_code same hash")

    # Fail-closed: remove genesis/GENESIS_KEY.pub temporarily and verify sentinel loads
    from ugk._paths import genesis_dir
    pub_path=genesis_dir()/"GENESIS_KEY.pub"
    if pub_path.exists():
        real_key=pub_path.read_text()
        pub_path.unlink()
        try:
            import importlib, ugk.kernel as km
            importlib.reload(km)
            sentinel=km.GOVERNOR_PUBKEY_HEX
            if "UNSET" not in sentinel and "CHARTER" not in sentinel:
                fails.append(f"Without GENESIS_KEY.pub, pubkey not sentinel: {sentinel[:16]!r}")
        finally:
            pub_path.write_text(real_key)
            importlib.reload(km)

    # CHARTER-S-02: charter verb produces artifacts, manifest_hash on session_open
    with tempfile.TemporaryDirectory() as td:
        m3=DeploymentManifest.create(GOVERNOR_PUBKEY_HEX,"charter-gate-test","kernel","trace_only")
        pub_p,mani_p=write_charter_artifacts(m3,genesis_dir=td)
        if not pub_p.exists(): fails.append("GENESIS_KEY.pub not created")
        if not mani_p.exists(): fails.append("DEPLOYMENT_MANIFEST.json not created")
        # Verify content
        stored=json.loads(mani_p.read_text())
        if stored.get("manifest_hash")!=m3.manifest_hash: fails.append("Stored manifest_hash mismatch")
        # Refuse to overwrite without --force
        try:
            write_charter_artifacts(m3,genesis_dir=td,force=False)
            fails.append("Should refuse to overwrite without force=True")
        except FileExistsError:
            pass
        # --force works
        write_charter_artifacts(m3,genesis_dir=td,force=True)

    # manifest_hash in session_open receipt
    from ugk.kernel import GovernanceKernel
    k=GovernanceKernel(); k._ceremony(); k.open_session()
    rs=[r for r in k.store.all_receipts() if r.op=="session_open"]
    if rs:
        params=rs[-1].parameters
        if isinstance(params,str):
            import json; params=json.loads(params or "{}")
        if "manifest_hash" not in (params or {}):
            fails.append("manifest_hash absent from session_open receipt")

    ok=not fails
    return ok,("CHARTER-S-01/02: content-addressed; derived fields verify; fail-closed sentinel; charter produces artifacts; manifest_hash on session_open." if ok else "; ".join(fails))
if __name__=="__main__":
    ok,detail=run(); print(f"charter_gate: {'PASS' if ok else 'FAIL'}  {detail}")
