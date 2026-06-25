"""ugk/conformance/receipts_for_warrant_gate.py — AUDIT-S-03: warrant→receipts reverse linkage."""


def run():
    from ugk.kernel import GovernanceKernel
    from ugk.governance.warrant import WarrantStore
    from ugk.storage.audit import AuditSession
    fails = []

    ws = WarrantStore()
    k = GovernanceKernel()
    k._ceremony(); k.open_session()
    k.set_warrant_store(ws)

    k.execute(op="crp_evidence", authority="rfw", parameters={"n": 1},
              warrant_basis=[1008, 1010])
    k.execute(op="crp_evidence", authority="rfw", parameters={"n": 2},
              warrant_basis=[1008, 1010])
    k.execute(op="crp_evidence", authority="rfw", parameters={"n": 3})  # no warrant
    k.close_session()

    session = AuditSession(k.store, ws)
    warrants = ws.all_warrants()
    if not warrants:
        return False, "No warrants in store"

    # Both execute() calls with warrant_basis should have produced one warrant
    # (same basis → same warrant_hash after content-addressing? No — timestamps differ)
    # Actually each call produces its own warrant. Let's find them.
    receipts_with_warrant = [r for r in k.store.all_receipts() if r.warrant_id]
    if len(receipts_with_warrant) < 2:
        fails.append(f"Expected ≥2 receipts with warrant_id, got {len(receipts_with_warrant)}")

    for w in warrants:
        citing = session.receipts_for_warrant(w.warrant_hash)
        if not citing:
            fails.append(f"receipts_for_warrant({w.warrant_hash[:8]}…) returned empty")
            continue
        for r in citing:
            if r.warrant_id != w.warrant_hash:
                fails.append(f"receipts_for_warrant returned receipt with wrong warrant_id")

    # Receipts without warrant_id are NOT in any receipts_for_warrant result
    no_warrant_receipts = [r for r in k.store.all_receipts() if not r.warrant_id]
    for w in warrants:
        citing = session.receipts_for_warrant(w.warrant_hash)
        citing_ids = {r.receipt_id for r in citing}
        for nwr in no_warrant_receipts:
            if nwr.receipt_id in citing_ids:
                fails.append("receipts_for_warrant returned receipt with no warrant_id")

    ok = not fails
    return ok, (
        f"AUDIT-S-03: receipts_for_warrant returns correct receipts for "
        f"{len(warrants)} warrant(s); receipts without warrant_id correctly excluded." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"receipts_for_warrant_gate: {'PASS' if ok else 'FAIL'}  {detail}")
