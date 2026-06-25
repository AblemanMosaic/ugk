"""ugk/conformance/nonretroactivity_gate.py — DM-S-01: retroactive modification is detected."""


def run():
    """Prove the store is append-only: altering a stored field breaks verify_stream_hash().

    Operates on a throwaway in-memory store — no shipped state is touched.
    Corrupts a row directly in SQLite (simulating an adversary with DB write access)
    and verifies that verify_stream_hash() detects it.
    """
    from ugk.kernel import GovernanceKernel
    fails = []

    k = GovernanceKernel()
    k.open_session()
    k.execute(op="crp_evidence", authority="nr_test", parameters={"n": 1})
    k.execute(op="crp_evidence", authority="nr_test", parameters={"n": 2})
    k.close_session()

    # Chain must verify clean before tampering
    if not k.store.verify_stream_hash():
        fails.append("Chain failed to verify BEFORE tampering (test setup error)")

    # Tamper: corrupt the first receipt's parent_h_r (M2 chain anchor). RT-3 (E5b): re-anchored from
    # the retired legacy authority/semantic_hash recompute to the M2 h_r chain.
    conn = k.store._conn
    original_row = conn.execute(
        "SELECT receipt_id, parent_h_r FROM receipts ORDER BY receipt_id ASC LIMIT 1"
    ).fetchone()
    receipt_id, orig_parent = original_row

    conn.execute(
        "UPDATE receipts SET parent_h_r = ? WHERE receipt_id = ?",
        ("e" * 64, receipt_id),
    )
    conn.commit()
    if k.store.verify_stream_hash():
        fails.append(
            "verify_stream_hash() returned True after parent_h_r corrupted "
            "(retroactive modification not detected!)"
        )
    conn.execute(
        "UPDATE receipts SET parent_h_r = ? WHERE receipt_id = ?",
        (orig_parent, receipt_id),
    )
    conn.commit()

    # Restore, then corrupt a non-tail h_r directly
    recs = k.store.all_receipts()
    mid = recs[len(recs) // 2]
    conn.execute(
        "UPDATE receipts SET h_r = ? WHERE receipt_id = ?",
        ("a" * 64, mid.receipt_id),
    )
    conn.commit()
    if k.store.verify_stream_hash():
        fails.append(
            "verify_stream_hash() returned True after h_r was replaced "
            "(chain corruption not detected!)"
        )

    ok = not fails
    return ok, ("DM-S-01: retroactive M2-chain corruption (parent_h_r + h_r) detected "
                "by verify_stream_hash()." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"nonretroactivity_gate: {'PASS' if ok else 'FAIL'}  {detail}")
