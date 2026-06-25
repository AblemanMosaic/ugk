"""ugk/conformance/external_irreversible_pilot_gate.py - r115 / AD-44.

Conformance-only pilot for the EXTERNAL_IRREVERSIBLE two-phase trail (the four-state model). It drives
the kernel's PREPARE / COMMIT / ABORT / orphan-PREPARE path end-to-end with ZERO real external action
and ZERO production callsite, using a purpose-built `external append-once sink`:

  - EXTERNAL_SINK is an in-process list modelling irreversible external state: once (key,payload) is
    appended, the kernel CANNOT un-append it (you cannot un-send). It lives in the gate, not the store,
    so the store seam genuinely cannot roll it back.
  - the effect idempotently appends (key,payload): if `key` already present it does NOT append again
    (external dedup) - this is what makes a MANUAL retry after an in-doubt state safe, and why the key
    is required.

Cases proven (the ones r115 must specify):
  (1) clean success            -> COMMIT (confirmed performed); sink has the entry; success after effect
  (2) confirmed non-performance-> effect raises ExternalEffectNotPerformed -> ABORT (failed=True,
                                  abort_reason=external_effect_not_performed); sink UNCHANGED; not a rollback
  (3) ambiguous failure        -> effect performs the act then raises a NON-designated exception -> kernel
                                  writes NO terminal and re-raises -> orphan PREPARE (in-doubt)
  (4) outcome-write failure     -> effect succeeds but the COMMIT store.write raises -> no terminal
                                  persists -> orphan PREPARE (in-doubt about the record)
  (5) orphan detection         -> detect_orphan_prepares flags exactly the in-doubt PREPAREs (cases 3,4)
                                  and NOT the success/abort attempts; the kernel never infers an outcome
  plus: required idempotency_key fail-closed (missing/empty -> ProtocolError, ZERO mutation, no PREPARE);
  the sink's append-once dedup; PREPARE/COMMIT/ABORT marker shapes; anti-vacuity (success truly appends).

confess-and-audit: the kernel records the attempt and the outcome; it does NOT prevent, sandbox, or
reverse the act, and NEVER auto-retries. The required idempotency_key lets the external system dedup a
deliberate, out-of-band MANUAL retry.
"""


