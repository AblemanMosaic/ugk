"""ugk/conformance/broker_propagation_gate.py

r107 / AD-40 proof. LocalBrokerServer.submit() now propagates the CALLER-DECLARED EffectAtomicity to
kernel.execute() and chooses no class on the caller's behalf (the old line-141 NON_ATOMIC hardcode is
gone). This gate proves the fail-closed cutover:

  (1) no-effect request                 -> admitted (no declaration needed; no-effect exempt);
  (2) explicit PURE                      -> propagates; effect runs; kernel atomic-outcome writes the
                                            success receipt (exactly one, non-failed);
  (3) effect present + NO declaration    -> RECEIPTED refusal (failed=True broker_refused receipt),
                                            admitted=False, and NO false success;
  (4) explicit NON_ATOMIC                -> the legacy bridge proceeds (admitted);
  (5) unimplemented external classes      -> fail closed (admitted=False) with NO receipt
                                            (zero-mutation kernel preflight).

The broker is a faithful conduit: it does not default, downgrade, or invent a class.
"""


def _fresh():
    import tempfile, os
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    from ugk.transport.broker import LocalBrokerServer
    fd, p = tempfile.mkstemp(suffix=".db"); os.close(fd); os.unlink(p)
    k = GovernanceKernel(store=UGKReceiptStore(db_path=p)); k.open_session()
    return k, p, LocalBrokerServer(k)



# r142 (AD-65): column-first effect-field accessor for gate scaffolding/assertions. Reads the typed
# effect COLUMN (authoritative for v>=4, the sole surface on v5), with parameter-MARKER fallback only
# for deliberately-constructed v<4 marker-era fixtures.
_R142_C = {"phase": "effect_phase", "effect_atomicity": "effect_atomicity",
           "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
           "compensate_ref": "effect_compensate_ref",
           "compensation_idempotency_key": "effect_compensation_idempotency_key",
           "abort_reason": "effect_abort_reason", "gate_admit_ref": "effect_gate_admit_ref"}
def _ef(r, marker):
    v = getattr(r, _R142_C[marker], None)
    return v if v is not None else (r.parameters or {}).get(marker)

