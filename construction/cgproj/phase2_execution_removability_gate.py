#!/usr/bin/env python3
"""Phase 2 — Execution Removability / Non-Authority Gate (CGProj), r11.

Proves the projection jurisdiction is non-authoritative AND removable. Three checks,
all must pass (behavioral is authoritative; static corroborates; removability is strongest):

  CHECK A (static):       no execution-jurisdiction module imports ugk.projections via a DIRECT
                          import or a DYNAMIC-import pattern (importlib / __import__ / 'projections'
                          string near an import call). This is a direct + dynamic-pattern source
                          scan, NOT a built transitive import graph; transitive edges are caught
                          instead by Check B (behavioral: nothing in the surface can load while
                          projections are barred) and Check C (deletion).
  CHECK B (behavioral):   with ugk.projections made UNIMPORTABLE (meta_path barrier), the FULL
                          execution surface (78 gates + 39 vectors + A1 conservativity + scale AL)
                          passes IDENTICALLY to baseline. The barrier is PROVEN active in the same
                          processes that ran the suite (sentinel) with positive+negative controls.
  CHECK C (removability): with ugk/projections/ physically DELETED, the execution jurisdiction
                          passes fully and identically. (Asymmetry per roadmap: execution must
                          survive deletion; projection-generation may fail — but no renderer
                          exists yet, so there is nothing of that kind to fail.)

Run from repo root:  python phase2_gate.py <repo_dir>
Exit 0 = gate PASS; nonzero = STOP (CGProj does not enter v0.1.0).
"""
import sys, os, subprocess, tempfile, shutil, ast, re, time

PY = sys.executable
REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

# Consume the SINGLE authoritative execution-jurisdiction definition shared with the Phase 4.5
# gate, so the boundary cannot drift between gates. (Script dir is on sys.path for this import.)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import execution_jurisdiction as EJ

# Full execution surface the roadmap names for the behavioral/removability checks.
# Roadmap 7.1: "78 gates + 39 vectors + A1 + rho + scale conformance + scale AL".
SURFACE = [
    ("78 gates", "ugk.conformance.run_gates_batch"),
    ("39 vectors", "ugk.conformance.m2_vectors_runner"),
    ("A1 conservativity", "ugk.conformance.a1_conservativity_gate"),
    ("rho fixtures", "ugk.conformance.rho_fixtures"),     # R1-R5 + adversarial; rho is dormant-by-default
    ("scale conformance", "ugk.scale.conformance"),       # 7/7
    ("scale AL", "ugk.scale.al_conformance"),             # 22/22 (AL CLEAN)
]


def _summary(out):
    """Extract a deterministic pass summary or verdict from runner output.

    Prefer the AUTHORITATIVE final summary/verdict, not the first incidental "N/N"
    (e.g. a 'violations=0/200' progress line must NOT be mistaken for the run summary).

    NOTE ON RECEIPT HASHES: these runner entry points emit deterministic PASS/FAIL
    summaries to stdout but do NOT expose per-run receipt/chain hashes for capture.
    This gate therefore compares deterministic runner OUTPUTS across baseline / barred /
    deleted conditions. It does NOT prove receipt-hash identity (see report). Capturing
    true receipt hashes would require instrumenting the runners — an execution-surface
    code change that is out of scope for Phase 2.
    """
    # 0) batch-style posture: "N/M passed | F failed | K not-established | ALL PASS" passes iff 0 failed
    #    and a PASS verdict (a not-established posture warning, e.g. grundnorm_readonly_gate pre-harden,
    #    is tolerated — see verify_release semantics; this is NOT a hardened-posture assertion).
    _mf = re.search(r"(\d+)\s+failed", out)
    if _mf and int(_mf.group(1)) == 0 and re.search(r"ALL PASS|PASS \(\d+ not-established\)", out):
        _mp = re.search(r"(\d+)/(\d+)\s+passed", out)
        return ((_mp.group(0) if _mp else "PASS") + " (0 failed; posture-tolerant)"), True
    # 1) explicit terminal verdicts first
    if "AL CLEAN" in out:
        return "AL CLEAN", True
    if re.search(r"VERDICT:\s*ALL PASS", out) or re.search(r"VERDICT:\s*PASS", out):
        return "VERDICT PASS", True
    # 2) an "X/Y passed" or "X/Y pass" summary, taking the LAST such match (the summary line,
    #    not an earlier incidental ratio like violations=0/200)
    summ = re.findall(r"(\d+)/(\d+)\s+(?:passed|pass|checks|gates)\b", out)
    if summ:
        a, b = summ[-1]
        return (a + "/" + b), (a == b)
    # 3) bare "ALL PASS"
    if re.search(r"\bALL PASS\b", out):
        return "ALL PASS", True
    # 4) last-resort bare ratio (only if nothing better) — still take the last
    bare = re.findall(r"(\d+)/(\d+)", out)
    if bare:
        a, b = bare[-1]
        return (a + "/" + b + " (bare)"), (a == b)
    return "NO-MATCH", False


