#!/usr/bin/env python3
"""Full check: M2 vectors + 78 gates + ρ fixtures. PYTHONPATH=. python tests/run_full.py"""
import os, sys, subprocess, tempfile
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run(mod):
    env = {**os.environ, "PYTHONPATH": root, "UGK_GENESIS_DIR": tempfile.mkdtemp()}
    return subprocess.call([sys.executable, "-m", mod], env=env)
rc = 0
for mod in ("ugk.conformance.m2_vectors_runner",
            "ugk.conformance.run_gates_batch",
            "ugk.conformance.rho_fixtures"):
    rc |= run(mod)
print("full check:", "PASS" if rc == 0 else "FAIL")
sys.exit(rc)
