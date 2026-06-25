"""IEL Invariant D adversarial gate (AD-30).

Proves the production read-only CLI substrate (verify / status / attest) NEVER mutates filesystem
or receipt state:

  Case A (absent/empty state-dir): every read-only command fails closed with a structured result
    and DOES NOT create ugk.db.
  Case B (founded state): every read-only command succeeds (exit 0) WITHOUT adding receipts or
    genesis files - receipt_count is byte-identical before and after.
  Case C (substrate): write() on a mode=ro store raises ReadOnlyViolation.

Because GOVERNOR_PUBKEY_HEX resolves at IMPORT time from genesis/, the founded cases are exercised
as SUBPROCESSES under a genesis env pointing at a freshly-chartered temp deployment - the gate does
not (and cannot soundly) found a second deployment in its own already-imported process.
"""
from __future__ import annotations
import os
import sys
import json
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path

import ugk

_REPO = str(Path(ugk.__file__).parent.parent)
_TIMEOUT = 120


def _env(genesis_dir: str) -> dict:
    e = dict(os.environ)
    e["UGK_GENESIS_DIR"] = genesis_dir
    e["UGK_STATE_DIR"] = genesis_dir
    e["PYTHONPATH"] = _REPO + os.pathsep + e.get("PYTHONPATH", "")
    return e


def _run(argv, env):
    return subprocess.run(argv, capture_output=True, text=True, env=env, timeout=_TIMEOUT)


def _cli(args, env):
    return _run([sys.executable, "-m", "ugk.cli"] + args, env)


def _found(genesis_dir: str, env: dict) -> None:
    """Charter (pubkey + manifest + privkey) then found a chain (ceremony + open_session)."""
    charter = (
        "from ugk.conformance._fixture import fixture_pubkey, DEV_FIXTURE_PRIVKEY;"
        "from ugk.charter import DeploymentManifest, write_charter_artifacts;"
        "import os;"
        "write_charter_artifacts(DeploymentManifest.create("
        "fixture_pubkey(),'ro-gate','verify','trace_only'), force=True);"
        "g=os.environ['UGK_GENESIS_DIR'];"
        "open(g+'/GENESIS_PRIVKEY.hex','w').write(DEV_FIXTURE_PRIVKEY);"
        "open(g+'/GENESIS_KEY.pub','w').write(fixture_pubkey())"
    )
    r = _run([sys.executable, "-c", charter], env)
    if r.returncode != 0:
        raise RuntimeError("charter subprocess failed: %s" % (r.stderr[:200]))
    found = (
        "import os;"
        "from ugk.storage.store import UGKReceiptStore;"
        "from ugk.kernel import GovernanceKernel;"
        "g=os.environ['UGK_GENESIS_DIR'];"
        "k=GovernanceKernel(store=UGKReceiptStore(db_path=g+'/ugk.db'), authority='cli');"
        "k._ceremony(); k.open_session()"
    )
    r = _run([sys.executable, "-c", found], env)
    if r.returncode != 0:
        raise RuntimeError("found subprocess failed: %s" % (r.stderr[:200]))


def _receipt_count(db_path: str, env: dict) -> int:
    code = ("import sys;from ugk.storage.store import UGKReceiptStore as S;"
            "print(S(db_path=sys.argv[1], read_only=True).receipt_count())")
    r = _run([sys.executable, "-c", code, db_path], env)
    return int(r.stdout.strip())


def _file_names(d: str) -> set:
    return {p.name for p in Path(d).iterdir() if p.is_file()}


def run():
    failures = []

    # ----- Case A: absent/empty state-dir -> fail closed, no ugk.db -----
    empty = tempfile.mkdtemp()
    try:
        env_e = _env(empty)
        for cmd in ("verify", "status", "attest"):
            r = _cli(["--state-dir", empty, cmd], env_e)
            if (Path(empty) / "ugk.db").exists():
                failures.append("empty:%s CREATED ugk.db" % cmd)
                (Path(empty) / "ugk.db").unlink()  # reset for next cmd
            if r.returncode == 0:
                failures.append("empty:%s did not fail closed (exit 0)" % cmd)
            try:
                if "error" not in json.loads(r.stdout):
                    failures.append("empty:%s missing structured error" % cmd)
            except Exception:
                failures.append("empty:%s non-JSON output" % cmd)
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    # ----- Case B: founded state -> succeeds, ZERO mutation -----
    g = tempfile.mkdtemp()
    try:
        env_g = _env(g)
        _found(g, env_g)
        db = str(Path(g) / "ugk.db")
        n0 = _receipt_count(db, env_g)
        names0 = _file_names(g)
        for cmd in ("verify", "status", "attest"):
            r = _cli(["--state-dir", g, cmd], env_g)
            if r.returncode != 0:
                failures.append("founded:%s failed (exit %d): %s"
                                % (cmd, r.returncode, (r.stdout or r.stderr)[:120]))
        n1 = _receipt_count(db, env_g)
        new_names = _file_names(g) - names0
        if n1 != n0:
            failures.append("founded: receipt_count %d -> %d (RECEIPT MUTATION)" % (n0, n1))
        if new_names:
            failures.append("founded: new files created by read-only cmds: %s" % sorted(new_names))
    except Exception as e:
        failures.append("founded-setup error: %s" % (str(e)[:160]))
    finally:
        shutil.rmtree(g, ignore_errors=True)

    # ----- Case C: write() on a read-only store raises -----
    g2 = tempfile.mkdtemp()
    try:
        env_g2 = _env(g2)
        _found(g2, env_g2)
        wscript = (
            "import sys\n"
            "from ugk.storage.store import UGKReceiptStore\n"
            "from ugk.integrity.readonly import ReadOnlyViolation\n"
            "s = UGKReceiptStore(db_path=sys.argv[1], read_only=True)\n"
            "try:\n"
            "    s.write(op='x', authority='a', parameters={}, intent='t', jurisdiction='production',\n"
            "            session_dkn='d', law_hash='L', legend_hash='G', warrant_id='', intent_ref='')\n"
            "    print('NOVIOLATION')\n"
            "except ReadOnlyViolation:\n"
            "    print('RAISED')\n"
        )
        sp = Path(g2) / "_wtest.py"
        sp.write_text(wscript)
        r = _run([sys.executable, str(sp), str(Path(g2) / "ugk.db")], env_g2)
        if "RAISED" not in r.stdout:
            failures.append("read-only store write() did not raise: %s | %s"
                            % (r.stdout[:80], r.stderr[:80]))
    except Exception as e:
        failures.append("write-test error: %s" % (str(e)[:160]))
    finally:
        shutil.rmtree(g2, ignore_errors=True)

    if failures:
        return False, "Invariant D (read-only) FAILURES: " + "; ".join(failures)
    return True, ("Invariant D: verify/status/attest fail closed on empty (no ugk.db, structured "
                  "error), succeed on founded with zero receipt/file mutation; mode=ro store "
                  "write() raises ReadOnlyViolation.")


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + ": " + detail)
    sys.exit(0 if ok else 1)
