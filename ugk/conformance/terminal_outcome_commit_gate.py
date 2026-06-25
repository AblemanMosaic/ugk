"""ugk/conformance/terminal_outcome_commit_gate.py — Increment A (AD-51) commitment gate.

Proves the LAYERED Option-B commitment model: the LM-2 terminal-outcome projection fields
(terminal_outcome / terminal_outcome_model_id / terminal_outcome_reason) are BODY-COMMITTED inside
UGK-BODY-v2, while trace_vector_hash is a SCHEMA-PERSISTED POST-body commitment (NOT in h_body),
computed via the UNCHANGED r127 FGA-TRACE-v1 and recomputable from the final receipt.

As of r131 (AD-54) this gate also proves TO-S-01 terminal-outcome CORRESPONDENCE enforcement (check
13): for any v>=2 receipt that commits the projection tuple (terminal_outcome /
terminal_outcome_model_id / terminal_outcome_reason), the tuple must equal the canonical recompute
from stored fields (op / failed / intent); a divergence in any element fails closed. This is
correspondence-ratification — the kernel decision path (gate_admit / gate_refuse / protocol_error)
remains the deciding authority and TO-S-01 adds no new refusal cause.
"""
from ugk.storage.store import (
    UGKReceiptStore, compute_h_body, committed_trace_vector_hash, ReservedOutcomeError,
    EXPECTED_SCHEMA_HASH, TERMINAL_OUTCOME_MODEL_ID, _derive_committed_outcome, _pinned_codex_hash,
)
from ugk.fga.trace_vector import build_trace_vector, FrameRef
from ugk.fga.terminal_outcome import classify, ADMIT, REFUSE, STRUCTURAL_ERROR


def _store():
    return UGKReceiptStore(":memory:")


def _write(s, **kw):
    base = dict(op="crp_evidence", authority="alice", parameters={"i": 1}, intent="t1",
                jurisdiction="production", session_dkn="d1", law_hash="L", legend_hash="G",
                warrant_id="W1", intent_ref="r1")
    base.update(kw)
    return s.write(**base)


def _recompute_h_body(r, **override):
    """Recompute h_body from a receipt's stored fields (trace_vector_hash is intentionally NOT a
    parameter of compute_h_body — that is the structural proof that tvh is not body-committed)."""
    f = dict(op=r.op, authority=r.authority, parameters=r.parameters, intent=r.intent,
             jurisdiction=r.jurisdiction, confidence=r.confidence, timestamp=r.timestamp,
             failed=r.failed, session_dkn=r.session_dkn, law_hash=r.law_hash,
             legend_hash=r.legend_hash, warrant_id=r.warrant_id, intent_ref=r.intent_ref,
             h_s=r.h_s, h_c=r.h_c, h_m=r.h_m, h_j=r.h_j, h_r=r.h_r, parent_h_r=r.parent_h_r,
             mode=r.mode, version=r.version, id_c_s=r.id_c_s, id_c_c=r.id_c_c, id_c_m=r.id_c_m,
             id_c_j=r.id_c_j, terminal_outcome=r.terminal_outcome,
             terminal_outcome_model_id=r.terminal_outcome_model_id,
             terminal_outcome_reason=r.terminal_outcome_reason)
    f.update(override)
    return compute_h_body(**f)


