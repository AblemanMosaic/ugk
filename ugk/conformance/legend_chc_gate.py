"""ugk/conformance/legend_chc_gate.py — LEGEND-S-03: legend_hash in CHC envelope."""


def run():
    from ugk.storage.binding import dm_s03, LEGEND_HASH
    from ugk.kernel import GovernanceKernel
    fails = []

    # dm_s03 is sensitive to legend_hash — altering it changes semantic_hash
    base = dict(
        state_hash="s" * 64, parent="p" * 64, intent="crp_evidence",
        authority="system", jurisdiction="session", confidence="high",
        session_id="dkn", agent_id="dkn", ts="1700000000.0",
        law_hash="l" * 64,
    )
    h_without = dm_s03(**base)
    h_with    = dm_s03(**base, legend_hash=LEGEND_HASH)
    h_tampered = dm_s03(**base, legend_hash="a" * 64)

    if h_with == h_without:
        fails.append("Adding legend_hash to dm_s03 did not change semantic_hash")
    if h_with == h_tampered:
        fails.append("Different legend_hash values produced same semantic_hash")
    if h_without == h_tampered:
        fails.append("Tampered legend_hash same as no-legend hash (field not bound)")

    # Kernel ceremony injects legend_hash
    k = GovernanceKernel()
    k._ceremony()
    snap = k.snapshot_fast()
    if not snap.get("legend_hash"):
        fails.append("legend_hash absent from snapshot_fast() after ceremony")
    if snap.get("legend_hash") != LEGEND_HASH:
        fails.append(
            f"snapshot_fast legend_hash {snap.get('legend_hash','')[:16]!r}… "
            f"!= LEGEND_HASH {LEGEND_HASH[:16]!r}…"
        )

    # ACTIVE receipts carry legend_hash
    k.open_session()
    k.execute(op="crp_evidence", authority="test", parameters={})
    receipts = k.store.all_receipts()
    active_receipts = [r for r in receipts if r.law_hash]
    if not active_receipts:
        fails.append("No receipts carry law_hash after ceremony (ACTIVE receipts expected)")
    for r in active_receipts:
        if r.legend_hash != LEGEND_HASH:
            fails.append(f"Receipt {r.op!r} has legend_hash={r.legend_hash[:8]!r}… != LEGEND_HASH")
            break

    ok = not fails
    return ok, (
        f"LEGEND-S-03: dm_s03 is legend_hash-sensitive; "
        f"kernel ceremony injects LEGEND_HASH={LEGEND_HASH[:16]}…; "
        f"ACTIVE receipts carry correct legend_hash." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"legend_chc_gate: {'PASS' if ok else 'FAIL'}  {detail}")
