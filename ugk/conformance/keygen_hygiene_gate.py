"""ugk/conformance/keygen_hygiene_gate.py — Phase 14/17 keygen output contract. GATE_GROUP = "structural" """
def run():
    # Verifies the keygen output contract. Calls ugk.cli.main(["keygen", ...]) IN-PROCESS, capturing
    # BOTH stdout and stderr (the SENSITIVE/PRIVATE warning is on stderr), instead of spawning
    # interpreters. keygen is store-free (identity creation), so in-process is behavior-identical;
    # --write-secure still writes a real 0o600 file into the test's TemporaryDirectory.
    import os, stat, json, tempfile, io, contextlib
    from ugk.cli import main as _cli_main
    def _cli(*argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = _cli_main(list(argv))
        return rc, out.getvalue(), err.getvalue()
    fails = []
    # Default: pubkey only, no privkey
    rc, out, err = _cli("keygen")
    try:
        d = json.loads(out)
        if "privkey_hex" in d: fails.append("Default keygen exposes privkey_hex in stdout")
        if "pubkey_hex" not in d: fails.append("Default keygen missing pubkey_hex")
    except Exception as e: fails.append(f"Default keygen JSON parse failed: {e}")
    # --show-private: privkey on stdout, warning on stderr
    rc, out, err = _cli("keygen", "--show-private")
    try:
        d2 = json.loads(out)
        if "privkey_hex" not in d2: fails.append("--show-private missing privkey_hex")
        if "SENSITIVE" not in err and "PRIVATE" not in err:
            fails.append("--show-private missing warning on stderr")
    except Exception as e: fails.append(f"--show-private JSON parse failed: {e}")
    # --write-secure: POSIX file at 0o600; Windows fails closed because this
    # stdlib-only build does not install user-only ACLs.
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "test_key.json")
        rc, out, err = _cli("keygen", "--write-secure", path)
        if os.name == "nt":
            if rc == 0:
                fails.append("--write-secure: Windows path should fail closed")
            if os.path.exists(path):
                fails.append("--write-secure: Windows fail-closed path created a key file")
            if "Windows" not in err and "ACL" not in err:
                fails.append("--write-secure: Windows fail-closed path missing ACL explanation")
        else:
            if rc != 0: fails.append(f"--write-secure failed: {err}")
            elif not os.path.exists(path): fails.append("--write-secure: file not created")
            else:
                mode = stat.S_IMODE(os.stat(path).st_mode)
                if mode != 0o600: fails.append(f"--write-secure: mode {oct(mode)} != 0o600")
            rc, out, err = _cli("keygen", "--write-secure", path)
            if rc == 0: fails.append("--write-secure: should refuse to overwrite existing file")
    ok = not fails
    return ok, ("Keygen: default=pubkey-only; --show-private warns; --write-secure is 0o600 on POSIX and fails closed on Windows." if ok else "; ".join(fails))
if __name__ == "__main__":
    ok, detail = run(); print(f"keygen_hygiene_gate: {'PASS' if ok else 'FAIL'}  {detail}")
