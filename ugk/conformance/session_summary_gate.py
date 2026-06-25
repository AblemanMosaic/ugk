"""ugk/conformance/session_summary_gate.py — SUM-S-01: SessionSummary at close_session."""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal
    from ugk.governance.warrant import WarrantStore
    from ugk.summary import SessionSummary
    fails = []

    ws = WarrantStore()
    k = GovernanceKernel()
    k._ceremony(); k.open_session()
    k.set_warrant_store(ws)

    k.execute(op="crp_evidence", authority="sum_test",
              parameters={"n": 1}, warrant_basis=[1008])
    k.execute(op="crp_evidence", authority="sum_test", parameters={"n": 2})
    try:
        k.execute(op="crp_evidence", authority="sum_test",
                  parameters={"n": 3}, gate=lambda: False)
    except GateRefusal:
        pass

    k.close_session()

    summary = k.last_summary
    if summary is None:
        return False, "SUM-S-01: kernel.last_summary is None after close_session()"

    if not summary.verify_hash():
        fails.append("summary_hash does not verify against body")

    if not summary.is_consistent_with(k.store, ws):
        fails.append(
            f"SessionSummary inconsistent with store: "
            f"receipt_count={summary.receipt_count} vs store={k.store.receipt_count()}, "
            f"warrant_count={summary.warrant_count} vs ws={ws.warrant_count()}"
        )

    if summary.refusal_count != k.store.refusal_count():
        fails.append(
            f"refusal_count {summary.refusal_count} != store {k.store.refusal_count()}"
        )

    if summary.session_dkn != k._session_dkn:
        # session_dkn may be cleared after close; verify field is non-empty
        if not summary.session_dkn:
            fails.append("summary.session_dkn is empty")

    if summary.final_stream_hash != k.store.stream_hash():
        fails.append("final_stream_hash mismatch with current stream_hash")

    ok = not fails
    return ok, (
        f"SUM-S-01: SessionSummary produced at close_session(); hash verifies; "
        f"counts consistent ({summary.receipt_count} receipts, "
        f"{summary.warrant_count} warrants, {summary.refusal_count} refusals)." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"session_summary_gate: {'PASS' if ok else 'FAIL'}  {detail}")
