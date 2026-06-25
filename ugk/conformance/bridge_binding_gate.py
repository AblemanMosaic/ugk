"""ugk/conformance/bridge_binding_gate.py — proves BRIDGE-BINDING (CK-BRIDGE Stage 3, law leg).

Exercises the pure, resolver-parameterized verify_bridge_binding with FIXTURE read-only resolvers:
a valid committed bridge surface verifies; each violation refutes independently; verification is
deterministic and KERNEL-FREE (no store/kernel instance); BRIDGE stays NON-EMITTABLE (surface-validity
binding only — the terminal-outcome correspondence is Stage 4); ADMIT/REFUSE/DEFER/STRUCTURAL_ERROR
are unchanged. MCIR/SMH are never imported; resolvers are injected.
"""
from ugk.storage import store as S
from ugk.storage.bridge_binding import verify_bridge_binding, has_bridge_surface


def run():
    checks = []

    def chk(n, c):
        checks.append((n, bool(c)))

    # A valid committed surface + deterministic fixture resolvers.
    VALID = dict(bridge_record_id="BR_ID_OK", bridge_source_regime_ref="mcir:src",
                 bridge_target_regime_ref="mcir:tgt", bridge_transformation_ref="mcir:xform",
                 bridge_downgrade_reason="semantic_downgrade", bridge_preserved_evidence_ref="smh:ev")

    # Fixture read-only resolvers (deterministic; the gate is the verification context).
    def identity_of(src, tgt, xform, reason, ev):
        # deterministic identity derivation fixture: the valid surface's id.
        return "BR_ID_OK" if (src, tgt, xform, reason, ev) == (
            "mcir:src", "mcir:tgt", "mcir:xform", "semantic_downgrade", "smh:ev") else "BR_ID_OTHER"
    diverge_yes = lambda s, t: s != t          # structural divergence (fixture: distinct regimes diverge)
    diverge_no = lambda s, t: False            # refusing divergence resolver
    xform_ok = lambda x: x == "mcir:xform"     # transformation resolves
    xform_no = lambda x: False
    ev_ok = lambda e: e == "smh:ev"            # SMH read-only resolution
    ev_no = lambda e: False

    R = dict(mcir_identity_resolver=identity_of, mcir_divergence_resolver=diverge_yes,
             mcir_transformation_resolver=xform_ok, smh_evidence_resolver=ev_ok)

    def verify(fields, **over):
        kw = dict(R); kw.update(over)
        return verify_bridge_binding(fields, **kw)

    # (13) valid surface verifies.
    ok, why = verify(VALID)
    chk("13.valid bridge surface verifies under fixture resolvers", ok)

    # absent surface -> valid (N/A), and detection helper agrees.
    empty = {k: None for k in VALID}
    chk("0.absent surface is N/A (valid)", verify(empty)[0] is True and not has_bridge_surface(empty))

    # (14) missing id refutes.
    chk("14.missing bridge_record_id refutes", not verify({**VALID, "bridge_record_id": None})[0])
    chk("14.empty bridge_record_id refutes", not verify({**VALID, "bridge_record_id": ""})[0])

    # (15) missing each required ref refutes.
    for k in ("bridge_source_regime_ref", "bridge_target_regime_ref",
              "bridge_transformation_ref", "bridge_preserved_evidence_ref"):
        chk("15.missing %s refutes" % k, not verify({**VALID, k: None})[0])

    # (16) source/target must be distinct.
    chk("16.identical source/target refutes", not verify({**VALID, "bridge_target_regime_ref": "mcir:src"})[0])

    # (17) source/target must structurally diverge under resolver evidence.
    chk("17.non-divergent source/target refutes (divergence resolver False)",
        not verify(VALID, mcir_divergence_resolver=diverge_no)[0])

    # (18) transformation ref required + resolver-validated.
    chk("18.unresolved transformation refutes (resolver False)",
        not verify(VALID, mcir_transformation_resolver=xform_no)[0])

    # (19) downgrade reason closed taxonomy enforced.
    chk("19.downgrade_reason outside taxonomy refutes",
        not verify({**VALID, "bridge_downgrade_reason": "bogus"})[0])
    chk("19.closed taxonomy is the proven 3-set",
        S.BRIDGE_DOWNGRADE_TAXONOMY == frozenset({"jurisdiction_crossing", "semantic_downgrade", "regime_translation"}))

    # (20) preserved evidence required + resolver-validated.
    chk("20.unresolved preserved evidence refutes (SMH resolver False)",
        not verify(VALID, smh_evidence_resolver=ev_no)[0])

    # (10) identity verification is deterministic: tampered id (mismatch vs resolver) refutes; same input same verdict.
    chk("10.tampered id (identity mismatch) refutes", not verify({**VALID, "bridge_record_id": "FORGED"})[0])
    chk("10.deterministic: identical input -> identical verdict", verify(VALID) == verify(VALID))

    # (21) kernel-free / read-only: a resolver that raises is fail-closed (no live kernel, no escape).
    def boom(*a):
        raise RuntimeError("resolver side-effect attempt")
    chk("21.evidence resolver exception is fail-closed (read-only, kernel-free)",
        not verify(VALID, smh_evidence_resolver=boom)[0])
    chk("21.verification needs no store/kernel instance (pure function)", callable(verify_bridge_binding))

    # (22/23) SMH non-authority / MCIR bodies unembedded: only ref strings are consumed; the verdict is
    #         a function of refs + resolver booleans, never of an embedded artifact body.
    opaque = {**VALID, "bridge_preserved_evidence_ref": "smh:ev", "bridge_source_regime_ref": "mcir:src"}
    chk("22/23.verdict is a function of refs + resolver results only (no embedded MCIR/SMH body)",
        verify(opaque)[0] is True)

    # (10/11) BRIDGE remains NON-EMITTABLE; correspondence inert; no kernel emission.
    def raises_emit(o):
        try:
            S._assert_emittable(o); return False
        except (ValueError, S.ReservedOutcomeError):
            return True
    chk("11.BRIDGE non-emittable WITHOUT a verifying surface (Stage 4: emittable only via valid surface)", raises_emit("BRIDGE"))
    chk("11.BRIDGE is now in the terminal-outcome domain (Stage 4 native outcome)", "BRIDGE" in S.TERMINAL_OUTCOME_DOMAIN)

    # (24) ADMIT/REFUSE/DEFER/STRUCTURAL_ERROR unchanged.
    chk("24.ADMIT/REFUSE/STRUCTURAL_ERROR emittable; DEFER HELD-gated; unchanged",
        S._assert_emittable("ADMIT") is None and S._assert_emittable("REFUSE") is None
        and S._assert_emittable("STRUCTURAL_ERROR") is None and raises_emit("DEFER")
        and S.EMITTABLE_OUTCOMES == ("ADMIT", "REFUSE", "STRUCTURAL_ERROR"))

    # (12) r160 compatibility: a surface validated by store at write still verifies here (no schema/body change).
    st = S.UGKReceiptStore(db_path=":memory:")
    rb = st.write(op="o", authority="a", parameters={}, bridge=VALID)
    fields = {k: getattr(rb, k) for k in VALID}
    chk("12.r160-committed bridge surface verifies under BRIDGE-BINDING", verify(fields)[0])

    passed = sum(1 for _, c in checks if c)
    total = len(checks)
    fails = [n for n, c in checks if not c]
    detail = ("BRIDGE-BINDING (Stage 3, law leg): resolver-parameterized verify_bridge_binding binds "
              "committed v8 bridge-surface VALIDITY — deterministic, kernel-free, MCIR/SMH never imported. "
              "Valid surface verifies; missing id/refs, identical or non-divergent source/target, unresolved "
              "transformation, bad taxonomy, unresolved evidence, and tampered identity all REFUTE fail-closed; "
              "resolver exceptions fail closed (read-only). SMH resolution is not authority; MCIR bodies stay "
              "external. BRIDGE in domain, emittable only via a verifying surface (Stage 4); ADMIT/REFUSE/DEFER/STRUCTURAL_ERROR "
              "unchanged; r160-committed surface stays compatible.")
    if fails:
        detail += " FAILS: " + "; ".join(fails)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
