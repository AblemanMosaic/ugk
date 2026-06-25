#!/usr/bin/env python3
"""Fast check: M2 vectors + A1 conservativity. PYTHONPATH=. python tests/run_fast.py"""
import os, sys, subprocess, tempfile
os.environ.setdefault("UGK_GENESIS_DIR", tempfile.mkdtemp())
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = {**os.environ, "PYTHONPATH": root}
rc = subprocess.call([sys.executable, "-m", "ugk.conformance.m2_vectors_runner"], env=env)
print("fast check:", "PASS" if rc == 0 else "FAIL")
sys.exit(rc)
