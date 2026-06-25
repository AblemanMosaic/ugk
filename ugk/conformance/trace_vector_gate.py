"""ugk/conformance/trace_vector_gate.py — focused gate for the SB-3a-core FGA trace-vector layer.

Narrow claim (NO OVERCLAIM): SB-3a-core makes the existing FOUR committed FGA axes
(h_s/h_c/h_m/h_j) explicit, enumerable, deterministic, frame-bound, and receipt-correspondent.
Only h_s and the whole-body h_body are independently re-derived; h_c/h_m/h_j are surfaced as
committed axes bound by h_r/h_body, NOT recomputed. CGP capability evidence is NOT a
constitutional surface here. A lantern over the existing receipt structure, not a new sky.

Registered in run_gates_batch as of r126 (the gate-count frame move 100 -> 101). Also
runnable standalone for focused SB-3a-core evidence.
"""
import hashlib
from types import SimpleNamespace

from ugk.storage import binding_m2 as _m2
from ugk.storage.store import compute_h_body
from ugk.fga.trace_vector import (
    COMMITTED_SURFACES, COMMITTED_RECEIPT_FIELDS, DecisionSurface, FrameRef, TraceVector,
    build_trace_vector, aggregate, validate_committed_registry, _trace_vector_hash,
    SURFACE_REGISTRY_VERSION, AGGREGATION_OPERATOR_ID, MODE_REDERIVED, MODE_COMMITTED_BODY_BOUND,
    ADMIT, REFUSE, PASS,
)

_LAW = "7f28d36859f195a6" + "00" * 24
_LEGEND = "db3c177d45ebac6c" + "00" * 24
_FRAME = FrameRef(law_hash=_LAW, schema_hash="cbe140bfcecd" + "00" * 26,
                  legend_hash=_LEGEND, codex_hash="1cf6b94c3448500f" + "00" * 24)
_hd = lambda b: hashlib.sha256(b).hexdigest()


def _valid_receipt(**over):
    op = over.get("op", "demo.transition")
    params = over.get("parameters", {"k": "v"})
    fields = dict(
        op=op, authority="dev-fixture", parameters=params, intent="demo",
        jurisdiction="conformance", confidence=1, timestamp=0, failed=False,
        session_dkn="s", law_hash=_LAW, legend_hash=_LEGEND, warrant_id="", intent_ref="",
        h_s=_m2.H_s(op, params).hex(), h_c=_hd(b"admissibility"), h_m=_hd(b"meaning"),
        h_j=_hd(b"locality"), h_r="a" * 64, parent_h_r="", mode="strict", version=1,
        id_c_s=_m2.ID_C_S, id_c_c=_m2.ID_C_C, id_c_m=_m2.ID_C_M, id_c_j=_m2.ID_C_J,
    )
    fields.update({k: v for k, v in over.items() if k in fields})
    fields["h_body"] = compute_h_body(**{k: fields[k] for k in (
        "op", "authority", "parameters", "intent", "jurisdiction", "confidence", "timestamp",
        "failed", "session_dkn", "law_hash", "legend_hash", "warrant_id", "intent_ref",
        "h_s", "h_c", "h_m", "h_j", "h_r", "parent_h_r", "mode", "version",
        "id_c_s", "id_c_c", "id_c_m", "id_c_j")})
    if "h_body" in over:
        fields["h_body"] = over["h_body"]
    return SimpleNamespace(**fields)


