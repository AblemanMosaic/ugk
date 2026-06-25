"""ugk/conformance/csil_topology_gate.py — CSIL-S-02: invariant topology navigator. GATE_GROUP = "structural" """
def run():
    # CSIL-S-02 verifies the explain navigator's output. It calls ugk.cli.main(["explain", ...])
    # IN-PROCESS (capturing stdout) rather than spawning `python -m ugk.cli explain ...`: explain is
    # a pure-static legend/invariant lookup (no kernel, no store), so the spawned-interpreter round
    # trip added cost and cross-process fragility without verifying anything extra. The behavior under
    # test (explain output by invariant ID, CSIL integer, and gate name) is unchanged.
    import io, contextlib
    from ugk.cli import main as _cli_main
    fails = []
    def _explain(arg):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = _cli_main(["explain", arg])
        return rc, buf.getvalue()
    rc, out = _explain("LEGEND-S-01")
    if rc != 0: fails.append("explain LEGEND-S-01 failed")
    elif "Gate:" not in out: fails.append("explain missing Gate: field")
    elif "In-degree:" not in out: fails.append("explain missing In-degree: topology field")
    rc, out = _explain("3003")
    if rc != 0: fails.append("explain 3003 failed")
    elif "crp_evidence" not in out: fails.append("explain 3003 should resolve to crp_evidence")
    rc, out = _explain("6001")
    if rc != 0: fails.append("explain 6001 (CSIL meta) failed")
    elif "CSIL" not in out: fails.append("explain 6001 should mention CSIL")
    rc, out = _explain("legend_hash_gate")
    if rc != 0: fails.append("explain legend_hash_gate failed")
    ok = not fails
    return ok, ("CSIL-S-02: topology navigation by invariant ID, CSIL integer (op+meta), and gate name." if ok else "; ".join(fails))
if __name__ == "__main__":
    ok, detail = run(); print(f"csil_topology_gate: {'PASS' if ok else 'FAIL'}  {detail}")
