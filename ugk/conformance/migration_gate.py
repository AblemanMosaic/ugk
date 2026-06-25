"""ugk/conformance/migration_gate.py — Phase 5: AbleTools migration shim integration test."""


def run():
    """Phase 5 integration test: GovernedContext is a fully functional UGK consumer.

    Proves:
      1. from_env() constructs a working GovernedContext backed by GovernanceKernel.
      2. ctx.govern() routes through kernel.execute() (produces gate_admit receipts).
      3. AbleTools compatibility shims (fs_read, fs_write, proc_run, net_fetch)
         all produce governed receipts (no silent bypasses).
      4. ctx.verify_chain() returns True at session close.
      5. ctx.attest() returns a structurally sound attestation.
      6. Context manager __enter__/__exit__ correctly opens and closes session.
      7. GovernedContext can be imported from ugk.migration (migration import path works).
    """
    from ugk.migration import GovernedContext
    from ugk.migration.abletools import GovResult
    fails = []

    # --- 1. from_env() constructs working context ---
    try:
        ctx = GovernedContext.from_env(authority="migration_gate")
    except Exception as e:
        return False, f"GovernedContext.from_env() raised: {type(e).__name__}: {e}"

    # --- 2. ctx.govern() routes through kernel.execute() ---
    count_before = ctx._kernel.store.receipt_count()
    result = ctx.govern("orient", "migration test")
    if not result.ok:
        fails.append(f"ctx.govern() returned non-admitted: {result.reason}")
    admits = ctx._kernel.store.receipts_by_op("gate_admit")
    if not admits:
        fails.append("ctx.govern() produced no gate_admit receipts")
    if result.receipt_hash == "":
        fails.append("ctx.govern() returned empty receipt_hash")
    if not isinstance(result, GovResult):
        fails.append(f"ctx.govern() returned {type(result)}, expected GovResult")
    if result.outcome != "execute":
        fails.append(f"GovResult.outcome is {result.outcome!r}, expected 'execute'")

    # --- 3. AbleTools shims produce governed receipts ---
    count_shims_before = ctx._kernel.store.receipt_count()
    for shim_call in (
        lambda: ctx.fs_read("/tmp/test.txt", intent="orient"),
        lambda: ctx.fs_write("/tmp/out.txt", b"data", intent="transform"),
        lambda: ctx.proc_run(["echo", "hello"], intent="transform"),
        lambda: ctx.net_fetch("https://example.com", intent="orient"),
    ):
        r = shim_call()
        if not r.ok:
            fails.append(f"Shim call returned non-admitted: {r.reason}")
    count_shims_after = ctx._kernel.store.receipt_count()
    # Each shim: gate_admit + crp_evidence = 2 receipts
    shim_delta = count_shims_after - count_shims_before
    if shim_delta < 8:  # 4 shims × 2 receipts each
        fails.append(f"Shim calls produced only {shim_delta} receipts (expected ≥ 8)")

    # --- 4. ctx.verify_chain() ---
    if not ctx.verify_chain():
        fails.append("ctx.verify_chain() returned False (chain integrity broken)")

    # --- 5. ctx.attest() ---
    att = ctx.attest()
    if not att.get("hash_verified"):
        fails.append("ctx.attest() hash_verified is False")
    if not att.get("law_hash"):
        fails.append("ctx.attest() law_hash is empty")
    if not att.get("stream_hash"):
        fails.append("ctx.attest() stream_hash is empty")

    ctx.close()

    # --- 6. Context manager lifecycle ---
    with GovernedContext.from_env(authority="migration_ctx_mgr") as ctx2:
        r2 = ctx2.govern("verify", "cm_test")
        if not r2.ok:
            fails.append(f"Context-manager ctx.govern() failed: {r2.reason}")
    # After __exit__, session should be closed
    receipts_after = ctx2._kernel.store.receipts_by_op("session_close")
    if not receipts_after:
        fails.append("session_close receipt absent after context manager exit")

    # --- 7. Import path ---
    try:
        from ugk.migration import GovernedContext as GC2
        assert GC2 is GovernedContext
    except Exception as e:
        fails.append(f"ugk.migration import path broken: {e}")

    ok = not fails
    return ok, (
        "migration_gate: GovernedContext.from_env() works; ctx.govern() routes through "
        "kernel.execute(); all 4 AbleTools shims produce receipts; chain intact; "
        "attest sound; context manager lifecycle correct." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"migration_gate: {'PASS' if ok else 'FAIL'}  {detail}")
