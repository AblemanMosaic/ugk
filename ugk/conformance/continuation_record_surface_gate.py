"""ugk/conformance/continuation_record_surface_gate.py — proves the r148 continuation-record SURFACE
(AD-71, UGK-BODY-v7). SCHEMA leg: the support record TO-S-01 requires before DEFER can be a live
outcome. r148 commits the surface ONLY; DEFER stays reserved/non-emittable (no law/lifecycle yet).
"""
from ugk.storage import store as S


def run():
    checks = []

    def chk(n, c):
        checks.append((n, bool(c)))

    def raises(f):
        try:
            f(); return False
        except (ValueError, S.ReservedOutcomeError):
            return True

    common = dict(op="x", authority="a", parameters={"k": 1}, intent="i", jurisdiction="session",
                  confidence="high", timestamp="2026-06-21T00:00:00Z", failed=False, session_dkn="d",
                  law_hash="L", legend_hash="G", warrant_id="", intent_ref="", h_s="hs", h_c="hc",
                  h_m="hm", h_j="hj", h_r="hr", parent_h_r="ph", mode="strict",
                  id_c_s="c_s.v1", id_c_c="c_c.v1", id_c_m="c_m.v1+sigma_0", id_c_j="c_j.v1")

    # (1) NON-RETROACTIVE by version-gating: a v<7 body is INDEPENDENT of the continuation surface
    #     (the v7 block + tag are skipped), so pre-existing v<7 receipts are byte-identical.
    v6_none = S.compute_h_body(version=6, **common)
    v6_with = S.compute_h_body(version=6, continuation_state="HELD",
                               continuation_id="x", continuation_op="o", **common)
    chk("1.v6 body ignores the continuation surface (non-retroactive)", v6_none == v6_with)
    chk("1.v7 commits the continuation surface (distinct from v6)",
        S.compute_h_body(version=7, **common) != v6_none)

    # (2) Uniform v7 forward: a normal write is v7 with NULL continuation and verifies.
    st = S.UGKReceiptStore(db_path=":memory:")
    r = st.write(op="crp_evidence", authority="a", parameters={}, law_hash="L", legend_hash="G")
    chk("2.normal write is v7", r.version == 7)
    chk("2.normal write carries NULL continuation (DEFER not emittable -> nothing populates it)",
        r.continuation_id is None and r.continuation_state is None and r.continuation_model_id is None)
    chk("2.normal v7 body verifies", st.verify_receipt_bodies())

    # (3) A continuation-record fixture commits, verifies, and round-trips through the DB read path.
    anchor = "anchor-fixture"
    cid = S.compute_continuation_id(op="deferred_op", authority="auth", parameters={"p": 1},
                                    jurisdiction="session", anchor=anchor)
    cont = dict(id=cid, op="deferred_op", authority="auth", parameters={"p": 1}, jurisdiction="session",
                anchor=anchor, expiry_basis={"kind": "receipt_height", "value": 100},
                state="HELD", model_id="continuation_record_model_v1")
    st2 = S.UGKReceiptStore(db_path=":memory:")
    rc = st2.write(op="crp_evidence", authority="a", parameters={}, law_hash="L", legend_hash="G", continuation=cont)
    chk("3.continuation committed (state HELD, deterministic id)", rc.continuation_state == "HELD" and rc.continuation_id == cid)
    chk("3.body verifies WITH continuation committed", st2.verify_receipt_bodies())
    rr = st2.all_receipts()[-1]
    chk("3.read-back round-trip (state/id/op)", rr.continuation_state == "HELD" and rr.continuation_id == cid and rr.continuation_op == "deferred_op")
    chk("3.expiry_basis stored canonical {kind,value}", rr.continuation_expiry_basis == '{"kind":"receipt_height","value":100}')

    # (4) continuation_id is deterministic + recomputable.
    chk("4.continuation_id recomputes deterministically",
        S.compute_continuation_id(op="deferred_op", authority="auth", parameters={"p": 1},
                                  jurisdiction="session", anchor=anchor) == cid)

    # (5) Closed-domain, FAIL-CLOSED validation (no wall-clock; no silent coercion).
    st3 = S.UGKReceiptStore(db_path=":memory:")
    w = lambda **kw: st3.write(op="o", authority="a", parameters={}, continuation=dict(cont, **kw))
    chk("5.bad lifecycle state fails closed", raises(lambda: w(state="BOGUS")))
    chk("5.wall-clock expiry kind fails closed (committed-evidence only)", raises(lambda: w(expiry_basis={"kind": "wall_clock", "value": "2026"})))
    chk("5.malformed expiry (not {kind,value}) fails closed", raises(lambda: w(expiry_basis={"deadline": "soon"})))
    chk("5.receipt_height non-int value fails closed", raises(lambda: w(expiry_basis={"kind": "receipt_height", "value": "soon"})))
    chk("5.bad model_id fails closed", raises(lambda: w(model_id="evil")))
    chk("5.non-recomputable continuation_id fails closed", raises(lambda: w(id="deadbeef")))

    # (6) r148 is SCHEMA-ONLY: DEFER + CRISIS remain reserved / non-emittable; no law/lifecycle yet.
    chk("6.DEFER still non-emittable (reserved at law)", raises(lambda: S._assert_emittable("DEFER")))
    chk("6.CRISIS still non-emittable (reserved)", raises(lambda: S._assert_emittable("CRISIS")))
    chk("6.EMITTABLE_OUTCOMES unchanged (no DEFER added)", S.EMITTABLE_OUTCOMES == ("ADMIT", "REFUSE", "STRUCTURAL_ERROR"))
    chk("6.lifecycle marker domain is the closed 5-set (append-only vocabulary)",
        S.CONTINUATION_STATE_DOMAIN == frozenset({"HELD", "RESUMED", "RESOLVED", "EXPIRED", "REFUSED"}))
    chk("6.expiry kinds are committed-evidence-only (no wall-clock)",
        S.CONTINUATION_EXPIRY_KIND_DOMAIN == frozenset({"receipt_height", "explicit_trigger"}))

    passed = sum(1 for _, c in checks if c)
    total = len(checks)
    fails = [n for n, c in checks if not c]
    detail = ("continuation-record SURFACE (AD-71, r148, UGK-BODY-v7): the support record TO-S-01 requires "
              "before DEFER becomes live. Non-retroactive (v<7 byte-identical via version-gating); uniform v7 "
              "forward commits + verifies the eight nullable continuation columns; a fixture record persists, "
              "verifies, and round-trips; continuation_id is deterministic/recomputable; closed-domain validation "
              "fails closed (no wall-clock expiry; no silent coercion); DEFER/CRISIS remain reserved/non-emittable "
              "(schema-only -- no law/lifecycle). Append-only lifecycle vocabulary; committed-evidence expiry only.")
    if fails:
        detail = "FAILED: " + "; ".join(fails)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
