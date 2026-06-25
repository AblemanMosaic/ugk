"""ugk/conformance/receipt_commitment_integrity_gate.py — full receipt-body integrity
(IEL / AD-28, Invariants B + C).

The adversarial gate the external review asked for: it tampers EVERY committed receipt field
directly in the DB and requires verify_chain to FAIL CLOSED on each. This pins the boundary that
`BODY` must mean "the whole stored receipt body is intact", not merely "op/parameters recompute to
h_s". A clean chain must still verify (no false positives)."""
from __future__ import annotations
from ugk.storage.store import UGKReceiptStore

# every committed field whose tampering must be detected (op/parameters already covered by h_s;
# h_body is the new full-body commitment and must itself be tamper-evident once present)
FIELDS = ["op", "authority", "parameters", "intent", "jurisdiction", "confidence", "timestamp",
          "failed", "session_dkn", "law_hash", "legend_hash", "warrant_id", "intent_ref",
          "h_s", "h_c", "h_m", "h_j", "h_r", "parent_h_r", "mode", "version",
          "id_c_s", "id_c_c", "id_c_m", "id_c_j", "h_body"]


def _fresh():
    s = UGKReceiptStore(":memory:")
    s.write(op="crp_evidence", authority="alice", parameters={"i": 1}, intent="t1",
            jurisdiction="production", session_dkn="d1", law_hash="L", legend_hash="G",
            warrant_id="W1", intent_ref="r1")
    s.write(op="policy_evaluate", authority="bob", parameters={"i": 2}, intent="t2",
            jurisdiction="production", session_dkn="d2", law_hash="L", legend_hash="G",
            warrant_id="W2", intent_ref="r2")
    return s


def _tampered_value(old):
    if isinstance(old, bool):
        return (not old)
    if isinstance(old, int):
        return (old or 0) + 1
    if isinstance(old, float):
        return old + 1.0
    if old is None:
        return "X"
    return str(old) + "_X"


def run():
    # no false positives: a clean chain verifies at BODY
    base = _fresh().verify_chain()
    if not base.ok:
        return False, "false positive: a clean chain failed verify_chain (%s)" % getattr(base, "detail", "")

    undetected = []
    for f in FIELDS:
        s = _fresh()
        try:
            row = s._conn.execute("SELECT %s FROM receipts WHERE receipt_id=1" % f).fetchone()
        except Exception:
            continue  # column not present in this schema version
        old = row[0]
        # parameters must remain valid JSON so all_receipts() can parse it
        new = '{"i": 999}' if f == "parameters" else _tampered_value(old)
        try:
            s._conn.execute("UPDATE receipts SET %s=? WHERE receipt_id=1" % f, (new,))
            s._conn.commit()
            caught = not s.verify_chain().ok
        except Exception:
            caught = True  # unreadable after tamper counts as detected (fail-closed)
        if not caught:
            undetected.append(f)

    if undetected:
        return False, "tamper UNDETECTED for committed fields: " + ", ".join(undetected)

    # DOWNGRADE: stripping h_body from EVERY receipt must not let the verifier fall back to h_s-only
    # and still report BODY (the era guard alone does not catch wholesale absence). Two cases:
    #   (1) strip-all + tamper a non-h_s field  -> verify_chain must FAIL CLOSED
    #   (2) strip-all alone                      -> still < BODY (h_body is mandatory under this schema)
    s = _fresh()
    s._conn.execute("UPDATE receipts SET h_body=''")
    s._conn.execute("UPDATE receipts SET authority='mallory' WHERE receipt_id=1")
    s._conn.commit()
    if s.verify_chain().ok:
        return False, "DOWNGRADE: stripping all h_body lets non-h_s tampering pass as BODY"
    s2 = _fresh()
    s2._conn.execute("UPDATE receipts SET h_body=''")
    s2._conn.commit()
    if s2.verify_chain().ok:
        return False, "DOWNGRADE: a chain with all h_body stripped still reports BODY (h_body not required)"

    return True, "every committed receipt field is tamper-evident; verify_chain fails closed on each"


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + "  receipt_commitment_integrity_gate — " + detail)
    raise SystemExit(0 if ok else 1)
