#!/usr/bin/env python3
"""GRBSA — Category-Separation Gate.

Proves the anti-collapse property across the three adapter domains (gate / projection / explain): no
domain's success predicate validates another domain's (receipt, envelope) pair. Separation is by an
EXPLICIT domain tag (Option B, ratified) — each predicate returns a CLEAN False on category mismatch,
NOT a raised exception. A raised AttributeError would prove only accidental structural mismatch; a
clean False proves principled separation.

Run:  python category_separation_gate.py <repo_dir>
"""
import sys, os, dataclasses as dc

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools", "grbsa"))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

from grbsa_runtime import (GateAdapter, gate_success, ProjectionAdapter, projection_success,
                           ExplainAdapter, explain_success, ExecutionAdapter, execution_success)
from ugk.conformance import a1_conservativity_gate as A1
from ugk.kernel import GovernanceKernel, EffectAtomicity

# Build one honest (receipt, envelope) per domain.
gr, ge, _ = GateAdapter("a1_conservativity", A1.run_gate).run()
pr, pe, _ = ProjectionAdapter(REPO).run()
er, ee, _ = ExplainAdapter(REPO).run()
_k = GovernanceKernel()
xr, xe, _ = ExecutionAdapter(_k, op="crp_evidence", authority="adm",
                             gate=lambda: True, effect=lambda: {"ok": True}, effect_atomicity=EffectAtomicity.NON_ATOMIC).run()

DOMAINS = {
    "gate":       (gate_success, gr, ge),
    "projection": (projection_success, pr, pe),
    "explain":    (explain_success, er, ee),
    "execution":  (execution_success, xr, xe),
}

# ---- 3 native positives: each predicate accepts its OWN honest pair (non-vacuity of separation) ----
for name, (pred, r, e) in DOMAINS.items():
    check("native positive: " + name + "_success accepts its own honest pair", pred(r, e) is True)

# ---- 6 cross-pair rejections: clean False (NOT an exception) ----
def clean_reject(pred, r, e):
    """True iff pred(r,e) returns the bool False WITHOUT raising. A raise is NOT a clean rejection."""
    try:
        return pred(r, e) is False
    except Exception:
        return False   # raised => not a clean False => fails this gate (Option B requires clean False)

for xname, (pred, _, _) in DOMAINS.items():
    for yname, (_, ry, ey) in DOMAINS.items():
        if xname == yname:
            continue
        ok = clean_reject(pred, ry, ey)
        check("cross-pair: " + xname + "_success rejects " + yname + " pair with CLEAN False", ok,
              "(returns False, no exception)")

# ---- negative control: the tag guard actually does the work ----
# Mis-tag a Gate envelope as 'projection' and feed the (gate_receipt, mis-tagged_env) to gate_success.
# The guard must catch the mismatch and return CLEAN False — proving separation is by TAG, not by
# field shape (the fields are still all present and valid; only the tag is wrong).
mis_ge = dc.replace(ge, domain="projection")
mis_caught = (gate_success(gr, mis_ge) is False)
check("  (neg) mis-tagged envelope (gate->projection) is caught by the tag guard (clean False)",
      mis_caught, "gate_success(gate_receipt, env tagged 'projection') == False")

# Symmetric: mis-tag the RECEIPT.
mis_gr = dc.replace(gr, domain="explain")
check("  (neg) mis-tagged receipt (gate->explain) is caught by the tag guard (clean False)",
      gate_success(mis_gr, ge) is False)

# ---- prove the guard is what rejects, not accidental field absence: a correctly-tagged native pair
#      still PASSES (so the guard isn't just rejecting everything) ----
check("  (control) correctly-tagged native gate pair still passes (guard not over-rejecting)",
      gate_success(gr, ge) is True)

# ---- confirm every receipt/envelope actually carries a domain tag ----
all_tagged = all(hasattr(o, "domain") for o in (gr, ge, pr, pe, er, ee, xr, xe))
tags = {nm: getattr(o, "domain") for nm, o in
        [("gr",gr),("ge",ge),("pr",pr),("pe",pe),("er",er),("ee",ee),("xr",xr),("xe",xe)]}
check("every receipt/envelope carries an explicit domain tag", all_tagged, str(tags))

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA CATEGORY-SEPARATION GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
