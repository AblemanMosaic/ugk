"""ugk/conformance/canary_gate.py — CR-S-02: CLASSIFIED_REMAINDERS are inert."""


def run():
    """CR-04 canary: effect() internals are opaque but do not grant extra capability.

    Demonstrates that calling execute() with an effect that contains ungoverned
    I/O does not produce additional governance receipts or extend the kernel's
    constitutional claim — the CR-04 gap is real (effect internals are opaque),
    but it is also inert (no capability flows from exploiting it).

    Proof strategy: execute with a side-effecting lambda that does NOT call
    kernel.execute().  Verify that only the expected receipts are produced
    (gate_admit + op receipt = 2) and that the kernel makes no claim about
    what happened inside the effect.
    """
    from ugk.kernel import GovernanceKernel, EffectAtomicity

    k = GovernanceKernel()
    k.open_session()
    count_before = k.store.receipt_count()

    # CR-04 canary: effect does ungoverned I/O (just a no-op here, but opaque to kernel)
    ungoverned_side_effect_ran = []
    def _ungoverned_effect():
        ungoverned_side_effect_ran.append(True)  # opaque to kernel

    k.execute(
        op="crp_evidence",
        authority="canary",
        parameters={"test": "cr04"},
        effect=_ungoverned_effect, effect_atomicity=EffectAtomicity.NON_ATOMIC,
    )

    count_after = k.store.receipt_count()
    receipts_produced = count_after - count_before
    # Expect: session_open(1) + gate_admit(1) + crp_evidence(1) = 3 from open_session + execute
    # But we measure from count_before (after open_session), so: gate_admit + crp_evidence = 2
    expected_receipts = 2

    fails = []
    if not ungoverned_side_effect_ran:
        fails.append("effect() was not called (canary scenario broken)")
    if receipts_produced != expected_receipts:
        fails.append(
            f"CR-04 canary: expected {expected_receipts} receipts, got {receipts_produced} — "
            f"either extra capability from gap or missing receipt"
        )
    # The kernel must NOT claim to have receipted the effect internals
    snap = k.snapshot_fast()
    cr_list = snap.get("classified_remainders", [])
    cr04_declared = any("CR-04" in r for r in cr_list)
    if not cr04_declared:
        fails.append("CR-04 not declared in classified_remainders — gap not honestly surfaced")

    if fails:
        return False, "; ".join(fails)
    return True, (
        f"CR-04 canary: effect() ran ungoverned, produced exactly {receipts_produced} receipts "
        f"(gate_admit + op), CR-04 declared inert — no capability from the gap."
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"canary_gate: {'PASS' if ok else 'FAIL'}  {detail}")
