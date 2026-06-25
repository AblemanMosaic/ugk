#!/usr/bin/env python3
"""GRBSA G5 — ExecutionAdapter Equivalence Gate (highest-risk).

Proves the ExecutionAdapter OBSERVES a real founded execute() equivalently to a direct call, on the
Receipt Sufficiency Principle (admissibility + success semantics + lineage shape), never receipt-hash
identity. The adapter mints NO receipt, originates NO authority, founds NO kernel, edits NO ugk/.

Target (ratified Q1): op='crp_evidence' on a freshly constructed kernel, gate=True, trivial effect —
the simplest existing conformance-style execution; no extra authority invented.

Run:  python g5_execution_adapter_gate.py <repo_dir>
"""
import sys, os

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools", "grbsa"))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

from ugk.kernel import GovernanceKernel, GateRefusal, GovernanceNotFounded, EffectAtomicity
from grbsa_runtime import ExecutionAdapter, execution_success, PostureRefusal

OP = "crp_evidence"

# r111 (AD-42): declare the atomicity class ONCE and feed it to BOTH views so the equivalence stays
# "same call, two views", never adapter-vs-direct with different classes. The adapter side reads CLS
# (an ExecutionAdapter construction is NOT scanned by the effect-declaration probe, so a constant is
# fine there). The direct-execute baseline must use the SAME class as a static literal -- the probe
# recognizes effect_atomicity only as a literal/seam at an execute() callsite by design -- so it is
# pinned to CLS by the assertion below. Changing the baseline class means changing CLS, the direct
# literal, AND this assertion together; a half-change fails loudly right here.
CLS = EffectAtomicity.NON_ATOMIC
assert CLS is EffectAtomicity.NON_ATOMIC, "g5 atomicity-class drift: CLS must equal the direct-execute baseline literal"


def direct_execute():
    """Direct execute() view: receipts written + failed flag + admit verdict."""
    k = GovernanceKernel(); store = k._store
    b = store.receipt_count()
    # r111 (AD-42): static NON_ATOMIC literal == CLS (asserted at load). The probe recognizes a literal/
    # seam at an execute() callsite; this is the direct baseline that the adapter side (CLS) is pinned to.
    k.execute(op=OP, authority="adm", parameters={}, gate=lambda: True, effect=lambda: {"ok": True}, effect_atomicity=EffectAtomicity.NON_ATOMIC)
    a = store.receipt_count()
    outcome = [r for r in store.all_receipts() if getattr(r, "op", None) == OP]
    failed = bool(getattr(outcome[-1], "failed", False)) if outcome else True
    return {"written": a - b, "failed": failed, "admit": True}


def adapter_execute(**kw):
    k = GovernanceKernel()
    a = ExecutionAdapter(k, op=OP, authority="adm", parameters={},
                         gate=lambda: True, effect=lambda: {"ok": True}, effect_atomicity=CLS, **kw)
    receipt, env, trace = a.run()
    return {"written": env.receipts_written, "failed": env.failed,
            "admit": receipt.gate_outcome == "admit",
            "receipt": receipt, "env": env, "trace": trace,
            "success": execution_success(receipt, env)}


def equivalent(d, a):
    same_admit = d["admit"] == a["admit"]
    same_failed = d["failed"] == a["failed"]
    same_written = d["written"] == a["written"]      # lineage shape: same # of receipts written
    return same_admit and same_failed and same_written, {
        "same_admit": same_admit, "same_failed": same_failed, "same_written": same_written}


# ---- POSITIVE CONTROL: founded, authorized, gate-true execute() equivalent direct vs adapter ----
D = direct_execute(); A = adapter_execute()
eq_ok, eq_d = equivalent(D, A)
check("equivalence: direct execute() == adapter (admit + failed + receipts-written shape)", eq_ok,
      str(eq_d) + " written=" + str(A["written"]))

# ---- adapter run is successful on the honest founded path ----
check("execution_success on honest founded path (gate admit, not failed, receipt written)",
      A["success"] is True and A["written"] >= 1)

# ---- adapter MINTS NO receipt: receipts_written equals what direct execute() wrote ----
check("adapter mints NO parallel receipt (observed count == direct execute count)",
      A["written"] == D["written"], "adapter=" + str(A["written"]) + " direct=" + str(D["written"]))

# ---- NBER-1 is owned by execute(): receipt recorded before effect in the adapter trace ----
check("NBER-1: receipt observed before effect (execute() owns the order)",
      A["trace"].receipt_before_effect(), "order=" + str(A["trace"].events))