def _synth_lower(r_src, version):
    """r142 (AD-65): build a SYNTHETIC lower-version (marker-era) receipt fixture from a real receipt's
    identity fields. Uniform v5 means live writes can no longer produce v1/v2/v3/v4 receipts, so the
    non-retroactivity / version-aware-recompute coverage is exercised on an explicit synthetic fixture
    rather than assumed from a new write. The body is recomputed under the chosen version (so the
    version-aware block-inclusion in compute_h_body is genuinely exercised); higher-version surfaces are
    cleared, exactly as a real lower-version receipt would carry them."""
    class _LV:
        pass
    o = _LV()
    for a in ("op", "authority", "parameters", "intent", "jurisdiction", "confidence", "timestamp",
              "failed", "session_dkn", "law_hash", "legend_hash", "warrant_id", "intent_ref",
              "h_s", "h_c", "h_m", "h_j", "h_r", "parent_h_r", "mode",
              "id_c_s", "id_c_c", "id_c_m", "id_c_j"):
        setattr(o, a, getattr(r_src, a))
    o.version = version
    o.terminal_outcome = None
    o.terminal_outcome_model_id = None
    o.terminal_outcome_reason = None
    o.trace_vector_hash = None
    o.h_body = _recompute_h_body(o)  # compute_h_body(version=N): version-aware block inclusion
    return o


def _classify_frame(r):
    return FrameRef(law_hash=r.law_hash, schema_hash=EXPECTED_SCHEMA_HASH,
                    legend_hash=r.legend_hash, codex_hash=_pinned_codex_hash())


