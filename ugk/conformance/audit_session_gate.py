"""ugk/conformance/audit_session_gate.py — AUDIT-S-01: AuditSession is read-only."""
import tempfile, os


def run():
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    from ugk.governance.warrant import WarrantStore, DecisionWarrant
    from ugk.storage.audit import AuditSession
    from ugk.storage.binding import LEGEND_HASH
    fails = []

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        w_path = f.name

    try:
        # Populate stores
        rs = UGKReceiptStore(db_path=db_path)
        ws = WarrantStore(db_path=w_path)
        k = GovernanceKernel(store=rs)
        k._ceremony(); k.open_session()
        k.set_warrant_store(ws)
        k.execute(op="crp_evidence", authority="audit_test",
                  parameters={"x": 1}, warrant_basis=[1008, 1010])
        k.close_session()
        count_before = rs.receipt_count()
        warrant_count_before = ws.warrant_count()
        del k

        # Open AuditSession — must be read-only
        session = AuditSession(rs, ws)

        # Call all public methods
        session.verify_full_chain()
        session.attest()
        session.all_receipts()
        session.receipts_in_session("nonexistent_dkn")
        session.receipts_for_warrant("nonexistent_hash")
        session.receipts_by_law_hash("x" * 64)
        session.all_warrants()
        session.warrants_for_invariant(1008)
        session.warrants_for_invariant_and_law(1008, "x" * 64)
        session.warrant_lineage("nonexistent")

        if rs.receipt_count() != count_before:
            fails.append(
                f"AuditSession wrote receipts: count went "
                f"{count_before} → {rs.receipt_count()}"
            )
        if ws.warrant_count() != warrant_count_before:
            fails.append(f"AuditSession wrote warrants")

        # AuditSession.open() works on a real state_dir
        state_dir = os.path.dirname(db_path)
        import shutil
        shutil.copy(db_path, os.path.join(state_dir, "ugk.db"))
        try:
            s2 = AuditSession.open(state_dir)
            s2.verify_full_chain()
            s2.close()
        except Exception as e:
            fails.append(f"AuditSession.open() raised: {type(e).__name__}: {e}")

    finally:
        for p in (db_path, w_path,
                  os.path.join(os.path.dirname(db_path), "ugk.db")):
            try: os.unlink(p)
            except: pass

    ok = not fails
    return ok, ("AUDIT-S-01: AuditSession is read-only — all public methods called, "
                "receipt_count and warrant_count unchanged." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"audit_session_gate: {'PASS' if ok else 'FAIL'}  {detail}")
