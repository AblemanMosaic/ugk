"""ugk/conformance/body_integrity_gate.py — BODY-level receipt-integrity gate (IEL / AD-23).

Closes finding #27 on the runtime path and proves the VerificationLevel distinction has teeth:

  GIVEN a clean store:
    - verify_receipt_bodies() is True and verify_chain() reaches BODY (ok).
  GIVEN a store whose receipt BODY has been tampered directly in the DB (op/parameters altered,
  leaving the committed h_s/h_r/parent_h_r columns intact):
    - verify_stream_hash() (LINKAGE) STILL passes — linkage alone never detected this (the #27 gap),
    - verify_receipt_bodies() (BODY) now FAILS — the body recompute catches it,
    - verify_chain() reports ok=False with CorruptionKind.CORRUPT.

This gate is the adversarial evidence that the body verifier is not merely coded but enforced.
"""
from __future__ import annotations
import os
import sqlite3
import tempfile

from ugk.integrity import CorruptionKind


def _build_tampered_db():
    """Create a fresh founded-by-default kernel store with one governed op, then tamper a stored
    receipt's parameters directly in SQLite. Returns the db path."""
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    d = tempfile.mkdtemp()
    db = os.path.join(d, "ugk.db")
    k = GovernanceKernel(store=UGKReceiptStore(db_path=db))
    k.open_session()
    k.execute(op="crp_evidence", authority="alice", parameters={"amount": 100})
    k.close_session()
    return db


def run():
    from ugk.storage.store import UGKReceiptStore

    db = _build_tampered_db()

    # (1) clean store: BODY established
    clean = UGKReceiptStore(db_path=db)
    if not clean.verify_stream_hash():
        return False, "clean store failed LINKAGE (verify_stream_hash) — fixture broken"
    if not clean.verify_receipt_bodies():
        return False, "clean store failed BODY (verify_receipt_bodies) — body verifier false-positive"
    cres = clean.verify_chain()
    if not cres.ok or cres.achieved.name != "BODY":
        return False, f"clean store verify_chain not BODY/ok: {cres.achieved.name} ok={cres.ok}"
    del clean

    # (2) tamper a stored receipt BODY directly in the DB (committed h_* columns untouched)
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT receipt_id, op, parameters FROM receipts").fetchall()
    tampered = False
    for rid, op, params in rows:
        if op == "crp_evidence" and params and "100" in str(params):
            conn.execute("UPDATE receipts SET parameters=? WHERE receipt_id=?",
                         (str(params).replace("100", "999"), rid))
            tampered = True
            break
    conn.commit()
    conn.close()
    if not tampered:
        return False, "could not locate a governed receipt body to tamper — fixture broken"

    # (3) re-open and assert the level distinction
    st = UGKReceiptStore(db_path=db)
    linkage_still_ok = st.verify_stream_hash()      # the #27 gap: linkage does NOT catch body tamper
    body_now_fails = not st.verify_receipt_bodies()  # the fix: body recompute catches it
    res = st.verify_chain()

    if not linkage_still_ok:
        return False, "LINKAGE unexpectedly failed on body tamper (verify_stream_hash should be linkage-only)"
    if not body_now_fails:
        return False, "BODY verifier MISSED receipt-body tampering — finding #27 NOT closed"
    if res.ok or res.corruption is not CorruptionKind.CORRUPT:
        return False, f"verify_chain did not fail-closed as CORRUPT on body tamper: ok={res.ok} corruption={res.corruption}"

    return True, ("BODY catches receipt-body tampering that LINKAGE misses "
                  "(verify_stream_hash still True; verify_receipt_bodies False; verify_chain CORRUPT) — #27 closed")


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + "  body_integrity_gate — " + detail)
    raise SystemExit(0 if ok else 1)
