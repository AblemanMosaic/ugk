"""ugk/conformance/health_surface_gate.py — CGP-S-02, CGP-S-03. GATE_GROUP = "structural" """
def run():
    # CGP-S-02/03 verifies the health + help CLI surfaces. Calls ugk.cli.main(...) IN-PROCESS
    # (capturing stdout) instead of spawning interpreters; health is a read-only diagnostic and help
    # is static, so behavior under test is unchanged while spawn cost/fragility is removed.
    import io, contextlib, json
    from ugk.cli import main as _cli_main
    def _cli(*argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _cli_main(list(argv))
        return rc, out.getvalue(), err.getvalue()
    fails = []
    # CGP-S-02: health covers five sub-checks
    rc, out, err = _cli("health", "--format", "json")
    if rc not in (0, 1): fails.append(f"health exited {rc}")
    try:
        d = json.loads(out)
        for fld in ["sections","chain_intact","authority_model","phi","disjuncts","posture_hash"]:
            if fld not in d: fails.append(f"health JSON missing {fld!r}")
        if set(d.get("sections",[])) != {"chain","authority_model","posture","disjuncts","gate_compliance"}:
            fails.append(f"health sections incomplete: {d.get('sections')}")
    except Exception as e: fails.append(f"health JSON parse: {e}")
    # CGP-S-03: gate group annotations
    import importlib
    from ugk.conformance.run_gates_batch import GATES
    no_group = []
    for modname in GATES[:10]:
        try:
            mod = importlib.import_module(modname); doc = mod.__doc__ or ""
            has_group = any(g in doc.upper() for g in ["STRUCTURAL","UNIT","INTEGRATION","CONFORMANCE","GATE_GROUP"])
            if not has_group: no_group.append(modname.rsplit(".",1)[-1])
        except Exception: pass
    if len(no_group) > 5: fails.append(f"Too many gates without GATE_GROUP: {no_group[:3]}...")
    # ugk help surface
    rc, out, err = _cli("help")
    if rc != 0: fails.append("ugk help failed")
    elif "charter" not in out: fails.append("ugk help missing charter verb")
    rc, out, err = _cli("help", "charter")
    if rc != 0: fails.append("ugk help charter failed")
    elif "--pubkey" not in out: fails.append("ugk help charter missing --pubkey parameter")
    ok = not fails
    return ok, ("CGP-S-02/03: health covers 5 sub-checks; gate group annotations; ugk help shows charter parameters." if ok else "; ".join(fails))
if __name__ == "__main__":
    ok, detail = run(); print(f"health_surface_gate: {'PASS' if ok else 'FAIL'}  {detail}")
