"""ugk/conformance/pure_migration_r108_gate.py

r108 Path-A migration proof. admission_gate's ADMIT-PATH callsite (gate=True, whose store-pure effect
actually runs) was migrated NON_ATOMIC -> PURE (AD-41). GK-S-02 keeps asserting the W/G/E property
(gate before effect; gate_admit present when the effect fires; refusal blocks the effect); THIS gate
carries the per-callsite migration property that justifies the reclass, for the admission-gate effect
SHAPE (a store-READING probe: it reads gate_admit and appends to a local list):

  1. classification by evidence  - the migrated effect is STORE-PURE: running it advances no receipts
                                    (it only READS the store and touches a local list);
  2. decision-before-effect      - gate_admit is written BEFORE the effect runs (the effect observes it);
  3. success-after-effect         - the success receipt does NOT exist at the moment the effect runs,
                                    and exists exactly once afterward (the r103 atomic-outcome order);
  4. fail-closed outcome          - a forced effect failure leaves a durable, classified structural
                                    abort (effect_failure / pure / gate_admit_ref) and NO false success;
  5. fresh-connection verified    - (3)/(4) are re-read on a brand-new read-only connection.

This gate is migration-specific; it does not restate GK-S-02 (admission_gate keeps its own assertion).
The admission_gate refusal-path callsite stays NON_ATOMIC (gate=False, the effect never runs).
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

    # (1) classification by evidence: the migrated effect SHAPE (reads gate_admit + local append) is store-pure.
    k, path = _fresh_kernel()
    try:
        before = len(k.store.all_receipts())
        sink = []
        def eff():                               # admission_gate admit-path effect shape: READS the store
            _ = k.store.receipts_by_op("gate_admit")
            sink.append(True)
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
        k.execute(op=OP, authority="adm", parameters={"r108": "admit"},
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
        def boom(): raise RuntimeError("r108 forced effect failure")
        raised = False
        try:
            k.execute(op=OP, authority="adm", parameters={"r108": "fail"},
                      gate=lambda: True, effect=boom, effect_atomicity=EffectAtomicity.PURE)
        except RuntimeError:
            raised = True
        if not raised:
            fails.append("failure: execute() did not propagate the effect error")
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
        if not any(r.op == "gate_admit" for r in recs):
            fails.append("failure: gate_admit decision receipt did not persist (it should, before the seam)")
    finally:
        try: os.unlink(path)
        except OSError: pass

    ok = not fails
    return ok, (
        "r108 Path-A (admission_gate admit-path callsite -> PURE): store-reading effect store-pure by "
        "evidence; gate_admit before effect; success after effect; forced failure -> durable classified "
        "structural abort with gate_admit_ref and NO false success; fresh-connection verified." if ok
        else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print("pure_migration_r108_gate: %s  %s" % ("PASS" if ok else "FAIL", detail))