# ---- category boundary: execution findings in envelope, not receipt ----
check("category boundary: failed/receipts_written in ResultEnvelope, not Receipt",
      not hasattr(A["receipt"], "failed") and hasattr(A["env"], "failed"))

# ======================= NEGATIVE CONTROLS (must fire) =======================
# (i) gate refusal -> first-class: valid receipt, execution_success False (NOT an error)
k = GovernanceKernel()
ref = ExecutionAdapter(k, op=OP, authority="adm", parameters={"r": True},
                       gate=lambda: False, effect=lambda: None, effect_atomicity=CLS)  # CLS so gate=False -> GateRefusal, not UndeclaredEffect
rr, re_env, rtr = ref.run()
refused_first_class = (rr.gate_outcome == "refuse" and execution_success(rr, re_env) is False
                       and isinstance(rr, type(A["receipt"])))
check("  (neg-i) gate refusal is first-class: valid receipt, execution_success=False",
      refused_first_class, "gate_outcome=" + rr.gate_outcome)

# (ii) unfounded-kernel: a non-universal op on a kernel must raise GovernanceNotFounded through direct;
#      the adapter must surface the SAME refusal (it must not 'helpfully' found the kernel).
#      crp_evidence is a universal op (works uninitialized), so use a Tier-2 op to exercise founding.
TIER2_OP = "amend_constitution"
k2 = GovernanceKernel()
direct_notfounded = False
try:
    k2.execute(op=TIER2_OP, authority="adm", parameters={}, gate=lambda: True, effect=lambda: None, effect_atomicity=EffectAtomicity.NON_ATOMIC)  # == CLS (direct baseline literal)
except GovernanceNotFounded:
    direct_notfounded = True
except Exception:
    direct_notfounded = False
k3 = GovernanceKernel()
adapter_notfounded = False
a_nf = ExecutionAdapter(k3, op=TIER2_OP, authority="adm", parameters={}, gate=lambda: True, effect=lambda: None, effect_atomicity=CLS)  # CLS so unfounded -> GovernanceNotFounded, not UndeclaredEffect
rnf, enf, _ = a_nf.run()
adapter_notfounded = (rnf.gate_outcome == "refuse" and "GovernanceNotFounded" in str(rnf.core.evaluation))
check("  (neg-ii) unfounded Tier-2 op refused identically (adapter does not found the kernel)",
      direct_notfounded and adapter_notfounded,
      "direct=" + str(direct_notfounded) + " adapter=" + str(adapter_notfounded))

# (iii) authority expansion -> refused (adapter tries to originate authority it wasn't given)
auth_refused = False
try:
    k4 = GovernanceKernel()
    ExecutionAdapter(k4, op=OP, authority="adm", gate=lambda: True, effect=lambda: None,
                     effect_atomicity=CLS, _attempt_authority=True).run()  # CLS declared for consistency; PostureRefusal fires first
except PostureRefusal:
    auth_refused = True
check("  (neg-iii) adapter attempting to originate execution authority is REFUSED", auth_refused)

# (iv) posture op as the adapter's own op -> refused
posture_refused = False
try:
    from ugk.scale.oracle import POSTURE_OPS
    k5 = GovernanceKernel()
    ExecutionAdapter(k5, op=OP, authority="adm", gate=lambda: True, effect=lambda: None,
                     effect_atomicity=CLS, adapter_op=sorted(POSTURE_OPS)[0]).run()  # CLS declared for consistency; PostureRefusal fires first
except PostureRefusal:
    posture_refused = True
check("  (neg-iv) adapter posture op is REFUSED", posture_refused)

# (v) vacuity: an envelope with zero receipts written is NOT success (real predicate path)
from grbsa_runtime import ExecutionReceipt, ExecutionResultEnvelope
from grbsa_runtime.gate_adapter import ReceiptCore, ResultEnvelopeCore
vr = ExecutionReceipt(core=ReceiptCore({}, (), (), {}, "admitted", {}), op=OP,
                      authority_ref="x", gate_outcome="admit")
ve = ExecutionResultEnvelope(core=ResultEnvelopeCore("pass", (), {}, "", {}),
                             effect_result_ref="", failed=False, receipts_written=0)
check("  (neg-v) zero-receipt (vacuous) execution is NOT success", execution_success(vr, ve) is False)

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G5 EXECUTION-ADAPTER GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
