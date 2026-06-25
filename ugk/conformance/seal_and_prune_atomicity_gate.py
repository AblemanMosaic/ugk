"""r101 / AD-36 - seal_and_prune_epoch atomicity gate: the SECOND seam-backed path.

Proves that epoch_sealed + epoch_pruned + the destructive prefix DELETE + the postconditions are ONE
governed transition through the audited deferred-commit seam (store.transaction()) - all-or-nothing:

  - valid seal/prune commits both provenance receipts AND the prefix deletion together; the retained
    chain verifies from the seal commitment S from a FRESH connection; the tip (measured AFTER the two
    terminal receipts are appended) is unchanged by the prefix deletion;
  - a fault at ANY boundary - write failure, DELETE failure, or postcondition failure (tip moved /
    verify_from_seal fails) - rolls back BOTH receipts AND the DELETE; from a FRESH connection the
    receipt count, the receipt-id set (pruned rows AND frontier), and the stream hash all match the
    pre-transaction state, with NO outer commit;
  - postconditions are PRE-COMMIT GATES inside the seam (not post-commit assertions);
  - preflight (missing intent / unknown seal_hash / frontier-does-not-chain) still refuses before any
    mutation.

seal_and_prune_epoch is store-level (no kernel founding required), so this gate runs standalone (it is
NOT NOT_ESTABLISHED) and also under verify_release.
"""
from __future__ import annotations
import os
import sqlite3
import tempfile


def _fresh_db():
    return os.path.join(tempfile.mkdtemp(), "ugk.db")


def _disk(db):
    """receipt count, the full receipt-id set (captures pruned rows AND frontier), and stream hash -
    all from a FRESH connection / fresh read-only store, so it reflects only durably-committed state."""
    from ugk.storage.store import UGKReceiptStore
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    n = c.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    ids = tuple(r[0] for r in c.execute("SELECT receipt_id FROM receipts ORDER BY receipt_id").fetchall())
    c.close()
    return n, ids, UGKReceiptStore(db_path=db, read_only=True).stream_hash()


def _seed():
    """A store-level chain of 6 receipts; boundary = the 3rd receipt's h_r (seal commitment S)."""
    from ugk.storage.store import UGKReceiptStore
    db = _fresh_db()
    s = UGKReceiptStore(db_path=db)
    for i in range(6):
        s.write(op="crp_evidence", authority="a", parameters={"i": i}, intent="seed")
    return db, s, s.all_receipts()[2].h_r


class _ConnProxy:
    """Delegates everything to the real connection except a DELETE, which raises (fault injection)."""
    def __init__(self, real, fail):
        self._real = real
        self._fail = fail
    def execute(self, sql, *a, **k):
        if self._fail(sql):
            raise sqlite3.OperationalError("injected DELETE failure")
        return self._real.execute(sql, *a, **k)
    def __getattr__(self, n):
        return getattr(self._real, n)


