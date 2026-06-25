#!/usr/bin/env python3
"""Read-only: internal ugk import dependency summary (no external deps mapped)."""
import os, re, collections
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ugk")
edges = collections.Counter()
pat = re.compile(r"^\s*(?:from|import)\s+ugk\.([a-zA-Z_][\w.]*)")
for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d != "__pycache__"]
    for f in fns:
        if not f.endswith(".py"): continue
        mod = os.path.relpath(os.path.join(dp, f), root)
        for line in open(os.path.join(dp, f), encoding="utf-8", errors="ignore"):
            m = pat.match(line)
            if m: edges[m.group(1).split(".")[0]] += 1
print("most-imported internal ugk modules:")
for mod, n in edges.most_common(15): print(f"  {n:4d}  ugk.{mod}")
