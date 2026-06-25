"""ugk/conformance/legend_archive_gate.py — AUDIT-S-02: legend sealed into store at ceremony."""


def run():
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    from ugk.storage.binding import LEGEND_HASH, LEGEND_ENTRY_COUNT
    from ugk.storage.audit import AuditSession, LegendNotResolvable
    fails = []

    k = GovernanceKernel()
    k._ceremony()

    # legend_seal receipt in chain
    seal_receipts = k.store.receipts_by_op("legend_seal")
    if not seal_receipts:
        fails.append("No legend_seal receipt emitted at ceremony")
    else:
        sr = seal_receipts[-1]
        if sr.parameters.get("legend_hash") != LEGEND_HASH:
            fails.append(f"legend_seal receipt has wrong legend_hash")
        if sr.parameters.get("entry_count") != LEGEND_ENTRY_COUNT:
            fails.append(f"legend_seal entry_count mismatch")

    # legend_archive table populated
    entries = k.store.resolve_legend(LEGEND_HASH)
    if entries is None:
        fails.append("resolve_legend(LEGEND_HASH) returned None after ceremony")
    elif len(entries) != LEGEND_ENTRY_COUNT:
        fails.append(f"legend_archive has {len(entries)} entries, expected {LEGEND_ENTRY_COUNT}")

    # Unknown hash raises LegendNotResolvable via AuditSession
    audit = AuditSession(k.store)
    try:
        audit.resolve_legend("unknown" + "x" * 58)
        fails.append("resolve_legend with unknown hash did not raise LegendNotResolvable")
    except LegendNotResolvable:
        pass
    except Exception as e:
        fails.append(f"Wrong exception: {type(e).__name__}: {e}")

    # Current LEGEND_HASH resolves correctly
    resolved = audit.resolve_legend(LEGEND_HASH)
    if not resolved or len(resolved) < 70:
        fails.append(f"resolve_legend(LEGEND_HASH) returned {len(resolved) if resolved else None} entries")

    ok = not fails
    return ok, (
        f"AUDIT-S-02: legend_seal receipt emitted; legend_archive has "
        f"{LEGEND_ENTRY_COUNT} entries; resolve_legend resolves current hash; "
        f"unknown hash raises LegendNotResolvable." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"legend_archive_gate: {'PASS' if ok else 'FAIL'}  {detail}")
