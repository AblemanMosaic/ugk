"""ugk/conformance/abletools_migration_gate.py — Phase 12: AbleTools GovernedContext."""


def run():
    try:
        from ugk.migration.abletools import GovernedContext
    except ImportError as e:
        return False, f"Cannot import GovernedContext: {e}"
    fails = []

    ctx = GovernedContext.from_env()
    if ctx is None:
        return False, "GovernedContext.from_env() returned None"

    if not hasattr(ctx, "_kernel"):
        fails.append("GovernedContext has no ._kernel attribute")

    # Basic execute path via context
    try:
        # GovernedContext auto-runs ceremony and opens session in __init__
        ctx.govern(intent="orient", subject="migration_gate_test", op="crp_evidence")
        receipts = ctx._kernel.store.all_receipts()
        if not any(r.op == "crp_evidence" for r in receipts):
            fails.append("No crp_evidence receipt after ctx.govern()")
        if not ctx._kernel.store.verify_stream_hash():
            fails.append("Chain broken after migration context execute")
    except Exception as e:
        fails.append(f"Migration context execute raised: {type(e).__name__}: {e}")

    ok = not fails
    return ok, (
        "Phase 12 migration: GovernedContext.from_env() works; "
        "ctx.execute() routes through UGK kernel; chain intact." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"abletools_migration_gate: {'PASS' if ok else 'FAIL'}  {detail}")
