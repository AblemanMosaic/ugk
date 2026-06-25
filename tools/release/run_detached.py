#!/usr/bin/env python3
"""run_detached.py — UGK r114 release-cert detached launcher.

Truly detaches a long-running command so a caller (a tool harness, or certify_release.py) sees the
LAUNCHER exit immediately, while the real job runs in its own session. This eliminates the failure mode
where a harness timeout on the launching shell is mistaken for a job failure (the r111 setsid pain).

It is a THIN launcher with EVIDENCE-PRODUCTION duties, not a judge: it launches, reports (PID, log,
status, command, start time), and durably captures the job's exit code in an atomic sidecar status file
so the verdict survives the launcher's own exit.

Design (UGK r113 design, section 4):
  - subprocess.Popen(argv, start_new_session=True, stdin=DEVNULL, stdout=log, stderr=STDOUT,
    close_fds=True): new session/process group, all inherited fds closed, stdin from /dev/null.
  - The launched process is THIS file in `exec` mode, which runs the real command (inheriting the
    already-redirected stdout/stderr -> log), waits, and writes "<log>.status" ATOMICALLY
    (write-temp + os.replace) as a small JSON: {"exit": <rc>, "ended_utc": "..."}.
  - poll(pid, status) reports RUNNING (pid alive, no status), DONE <rc> (status present), or LOST
    (pid dead, no status). LOST is a fail-closed condition for the caller.

CLI:
  run_detached.py launch --log L [--status S] -- CMD...     # prints launch-record JSON, exits 0
  run_detached.py exec   --status S -- CMD...               # internal: runs CMD, writes status, exits rc
  run_detached.py poll   --pid N --status S                 # prints RUNNING | DONE <rc> | LOST

Importable:
  launch(cmd: list[str], log_path: str, status_path: str | None = None) -> dict
  poll(pid: int, status_path: str) -> str
  read_status(status_path: str) -> int | None     # exit code, or None if not yet written
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path: str, obj: dict) -> None:
    """Write JSON atomically: temp file in the same dir, then os.replace (atomic on POSIX)."""
    tmp = path + ".tmp.%d" % os.getpid()
    with open(tmp, "w") as f:
        json.dump(obj, f, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_status(status_path: str) -> int | None:
    """Return the captured exit code, or None if the status file is not present / not yet complete."""
    if not os.path.exists(status_path):
        return None
    try:
        with open(status_path) as f:
            obj = json.load(f)
        return int(obj["exit"])
    except Exception:
        # Present but unreadable/incomplete -> treat as not-yet-done (caller's timeout/LOST handles it).
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but not ours
    return True


def poll(pid: int, status_path: str) -> str:
    """RUNNING (pid alive, no status) | DONE <rc> (status present) | LOST (pid dead, no status)."""
    rc = read_status(status_path)
    if rc is not None:
        return "DONE %d" % rc
    if _pid_alive(pid):
        return "RUNNING"
    return "LOST"


def launch(cmd: list[str], log_path: str, status_path: str | None = None) -> dict:
    """Launch cmd detached. Returns a launch record dict; does NOT wait. The status sidecar
    "<log>.status" (or status_path) will hold the exit code once the job finishes."""
    if status_path is None:
        status_path = log_path + ".status"
    # Pre-clear a stale status so poll() cannot read an old verdict for this fresh launch.
    try:
        if os.path.exists(status_path):
            os.remove(status_path)
    except OSError:
        pass
    os.makedirs(os.path.dirname(os.path.abspath(log_path)) or ".", exist_ok=True)
    logf = open(log_path, "ab", buffering=0)
    try:
        devnull = open(os.devnull, "rb")
        argv = [sys.executable, os.path.abspath(__file__), "exec", "--status", status_path, "--", *cmd]
        p = subprocess.Popen(
            argv,
            stdin=devnull,
            stdout=logf,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,   # detach: own session + process group
        )
    finally:
        logf.close()
    return {
        "pid": p.pid,
        "log": os.path.abspath(log_path),
        "status": os.path.abspath(status_path),
        "command": cmd,
        "started_utc": _utc(),
    }


def _exec(status_path: str, cmd: list[str]) -> int:
    """Internal: run cmd (stdout/stderr already redirected to the log by the parent), capture rc,
    write the status sidecar atomically, return rc."""
    rc = 1
    try:
        rc = subprocess.call(cmd)   # inherits our stdout/stderr (the log)
    except FileNotFoundError:
        sys.stderr.write("run_detached exec: command not found: %r\n" % (cmd,))
        rc = 127
    except Exception as e:  # noqa: BLE001 - any failure must still produce a durable status
        sys.stderr.write("run_detached exec: %s: %s\n" % (type(e).__name__, e))
        rc = 1
    finally:
        _atomic_write_json(status_path, {"exit": int(rc), "ended_utc": _utc()})
    return rc


def _split_cmd(argv: list[str]) -> tuple[dict, list[str]]:
    """Split argv at the '--' separator into (flags, command)."""
    if "--" not in argv:
        sys.stderr.write("run_detached: missing '--' separator before command\n")
        sys.exit(2)
    i = argv.index("--")
    flags_list, cmd = argv[:i], argv[i + 1:]
    flags: dict = {}
    j = 0
    while j < len(flags_list):
        a = flags_list[j]
        if a.startswith("--"):
            flags[a[2:]] = flags_list[j + 1] if j + 1 < len(flags_list) else ""
            j += 2
        else:
            j += 1
    return flags, cmd


def main(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write(__doc__ or "")
        return 2
    mode, rest = argv[0], argv[1:]
    if mode == "launch":
        flags, cmd = _split_cmd(rest)
        if not cmd:
            sys.stderr.write("run_detached launch: empty command\n")
            return 2
        rec = launch(cmd, flags.get("log") or "detached.log", flags.get("status"))
        print(json.dumps(rec, sort_keys=True))
        return 0
    if mode == "exec":
        flags, cmd = _split_cmd(rest)
        status = flags.get("status")
        if not status or not cmd:
            sys.stderr.write("run_detached exec: --status and command required\n")
            return 2
        return _exec(status, cmd)
    if mode == "poll":
        # poll --pid N --status S
        flags: dict = {}
        j = 0
        while j < len(rest):
            if rest[j].startswith("--"):
                flags[rest[j][2:]] = rest[j + 1] if j + 1 < len(rest) else ""
                j += 2
            else:
                j += 1
        if "pid" not in flags or "status" not in flags:
            sys.stderr.write("run_detached poll: --pid and --status required\n")
            return 2
        print(poll(int(flags["pid"]), flags["status"]))
        return 0
    sys.stderr.write("run_detached: unknown mode %r (launch|exec|poll)\n" % mode)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
