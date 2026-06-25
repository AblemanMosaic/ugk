"""ugk/conformance/readme_freshness_gate.py - README FRESHNESS (full artifact matches source).
GATE_GROUP = "structural"

Strengthened (r163): proves the SHIPPED README.md equals the FULL projection of current sources
(via the canonical generator readme_gen.py), not merely that the gate-count strings are present.

Determinism note: readme_gen embeds a `ugk status` snapshot built from kernel module constants
(GOVERNOR_PUBKEY_HEX / _PHASE_CODE). Inside the single-interpreter batch those globals have already
been MUTATED by an earlier founded/charter step, so executing the generator IN-PROCESS would (a) read
a founded snapshot that diverges from the shipped (unfounded) README and (b) contaminate shared state
relied on by later gates. The check is therefore run in an ISOLATED SUBPROCESS with a clean genesis
dir, using the generator's own `--check`: deterministic (fresh unfounded constants == shipped) and
side-effect-free w.r.t. the batch. `--check` regenerates the FULL README and exits non-zero on any
drift, so this fails on real staleness — not just gate-count strings.

If the top-level readme_gen.py is not shipped (package-only install), freshness-vs-source is not
evaluable here and the gate returns NOT_ESTABLISHED.
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
import ugk
from ugk.conformance import NOT_ESTABLISHED


def run():
    root = Path(ugk.__file__).resolve().parent.parent
    rg_path = root / "readme_gen.py"
    readme_path = root / "README.md"
    if not rg_path.exists():
        return NOT_ESTABLISHED, (
            "README freshness: top-level readme_gen.py not present in this deployment; "
            "freshness-vs-source is not evaluable here."
        )
    if not readme_path.exists():
        return False, "README.md absent (cannot prove freshness)"
    # Isolated subprocess: clean genesis dir so the generator reads fresh (unfounded) kernel constants,
    # matching the shipped README. No in-process global mutation; cannot affect sibling gates.
    with tempfile.TemporaryDirectory(prefix="readme-fresh-") as tmp:
        env = dict(os.environ, UGK_GENESIS_DIR=tmp)
        env.pop("PYTHONUTF8", None)  # determinism: do not let caller UTF-8 mode change the generator path
        proc = subprocess.run([sys.executable, str(rg_path), "--check"],
                              cwd=str(root), env=env, capture_output=True, text=True, timeout=120)
    out = (proc.stdout + proc.stderr).strip().splitlines()
    tail = out[-1] if out else ""
    if proc.returncode == 0:
        return True, "README.md is FRESH: full generated projection (readme_gen --check) matches the shipped artifact."
    return False, ("README.md STALE vs full generated projection (run `python readme_gen.py`): " + tail)


if __name__ == "__main__":
    ok, detail = run()
    tag = "PASS" if ok is True else ("N/EST" if ok is NOT_ESTABLISHED else "FAIL")
    print(f"readme_freshness_gate: {tag}  {detail}")
