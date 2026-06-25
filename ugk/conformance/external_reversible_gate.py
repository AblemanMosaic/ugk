"""ugk/conformance/external_reversible_gate.py - r132 / AD-55.

Conformance-only gate for the EXTERNAL_REVERSIBLE (compensation / saga) trail. It drives the kernel's
FORWARD arc (PREPARE / COMMIT / ABORT / orphan-PREPARE) and the SEPARATELY-GOVERNED, SEPARATELY-
IDEMPOTENT COMPENSATION arc (COMPENSATE / COMPENSATED / COMPENSATION_FAILED / orphan-COMPENSATE) end to
end with ZERO real external action and ZERO production callsite, using purpose-built in-process sinks.

Cases proven (the required-evidence set):
  (1)  forward receipt-before-effect      -- PREPARE is durable when effect() runs; no COMMIT yet
  (2)  success -> COMMIT after effect; the COMMIT carries the idempotency_key verbatim
  (3)  confirmed-not-performed -> ABORT    (failed=True, abort_reason); forward sink UNCHANGED
  (4)  uncertain failure -> orphan PREPARE (no terminal); gate_admit ADMIT preserved; NO gate_refuse
  (5)  compensation receipt-before-effect  -- COMPENSATE is durable when the compensating action runs;
                                              no COMPENSATED yet
  (6)  compensation success -> COMPENSATED; the forward COMMIT REMAINS historically true (offset, not
                                              erasure -- same COMMIT h_r persists, unchanged)
  (7)  compensation failure -> COMPENSATION_FAILED (failed=True, UNRESOLVED execution status, NOT a
                                              REFUSE); the forward COMMIT still stands
  (8)  orphan PREPARE detected by detect_orphan_prepares
  (9)  orphan COMPENSATE detected by detect_orphan_compensates
  (10) detector NEVER auto-resolves         -- calling the detectors writes no receipts
  (11) missing original idempotency_key fails closed (ProtocolError, ZERO mutation, no PREPARE)
  (12) missing compensation idempotency_key fails closed (CompensationRefused, no receipt)
  (13) ambiguous/reused compensation idempotency fails closed (key == forward key -> CompensationRefused)
  (14) compensation guard: an aborted / in-doubt / already-compensated forward effect fails closed
  (15) no-physical-undo: COMPENSATED records an OFFSET; the forward COMMIT persists unchanged
  (16) anti-vacuity: a clean forward+compensation saga truly performs both actions

r136 bounded terminal-write retry (AD-46 pattern), forward {commit,abort} + compensation
{compensated,compensation_failed} terminals only -- the external act / compensating action live OUTSIDE
the durable helper and are NEVER re-invoked:
  (r136-Tf/Tc) transient store-write failure -> clean terminal after retry; effect/action runs ONCE;
               no orphan; forward COMMIT preserved on the compensation path; Option A (no retry param);
               EFFECT-S-01 conformant
  (r136-Pf/Pc) retry-budget exhaustion -> NO terminal persists; TerminalWriteExhausted; the orphan
               PREPARE/COMPENSATE STANDS and is still reported by the detector; effect/action ran ONCE
  (r136-Aeff)  ambiguous forward failure -> the terminal-retry is NOT entered; orphan unchanged
  (r136-CNPf)  confirmed non-performance under transient retry -> clean failed=True ABORT; never gate_refuse
  TO-S-01 effect-abort separation and EFFECT-S-01 trail-integrity remain intact under retry.

confess-and-audit: the kernel records the attempt and the outcome; it does NOT prevent, sandbox, or
reverse any external act, and NEVER auto-resolves. Compensation is a NEW FORWARD offsetting action, never
a physical undo. The required keys make deliberate out-of-band MANUAL retries externally dedup-safe.
"""


