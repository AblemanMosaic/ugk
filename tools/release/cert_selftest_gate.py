#!/usr/bin/env python3
"""cert_selftest_gate.py — UGK r114 release-cert orchestrator self-test gate (GRBSA-style tool gate).

Proves that certify_release.py FAILS CLOSED on adversarial inputs and is NOT vacuous (a clean archive
still passes). This is certification TOOLING, not a kernel/conformance invariant: it is run DIRECTLY
(like adapter_atomicity_propagation_gate), is NOT in G6's fixed gate list, and does not move the
conformance gate count (gates stay 98).

Adversarial fixtures (r113 design section 13), each must yield a NON-PASS aggregate:
  1. bad archive            -> corrupt tarball                 -> HOLD(preflight)
  2. missing tool           -> a required gate removed         -> HOLD(preflight)
  3. planted forbidden art. -> a .pyc planted in the archive   -> hygiene FAIL
  4. mismatched resume       -> resume across a changed sha     -> stale verdict refused (no reuse)
  5. simulated failing cmd  -> a gate stubbed to exit 1        -> that check FAIL

Anti-vacuity:
  0. the unmutated base archive -> aggregate PASS (the orchestrator CAN say PASS on good input)

Usage:
  cert_selftest_gate.py --base-archive ugk-v0.1.0-release-rNN.tar.gz [--archives-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_CERTIFY = os.path.join(_HERE, "certify_release.py")


def _extract(archive, dest):
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(archive, "r:gz") as t:
        t.extractall(dest)
    return dest


def _retar(srcdir, out_tar):
    with tarfile.open(out_tar, "w:gz") as t:
        for name in sorted(os.listdir(srcdir)):
            t.add(os.path.join(srcdir, name), arcname=name)
    return out_tar


def _run_certify(archive, workdir, extra=None, archives_dir=None):
    """Run certify_release --phase quick; return (aggregate_verdict, manifest_path)."""
    manifest = os.path.join(workdir, "m_%s.json" % os.path.basename(archive))
    argv = [sys.executable, _CERTIFY, "--archive", archive, "--phase", "quick",
            "--manifest", manifest, "--scratch", tempfile.mkdtemp(prefix="st-", dir=workdir)]
    if archives_dir:
        argv += ["--archives-dir", archives_dir]
    if extra:
        argv += extra
    out = subprocess.run(argv, capture_output=True, text=True)
    m = re.search(r"AGGREGATE:\s+(\w+)", out.stdout)
    verdict = m.group(1) if m else ("HOLD" if "HOLD(preflight)" in out.stdout else "UNKNOWN")
    return verdict, manifest


def _run_certify_raw(archive, workdir, extra):
    """Run certify_release with arbitrary args; return (returncode, stdout, stderr, verdict)."""
    argv = [sys.executable, _CERTIFY, "--archive", archive,
            "--scratch", tempfile.mkdtemp(prefix="stb-", dir=workdir)] + extra
    out = subprocess.run(argv, capture_output=True, text=True)
    m = re.search(r"AGGREGATE[^:]*:\s+(\w+)", out.stdout)
    verdict = m.group(1) if m else None
    return out.returncode, out.stdout, out.stderr, verdict


def _derive_frame(base, work):
    """Derive the candidate archive's expected frame (law/schema/legend/codex + counts + latest ADR)
    from the extracted archive, so the bundle-phase self-tests are self-contained."""
    ex = _extract(base, os.path.join(work, "frame_ex"))
    code = (
        "import sys;sys.dont_write_bytecode=True;"
        "from ugk.conformance.amendment_admissibility_gate import _live_frame;"
        "from ugk.invariants import INVARIANT_REGISTRY as R;"
        "from ugk.adr import ADR_REGISTRY as A;"
        "f=_live_frame();"
        "c=open('ugk/codex/CODEX_HASH.txt').read().split('=')[-1].strip();"
        "ad=sorted(A, key=lambda k:int(k.split('-')[-1]))[-1];"
        "print(f['law_hash'],f['schema_hash'],f['legend_hash'],c,len(A),len(R),ad)")
    env = dict(os.environ, PYTHONPATH=ex, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-c", code], cwd=ex, capture_output=True, text=True, env=env)
    law, schema, legend, codex, adr, reg, adr_id = out.stdout.split()
    return ["--expected-law", law, "--expected-schema", schema, "--expected-legend", legend,
            "--expected-codex", codex, "--expected-adr-count", adr,
            "--expected-registry-count", reg, "--expected-adr", adr_id]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-archive", required=True)
    ap.add_argument("--archives-dir", default=None)
    args = ap.parse_args(argv)

    base = os.path.abspath(args.base_archive)
    if not os.path.exists(base):
        print("CERT SELF-TEST GATE: FAIL (base archive missing: %s)" % base)
        return 1
    archives_dir = args.archives_dir or os.path.dirname(base)

    work = tempfile.mkdtemp(prefix="cert-selftest-")
    results = []  # (case, verdict, expected_predicate, ok)

    # ---- 0. anti-vacuity: clean base must PASS ----
    v, _ = _run_certify(base, work, archives_dir=archives_dir)
    results.append(("0-clean-base", v, "PASS", v == "PASS"))

    # ---- 1. bad archive (corrupt tarball) ----
    corrupt = os.path.join(work, "corrupt.tar.gz")
    with open(corrupt, "wb") as f:
        f.write(b"this is not a gzip tarball \x00\x01\x02" * 64)
    v, _ = _run_certify(corrupt, work, archives_dir=archives_dir)
    results.append(("1-bad-archive", v, "non-PASS", v != "PASS"))

    # ---- 2. missing tool (remove a required gate) ----
    ex2 = _extract(base, os.path.join(work, "ex2"))
    tgt = os.path.join(ex2, "tools", "b4a_conformance.py")
    if os.path.exists(tgt):
        os.remove(tgt)
    mt = _retar(ex2, os.path.join(work, "missing_tool.tar.gz"))
    v, _ = _run_certify(mt, work, archives_dir=archives_dir)
    results.append(("2-missing-tool", v, "non-PASS", v != "PASS"))

    # ---- 3. planted forbidden artifact (.pyc) ----
    ex3 = _extract(base, os.path.join(work, "ex3"))
    with open(os.path.join(ex3, "ugk", "planted_artifact.pyc"), "wb") as f:
        f.write(b"\x00planted bytecode\x00")
    pf = _retar(ex3, os.path.join(work, "planted.tar.gz"))
    v, _ = _run_certify(pf, work, archives_dir=archives_dir)
    results.append(("3-planted-pyc", v, "non-PASS (hygiene)", v != "PASS"))

    # ---- 5. simulated failing command (stub a gate to exit 1) ----
    ex5 = _extract(base, os.path.join(work, "ex5"))
    with open(os.path.join(ex5, "tools", "b4a_conformance.py"), "w") as f:
        f.write("import sys\nprint('STUB: forced failure')\nsys.exit(1)\n")
    fc = _retar(ex5, os.path.join(work, "failing_cmd.tar.gz"))
    v, _ = _run_certify(fc, work, archives_dir=archives_dir)
    results.append(("5-failing-command", v, "FAIL", v == "FAIL"))

    # ---- 4. mismatched resume fingerprint ----
    # produce a clean manifest on base, then resume it against a DIFFERENT archive (planted, different sha).
    base_v, base_manifest = _run_certify(base, work, archives_dir=archives_dir)
    rv, resume_manifest = _run_certify(pf, work, extra=["--resume", base_manifest], archives_dir=archives_dir)
    resumed_any = False
    try:
        mm = json.load(open(resume_manifest))
        resumed_any = any(c.get("resumed") for c in mm.get("checks", []))
    except Exception:
        resumed_any = False
    # correct behavior: the changed archive sha invalidates the resume binding -> NO checks reused.
    results.append(("4-resume-mismatch", "reused=%s" % resumed_any, "no-reuse", (not resumed_any)))

    # ---- r150 erratum self-tests (release-tooling defects) ----
    frame = _derive_frame(base, work)

    # 6. DEFECT 1: --phase bundle WITHOUT --expected-codex must fail closed CLEARLY (no NameError)
    rc6, so6, se6, _ = _run_certify_raw(base, work, ["--phase", "bundle", "--archives-dir", archives_dir])
    blob6 = so6 + se6
    ok6 = (rc6 != 0) and ("NameError" not in blob6) and ("expected-codex" in blob6.lower())
    results.append(("6-missing-codex-clear", "rc=%s" % rc6, "clear-fail-no-NameError", ok6))

    # 7. DEFECT 2 + explicit-codex + normal evidence path: --emit-bundle INSIDE --evidence-dir (same file)
    ev7 = tempfile.mkdtemp(prefix="ev7-", dir=work)
    emit7 = os.path.join(ev7, "release-cert-bundle.json")
    rc7, so7, se7, v7 = _run_certify_raw(base, work,
        ["--phase", "bundle", "--archives-dir", archives_dir,
         "--emit-bundle", emit7, "--evidence-dir", ev7] + frame)
    ok7 = (rc7 == 0) and (v7 == "PASS") and ("SameFileError" not in (so7 + se7)) and os.path.exists(emit7)
    results.append(("7-samefile-emit-bundle", "rc=%s v=%s" % (rc7, v7), "PASS-no-SameFileError", ok7))

    # 8. normal evidence-dir copy: --emit-bundle OUTSIDE --evidence-dir -> bundle copied in
    ev8 = tempfile.mkdtemp(prefix="ev8-", dir=work)
    emit8 = os.path.join(work, "outside-bundle.json")
    rc8, so8, se8, v8 = _run_certify_raw(base, work,
        ["--phase", "bundle", "--archives-dir", archives_dir,
         "--emit-bundle", emit8, "--evidence-dir", ev8] + frame)
    copied8 = os.path.exists(os.path.join(ev8, os.path.basename(emit8)))
    ok8 = (rc8 == 0) and (v8 == "PASS") and copied8
    results.append(("8-normal-evidence-copy", "rc=%s v=%s copied=%s" % (rc8, v8, copied8), "PASS-and-copied", ok8))

    # 9. DEFECT (run_conformance hang): run_conformance() must return PASS CLEANLY and PROMPTLY when
    #    verify_release.sh prints "=== verify_release PASS ===", even if the run leaves a process that
    #    never exits after the sentinel (a lingering grandchild). Regression for the orchestrated-
    #    conformance hang: the marker path reaps the group and returns at once instead of stalling on
    #    a process tree that never exits.
    import time as _time
    import importlib
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    certmod = importlib.import_module("certify_release")
    rc_ex = os.path.join(work, "rc_ex"); os.makedirs(rc_ex, exist_ok=True)
    with open(os.path.join(rc_ex, "verify_release.sh"), "w") as f:
        f.write("#!/usr/bin/env bash\n"
                "echo '  ... gates ... 110/110 ALL PASS'\n"
                "echo '=== verify_release PASS ==='\n"
                "exec sleep 600   # process never exits AFTER the sentinel: pre-fix code stalls on p.wait\n")
    os.chmod(os.path.join(rc_ex, "verify_release.sh"), 0o755)
    rc_log = os.path.join(work, "rc_logdir"); os.makedirs(rc_log, exist_ok=True)
    _saved = certmod.BUDGET["verify_release"]
    certmod.BUDGET["verify_release"] = 8   # cap so a REGRESSION fails fast (~8s) instead of hanging
    try:
        _t0 = _time.monotonic()
        verdict9, _code9 = certmod.run_conformance(rc_ex, rc_log)
        dt9 = _time.monotonic() - _t0
    finally:
        certmod.BUDGET["verify_release"] = _saved
    ok9 = (verdict9 == "PASS") and (dt9 < 5.0)   # marker path returns ~instantly; a hang would be ~8s/FAIL
    results.append(("9-run_conformance-clean", "v=%s t=%.1fs" % (verdict9, dt9), "PASS-and-prompt", ok9))

    print("=" * 70)
    print("  CERT ORCHESTRATOR SELF-TEST (fail-closed + anti-vacuity)")
    print("-" * 70)
    all_ok = True
    for case, verdict, expected, ok in results:
        all_ok = all_ok and ok
        print("  %-20s got=%-14s expect=%-18s %s" % (case, verdict, expected, "OK" if ok else "*FAIL*"))
    print("-" * 70)
    # anti-vacuity is explicit: case 0 must PASS AND at least the failing-command case must FAIL,
    # proving the gate distinguishes good from broken (not trivially failing everything).
    vacuity_ok = results[0][3] and any(c[0] == "5-failing-command" and c[3] for c in results)
    print("  anti-vacuity (clean PASS + broken FAIL distinguished): %s" % ("OK" if vacuity_ok else "*FAIL*"))
    verdict = "PASS" if (all_ok and vacuity_ok) else "FAIL"
    print("=" * 70)
    print("  CERT SELF-TEST GATE: %s" % verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
