#!/usr/bin/env python3
"""Read-only: enumerate refusal/exception classes the substrate can raise."""
import os, re, collections
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ugk")
refusals = collections.Counter()
pat = re.compile(r"raise\s+(\w*(?:Refusal|NotFounded|UndeclaredOp|Error|Internal)\w*)")
for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d != "__pycache__"]
    for f in fns:
        if not f.endswith(".py") or "conformance" in dp: continue
        for line in open(os.path.join(dp, f), encoding="utf-8", errors="ignore"):
            for m in pat.findall(line): refusals[m] += 1
print("refusal / fail-closed exception classes raised in substrate (non-test):")
for cls, n in refusals.most_common(): print(f"  {n:3d}  {cls}")
