#!/usr/bin/env python3
"""Read-only package hygiene check. Exit 0 if clean. python tools/hygiene_check.py"""
import os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = []
for dp, dns, fns in os.walk(root):
    if "__pycache__" in dp or "/build" in dp or ".egg-info" in dp:
        bad.append(dp); continue
    for f in fns:
        if f.endswith((".pyc", ".pyo")): bad.append(os.path.join(dp, f))
print(f"hygiene: {'CLEAN' if not bad else str(len(bad))+' violations'}")
for b in bad[:20]: print("  ", os.path.relpath(b, root))
sys.exit(1 if bad else 0)
