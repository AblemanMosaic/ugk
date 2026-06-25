"""ugk/conformance/constitution_surface_gate.py — PED-S-01. GATE_GROUP = "structural" """
def run():
    # PED-S-01 verifies the constitution + explain CLI surfaces. Calls ugk.cli.main(...) IN-PROCESS
    # (capturing stdout/stderr) rather than spawning interpreters: these surfaces are read-only/
    # static, so the behavior verified is identical while the per-check interpreter spawn (cost +
    # cross-process fragility) is removed.
    import io, contextlib, json
    from ugk.cli import main as _cli_main
    def _cli(*argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _cli_main(list(argv))
        return rc, out.getvalue(), err.getvalue()
    fails = []
    rc, out, err = _cli("constitution", "--format", "json")
    if rc != 0: return False, f"ugk constitution failed: {err}"
    try:
        d = json.loads(out)
        for field in ["governor_pubkey","mosaic_root","law_hash","legend_hash","invariant_count"]:
            if field not in d: fails.append(f"constitution missing {field!r}")
    except Exception as e: return False, f"JSON parse: {e}"
    rc, out, err = _cli("explain", "LEGEND-S-01")
    if rc != 0: fails.append("ugk explain LEGEND-S-01 failed")
    elif "Gate:" not in out: fails.append("explain output missing Gate: field")
    rc, out, err = _cli("explain", "3003")
    if rc != 0: fails.append("ugk explain 3003 failed")
    elif "crp_evidence" not in out: fails.append("explain 3003 should resolve to crp_evidence")
    from ugk.implementation_codex import load_entries
    concepts = load_entries()
    if not concepts:
        fails.append("IMPLEMENTATION_CODEX concept entries not loadable")
    for concept_id in sorted(concepts):
        rc, out, err = _cli("explain", concept_id)
        if rc != 0:
            fails.append(f"ugk explain {concept_id} failed")
        elif "Boundary:    navigation only" not in out:
            fails.append(f"concept explain {concept_id} should preserve non-law boundary")
    ok = not fails
    return ok, ("PED-S-01: constitution surface complete; explain resolves invariants, CSIL integers, and implementation concept IDs." if ok else "; ".join(fails))
if __name__ == "__main__":
    ok, detail = run(); print(f"constitution_surface_gate: {'PASS' if ok else 'FAIL'}  {detail}")
