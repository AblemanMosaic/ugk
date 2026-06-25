"""ugk/conformance/nber1_gate.py — UL-S-02: receipt-before-effect kernel-enforced."""


def run():
    """Prove NBER-1: the success receipt is written BEFORE effect() is called.

    Method: inject an effect() that reads the store's receipt count at execution
    time.  If NBER-1 holds, the receipt for the current op will already be in the
    store when effect() fires.
    """
    from ugk.kernel import GovernanceKernel, EffectAtomicity
    fails = []

    k = GovernanceKernel()
    k.open_session()

    receipt_count_at_effect_time = []
    receipt_count_before = k.store.receipt_count()

    def _effect():
        # At this point, the success receipt for "crp_evidence" must already be written
        receipt_count_at_effect_time.append(k.store.receipt_count())

    k.execute(
        op="crp_evidence",
        authority="nber1_test",
        parameters={"test": "nber1"},
        effect=_effect, effect_atomicity=EffectAtomicity.NON_ATOMIC,
    )

    if not receipt_count_at_effect_time:
        fails.append("effect() was never called")
    else:
        count_in_effect = receipt_count_at_effect_time[0]
        # When effect() ran, the store should contain:
        #   receipts_before + gate_admit + crp_evidence (success) = before + 2
        expected_min = receipt_count_before + 2  # gate_admit + op receipt
        if count_in_effect < expected_min:
            fails.append(
                f"NBER-1 violated: effect() saw {count_in_effect} receipts, "
                f"expected >= {expected_min} (gate_admit + op receipt before effect)"
            )

    ok = not fails
    return ok, ("NBER-1: success receipt written before effect() — "
                f"effect saw {receipt_count_at_effect_time[0] if receipt_count_at_effect_time else '?'} "
                f"receipts (expected {receipt_count_before + 2})." if ok
                else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"nber1_gate: {'PASS' if ok else 'FAIL'}  {detail}")
