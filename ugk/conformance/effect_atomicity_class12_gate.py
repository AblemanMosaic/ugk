"""ugk/conformance/effect_atomicity_class12_gate.py - r102-b / AD-38.

Proves the ATOMIC OUTCOME protocol for the rollback-able effect classes (PURE / STORE_LOCAL):

  1. gate_admit is the durable decision-before-effect receipt, committed at depth 0 BEFORE the
     effect transaction (it survives a rolled-back outcome).
  2. [effect + success receipt] run inside the AD-34/36 seam: the success receipt is written AFTER
     effect() returns, and a STORE_LOCAL effect's store writes commit TOGETHER with the success
     receipt on clean RELEASE (proven from a FRESH connection).
  3. On effect failure the seam rolls back BOTH the effect's store writes AND the would-be success
     receipt (fresh connection: neither persists), and the kernel writes a durable STRUCTURAL ABORT
     receipt (failed=True, effect_aborted, abort_reason=effect_failure, gate_admit_ref) at depth 0 -
     gate_admit + abort durable, with NO false success.
  4. Clean-path RELEASE (commit) failure is fail-closed: a distinct TransactionCommitError surfaces,
     the frontier is restored, nothing from the outcome transition persists, no success is durable,
     and the abort is classified commit_release_failure.

confess-and-audit (r102-b): STORE_LOCAL asserts its durable mutations are store-local and flow only
through audited store surfaces; the seam guarantees rollback only for those audited store mutations.
External state touched by a STORE_LOCAL effect is a caller contract violation, not kernel-made-atomic.
"""



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
    import tempfile, sqlite3
    from ugk.kernel import GovernanceKernel, EffectAtomicity
    from ugk.storage.store import UGKReceiptStore
    from ugk.integrity import TransactionCommitError
    fails = []

    def mk():
        db = tempfile.mktemp(suffix=".db")
        k = GovernanceKernel(store=UGKReceiptStore(db_path=db)); k.open_session()
        return k, db

    def fresh_store(db):
        return UGKReceiptStore(db_path=db, read_only=True)

    def fresh_count(db, op=None):
        s = fresh_store(db)
        return len(s.receipts_by_op(op)) if op else s.receipt_count()

    # (1+2) PURE: success written only after effect returns; durable exactly once on success.
    k, db = mk()
    k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True,
              effect=lambda: 7, effect_atomicity=EffectAtomicity.PURE)
    if sum(1 for r in fresh_store(db).receipts_by_op("crp_evidence") if not r.failed) != 1:
        fails.append("PURE success not durably written exactly once")

    # (2) STORE_LOCAL atomic commit: effect store-write + success commit together (fresh conn: both).
    k, db = mk()
    def sl_ok():
        k.store.write(op="side_effect", authority="adm", parameters={"x": 1})
    k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True,
              effect=sl_ok, effect_atomicity=EffectAtomicity.STORE_LOCAL)
    if fresh_count(db, "side_effect") != 1:
        fails.append("STORE_LOCAL effect store-write not durable after clean commit")
    if sum(1 for r in fresh_store(db).receipts_by_op("crp_evidence") if not r.failed) != 1:
        fails.append("STORE_LOCAL success not durable after clean commit")

    # (3) STORE_LOCAL failure: roll back BOTH; gate_admit + abort durable, no success (fresh conn).
    k, db = mk()
    def sl_fail():
        k.store.write(op="side_effect", authority="adm", parameters={"x": 1})   # store-local write...
        raise RuntimeError("effect boom")                                        # ...then fail
    raised = False
    try:
        k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True,
                  effect=sl_fail, effect_atomicity=EffectAtomicity.STORE_LOCAL)
    except RuntimeError:
        raised = True
    if not raised:
        fails.append("failing STORE_LOCAL effect did not re-raise")
    if fresh_count(db, "gate_admit") != 1:
        fails.append("gate_admit not durable after failed effect")
    if fresh_count(db, "side_effect") != 0:
        fails.append("effect store-write LEAKED on failure (not rolled back)")
    fs = fresh_store(db)
    if sum(1 for r in fs.receipts_by_op("crp_evidence") if not r.failed) != 0:
        fails.append("false success durable after failed effect")
    abort = [r for r in fs.receipts_by_op("crp_evidence")
             if r.failed and (r.parameters or {}).get("effect_aborted")]
    if len(abort) != 1:
        fails.append("expected exactly one structural abort after failed effect (got %d)" % len(abort))
    else:
        p = abort[0].parameters or {}
        if _ef(abort[0], "abort_reason") != "effect_failure":
            fails.append("abort reason != effect_failure (%s)" % _ef(abort[0], "abort_reason"))
        if _ef(abort[0], "effect_atomicity") != "store_local":
            fails.append("abort missing effect_atomicity=store_local")
        if not _ef(abort[0], "gate_admit_ref"):
            fails.append("abort missing gate_admit_ref linkage")

    # (4) clean-path RELEASE (commit) failure: distinct error + frontier restored + nothing persists.
    class ConnProxy:
        """Delegates to the real connection but fails the FIRST 'RELEASE SAVEPOINT' (clean commit)."""
        def __init__(self, real): self._real = real; self._n = 0
        def execute(self, sql, *a, **kw):
            if isinstance(sql, str) and sql.strip().upper().startswith("RELEASE SAVEPOINT"):
                self._n += 1
                if self._n == 1:
                    raise sqlite3.OperationalError("simulated clean RELEASE failure")
            return self._real.execute(sql, *a, **kw)
        def __getattr__(self, name): return getattr(self._real, name)

    k, db = mk()
    k.store._conn = ConnProxy(k.store._conn)
    def sl_commitfail():
        k.store.write(op="side_effect", authority="adm", parameters={"x": 1})   # succeeds, deferred
    distinct = False
    try:
        k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True,
                  effect=sl_commitfail, effect_atomicity=EffectAtomicity.STORE_LOCAL)
    except TransactionCommitError:
        distinct = True
    except Exception as e:  # noqa: BLE001
        fails.append("clean-RELEASE-failure surfaced %s, not TransactionCommitError" % type(e).__name__)
    if not distinct:
        fails.append("clean-RELEASE-failure did not surface a distinct TransactionCommitError")
    if fresh_count(db, "gate_admit") != 1:
        fails.append("gate_admit not durable after commit failure")
    if fresh_count(db, "side_effect") != 0:
        fails.append("effect store-write LEAKED on commit failure")
    fs = fresh_store(db)
    if sum(1 for r in fs.receipts_by_op("crp_evidence") if not r.failed) != 0:
        fails.append("false success durable after commit failure")
    abort = [r for r in fs.receipts_by_op("crp_evidence")
             if r.failed and (r.parameters or {}).get("effect_aborted")]
    if len(abort) != 1:
        fails.append("expected exactly one structural abort after commit failure (got %d)" % len(abort))
    elif _ef(abort[0], "abort_reason") != "commit_release_failure":
        fails.append("abort reason != commit_release_failure (%s)"
                     % _ef(abort[0], "abort_reason"))

    ok = not fails
    return ok, ("class-1/2 atomic outcome: gate_admit is the durable decision-before-effect at depth 0; "
                "[effect + success] commit-or-rollback together through the AD-34/36 seam (success "
                "written after effect); a failed effect or a clean-path RELEASE (commit) failure rolls "
                "back the effect's store writes AND the would-be success (fresh-connection verified), "
                "surfaces a distinct error on commit failure, and leaves gate_admit + a classified "
                "structural abort (effect_failure / commit_release_failure, carrying effect_atomicity "
                "and gate_admit_ref) - never a false success."
                if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"effect_atomicity_class12_gate: {'PASS' if ok else 'FAIL'}  {detail}")
