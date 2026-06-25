"""ugk/conformance/chain_gate.py — DM-S-03: receipt stream is a tamper-evident causal chain."""


def run():
    """Prove DM-S-03: all receipts are stream-chained and verify_stream_hash() is load-bearing.

    Three sub-proofs (all on throwaway state):
      1. clean chain verifies
      2. corrupting one stored semantic_hash breaks verification at that position
      3. truncating prior_receipt_hash (making it zero) breaks verification
    """
    from ugk.kernel import GovernanceKernel
    fails = []

    # --- Proof 1: clean chain verifies ---
    k = GovernanceKernel()
    k.open_session()
    k.execute(op="crp_evidence", authority="chain_t", parameters={"i": 0})
    k.execute(op="crp_evidence", authority="chain_t", parameters={"i": 1})
    k.execute(op="crp_evidence", authority="chain_t", parameters={"i": 2})
    k.close_session()

    if not k.store.verify_stream_hash():
        fails.append("Clean chain failed to verify (test setup error)")

    receipts = k.store.all_receipts()
    n = len(receipts)
    if n < 3:
        fails.append(f"Expected >= 3 receipts, got {n}")
        return False, "; ".join(fails)

    genesis = k.store.GENESIS
    # --- RT-2e/RT-3 (E5b): chain linkage is the M2 h_r chain; each receipt's parent_h_r links
    # to the previous receipt's h_r (merkle binding root). Legacy semantic_hash chain removed at r80. ---
    for i, r in enumerate(receipts):
        expected_parent = genesis if i == 0 else receipts[i-1].h_r
        if r.parent_h_r != expected_parent:
            fails.append(
                f"Receipt {i} ({r.op!r}) M2 parent_h_r mismatch: "
                f"got {r.parent_h_r[:16]!r}… expected {expected_parent[:16]!r}… (RT-2e)"
            )
        if len(r.h_r) != 64:
            fails.append(f"Receipt {i} ({r.op!r}): h_r not a 64-hex merkle root (RT-2e)")

    # --- Proof 2: corrupting a stored semantic_hash breaks chain ---
    # --- Proof 2 (RT-3, M2): corrupting a non-tail h_r breaks the M2 chain ---
    conn = k.store._conn
    mid_id = receipts[len(receipts) // 2].receipt_id          # non-tail
    original_h_r = receipts[len(receipts) // 2].h_r
    conn.execute("UPDATE receipts SET h_r = ? WHERE receipt_id = ?", ("b" * 64, mid_id))
    conn.commit()
    if k.store.verify_stream_hash():
        fails.append("verify_stream_hash() passed after middle h_r corrupted (M2)")
    conn.execute("UPDATE receipts SET h_r = ? WHERE receipt_id = ?", (original_h_r, mid_id))
    conn.commit()

    # --- Proof 3 (RT-3, M2): corrupting parent_h_r breaks the M2 chain ---
    conn.execute("UPDATE receipts SET parent_h_r = ? WHERE receipt_id = ?", ("c" * 64, mid_id))
    conn.commit()
    if k.store.verify_stream_hash():
        fails.append("verify_stream_hash() passed after parent_h_r corrupted (M2)")

    ok = not fails
    return ok, (
        f"M2 chain verified ({n} receipts, genesis->tip via parent_h_r->h_r); "
        "mid-chain h_r corruption and parent_h_r corruption both detected." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"chain_gate: {'PASS' if ok else 'FAIL'}  {detail}")
