#!/usr/bin/env python3
"""verify_release.py - canonical, stdlib-only, CROSS-PLATFORM release verification.

This is the authoritative release check. verify_release.sh is now a thin POSIX convenience
wrapper that just execs this file. The certifier (tools/release/certify_release.py) selects this
Python entry point directly on Windows, where `bash` may be absent or be the WSL launcher with no
distro installed, so certification never depends on bash/WSL.

Authoritative steps (equivalent to the historical verify_release.sh):
  1. UTF-8 output + PYTHONHASHSEED=0 for every subprocess (Windows defaults to cp1252 / random hash).
  2. Pin-drift check: invariants_pin and LEGEND_HASH in RELEASE.txt must match the live tree.
  3. Found genesis in an ISOLATED throwaway dir (never <repo>/genesis) and PRE-found it, so the gate
     batch runs in-process and never takes the ephemeral-founding re-exec path that could hang.
  4. python -m ugk.cli harden  (explicit grundnorm read-only lifecycle step).
  5. python -m ugk.conformance.run_gates_batch  (the live GATES; the suite prints its own N/N summary).
  6. Require the suite's own success exit (0).
  7. Print exactly: === verify_release PASS ===
  8. Exit nonzero on ANY failure (missing RELEASE.txt, pin drift, founding, harden, or gate failure).
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _fail(msg: str) -> "NoReturn":  # noqa: F821
    print("  FAIL %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def _base_env() -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"               # force UTF-8 text mode (Windows defaults to cp1252)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONHASHSEED"] = "0"           # deterministic hashing across subprocesses
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # never leave .pyc in the tree (hygiene)
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")
    return env


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # py3.7+; harmless if already utf-8
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    env = _base_env()
    print("=== UGK v0.1.0 verify_release ===")

    release = os.path.join(HERE, "RELEASE.txt")
    if not os.path.isfile(release):
        _fail("RELEASE.txt not found")
    txt = open(release, encoding="utf-8").read()

    def _pin(name: str):
        m = re.search(r"^%s:\s*(\S+)" % re.escape(name), txt, re.M)
        return m.group(1) if m else None

    pinned_inv = _pin("invariants_pin")
    pinned_lh = _pin("LEGEND_HASH")
    if not pinned_inv or not pinned_lh:
        _fail("RELEASE.txt missing invariants_pin / LEGEND_HASH")

    # 2. pin-drift check (parity with verify_release.sh)
    actual_inv = hashlib.sha256(
        open(os.path.join(HERE, "ugk", "invariants.py"), "rb").read()).hexdigest()
    lh = subprocess.run(
        [sys.executable, "-c",
         "import sys;sys.path.insert(0,%r);"
         "from ugk.storage.binding import LEGEND_HASH;print(LEGEND_HASH)" % HERE],
        capture_output=True, text=True, env=env)
    actual_lh = lh.stdout.strip()
    if actual_inv != pinned_inv:
        _fail("invariants_pin: drift detected")
    print("  PASS invariants_pin")
    if actual_lh != pinned_lh:
        _fail("LEGEND_HASH: drift detected")
    print("  PASS LEGEND_HASH")

    # 3. isolated, pre-founded genesis dir (never <repo>/genesis)
    genesis_dir = tempfile.mkdtemp(prefix="ugk-verify-genesis-")
    env["UGK_GENESIS_DIR"] = genesis_dir
    try:
        print("  Running conformance suite...")
        pre = subprocess.run(
            [sys.executable, "-c",
             "from ugk.conformance._fixture import fixture_pubkey;"
             "from ugk.charter import DeploymentManifest, write_charter_artifacts;"
             "write_charter_artifacts(DeploymentManifest.create("
             "fixture_pubkey(),'verify-release','verify','trace_only'), force=False)"],
            cwd=HERE, env=env)
        if pre.returncode != 0:
            _fail("charter pre-founding failed")

        # 4. explicit lifecycle step: harden writes GRUNDNORM_POSTURE.json into UGK_GENESIS_DIR
        print("  Establishing Grundnorm read-only posture (explicit lifecycle step: ugk harden)...")
        if subprocess.run([sys.executable, "-m", "ugk.cli", "harden"],
                          cwd=HERE, env=env).returncode != 0:
            _fail("ugk harden failed")

        # 5/6. run the live gate batch in-process under the pre-founded genesis; require success exit
        benv = dict(env)
        benv["PYTHONUNBUFFERED"] = "1"
        if subprocess.run([sys.executable, "-m", "ugk.conformance.run_gates_batch"],
                          cwd=HERE, env=benv).returncode != 0:
            _fail("conformance suite")
        print("  PASS conformance suite")
    finally:
        shutil.rmtree(genesis_dir, ignore_errors=True)

    # 7. success sentinel (the certifier's completion marker)
    print("=== verify_release PASS ===")


if __name__ == "__main__":
    main()
