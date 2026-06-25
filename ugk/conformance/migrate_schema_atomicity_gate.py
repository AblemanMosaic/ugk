"""r99 / AD-34 - migrate_schema atomicity gate: the deferred-commit governed-transaction seam.

Proves migrate_schema's schema ALTER and its migration receipt commit together as ONE atomic governed
transition (FGA / AD-33 M6: the governed transition T is the atom) or roll back together - all-or-
nothing - with NO outer commit persisting any side effect of a failed block, and with the in-memory
chain/frame frontier restored on rollback. The critical post-fault checks are verified from a FRESH
connection after close/reopen (schema, receipt count, stream hash, and the frontier-derived next
write), and a rolled-back transaction's next write is shown to link to the PRE-rollback frontier, not
to the rolled-back receipt's h_r.

migrate_schema and store.transaction() are store-level (no kernel founding required), so this gate
runs standalone (it is NOT NOT_ESTABLISHED) and also under verify_release.
"""
from __future__ import annotations
import os
import sqlite3
import tempfile


def _fresh_db():
    return os.path.join(tempfile.mkdtemp(), "ugk.db")


def _disk_state(db):
    """schema_hash, receipt_count, stream_hash, and frontier tip - ALL read from a FRESH connection
    / fresh read-only store, so this reflects only what is durably committed."""
    from ugk.storage.store import UGKReceiptStore, compute_schema_hash
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    sh = compute_schema_hash(c)
    n = c.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    row = c.execute("SELECT h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()
    tip = row[0] if row else None
    c.close()
    strm = UGKReceiptStore(db_path=db, read_only=True).stream_hash()
    return {"schema": sh, "count": n, "stream": strm, "tip": tip}


def _last_parent(db):
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    p = c.execute("SELECT parent_h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()[0]
    c.close()
    return p


def run():
    from ugk.storage.store import UGKReceiptStore
    fails = []

    # (1) valid migration: schema + receipt commit TOGETHER, durable in a fresh connection
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db)
    s.migrate_schema(["ALTER TABLE receipts ADD COLUMN g_valid_col TEXT"], intent="add g_valid_col")
    post = _disk_state(db)
    if not (post["schema"] != pre["schema"] and post["count"] == pre["count"] + 1):
        fails.append("valid: schema+receipt not committed together (schema_changed=%s count %d->%d)"
                     % (post["schema"] != pre["schema"], pre["count"], post["count"]))

    # (2) empty migration refuses BEFORE mutation
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db)
    try:
        s.migrate_schema([], intent="x"); fails.append("empty: not refused")
    except ValueError:
        pass
    if _disk_state(db) != pre:
        fails.append("empty: mutated despite refusal")

    # (3) invalid statement refuses BEFORE mutation
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db)
    try:
        s.migrate_schema(["DROP TABLE receipts"], intent="x"); fails.append("invalid: not refused")
    except ValueError:
        pass
    if _disk_state(db) != pre:
        fails.append("invalid: mutated despite refusal")

    # (4) FAULT at the receipt boundary: schema mutation succeeds but the receipt write fails.
    #     Schema must roll back. Verified from a FRESH connection: schema, receipt count, AND stream
    #     hash all match pre-transaction; the in-memory frontier is restored; and the next write on
    #     the SAME instance links to the pre-rollback frontier (not the rolled-back receipt's h_r).
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db); pre_tip = s._prior_h_r
    _orig = s.write
    def _boom(*a, **k):
        raise RuntimeError("injected receipt-write failure")
    s.write = _boom
    raised = False
    try:
        s.migrate_schema(["ALTER TABLE receipts ADD COLUMN g_rb_col TEXT"], intent="rollback")
    except RuntimeError:
        raised = True
    s.write = _orig
    if not raised:
        fails.append("receipt-fail: exception did not propagate")
    post = _disk_state(db)
    if post["schema"] != pre["schema"]:
        fails.append("receipt-fail: schema NOT rolled back (fresh-conn)")
    if post["count"] != pre["count"]:
        fails.append("receipt-fail: a receipt persisted (fresh-conn count %d != %d)" % (post["count"], pre["count"]))
    if post["stream"] != pre["stream"]:
        fails.append("receipt-fail: stream_hash changed on disk (fresh-conn)")
    if s._prior_h_r != pre_tip:
        fails.append("receipt-fail: in-memory frontier NOT restored")
    s.write(op="crp_evidence", authority="a", parameters={"x": 1}, intent="i")
    if _last_parent(db) != pre_tip:
        fails.append("receipt-fail: next write linked to the rolled-back h_r, not the pre-rollback frontier")

    # (4b) FRESH-REOPEN frontier check (Governor criterion: frontier-derived next write from a fresh
    #      connection). A receipt-fail-only db, reopened fresh, must hydrate its frontier from the
    #      pre-transaction state and link its next write there.
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db); pre_tip = s._prior_h_r
    _orig = s.write
    s.write = _boom
    try:
        s.migrate_schema(["ALTER TABLE receipts ADD COLUMN g_rb2_col TEXT"], intent="rollback2")
    except RuntimeError:
        pass
    s.write = _orig
    reopened = UGKReceiptStore(db_path=db)  # fresh store on the failed-only db
    if reopened._prior_h_r != pre_tip:
        fails.append("receipt-fail(reopen): fresh store frontier != pre-transaction tip")
    reopened.write(op="crp_evidence", authority="a", parameters={"x": 1}, intent="i")
    if _last_parent(db) != pre_tip:
        fails.append("receipt-fail(reopen): fresh store's next write did not link to the pre-transaction frontier")

    # (5) FAULT at the schema boundary: a statement fails mid-batch (duplicate ADD COLUMN passes the
    #     receipt-safe validator but fails at execute). Nothing persists - verified from a fresh conn.
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db)
    raised = False
    try:
        s.migrate_schema(["ALTER TABLE receipts ADD COLUMN g_dup TEXT",
                          "ALTER TABLE receipts ADD COLUMN g_dup TEXT"], intent="dup")
    except Exception:
        raised = True
    if not raised:
        fails.append("schema-fail: exception did not propagate")
    post = _disk_state(db)
    if post["schema"] != pre["schema"] or post["count"] != pre["count"] or post["stream"] != pre["stream"]:
        fails.append("schema-fail: partial state persisted (fresh-conn schema/count/stream)")

    # (6) existing store.write() at depth 0 still commits durably (no regression for unmigrated callers)
    db = _fresh_db(); s = UGKReceiptStore(db_path=db); pre = _disk_state(db)
    s.write(op="crp_evidence", authority="a", parameters={"x": 1}, intent="i")
    if _disk_state(db)["count"] != pre["count"] + 1:
        fails.append("depth-0: existing write() no longer commits durably")
    if s._txn_depth != 0:
        fails.append("depth-0: _txn_depth not 0 after a plain write")

    if fails:
        return False, "migrate_schema atomicity FAILURES: " + "; ".join(fails)
    return True, ("AD-34 deferred-commit seam: migrate_schema commits schema+receipt together or rolls "
                  "back together (all-or-nothing); receipt-boundary and schema-boundary faults both leave "
                  "schema, receipt count, and stream hash at the pre-transaction state (verified from a "
                  "FRESH connection) with NO outer commit; the in-memory frontier is restored and the next "
                  "write (same-instance and fresh-reopen) links to the pre-rollback frontier; empty/invalid "
                  "refuse before mutation; depth-0 writes still commit. The governed transition T is the atom.")


if __name__ == "__main__":
    import sys
    ok, detail = run()
    print(("PASS" if ok is True else "FAIL") + ": " + detail)
    sys.exit(0 if ok is True else 1)
