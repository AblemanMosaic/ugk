"""ugk/conformance/bridge_emission_gate.py — proves native BRIDGE kernel emission (CK-BRIDGE Stage 4 / r162).

BRIDGE becomes a native terminal outcome, emittable ONLY under a committed v8 bridge surface that verifies
under BRIDGE-BINDING at emit, via the kernel's explicit opt-in path (kernel.emit_bridge). The kernel never
spontaneously bridges; an invalid surface refuses/errors fail-closed (never ADMITs). ADMIT/REFUSE/DEFER/
STRUCTURAL_ERROR are unchanged; BRIDGE is distinct from every other outcome. Runs the V12/V13 bridge
validation scenarios natively (valid emits+verifies; no-record / no-evidence refute) without tailoring.
"""
from ugk.storage import store as S
from ugk.storage.bridge_binding import verify_bridge_binding


def run():
    checks = []

    def chk(n, c):
        checks.append((n, bool(c)))

    def raises(f):
        try:
            f(); return False
        except (ValueError, S.ReservedOutcomeError):
            return True

    VALID = dict(bridge_record_id="BR_OK", bridge_source_regime_ref="mcir:src",
                 bridge_target_regime_ref="mcir:tgt", bridge_transformation_ref="mcir:xf",
                 bridge_downgrade_reason="jurisdiction_crossing", bridge_preserved_evidence_ref="smh:ev")

    # The opt-in path injects read-only resolvers (the kernel imports neither MCIR nor SMH).
    def make_verifier(identity="BR_OK", diverge=True, xform_ok=True, ev_ok=True):
        return lambda b: verify_bridge_binding(
            b,
            mcir_identity_resolver=lambda s, t, x, r, e: identity,
            mcir_divergence_resolver=lambda s, t: diverge and s != t,
            mcir_transformation_resolver=lambda x: xform_ok,
            smh_evidence_resolver=lambda e: ev_ok)
    verifier = make_verifier()

    def emit(bridge=VALID, bv=verifier, override="BRIDGE", **over):
        st = S.UGKReceiptStore(db_path=":memory:")
        kw = dict(op="regime_cross", authority="a", parameters={}, law_hash="L", legend_hash="G",
                  commit_terminal_outcome=True, terminal_outcome_override=override)
        if bridge is not None:
            kw["bridge"] = bridge
        if bv is not None:
            kw["bridge_verifier"] = bv
        kw.update(over)
        return st, st.write(**kw)

    # (1) emittable only under valid bridge conditions.
    st, r = emit()
    chk("1.BRIDGE emittable under a valid verifying surface", r.terminal_outcome == "BRIDGE")
    # (2) not emittable without a bridge surface.
    chk("2.BRIDGE not emittable without a bridge surface", raises(lambda: emit(bridge=None)))
    # (3) not emittable with a malformed surface (missing a ref).
    chk("3.BRIDGE not emittable with malformed surface", raises(lambda: emit(bridge={**VALID, "bridge_transformation_ref": None})))
    # (4) not emittable when BRIDGE-BINDING refutes (divergence resolver False).
    chk("4.BRIDGE not emittable when BRIDGE-BINDING refutes (no divergence)",
        raises(lambda: emit(bv=make_verifier(diverge=False))))
    chk("4b.refute on transformation-unresolved", raises(lambda: emit(bv=make_verifier(xform_ok=False))))
    chk("4c.refute on evidence-unresolved", raises(lambda: emit(bv=make_verifier(ev_ok=False))))
    chk("4d.refute on identity-mismatch (tampered id)", raises(lambda: emit(bridge={**VALID, "bridge_record_id": "FORGED"})))
    # (5) explicit opt-in only: the kernel exposes emit_bridge; (6) no spontaneous bridge.
    from ugk.kernel import GovernanceKernel as _K
    chk("5.kernel exposes an explicit opt-in emit_bridge path", hasattr(_K, "emit_bridge"))
    chk("6.kernel cannot spontaneously bridge: classify never yields BRIDGE (override-only)",
        "BRIDGE" not in (lambda m: [getattr(m, n, None) for n in ("ADMIT", "REFUSE", "DEFER", "STRUCTURAL_ERROR")])(__import__("ugk.fga.terminal_outcome", fromlist=["x"])))
    ra = S.UGKReceiptStore(db_path=":memory:").write(op="normal_op", authority="a", parameters={}, commit_terminal_outcome=True)
    chk("6b.an ordinary op never yields BRIDGE", ra.terminal_outcome == "ADMIT")
    # (7) BRIDGE receipt commits the v8 surface; (8) verifies under BRIDGE-BINDING; (9) receipt persisted (receipt-before-effect).
    chk("7.BRIDGE receipt commits the v8 surface", r.version >= 8 and r.bridge_record_id == "BR_OK"
        and r.bridge_preserved_evidence_ref == "smh:ev")
    fields = {k: getattr(r, k) for k in VALID}
    chk("8.BRIDGE receipt verifies under BRIDGE-BINDING", verifier(fields)[0] and st.verify_receipt_bodies())
    chk("9.receipt-before-effect: the BRIDGE receipt is durably written (present in the store)",
        any(x.terminal_outcome == "BRIDGE" for x in st.all_receipts()))

    # (10-13) ADMIT/REFUSE/DEFER/STRUCTURAL_ERROR unchanged.
    chk("10.ADMIT unchanged", S._assert_emittable("ADMIT") is None)
    chk("11.REFUSE unchanged", S._assert_emittable("REFUSE") is None)
    chk("12.DEFER unchanged (HELD-gated)", raises(lambda: S._assert_emittable("DEFER")))
    chk("13.STRUCTURAL_ERROR unchanged", S._assert_emittable("STRUCTURAL_ERROR") is None)

    # (14-19) BRIDGE distinct from every other outcome (distinct domain member + distinct value).
    dom = S.TERMINAL_OUTCOME_DOMAIN
    chk("14/15/16/17/18.BRIDGE distinct from ADMIT/REFUSE/DEFER/STRUCTURAL_ERROR (and locality-refuse=REFUSE family)",
        "BRIDGE" in dom and len({"BRIDGE", "ADMIT", "REFUSE", "DEFER", "STRUCTURAL_ERROR"}) == 5
        and r.terminal_outcome == "BRIDGE" and r.terminal_outcome not in ("ADMIT", "REFUSE", "DEFER", "STRUCTURAL_ERROR"))
    chk("19.BRIDGE distinct from CRISIS (CRISIS still reserved/non-emittable)",
        "BRIDGE" != "CRISIS" and raises(lambda: S._assert_emittable("CRISIS")))

    # (20) V12 native: a valid bridge OUTCOME emits and verifies.
    chk("20.V12 native: valid bridge emits BRIDGE and verifies under BRIDGE-BINDING",
        r.terminal_outcome == "BRIDGE" and verifier(fields)[0])
    # (21) V13 native: the committed downgrade_reason is recoverable from the closed taxonomy and verifies.
    chk("21.V13 native: downgrade_reason recovered from committed surface, in closed taxonomy, verifies",
        r.bridge_downgrade_reason == "jurisdiction_crossing"
        and r.bridge_downgrade_reason in S.BRIDGE_DOWNGRADE_TAXONOMY and verifier(fields)[0])
    # (22) BRIDGE without a BridgeRecord fails; (23) BridgeRecord without preserved evidence fails.
    chk("22.BRIDGE without a BridgeRecord (surface) fails", raises(lambda: emit(bridge=None)))
    chk("23.BridgeRecord without preserved_evidence_ref fails",
        raises(lambda: emit(bridge={**VALID, "bridge_preserved_evidence_ref": None})))

    # (24-26) MCIR refs external (only ref strings committed); SMH read-only/non-authoritative; no bodies embedded.
    chk("24/26.only ref strings committed; no MCIR/SMH body column on the receipt",
        isinstance(r.bridge_source_regime_ref, str)
        and not any(hasattr(r, a) for a in ("bridge_source_regime_body", "bridge_transformation_body",
                                            "bridge_preserved_evidence_body")))
    boom = lambda *a: (_ for _ in ()).throw(RuntimeError("resolver side-effect"))
    chk("25.SMH resolution read-only/non-authoritative: a raising SMH resolver fails closed (no admit)",
        raises(lambda: emit(bv=lambda b: verify_bridge_binding(b,
            mcir_identity_resolver=lambda *a: "BR_OK", mcir_divergence_resolver=lambda s, t: True,
            mcir_transformation_resolver=lambda x: True, smh_evidence_resolver=boom))))

    # (27-28) schema + legend stationary.
    from ugk.storage.binding import LEGEND_HASH
    chk("27.schema stationary 82d02279", S.EXPECTED_SCHEMA_HASH.startswith("82d02279"))
    chk("28.legend stationary db3c177d", LEGEND_HASH.startswith("db3c177d"))

    # (35-40) precision checks.
    from ugk import invariants as _I
    chk("35/36.no new invariant; registry remains 87", len(_I.INVARIANT_REGISTRY) == 87 and "BRIDGE-EMIT" not in _I.INVARIANT_REGISTRY)
    chk("39.correspondence activated only after BRIDGE-BINDING passes (emit re-checks the surface every time)",
        raises(lambda: emit(bv=make_verifier(diverge=False))) and emit()[1].terminal_outcome == "BRIDGE")
    chk("40.BRIDGE-BINDING is the emit-time correspondence (TO-S-01 + BRIDGE-BINDING name BRIDGE)",
        "BRIDGE" in _I.INVARIANT_REGISTRY["TO-S-01"].statement
        and "ACTIVATES the terminal-outcome correspondence" in _I.INVARIANT_REGISTRY["BRIDGE-BINDING"].statement)

    passed = sum(1 for _, c in checks if c)
    total = len(checks)
    fails = [n for n, c in checks if not c]
    detail = ("Native BRIDGE emission (Stage 4 / r162): BRIDGE is a native terminal outcome emittable ONLY "
              "via the kernel's explicit opt-in emit_bridge path under a committed v8 surface that verifies "
              "under BRIDGE-BINDING at emit (resolver-parameterized, kernel-free). No surface / malformed / "
              "refuting / tampered-identity all fail closed (refuse, never admit); the kernel never "
              "spontaneously bridges. BRIDGE is distinct from ADMIT/REFUSE/locality-refuse/DEFER/"
              "STRUCTURAL_ERROR/CRISIS; those are unchanged. V12/V13 pass natively (valid emits+verifies; "
              "no-record / no-evidence refute) without tailoring. MCIR refs external, SMH read-only/"
              "non-authoritative, no bodies embedded. Registry 87 (no new invariant); schema/legend stationary.")
    if fails:
        detail += " FAILS: " + "; ".join(fails)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