def run():
    import os
    from ugk.kernel import EffectAtomicity
    from ugk.transport.broker import GovernedRequest
    fails = []
    OP = "crp_evidence"

    def _nonfailed_success(store):
        return [r for r in store.all_receipts() if r.op == OP and not getattr(r, "failed", False)]

    # (1) no-effect -> exempt, admitted
    k, p, b = _fresh()
    try:
        r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 1}))
        if not r["admitted"]:
            fails.append("(1) no-effect request not admitted (no-effect exemption broken): %r" % r.get("reason"))
    finally:
        try: os.unlink(p)
        except OSError: pass

    # (2) explicit PURE -> propagates; effect runs; atomic-outcome success receipt present
    k, p, b = _fresh()
    try:
        ran = []
        r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 2},
                                     gate=lambda: True, effect=lambda: ran.append(True),
                                     effect_atomicity=EffectAtomicity.PURE))
        if not r["admitted"]:
            fails.append("(2) PURE not admitted: %r" % r.get("reason"))
        if not ran:
            fails.append("(2) PURE effect did not run")
        n = len(_nonfailed_success(k.store))
        if n != 1:
            fails.append("(2) PURE: expected exactly 1 non-failed success receipt, got %d" % n)
    finally:
        try: os.unlink(p)
        except OSError: pass

    # (3) effect present + NO declaration -> receipted refusal, no false success
    k, p, b = _fresh()
    try:
        r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 3},
                                     gate=lambda: True, effect=lambda: None))  # no effect_atomicity
        if r["admitted"]:
            fails.append("(3) missing declaration admitted (fail-closed cutover broken)")
        if not r["receipt_hash"]:
            fails.append("(3) missing-declaration refusal not receipted (NBER-1)")
        recs = k.store.all_receipts()
        refusals = [x for x in recs if isinstance(getattr(x, "parameters", None), dict)
                    and x.parameters.get("broker_refused") is True]
        if not refusals:
            fails.append("(3) no broker_refused receipt written")
        elif not getattr(refusals[-1], "failed", False):
            fails.append("(3) broker refusal receipt is not failed=True")
        if _nonfailed_success(k.store):
            fails.append("(3) FALSE SUCCESS: non-failed success receipt exists for a refused request")
    finally:
        try: os.unlink(p)
        except OSError: pass

    # (4) explicit NON_ATOMIC -> legacy bridge proceeds
    k, p, b = _fresh()
    try:
        ran = []
        r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 4},
                                     gate=lambda: True, effect=lambda: ran.append(True),
                                     effect_atomicity=EffectAtomicity.NON_ATOMIC))
        if not r["admitted"]:
            fails.append("(4) explicit NON_ATOMIC not admitted (legacy bridge broken): %r" % r.get("reason"))
        if not ran:
            fails.append("(4) NON_ATOMIC effect did not run")
    finally:
        try: os.unlink(p)
        except OSError: pass

    # (5) external classes fail closed WITHOUT a key -> no receipt. Both implemented external classes
    #     now require a mandatory idempotency_key, so absent a key the kernel preflight fails closed
    #     (missing-key) for BOTH (r118/AD-45 irreversible; r132/AD-55 reversible). Either way the broker
    #     fabricates no key and surfaces admitted=False with zero mutation.
    for cls in (EffectAtomicity.EXTERNAL_IRREVERSIBLE, EffectAtomicity.EXTERNAL_REVERSIBLE):
        k, p, b = _fresh()
        try:
            r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 5},
                                         gate=lambda: True, effect=lambda: None,
                                         effect_atomicity=cls))   # NO idempotency_key
            if r["admitted"]:
                fails.append("(5) %s admitted without a key (should fail closed)" % cls.name)
            if r["receipt_hash"]:
                fails.append("(5) %s fail-closed wrote a receipt (expected zero-mutation)" % cls.name)
            if _nonfailed_success(k.store):
                fails.append("(5) %s: false success receipt exists" % cls.name)
        finally:
            try: os.unlink(p)
            except OSError: pass

    # (6) EXTERNAL_IRREVERSIBLE WITH an idempotency_key PROCEEDS via the kernel AD-44 two-phase path:
    #     admitted, exactly one COMMIT terminal is written, and that COMMIT carries the key VERBATIM
    #     (r118/AD-45 -- the broker is the third relay joint; it propagates the key unaltered and the
    #     kernel alone enforces it). Together with (5) this proves the broker invents/defaults no key:
    #     no key -> refused (not silently keyed); a key -> exactly that key reaches the trail.
    k, p, b = _fresh()
    try:
        sink6 = []
        r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 6},
                                     gate=lambda: True, effect=lambda: sink6.append(1),
                                     effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE,
                                     idempotency_key="K-6"))
        commits = [rec for rec in k.store.all_receipts() if _ef(rec, "phase") == "commit"]
        if not r["admitted"]:
            fails.append("(6) EXTERNAL_IRREVERSIBLE with a key not admitted: %r" % r.get("reason"))
        if len(commits) != 1:
            fails.append("(6) expected exactly 1 COMMIT, got %d" % len(commits))
        elif _ef(commits[0], "idempotency_key") != "K-6":
            fails.append("(6) COMMIT did not carry the verbatim key (got %r)" %
                         _ef(commits[0], "idempotency_key"))
        if len(sink6) != 1:
            fails.append("(6) effect did not run exactly once (sink=%d)" % len(sink6))
    finally:
        try: os.unlink(p)
        except OSError: pass

    # (7) r132/AD-55: EXTERNAL_REVERSIBLE WITH an idempotency_key PROCEEDS via the forward-effect trail
    #     through the broker (the relay propagates effect + class + key verbatim; the kernel runs
    #     PREPARE -> effect -> COMMIT). Proves the broker no longer fails closed on the reversible class
    #     and still invents/defaults no key.
    k, p, b = _fresh()
    try:
        sink7 = []
        r = b.submit(GovernedRequest(op=OP, authority="t", parameters={"c": 7},
                                     gate=lambda: True, effect=lambda: sink7.append(1),
                                     effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE,
                                     idempotency_key="K-7"))
        rev_commits = [rec for rec in k.store.all_receipts()
                       if _ef(rec, "phase") == "commit"
                       and _ef(rec, "effect_atomicity") == "external_reversible"]
        if not r["admitted"]:
            fails.append("(7) EXTERNAL_REVERSIBLE with a key not admitted: %r" % r.get("reason"))
        if len(rev_commits) != 1:
            fails.append("(7) expected exactly 1 reversible COMMIT, got %d" % len(rev_commits))
        elif _ef(rev_commits[0], "idempotency_key") != "K-7":
            fails.append("(7) reversible COMMIT did not carry the verbatim key (got %r)" %
                         _ef(rev_commits[0], "idempotency_key"))
        if len(sink7) != 1:
            fails.append("(7) reversible effect did not run exactly once (sink=%d)" % len(sink7))
    finally:
        try: os.unlink(p)
        except OSError: pass

    ok = not fails
    return ok, (
        "r107/AD-40 + r118/AD-45 + r132/AD-55 broker propagation: no-effect exempt; explicit PURE "
        "propagates to the kernel atomic-outcome; missing declaration -> receipted refusal with no false "
        "success; explicit NON_ATOMIC bridge proceeds; EXTERNAL_IRREVERSIBLE and EXTERNAL_REVERSIBLE "
        "without a key both fail closed (missing-key), no receipt; EXTERNAL_IRREVERSIBLE WITH a key "
        "proceeds via the AD-44 two-phase path and EXTERNAL_REVERSIBLE WITH a key proceeds via the "
        "AD-55 forward trail, the key propagated verbatim into the COMMIT. The broker chooses no class "
        "and invents no key." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print("broker_propagation_gate: %s  %s" % ("PASS" if ok else "FAIL", detail))