def run():
    import tempfile
    from ugk.kernel import (GovernanceKernel, EffectAtomicity, ProtocolError,
                            ExternalEffectNotPerformed)
    from ugk.storage.store import UGKReceiptStore
    from ugk.integrity.external_irreversible import detect_orphan_prepares, summarize, probe
    fails = []

    def drive(k, key, effect, params=None):
        # Pass effect_atomicity + idempotency_key via dynamic **kwargs (a dict, not a callsite literal)
        # so tools/effect_declaration_probe.py's per-callsite literal-class scan stays clean: this
        # conformance fixture is invisible to the probe's production-callsite census (r104 convention).
        kw = {"effect": effect,
              "effect_atomicity": EffectAtomicity.EXTERNAL_IRREVERSIBLE,
              "idempotency_key": key}
        return k.execute(op="crp_evidence", authority="adm", parameters=params or {},
                         gate=lambda: True, **kw)

    def mk():
        db = tempfile.mktemp(suffix=".db")
        k = GovernanceKernel(store=UGKReceiptStore(db_path=db)); k.open_session()
        return k, db

    def fresh(db):
        return UGKReceiptStore(db_path=db, read_only=True)

    # ---- the purpose-built external append-once sink (irreversible external state) ----
    SINK = []   # list of (key, payload); modelling "you cannot un-send"

    def append_once(key, payload):
        for (k_, _p) in SINK:
            if k_ == key:
                return ("dedup", key)        # already present: external dedup, no re-append
        SINK.append((key, payload))
        return ("appended", key)

    def succeed(key, payload):
        return lambda: append_once(key, payload)

    def confirmed_nonperf():
        # proves the act did NOT happen (does not touch the sink) -> ABORT
        raise ExternalEffectNotPerformed("dry-run: proved the external act was not performed")

    def ambiguous(key, payload):
        # the act HAPPENS, then a NON-designated failure: genuinely in-doubt from the trail's view
        def _e():
            append_once(key, payload)
            raise ValueError("ambiguous post-act failure (status unknown)")
        return _e

    def _ef(r, marker):
        # r142 (AD-65): column-first (v>=4 / v5 authoritative), marker fallback (v<4 fixtures)
        _c = {"phase": "effect_phase", "effect_atomicity": "effect_atomicity",
              "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
              "compensate_ref": "effect_compensate_ref", "gate_admit_ref": "effect_gate_admit_ref",
              "abort_reason": "effect_abort_reason",
              "compensation_idempotency_key": "effect_compensation_idempotency_key"}
        v = getattr(r, _c[marker], None)
        return v if v is not None else (r.parameters or {}).get(marker)

    def by_key(receipts, phase, key):
        return [r for r in receipts
                if _ef(r, "phase") == phase
                and _ef(r, "effect_atomicity") == "external_irreversible"
                and _ef(r, "idempotency_key") == key]

    # ============ kernel A: success / confirmed-abort / ambiguous-orphan (shared chain) ============
    kA, dbA = mk()

    # (1) clean success -> COMMIT
    rv = drive(kA, "k-ok", succeed("k-ok", "p1"))
    if rv != ("appended", "k-ok"):
        fails.append("(1) success effect result not returned (%r)" % (rv,))
    if ("k-ok", "p1") not in SINK:
        fails.append("(1) success did not append to the external sink (anti-vacuity)")

    # (2) confirmed non-performance -> ABORT, sink unchanged
    sink_before = list(SINK)
    raised2 = False
    try:
        drive(kA, "k-abort", confirmed_nonperf)
    except ExternalEffectNotPerformed:
        raised2 = True
    if not raised2:
        fails.append("(2) confirmed non-performance did not propagate ExternalEffectNotPerformed")
    if SINK != sink_before:
        fails.append("(2) confirmed non-performance changed the external sink (must be unchanged)")

    # (3) ambiguous failure -> no terminal, re-raise -> orphan PREPARE; sink DID get the act
    raised3 = False
    try:
        drive(kA, "k-doubt", ambiguous("k-doubt", "p3"))
    except ValueError:
        raised3 = True
    except ExternalEffectNotPerformed:
        fails.append("(3) ambiguous failure was misclassified as confirmed non-performance")
    if not raised3:
        fails.append("(3) ambiguous failure did not re-raise the original exception")
    if ("k-doubt", "p3") not in SINK:
        fails.append("(3) ambiguous effect should have performed the act (sink missing the entry)")

    recA = fresh(dbA).all_receipts()

    # marker shapes (PREPARE / COMMIT / ABORT)
    prep_ok = by_key(recA, "prepare", "k-ok")
    com_ok = by_key(recA, "commit", "k-ok")
    if len(prep_ok) != 1:
        fails.append("(1) expected exactly one PREPARE for k-ok (got %d)" % len(prep_ok))
    if len(com_ok) != 1:
        fails.append("(1) expected exactly one COMMIT for k-ok (got %d)" % len(com_ok))
    elif prep_ok and com_ok:
        if _ef(com_ok[0], "prepare_ref") != prep_ok[0].h_r:
            fails.append("(1) COMMIT.prepare_ref does not point back to the PREPARE h_r")
        if com_ok[0].failed:
            fails.append("(1) COMMIT receipt must be failed=False (confirmed performed)")
        if _ef(prep_ok[0], "gate_admit_ref") in (None, ""):
            fails.append("(1) PREPARE missing gate_admit_ref")

    ab = by_key(recA, "abort", "k-abort")
    if len(ab) != 1:
        fails.append("(2) expected exactly one ABORT for k-abort (got %d)" % len(ab))
    else:
        if not ab[0].failed:
            fails.append("(2) ABORT receipt must be failed=True")
        if _ef(ab[0], "abort_reason") != "external_effect_not_performed":
            fails.append("(2) ABORT.abort_reason != external_effect_not_performed (%s)"
                         % _ef(ab[0], "abort_reason"))
        prep_ab = by_key(recA, "prepare", "k-abort")
        if not prep_ab or _ef(ab[0], "prepare_ref") != prep_ab[0].h_r:
            fails.append("(2) ABORT.prepare_ref does not point back to its PREPARE")
    # ABORT must never be readable as a rollback/undo (scan the params AND the v5 abort_reason column):
    if any("undo" in str(r.parameters).lower()
           or "rollback" in str(_ef(r, "abort_reason") or "").lower()
           or "undo" in str(_ef(r, "abort_reason") or "").lower()
           for r in ab):
        fails.append("(2) ABORT must not claim rollback/undo for EXTERNAL_IRREVERSIBLE")

    # (3) orphan: PREPARE for k-doubt, NO terminal
    if len(by_key(recA, "prepare", "k-doubt")) != 1:
        fails.append("(3) expected a PREPARE for k-doubt")
    if by_key(recA, "commit", "k-doubt") or by_key(recA, "abort", "k-doubt"):
        fails.append("(3) in-doubt attempt must have NO terminal (false terminal written)")

    # (5a) detector on chain A -> exactly one orphan: k-doubt (NOT k-ok, NOT k-abort)
    orphansA = detect_orphan_prepares(recA)
    keysA = {o["idempotency_key"] for o in orphansA}
    if keysA != {"k-doubt"}:
        fails.append("(5) detector on chain A flagged %r, expected {'k-doubt'}" % (keysA,))
    if orphansA and orphansA[0]["state"] != "in_doubt":
        fails.append("(5) orphan state must be 'in_doubt'")
    sumA = summarize(recA)
    if sumA["counts"] != {"prepare": 3, "commit": 1, "abort": 1}:
        fails.append("(5) summarize counts unexpected: %r" % (sumA["counts"],))

    # ============ kernel B: outcome-write failure -> orphan ============
    kB, dbB = mk()
    _orig_write = kB.store.write

    def failing_commit_write(*a, **kw):
        # r139 (Lane 1): the canonical write-boundary effect value moved to effect_columns; detect the
        # COMMIT terminal via the descriptor first, retaining the legacy parameters-marker fallback.
        phase = ((kw.get("effect_columns") or {}).get("effect_phase")
                 or (kw.get("parameters") or {}).get("phase"))
        if phase == "commit":
            raise RuntimeError("simulated outcome-write failure")
        return _orig_write(*a, **kw)
    kB.store.write = failing_commit_write

    raised4 = False
    try:
        drive(kB, "k-owf", succeed("k-owf", "p4"))
    except RuntimeError:
        raised4 = True
    if not raised4:
        fails.append("(4) outcome-write failure did not propagate")
    if ("k-owf", "p4") not in SINK:
        fails.append("(4) outcome-write-fail case should have performed the act (sink missing entry)")
    kB.store.write = _orig_write   # restore for the read-back
    recB = fresh(dbB).all_receipts()
    if len(by_key(recB, "prepare", "k-owf")) != 1:
        fails.append("(4) expected a durable PREPARE for k-owf")
    if by_key(recB, "commit", "k-owf"):
        fails.append("(4) COMMIT must NOT be durable when its write failed")
    orphansB = detect_orphan_prepares(recB)
    if {o["idempotency_key"] for o in orphansB} != {"k-owf"}:
        fails.append("(4/5) detector on chain B did not flag exactly k-owf (%r)"
                     % ([o["idempotency_key"] for o in orphansB],))

    # ============ required idempotency_key fail-closed (ZERO mutation, no PREPARE) ============
    for badkey, label in [(None, "missing"), ("", "empty")]:
        kC, dbC = mk()
        n_before = fresh(dbC).receipt_count() if hasattr(fresh(dbC), "receipt_count") else len(fresh(dbC).all_receipts())
        threw = False
        try:
            drive(kC, badkey, succeed("k-nokey", "x"))
        except ProtocolError:
            threw = True
        if not threw:
            fails.append("(key) %s idempotency_key did not fail closed with ProtocolError" % label)
        recC = fresh(dbC).all_receipts()
        if any(_ef(r, "phase") == "prepare" for r in recC):
            fails.append("(key) %s key wrote a PREPARE before failing closed (must be zero mutation)" % label)

    # ============ append-once dedup (the sink models external dedup) ============
    pre = len([1 for (kk, _p) in SINK if kk == "k-ok"])
    again = append_once("k-ok", "p1-retry")
    if again != ("dedup", "k-ok"):
        fails.append("(dedup) repeated key did not dedup (%r)" % (again,))
    if len([1 for (kk, _p) in SINK if kk == "k-ok"]) != pre:
        fails.append("(dedup) repeated key double-appended to the external sink")

    # ============ r119: enriched orphan descriptors + reusable read-only probe ============
    # (r119-a) the chain-A k-doubt orphan carries the additive operator-triage fields, drawn from the
    #          source PREPARE receipt; the strict orphan determination is unaffected. k-doubt has no
    #          terminal anywhere here, so key_has_terminal is False / phases [].
    od = orphansA[0] if orphansA else {}
    _srcp = by_key(recA, "prepare", "k-doubt")
    src = _srcp[0] if _srcp else None
    for f in ("prepare_ts", "gate_admit_ref", "key_has_terminal", "key_terminal_phases"):
        if f not in od:
            fails.append("(r119-a) enriched orphan descriptor missing field %r" % f)
    if src is not None:
        if od.get("prepare_ts") != getattr(src, "timestamp", None):
            fails.append("(r119-a) prepare_ts does not match the source PREPARE timestamp")
        if od.get("gate_admit_ref") != _ef(src, "gate_admit_ref"):
            fails.append("(r119-a) gate_admit_ref does not match the source PREPARE marker")
    if od.get("key_has_terminal") is not False or od.get("key_terminal_phases") != []:
        fails.append("(r119-a) k-doubt (no terminal anywhere) must annotate key_has_terminal=False, phases=[]")

    # (r119-b) THE CENTRAL r119 INVARIANT -- strict per-prepare_ref orphan semantics PRESERVED under a
    #          SAME-KEY retry. An ambiguous attempt (orphan PREPARE#1, key k-retry) followed by a same-key
    #          retry (PREPARE#2 + COMMIT#2, a DIFFERENT prepare_ref) must STILL flag PREPARE#1 as in-doubt:
    #          the later same-key terminal does NOT silently clear it. It is only ANNOTATED
    #          (key_has_terminal=True, phases=['commit']) so an operator can see the key was resolved on
    #          some attempt while this attempt stays in-doubt.
    kD, dbD = mk()
    try:
        drive(kD, "k-retry", ambiguous("k-retry", "pd1"))   # PREPARE#1 -> act -> ambiguous raise -> orphan
    except ValueError:
        pass
    drive(kD, "k-retry", succeed("k-retry", "pd2"))         # PREPARE#2 -> dedup -> COMMIT#2 (diff prepare_ref)
    recD = fresh(dbD).all_receipts()
    orphansD = [o for o in detect_orphan_prepares(recD) if o["idempotency_key"] == "k-retry"]
    prepsD = by_key(recD, "prepare", "k-retry")
    commitsD = by_key(recD, "commit", "k-retry")
    if len(prepsD) != 2 or len(commitsD) != 1:
        fails.append("(r119-b) expected 2 PREPAREs + 1 COMMIT for k-retry (got %d/%d)" % (len(prepsD), len(commitsD)))
    if len(orphansD) != 1:
        fails.append("(r119-b) same-key retry must leave EXACTLY ONE orphan (PREPARE#1), got %d" % len(orphansD))
    else:
        oD = orphansD[0]
        committed_prepare_refs = {_ef(c, "prepare_ref") for c in commitsD}
        if oD["prepare_ref"] in committed_prepare_refs:
            fails.append("(r119-b) flagged orphan's prepare_ref was actually committed (strict match-rule leak)")
        if oD["state"] != "in_doubt":
            fails.append("(r119-b) same-key-retry orphan must stay 'in_doubt' (NOT silently cleared by COMMIT#2)")
        if oD.get("key_has_terminal") is not True or oD.get("key_terminal_phases") != ["commit"]:
            fails.append("(r119-b) same-key-retry orphan must annotate key_has_terminal=True, phases=['commit']")

    # (r119-c) the reusable read-only probe is the stable summarize() alias -- pure, no mutation.
    if probe(recA) != summarize(recA):
        fails.append("(r119-c) probe() must equal summarize() (stable read-only entrypoint)")
    _n = len(recA)
    _ = probe(recA)
    if len(recA) != _n:
        fails.append("(r119-c) probe() mutated the receipt list (must be read-only)")

    # ============ r121: bounded COMMIT/ABORT terminal-write retry (AD-46) ============
    import sqlite3
    from ugk.kernel import TerminalWriteExhausted, MAX_OUTCOME_WRITE_ATTEMPTS

    def inject_terminal_write_faults(k, fail_phases, n_fail, exc_factory):
        """Patch k._emit_irreversible to raise exc_factory() the first n_fail times it is called for a
        phase in fail_phases, then delegate. PREPARE (phase not in fail_phases) always passes through.
        Records every phase call so we can count attempts and prove the retry path was / was not entered."""
        orig = k._emit_irreversible
        st = {"left": n_fail, "calls": []}
        def patched(op, authority, base_params, phase, *a, **kw):
            st["calls"].append(phase)
            if phase in fail_phases and st["left"] > 0:
                st["left"] -= 1
                raise exc_factory()
            return orig(op, authority, base_params, phase, *a, **kw)
        k._emit_irreversible = patched
        return st
    LOCK = lambda: sqlite3.OperationalError("database is locked")

    def eff_spy(key, payload):
        box = {"n": 0}
        def _e():
            box["n"] += 1
            return append_once(key, payload)
        return _e, box

    TERMINAL_PARAM_KEYS = {"phase", "effect_atomicity", "idempotency_key", "prepare_ref"}

    # (r121-T) TRANSIENT commit-write failure -> clean COMMIT, NO orphan, effect ONCE, NO retry field.
    kT, dbT = mk(); stT = inject_terminal_write_faults(kT, {"commit"}, 2, LOCK)
    effT, boxT = eff_spy("k-rT", "pT")
    drive(kT, "k-rT", effT)
    recT = fresh(dbT).all_receipts()
    commitsT = by_key(recT, "commit", "k-rT")
    orphansT = [o for o in detect_orphan_prepares(recT) if o["idempotency_key"] == "k-rT"]
    if len(commitsT) != 1:
        fails.append("(r121-T) transient: expected exactly 1 COMMIT, got %d" % len(commitsT))
    if orphansT:
        fails.append("(r121-T) transient: COMMIT succeeded on retry but an orphan was flagged")
    if boxT["n"] != 1:
        fails.append("(r121-T) transient: effect must run exactly once, ran %d" % boxT["n"])
    if stT["calls"].count("commit") != 3:
        fails.append("(r121-T) transient: expected 3 commit-write attempts (2 fail + 1 ok), got %d" % stT["calls"].count("commit"))
    if commitsT:  # Option A: the terminal carries NO retry/attempt marker (params identical to a clean one)
        cp = set((commitsT[0].parameters or {}).keys())
        if any(("attempt" in kk.lower() or "retry" in kk.lower()) for kk in cp):
            fails.append("(r121-T) Option A violated: COMMIT carries a retry/attempt param %r" % sorted(cp))
        if cp - TERMINAL_PARAM_KEYS:
            fails.append("(r121-T) Option A violated: COMMIT carries unexpected param(s) %r" % sorted(cp - TERMINAL_PARAM_KEYS))

    # (r121-P) PERSISTENT commit-write failure -> NO terminal, orphan, TerminalWriteExhausted, effect ONCE.
    kP, dbP = mk(); inject_terminal_write_faults(kP, {"commit"}, MAX_OUTCOME_WRITE_ATTEMPTS, LOCK)
    effP, boxP = eff_spy("k-rP", "pP"); excP = None
    try:
        drive(kP, "k-rP", effP)
    except TerminalWriteExhausted as e:
        excP = e
    recP = fresh(dbP).all_receipts()
    commitsP = by_key(recP, "commit", "k-rP")
    orphansP = [o for o in detect_orphan_prepares(recP) if o["idempotency_key"] == "k-rP"]
    if excP is None:
        fails.append("(r121-P) persistent: expected TerminalWriteExhausted to propagate")
    elif excP.phase != "commit" or excP.attempts != MAX_OUTCOME_WRITE_ATTEMPTS:
        fails.append("(r121-P) persistent: wrong exhaustion signal (phase=%r attempts=%r)" % (excP.phase, excP.attempts))
    if commitsP:
        fails.append("(r121-P) persistent: a COMMIT persisted despite exhaustion (FALSE success)")
    if len(orphansP) != 1:
        fails.append("(r121-P) persistent: expected exactly 1 orphan PREPARE, got %d" % len(orphansP))
    if boxP["n"] != 1:
        fails.append("(r121-P) persistent: effect must run exactly once, ran %d" % boxP["n"])

    # (r121-Aeff) AMBIGUOUS effect failure -> orphan UNCHANGED, retry path NOT entered, effect ONCE.
    kA, dbA = mk(); stA = inject_terminal_write_faults(kA, {"commit", "abort"}, 9, LOCK)
    boxA = {"n": 0}
    def _amb():
        boxA["n"] += 1
        append_once("k-rA", "pA")
        raise ValueError("ambiguous post-act failure (status unknown)")
    try:
        drive(kA, "k-rA", _amb)
    except ValueError:
        pass
    recA2 = fresh(dbA).all_receipts()
    orphansA2 = [o for o in detect_orphan_prepares(recA2) if o["idempotency_key"] == "k-rA"]
    if stA["calls"].count("commit") != 0 or stA["calls"].count("abort") != 0:
        fails.append("(r121-Aeff) ambiguous: terminal-write retry was ENTERED (commit=%d abort=%d) -- must NOT be" %
                     (stA["calls"].count("commit"), stA["calls"].count("abort")))
    if len(orphansA2) != 1:
        fails.append("(r121-Aeff) ambiguous: expected exactly 1 orphan, got %d" % len(orphansA2))
    if boxA["n"] != 1:
        fails.append("(r121-Aeff) ambiguous: effect must run exactly once, ran %d" % boxA["n"])

    # (r121-CNP) CONFIRMED non-performance -> ABORT under the SAME retry: transient abort then clean ABORT.
    kC, dbC = mk(); stC = inject_terminal_write_faults(kC, {"abort"}, 1, LOCK)
    boxC = {"n": 0}
    def _nonperf():
        boxC["n"] += 1
        raise ExternalEffectNotPerformed("proved the act was not performed")
    try:
        drive(kC, "k-rC", _nonperf)
    except ExternalEffectNotPerformed:
        pass
    recC = fresh(dbC).all_receipts()
    abortsC = by_key(recC, "abort", "k-rC")
    orphansC = [o for o in detect_orphan_prepares(recC) if o["idempotency_key"] == "k-rC"]
    if len(abortsC) != 1:
        fails.append("(r121-CNP) confirmed-nonperf: expected exactly 1 ABORT after retry, got %d" % len(abortsC))
    if orphansC:
        fails.append("(r121-CNP) confirmed-nonperf: ABORT succeeded on retry but an orphan was flagged")
    if stC["calls"].count("abort") != 2:
        fails.append("(r121-CNP) confirmed-nonperf: expected 2 abort-write attempts (1 fail + 1 ok), got %d" % stC["calls"].count("abort"))
    if boxC["n"] != 1:
        fails.append("(r121-CNP) confirmed-nonperf: effect must run exactly once, ran %d" % boxC["n"])

    # (r121-D) NO DUPLICATE TERMINAL across retries: the transient (T) case left exactly ONE COMMIT + ONE PREPARE.
    if len(commitsT) > 1:
        fails.append("(r121-D) duplicate terminal: %d COMMITs for one (key,prepare_ref)" % len(commitsT))
    if len(by_key(recT, "prepare", "k-rT")) != 1:
        fails.append("(r121-D) transient produced != 1 PREPARE for k-rT")

    # (r121-disc) RETRYABLE-SET DISCIPLINE: a NON-retryable write error fails closed IMMEDIATELY (1 attempt).
    kN, dbN = mk(); stN = inject_terminal_write_faults(kN, {"commit"}, 9, lambda: sqlite3.OperationalError("no such column: x"))
    effN, boxN = eff_spy("k-rN", "pN"); excN = None
    try:
        drive(kN, "k-rN", effN)
    except TerminalWriteExhausted as e:
        excN = ("EXHAUSTED", e)
    except sqlite3.OperationalError as e:
        excN = ("IMMEDIATE", e)
    recN = fresh(dbN).all_receipts()
    orphansN = [o for o in detect_orphan_prepares(recN) if o["idempotency_key"] == "k-rN"]
    if not excN or excN[0] != "IMMEDIATE":
        fails.append("(r121-disc) non-retryable error must fail closed IMMEDIATELY (got %r)" % (excN[0] if excN else None))
    if stN["calls"].count("commit") != 1:
        fails.append("(r121-disc) non-retryable: expected exactly 1 commit attempt (NO retry), got %d" % stN["calls"].count("commit"))
    if len(orphansN) != 1:
        fails.append("(r121-disc) non-retryable: expected exactly 1 orphan, got %d" % len(orphansN))

    # (r121-vac) ANTI-VACUITY: a clean COMMIT with NO injected fault succeeds, effect once, exactly 1 attempt.
    kV, dbV = mk(); stV = inject_terminal_write_faults(kV, set(), 0, LOCK)  # empty fail set -> never fails, only counts
    effV, boxV = eff_spy("k-rV", "pV")
    drive(kV, "k-rV", effV)
    recV = fresh(dbV).all_receipts()
    if len(by_key(recV, "commit", "k-rV")) != 1:
        fails.append("(r121-vac) anti-vacuity: clean COMMIT did not produce exactly 1 terminal")
    if stV["calls"].count("commit") != 1:
        fails.append("(r121-vac) anti-vacuity: clean path took != 1 commit attempt (%d)" % stV["calls"].count("commit"))
    if boxV["n"] != 1:
        fails.append("(r121-vac) anti-vacuity: effect ran %d times" % boxV["n"])

    # ============ r123: governed orphan reconciliation op (AD-47) ============
    from ugk.kernel import ReconciliationRefused

    def build_orphan(key, payload):
        """Drive a real EXTERNAL_IRREVERSIBLE op whose effect happens then raises a non-designated
        exception -> a genuine orphan PREPARE (no terminal). Returns (kernel, db, prepare_ref)."""
        kk, dbk = mk()
        try:
            drive(kk, key, ambiguous(key, payload))
        except Exception:
            pass
        orphs = [o for o in detect_orphan_prepares(kk._store.all_receipts()) if o["idempotency_key"] == key]
        return kk, dbk, (orphs[0]["prepare_ref"] if orphs else None)

    def rterms(kk, phase, key):
        return [r for r in kk._store.all_receipts()
                if _ef(r, "phase") == phase and _ef(r, "idempotency_key") == key]
    def rorphans(kk, key):
        return [o for o in detect_orphan_prepares(kk._store.all_receipts()) if o["idempotency_key"] == key]
    def refused_reason(fn):
        try:
            fn(); return None
        except ReconciliationRefused as e:
            return e.reason
    PROV = ("reconciled", "reconciled_by", "reconciliation_evidence_ref", "determination")

    # (r123-R-COMMIT) performed -> exactly 1 reconciling COMMIT, orphan cleared, markers present, NO effect run.
    kRC, dbRC, prefRC = build_orphan("k-recC", "pRC")
    sink_pre = list(SINK)
    kRC.reconcile_external_irreversible(prepare_ref=prefRC, determination="performed",
                                        evidence_ref="ext://c", authority="ops")
    cRC = rterms(kRC, "commit", "k-recC")
    if len(cRC) != 1:
        fails.append("(r123-R-COMMIT) expected exactly 1 reconciling COMMIT, got %d" % len(cRC))
    if rorphans(kRC, "k-recC"):
        fails.append("(r123-R-COMMIT) orphan not cleared after reconcile-performed")
    if SINK != sink_pre:
        fails.append("(r123-R-COMMIT) reconciliation mutated the external sink (ran an effect) -- must NOT")
    if cRC:
        p = cRC[0].parameters or {}
        if not (p.get("reconciled") is True and p.get("reconciled_by") == "ops"
                and p.get("reconciliation_evidence_ref") == "ext://c" and p.get("determination") == "performed"):
            fails.append("(r123-R-COMMIT) provenance markers missing/wrong: %r" % {k_: p.get(k_) for k_ in PROV})

    # (r123-R-ABORT) not_performed -> exactly 1 reconciling ABORT (reconciled_not_performed), cleared, no effect.
    kRA, dbRA, prefRA = build_orphan("k-recA", "pRA")
    sink_pre = list(SINK)
    kRA.reconcile_external_irreversible(prepare_ref=prefRA, determination="not_performed",
                                        evidence_ref="ext://a", authority="ops")
    aRA = rterms(kRA, "abort", "k-recA")
    if len(aRA) != 1:
        fails.append("(r123-R-ABORT) expected exactly 1 reconciling ABORT, got %d" % len(aRA))
    if rorphans(kRA, "k-recA"):
        fails.append("(r123-R-ABORT) orphan not cleared after reconcile-not_performed")
    if SINK != sink_pre:
        fails.append("(r123-R-ABORT) reconciliation mutated the external sink -- must NOT")
    if aRA:
        p = aRA[0].parameters or {}
        if _ef(aRA[0], "abort_reason") != "reconciled_not_performed":
            fails.append("(r123-R-ABORT) abort_reason must be 'reconciled_not_performed', got %r" % _ef(aRA[0], "abort_reason"))
        if not (p.get("reconciled") is True and p.get("determination") == "not_performed"):
            fails.append("(r123-R-ABORT) provenance markers missing/wrong: %r" % {k_: p.get(k_) for k_ in PROV})

    # (r123-R-no-evidence) missing evidence -> refused, orphan stays, no terminal.
    kNE, _, prefNE = build_orphan("k-recNE", "pNE")
    rea = refused_reason(lambda: kNE.reconcile_external_irreversible(prepare_ref=prefNE, determination="performed",
                                                                     evidence_ref="", authority="ops"))
    if rea != "evidence-required":
        fails.append("(r123-R-no-evidence) expected refusal 'evidence-required', got %r" % rea)
    if not rorphans(kNE, "k-recNE") or rterms(kNE, "commit", "k-recNE") or rterms(kNE, "abort", "k-recNE"):
        fails.append("(r123-R-no-evidence) orphan must remain and NO terminal written")

    # (r123-R-no-authority) missing authority -> refused, orphan stays.
    kNA, _, prefNA = build_orphan("k-recNA", "pNA")
    rea = refused_reason(lambda: kNA.reconcile_external_irreversible(prepare_ref=prefNA, determination="performed",
                                                                     evidence_ref="e", authority=""))
    if rea != "authority-required":
        fails.append("(r123-R-no-authority) expected refusal 'authority-required', got %r" % rea)
    if not rorphans(kNA, "k-recNA"):
        fails.append("(r123-R-no-authority) orphan must remain")

    # (r123-R-cannot-determine) inconclusive determination -> first-class refusal, orphan stays.
    kCD, _, prefCD = build_orphan("k-recCD", "pCD")
    rea = refused_reason(lambda: kCD.reconcile_external_irreversible(prepare_ref=prefCD, determination="cannot_determine",
                                                                     evidence_ref="e", authority="ops"))
    if rea != "determination-undetermined":
        fails.append("(r123-R-cannot-determine) expected refusal 'determination-undetermined', got %r" % rea)
    if not rorphans(kCD, "k-recCD"):
        fails.append("(r123-R-cannot-determine) orphan must remain (system never forces a terminal)")

    # (r123-R-unknown-ref) unknown prepare_ref -> refused, nothing written.
    kUR, _, _ = build_orphan("k-recUR", "pUR")
    rea = refused_reason(lambda: kUR.reconcile_external_irreversible(prepare_ref="deadbeef00", determination="performed",
                                                                     evidence_ref="e", authority="ops"))
    if rea != "not-an-outstanding-orphan":
        fails.append("(r123-R-unknown-ref) expected refusal 'not-an-outstanding-orphan', got %r" % rea)

    # (r123-R-double) reconciling an already-reconciled ref -> refused, still exactly ONE terminal.
    kDB, _, prefDB = build_orphan("k-recDB", "pDB")
    kDB.reconcile_external_irreversible(prepare_ref=prefDB, determination="performed", evidence_ref="e", authority="ops")
    rea = refused_reason(lambda: kDB.reconcile_external_irreversible(prepare_ref=prefDB, determination="performed",
                                                                     evidence_ref="e", authority="ops"))
    if rea != "not-an-outstanding-orphan":
        fails.append("(r123-R-double) second reconcile must refuse 'not-an-outstanding-orphan', got %r" % rea)
    if len(rterms(kDB, "commit", "k-recDB")) != 1:
        fails.append("(r123-R-double) duplicate terminal: %d COMMITs" % len(rterms(kDB, "commit", "k-recDB")))

    # (r123-R-strict-ref) two same-key orphan attempts; reconciling one leaves the OTHER orphaned.
    kRS, dbRS = mk()
    for _ in range(2):
        try:
            drive(kRS, "k-recS", ambiguous("k-recS", "pRS"))
        except Exception:
            pass
    osS = [o for o in detect_orphan_prepares(kRS._store.all_receipts()) if o["idempotency_key"] == "k-recS"]
    if len(osS) != 2:
        fails.append("(r123-R-strict) expected 2 same-key orphan attempts, got %d" % len(osS))
    else:
        kRS.reconcile_external_irreversible(prepare_ref=osS[0]["prepare_ref"], determination="performed",
                                            evidence_ref="e", authority="ops")
        leftS = [o for o in detect_orphan_prepares(kRS._store.all_receipts()) if o["idempotency_key"] == "k-recS"]
        if len(leftS) != 1 or leftS[0]["prepare_ref"] != osS[1]["prepare_ref"]:
            fails.append("(r123-R-strict) reconciling one attempt must leave exactly the OTHER attempt orphaned")

    # (r123-R-provenance) an in-band COMMIT carries NO reconciled marker; a reconciled COMMIT does.
    kIB, dbIB = mk()
    drive(kIB, "k-recIB", succeed("k-recIB", "pIB"))
    ibc = rterms(kIB, "commit", "k-recIB")
    if not ibc or "reconciled" in (ibc[0].parameters or {}):
        fails.append("(r123-R-provenance) in-band COMMIT must NOT carry a reconciled marker")
    if cRC and (cRC[0].parameters or {}).get("reconciled") is not True:
        fails.append("(r123-R-provenance) reconciled COMMIT must carry reconciled=true")

    # (r123-R-determinism) identical reconciliation inputs -> identical provenance markers (timestamp aside).
    kD1, _, pD1 = build_orphan("k-recD1", "pD1")
    kD2, _, pD2 = build_orphan("k-recD2", "pD2")
    r1 = kD1.reconcile_external_irreversible(prepare_ref=pD1, determination="performed", evidence_ref="ext://same", authority="ops")
    r2 = kD2.reconcile_external_irreversible(prepare_ref=pD2, determination="performed", evidence_ref="ext://same", authority="ops")
    m1 = {k_: (r1.parameters or {}).get(k_) for k_ in PROV}
    m2 = {k_: (r2.parameters or {}).get(k_) for k_ in PROV}
    if m1 != m2:
        fails.append("(r123-R-determinism) identical inputs produced differing markers: %r vs %r" % (m1, m2))

    # ============ r141 / AD-64: OPT-IN warrant-backed VERIFIED-GRADE reconciliation ============
    # Verified-grade verifies the ADMISSIBLE BASIS (warrant resolvable + hash-intact + current-frame-
    # bound + non-empty basis), NOT the external event. Opt-in: verified=False is unchanged (recorded).
    from ugk.governance.warrant import DecisionWarrant, WarrantStore

    def _warrant(kk, basis=(1,), law=None, legend=None):
        return DecisionWarrant.create(constitutional_basis=list(basis),
                                      law_hash=(law if law is not None else kk._law_hash),
                                      legend_hash=(legend if legend is not None else kk._legend_hash))

    # (r141-V-OK) valid warrant -> verified COMMIT: grade marker + committed warrant_id, orphan cleared, NO effect.
    kV, _, prefV = build_orphan("k-recV", "pV")
    wsV = WarrantStore(); kV.set_warrant_store(wsV); wV = _warrant(kV); wsV.write(wV)
    sink_pre = list(SINK)
    kV.reconcile_external_irreversible(prepare_ref=prefV, determination="performed",
                                       evidence_ref="ext://v", authority="ops",
                                       warrant_id=wV.warrant_hash, verified=True)
    cV = rterms(kV, "commit", "k-recV")
    if len(cV) != 1:
        fails.append("(r141-V-OK) expected exactly 1 verified COMMIT, got %d" % len(cV))
    if SINK != sink_pre:
        fails.append("(r141-V-OK) verified reconciliation ran an effect -- must NOT")
    if rorphans(kV, "k-recV"):
        fails.append("(r141-V-OK) orphan not cleared after verified reconcile")
    if cV:
        rcv = cV[0]; p = rcv.parameters or {}
        # r143/AD-66 (UGK-BODY-v6): grade is now the TYPED column, not a parameters marker.
        if rcv.reconciliation_grade != "verified":
            fails.append("(r141-V-OK) verified terminal missing typed reconciliation_grade=verified: %r" % rcv.reconciliation_grade)
        if rcv.warrant_id != wV.warrant_hash:
            fails.append("(r141-V-OK) verified terminal did not commit the cited warrant_id")
        # r143/AD-66: the snapshot is SELF-VERIFYING from receipt state alone -- sha256(snapshot)==warrant_id,
        # frame-bound to the receipt, non-empty basis. NO WarrantStore resolution is performed here.
        import hashlib as _hl, json as _js
        snp = rcv.reconciliation_warrant_snapshot
        if not snp:
            fails.append("(r143-V6-OK) verified terminal missing reconciliation_warrant_snapshot")
        elif _hl.sha256(snp.encode()).hexdigest() != rcv.warrant_id:
            fails.append("(r143-V6-OK) snapshot sha256 != committed warrant_id (not self-verifying)")
        else:
            _wb = _js.loads(snp)
            if _wb.get("law_hash") != rcv.law_hash or _wb.get("legend_hash") != rcv.legend_hash:
                fails.append("(r143-V6-OK) snapshot frame not bound to receipt frame")
            if not _wb.get("constitutional_basis"):
                fails.append("(r143-V6-OK) snapshot constitutional_basis empty")
            if _wb.get("result") != 9001:
                fails.append("(r144-RECON-S-01) snapshot.result != ADMIT (9001) -- verified must cite an admit-verdict warrant")
        if ("reconciliation_grade" in p) or ("reconciliation_warrant_snapshot" in p):
            fails.append("(r143-V6-OK) typed reconciliation surface must be STRIPPED from parameters (sole committed surface)")
        if not (p.get("reconciled") is True and p.get("determination") == "performed"):
            fails.append("(r141-V-OK) verified terminal lost base provenance")

    # (r141-V-recorded) recorded path (verified=False) carries NO grade marker and NO warrant_id -> the two
    # grades are structurally distinguishable and cannot launder (markers are kernel-built, no caller seam).
    kVR, _, prefVR = build_orphan("k-recVR", "pVR")
    kVR.reconcile_external_irreversible(prepare_ref=prefVR, determination="performed",
                                        evidence_ref="ext://vr", authority="ops")
    cVR = rterms(kVR, "commit", "k-recVR")
    if cVR:
        p = cVR[0].parameters or {}
        # r143/AD-66: laundering guard now over the TYPED columns -- recorded terminals carry NULL grade+snapshot.
        if cVR[0].reconciliation_grade is not None:
            fails.append("(r141-V-recorded) recorded terminal must carry NULL typed reconciliation_grade (laundering guard)")
        if cVR[0].reconciliation_warrant_snapshot is not None:
            fails.append("(r143-V6-recorded) recorded terminal must carry NULL reconciliation_warrant_snapshot")
        if ("reconciliation_grade" in p) or ("reconciliation_warrant_snapshot" in p):
            fails.append("(r141-V-recorded) recorded terminal must carry NO reconciliation surface in parameters")
        if cVR[0].warrant_id not in ("", None):
            fails.append("(r141-V-recorded) recorded terminal must carry NO warrant_id")

    # (r141-V-fc) every verified-mode violation REFUSES, orphan stays, NO terminal.
    def _vfc_orphan_intact(kk, key):
        return bool(rorphans(kk, key)) and not rterms(kk, "commit", key) and not rterms(kk, "abort", key)
    # no store
    kFNS, _, pFNS = build_orphan("k-vf-nostore", "pNS")
    if refused_reason(lambda: kFNS.reconcile_external_irreversible(prepare_ref=pFNS, determination="performed",
            evidence_ref="e", authority="ops", warrant_id="x", verified=True)) != "verified-requires-warrant-store" \
       or not _vfc_orphan_intact(kFNS, "k-vf-nostore"):
        fails.append("(r141-V-fc-nostore) expected verified-requires-warrant-store with orphan intact")
    # missing warrant id
    kFI, _, pFI = build_orphan("k-vf-noid", "pNI"); kFI.set_warrant_store(WarrantStore())
    if refused_reason(lambda: kFI.reconcile_external_irreversible(prepare_ref=pFI, determination="performed",
            evidence_ref="e", authority="ops", warrant_id="", verified=True)) != "verified-requires-warrant-id" \
       or not _vfc_orphan_intact(kFI, "k-vf-noid"):
        fails.append("(r141-V-fc-noid) expected verified-requires-warrant-id with orphan intact")
    # warrant not found
    kFN, _, pFN = build_orphan("k-vf-nf", "pNF"); kFN.set_warrant_store(WarrantStore())
    if refused_reason(lambda: kFN.reconcile_external_irreversible(prepare_ref=pFN, determination="performed",
            evidence_ref="e", authority="ops", warrant_id="deadbeef", verified=True)) != "warrant-not-found" \
       or not _vfc_orphan_intact(kFN, "k-vf-nf"):
        fails.append("(r141-V-fc-nf) expected warrant-not-found with orphan intact")
    # hash invalid (tampered warrant returned by a stub store)
    class _StubStore:
        def __init__(self, w): self._w = w
        def get(self, wid): return self._w
    kFH, _, pFH = build_orphan("k-vf-hash", "pHF"); wH = _warrant(kFH)
    object.__setattr__(wH, "constitutional_basis", (1, 2, 3))  # tamper after hashing -> verify_hash() False
    kFH.set_warrant_store(_StubStore(wH))
    if refused_reason(lambda: kFH.reconcile_external_irreversible(prepare_ref=pFH, determination="performed",
            evidence_ref="e", authority="ops", warrant_id=wH.warrant_hash, verified=True)) != "warrant-hash-invalid" \
       or not _vfc_orphan_intact(kFH, "k-vf-hash"):
        fails.append("(r141-V-fc-hash) expected warrant-hash-invalid with orphan intact")
    # stale frame (warrant binds a different law_hash)
    kFS, _, pFS = build_orphan("k-vf-stale", "pST"); wsS = WarrantStore(); kFS.set_warrant_store(wsS)
    wS = _warrant(kFS, law="00" * 32); wsS.write(wS)
    if refused_reason(lambda: kFS.reconcile_external_irreversible(prepare_ref=pFS, determination="performed",
            evidence_ref="e", authority="ops", warrant_id=wS.warrant_hash, verified=True)) != "warrant-stale-frame" \
       or not _vfc_orphan_intact(kFS, "k-vf-stale"):
        fails.append("(r141-V-fc-stale) expected warrant-stale-frame with orphan intact")
    # empty basis
    kFB, _, pFB = build_orphan("k-vf-basis", "pEB"); wsB = WarrantStore(); kFB.set_warrant_store(wsB)
    wB = _warrant(kFB, basis=()); wsB.write(wB)
    if refused_reason(lambda: kFB.reconcile_external_irreversible(prepare_ref=pFB, determination="performed",
            evidence_ref="e", authority="ops", warrant_id=wB.warrant_hash, verified=True)) != "warrant-basis-invalid" \
       or not _vfc_orphan_intact(kFB, "k-vf-basis"):
        fails.append("(r141-V-fc-basis) expected warrant-basis-invalid with orphan intact")

    ok = not fails
    return ok, (
        "EXTERNAL_IRREVERSIBLE two-phase pilot: PREPARE (intent-to-act, depth 0, before effect) -> "
        "effect -> COMMIT (confirmed performed, after effect) | ABORT (confirmed non-performance via "
        "ExternalEffectNotPerformed, failed=True, abort_reason=external_effect_not_performed, NOT a "
        "rollback) | no-terminal+re-raise (ambiguous or outcome-write failure) == orphan PREPARE "
        "(in-doubt), flagged by the deterministic orphan detector and never auto-resolved; required "
        "idempotency_key fails closed with zero mutation; append-once sink dedups a manual retry. "
        "r119: orphan descriptors enriched with prepare_ts / gate_admit_ref / key_has_terminal / "
        "key_terminal_phases (read-only triage, drawn from the receipts); the strict per-prepare_ref rule "
        "is preserved -- a same-key terminal under a different prepare_ref annotates but NEVER clears the "
        "orphan; probe() is the reusable read-only summarize() alias. r121/AD-46: the COMMIT/ABORT terminal "
        "store write has a BOUNDED retry (store write only, never the effect; MAX=3, narrow transient set) -- "
        "transient write failure -> clean terminal, persistent -> TerminalWriteExhausted + orphan, ambiguous "
        "effect never enters the retry, ABORT retried like COMMIT, no duplicate terminal, non-retryable fails "
        "closed immediately, effect runs exactly once on every path."
        if ok else "; ".join(fails))


if __name__ == "__main__":
    import sys
    ok, detail = run()
    print(f"external_irreversible_pilot_gate: {'PASS' if ok else 'FAIL'}  {detail}")
    sys.exit(0 if ok else 1)
