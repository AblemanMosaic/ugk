"""ugk/conformance/recovery_gate.py — EH-S-02: last_valid_frontier() identifies corruption boundary."""


def run():
    """Prove last_valid_frontier() pinpoints where the chain diverges.

    Proof:
      1. Build a clean chain of N receipts (verify_stream_hash=True).
      2. Corrupt receipt at position K (overwrite authority field in SQLite).
      3. last_valid_frontier() returns the receipt_id of receipt K-1 (last valid).
      4. Receipts 0..K-1 are intact; receipts K..N are untrustworthy.
    """
    from ugk.kernel import GovernanceKernel
    fails = []

    k = GovernanceKernel()
    k.open_session()
    for i in range(5):
        k.execute(op="crp_evidence", authority="rec_t", parameters={"i": i})
    k.close_session()

    if not k.store.verify_stream_hash():
        return False, "Clean chain failed (test setup error)"

    receipts = k.store.all_receipts()
    n = len(receipts)
    if n < 4:
        return False, f"Expected >= 4 receipts, got {n}"

    # Clean chain: last_valid_frontier() should return None (intact)
    frontier = k.store.last_valid_frontier()
    if frontier is not None:
        fails.append(f"last_valid_frontier() returned {frontier!r} on clean chain (expected None)")

    # Corrupt receipt at position K=3 (0-indexed)
    corrupt_idx = 3
    corrupt_receipt = receipts[corrupt_idx]
    conn = k.store._conn
    conn.execute(
        "UPDATE receipts SET parent_h_r = ? WHERE receipt_id = ?",
        ("f" * 64, corrupt_receipt.receipt_id),   # RT-3: corrupt M2 chain link
    )
    conn.commit()

    # Chain must fail now
    if k.store.verify_stream_hash():
        fails.append("verify_stream_hash() passed after corruption (test setup error)")

    # last_valid_frontier() must return the receipt_id just before the corruption
    frontier = k.store.last_valid_frontier()
    expected_frontier = receipts[corrupt_idx - 1].receipt_id if corrupt_idx > 0 else None

    if frontier != expected_frontier:
        fails.append(
            f"last_valid_frontier() returned {frontier!r}, "
            f"expected {expected_frontier!r} (receipt before position {corrupt_idx})"
        )

    ok = not fails
    return ok, (
        f"EH-S-02: last_valid_frontier() correctly identified receipt_id={expected_frontier} "
        f"as the last valid receipt before corruption at position {corrupt_idx}." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"recovery_gate: {'PASS' if ok else 'FAIL'}  {detail}")
