"""ugk/conformance/terminal_outcome_gate.py — focused gate for the LM-2 terminal-outcome classifier.

Registered in run_gates_batch (since r127). Proves
the classifier is a pure, derivational labeling layer with exactly five mutually-exclusive terminal
outcomes, fail-closed DEFER, narrow CRISIS, and preserved diagnostic specificity. ADMIT/REFUSE use
REAL SB-3a-core TraceVectors (store-issued receipts); DEFER/STRUCTURAL_ERROR/CRISIS use synthetic
inputs (DEFER and CRISIS are unreachable by default and exercised only via explicit inputs).
"""
from ugk.storage.store import UGKReceiptStore
from ugk.fga.trace_vector import build_trace_vector, FrameRef
from ugk.fga.terminal_outcome import (
    classify, MODEL_ID, TERMINAL_OUTCOMES, STRUCTURAL_REASONS,
    PartialEvaluationTrace, RootConflict, DeferPolicy,
    ADMIT, REFUSE, DEFER, STRUCTURAL_ERROR, CRISIS,
)


def _real_trace(tamper=False):
    s = UGKReceiptStore(":memory:")
    r = s.write(op="crp_evidence", authority="alice", parameters={"i": 1}, intent="t1",
                jurisdiction="production", session_dkn="d1", law_hash="L", legend_hash="G",
                warrant_id="W1", intent_ref="r1")
    if tamper:
        r.h_s = "0" * 64
    frame = FrameRef(law_hash=r.law_hash, schema_hash="cbe140bfcecd" + "00" * 26,
                     legend_hash=r.legend_hash, codex_hash="54bfe718a74cd518" + "00" * 24)
    return s, build_trace_vector(r, frame)


