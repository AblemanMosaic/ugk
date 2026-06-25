"""ugk/conformance/warrant_gate.py — DW-S-01: DecisionWarrant is a first-class artifact."""


def run():
    from ugk.governance.warrant import (
        DecisionWarrant, WarrantStore,
        RESULT_ADMIT, ANALYSIS_AUTH_SUFFICIENT, ANALYSIS_JURIS_VALID,
        GENESIS_WARRANT_HASH,
    )
    from ugk.kernel import GovernanceKernel
    from ugk.storage.binding import LEGEND_HASH
    fails = []

    # --- 1. warrant_hash = SHA-256(canonical_json(body)) ---
    w = DecisionWarrant.create(
        constitutional_basis=[1008, 1010, 1003],
        law_hash="l" * 64,
        legend_hash=LEGEND_HASH,
    )
    if not w.verify_hash():
        fails.append("warrant_hash does not verify against body (content-addressing broken)")
    if len(w.warrant_hash) != 64:
        fails.append(f"warrant_hash length {len(w.warrant_hash)}, expected 64")

    # --- 2. constitutional_basis is sorted tuple of ints ---
    if list(w.constitutional_basis) != sorted([1008, 1010, 1003]):
        fails.append(f"constitutional_basis not sorted: {w.constitutional_basis}")

    # --- 3. cites_invariant() ---
    if not w.cites_invariant(1008):
        fails.append("cites_invariant(1008) returned False (1008 is in basis)")
    if w.cites_invariant(9999):
        fails.append("cites_invariant(9999) returned True (9999 not in basis)")

    # --- 4. WarrantStore write + get roundtrip ---
    ws = WarrantStore()
    ws.write(w)
    got = ws.get(w.warrant_hash)
    if got is None:
        fails.append("WarrantStore.get() returned None after write")
    elif got.warrant_hash != w.warrant_hash:
        fails.append("WarrantStore roundtrip hash mismatch")

    # --- 5. Kernel execute() with warrant_basis produces warrant_id in receipt ---
    k = GovernanceKernel()
    k._ceremony()
    k.open_session()
    k.set_warrant_store(ws)

    count_before = ws.warrant_count()
    k.execute(
        op="crp_evidence", authority="warrant_gate",
        parameters={"test": True},
        warrant_basis=[1008, 1010, 1003],
    )
    count_after = ws.warrant_count()
    if count_after != count_before + 1:
        fails.append(f"Warrant store gained {count_after - count_before} warrants, expected 1")

    # Receipt carries warrant_id
    crp_receipts = k.store.receipts_by_op("crp_evidence")
    if not crp_receipts:
        fails.append("No crp_evidence receipts found")
    else:
        last = crp_receipts[-1]
        if not last.warrant_id:
            fails.append("crp_evidence receipt has empty warrant_id")
        else:
            stored_warrant = ws.get(last.warrant_id)
            if stored_warrant is None:
                fails.append(f"warrant_id {last.warrant_id[:16]!r}… not in WarrantStore")

    # --- 6. WarrantStore is append-only (duplicate ignored) ---
    ws.write(w)  # write same warrant again
    if ws.warrant_count() != count_before + 1:
        fails.append("WarrantStore accepted duplicate warrant (not idempotent)")

    ok = not fails
    return ok, (
        "DW-S-01: DecisionWarrant is content-addressed; warrant_hash verifies; "
        "constitutional_basis is sorted; cites_invariant() correct; "
        "kernel execute() produces warrant in store; receipt carries warrant_id; "
        "WarrantStore is idempotent on duplicates." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"warrant_gate: {'PASS' if ok else 'FAIL'}  {detail}")
