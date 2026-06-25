#!/usr/bin/env python3
"""GRBSA G4a — GateAdapter Generality Gate (second gate proof).

Proves the GateAdapter is NOT a1-specific by wrapping a SECOND, structurally-DIFFERENT conformance
gate — `determinism_gate`, whose native result is a (ok, detail) verdict tuple, not a1's GateResult
per-check triples — as a receipt-bound continuation, equivalent to its legacy runner, with the same
discipline as G3: equivalence relation (unique names + same count + identical (name,ok) mapping +
verdict), NBER-1, anti-vacuity, authority boundary. No ugk/ change; legacy gate unmodified.

Run:  python g4a_adapter_generality_gate.py <repo_dir>
"""
import sys, os

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools", "grbsa"))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

from ugk.conformance import determinism_gate as LEGACY
from grbsa_runtime import GateAdapter, gate_success, PostureRefusal, verdict_tuple_normalizer

GATE_ID = "determinism"
NORM = verdict_tuple_normalizer(GATE_ID)


def legacy_view():
    """Legacy (ok, detail) -> the SAME canonical mapping the adapter will produce (one synthetic
    verdict check). Detail string excluded (prose)."""
    ok, _detail = LEGACY.run()
    name = GATE_ID + ":verdict"
    return {"passed": bool(ok), "names": [name], "mapping": {name: bool(ok)}}


def adapter_view(**kw):
    a = GateAdapter(GATE_ID, LEGACY.run, normalizer=NORM, **kw)
    receipt, env, trace = a.run()
    names = [n for n, _ in env.findings]
    mapping = {n: ok for n, ok in env.findings}
    return {"passed": gate_success(receipt, env), "names": names, "mapping": mapping,
            "receipt": receipt, "env": env, "trace": trace}


def equivalent(lhs, rhs):
    l, r = lhs["names"], rhs["names"]
    unique = len(set(l)) == len(l) and len(set(r)) == len(r)
    same_count = len(l) == len(r)
    same_mapping = lhs["mapping"] == rhs["mapping"]
    same_passed = lhs["passed"] == rhs["passed"]
    return unique and same_count and same_mapping and same_passed, {
        "unique": unique, "same_count": same_count, "same_mapping": same_mapping, "same_passed": same_passed}


# ---- the gate is structurally different from a1 (proves generality) ----
raw = LEGACY.run()
check("target gate has a DIFFERENT result shape than a1 ((ok,detail) tuple, not GateResult)",
      isinstance(raw, tuple) and isinstance(raw[0], bool) and not hasattr(raw, "checks"),
      "shape=(%s, %s)" % (type(raw[0]).__name__, type(raw[1]).__name__))

# ---- POSITIVE CONTROL: honest legacy == adapter ----
L = legacy_view(); A = adapter_view()
eq_ok, eq_d = equivalent(L, A)
check("verdict + per-check equivalence (legacy == adapter via verdict-tuple normalizer)", eq_ok,
      str(eq_d) + " checks=" + str(len(A["names"])))

# ---- NBER-1 honest path ----
check("NBER-1: GateReceipt minted before continuation runs (honest path)",
      A["trace"].receipt_before_effect(), "order=" + str(A["trace"].events))

# ---- success semantics = anti-vacuity predicate, not trivially true ----
check("success semantics = anti-vacuity predicate over receipt+envelope (not a stored field)",
      A["passed"] is True and len(A["env"].findings) > 0)

# ---- category boundary: findings in envelope, not receipt ----
check("category boundary: findings in ResultEnvelope, not Receipt",
      not hasattr(A["receipt"], "findings") and not hasattr(A["receipt"].core, "findings")
      and hasattr(A["env"], "findings"))

# ---- A1 path still works through the SAME adapter (generality, both shapes) ----
from ugk.conformance import a1_conservativity_gate as A1
a1_adapter = GateAdapter("a1_conservativity", A1.run_gate)  # default normalizer (.checks)
r_a1, e_a1, t_a1 = a1_adapter.run()
a1_legacy = A1.run_gate()
a1_map_adapter = {n: ok for n, ok in e_a1.findings}
a1_map_legacy = {n: bool(ok) for (n, ok, *_ ) in a1_legacy.checks}
check("SAME GateAdapter still wraps a1 (GateResult shape) equivalently", a1_map_adapter == a1_map_legacy
      and gate_success(r_a1, e_a1) == bool(a1_legacy.passed),
      "a1 checks=" + str(len(e_a1.findings)))

# ======================= NEGATIVE CONTROLS (must fire) =======================
# (i) receipt-after-effect -> NBER-1 must FAIL
A_bad = adapter_view(_emit_receipt_before_effect=False)
check("  (neg-i) receipt-after-effect variant FAILS NBER-1",
      not A_bad["trace"].receipt_before_effect(), "order=" + str(A_bad["trace"].events))

# (ii) dropped/swallowed check -> equivalence must FAIL
A_drop = adapter_view(_drop_check=GATE_ID + ":verdict")
eq_drop_ok, eq_drop_d = equivalent(L, A_drop)
check("  (neg-ii) dropped/swallowed check FAILS equivalence", not eq_drop_ok, str(eq_drop_d))

# (iii) attempted posture op -> refused
refused = False
try:
    from ugk.scale.oracle import POSTURE_OPS
    GateAdapter(GATE_ID, LEGACY.run, normalizer=NORM, op=sorted(POSTURE_OPS)[0]).run()
except PostureRefusal:
    refused = True
check("  (neg-iii) adapter attempting a posture op is REFUSED", refused)

# (iv) vacuous (zero-check) -> NOT success
class _Empty:  # a degenerate normalizer producing zero findings
    pass
a_vac = GateAdapter("empty", LEGACY.run, normalizer=lambda res: [])
r_v, e_v, _ = a_vac.run()
check("  (neg-iv) zero-check (vacuous) run is NOT success", gate_success(r_v, e_v) is False,
      "findings=" + str(len(e_v.findings)))

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G4a ADAPTER-GENERALITY GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