def run():
    import tempfile
    from ugk.kernel import (GovernanceKernel, EffectAtomicity, ProtocolError,
                            ExternalEffectNotPerformed, CompensationRefused)
    from ugk.storage.store import UGKReceiptStore
    from ugk.integrity.external_reversible import (
        detect_orphan_prepares, detect_orphan_compensates, find_committed_forward)
    fails = []
    OP = "crp_evidence"

    def mk():
        db = tempfile.mktemp(suffix=".db")
        k = GovernanceKernel(store=UGKReceiptStore(db_path=db)); k.open_session()
        return k

    def drive(k, key, effect, params=None):
        # dynamic **kwargs (dict, not a callsite literal) so the effect_declaration_probe's per-callsite
        # literal-class scan stays clean (r104 convention; this fixture is not a production callsite).
        kw = {"effect": effect, "effect_atomicity": EffectAtomicity.EXTERNAL_REVERSIBLE,
              "idempotency_key": key}
        return k.execute(op=OP, authority="adm", parameters=params or {}, gate=lambda: True, **kw)

    _C = {"effect_atomicity": "effect_atomicity", "phase": "effect_phase",
          "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
          "compensate_ref": "effect_compensate_ref",
          "compensation_idempotency_key": "effect_compensation_idempotency_key",
          "abort_reason": "effect_abort_reason", "gate_admit_ref": "effect_gate_admit_ref"}
    def _ef(r, marker):
        # r142 (AD-65): column-first (v>=4 / v5 authoritative), marker fallback (v<4 fixtures)
        v = getattr(r, _C[marker], None)
        return v if v is not None else (r.parameters or {}).get(marker)

    def rev(rcs, phase):
        return [r for r in rcs if _ef(r, "effect_atomicity") == "external_reversible"
                and _ef(r, "phase") == phase]

    def prepare_ref_of_commit(rcs, key):
        cs = [r for r in rev(rcs, "commit") if _ef(r, "idempotency_key") == key]
        return _ef(cs[0], "prepare_ref") if cs else None

    # ---- (1)(2)(16) forward success + receipt-before-effect + key verbatim + anti-vacuity ----
    k = mk()
    fsink = []
    rbe = {"prepare_present": False, "commit_absent": True}

    def fx_ok():
        rcs = k._store.all_receipts()
        rbe["prepare_present"] = len(rev(rcs, "prepare")) >= 1
        rbe["commit_absent"] = len(rev(rcs, "commit")) == 0
        fsink.append("performed")
    drive(k, "K1", fx_ok, {"amt": 100})
    rcs = k._store.all_receipts()
    if not rbe["prepare_present"]:
        fails.append("(1) PREPARE not durable when forward effect ran")
    if not rbe["commit_absent"]:
        fails.append("(1) COMMIT existed before forward effect returned (receipt-before-effect broken)")
    commits = rev(rcs, "commit")
    if len(commits) != 1:
        fails.append("(2) expected exactly 1 forward COMMIT, got %d" % len(commits))
    elif _ef(commits[0], "idempotency_key") != "K1":
        fails.append("(2) COMMIT did not carry the verbatim key")
    if fsink != ["performed"]:
        fails.append("(16) anti-vacuity: forward effect did not perform exactly once")

    # ---- (3) confirmed-not-performed -> ABORT, sink unchanged ----
    k = mk()
    asink = []

    def fx_notperformed():
        raise ExternalEffectNotPerformed("provably not performed")
    try:
        drive(k, "K2", fx_notperformed)
        fails.append("(3) ExternalEffectNotPerformed did not propagate")
    except ExternalEffectNotPerformed:
        pass
    rcs = k._store.all_receipts()
    aborts = rev(rcs, "abort")
    if len(aborts) != 1 or not aborts[0].failed:
        fails.append("(3) expected exactly one failed ABORT terminal")
    elif _ef(aborts[0], "abort_reason") != "external_effect_not_performed":
        fails.append("(3) ABORT missing abort_reason")
    if rev(rcs, "commit"):
        fails.append("(3) a COMMIT was written on the confirmed-not-performed path")
    if asink:
        fails.append("(3) sink mutated on a confirmed-not-performed effect")

    # ---- (4) uncertain failure -> orphan PREPARE; ADMIT preserved; no gate_refuse ----
    k = mk()

    def fx_uncertain():
        raise RuntimeError("ambiguous failure after possibly acting")
    try:
        drive(k, "K3", fx_uncertain)
        fails.append("(4) uncertain failure did not propagate")
    except RuntimeError:
        pass
    rcs = k._store.all_receipts()
    if rev(rcs, "commit") or rev(rcs, "abort"):
        fails.append("(4) a terminal was written on an uncertain failure (should be orphan)")
    if not [r for r in rcs if r.op == "gate_admit" and not r.failed]:
        fails.append("(4) gate_admit (ADMIT decision) absent after uncertain failure")
    if [r for r in rcs if r.op == "gate_refuse"]:
        fails.append("(4) a gate_refuse was written (uncertain failure must NOT become a REFUSE)")
    orphans4 = detect_orphan_prepares(rcs)
    if len(orphans4) != 1:
        fails.append("(4)/(8) expected exactly one orphan PREPARE, got %d" % len(orphans4))

    # ---- (5)(6)(15) compensation success + receipt-before-effect + COMMIT remains true ----
    k = mk()
    drive(k, "K5", lambda: None, {"amt": 50})
    rcs = k._store.all_receipts()
    pref = prepare_ref_of_commit(rcs, "K5")
    commit_hr_before = rev(rcs, "commit")[0].h_r
    csink = []
    crbe = {"compensate_present": False, "compensated_absent": True}

    def cfx_ok():
        rr = k._store.all_receipts()
        crbe["compensate_present"] = len(rev(rr, "compensate")) >= 1
        crbe["compensated_absent"] = len(rev(rr, "compensated")) == 0
        csink.append("offset")
    k.compensate_external_reversible(
        prepare_ref=pref, compensation_effect=cfx_ok,
        compensation_idempotency_key=k.compose_compensation_key("K5"), authority="adm")
    rcs = k._store.all_receipts()
    if not crbe["compensate_present"]:
        fails.append("(5) COMPENSATE not durable when compensating action ran")
    if not crbe["compensated_absent"]:
        fails.append("(5) COMPENSATED existed before the compensating action returned")
    if len(rev(rcs, "compensated")) != 1:
        fails.append("(6) expected exactly one COMPENSATED terminal")
    commits_after = rev(rcs, "commit")
    if len(commits_after) != 1 or commits_after[0].h_r != commit_hr_before:
        fails.append("(6)/(15) forward COMMIT not historically preserved after COMPENSATED (erasure?)")
    if csink != ["offset"]:
        fails.append("(16) anti-vacuity: compensating action did not perform exactly once")
    # no-physical-undo: COMPENSATED must not claim erasure/undo
    comp_terminal = rev(rcs, "compensated")[0].parameters
    if any(comp_terminal.get(k_) for k_ in ("undone", "reversed", "erased", "rolled_back")):
        fails.append("(15) COMPENSATED carries a physical-undo claim")

    # ---- (7) compensation failure -> COMPENSATION_FAILED, unresolved, not REFUSE; COMMIT stands ----
    k = mk()
    drive(k, "K7", lambda: None)
    rcs = k._store.all_receipts()
    pref7 = prepare_ref_of_commit(rcs, "K7")

    def cfx_fail():
        raise RuntimeError("offset action failed")
    try:
        k.compensate_external_reversible(
            prepare_ref=pref7, compensation_effect=cfx_fail,
            compensation_idempotency_key="COMP-7", authority="adm")
        fails.append("(7) compensation failure did not propagate")
    except RuntimeError:
        pass
    rcs = k._store.all_receipts()
    cfailed = rev(rcs, "compensation_failed")
    if len(cfailed) != 1 or not cfailed[0].failed:
        fails.append("(7) expected exactly one failed COMPENSATION_FAILED terminal")
    if [r for r in rcs if r.op == "gate_refuse"]:
        fails.append("(7) compensation failure became a gate_refuse (must be execution status)")
    if len(rev(rcs, "commit")) != 1:
        fails.append("(7) forward COMMIT not preserved after COMPENSATION_FAILED")

    # ---- (9) orphan COMPENSATE detected (compensate with no terminal) ----
    # synthesize an in-doubt compensation: the compensating action crashes BEFORE its terminal is
    # writable is not directly forceable, so we model an orphan via a compensate whose terminal never
    # arrives by detecting on the COMPENSATION_FAILED-suppressed state. Instead: drive a fresh commit,
    # then call compensate with an action that itself prevents the terminal by raising a NON-Exception?
    # Cleaner: a COMPENSATE with no terminal is what the detector keys on; we produce one by writing the
    # COMPENSATE intent then NOT its terminal -- exercised here via a compensating action that records an
    # orphan by raising AFTER we have asserted (7) handles the failed-terminal case. We instead build the
    # orphan directly through the kernel's emit path on a committed forward effect.
    k = mk()
    drive(k, "K9", lambda: None)
    rcs = k._store.all_receipts()
    pref9 = prepare_ref_of_commit(rcs, "K9")
    fwd9 = find_committed_forward(rcs, pref9)
    # write ONLY the COMPENSATE intent (no terminal) via the kernel helper -> orphan COMPENSATE.
    k._emit_reversible(fwd9["op"], "adm", {"compensates_prepare_ref": pref9}, "compensate",
                       fwd9["idempotency_key"], "session", "", "", failed=False,
                       compensate_ref=pref9, compensation_idempotency_key="COMP-9")
    rcs = k._store.all_receipts()
    oc = detect_orphan_compensates(rcs)
    if len(oc) != 1 or oc[0]["compensate_ref"] != pref9:
        fails.append("(9) orphan COMPENSATE not detected exactly once")

    # ---- (10) detectors never auto-resolve (no receipts written by detection) ----
    before = len(k._store.all_receipts())
    detect_orphan_prepares(rcs); detect_orphan_compensates(rcs); find_committed_forward(rcs, pref9)
    after = len(k._store.all_receipts())
    if before != after:
        fails.append("(10) a detector mutated the store (must be read-only / never auto-resolve)")

    # ---- (11) missing original idempotency_key fails closed, zero mutation, no PREPARE ----
    k = mk()
    n0 = len(k._store.all_receipts())
    try:
        k.execute(op=OP, authority="adm", parameters={}, gate=lambda: True,
                  effect=lambda: None, effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE)
        fails.append("(11) missing original key was admitted (should fail closed)")
    except ProtocolError:
        rcs = k._store.all_receipts()
        if len(rcs) != n0:
            fails.append("(11) missing-key path mutated the store (expected zero mutation)")
        if rev(rcs, "prepare"):
            fails.append("(11) a PREPARE was written despite the missing-key fail-closed")

    # ---- (12)(13)(14) compensation fail-closed contract ----
    k = mk()
    drive(k, "K12", lambda: None)
    rcs = k._store.all_receipts()
    pref12 = prepare_ref_of_commit(rcs, "K12")
    n1 = len(k._store.all_receipts())
    # (12) missing compensation key
    try:
        k.compensate_external_reversible(prepare_ref=pref12, compensation_effect=lambda: None,
                                         compensation_idempotency_key="", authority="adm")
        fails.append("(12) missing compensation key was accepted")
    except CompensationRefused:
        pass
    # (13) ambiguous/reused compensation key (== forward key)
    try:
        k.compensate_external_reversible(prepare_ref=pref12, compensation_effect=lambda: None,
                                         compensation_idempotency_key="K12", authority="adm")
        fails.append("(13) ambiguous compensation key (== forward key) was accepted")
    except CompensationRefused:
        pass
    # (14a) compensating an in-doubt / unknown forward effect fails closed
    try:
        k.compensate_external_reversible(prepare_ref="deadbeef", compensation_effect=lambda: None,
                                         compensation_idempotency_key="COMP-X", authority="adm")
        fails.append("(14) compensating an unknown forward ref was accepted")
    except CompensationRefused:
        pass
    if len(k._store.all_receipts()) != n1:
        fails.append("(12)/(13)/(14) a refused compensation mutated the store (expected zero mutation)")
    # (14b) double-compensation fails closed
    k.compensate_external_reversible(prepare_ref=pref12, compensation_effect=lambda: None,
                                     compensation_idempotency_key="COMP-12A", authority="adm")
    try:
        k.compensate_external_reversible(prepare_ref=pref12, compensation_effect=lambda: None,
                                         compensation_idempotency_key="COMP-12B", authority="adm")
        fails.append("(14) double-compensation of one forward COMMIT was accepted")
    except CompensationRefused:
        pass
    # (14c) compensating a confirmed-aborted forward effect fails closed
    k2 = mk()
    try:
        k2.execute(op=OP, authority="adm", parameters={}, gate=lambda: True,
                   effect=lambda: (_ for _ in ()).throw(ExternalEffectNotPerformed("np")),
                   effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE, idempotency_key="K14C")
    except ExternalEffectNotPerformed:
        pass
    rcs2 = k2._store.all_receipts()
    aborts2 = rev(rcs2, "abort")
    pref14c = _ef(aborts2[0], "prepare_ref") if aborts2 else None
    try:
        k2.compensate_external_reversible(prepare_ref=pref14c, compensation_effect=lambda: None,
                                          compensation_idempotency_key="COMP-14C", authority="adm")
        fails.append("(14) compensating a confirmed-ABORTED forward effect was accepted")
    except CompensationRefused:
        pass

    # ============ r136: bounded reversible TERMINAL-write retry (mirrors r121 / AD-46) ============
    # Bounded retry of the FORWARD (commit/abort) and COMPENSATION (compensated/compensation_failed)
    # terminal store writes ONLY. The external effect and the compensating action live OUTSIDE the durable
    # helper and are NEVER re-invoked. Proves: transient store failure -> clean terminal; exhaustion ->
    # honest in-doubt orphan (no false terminal); effect/compensating-action run exactly once across
    # retries; ambiguous failure does not enter the terminal-retry; orphan detectors still report;
    # TO-S-01 effect-abort separation (no gate_refuse); EFFECT-S-01 trail-integrity (no false flag);
    # Option A (the terminal carries no retry/attempt param).
    import sqlite3
    from ugk.kernel import TerminalWriteExhausted, MAX_OUTCOME_WRITE_ATTEMPTS
    from ugk.conformance.effect_trail_integrity_gate import verify_effect_trail_integrity
    LOCK = lambda: sqlite3.OperationalError("database is locked")
    REV_TERMINAL_KEYS = {"phase", "effect_atomicity", "idempotency_key", "prepare_ref", "gate_admit_ref",
                         "abort_reason", "compensate_ref", "compensation_idempotency_key",
                         "compensates_prepare_ref"}

    def inject_rev_terminal_faults(k, fail_phases, n_fail, exc_factory):
        """Patch k._emit_reversible to raise exc_factory() the first n_fail times it is called for a phase
        in fail_phases, then delegate. Intent writes (prepare/compensate) are never in fail_phases, so they
        always pass through. Records every phase call to count terminal-write attempts."""
        orig = k._emit_reversible
        st = {"left": n_fail, "calls": []}
        def patched(op, authority, base_params, phase, *a, **kw):
            st["calls"].append(phase)
            if phase in fail_phases and st["left"] > 0:
                st["left"] -= 1
                raise exc_factory()
            return orig(op, authority, base_params, phase, *a, **kw)
        k._emit_reversible = patched
        return st

    # (r136-Tf) TRANSIENT forward COMMIT-write failure -> clean COMMIT after retry; effect ONCE; no orphan;
    #           Option A (no retry/attempt param); EFFECT-S-01 conformant.
    kTf = mk(); stTf = inject_rev_terminal_faults(kTf, {"commit"}, 2, LOCK)
    boxTf = {"n": 0}
    def _fx_tf():
        boxTf["n"] += 1
    drive(kTf, "RT-Tf", _fx_tf)
    rTf = kTf._store.all_receipts(); commitsTf = rev(rTf, "commit")
    if len(commitsTf) != 1:
        fails.append("(r136-Tf) transient forward: expected exactly 1 COMMIT, got %d" % len(commitsTf))
    if detect_orphan_prepares(rTf):
        fails.append("(r136-Tf) transient forward: COMMIT succeeded on retry but an orphan was flagged")
    if boxTf["n"] != 1:
        fails.append("(r136-Tf) transient forward: effect must run exactly once, ran %d" % boxTf["n"])
    if stTf["calls"].count("commit") != 3:
        fails.append("(r136-Tf) transient forward: expected 3 commit-write attempts (2 fail + 1 ok), got %d" % stTf["calls"].count("commit"))
    if commitsTf:
        cp = set((commitsTf[0].parameters or {}).keys())
        if any(("attempt" in kk.lower() or "retry" in kk.lower()) for kk in cp):
            fails.append("(r136-Tf) Option A violated: COMMIT carries a retry/attempt param %r" % sorted(cp))
        if cp - REV_TERMINAL_KEYS:
            fails.append("(r136-Tf) Option A violated: COMMIT carries unexpected param(s) %r" % sorted(cp - REV_TERMINAL_KEYS))
    if verify_effect_trail_integrity(rTf):
        fails.append("(r136-Tf) EFFECT-S-01 flagged the retried-clean forward trail")

    # (r136-Pf) PERSISTENT forward COMMIT-write failure -> NO terminal, orphan stands, TerminalWriteExhausted,
    #           effect ONCE; detector still reports the orphan PREPARE.
    kPf = mk(); inject_rev_terminal_faults(kPf, {"commit"}, MAX_OUTCOME_WRITE_ATTEMPTS, LOCK)
    boxPf = {"n": 0}; excPf = None
    def _fx_pf():
        boxPf["n"] += 1
    try:
        drive(kPf, "RT-Pf", _fx_pf)
    except TerminalWriteExhausted as e:
        excPf = e
    rPf = kPf._store.all_receipts()
    if excPf is None:
        fails.append("(r136-Pf) persistent forward: expected TerminalWriteExhausted to propagate")
    elif excPf.phase != "commit" or excPf.attempts != MAX_OUTCOME_WRITE_ATTEMPTS:
        fails.append("(r136-Pf) persistent forward: wrong exhaustion signal (phase=%r attempts=%r)" % (excPf.phase, excPf.attempts))
    if rev(rPf, "commit"):
        fails.append("(r136-Pf) persistent forward: a COMMIT persisted despite exhaustion (FALSE success)")
    if len(detect_orphan_prepares(rPf)) != 1:
        fails.append("(r136-Pf) persistent forward: expected exactly 1 orphan PREPARE, got %d" % len(detect_orphan_prepares(rPf)))
    if boxPf["n"] != 1:
        fails.append("(r136-Pf) persistent forward: effect must run exactly once, ran %d" % boxPf["n"])

    # (r136-Aeff) AMBIGUOUS forward effect failure -> terminal-retry NOT entered, orphan unchanged, effect ONCE.
    kAf = mk(); stAf = inject_rev_terminal_faults(kAf, {"commit", "abort"}, 9, LOCK)
    boxAf = {"n": 0}
    def _fx_amb():
        boxAf["n"] += 1
        raise RuntimeError("ambiguous forward failure (status unknown)")
    try:
        drive(kAf, "RT-Aeff", _fx_amb)
    except RuntimeError:
        pass
    rAf = kAf._store.all_receipts()
    if stAf["calls"].count("commit") != 0 or stAf["calls"].count("abort") != 0:
        fails.append("(r136-Aeff) ambiguous forward: terminal-write retry was ENTERED (commit=%d abort=%d) -- must NOT be" % (stAf["calls"].count("commit"), stAf["calls"].count("abort")))
    if len(detect_orphan_prepares(rAf)) != 1:
        fails.append("(r136-Aeff) ambiguous forward: expected exactly 1 orphan, got %d" % len(detect_orphan_prepares(rAf)))
    if boxAf["n"] != 1:
        fails.append("(r136-Aeff) ambiguous forward: effect must run exactly once, ran %d" % boxAf["n"])

    # (r136-CNPf) CONFIRMED non-performance -> ABORT under transient retry: transient abort then clean ABORT;
    #             no orphan; effect ONCE; failed=True execution status, NEVER a gate_refuse (TO-S-01 sep).
    kCf = mk(); stCf = inject_rev_terminal_faults(kCf, {"abort"}, 1, LOCK)
    boxCf = {"n": 0}
    def _fx_np():
        boxCf["n"] += 1
        raise ExternalEffectNotPerformed("provably not performed")
    try:
        drive(kCf, "RT-CNPf", _fx_np)
    except ExternalEffectNotPerformed:
        pass
    rCf = kCf._store.all_receipts(); abortsCf = rev(rCf, "abort")
    if len(abortsCf) != 1 or not abortsCf[0].failed:
        fails.append("(r136-CNPf) confirmed-nonperf: expected exactly 1 failed ABORT after retry, got %d" % len(abortsCf))
    if detect_orphan_prepares(rCf):
        fails.append("(r136-CNPf) confirmed-nonperf: ABORT succeeded on retry but an orphan was flagged")
    if stCf["calls"].count("abort") != 2:
        fails.append("(r136-CNPf) confirmed-nonperf: expected 2 abort-write attempts (1 fail + 1 ok), got %d" % stCf["calls"].count("abort"))
    if [r for r in rCf if r.op == "gate_refuse"]:
        fails.append("(r136-CNPf) confirmed-nonperf: ABORT-on-retry became a gate_refuse (TO-S-01 separation broken)")
    if boxCf["n"] != 1:
        fails.append("(r136-CNPf) confirmed-nonperf: effect must run exactly once, ran %d" % boxCf["n"])

    # (r136-Tc) TRANSIENT COMPENSATED-write failure -> clean COMPENSATED after retry; compensating action
    #           ONCE; forward COMMIT preserved (offset not erasure); no orphan COMPENSATE; EFFECT-S-01 clean.
    kTc = mk(); drive(kTc, "RC-Tc", lambda: None)
    prefTc = prepare_ref_of_commit(kTc._store.all_receipts(), "RC-Tc")
    commit_hr_Tc = rev(kTc._store.all_receipts(), "commit")[0].h_r
    stTc = inject_rev_terminal_faults(kTc, {"compensated"}, 2, LOCK)
    boxTc = {"n": 0}
    def _cfx_tc():
        boxTc["n"] += 1
    kTc.compensate_external_reversible(prepare_ref=prefTc, compensation_effect=_cfx_tc,
                                       compensation_idempotency_key="COMP-RC-Tc", authority="adm")
    rTc = kTc._store.all_receipts()
    if len(rev(rTc, "compensated")) != 1:
        fails.append("(r136-Tc) transient compensation: expected exactly 1 COMPENSATED, got %d" % len(rev(rTc, "compensated")))
    if detect_orphan_compensates(rTc):
        fails.append("(r136-Tc) transient compensation: COMPENSATED succeeded on retry but an orphan COMPENSATE was flagged")
    if boxTc["n"] != 1:
        fails.append("(r136-Tc) transient compensation: compensating action must run exactly once, ran %d" % boxTc["n"])
    if stTc["calls"].count("compensated") != 3:
        fails.append("(r136-Tc) transient compensation: expected 3 compensated-write attempts (2 fail + 1 ok), got %d" % stTc["calls"].count("compensated"))
    commits_Tc = rev(rTc, "commit")
    if len(commits_Tc) != 1 or commits_Tc[0].h_r != commit_hr_Tc:
        fails.append("(r136-Tc) transient compensation: forward COMMIT not historically preserved (offset not erasure)")
    if verify_effect_trail_integrity(rTc):
        fails.append("(r136-Tc) EFFECT-S-01 flagged the retried-clean compensation trail")

    # (r136-Pc) PERSISTENT COMPENSATION_FAILED-write failure -> NO terminal, orphan COMPENSATE stands,
    #           TerminalWriteExhausted, compensating action ONCE; detector reports orphan; COMMIT preserved;
    #           never a gate_refuse.
    kPc = mk(); drive(kPc, "RC-Pc", lambda: None)
    prefPc = prepare_ref_of_commit(kPc._store.all_receipts(), "RC-Pc")
    inject_rev_terminal_faults(kPc, {"compensation_failed"}, MAX_OUTCOME_WRITE_ATTEMPTS, LOCK)
    boxPc = {"n": 0}; excPc = None
    def _cfx_pc():
        boxPc["n"] += 1
        raise RuntimeError("offset action failed")
    try:
        kPc.compensate_external_reversible(prepare_ref=prefPc, compensation_effect=_cfx_pc,
                                           compensation_idempotency_key="COMP-RC-Pc", authority="adm")
    except (TerminalWriteExhausted, RuntimeError) as e:
        excPc = e
    rPc = kPc._store.all_receipts()
    if not isinstance(excPc, TerminalWriteExhausted):
        fails.append("(r136-Pc) persistent compensation: expected TerminalWriteExhausted, got %r" % type(excPc).__name__)
    elif excPc.phase != "compensation_failed" or excPc.attempts != MAX_OUTCOME_WRITE_ATTEMPTS:
        fails.append("(r136-Pc) persistent compensation: wrong exhaustion signal (phase=%r attempts=%r)" % (excPc.phase, excPc.attempts))
    if rev(rPc, "compensation_failed") or rev(rPc, "compensated"):
        fails.append("(r136-Pc) persistent compensation: a compensation terminal persisted despite exhaustion (FALSE record)")
    if len(detect_orphan_compensates(rPc)) != 1:
        fails.append("(r136-Pc) persistent compensation: expected exactly 1 orphan COMPENSATE, got %d" % len(detect_orphan_compensates(rPc)))
    if boxPc["n"] != 1:
        fails.append("(r136-Pc) persistent compensation: compensating action must run exactly once, ran %d" % boxPc["n"])
    if len(rev(rPc, "commit")) != 1:
        fails.append("(r136-Pc) persistent compensation: forward COMMIT not preserved")
    if [r for r in rPc if r.op == "gate_refuse"]:
        fails.append("(r136-Pc) persistent compensation: exhaustion became a gate_refuse (must be execution status)")

    # ====================================================================== r137 / AD-60
    #   governed reconciliation of honest in-doubt residue (the AD-47 analogue for the reversible class)
    # ======================================================================
    from ugk.kernel import ReconciliationRefused
    from ugk.conformance.effect_trail_integrity_gate import verify_effect_trail_integrity

    def orphan_prepare(k, key):
        pr = k._emit_reversible(OP, "adm", {}, "prepare", key, "session", "", "",
                                failed=False, gate_admit_ref="g-recon")
        return pr.h_r

    def orphan_compensate(k, key, comp_key):
        drive(k, key, lambda: None)
        rcs = k._store.all_receipts()
        pref = prepare_ref_of_commit(rcs, key)
        fwd = find_committed_forward(rcs, pref)
        k._emit_reversible(fwd["op"], "adm", {"compensates_prepare_ref": pref}, "compensate",
                           fwd["idempotency_key"], "session", "", "", failed=False,
                           compensate_ref=pref, compensation_idempotency_key=comp_key)
        return pref

    # ---- (r137-RFa) forward orphan PREPARE + performed -> reconciling COMMIT clears it ----
    k = mk(); pr = orphan_prepare(k, "RF1")
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                            evidence_ref="ev-rf1", authority="ops")
    rcs = k._store.all_receipts()
    if detect_orphan_prepares(rcs):
        fails.append("(r137-RFa) forward performed: orphan PREPARE not cleared")
    cc = rev(rcs, "commit")[0].parameters
    if not (cc.get("reconciled") is True and cc.get("reconciled_by") == "ops"
            and cc.get("reconciliation_evidence_ref") == "ev-rf1" and cc.get("determination") == "performed"):
        fails.append("(r137-RFa) forward performed: provenance markers missing/incorrect")
    if rev(rcs, "commit")[0].failed:
        fails.append("(r137-RFa) forward performed: reconciling COMMIT marked failed")

    # ---- (r137-RFb) forward orphan PREPARE + not_performed -> reconciling ABORT (distinct reason) ----
    k = mk(); pr = orphan_prepare(k, "RF2")
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="not_performed",
                                            evidence_ref="ev-rf2", authority="ops")
    rcs = k._store.all_receipts()
    if detect_orphan_prepares(rcs):
        fails.append("(r137-RFb) forward not_performed: orphan PREPARE not cleared")
    ab_r = rev(rcs, "abort")[0]; ab = ab_r.parameters
    if _ef(ab_r, "abort_reason") != "reconciled_not_performed":
        fails.append("(r137-RFb) forward not_performed: abort_reason not the distinct reconciled reason")
    if not rev(rcs, "abort")[0].failed:
        fails.append("(r137-RFb) forward not_performed: reconciling ABORT not marked failed")
    if not ab.get("reconciled"):
        fails.append("(r137-RFb) forward not_performed: ABORT not provenance-marked")

    # ---- (r137-RCa) compensation orphan + performed -> reconciling COMPENSATED; COMMIT stays; no erasure ----
    k = mk(); pref = orphan_compensate(k, "RC1", "RCK1")
    k.reconcile_external_reversible_compensation(compensate_ref=pref, determination="performed",
                                                 evidence_ref="ev-rc1", authority="ops")
    rcs = k._store.all_receipts()
    if detect_orphan_compensates(rcs):
        fails.append("(r137-RCa) compensation performed: orphan COMPENSATE not cleared")
    cd = rev(rcs, "compensated")[0].parameters
    if not (cd.get("reconciled") is True and cd.get("determination") == "performed"
            and cd.get("arc") == "compensation"):
        fails.append("(r137-RCa) compensation performed: provenance markers missing/incorrect")
    if rev(rcs, "compensated")[0].failed:
        fails.append("(r137-RCa) compensation performed: reconciling COMPENSATED marked failed")
    if not [r for r in rcs if _ef(r, "phase") == "commit"
            and _ef(r, "idempotency_key") == "RC1"]:
        fails.append("(r137-RCa) compensation performed: forward COMMIT no longer historically true")

    # ---- (r137-RCb) compensation orphan + not_performed -> reconciling COMPENSATION_FAILED (distinct) ----
    k = mk(); pref = orphan_compensate(k, "RC2", "RCK2")
    k.reconcile_external_reversible_compensation(compensate_ref=pref, determination="not_performed",
                                                 evidence_ref="ev-rc2", authority="ops")
    rcs = k._store.all_receipts()
    if detect_orphan_compensates(rcs):
        fails.append("(r137-RCb) compensation not_performed: orphan COMPENSATE not cleared")
    cf_r = rev(rcs, "compensation_failed")[0]; cf = cf_r.parameters
    if _ef(cf_r, "abort_reason") != "reconciled_compensation_not_performed":
        fails.append("(r137-RCb) compensation not_performed: not the distinct reconciled compensation reason")
    if not rev(rcs, "compensation_failed")[0].failed:
        fails.append("(r137-RCb) compensation not_performed: COMPENSATION_FAILED not marked failed")

    # ---- (r137-RR) refusal taxonomy: each writes NOTHING and leaves the orphan untouched ----
    def fwd_refuse(call, sub):
        k = mk(); pr = orphan_prepare(k, "RRf"); n0 = len(k._store.all_receipts())
        try:
            call(k, pr); return "NO-REFUSE"
        except ReconciliationRefused as e:
            if len(k._store.all_receipts()) != n0: return "MUTATED"
            if len(detect_orphan_prepares(k._store.all_receipts())) != 1: return "ORPHAN-GONE"
            return "ok" if sub in str(e) else "WRONG-REASON:%s" % e
    for label, call, sub in [
        ("RR1-missing-authority",
         lambda k, pr: k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                                               evidence_ref="e", authority="  "),
         "authority-required"),
        ("RR2-missing-evidence",
         lambda k, pr: k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                                               evidence_ref="", authority="o"),
         "evidence-required"),
        ("RR3-inconclusive",
         lambda k, pr: k.reconcile_external_reversible_forward(prepare_ref=pr,
                                                               determination="cannot determine",
                                                               evidence_ref="e", authority="o"),
         "determination-undetermined"),
        ("RR3-none",
         lambda k, pr: k.reconcile_external_reversible_forward(prepare_ref=pr, determination=None,
                                                               evidence_ref="e", authority="o"),
         "determination-undetermined"),
        ("RR4-non-orphan",
         lambda k, pr: k.reconcile_external_reversible_forward(prepare_ref="not-an-orphan",
                                                               determination="performed",
                                                               evidence_ref="e", authority="o"),
         "not-an-outstanding-orphan"),
    ]:
        r = fwd_refuse(call, sub)
        if r != "ok":
            fails.append("(r137-%s) -> %s" % (label, r))

    # already-resolved target refuses (at-most-one-terminal per (key, ref)) ----
    k = mk(); pr = orphan_prepare(k, "RR5")
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                            evidence_ref="e", authority="o")
    n0 = len(k._store.all_receipts())
    try:
        k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                                evidence_ref="e", authority="o")
        fails.append("(r137-RR5) re-reconcile of a resolved ref did not refuse")
    except ReconciliationRefused as e:
        if len(k._store.all_receipts()) != n0:
            fails.append("(r137-RR5) re-reconcile mutated the store")
        if "not-an-outstanding-orphan" not in str(e):
            fails.append("(r137-RR5) re-reconcile wrong reason: %s" % e)

    # compensation-arc refusal: non-orphan compensate_ref writes nothing ----
    k = mk(); pref = orphan_compensate(k, "RR6", "RRK6"); n0 = len(k._store.all_receipts())
    try:
        k.reconcile_external_reversible_compensation(compensate_ref="no-such-compensate",
                                                     determination="performed",
                                                     evidence_ref="e", authority="o")
        fails.append("(r137-RR6) compensation non-orphan did not refuse")
    except ReconciliationRefused as e:
        if len(k._store.all_receipts()) != n0:
            fails.append("(r137-RR6) compensation non-orphan refusal mutated the store")
        if len(detect_orphan_compensates(k._store.all_receipts())) != 1:
            fails.append("(r137-RR6) compensation non-orphan refusal disturbed the orphan")

    # ---- (r137-RE) EFFECT-S-01 trail integrity stays clean across BOTH reconciled arcs ----
    k = mk()
    pr = orphan_prepare(k, "RE-f")
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="not_performed",
                                            evidence_ref="e", authority="o")
    prefc = orphan_compensate(k, "RE-c", "RE-ck")
    k.reconcile_external_reversible_compensation(compensate_ref=prefc, determination="performed",
                                                 evidence_ref="e", authority="o")
    rcs = k._store.all_receipts()
    v = verify_effect_trail_integrity(rcs)
    if v != []:
        fails.append("(r137-RE) EFFECT-S-01 violated by reconciled terminals: %r" % v)

    # ---- (r137-RT) TO-S-01: reconciliation never emits a gate_refuse (failures are execution status) ----
    if [r for r in rcs if r.op == "gate_refuse"]:
        fails.append("(r137-RT) reconciliation produced a gate_refuse (must be execution status, not REFUSE)")

    # ---- (r137-RL) no laundering: a reconciled terminal is distinct from an in-band one ----
    k = mk()
    drive(k, "RL-inband", lambda: None)                         # in-band COMMIT (no 'reconciled')
    pr = orphan_prepare(k, "RL-recon")
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                            evidence_ref="e", authority="o")
    rcs = k._store.all_receipts()
    inband = [r for r in rev(rcs, "commit") if _ef(r, "idempotency_key") == "RL-inband"][0]
    recon = [r for r in rev(rcs, "commit") if _ef(r, "idempotency_key") == "RL-recon"][0]
    if (inband.parameters or {}).get("reconciled"):
        fails.append("(r137-RL) in-band COMMIT carries a reconciled marker (laundering risk)")
    if not (recon.parameters or {}).get("reconciled"):
        fails.append("(r137-RL) reconciled COMMIT lacks its provenance marker")

    # ============ r141 / AD-64: OPT-IN warrant-backed VERIFIED-GRADE (forward + compensation arcs) ============
    from ugk.governance.warrant import DecisionWarrant, WarrantStore
    def _warrant(kk, basis=(1,), law=None):
        return DecisionWarrant.create(constitutional_basis=list(basis),
                                      law_hash=(law if law is not None else kk._law_hash),
                                      legend_hash=kk._legend_hash)
    # (r141-Vf-OK) forward verified COMMIT: grade marker + committed warrant_id, orphan cleared.
    k = mk(); pr = orphan_prepare(k, "RVF"); wsf = WarrantStore(); k.set_warrant_store(wsf)
    wf = _warrant(k); wsf.write(wf)
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                            evidence_ref="ev-rvf", authority="ops",
                                            warrant_id=wf.warrant_hash, verified=True)
    rcs = k._store.all_receipts()
    if detect_orphan_prepares(rcs):
        fails.append("(r141-Vf-OK) forward verified: orphan not cleared")
    cvf = rev(rcs, "commit")[0]
    import hashlib as _hl, json as _js
    def _v6_sv(r):
        # r143/AD-66: self-verify the typed verified-grade surface from receipt state ALONE (no WarrantStore).
        if r.reconciliation_grade != "verified" or not r.reconciliation_warrant_snapshot: return False
        if _hl.sha256(r.reconciliation_warrant_snapshot.encode()).hexdigest() != r.warrant_id: return False
        b=_js.loads(r.reconciliation_warrant_snapshot)
        return (b.get("law_hash")==r.law_hash and b.get("legend_hash")==r.legend_hash
                and bool(b.get("constitutional_basis")) and b.get("result")==9001)  # r144/RECON-S-01: result==ADMIT
    if cvf.reconciliation_grade != "verified" or cvf.warrant_id != wf.warrant_hash:
        fails.append("(r141-Vf-OK) forward verified terminal missing typed grade or committed warrant_id")
    if not _v6_sv(cvf):
        fails.append("(r143-V6f-OK) forward verified terminal snapshot not self-verifying")
    # (r141-Vf-recorded) forward recorded path carries NO grade marker / NO warrant_id (laundering guard).
    k = mk(); pr = orphan_prepare(k, "RVFr")
    k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                            evidence_ref="ev", authority="ops")
    crv = rev(k._store.all_receipts(), "commit")[0]
    if crv.reconciliation_grade is not None or crv.reconciliation_warrant_snapshot is not None or crv.warrant_id not in ("", None):
        fails.append("(r141-Vf-recorded) recorded forward terminal must carry NULL typed grade/snapshot and no warrant_id")
    # (r141-Vf-fc) forward verified fails closed (stale frame), orphan intact.
    k = mk(); pr = orphan_prepare(k, "RVFs"); wss = WarrantStore(); k.set_warrant_store(wss)
    ws = _warrant(k, law="00" * 32); wss.write(ws)
    try:
        k.reconcile_external_reversible_forward(prepare_ref=pr, determination="performed",
                                                evidence_ref="e", authority="ops",
                                                warrant_id=ws.warrant_hash, verified=True)
        fails.append("(r141-Vf-fc) forward verified stale-frame did NOT refuse")
    except ReconciliationRefused as e:
        if e.reason != "warrant-stale-frame":
            fails.append("(r141-Vf-fc) forward verified expected warrant-stale-frame, got %r" % e.reason)
    if len(detect_orphan_prepares(k._store.all_receipts())) != 1:
        fails.append("(r141-Vf-fc) forward verified refusal must leave the orphan intact")
    # (r141-Vc-OK) compensation verified COMPENSATED: grade marker + committed warrant_id, orphan cleared.
    k = mk(); pref = orphan_compensate(k, "RVC", "RVCK"); wsc = WarrantStore(); k.set_warrant_store(wsc)
    wc = _warrant(k); wsc.write(wc)
    k.reconcile_external_reversible_compensation(compensate_ref=pref, determination="performed",
                                                 evidence_ref="ev-rvc", authority="ops",
                                                 warrant_id=wc.warrant_hash, verified=True)
    rcs = k._store.all_receipts()
    if detect_orphan_compensates(rcs):
        fails.append("(r141-Vc-OK) compensation verified: orphan not cleared")
    cvc = rev(rcs, "compensated")[0]
    if cvc.reconciliation_grade != "verified" or cvc.warrant_id != wc.warrant_hash:
        fails.append("(r141-Vc-OK) compensation verified terminal missing typed grade or committed warrant_id")
    if not _v6_sv(cvc):
        fails.append("(r143-V6c-OK) compensation verified terminal snapshot not self-verifying")
    # (r141-Vc-fc) compensation verified fails closed (empty basis), orphan intact.
    k = mk(); pref = orphan_compensate(k, "RVCb", "RVCKb"); wsb = WarrantStore(); k.set_warrant_store(wsb)
    wb = _warrant(k, basis=()); wsb.write(wb)
    try:
        k.reconcile_external_reversible_compensation(compensate_ref=pref, determination="performed",
                                                     evidence_ref="e", authority="ops",
                                                     warrant_id=wb.warrant_hash, verified=True)
        fails.append("(r141-Vc-fc) compensation verified empty-basis did NOT refuse")
    except ReconciliationRefused as e:
        if e.reason != "warrant-basis-invalid":
            fails.append("(r141-Vc-fc) compensation verified expected warrant-basis-invalid, got %r" % e.reason)
    if len(detect_orphan_compensates(k._store.all_receipts())) != 1:
        fails.append("(r141-Vc-fc) compensation verified refusal must leave the orphan intact")

    ok = not fails
    return ok, (
        "r132/AD-55 EXTERNAL_REVERSIBLE compensation/saga: forward PREPARE->COMMIT|ABORT|orphan "
        "(receipt-before-effect; uncertain failure stays ADMIT, never REFUSE); separately-governed, "
        "separately-idempotent COMPENSATE->COMPENSATED|COMPENSATION_FAILED|orphan (receipt-before-"
        "compensating-effect; COMMIT stays historically true -- offset not erasure; failure is "
        "unresolved execution status not REFUSE); detectors flag both in-doubt arcs and never auto-"
        "resolve; missing original key, missing/ambiguous/reused compensation key, and "
        "non-compensable forward refs all fail closed; no physical-undo claim. "
        "r136 bounded terminal-write retry (AD-46 pattern) for forward commit/abort and compensation "
        "compensated/compensation_failed: transient store failure -> clean terminal; exhaustion -> "
        "honest in-doubt orphan (no false terminal, TerminalWriteExhausted); the external act and the "
        "compensating action run exactly once across retries; ambiguous failure never enters the "
        "terminal-retry; orphan detectors still report; no gate_refuse (TO-S-01); EFFECT-S-01 clean; "
        "Option A (no retry/attempt param in the receipt). "
        "r137/AD-60 governed reconciliation (the AD-47 analogue for the reversible class): an orphan "
        "forward PREPARE reconciles to a provenance-marked COMMIT (performed) or ABORT "
        "(reconciled_not_performed); an orphan COMPENSATE reconciles to a COMPENSATED (performed; offset "
        "not erasure, COMMIT stays true) or COMPENSATION_FAILED (reconciled_compensation_not_performed); "
        "authority + evidence_ref required and recorded-not-verified; determination closed-domain; "
        "inconclusive/missing-authority/missing-evidence/non-orphan/already-resolved all refuse writing "
        "nothing (orphan untouched); no effect or compensation action runs; reconciled terminals are "
        "distinct from in-band (no laundering); TO-S-01 (no gate_refuse) and EFFECT-S-01 stay clean." if ok else
        "; ".join(fails))


if __name__ == "__main__":
    import sys
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
    sys.exit(0 if ok else 1)
