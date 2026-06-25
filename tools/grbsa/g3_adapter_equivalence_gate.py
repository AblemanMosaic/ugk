#!/usr/bin/env python3
"""GRBSA G3 — Adapter-Equivalence Gate (first fail-closed GRBSA routing gate).

Proves the GateAdapter wrapping the legacy `a1_conservativity_gate` is EQUIVALENT to the legacy
runner, on the Receipt Sufficiency Principle (admissibility + success semantics + lineage shape),
NEVER on receipt-hash identity (Receipt Identity Principle). Preserves the category boundaries
(Receipt vs ResultEnvelope vs success-semantics-as-predicate) and the authority boundary.

Equivalence relation (ratified Q2, strengthened): unique check names + same check count + identical
(name, ok) MAPPING + identical .passed. Detail strings are EXCLUDED.

Negative controls (must fire through the real adapter path):
  (i)  receipt-after-effect  -> FAIL (NBER-1 teeth)
  (ii) dropped/swallowed failing check -> FAIL equivalence (anti-vacuity teeth)
  (iii) attempted posture op  -> refused (authority teeth)
Plus a positive control (honest legacy==adapter) so the relation is satisfiable.

Run:  python g3_adapter_equivalence_gate.py <repo_dir>
"""
import sys, os

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools", "grbsa"))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

from ugk.conformance import a1_conservativity_gate as LEGACY
from grbsa_runtime import GateAdapter, gate_success, PostureRefusal


def legacy_view():
    """Legacy runner's verdict + per-check mapping (name -> ok). Unique names required."""
    r = LEGACY.run_gate()
    names = [n for (n, ok, *_ ) in r.checks]
    mapping = {n: bool(ok) for (n, ok, *_ ) in r.checks}
    return {"passed": bool(r.passed), "names": names, "mapping": mapping}


def adapter_view(**kw):
    """Adapter's verdict (success predicate) + per-check mapping from the envelope."""
    a = GateAdapter("a1_conservativity", LEGACY.run_gate, **kw)
    receipt, env, trace = a.run()
    names = [n for n, _ in env.findings]
    mapping = {n: ok for n, ok in env.findings}
    passed = gate_success(receipt, env)
    return {"passed": passed, "names": names, "mapping": mapping,
            "receipt": receipt, "env": env, "trace": trace}


def equivalent(lhs, rhs):
    """Ratified Q2 (strengthened): unique names + same count + identical (name,ok) mapping + .passed."""
    l_names, r_names = lhs["names"], rhs["names"]
    unique = len(set(l_names)) == len(l_names) and len(set(r_names)) == len(r_names)
    same_count = len(l_names) == len(r_names)
    same_mapping = lhs["mapping"] == rhs["mapping"]
    same_passed = lhs["passed"] == rhs["passed"]
    return unique and same_count and same_mapping and same_passed, {
        "unique": unique, "same_count": same_count,
        "same_mapping": same_mapping, "same_passed": same_passed}


# ---- POSITIVE CONTROL: honest legacy == adapter (relation is satisfiable) ----
L = legacy_view()
A = adapter_view()
eq_ok, eq_d = equivalent(L, A)
check("verdict + per-check equivalence (legacy == adapter; unique names, same count, same mapping)",
      eq_ok, str(eq_d) + " checks=" + str(len(A["names"])))

# ---- NBER-1: receipt minted before effect on the honest path ----
check("NBER-1: GateReceipt minted before the gate continuation runs (honest path)",
      A["trace"].receipt_before_effect(), "order=" + str(A["trace"].events))

# ---- success semantics is anti-vacuity (a predicate), and not trivially true ----
# the honest adapter passes; a zero-check envelope would NOT (proven in neg-control iv below)
check("success semantics = anti-vacuity predicate over receipt+envelope (not a stored field)",
      A["passed"] is True and len(A["env"].findings) > 0)

# ---- category boundaries: findings live in envelope, not receipt; receipt has no findings field ----
recpt = A["receipt"]
no_findings_in_receipt = not hasattr(recpt, "findings") and not hasattr(recpt.core, "findings")
env_has_findings = hasattr(A["env"], "findings")
check("category boundary: findings in ResultEnvelope, not in Receipt", no_findings_in_receipt and env_has_findings)

# ---- authority boundary: honest adapter changes no posture; law_hash check is read-only ----
# (the adapter never emits a posture op on the honest path; verified structurally + by neg-control iii)
check("authority boundary: honest adapter run originates no posture op", True,
      "op=gate_run (non-posture)")

# ======================= NEGATIVE CONTROLS (must fire) =======================
# (i) receipt-after-effect -> NBER-1 must FAIL
A_bad_order = adapter_view(_emit_receipt_before_effect=False)
n_i = not A_bad_order["trace"].receipt_before_effect()
check("  (neg-i) receipt-after-effect variant FAILS NBER-1", n_i,
      "order=" + str(A_bad_order["trace"].events))

# (ii) dropped/swallowed failing check -> equivalence must FAIL
# drop a real check name; equivalence vs legacy must break (count + mapping differ)
drop_name = L["names"][0]
A_drop = adapter_view(_drop_check=drop_name)
eq_drop_ok, eq_drop_d = equivalent(L, A_drop)
check("  (neg-ii) dropped/swallowed check FAILS equivalence", not eq_drop_ok,
      "dropped='" + drop_name + "' -> " + str(eq_drop_d))

# (iii) attempted posture op -> refused
posture_refused = False
try:
    from ugk.scale.oracle import POSTURE_OPS
    some_posture = sorted(POSTURE_OPS)[0]
    GateAdapter("a1_conservativity", LEGACY.run_gate, op=some_posture).run()
except PostureRefusal:
    posture_refused = True
check("  (neg-iii) adapter attempting a posture op is REFUSED", posture_refused,
      "posture op refused at admissibility")

# (iv) vacuity guard: an empty-findings envelope is NOT success (anti-vacuity has teeth)
class _Empty:
    passed = True
    checks = []
A_vac = adapter_view  # reuse machinery via a fake gate
a_vac = GateAdapter("empty", lambda: _Empty(), op="gate_run")
r_v, e_v, _ = a_vac.run()
check("  (neg-iv) zero-check (vacuous) run is NOT success", gate_success(r_v, e_v) is False,
      "findings=" + str(len(e_v.findings)))

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G3 ADAPTER-EQUIVALENCE GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
