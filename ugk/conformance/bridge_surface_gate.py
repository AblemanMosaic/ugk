"""ugk/conformance/bridge_surface_gate.py — proves the CK-BRIDGE Stage 2 committed SURFACE
(UGK-BODY-v8). SCHEMA/BODY leg only: commits a typed BridgeRecord identity + MCIR/SMH refs
(citation, never embedding). BRIDGE stays reserved/non-emittable; no BRIDGE-BINDING law invariant;
no kernel BRIDGE behavior. The surface is committed-but-unbound (the proven r148 continuation pattern).
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
                  confidence="high", timestamp="2026-06-23T00:00:00Z", failed=False, session_dkn="d",
                  law_hash="L", legend_hash="G", warrant_id="", intent_ref="", h_s="hs", h_c="hc",
                  h_m="hm", h_j="hj", h_r="hr", parent_h_r="ph", mode="strict",
                  id_c_s="c_s.v1", id_c_c="c_c.v1", id_c_m="c_m.v1+sigma_0", id_c_j="c_j.v1")
    br = dict(bridge_record_id="BR_hash", bridge_source_regime_ref="mcir:src",
              bridge_target_regime_ref="mcir:tgt", bridge_transformation_ref="mcir:xform",
              bridge_downgrade_reason="semantic_downgrade", bridge_preserved_evidence_ref="smh:ev")

    # (1) NON-RETROACTIVE by version-gating: a v<8 body is INDEPENDENT of the bridge surface
    #     (the v8 block + tag are skipped), so pre-existing v<8 receipts are byte-identical.
    v7_none = S.compute_h_body(version=7, **common)
    v7_with = S.compute_h_body(version=7, **{**common, **{"bridge_record_id": "x", "bridge_source_regime_ref": "y"}})
    chk("1.v7 body ignores the bridge surface (non-retroactive)", v7_none == v7_with)
    chk("1.v8 commits the bridge surface (distinct from v7)",
        S.compute_h_body(version=8, **{**common, **br}) != v7_none)

    # (2) BRIDGE-ONLY v8: a normal write is v7 with NULL bridge; only an explicit bridge surface -> v8.
    st = S.UGKReceiptStore(db_path=":memory:")
    r = st.write(op="crp_evidence", authority="a", parameters={}, law_hash="L", legend_hash="G")
    chk("2.normal write is v7 (bridge-only v8; non-bridge stays v7)", r.version == 7)
    chk("2.normal write carries NULL bridge surface", r.bridge_record_id is None
        and r.bridge_source_regime_ref is None and r.bridge_preserved_evidence_ref is None)
    chk("2.normal v7 body verifies", st.verify_receipt_bodies())
    rb = st.write(op="crp_evidence", authority="a", parameters={}, law_hash="L", legend_hash="G", bridge=br)
    chk("2.explicit bridge surface -> v8", rb.version == 8)

    # (3) A bridge-surface fixture commits, verifies, and round-trips through the DB read path.
    chk("3.bridge committed (id + refs + taxonomy)", rb.bridge_record_id == "BR_hash"
        and rb.bridge_transformation_ref == "mcir:xform" and rb.bridge_downgrade_reason == "semantic_downgrade")
    chk("3.body verifies WITH bridge committed", st.verify_receipt_bodies())
    rr = [x for x in st.all_receipts() if x.version == 8][-1]
    chk("3.read-back round-trip (id/src/tgt/xform/reason/evidence)",
        rr.bridge_record_id == "BR_hash" and rr.bridge_source_regime_ref == "mcir:src"
        and rr.bridge_target_regime_ref == "mcir:tgt" and rr.bridge_transformation_ref == "mcir:xform"
        and rr.bridge_downgrade_reason == "semantic_downgrade" and rr.bridge_preserved_evidence_ref == "smh:ev")

    # (4) Every committed bridge ref ENTERS h_body: mutating any one changes the body hash.
    base = S.compute_h_body(version=8, **{**common, **br})
    for k in br:
        mutated = S.compute_h_body(version=8, **{**common, **{**br, k: br[k] + "_X"}})
        chk("4.mutating %s changes h_body (committed, not ignored)" % k, mutated != base)

    # (5) FAIL-CLOSED validation (no silent coercion): bad taxonomy, empty ref, missing id all reject.
    st3 = S.UGKReceiptStore(db_path=":memory:")
    w = lambda **kw: st3.write(op="o", authority="a", parameters={}, bridge=dict(br, **kw))
    chk("5.downgrade_reason outside closed taxonomy fails closed", raises(lambda: w(bridge_downgrade_reason="bogus")))
    chk("5.empty required ref fails closed", raises(lambda: w(bridge_source_regime_ref="")))
    chk("5.missing bridge_record_id fails closed",
        raises(lambda: st3.write(op="o", authority="a", parameters={},
                                 bridge={k: v for k, v in br.items() if k != "bridge_record_id"})))
    chk("5.closed downgrade taxonomy is the proven 3-set",
        S.BRIDGE_DOWNGRADE_TAXONOMY == frozenset({"jurisdiction_crossing", "semantic_downgrade", "regime_translation"}))

    # (6) CITATION, never embedding: the committed values are exactly the supplied ref/hash strings
    #     (no MCIR artifact body, no SMH evidence body field exists). Identity-preserving round-trip
    #     of arbitrary opaque ref strings proves no body is parsed/expanded/embedded.
    opaque = dict(bridge_record_id="h:" + "a" * 64, bridge_source_regime_ref="ref://s",
                  bridge_target_regime_ref="ref://t", bridge_transformation_ref="ref://x",
                  bridge_downgrade_reason="regime_translation", bridge_preserved_evidence_ref="smh://e")
    st4 = S.UGKReceiptStore(db_path=":memory:")
    ro = st4.write(op="o", authority="a", parameters={}, bridge=opaque)
    chk("6.refs/hashes committed verbatim (citation, no body embedding)",
        ro.bridge_record_id == opaque["bridge_record_id"] and ro.bridge_preserved_evidence_ref == "smh://e")
    chk("6.no MCIR/SMH body column on the Receipt (only refs)",
        not any(hasattr(ro, a) for a in ("bridge_source_regime_body", "bridge_transformation_body",
                                         "bridge_preserved_evidence_body")))

    # (7) SCHEMA/BODY-ONLY: BRIDGE remains non-emittable; no BRIDGE-BINDING invariant; outcomes unchanged.
    chk("7.BRIDGE non-emittable WITHOUT a valid surface (Stage 4: emittable only with a verifying surface)",
        raises(lambda: S._assert_emittable("BRIDGE")))
    chk("7.BRIDGE is now in the closed terminal-outcome domain (Stage 4 native outcome)",
        "BRIDGE" in S.TERMINAL_OUTCOME_DOMAIN)
    chk("7.EMITTABLE_OUTCOMES (the unconditional set) unchanged; BRIDGE is conditional like DEFER",
        S.EMITTABLE_OUTCOMES == ("ADMIT", "REFUSE", "STRUCTURAL_ERROR"))
    chk("7.ADMIT/REFUSE/STRUCTURAL_ERROR still emittable; DEFER still HELD-gated",
        S._assert_emittable("ADMIT") is None and S._assert_emittable("REFUSE") is None
        and S._assert_emittable("STRUCTURAL_ERROR") is None and raises(lambda: S._assert_emittable("DEFER")))
    # NOTE (CK-BRIDGE Stage 3): the Stage-2 temporal guard "no BRIDGE-BINDING invariant exists yet" is
    # RETIRED — Stage 3 (r161) intentionally adds the BRIDGE-BINDING law invariant. This gate proves the
    # committed v8 SURFACE (committed-but-unbound at the schema/body level); BRIDGE-BINDING's surface-VALIDITY
    # binding is proven separately by bridge_binding_gate. BRIDGE remains non-emittable (asserted above).

    passed = sum(1 for _, c in checks if c)
    total = len(checks)
    fails = [n for n, c in checks if not c]
    detail = ("CK-BRIDGE Stage 2 committed SURFACE (UGK-BODY-v8): bridge-only v8 (non-bridge stays v7, "
              "byte-identical; v<8 non-retroactive); a bridge fixture commits + verifies + round-trips; "
              "every committed ref enters h_body (mutation-sensitive); fail-closed validation (closed "
              "downgrade taxonomy, required refs, non-empty id); CITATION only (refs/hashes committed "
              "verbatim, no MCIR/SMH body embedded); BRIDGE in domain (emittable only with a verifying surface, Stage 4), "
              "ADMIT/REFUSE/DEFER/STRUCTURAL_ERROR unchanged. Committed-but-unbound (law/kernel are later legs).")
    if fails:
        detail += " FAILS: " + "; ".join(fails)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
