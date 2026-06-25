"""ugk/conformance/genesis_path_gate.py — UGK_GENESIS_DIR env override honored.

Proves the genesis path is deployer-configurable end-to-end (R2 fix for
pip-installed deployments where the default site-packages-relative path is
not writable):

  1. _paths.genesis_dir() returns the UGK_GENESIS_DIR value when set.
  2. With UGK_GENESIS_DIR pointed at a temp dir, write_charter_artifacts
     lands the GENESIS_KEY.pub + DEPLOYMENT_MANIFEST.json in that temp dir.
  3. In a fresh subprocess with UGK_GENESIS_DIR pointed at the chartered
     temp dir, kernel identity loads from there (pubkey == fixture, NOT
     the sentinel). The fail-closed sentinel only applies when nothing is
     chartered — not when the deployer has correctly set the env var.
  4. With env unset, the default fallback equals the historical hardcoded
     path (package-adjacent ../genesis) — no behavior drift for existing
     deployments.
"""


def run():
    import os, subprocess, sys, tempfile, shutil
    from pathlib import Path

    from ugk._paths import genesis_dir
    from ugk.charter import DeploymentManifest, write_charter_artifacts
    from ugk.conformance._fixture import fixture_pubkey
    fails = []

    pkg_root = Path(__file__).resolve().parent.parent.parent

    # --- 1. env override honored by resolver ---
    with tempfile.TemporaryDirectory() as td:
        os.environ["UGK_GENESIS_DIR"] = td
        try:
            resolved = genesis_dir()
            if str(resolved) != td:
                fails.append(f"resolver returned {resolved!r}, expected {td!r}")

            # --- 2. charter writes to env-pointed dir ---
            m = DeploymentManifest.create(
                fixture_pubkey(), "genesis-path-gate", "conformance", "trace_only")
            write_charter_artifacts(m, force=False)
            if not (Path(td) / "GENESIS_KEY.pub").exists():
                fails.append("charter did not write GENESIS_KEY.pub to UGK_GENESIS_DIR")
            if not (Path(td) / "DEPLOYMENT_MANIFEST.json").exists():
                fails.append("charter did not write DEPLOYMENT_MANIFEST.json to UGK_GENESIS_DIR")

            # --- 3. kernel identity loads from env-pointed dir (subprocess: import-time) ---
            env = dict(os.environ); env["UGK_GENESIS_DIR"] = td
            env["PYTHONPATH"] = str(pkg_root)
            r = subprocess.run(
                [sys.executable, "-c",
                 "from ugk.kernel import GOVERNOR_PUBKEY_HEX; print(GOVERNOR_PUBKEY_HEX)"],
                capture_output=True, text=True, env=env, timeout=120)
            loaded = r.stdout.strip()
            if loaded.startswith("GOVERNOR_KEY_UNSET"):
                fails.append("kernel loaded sentinel despite UGK_GENESIS_DIR pointing at chartered tempdir")
            elif loaded != fixture_pubkey():
                fails.append(f"kernel loaded {loaded[:16]!r}…, expected fixture {fixture_pubkey()[:16]!r}…")
        finally:
            os.environ.pop("UGK_GENESIS_DIR", None)

    # --- 4. default fallback unchanged ---
    default = genesis_dir()
    historic = Path(__file__).resolve().parent.parent.parent / "ugk" / "_paths.py"
    expected_default = historic.parent.parent / "genesis"
    if default != expected_default:
        fails.append(f"default fallback {default!r} != historic {expected_default!r}")

    ok = not fails
    return ok, (
        "UGK_GENESIS_DIR honored end-to-end: resolver, charter writes, kernel "
        "identity loads from env path in fresh subprocess; default fallback "
        "byte-identical to historic hardcoded path." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"genesis_path_gate: {'PASS' if ok else 'FAIL'}  {detail}")