def run_surface(env, cwd, barrier_prefixes=None, sentinel=None):
    """Run the full execution surface; return ({label: summary}, all_ok).

    If barrier_prefixes is set, each surface module runs under a SAME-PROCESS meta_path barrier
    (via runpy), with the barrier proven active by `sentinel` (no sitecustomize ordering dependence).
    """
    results, ok = {}, True
    mode = "barrier" if barrier_prefixes is not None else "direct"
    for label, mod in SURFACE:
        e = {**os.environ, **env}
        e["UGK_GENESIS_DIR"] = tempfile.mkdtemp()
        e["PYTHONPATH"] = env.get("PYTHONPATH", cwd)
        e["PYTHONUTF8"] = "1"
        e["PYTHONIOENCODING"] = "utf-8:backslashreplace"
        print("      [%s] %-12s running %-32s ..." % (mode, label, mod), flush=True)
        t0 = time.time()
        if barrier_prefixes is not None:
            p = EJ.run_module_under_barrier(PY, mod, barrier_prefixes, sentinel, cwd,
                                            env=e, cwd=cwd, timeout=120)
        else:
            p = EJ.bounded_run([PY, "-m", mod], cwd=cwd, env=e, timeout=120)
        summ, good = _summary(p.stdout + p.stderr)
        dt = time.time() - t0
        print("      [%s] %-12s %-10s %s (%.1fs, exit=%s)" %
              (mode, label, summ, "OK" if good else "NOT-CLEAN", dt, p.returncode), flush=True)
        results[label] = summ
        ok = ok and good
    return results, ok


def check_A_static():
    """No execution module (named set + all conformance gates) imports ugk.projections."""
    scan = EJ.static_scan_files(REPO)   # shared authoritative execution-jurisdiction file set
    violations = []
    scanned = 0
    for path in scan:
        rel = os.path.relpath(path, REPO)
        scanned += 1
        src = open(path, encoding="utf-8").read()
        try:
            tree = ast.parse(src)
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module and "projections" in n.module and "ugk" in n.module:
                    violations.append(rel + ": from " + n.module + " import ...")
                if isinstance(n, ast.Import):
                    for a in n.names:
                        if "ugk.projections" in a.name:
                            violations.append(rel + ": import " + a.name)
        except SyntaxError as e:
            violations.append(rel + ": parse error " + str(e))
        for kw in ("import_module", "__import__", "importlib"):
            if kw in src and "projections" in src:
                violations.append(rel + ": possible dynamic import (" + kw + " + 'projections')")
                break
    return violations, scanned


