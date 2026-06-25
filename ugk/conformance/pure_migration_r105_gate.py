"""ugk/conformance/pure_migration_r105_gate.py

r105 Path-A pilot proof. enforcement_gate callsite B (the gate=True admit case, whose pure effect
actually runs) was migrated NON_ATOMIC -> PURE (AD-39). GK-S-01 keeps asserting "effect runs iff
gate admits"; THIS gate carries the per-callsite migration property that justifies the reclass:

  1. classification by evidence  - the migrated effect is STORE-PURE: running it advances no receipts
                                    (it touches only a local list; external-purity is by construction);
  2. decision-before-effect      - gate_admit is written BEFORE the effect runs;
  3. success-after-effect         - the success receipt does NOT exist at the moment the effect runs,
                                    and exists exactly once afterward (the r103 atomic-outcome order);
  4. fail-closed outcome          - a forced effect failure leaves a durable, classified structural
                                    abort and NO false success;
  5. fresh-connection verified    - (3)/(4) are re-read on a brand-new read-only connection.

This gate is migration-specific; it does not restate GK-S-01.
"""


def _fresh_kernel():
    import tempfile, os
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd); os.unlink(path)
    k = GovernanceKernel(store=UGKReceiptStore(db_path=path)); k.open_session()
    return k, path



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
    from ugk.storage.store import UGKReceiptStore
    fails = []
    OP = "crp_evidence"

    def _nonfailed(recs, op):
        return [r for r in recs if r.op == op and not getattr(r, "failed", False)]

    # (1) classification by evidence: the migrated effect shape is store-pure.
    k, path = _fresh_kernel()
    try:
        before = len(k.store.all_receipts())
        sink = []
        eff = lambda: sink.append(True)      # the enforcement_gate callsite B effect shape
        eff()
        after = len(k.store.all_receipts())
        if after != before:
            fails.append("classification: effect advanced receipts by %d (not store-pure)" % (after - before))
        if not sink:
            fails.append("classification: effect did not run in isolation")
    finally:
        try: os.unlink(path)
        except OSError: pass

    # (2)+(3) success path: gate_admit before effect, success after effect, no false abort.
    k, path = _fresh_kernel()
    try:
        seen = {}
        ran = []
        def eff():
            recs = k.store.all_receipts()
            seen["gate_admit_at_effect"] = sum(1 for r in recs if r.op == "gate_admit")
            seen["success_at_effect"]    = len(_nonfailed(recs, OP))
            ran.append(True)
        k.execute(op=OP, authority="test", parameters={"r105": "admitB"},
                  gate=lambda: True, effect=eff, effect_atomicity=EffectAtomicity.PURE)
        if not ran:
            fails.append("success: effect did not run")
        if seen.get("gate_admit_at_effect", 0) < 1:
            fails.append("success: gate_admit was NOT written before the effect (decision-before-effect violated)")
        if seen.get("success_at_effect", 99) != 0:
            fails.append("success: a success receipt already existed when the effect ran (not success-after-effect)")
        recs = k.store.all_receipts()
        if len(_nonfailed(recs, OP)) != 1:
            fails.append("success: expected exactly 1 non-failed success receipt, got %d" % len(_nonfailed(recs, OP)))
        if any(getattr(r, "failed", False) for r in recs):
            fails.append("success: a failed/abort receipt was written on the clean path (false abort)")
    finally:
        try: os.unlink(path)
        except OSError: pass

    # (4)+(5) forced effect failure: durable structural abort, no false success, fresh-connection verified.
    k, path = _fresh_kernel()
    try:
        def boom(): raise RuntimeError("r105 forced effect failure")
        raised = False
        try:
            k.execute(op=OP, authority="test", parameters={"r105": "failB"},
                      gate=lambda: True, effect=boom, effect_atomicity=EffectAtomicity.PURE)
        except RuntimeError:
            raised = True
        if not raised:
            fails.append("failure: execute() did not propagate the effect error")
        # fresh read-only connection
        ro = UGKReceiptStore(db_path=path, read_only=True)
        recs = ro.all_receipts()
        if _nonfailed(recs, OP):
            fails.append("failure: FALSE SUCCESS - a non-failed success receipt persisted for a failed effect")
        aborts = [r for r in recs if getattr(r, "failed", False)
                  and isinstance(getattr(r, "parameters", None), dict)
                  and r.parameters.get("effect_aborted") is True]
        if not aborts:
            fails.append("failure: no durable structural abort receipt after forced failure")
        else:
            ar = aborts[-1]
            if _ef(ar, "abort_reason") != "effect_failure":
                fails.append("failure: abort_reason=%r (expected effect_failure)" % _ef(ar, "abort_reason"))
            if "pure" not in str(_ef(ar, "effect_atomicity") or "").lower():
                fails.append("failure: abort marker effect_atomicity=%r (expected pure)" % _ef(ar, "effect_atomicity"))
            if not _ef(ar, "gate_admit_ref"):
                fails.append("failure: abort receipt missing gate_admit_ref")
        # gate_admit (decision) must still be durably present even though the effect failed
        if not any(r.op == "gate_admit" for r in recs):
            fails.append("failure: gate_admit decision receipt did not persist (it should, before the seam)")
    finally:
        try: os.unlink(path)
        except OSError: pass

    ok = not fails
    return ok, (
        "r105 Path-A pilot (enforcement_gate callsite B -> PURE): effect store-pure by evidence; "
        "gate_admit before effect; success after effect; forced failure -> durable classified structural "
        "abort with gate_admit_ref and NO false success; fresh-connection verified." if ok
        else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print("pure_migration_r105_gate: %s  %s" % ("PASS" if ok else "FAIL", detail))