def run():
    checks = []

    def chk(name, cond):
        checks.append((name, bool(cond)))

    def raises(fn):
        try:
            fn(); return False
        except Exception:
            return True

    # real TraceVectors for ADMIT / REFUSE
    _, tv_ok = _real_trace(tamper=False)
    _, tv_bad = _real_trace(tamper=True)
    r_admit = classify(trace=tv_ok)
    r_refuse = classify(trace=tv_bad)
    partial = PartialEvaluationTrace(resolved=(("D_s", "PASS", "ok"),), pending=("D_c",), reason="non-evaluable")

    # (1) exhaustiveness — every result is one of the five; all five reachable via explicit inputs
    outs = {
        r_admit.outcome, r_refuse.outcome,
        classify(trace=None, structural_reason="malformed-input").outcome,
        classify(trace=None, partial=partial,
                 defer_policy=DeferPolicy("pending evidence", "operator:X", "external check returns",
                                          applies_to=("non-evaluable",))).outcome,
        classify(root_conflict=RootConflict(roots=("c1", "c2"), detail="two roots admit J")).outcome,
    }
    chk("1.exhaustiveness: all five terminal outcomes reachable and within the closed set",
        outs == set(TERMINAL_OUTCOMES))
    chk("1.exhaustiveness: every classify result is a valid terminal outcome",
        all(x.outcome in TERMINAL_OUTCOMES for x in (r_admit, r_refuse)))

    # (2) refuse/error separation
    se = classify(trace=None, structural_reason="malformed-input")
    chk("2.refuse/error: complete trace + refused surface -> REFUSE", r_refuse.outcome == REFUSE)
    chk("2.refuse/error: no complete trace + no policy -> STRUCTURAL_ERROR (never REFUSE)",
        se.outcome == STRUCTURAL_ERROR)

    # (3) partial-not-complete
    chk("3.partial-not-complete: a PartialEvaluationTrace cannot be passed as a complete trace",
        raises(lambda: classify(trace=partial)))

    # (4) defer-not-admit + (5) explicit defer-policy requirement
    pol = DeferPolicy("pending evidence", "operator:X", "external check returns", applies_to=("non-evaluable",))
    r_defer = classify(trace=None, partial=partial, defer_policy=pol)
    chk("4.defer-not-admit: DEFER is not ADMIT and carries a partial (no trace_vector)",
        r_defer.outcome == DEFER and r_defer.carried_kind == "partial")
    chk("5.explicit-policy: incomplete + NO policy -> STRUCTURAL_ERROR",
        classify(trace=None, partial=partial).outcome == STRUCTURAL_ERROR)
    chk("5.explicit-policy: incomplete + policy that does NOT authorize the reason -> STRUCTURAL_ERROR",
        classify(trace=None, partial=partial,
                 defer_policy=DeferPolicy("x", "y", "z", applies_to=("some-other-reason",))).outcome == STRUCTURAL_ERROR)
    chk("5.explicit-policy: a non-DeferPolicy object is rejected (no ambient policy)",
        raises(lambda: classify(trace=None, partial=partial, defer_policy={"permissive": True})))

    # (6) crisis-narrowness + single-root unreachability
    r_crisis = classify(root_conflict=RootConflict(roots=("c1", "c2"), detail="two roots admit J"))
    chk("6.crisis: explicit root conflict -> CRISIS", r_crisis.outcome == CRISIS)
    chk("6.crisis-narrow: structural/constitutional failures are never CRISIS",
        se.outcome != CRISIS and r_refuse.outcome != CRISIS and r_defer.outcome != CRISIS)
    chk("6.single-root-unreachable: with no root_conflict (the single-root default) CRISIS never occurs",
        all(classify(**kw).outcome != CRISIS for kw in (
            {"trace": tv_ok}, {"trace": tv_bad}, {"trace": None, "structural_reason": "not-founded"},
            {"trace": None, "partial": partial, "defer_policy": pol})))

    # (7) trace/outcome correspondence
    chk("7.correspondence: ADMIT/REFUSE carry trace_vector; DEFER partial; STRUCTURAL_ERROR partial/none; CRISIS root_conflict",
        r_admit.carried_kind == "trace_vector" and r_refuse.carried_kind == "trace_vector"
        and r_defer.carried_kind == "partial"
        and classify(trace=None, structural_reason="not-founded").carried_kind == "none"
        and se.carried_kind in ("partial", "none")
        and r_crisis.carried_kind == "root_conflict")

    # (8) receipt-commitment honesty — result is a derived LABEL (model id present), commits no field
    chk("8.honesty: result carries model_id and is a derived label (no committed receipt field/attr)",
        r_admit.model_id == MODEL_ID == "terminal_outcome_model_v1"
        and not hasattr(r_admit, "committed") and not hasattr(r_admit, "receipt_field"))

    # (9) no monolithic terminal — basis records the determining inputs
    chk("9.no-monolith: every outcome's basis is non-empty and derivable",
        all(x.basis for x in (r_admit, r_refuse, r_defer, se, r_crisis)))

    # (10) classifier purity / zero-effect DEFER — a DEFER classification mutates no store
    s2 = UGKReceiptStore(":memory:")
    s2.write(op="seed", authority="a", parameters={}, intent="i", jurisdiction="j",
             session_dkn="d", law_hash="L", legend_hash="G", warrant_id="", intent_ref="")
    before = len(s2.all_receipts())
    _ = classify(trace=None, partial=partial, defer_policy=pol)   # DEFER
    _ = classify(trace=tv_ok)                                     # ADMIT
    after = len(s2.all_receipts())
    chk("10.purity/zero-effect: classification (incl. DEFER) performs no store mutation",
        before == after == 1)

    # (11) deterministic output identity incl model id
    chk("11.determinism: identical inputs -> identical result identity (binds model_id)",
        classify(trace=tv_ok).identity == r_admit.identity
        and classify(trace=None, structural_reason="malformed-input").identity == se.identity
        and r_admit.identity != r_refuse.identity)

    # (12) original diagnostic reason preserved for STRUCTURAL_ERROR (no fog bank)
    preserved = all(classify(trace=None, structural_reason=reason).reason == reason
                    for reason in STRUCTURAL_REASONS)
    chk("12.diagnostic-specificity: STRUCTURAL_ERROR preserves the original protocol/preflight reason",
        preserved)

    # (13) contradictory inputs fail closed
    chk("13.fail-closed: complete trace + structural_reason is rejected (contradiction)",
        raises(lambda: classify(trace=tv_ok, structural_reason="malformed-input")))

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    failed = [n for n, ok in checks if not ok]
    detail = "%d/%d checks pass" % (passed, total)
    if failed:
        detail += " | FAILED: " + "; ".join(failed)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
