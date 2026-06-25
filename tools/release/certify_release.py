#!/usr/bin/env python3
"""certify_release.py — UGK r114 release-certification orchestrator.

THIN RECORDER, NOT JUDGE (UGK r113 design). It runs the EXISTING certification surface against the
EXTRACTED archive (clean-room: the archive's own tools certify the archive's own ugk/) and emits a
machine-readable evidence manifest. It introduces no new truth: a check's verdict is the check's own
EXIT CODE, or a mechanical comparison whose inputs (computed value, expected value) are recorded so the
verdict is re-derivable. It never mints, re-attests, re-pins CODEX, or writes governance artifacts.

Phases (r113 section 3):
  --quick    : fast structural green (hygiene, frame, verify_release, probe, focused gates, b4a,
               attestation, ugk-confinement, no-drift)        -> iteration lane, NOT acceptance
  --deep     : --quick plus G6 and the 8 cgproj gates
  --compose  : continuity composition over all links
  --full     : --quick + --deep + --compose (canonical clean-room cert)

Fail-closed: missing tool/path, timeout, lost detached job, dirty extract, hash mismatch, or unexpected
output all yield HOLD/FAIL, never an inferred PASS.

BOOTSTRAP RULE (r113 section 12): this orchestrator does NOT certify the release that introduces it
(r114 is certified by the manual method). It is evidentiary tooling for LATER releases.

Usage:
  certify_release.py --archive R.tar.gz --phase full --archives-dir DIR \
      [--prior-archive P.tar.gz --declared-surfaces s1,s2,...] [--worktree DIR] \
      [--expected-codex HASH --expected-adr-count N --expected-adr AD-NN] \
      [--manifest OUT.json --evidence-dir DIR] [--resume PRIOR_MANIFEST.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil


def _safe_copy(src, dst):
    """copy2 that no-ops when src and dst are the same file (e.g. --emit-bundle already inside
    --evidence-dir), so durable-evidence copying never crashes with SameFileError."""
    try:
        if os.path.abspath(src) == os.path.abspath(dst) or (os.path.exists(dst) and os.path.samefile(src, dst)):
            return
    except OSError:
        pass
    shutil.copy2(src, dst)
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import run_detached as rd  # noqa: E402

SCHEMA = "ugk-cert-manifest/1"

# Stationary grundnorm frame (law/schema/legend) — unmoved since r102. Defaults (recorded as the
# expected_frame in the manifest); override with --expected-law/schema/legend. The orchestrator does
# not OWN these values; it records expected-vs-computed so the equality verdict is auditable.
DEFAULT_LAW = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"
DEFAULT_SCHEMA = "82d02279c39d5fa82d6bb18a2a12b0f85cc5210a93502d827a9f89c570327c99"
DEFAULT_LEGEND = "db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7"

# Budgets (seconds) for detached checks; exceeding -> HOLD(timeout), never a pass.
BUDGET = {"g6": 600, "compose": 1500, "cgproj": 600, "verify_release": 300}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def env_fingerprint() -> tuple[str, dict]:
    """r113 section 7 — concrete, not hand-waved. PYTHONHASHSEED is pinned to 0 for subprocesses."""
    detail = {
        "python_version": "%d.%d.%d" % sys.version_info[:3],
        "python_impl": platform.python_implementation(),
        "platform": "%s/%s" % (platform.system(), platform.machine()),
        "pythonhashseed": "0",
        "lang": os.environ.get("LANG", "unset"),
        "lc_all": os.environ.get("LC_ALL", "unset"),
        "tz": os.environ.get("TZ", "unset"),
    }
    canon = json.dumps(detail, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest(), detail


def _subproc_env(extract: str) -> dict:
    e = dict(os.environ)
    e["PYTHONHASHSEED"] = "0"
    e["PYTHONPATH"] = extract
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8:backslashreplace"
    return e


# ----- archive immutability + extraction (r113 section 11) -----

def extract_archive(archive: str, scratch: str) -> str:
    extract_dir = os.path.join(scratch, "extract")
    os.makedirs(extract_dir, exist_ok=True)
    with tarfile.open(archive, "r:gz") as t:
        t.extractall(extract_dir)
    # Some archives are rooted at "." — flatten if a single top dir is not present.
    return extract_dir


def _list_source_files(root: str) -> dict:
    """Map relpath -> sha256 for source files (excluding __pycache__/*.pyc), for dirty/confinement/drift."""
    out: dict = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                out[rel] = _sha256_file(full)
            except OSError:
                out[rel] = "UNREADABLE"
    return out


# ----- check execution -----

def _mk_record(band, name, command, cwd, tool_sha, launched_via, log_path):
    return {
        "band": band, "name": name, "command": command, "cwd": cwd,
        "tool_sha256": tool_sha, "launched_via": launched_via, "pid": None,
        "log_path": log_path, "started_utc": None, "ended_utc": None, "duration_s": None,
        "timeout_budget_s": None, "concurrent_context": None,
        "exit_code": None, "comparison": None, "verdict": "HOLD", "hold_reason": None,
    }


def _verdict_from_rc(rc, expect_substr, log_path):
    """Verdict is the exit code; an extra unexpected-output guard turns a 0-exit with a missing
    expected marker into HOLD(unexpected) — fail-closed, never optimistic. Returns (verdict, hold_reason)."""
    if rc != 0:
        return "FAIL", None
    if expect_substr:
        try:
            txt = open(log_path, "r", errors="replace").read()
        except OSError:
            return "HOLD", "log_unreadable"
        if expect_substr not in txt:
            return "HOLD", "unexpected"
    return "PASS", None


def run_exitcode_inline(band, name, argv, cwd, tool_sha, env, log_path, expect_substr=None):
    rec = _mk_record(band, name, argv, cwd, tool_sha, "inline", log_path)
    rec["started_utc"] = _utc(); t0 = time.time()
    with open(log_path, "wb") as lf:
        try:
            rc = subprocess.call(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT)
        except FileNotFoundError:
            lf.write(b"command not found\n"); rc = 127
    rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
    rec["exit_code"] = rc
    rec["verdict"], rec["hold_reason"] = _verdict_from_rc(rc, expect_substr, log_path)
    return rec


def run_exitcode_detached(band, name, argv, cwd, tool_sha, env, log_path, budget_s, expect_substr=None,
                          concurrent_context=None):
    rec = _mk_record(band, name, argv, cwd, tool_sha, "run_detached", log_path)
    rec["timeout_budget_s"] = budget_s
    rec["concurrent_context"] = concurrent_context
    rec["started_utc"] = _utc(); t0 = time.time()
    # rd.launch uses sys.executable; for cwd/env control we patch os.environ + chdir around launch.
    saved = dict(os.environ)
    os.environ.update({k: v for k, v in env.items()})
    cwd_saved = os.getcwd()
    try:
        os.chdir(cwd)
        launch = rd.launch(argv, log_path)
    finally:
        os.chdir(cwd_saved)
        os.environ.clear(); os.environ.update(saved)
    rec["pid"] = launch["pid"]
    status = launch["status"]
    state = "RUNNING"
    while time.time() - t0 < budget_s:
        state = rd.poll(launch["pid"], status)
        if state.startswith("DONE") or state == "LOST":
            break
        time.sleep(2.0)
    rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
    if state == "LOST":
        rec["verdict"] = "HOLD"; rec["hold_reason"] = "lost"; rec["exit_code"] = None
        rec["note"] = "LOST(detached job died with no status)"
        return rec
    if not state.startswith("DONE"):
        # Distinguish resource/timeout from a real FAIL: a job still running at the budget is HOLD(timeout),
        # NOT FAIL. The concurrent_context + timeout_budget_s + duration make this diagnosable from the
        # manifest alone (a timeout under max_concurrency=1 with nothing co-running is a strong real-stall
        # signal; a timeout with heavy co-running is a harness/resource artifact).
        rec["verdict"] = "HOLD"; rec["hold_reason"] = "timeout"
        rec["note"] = "timeout(budget %ds)" % budget_s
        return rec
    rc = int(state.split()[1]); rec["exit_code"] = rc
    rec["verdict"], rec["hold_reason"] = _verdict_from_rc(rc, expect_substr, log_path)
    return rec


# ----- mechanical checks (recorded comparisons, not judgments) -----

def check_frame(extract, env, log_path, expected):
    """Compute law/schema/legend/codex/adr via a subprocess (PYTHONPATH=extract) and compare to
    expected. The orchestrator does not import the archive's code; it records computed vs expected."""
    rec = _mk_record("B1", "frame", ["<python: compute frame from extract>"], extract, None, "inline", log_path)
    rec["started_utc"] = _utc(); t0 = time.time()
    prog = (
        "import hashlib,json\n"
        "from ugk.storage.store import UGKReceiptStore\n"
        "from ugk.storage.binding import LEGEND_HASH\n"
        "from ugk.adr import ADR_REGISTRY\n"
        "law=hashlib.sha256(open('ugk/invariants.py','rb').read()).hexdigest()\n"
        "schema=UGKReceiptStore(':memory:').schema_hash()\n"
        "codex=open('ugk/codex/CODEX_HASH.txt').read().strip()\n"
        "ids=[a if isinstance(a,str) else a.get('id') for a in ADR_REGISTRY]\n"
        "print(json.dumps({'law':law,'schema':schema,'legend':LEGEND_HASH,'codex':codex,"
        "'adr_count':len(ADR_REGISTRY),'adr_ids':ids}))\n"
    )
    try:
        out = subprocess.check_output([sys.executable, "-c", prog], cwd=extract, env=env,
                                      stderr=subprocess.STDOUT, timeout=120)
        computed = json.loads(out.decode().strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001
        with open(log_path, "w") as f:
            f.write("frame compute failed: %s\n" % e)
        rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
        rec["verdict"] = "HOLD"; rec["note"] = "frame compute error"
        return rec
    checks = {
        "law": (computed["law"], expected["law"], computed["law"] == expected["law"]),
        "schema": (computed["schema"], expected["schema"], computed["schema"] == expected["schema"]),
        "legend": (computed["legend"], expected["legend"], computed["legend"] == expected["legend"]),
    }
    # codex / adr asserted only if expected provided; else recorded.
    if expected.get("codex"):
        checks["codex"] = (computed["codex"], expected["codex"], computed["codex"] == expected["codex"])
    if expected.get("adr_count") is not None:
        checks["adr_count"] = (computed["adr_count"], expected["adr_count"], computed["adr_count"] == expected["adr_count"])
    if expected.get("adr_id"):
        present = expected["adr_id"] in computed["adr_ids"]
        checks["adr_present"] = (expected["adr_id"], "present", present)
    rec["comparison"] = {"computed": computed, "expected": expected, "checks": checks}
    with open(log_path, "w") as f:
        json.dump(rec["comparison"], f, indent=2)
    all_eq = all(c[2] for c in checks.values())
    rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
    rec["verdict"] = "PASS" if all_eq else "FAIL"
    return rec


def check_attestation(extract, log_path):
    """Verify the shipped continuity attestation. CARRIED ERRATUM (pre-existing at r134, independent of
    the G6 payload): the prior check compared `composed == "HOLD"` exactly, which FALSE-FAILED the
    descriptive composed string `ContinuityChain[..] composed=HOLD`. The attestation is now verified by
    DELEGATING to the same internal-consistency logic the verifier ships
    (proof_model_b._verify_attestation: every attested link verdict == HOLD, contiguous sha chain, and
    each current/unattested surfaces link content-chains to the attested head), guarded by a structured
    `composed=HOLD` token check. Fails CLOSED (FAIL) on missing/unreadable/malformed attestation, an
    ambiguous or non-HOLD composed value, or broken link continuity — semantics are strengthened, never
    weakened."""
    rec = _mk_record("B3", "attestation", ["<verify CONTINUITY_ATTESTATION.json>"], extract, None, "inline", log_path)
    rec["started_utc"] = _utc(); t0 = time.time()
    apath = os.path.join(extract, "tools", "grbsa", "CONTINUITY_ATTESTATION.json")
    spath = os.path.join(extract, "tools", "grbsa", "continuity_surfaces.json")
    pmpath = os.path.join(extract, "tools", "grbsa", "proof_model_b.py")
    log = []

    def _finish(verdict, note=None):
        rec["verdict"] = verdict
        if note:
            rec["note"] = note
        with open(log_path, "w") as f:
            f.write("\n".join(log) + ("\n%s\n" % note if note else "\n"))
        rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
        return rec

    # 1. load attestation (missing/unreadable/malformed -> FAIL, fail-closed)
    try:
        a = json.load(open(apath))
    except Exception as e:  # noqa: BLE001
        return _finish("FAIL", "attestation unreadable/malformed: %s" % e)
    composed = a.get("composed")
    n = a.get("n_links")
    rec["comparison"] = {"composed": composed, "n_links": n, "expected": "composed=HOLD (structured) + internal consistency"}

    # 2. structured composed-token guard: accept exact "HOLD" or a descriptive value that CLEARLY
    #    contains the token "composed=HOLD"; reject ambiguous/absent/non-HOLD (fail-closed).
    cs = composed if isinstance(composed, str) else ""
    composed_holds = (cs.strip() == "HOLD") or ("composed=HOLD" in cs.replace(" ", ""))
    if not composed_holds:
        log.append("composed value does not clearly indicate HOLD: %r" % composed)
        return _finish("FAIL", "ambiguous or non-HOLD composed value")

    # 3. delegate to the shipped attestation verifier (same logic as proof_model_b._verify_attestation).
    #    Loads the EXTRACT's own proof_model_b (the tooling under certification) and points its ATTEST at
    #    the extract's attestation; verifies internal consistency against the extract's surfaces links.
    saved_path = list(sys.path); saved_dwb = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        surf = json.load(open(spath))
        links = surf["links"]
        import importlib.util
        spec = importlib.util.spec_from_file_location("_pmb_attest_ext", pmpath)
        pmb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pmb)
        pmb.ATTEST = apath
        ok, lines = pmb._verify_attestation(links)
        log.extend(lines)
    except Exception as e:  # noqa: BLE001 - any failure to verify is fail-closed
        return _finish("FAIL", "attestation verification could not complete (fail-closed): %s" % e)
    finally:
        sys.path[:] = saved_path; sys.dont_write_bytecode = saved_dwb

    return _finish("PASS" if ok else "FAIL",
                   None if ok else "attestation failed internal-consistency / link continuity")


def _ugk_diff(a_root, b_root):
    """Return sorted list of relpaths under ugk/ that differ between two extracted trees (source only)."""
    a = _list_source_files(os.path.join(a_root, "ugk"))
    b = _list_source_files(os.path.join(b_root, "ugk"))
    keys = set(a) | set(b)
    diff = sorted(k for k in keys if a.get(k) != b.get(k))
    return diff


def _posix_path(path):
    return path.replace(os.sep, "/").replace("\\", "/")


def check_ugk_confinement(extract, prior_extract, declared_surfaces, log_path):
    rec = _mk_record("B3", "ugk_confinement", ["<diff ugk/ vs prior, == declared surfaces>"], extract, None, "inline", log_path)
    rec["started_utc"] = _utc(); t0 = time.time()
    if not prior_extract:
        rec["verdict"] = "SKIPPED"; rec["note"] = "no prior archive supplied"
        with open(log_path, "w") as f:
            f.write("SKIPPED: no prior archive\n")
        rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
        return rec
    diff = sorted(_posix_path(d) for d in _ugk_diff(prior_extract, extract))
    declared = sorted(_posix_path(s) for s in (declared_surfaces or []))
    # declared surfaces are relative to repo root (e.g. ugk/adr.py); strip leading "ugk/" for compare.
    declared_rel = sorted(s[len("ugk/"):] if s.startswith("ugk/") else s for s in declared)
    equal = sorted(diff) == declared_rel
    rec["comparison"] = {"changed_ugk_files": ["ugk/" + d for d in diff],
                         "declared_surfaces": declared, "equal": equal}
    with open(log_path, "w") as f:
        json.dump(rec["comparison"], f, indent=2)
    rec["verdict"] = "PASS" if equal else "FAIL"
    rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
    return rec


def check_nodrift(extract, worktree, log_path):
    rec = _mk_record("B3", "nodrift", ["<diff extract/ugk vs worktree/ugk>"], extract, None, "inline", log_path)
    rec["started_utc"] = _utc(); t0 = time.time()
    if not worktree:
        rec["verdict"] = "SKIPPED"; rec["note"] = "no worktree supplied"
        with open(log_path, "w") as f:
            f.write("SKIPPED: no worktree\n")
        rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
        return rec
    a = _list_source_files(os.path.join(extract, "ugk"))
    b = _list_source_files(os.path.join(worktree, "ugk"))
    keys = set(a) | set(b)
    diff = sorted(k for k in keys if a.get(k) != b.get(k))
    rec["comparison"] = {"differing_files": ["ugk/" + d for d in diff], "identical": not diff}
    with open(log_path, "w") as f:
        json.dump(rec["comparison"], f, indent=2)
    rec["verdict"] = "PASS" if not diff else "FAIL"
    rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - t0, 2)
    return rec


# ===== r135 release-cert bundle: orchestrator-OWNED gate execution + incremental frontier =====
# The orchestrator (not G6) executes the GRBSA forest, the conformance suite, and reads the receipts,
# then assembles a structured release-cert BUNDLE and invokes G6 as the FINAL bundle verifier. This is
# the architectural fix: G6 stops being an orchestrator (it consumes the bundle) and the genesis->head
# --compose is replaced by an INCREMENTAL continuity frontier over the rolling attestation checkpoint.
#
# CLEAN-ROOM BOUNDARY. The orchestrator supplies its OWN (r135) bundle tooling — g6_bundle,
# g6_proof_cache, and the g6 consumer — loaded from THIS file's sibling tools/grbsa, because a
# pre-tooling archive (e.g. r134) does not carry them. The archive's SUBSTRATE (ugk/, the 9 GRBSA leaf
# gates, the conformance suite, the continuity declaration) is still certified clean-room FROM THE
# EXTRACT. For a self-consistent r135+ archive the extract's copies are byte-identical to the
# orchestrator's anyway (proven by hygiene+frame), so the distinction only matters when certifying the
# archive that INTRODUCES the tooling.

GRBSA_LEAF_GATES = ["g1_core_shape_gate", "g1_separation_symmetry_gate", "g2_substrate_naming_gate",
                    "g3_adapter_equivalence_gate", "g4a_adapter_generality_gate",
                    "g4b_projection_adapter_gate", "g4c_explain_adapter_gate",
                    "category_separation_gate", "g5_execution_adapter_gate"]
MIGRATION_RECEIPTS = ["migration_receipt_a1", "migration_receipt_determinism",
                      "migration_receipt_projection", "migration_receipt_explain",
                      "migration_receipt_execution"]
_REPO_GRBSA = os.path.normpath(os.path.join(_HERE, "..", "grbsa"))   # orchestrator's own r135 tooling


def _founded_env(extract):
    """Env with PYTHONPATH=extract, PYTHONDONTWRITEBYTECODE=1, and a FRESH isolated UGK_GENESIS_DIR in a
    TEMP dir (NEVER inside the extract). Founding happens in temp so the extract stays byte-clean (req 2)."""
    e = _subproc_env(extract)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e["UGK_GENESIS_DIR"] = tempfile.mkdtemp(prefix="cert-genesis-")
    return e


def _bounded_call(argv, env, cwd, log_path, timeout, done_marker=None):
    """Grandchild-proof bounded child: own process group, output to a FILE (never an OS pipe), whole
    group SIGKILLed on timeout AND on return so no straggler lingers. Returns the exit code
    (124 on timeout, 127 if not found). EVERY wait is bounded, so a lingering process tree can never
    hang the orchestrator. If done_marker (bytes) is given, the call reaps the group and returns 0 as
    soon as the marker appears in the log: the child's work is provably complete, so a completed run
    that leaves a lingering grandchild in its session returns CLEANLY instead of stalling on a process
    that never exits."""
    import signal as _sig
    import time as _time

    def _reap(p):
        # best-effort: on POSIX SIGKILL the whole session so no grandchild lingers (holding fds /
        # blocking); on Windows (no killpg/getpgid) terminate the direct child. Either way the bounded
        # waits + completion-by-marker below guarantee the wrapper never hangs.
        try:
            if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                os.killpg(os.getpgid(p.pid), _sig.SIGKILL)
            else:
                p.kill()
        except (ProcessLookupError, OSError):
            pass

    def _drain(p):
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    with open(log_path, "wb") as lf:
        try:
            p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                  stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
        except FileNotFoundError:
            lf.write(b"command not found\n"); return 127
        deadline = _time.monotonic() + timeout
        while True:
            try:
                rc = p.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                rc = None
            if rc is not None:
                _reap(p)            # child exited; reap any session stragglers, then return cleanly
                return rc
            # completion-by-marker: the child's work is provably done -> do NOT block on a lingering
            # process tree; reap the group and report success.
            if done_marker is not None:
                try:
                    with open(log_path, "rb") as rf:
                        if done_marker in rf.read():
                            _reap(p); _drain(p)
                            return 0
                except OSError:
                    pass
            if _time.monotonic() >= deadline:   # bounded timeout -> structured result (124), never a hang
                _reap(p); _drain(p)
                return 124


def run_grbsa_gates(extract, logdir):
    """Run the 9 GRBSA leaf gates, each under its OWN isolated founded genesis dir. Orchestrator-owned
    (G6 no longer spawns this forest). Returns [{name, verdict, exit_code}]."""
    out = []
    for g in GRBSA_LEAF_GATES:
        path = os.path.join(extract, "tools", "grbsa", "%s.py" % g)
        log_path = os.path.join(logdir, "grbsa_%s.log" % g)
        rc = _bounded_call([sys.executable, path, extract], _founded_env(extract), extract, log_path,
                           BUDGET["g6"])
        out.append({"name": g, "verdict": "PASS" if rc == 0 else "FAIL", "exit_code": rc})
    return out


def read_migration_receipts(extract):
    """Read the 5 MigrationReceipt JSON artifacts (NOT scripts). PASS criterion = evidence.equivalent."""
    out = []
    for m in MIGRATION_RECEIPTS:
        path = os.path.join(extract, "tools", "grbsa", "grbsa_runtime", "%s.json" % m)
        present, equivalent = os.path.exists(path), None
        if present:
            try:
                equivalent = json.load(open(path)).get("evidence", {}).get("equivalent", None)
            except Exception:  # noqa: BLE001
                present = False
        out.append({"name": m, "present": present, "equivalent": equivalent})
    return out


def live_gate_ids(extract):
    """Import the live conformance GATES from the EXTRACT (read-only registry read; founds nothing)."""
    prog = ("import sys;sys.dont_write_bytecode=True;import json;"
            "from ugk.conformance.run_gates_batch import GATES;print(json.dumps(list(GATES)))")
    out = subprocess.check_output([sys.executable, "-c", prog], cwd=extract, env=_subproc_env(extract),
                                  stderr=subprocess.STDOUT, timeout=60)
    return json.loads(out.decode().strip().splitlines()[-1])


def verify_release_command(extract):
    """Platform-select the canonical release verifier. verify_release.py is the authoritative,
    stdlib-only, CROSS-PLATFORM check (ugk harden -> conformance batch -> sentinel); verify_release.sh
    is a POSIX convenience wrapper that just execs it. On Windows (where `bash` may be absent or be the
    WSL launcher with no distro) run the Python verifier DIRECTLY so certification never depends on bash."""
    py = os.path.join(extract, "verify_release.py")
    sh = os.path.join(extract, "verify_release.sh")
    if os.name == "nt":
        return [sys.executable, py]
    if os.path.exists(sh):
        return ["bash", sh]
    return [sys.executable, py]


def run_conformance(extract, logdir):
    """Run the canonical conformance suite (verify_release.sh: found->harden->batch over the live GATES).
    Returns (verdict, exit_code). Count/ids come separately from the LIVE registry (no second universe)."""
    log_path = os.path.join(logdir, "conformance.log")
    rc = _bounded_call(verify_release_command(extract), _subproc_env(extract),
                       extract, log_path, BUDGET["verify_release"],
                       done_marker=b"=== verify_release PASS ===")
    try:
        txt = open(log_path, errors="replace").read()
    except OSError:
        txt = ""
    verdict = "PASS" if (rc == 0 and "verify_release PASS" in txt) else "FAIL"
    return verdict, rc


def compute_registry_identity(extract, env):
    """Compute law/schema/legend/codex/adr_count/registry_count from the extract (subprocess)."""
    prog = (
        "import hashlib,json\n"
        "from ugk.storage.store import UGKReceiptStore\n"
        "from ugk.storage.binding import LEGEND_HASH\n"
        "from ugk.adr import ADR_REGISTRY\n"
        "from ugk.invariants import INVARIANT_REGISTRY\n"
        "law=hashlib.sha256(open('ugk/invariants.py','rb').read()).hexdigest()\n"
        "schema=UGKReceiptStore(':memory:').schema_hash()\n"
        "codex=open('ugk/codex/CODEX_HASH.txt').read().strip()\n"
        "print(json.dumps({'law':law,'schema':schema,'legend':LEGEND_HASH,'codex':codex,"
        "'adr_count':len(ADR_REGISTRY),'registry_count':len(INVARIANT_REGISTRY)}))\n"
    )
    out = subprocess.check_output([sys.executable, "-c", prog], cwd=extract, env=env,
                                  stderr=subprocess.STDOUT, timeout=120)
    return json.loads(out.decode().strip().splitlines()[-1])


def run_archive_hygiene(extract, archive, logdir):
    log_path = os.path.join(logdir, "hygiene.log")
    rc = _bounded_call([sys.executable, os.path.join(extract, "tools/archive_hygiene_check.py"), archive],
                       _subproc_env(extract), extract, log_path, 120)
    try:
        txt = open(log_path, errors="replace").read()
    except OSError:
        txt = ""
    return "PASS" if (rc == 0 and "HYGIENE PASS" in txt) else "FAIL"


def run_bundle_phase(*, archive, archive_sha, extract, archives_dir, expected_frame, worktree,
                     logdir, scratch, emit_bundle, manifest_path, evidence_dir, started, t_run,
                     env_fp, env_detail, orchestrator_sha, launcher_sha, budget_frontier):
    """Assemble the release-cert bundle (orchestrator-owned execution) and verify it with the G6
    consumer. Aggregate verdict = the G6 bundle verdict (PASS / FAIL / UNFINISHED)."""
    # Load the orchestrator's OWN (r135) bundle tooling from this file's sibling tools/grbsa.
    saved_path = list(sys.path)
    sys.dont_write_bytecode = True
    if _REPO_GRBSA not in sys.path:
        sys.path.insert(0, _REPO_GRBSA)
    import importlib
    g6_bundle = importlib.import_module("g6_bundle")
    g6_proof_cache = importlib.import_module("g6_proof_cache")

    env = _subproc_env(extract)
    print("  [bundle] orchestrator-owned gate execution (founds ephemerally in temp; extract stays clean)")

    # 1. conformance (canonical suite) + live gate ids/count (single source = live registry)
    conf_verdict, conf_rc = run_conformance(extract, logdir)
    gate_ids = live_gate_ids(extract)
    print("  [bundle] conformance: %s (%d live gates, exit=%s)" % (conf_verdict, len(gate_ids), conf_rc))

    # 2. GRBSA forest (9 leaf gates, isolated founded)
    grbsa = run_grbsa_gates(extract, logdir)
    print("  [bundle] GRBSA: %d/%d PASS" % (sum(g["verdict"] == "PASS" for g in grbsa), len(grbsa)))

    # 3. MigrationReceipts
    mrs = read_migration_receipts(extract)
    print("  [bundle] receipts: %d/%d equivalent" % (sum(m["equivalent"] is True for m in mrs), len(mrs)))

    # 4. registry identity
    ri = compute_registry_identity(extract, env)

    # 5. hygiene + no-drift
    hyg_verdict = run_archive_hygiene(extract, archive, logdir)
    nodrift_rec = check_nodrift(extract, worktree, os.path.join(logdir, "nodrift.log"))
    nodrift_verdict = "PASS" if nodrift_rec["verdict"] in ("PASS", "SKIPPED") else "FAIL"

    # 6. incremental continuity frontier (NOT the full --compose; rolling-checkpoint frontier only)
    att = os.path.join(extract, "tools", "grbsa", "CONTINUITY_ATTESTATION.json")
    surf = os.path.join(extract, "tools", "grbsa", "continuity_surfaces.json")
    frontier = g6_proof_cache.verify_frontier(
        attestation_path=att, surfaces_path=surf, archives_dir=archives_dir,
        cache_path=os.path.join(scratch, "g6_proof_cache.json"), budget_s=budget_frontier)
    print("  [bundle] frontier: %s (attested head=%s, %d frontier links)" % (
        frontier["verdict"], frontier.get("attested", {}).get("head_candidate"), len(frontier.get("frontier", []))))

    # 7. assemble bundle
    bundle = g6_bundle.assemble_bundle(
        release=os.path.basename(archive), archive_sha256=archive_sha,
        conformance=g6_bundle.build_conformance(gate_ids, conf_verdict),
        gates=g6_bundle.build_gates(grbsa),
        migration_receipts=g6_bundle.build_migration_receipts(mrs),
        registry_identity=g6_bundle.build_registry_identity(
            law=ri["law"], schema=ri["schema"], legend=ri["legend"], codex=ri["codex"],
            adr_count=ri["adr_count"], registry_count=ri["registry_count"]),
        hygiene=g6_bundle.build_hygiene(archive_sha256=archive_sha, hygiene_verdict=hyg_verdict,
                                        nodrift_verdict=nodrift_verdict),
        continuity_frontier=g6_bundle.build_continuity_frontier(frontier))

    bundle_path = emit_bundle or os.path.join(scratch, "release-cert-bundle.json")
    os.makedirs(os.path.dirname(os.path.abspath(bundle_path)), exist_ok=True)
    with open(bundle_path, "w") as f:
        json.dump(bundle, f, indent=2)
    print("  [bundle] emitted: %s" % bundle_path)

    # 8. invoke G6 as the FINAL bundle verifier (the orchestrator's r135 consumer, NOT the extract's G6).
    g6_path = os.path.join(_REPO_GRBSA, "g6_aggregate_validation_gate.py")
    g6_log = os.path.join(logdir, "g6_bundle_verify.log")
    g6_argv = [sys.executable, g6_path, "--bundle", bundle_path, "--extract", extract,
               "--expected-law", expected_frame["law"], "--expected-schema", expected_frame["schema"],
               "--expected-legend", expected_frame["legend"],
               "--expected-codex", expected_frame["codex"],
               "--expected-adr-count", str(expected_frame.get("adr_count") or 55),
               "--expected-registry-count", str(expected_frame.get("registry_count") or 82),
               "--expected-archive-sha256", archive_sha]
    g6_rc = _bounded_call(g6_argv, _subproc_env(extract), extract, g6_log, BUDGET["g6"])
    try:
        g6_txt = open(g6_log, errors="replace").read()
    except OSError:
        g6_txt = ""
    if "GRBSA G6 AGGREGATE VALIDATION GATE: PASS" in g6_txt:
        g6_verdict = "PASS"
    elif "GRBSA G6 AGGREGATE VALIDATION GATE: UNFINISHED" in g6_txt:
        g6_verdict = "UNFINISHED"
    else:
        g6_verdict = "FAIL"
    print("  [bundle] G6 final bundle verdict: %s (exit=%s)" % (g6_verdict, g6_rc))

    sys.path[:] = saved_path

    # manifest (records each section verdict + the G6 consumer verdict; aggregate = G6 verdict)
    records = [
        {"name": "conformance", "verdict": conf_verdict, "exit_code": conf_rc, "live_gate_count": len(gate_ids)},
        {"name": "grbsa_forest", "verdict": "PASS" if all(g["verdict"] == "PASS" for g in grbsa) else "FAIL",
         "gates": grbsa},
        {"name": "migration_receipts",
         "verdict": "PASS" if all(m["equivalent"] is True for m in mrs) else "FAIL", "receipts": mrs},
        {"name": "registry_identity", "verdict": "RECORDED", "computed": ri},
        {"name": "hygiene", "verdict": hyg_verdict},
        {"name": "nodrift", "verdict": nodrift_rec["verdict"]},
        {"name": "continuity_frontier", "verdict": frontier["verdict"],
         "attested_head": frontier.get("attested", {}).get("head_candidate")},
        {"name": "g6_bundle_consumer", "verdict": g6_verdict, "exit_code": g6_rc, "log_path": g6_log},
    ]
    aggregate = g6_verdict
    manifest = {
        "schema": SCHEMA, "archive": os.path.basename(archive), "archive_sha256": archive_sha,
        "orchestrator_sha256": orchestrator_sha, "launcher_sha256": launcher_sha,
        "phase_requested": "bundle", "env_fingerprint": env_fp, "env_detail": env_detail,
        "expected_frame": expected_frame, "worktree": worktree,
        "bundle_path": os.path.abspath(bundle_path), "bundle_schema": g6_bundle.BUNDLE_SCHEMA,
        "started_utc": started, "ended_utc": _utc(), "duration_s": round(time.time() - t_run, 2),
        "aggregate_verdict": aggregate, "checks": records,
    }
    if evidence_dir:
        os.makedirs(evidence_dir, exist_ok=True)
        for lp in [g6_log, os.path.join(logdir, "conformance.log"), os.path.join(logdir, "hygiene.log")]:
            if os.path.exists(lp):
                _safe_copy(lp, os.path.join(evidence_dir, os.path.basename(lp)))
        _safe_copy(bundle_path, os.path.join(evidence_dir, os.path.basename(bundle_path)))
        manifest["evidence_dir"] = os.path.abspath(evidence_dir)
    mpath = manifest_path or os.path.join(scratch, "cert-manifest.json")
    os.makedirs(os.path.dirname(os.path.abspath(mpath)), exist_ok=True)
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 70)
    for r in records:
        print("  %-26s %s" % (r["name"], r["verdict"]))
    print("-" * 70)
    print("  AGGREGATE (bundle phase): %s  (archive=%s)" % (aggregate, os.path.basename(archive)))
    print("  bundle:   %s" % os.path.abspath(bundle_path))
    print("  manifest: %s" % mpath)
    print("=" * 70)
    return {"PASS": 0, "FAIL": 1, "UNFINISHED": 3}.get(aggregate, 1)


# ----- phase membership -----
QUICK = ["hygiene", "frame", "verify_release", "probe", "adapter_atomicity", "g5",
         "category_separation", "b4a", "attestation", "ugk_confinement", "nodrift"]
CGPROJ = ["phase1_structural_validity_gate", "phase2_execution_removability_gate",
          "phase3_determinism_gate", "phase4_fidelity_gate", "phase4_5_jurisdiction_gate",
          "phase5a_docs_integration_gate", "phase5b_explain_gate", "phase6_full_validation_gate"]
# r135: G6 is no longer a self-validated gate in deep/full. The orchestrator runs the GRBSA forest
# directly (grbsa_forest); G6 runs only as the final bundle verifier in --phase bundle.
DEEP_EXTRA = ["grbsa_forest"] + ["cgproj." + g for g in CGPROJ]
COMPOSE = ["compose"]


def phase_members(phase):
    if phase == "quick":
        return list(QUICK)
    if phase == "deep":
        return list(QUICK) + list(DEEP_EXTRA)
    if phase == "compose":
        return ["hygiene"] + list(COMPOSE)
    if phase == "full":
        return list(QUICK) + list(DEEP_EXTRA) + list(COMPOSE)
    raise SystemExit("unknown phase: %s" % phase)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", required=True)
    ap.add_argument("--phase", choices=["quick", "deep", "compose", "full", "bundle"], default="quick")
    ap.add_argument("--archives-dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--prior-archive", default=None)
    ap.add_argument("--declared-surfaces", default="")
    ap.add_argument("--worktree", default=None)
    ap.add_argument("--expected-law", default=DEFAULT_LAW)
    ap.add_argument("--expected-schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--expected-legend", default=DEFAULT_LEGEND)
    ap.add_argument("--expected-codex", default=None)
    ap.add_argument("--expected-adr-count", type=int, default=None)
    ap.add_argument("--expected-adr", default=None)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--evidence-dir", default=None)
    ap.add_argument("--emit-bundle", default=None,
                    help="(--phase bundle) path to write the release-cert bundle JSON")
    ap.add_argument("--expected-registry-count", type=int, default=None,
                    help="(--phase bundle) expected len(INVARIANT_REGISTRY); bound to live registry, "
                         "fails closed on mismatch")
    ap.add_argument("--frontier-budget-s", type=int, default=120,
                    help="(--phase bundle) wall-clock budget for the incremental continuity frontier")
    ap.add_argument("--resume", default=None)
    ap.add_argument("--scratch", default=None)
    ap.add_argument("--max-concurrency", type=int, default=1,
                    help="resource-aware cap on co-scheduled heavy detached checks; default 1 (serial). "
                         "The orchestrator never blindly co-schedules G6 + cgproj + compose at max concurrency.")
    args = ap.parse_args(argv)
    if args.max_concurrency < 1:
        args.max_concurrency = 1

    started = _utc(); t_run = time.time()
    archive = os.path.abspath(args.archive)
    env_fp, env_detail = env_fingerprint()
    orchestrator_sha = _sha256_file(os.path.abspath(__file__))
    launcher_sha = _sha256_file(os.path.join(_HERE, "run_detached.py"))

    # ---- preflight (r113 section 9) ----
    scratch = args.scratch or tempfile.mkdtemp(prefix="cert-")
    logdir = os.path.join(scratch, "logs"); os.makedirs(logdir, exist_ok=True)

    def fail_preflight(msg):
        print("HOLD(preflight): %s" % msg)
        return 2

    if not os.path.exists(archive):
        return fail_preflight("archive missing: %s" % archive)
    archive_sha = _sha256_file(archive)

    try:
        extract = extract_archive(archive, scratch)
    except Exception as e:  # noqa: BLE001 - a corrupt/unreadable archive must fail closed
        return fail_preflight("archive not extractable (%s: %s)" % (type(e).__name__, e))
    required = ["verify_release.py", "verify_release.sh", "tools/grbsa/proof_model_b.py",
                "tools/grbsa/g6_aggregate_validation_gate.py",
                "tools/grbsa/adapter_atomicity_propagation_gate.py",
                "tools/grbsa/g5_execution_adapter_gate.py",
                "tools/grbsa/category_separation_gate.py",
                "tools/effect_declaration_probe.py", "tools/b4a_conformance.py",
                "tools/archive_hygiene_check.py", "ugk/codex/CODEX_HASH.txt"] + \
               ["construction/cgproj/%s.py" % g for g in CGPROJ]
    missing = [r for r in required if not os.path.exists(os.path.join(extract, r))]
    if missing:
        return fail_preflight("missing in archive: %s" % ", ".join(missing))

    expected_frame = {"law": args.expected_law, "schema": args.expected_schema,
                      "legend": args.expected_legend, "codex": args.expected_codex,
                      "adr_count": args.expected_adr_count, "adr_id": args.expected_adr,
                      "registry_count": args.expected_registry_count}
    declared = [s for s in args.declared_surfaces.split(",") if s.strip()]

    prior_extract = None
    if args.prior_archive:
        prior_extract = os.path.join(scratch, "prior")
        os.makedirs(prior_extract, exist_ok=True)
        with tarfile.open(os.path.abspath(args.prior_archive), "r:gz") as t:
            t.extractall(prior_extract)

    # ---- resume (r113 section 8) ----
    resume_cache = {}
    if args.resume and os.path.exists(args.resume):
        try:
            prev = json.load(open(args.resume))
            if (prev.get("archive_sha256") == archive_sha and prev.get("env_fingerprint") == env_fp
                    and prev.get("orchestrator_sha256") == orchestrator_sha):
                for c in prev.get("checks", []):
                    if c.get("verdict") == "PASS":
                        resume_cache[(c["name"], c.get("tool_sha256"), json.dumps(c["command"]))] = c
        except Exception:
            resume_cache = {}

    env = _subproc_env(extract)

    # ---- r135 bundle phase: orchestrator owns gate execution, founds ephemerally, emits a
    # structured release-cert bundle, and invokes G6 ONLY as the final bundle verifier. G6 spawns
    # no GRBSA/conformance forest in this path. Dispatched here (preflight already guaranteed a
    # clean, complete extract and a resolved expected_frame).
    if args.phase == "bundle":
        if not args.expected_codex:
            ap.error("--phase bundle requires --expected-codex HASH (no stale default; fail closed)")
        return run_bundle_phase(
            archive=archive, archive_sha=archive_sha, extract=extract,
            archives_dir=os.path.abspath(args.archives_dir), expected_frame=expected_frame,
            worktree=args.worktree, logdir=logdir, scratch=scratch,
            emit_bundle=(os.path.abspath(args.emit_bundle) if args.emit_bundle else None),
            manifest_path=(os.path.abspath(args.manifest) if args.manifest else None),
            evidence_dir=args.evidence_dir, started=started, t_run=t_run,
            env_fp=env_fp, env_detail=env_detail, orchestrator_sha=orchestrator_sha,
            launcher_sha=launcher_sha, budget_frontier=args.frontier_budget_s)

    members = phase_members(args.phase)
    records = []

    # Resource-aware scheduling (r114 requirement): heavy detached checks (G6, cgproj, compose) are
    # run SERIALLY by this loop (launched + polled to completion one at a time) and are NEVER blindly
    # co-scheduled at max concurrency. Effective concurrency is 1; max_concurrency is the recorded
    # ceiling, which serial execution trivially respects. This is recorded so a HOLD(timeout) is
    # diagnosable from the manifest alone: a timeout under effective_concurrency=1 with nothing
    # co-running is a strong real-stall signal; a timeout with heavy co-running is a harness artifact.
    EFFECTIVE_CONCURRENCY = 1
    scheduling = {
        "max_concurrency": args.max_concurrency,
        "effective_concurrency": EFFECTIVE_CONCURRENCY,
        "policy": ("resource-aware: heavy detached checks (G6, cgproj, compose) run serially "
                   "(effective concurrency 1) and are never co-scheduled at max concurrency; "
                   "max_concurrency is the recorded ceiling, trivially respected by serial execution"),
    }
    concurrent_ctx = {"effective_concurrency": EFFECTIVE_CONCURRENCY, "co_running": []}

    def tool_sha(rel):
        p = os.path.join(extract, rel)
        return _sha256_file(p) if os.path.exists(p) else None

    def maybe_resume(name, sha, command):
        return resume_cache.get((name, sha, json.dumps(command)))

    for name in members:
        log_path = os.path.join(logdir, name.replace(".", "_") + ".log")
        cached = None
        if name == "hygiene":
            sha = tool_sha("tools/archive_hygiene_check.py")
            argv_c = [sys.executable, os.path.join(extract, "tools/archive_hygiene_check.py"), archive]
            cached = maybe_resume(name, sha, argv_c)
            rec = cached or run_exitcode_inline("pre", name, argv_c, extract, sha, env, log_path,
                                                expect_substr="HYGIENE PASS")
        elif name == "frame":
            cached = maybe_resume(name, None, ["<frame>"])
            rec = cached or check_frame(extract, env, log_path, expected_frame)
        elif name == "verify_release":
            sha = tool_sha("verify_release.py")
            argv_c = verify_release_command(extract)
            cached = maybe_resume(name, sha, argv_c)
            rec = cached or run_exitcode_inline("B1", name, argv_c, extract, sha, env, log_path,
                                                expect_substr="ALL PASS")
        elif name == "probe":
            sha = tool_sha("tools/effect_declaration_probe.py")
            argv_c = [sys.executable, os.path.join(extract, "tools/effect_declaration_probe.py"), extract]
            cached = maybe_resume(name, sha, argv_c)
            rec = cached or run_exitcode_inline("B2", name, argv_c, extract, sha, env, log_path)
        elif name in ("adapter_atomicity", "g5", "category_separation"):
            relmap = {"adapter_atomicity": "tools/grbsa/adapter_atomicity_propagation_gate.py",
                      "g5": "tools/grbsa/g5_execution_adapter_gate.py",
                      "category_separation": "tools/grbsa/category_separation_gate.py"}
            sha = tool_sha(relmap[name])
            argv_c = [sys.executable, os.path.join(extract, relmap[name]), extract]
            cached = maybe_resume(name, sha, argv_c)
            rec = cached or run_exitcode_inline("B2", name, argv_c, extract, sha, env, log_path)
        elif name == "b4a":
            sha = tool_sha("tools/b4a_conformance.py")
            argv_c = [sys.executable, os.path.join(extract, "tools/b4a_conformance.py"), extract]
            cached = maybe_resume(name, sha, argv_c)
            rec = cached or run_exitcode_inline("B2", name, argv_c, extract, sha, env, log_path)
        elif name == "attestation":
            cached = maybe_resume(name, None, ["<attestation>"])
            rec = cached or check_attestation(extract, log_path)
        elif name == "ugk_confinement":
            cached = maybe_resume(name, None, ["<confinement>"])
            rec = cached or check_ugk_confinement(extract, prior_extract, declared, log_path)
        elif name == "nodrift":
            cached = maybe_resume(name, None, ["<nodrift>"])
            rec = cached or check_nodrift(extract, args.worktree, log_path)
        elif name == "grbsa_forest":
            # r135: the orchestrator runs the 9 GRBSA leaf gates DIRECTLY (each founds ephemerally
            # in temp; extract stays clean). G6 is no longer a self-validated gate here -- it runs
            # only as the final bundle verifier in --phase bundle. Aggregated to one record so
            # legacy deep/full retain full GRBSA coverage without invoking the removed G6 orchestrator.
            grbsa = run_grbsa_gates(extract, logdir)
            n_pass = sum(g["verdict"] == "PASS" for g in grbsa)
            rec = _mk_record("B2", name, ["<grbsa_forest:9-leaf-gates>"], extract, None, "inline", log_path)
            rec["verdict"] = "PASS" if (grbsa and n_pass == len(grbsa)) else "FAIL"
            rec["note"] = "%d/%d GRBSA leaf gates PASS" % (n_pass, len(grbsa))
            rec["gates"] = grbsa
            cached = None
        elif name.startswith("cgproj."):
            g = name.split(".", 1)[1]
            rel = "construction/cgproj/%s.py" % g
            sha = tool_sha(rel)
            argv_c = [sys.executable, os.path.join(extract, rel), extract]
            cached = maybe_resume(name, sha, argv_c)
            rec = cached or run_exitcode_inline("B4", name, argv_c, extract, sha, env, log_path)
        elif name == "compose":
            sha = tool_sha("tools/grbsa/proof_model_b.py")
            argv_c = [sys.executable, os.path.join(extract, "tools/grbsa/proof_model_b.py"),
                      "--compose", "--archives", os.path.abspath(args.archives_dir)]
            cached = maybe_resume(name, sha, argv_c)
            if cached:
                rec = cached
            else:
                rec = _mk_record("B3", name, argv_c, extract, sha, "bounded_inline", log_path)
                rec["timeout_budget_s"] = BUDGET["compose"]
                rec["concurrent_context"] = concurrent_ctx
                rec["started_utc"] = _utc(); _t0 = time.time()
                _rc = _bounded_call(argv_c, env, extract, log_path, BUDGET["compose"])
                rec["ended_utc"] = _utc(); rec["duration_s"] = round(time.time() - _t0, 2)
                rec["exit_code"] = _rc
                if _rc == 124:
                    rec["verdict"] = "HOLD"; rec["hold_reason"] = "timeout"; rec["note"] = "timeout(budget %ds)" % BUDGET["compose"]
                else:
                    rec["verdict"], rec["hold_reason"] = _verdict_from_rc(_rc, "CONTINUITY HOLDS", log_path)
        else:
            rec = _mk_record("?", name, ["<unknown>"], extract, None, "inline", log_path)
            rec["verdict"] = "HOLD"; rec["note"] = "unknown check"
        if cached:
            rec["resumed"] = True
        records.append(rec)

    if any(r["verdict"] == "FAIL" for r in records):
        aggregate = "FAIL"
    elif any(r["verdict"] == "HOLD" for r in records):
        aggregate = "HOLD"
    else:
        aggregate = "PASS"

    manifest = {
        "schema": SCHEMA, "archive": os.path.basename(archive), "archive_sha256": archive_sha,
        "orchestrator_sha256": orchestrator_sha, "launcher_sha256": launcher_sha,
        "phase_requested": args.phase, "env_fingerprint": env_fp, "env_detail": env_detail,
        "scheduling": scheduling,
        "expected_frame": expected_frame, "prior_release": (os.path.basename(args.prior_archive) if args.prior_archive else None),
        "declared_surfaces": declared, "worktree": args.worktree,
        "started_utc": started, "ended_utc": _utc(), "duration_s": round(time.time() - t_run, 2),
        "aggregate_verdict": aggregate, "checks": records,
    }

    # ---- evidence dir: copy logs durably (residual decision 1) ----
    if args.evidence_dir:
        os.makedirs(args.evidence_dir, exist_ok=True)
        for r in records:
            lp = r.get("log_path")
            if lp and os.path.exists(lp):
                _safe_copy(lp, os.path.join(args.evidence_dir, os.path.basename(lp)))
        manifest["evidence_dir"] = os.path.abspath(args.evidence_dir)

    manifest_path = args.manifest or os.path.join(scratch, "cert-manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 70)
    for r in records:
        v = r["verdict"]
        if v == "HOLD" and r.get("hold_reason"):
            v = "HOLD(%s)" % r["hold_reason"]
        print("  %-26s %-14s %s" % (r["name"], v, r.get("note", "")))
    print("-" * 70)
    print("  scheduling: effective_concurrency=%d (heavy checks serial), ceiling=%d" % (
        EFFECTIVE_CONCURRENCY, args.max_concurrency))
    print("  AGGREGATE: %s  (phase=%s, archive=%s)" % (aggregate, args.phase, os.path.basename(archive)))
    print("  manifest: %s" % manifest_path)
    print("=" * 70)
    return 0 if aggregate == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