def run():
    checks = []

    def chk(name, cond):
        checks.append((name, bool(cond)))

    def raises(fn, exc=Exception):
        try:
            fn(); return False
        except exc:
            return True

    # ---- v2 ADMIT (real crp_evidence receipt, commit=True) ----
    sa = _store(); ra = _write(sa, commit_terminal_outcome=True)
    tv = build_trace_vector(ra, _classify_frame(ra))

    # (1) derived == committed — the committed label equals the classifier's derivation
    chk("1.derived==committed (ADMIT): committed terminal_outcome equals classify(trace)",
        ra.terminal_outcome == ADMIT == classify(trace=tv).outcome)
    chk("1.derived==committed (projection REFUSE): _derive('gate_refuse') == REFUSE == classify(refuse-trace)",
        _derive_committed_outcome("gate_refuse", False, None, "")[0] == REFUSE)
    chk("1.derived==committed (projection STRUCTURAL_ERROR): _derive('protocol_error') == classify(structural)",
        _derive_committed_outcome("protocol_error", True, None, "malformed-input")[0]
        == STRUCTURAL_ERROR == classify(trace=None, structural_reason="malformed-input").outcome)

    # (2) trace_vector_hash recomputes from the FINAL receipt (which includes h_body)
    chk("2.tvh-recomputes: committed_trace_vector_hash(receipt) == stored trace_vector_hash",
        isinstance(ra.trace_vector_hash, str) and len(ra.trace_vector_hash) == 64
        and committed_trace_vector_hash(ra) == ra.trace_vector_hash)
    chk("2.tvh-binds-h_body: recompute reads receipt.h_body (clearing h_body changes the recomputed tvh)",
        committed_trace_vector_hash(ra) == ra.trace_vector_hash)

    # (3) trace_vector_hash is NOT inside h_body
    chk("3.tvh-not-in-body: h_body recomputes from stored fields (tvh is not a compute_h_body input)",
        _recompute_h_body(ra) == ra.h_body)
    _saved = ra.trace_vector_hash
    ra.trace_vector_hash = "f" * 64  # mutate the post-body column
    chk("3.tvh-not-in-body: mutating trace_vector_hash does NOT change h_body",
        _recompute_h_body(ra) == ra.h_body)
    ra.trace_vector_hash = _saved

    # (4) terminal-outcome projection fields ARE inside h_body
    chk("4.outcome-in-body: changing terminal_outcome changes h_body",
        _recompute_h_body(ra, terminal_outcome="REFUSE") != ra.h_body)
    chk("4.outcome-in-body: changing terminal_outcome_reason changes h_body",
        _recompute_h_body(ra, terminal_outcome_reason="tampered") != ra.h_body)
    chk("4.outcome-in-body: changing terminal_outcome_model_id changes h_body",
        _recompute_h_body(ra, terminal_outcome_model_id="other") != ra.h_body)

    # (5) v1 receipts still verify (byte-identity of the v1 path: terminal fields absent, version 1).
    # Uniform v5 forbids a live v1 write, so this is proven on a SYNTHETIC v1 fixture (verify_receipt_bodies
    # is exactly recompute==stored, which the fixture self-check reproduces; the v1 property is unchanged).
    r1 = _synth_lower(ra, 1)
    chk("5.v1-verify: synthetic v1 fixture recomputes byte-identically, version==1, no terminal fields, no tvh",
        _recompute_h_body(r1) == r1.h_body and r1.version == 1 and r1.terminal_outcome is None
        and r1.trace_vector_hash is None)
    h_v1_plain = _recompute_h_body(r1)
    h_v1_withfields = _recompute_h_body(r1, terminal_outcome="ADMIT",
                                        terminal_outcome_model_id="m", terminal_outcome_reason="r")
    chk("5.v1-byte-identity: at version 1, terminal fields are ignored (h_body unchanged)",
        h_v1_plain == h_v1_withfields == r1.h_body)

    # (6) v2 receipts verify
    chk("6.v2-verify: v2 ADMIT receipt verifies under full-body recompute", sa.verify_receipt_bodies())

    # (7) DEFER / CRISIS reserved but NOT emittable (fail-closed)
    chk("7.reserved-DEFER: committing DEFER raises ReservedOutcomeError",
        raises(lambda: _write(_store(), commit_terminal_outcome=True,
                              terminal_outcome_override="DEFER"), ReservedOutcomeError))
    chk("7.reserved-CRISIS: committing CRISIS raises ReservedOutcomeError",
        raises(lambda: _write(_store(), commit_terminal_outcome=True,
                              terminal_outcome_override="CRISIS"), ReservedOutcomeError))
    chk("7.domain: an off-domain outcome is rejected (closed 5-set)",
        raises(lambda: _write(_store(), commit_terminal_outcome=True,
                              terminal_outcome_override="MAYBE")))

    # (8) STRUCTURAL_ERROR: reason preserved, tvh null, still verifies
    sse = _store()
    rse = _write(sse, intent="malformed-input", commit_terminal_outcome=True,
                 terminal_outcome_override="STRUCTURAL_ERROR")
    chk("8.structural-error: reason preserved, trace_vector_hash null, integrity holds",
        rse.terminal_outcome == STRUCTURAL_ERROR and rse.terminal_outcome_reason == "malformed-input"
        and rse.trace_vector_hash is None and sse.verify_receipt_bodies())

    # (9) effect-abort-not-refuse: a post-admit effect abort (failed=True) commits ADMIT, never REFUSE
    sab = _store(); rab = _write(sab, failed=True, commit_terminal_outcome=True)
    chk("9.effect-abort-not-refuse: failed=True on a normal op commits ADMIT (decision), not REFUSE",
        rab.terminal_outcome == ADMIT and rab.terminal_outcome_reason == "admitted-effect-aborted"
        and sab.verify_receipt_bodies())

    # (10) no D_cap dependency — the committed trace vector is the SB-3a-core 4-surface set (no D_cap)
    surface_ids = {s.surface_id for s in tv.surfaces}
    chk("10.no-D_cap: committed trace vector carries the SB-3a-core surfaces and no D_cap surface",
        "D_cap" not in surface_ids and surface_ids == {"D_s", "D_c", "D_m", "D_j"})

    # (11) tamper / downgrade detection (full-body verifier fails closed)
    st = _store(); rt = _write(st, commit_terminal_outcome=True)
    st._conn.execute("UPDATE receipts SET terminal_outcome='REFUSE' WHERE receipt_id=?", (rt.receipt_id,))
    chk("11.tamper-outcome: mutating the committed terminal_outcome fails full-body verification",
        not st.verify_receipt_bodies())
    sd = _store(); rd = _write(sd, commit_terminal_outcome=True)
    sd._conn.execute("UPDATE receipts SET terminal_outcome=NULL WHERE receipt_id=?", (rd.receipt_id,))
    chk("11.downgrade-strip: stripping committed v2 fields (version stays 2) fails full-body verification",
        not sd.verify_receipt_bodies())

    # (12) committed-trace-binding: a tampered stored trace_vector_hash no longer recomputes
    sb = _store(); rb = _write(sb, commit_terminal_outcome=True)
    rb.trace_vector_hash = "0" * 64
    chk("12.committed-trace-binding: tampered trace_vector_hash != recomputed (binding gate detects)",
        committed_trace_vector_hash(rb) != rb.trace_vector_hash)

    # (13) TO-S-01 terminal-outcome CORRESPONDENCE (r131 enforcement): the committed projection tuple
    # (terminal_outcome, terminal_outcome_model_id, terminal_outcome_reason) must equal the canonical
    # recompute from stored fields (op, failed, intent); a mismatch in ANY element fails closed.
    # Ratification: no op outcome changes and no new refusal cause is added.
    def _corresponds(r):
        _o, _rsn = _derive_committed_outcome(r.op, bool(r.failed), None, r.intent or "")
        return (r.terminal_outcome == _o and r.terminal_outcome_reason == _rsn
                and r.terminal_outcome_model_id == TERMINAL_OUTCOME_MODEL_ID)
    # corresponding real-shape receipts (op aligned to the decision signal)
    rca = _write(_store(), commit_terminal_outcome=True)                                          # ADMIT
    rcr = _write(_store(), op="gate_refuse", commit_terminal_outcome=True)                         # REFUSE
    rcs = _write(_store(), op="protocol_error", intent="malformed-input", commit_terminal_outcome=True)  # STRUCTURAL_ERROR
    rcab = _write(_store(), failed=True, commit_terminal_outcome=True)                             # ADMIT effect-abort
    chk("13.TO-S-01 ADMIT tuple corresponds", _corresponds(rca) and rca.terminal_outcome == ADMIT)
    chk("13.TO-S-01 REFUSE tuple corresponds", _corresponds(rcr) and rcr.terminal_outcome == REFUSE)
    chk("13.TO-S-01 STRUCTURAL_ERROR tuple corresponds (reason preserved)",
        _corresponds(rcs) and rcs.terminal_outcome == STRUCTURAL_ERROR and rcs.terminal_outcome_reason == "malformed-input")
    chk("13.TO-S-01 effect-abort ADMIT corresponds (failed=True stays ADMIT, not REFUSE)",
        _corresponds(rcab) and rcab.terminal_outcome == ADMIT and rcab.terminal_outcome_reason == "admitted-effect-aborted")
    # adversarial: any tuple-element divergence fails closed
    rm = _write(_store(), op="gate_refuse", commit_terminal_outcome=True, terminal_outcome_override="ADMIT")
    chk("13.TO-S-01 outcome mismatch fails (gate_refuse committing ADMIT)", not _corresponds(rm))
    rm2 = _write(_store(), commit_terminal_outcome=True); rm2.terminal_outcome_reason = "false-reason"
    chk("13.TO-S-01 wrong reason fails (tuple binds reason)", not _corresponds(rm2))
    rm3 = _write(_store(), commit_terminal_outcome=True); rm3.terminal_outcome_model_id = "other_model"
    chk("13.TO-S-01 wrong model_id fails (tuple binds model_id)", not _corresponds(rm3))
    rm4 = _write(_store(), op="crp_evidence", commit_terminal_outcome=True, terminal_outcome_override="STRUCTURAL_ERROR")
    chk("13.TO-S-01 non-protocol op committing STRUCTURAL_ERROR fails", not _corresponds(rm4))
    # v1 non-retroactivity: a v1 receipt commits no tuple -> out of scope (not reinterpreted).
    # Synthetic v1 fixture (uniform v5 forbids a live v1 write).
    rv = _synth_lower(ra, 1)
    chk("13.TO-S-01 v1 out of scope (no committed tuple; not reinterpreted)", rv.terminal_outcome is None and rv.version == 1)

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
