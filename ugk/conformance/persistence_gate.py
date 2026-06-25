"""ugk/conformance/persistence_gate.py — PERSIST-S-01: cross-process chain continuity."""
import tempfile, os


def run():
    """Prove the M2 chain tip (_prior_h_r) is hydrated from disk when reopening a file-based store.

    This gate was missing from Phase 1-6 and is the root cause that allowed the
    cross-process persistence bug to go undetected. All prior gates use :memory:
    stores which never exercise the hydration path.
    """
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    fails = []

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # --- Pass 1: write receipts, record chain tip ---
        store1 = UGKReceiptStore(db_path=db_path)
        k1 = GovernanceKernel(store=store1)
        k1._ceremony()
        k1.open_session()
        k1.execute(op="crp_evidence", authority="persist_test",
                   parameters={"pass": 1})
        k1.close_session()
        tip_after_pass1 = store1.stream_hash()
        count_after_pass1 = store1.receipt_count()
        del k1, store1  # simulate process exit

        # --- Pass 2: reopen store, verify hydration, write more receipts ---
        store2 = UGKReceiptStore(db_path=db_path)

        # _prior_h_r (M2 chain tip) must equal the tip from pass 1 (RT-3: re-anchored from _prior_hash)
        if store2._prior_h_r != tip_after_pass1:
            fails.append(
                f"_prior_h_r after reopen: {store2._prior_h_r[:16]!r}… "
                f"!= tip from pass 1: {tip_after_pass1[:16]!r}… "
                "(hydration from disk failed — linked to genesis instead)"
            )

        # Write a new receipt and verify chain is intact
        k2 = GovernanceKernel(store=store2)
        k2._ceremony()
        k2.open_session()
        k2.execute(op="crp_evidence", authority="persist_test",
                   parameters={"pass": 2})
        k2.close_session()

        if not store2.verify_stream_hash():
            fails.append(
                "verify_stream_hash() returned False after cross-process write — "
                "chain is broken at the process boundary"
            )

        count_after_pass2 = store2.receipt_count()
        if count_after_pass2 <= count_after_pass1:
            fails.append(
                f"Pass 2 added no receipts: count went "
                f"{count_after_pass1} → {count_after_pass2}"
            )

        # --- Pass 3: third open, verify cumulative chain ---
        store3 = UGKReceiptStore(db_path=db_path)
        if store3._prior_h_r != store2.stream_hash():
            fails.append(
                "Pass 3 _prior_h_r does not match pass 2 stream_hash — "
                "hydration fails on second reopen"
            )
        if not store3.verify_stream_hash():
            fails.append("verify_stream_hash() failed on third open (cumulative chain broken)")

    finally:
        try:
            os.unlink(db_path)
            os.unlink(db_path + "-wal")
        except FileNotFoundError:
            pass
        except Exception:
            pass

    ok = not fails
    return ok, (
        f"PERSIST-S-01: cross-process chain continuity verified — "
        f"3 opens, {count_after_pass2} cumulative receipts, chain intact." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"persistence_gate: {'PASS' if ok else 'FAIL'}  {detail}")