def main():
    print("=== Phase 2: Execution Removability / Non-Authority Gate (r11) ===")
    print("repo: " + REPO + "\n")

    # baseline (projections present, importable)
    print("--- baseline (projections present, importable):")
    base, bok = run_surface({}, REPO)
    print("    " + str(base) + " all_ok=" + str(bok))

    # CHECK A — static isolation (direct + dynamic-pattern scan; must prove it scanned)
    print("--- CHECK A: static import isolation (direct + dynamic-pattern scan):")
    viol, scanned = check_A_static()
    a_ok = (not viol) and scanned > 0
    print("    scanned " + str(scanned) + " execution-surface files")
    print("    " + ("PASS — no execution module imports ugk.projections"
                    if a_ok else "FAIL — " + str(viol)))

    # CHECK B — behavioral isolation via SAME-PROCESS meta_path barrier proven active by sentinel
    # (No sitecustomize ordering dependence: each surface module runs under a prelude that installs
    #  the barrier and writes the sentinel before the module runs, via runpy.)
    print("--- CHECK B: behavioral isolation (ugk.projections made UNIMPORTABLE):")
    PROJ_PREFIXES = ("ugk.projections",)
    sentinel = os.path.join(tempfile.mkdtemp(), "BAR_LOADED")
    b_res, b_suite_ok = run_surface({}, REPO, barrier_prefixes=PROJ_PREFIXES, sentinel=sentinel)
    # PROOF 1: barrier prelude actually ran in the suite-run subprocesses
    sentinel_written = os.path.exists(sentinel)
    # PROOF 2: positive control — under the SAME prelude, importing projections is barred
    pos = EJ.run_code_under_barrier(PY, "import ugk.projections\n", PROJ_PREFIXES,
                                    os.path.join(tempfile.mkdtemp(), "S"), REPO, env={**os.environ}, cwd=REPO)
    bar_raises = pos.returncode != 0 and "barred jurisdiction module" in (pos.stderr + pos.stdout)
    # PROOF 3: negative control — WITHOUT the barrier, import succeeds (the bar is the cause)
    neg = subprocess.run([PY, "-c", "import sys; sys.path.insert(0, %r); import ugk.projections; print('imported')" % REPO],
                         cwd=REPO, env={**os.environ}, capture_output=True, text=True)
    bar_is_cause = "imported" in neg.stdout
    barred = sentinel_written and bar_raises and bar_is_cause
    print("    barrier ran in suite processes (sentinel): " + str(sentinel_written))
    print("    positive control — import barred under prelude: " + str(bar_raises))
    print("    negative control — import succeeds WITHOUT bar: " + str(bar_is_cause))
    print("    bar provably active (all three): " + str(barred))
    print("    surface under barrier: " + str(b_res) + " all_ok=" + str(b_suite_ok))
    behavioral_match = (b_res == base and b_suite_ok)
    behavioral_ok = barred and behavioral_match
    print("    " + ("PASS — execution identical WHILE projections provably unimportable"
                    if behavioral_ok else
                    "FAIL — " + ("barrier not proven active" if not barred else "execution changed")))

    # CHECK C — removability (projections physically deleted in a copy)
    print("--- CHECK C: removability (ugk/projections/ physically DELETED):")
    tmp = tempfile.mkdtemp()
    dst = os.path.join(tmp, "repo")
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
    proj = os.path.join(dst, "ugk", "projections")
    shutil.rmtree(proj)
    deleted = not os.path.exists(proj)
    c_res, c_ok = run_surface({}, dst)
    print("    projections dir deleted: " + str(deleted))
    print("    surface with projections deleted: " + str(c_res) + " all_ok=" + str(c_ok))
    removability_match = deleted and (c_res == base) and c_ok
    print("    " + ("PASS — execution jurisdiction passes fully with projections deleted"
                    if removability_match else "FAIL — execution depends on projections"))

    # verdict
    print("\n=== VERDICT ===")
    overall = bok and a_ok and behavioral_ok and removability_match
    print("  baseline surface green:  " + str(bok))
    print("  A static isolation:      " + ("PASS" if a_ok else "FAIL"))
    print("  B behavioral isolation:  " + ("PASS" if behavioral_ok else "FAIL") + " (barrier active: " + str(barred) + ")")
    print("  C removability:          " + ("PASS" if removability_match else "FAIL"))
    print("  GATE: " + ("PASS" if overall else "FAIL — STOP, CGProj does not enter v0.1.0"))
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