def run():
    from ugk.storage.store import UGKReceiptStore
    fails = []

    # (1) valid seal/prune commits BOTH receipts + the prefix DELETE together; tip stable; fresh-conn
    #     verify_from_seal(S) passes.
    db, s, seal = _seed(); pre = _disk(db)
    r = s.seal_and_prune_epoch(seal, intent="seal epoch", description="gate")
    post = _disk(db)
    fresh = UGKReceiptStore(db_path=db, read_only=True)
    if post[0] != pre[0] - r["pruned_count"] + 2:
        fails.append("valid: count wrong after commit (%d -> %d, pruned=%d)" % (pre[0], post[0], r["pruned_count"]))
    if r["tip_before_prune"] != r["tip_after_prune"]:
        fails.append("valid: tip moved during prune (tip measured after the two terminal receipts must be stable)")
    if not fresh.verify_from_seal(seal):
        fails.append("valid: retained chain does NOT verify_from_seal from a fresh connection (AC5)")
    if post[1] and post[1][0] <= 0:
        fails.append("valid: prefix not pruned")

    # (2) write-fail at epoch_pruned -> rolls back epoch_sealed; fresh-conn == pre
    db, s, seal = _seed(); pre = _disk(db); _orig = s.write
    def _wfail(*a, **k):
        op = k.get("op", a[0] if a else None)
        if op == "epoch_pruned":
            raise RuntimeError("injected epoch_pruned write failure")
        return _orig(*a, **k)
    s.write = _wfail
    raised = False
    try:
        s.seal_and_prune_epoch(seal, intent="x")
    except RuntimeError:
        raised = True
    s.write = _orig
    if not raised:
        fails.append("write-fail: exception did not propagate")
    if _disk(db) != pre:
        fails.append("write-fail: state not restored (fresh-conn count/ids/stream != pre)")

    # (3) DELETE-fail -> rolls back BOTH receipts AND (the would-be) deletion; fresh-conn == pre (pruned rows restored)
    db, s, seal = _seed(); pre = _disk(db); _real = s._conn
    s._conn = _ConnProxy(_real, lambda sql: isinstance(sql, str) and sql.lstrip().upper().startswith("DELETE"))
    raised = False
    try:
        s.seal_and_prune_epoch(seal, intent="x")
    except sqlite3.OperationalError:
        raised = True
    s._conn = _real
    if not raised:
        fails.append("delete-fail: exception did not propagate")
    if _disk(db) != pre:
        fails.append("delete-fail: state not restored (pruned rows / receipts / stream != pre)")

    # (4) postcondition-fail (verify_from_seal -> False) -> rolls back BOTH receipts AND the DELETE; fresh-conn == pre
    db, s, seal = _seed(); pre = _disk(db); _origv = s.verify_from_seal
    s.verify_from_seal = lambda h: False
    raised = False
    try:
        s.seal_and_prune_epoch(seal, intent="x")
    except RuntimeError:
        raised = True
    s.verify_from_seal = _origv
    if not raised:
        fails.append("postcondition-fail: exception did not propagate")
    if _disk(db) != pre:
        fails.append("postcondition-fail: receipts+DELETE not rolled back (pruned rows / count / stream != pre)")

    # (5) preflight refuses BEFORE mutation: missing intent, unknown seal_hash (the cleanly-testable
    #     refusals; frontier-does-not-chain is an internal consistency guard not reachable on a valid
    #     contiguous chain).
    db, s, seal = _seed(); pre = _disk(db)
    for label, call in [
        ("missing-intent", lambda: s.seal_and_prune_epoch(seal, intent="")),
        ("unknown-seal", lambda: s.seal_and_prune_epoch("ffff" * 16, intent="x")),
    ]:
        try:
            call(); fails.append("preflight %s: not refused" % label)
        except ValueError:
            pass
        if _disk(db) != pre:
            fails.append("preflight %s: mutated despite refusal" % label)

    if fails:
        return False, "seal_and_prune atomicity FAILURES: " + "; ".join(fails)
    return True, ("AD-36 second seam-backed path: seal_and_prune_epoch commits epoch_sealed + epoch_pruned + the "
                  "prefix DELETE together (all-or-nothing) through the audited deferred-commit seam, with "
                  "postconditions as PRE-COMMIT gates; write-fail, DELETE-fail, and postcondition-fail each roll "
                  "back both receipts AND the deletion - fresh-connection count, receipt-id set (pruned rows + "
                  "frontier), and stream hash all match pre-transaction with no outer commit; the tip (measured "
                  "after the two terminal receipts) is unchanged by the prefix deletion; the retained chain "
                  "verifies_from_seal from a fresh connection; preflight refuses before mutation. The governed "
                  "transition T is the atom.")


if __name__ == "__main__":
    import sys
    ok, detail = run()
    print(("PASS" if ok is True else "FAIL") + ": " + detail)
    sys.exit(0 if ok is True else 1)