def run():
    checks = []

    def chk(name, cond):
        checks.append((name, bool(cond)))

    def raises(fn):
        try:
            fn(); return False
        except Exception:
            return True

    tv = build_trace_vector(_valid_receipt(), _FRAME)

    # ---- Allowed claims (1-8) ----
    chk("C1.enumerable: exactly the 4 committed axes",
        [s.surface_id for s in COMMITTED_SURFACES] == ["D_s", "D_c", "D_m", "D_j"])
    chk("C1.enumerable: vector matches registry order",
        [s.surface_id for s in tv.surfaces] == ["D_s", "D_c", "D_m", "D_j"])
    chk("C2.deterministic order: identical surfaces across builds",
        build_trace_vector(_valid_receipt(), _FRAME).surfaces == tv.surfaces)
    chk("C3.operator explicit+versioned",
        tv.aggregation_operator_id == "conjunctive_refusal_monotone_v1" == AGGREGATION_OPERATOR_ID)
    chk("C4.trace hash stable",
        build_trace_vector(_valid_receipt(), _FRAME).trace_vector_hash == tv.trace_vector_hash)
    chk("C5.binds frame tuple + registry/operator/transition/receipt ids",
        all([tv.frame == _FRAME, tv.surface_registry_version == SURFACE_REGISTRY_VERSION,
             tv.aggregation_operator_id == AGGREGATION_OPERATOR_ID,
             tv.transition_op == "demo.transition", bool(tv.receipt_h_r and tv.receipt_h_body)]))
    r = _valid_receipt()
    chk("C6.correspondence: every surface maps to a present committed field",
        all(getattr(r, s.committed_field, None) is not None for s in COMMITTED_SURFACES)
        and all(s.committed_field in COMMITTED_RECEIPT_FIELDS for s in COMMITTED_SURFACES))
    chk("C7.h_body binds the receipt body (re-derivation holds for a valid receipt)", tv.integrity_ok)
    chk("C8.no uncommitted surface in the committed vector (no D_cap / will-intent)",
        all(s.surface_id not in ("D_cap", "D_will") for s in COMMITTED_SURFACES))

    # ---- Honesty: NO OVERCLAIM of recomputation ----
    modes = {s.surface_id: s.verification_mode for s in COMMITTED_SURFACES}
    chk("H1.honesty: only D_s is independently re-derived",
        modes["D_s"] == MODE_REDERIVED
        and modes["D_c"] == modes["D_m"] == modes["D_j"] == MODE_COMMITTED_BODY_BOUND)
    chk("H2.honesty: D_c/D_m/D_j carry no rederivable claim",
        all(not s.rederivable for s in COMMITTED_SURFACES if s.surface_id != "D_s"))

    # ---- Required negative tests (N1-N7) ----
    d_cap = DecisionSurface("D_cap", "capability", "h_cap", "c_cap.v1", False, False, MODE_COMMITTED_BODY_BOUND)
    chk("N1.adding D_cap to committed registry fails closed",
        raises(lambda: validate_committed_registry(COMMITTED_SURFACES + (d_cap,)))
        and raises(lambda: build_trace_vector(_valid_receipt(), _FRAME, COMMITTED_SURFACES + (d_cap,))))
    d_will = DecisionSurface("D_will", "will-intent", "h_will", "c_will.v1", False, False, MODE_COMMITTED_BODY_BOUND)
    chk("N2.adding will/intent standalone committed surface fails closed (no committed field)",
        raises(lambda: validate_committed_registry(COMMITTED_SURFACES + (d_will,))))
    miss = build_trace_vector(_valid_receipt(h_c=""), _FRAME)
    chk("N3.missing a committed field (h_c) fails correspondence -> not ADMIT",
        any(s.surface_id == "D_c" and s.result == REFUSE for s in miss.surfaces)
        and aggregate(miss)[0] == REFUSE)
    reordered = (COMMITTED_SURFACES[1], COMMITTED_SURFACES[0],
                 COMMITTED_SURFACES[2], COMMITTED_SURFACES[3])  # D_c,D_s,D_m,D_j
    tv_reordered = build_trace_vector(_valid_receipt(), _FRAME, reordered)
    chk("N4.mismatched canonical order changes trace hash AND cannot ADMIT",
        tv_reordered.trace_vector_hash != tv.trace_vector_hash and aggregate(tv_reordered)[0] == REFUSE)
    h_other_op = _trace_vector_hash(surfaces=tv.surfaces, frame=_FRAME,
                                    registry_version=SURFACE_REGISTRY_VERSION, operator_id="other_v9",
                                    transition_op=tv.transition_op, receipt_h_r=tv.receipt_h_r,
                                    receipt_h_body=tv.receipt_h_body, integrity_ok=tv.integrity_ok,
                                    frame_consistent=tv.frame_consistent)
    chk("N5.changing aggregation operator id changes trace identity",
        h_other_op != tv.trace_vector_hash)
    other_frame = FrameRef(law_hash="dead" + "0" * 60, schema_hash=_FRAME.schema_hash,
                           legend_hash=_FRAME.legend_hash, codex_hash=_FRAME.codex_hash)
    chk("N6.changing frame tuple changes trace identity",
        build_trace_vector(_valid_receipt(), other_frame).trace_vector_hash != tv.trace_vector_hash)
    empty_tv = TraceVector(surfaces=(), frame=_FRAME,
                           surface_registry_version=SURFACE_REGISTRY_VERSION,
                           aggregation_operator_id=AGGREGATION_OPERATOR_ID, transition_op="x",
                           receipt_h_r="a" * 64, receipt_h_body="b" * 64, integrity_ok=True,
                           frame_consistent=True, trace_vector_hash="z" * 64)
    chk("N7.monolithic result without displayed surface vector fails no-monolith gate",
        aggregate(empty_tv)[0] == REFUSE)

    # ---- monotone refusal sanity ----
    chk("M.baseline ADMITs; failing surfaces stay REFUSE",
        aggregate(tv)[0] == ADMIT
        and aggregate(build_trace_vector(_valid_receipt(h_m=""), _FRAME))[0] == REFUSE
        and aggregate(build_trace_vector(_valid_receipt(h_m="", h_c=""), _FRAME))[0] == REFUSE)

    # ---- real receipt/body fixture probe (in addition to synthetic) ----
    from ugk.storage.store import UGKReceiptStore
    rs = UGKReceiptStore(":memory:")
    real = rs.write(op="crp_evidence", authority="alice", parameters={"i": 1}, intent="t1",
                    jurisdiction="production", session_dkn="d1", law_hash="L", legend_hash="G",
                    warrant_id="W1", intent_ref="r1")
    real_frame = FrameRef(law_hash=real.law_hash, schema_hash=_FRAME.schema_hash,
                          legend_hash=real.legend_hash, codex_hash=_FRAME.codex_hash)
    real_tv = build_trace_vector(real, real_frame)
    chk("R1.real store-issued receipt: 4 committed fields present, all PASS, real h_body holds, ADMIT",
        all(getattr(real, s.committed_field) for s in COMMITTED_SURFACES)
        and all(x.result == PASS for x in real_tv.surfaces)
        and real_tv.integrity_ok and aggregate(real_tv)[0] == ADMIT)
    real.h_s = "0" * 64  # tamper a real committed field
    real_tv_t = build_trace_vector(real, real_frame)
    chk("R2.tampered real h_s -> D_s REFUSE + integrity fail + no ADMIT",
        any(x.surface_id == "D_s" and x.result == REFUSE for x in real_tv_t.surfaces)
        and (not real_tv_t.integrity_ok) and aggregate(real_tv_t)[0] == REFUSE)

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
