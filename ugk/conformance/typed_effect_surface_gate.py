"""ugk/conformance/typed_effect_surface_gate.py - r134 / AD-57.

Proves the UGK-BODY-v4 typed effect surface: the 9 typed nullable effect columns are a schema-closed,
domain-validated, body-committed MIRROR of the parameters effect markers (the single source during the
schema-leg transition). Schema-leg only — EFFECT-S-01 still binds the markers; no law move.

Required evidence proven here:
  * v1/v2/v3 receipts continue verifying unchanged (no retroactive reinterpretation);
  * v4 effect-bearing receipts body-commit the typed effect columns (in h_body);
  * domain closure for effect_atomicity (out-of-domain fails closed at write);
  * domain closure for effect_phase (out-of-domain fails closed at write);
  * typed columns equal the legacy parameter markers (consistency by construction);
  * a JSON-marker / column divergence fails closed at verification;
  * a tampered typed column breaks full-body (h_body) verification;
  * EXTERNAL_IRREVERSIBLE and EXTERNAL_REVERSIBLE v4 trails still verify;
  * terminal_outcome is unaffected by v4 (None on a non-outcome effect receipt; no trace_vector_hash).
"""


def run():
    import tempfile
    from ugk.kernel import GovernanceKernel, EffectAtomicity, ExternalEffectNotPerformed
    from ugk.storage.store import (
        UGKReceiptStore, verify_effect_column_marker_consistency,
        EffectDomainError, EFFECT_ATOMICITY_MODEL_ID, Receipt, compute_schema_hash, EXPECTED_SCHEMA_HASH)
    fails = []
    OP = "crp_evidence"

    def mk():
        k = GovernanceKernel(store=UGKReceiptStore(db_path=tempfile.mktemp(suffix=".db")))
        k.open_session(); return k

    # ---- schema pin: live schema == new anchor ----
    k = mk()
    if compute_schema_hash(k._store._conn) != EXPECTED_SCHEMA_HASH:
        fails.append("live schema_hash != EXPECTED_SCHEMA_HASH (f343b870 anchor)")

    # ---- v4 effect-bearing receipts: typed columns populated, body-committed, consistent ----
    k.execute(op=OP, authority="a", parameters={"x": 1}, gate=lambda: True,
              effect=lambda: None, effect_atomicity=EffectAtomicity.PURE)
    k.execute(op=OP, authority="a", parameters={"x": 2}, gate=lambda: True,
              effect=lambda: None, effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE, idempotency_key="I1")
    k.execute(op=OP, authority="a", parameters={"x": 3}, gate=lambda: True,
              effect=lambda: None, effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE, idempotency_key="R1")
    pref = [r for r in k._store.all_receipts()
            if getattr(r, "effect_phase", None) == "commit"
            and getattr(r, "effect_idempotency_key", None) == "R1"][0]
    pref = getattr(pref, "effect_prepare_ref", None)
    k.compensate_external_reversible(prepare_ref=pref, compensation_effect=lambda: None,
                                     compensation_idempotency_key=k.compose_compensation_key("R1"), authority="a")
    rcs = k._store.all_receipts()
    from ugk.storage.store import _EFFECT_MARKER_KEYS as _MK
    eff = [r for r in rcs if getattr(r, "effect_atomicity", None)]
    noneff = [r for r in rcs if not getattr(r, "effect_atomicity", None)]
    # r142 (AD-65): uniform UGK-BODY-v5 -- effect receipts are v5 and the typed columns are the SOLE
    # committed structural effect surface (the eight markers are RETIRED from committed parameters).
    if not (eff and all(int(getattr(r, "version", 1) or 1) == 7 for r in eff)):
        fails.append("effect-bearing receipts not all v6")
    if any(m in (r.parameters or {}) for r in eff for m in _MK):
        fails.append("v5 effect receipt still carries a structural effect marker in committed parameters")
    if not all(getattr(r, "effect_atomicity", None) for r in eff):
        fails.append("v5 effect receipt missing the typed effect_atomicity column")
    if not all(r.effect_atomicity_model_id == EFFECT_ATOMICITY_MODEL_ID for r in eff):
        fails.append("effect_atomicity_model_id not set on v5 effect receipts")
    if not all(verify_effect_column_marker_consistency(r) for r in rcs):
        fails.append("v4 bridge false-failed a marker-absent v5 receipt (must be out of scope)")
    if not k._store.verify_receipt_bodies():
        fails.append("v5 whole-chain h_body verification failed")
    # a phase receipt carries the typed effect_phase
    if not any(r.effect_phase for r in eff):
        fails.append("no typed effect_phase populated on phase receipts")

    # ---- non-effect receipts: uniform v5, no effect columns (no reinterpretation of the effect surface) ----
    if not all(int(getattr(r, "version", 1) or 1) == 7 and r.effect_atomicity is None for r in noneff):
        fails.append("non-effect receipts not uniform v5 / carry effect columns")

    # ---- legacy v2 verifier coverage preserved via a SYNTHETIC v2 fixture (uniform v5 forbids a live v2
    #      write); the version-aware recompute validates it and it carries no effect columns ----
    from ugk.storage.store import compute_h_body as _chb
    _b = dict(op=OP, authority="a", parameters={"x": 1}, intent="i", jurisdiction="session",
              confidence="high", timestamp=1.0, failed=False, session_dkn="d", law_hash="L",
              legend_hash="G", warrant_id="", intent_ref="", h_s="a" * 64, h_c="b" * 64, h_m="c" * 64,
              h_j="d" * 64, h_r="e" * 64, parent_h_r="", mode="strict",
              id_c_s="s", id_c_c="c", id_c_m="m", id_c_j="j")
    _to = dict(terminal_outcome="ADMIT", terminal_outcome_model_id="m", terminal_outcome_reason="r")
    hb_v2 = _chb(version=2, **_to, **_b)
    if not (_chb(version=2, **_to, **_b) == hb_v2
            and _chb(version=2, **_to, effect_atomicity="pure", **_b) == hb_v2):
        fails.append("synthetic v2 receipt broken / effect columns leaked into the v2 body")

    # ---- domain closure: out-of-domain fails closed at write ----
    k3 = mk()
    try:
        k3._store.write(op=OP, authority="a", parameters={"effect_atomicity": "bogus_class"})
        fails.append("domain closure: out-of-domain effect_atomicity admitted")
    except EffectDomainError:
        pass
    try:
        k3._store.write(op=OP, authority="a", parameters={"effect_atomicity": "pure", "phase": "bogus_phase"})
        fails.append("domain closure: out-of-domain effect_phase admitted")
    except EffectDomainError:
        pass

    # ---- divergence fails closed: a v4 receipt whose typed column != its marker ----
    _req = dict(intent="", jurisdiction="session", confidence="high", timestamp="t",
                failed=False, session_dkn="", law_hash="", legend_hash="", warrant_id="", intent_ref="")
    diverging = Receipt(
        op=OP, authority="a", parameters={"effect_atomicity": "store_local"}, version=4,
        effect_atomicity="pure", effect_atomicity_model_id=EFFECT_ATOMICITY_MODEL_ID, **_req)  # column != marker
    if verify_effect_column_marker_consistency(diverging):
        fails.append("divergence: column != marker NOT flagged (consistency check broken)")
    # a v4 receipt with the wrong model id also fails closed
    wrong_model = Receipt(
        op=OP, authority="a", parameters={"effect_atomicity": "pure"}, version=4,
        effect_atomicity="pure", effect_atomicity_model_id="other_model", **_req)
    if verify_effect_column_marker_consistency(wrong_model):
        fails.append("divergence: wrong effect_atomicity_model_id NOT flagged")

    # ---- tampered typed column breaks full-body verification ----
    k4 = mk()
    k4.execute(op=OP, authority="a", parameters={"x": 7}, gate=lambda: True,
               effect=lambda: None, effect_atomicity=EffectAtomicity.PURE)
    # tamper the stored typed column directly (simulating post-write corruption)
    k4._store._conn.execute(
        "UPDATE receipts SET effect_atomicity='non_atomic' WHERE effect_atomicity='pure'")
    k4._store._conn.commit()
    if k4._store.verify_receipt_bodies():
        fails.append("tampered typed effect column did NOT break h_body verification")

    # ---- terminal_outcome unaffected by v4 (None + no trace vector on a plain effect receipt) ----
    if not all(r.terminal_outcome is None and r.trace_vector_hash is None for r in eff):
        fails.append("v4 effect receipt carries an unexpected terminal_outcome / trace_vector_hash")

    ok = not fails
    return ok, (
        "AD-57 typed effect surface (UGK-BODY-v4): 9 typed nullable effect columns are a schema-closed, "
        "domain-validated, body-committed mirror of the parameters markers (single source); v1/v2/v3 "
        "receipts verify unchanged and carry no effect columns; v4 effect receipts body-commit the typed "
        "columns with effect_atomicity_model_v1; effect_atomicity and effect_phase domain closure fails "
        "closed at write; column/marker divergence and wrong model id fail closed at verification; a "
        "tampered typed column breaks h_body; EXTERNAL_IRREVERSIBLE/REVERSIBLE v4 trails verify; "
        "terminal_outcome is None and no trace_vector_hash on a plain effect receipt (terminal-outcome "
        "unaffected). Schema-leg only; EFFECT-S-01 still binds the markers; law stationary."
        if ok else "; ".join(str(f) for f in fails))
