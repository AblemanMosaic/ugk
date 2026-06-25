"""ugk/conformance/enforcement_gate.py — GK-S-01: admission is blocking and fail-closed."""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal, EffectAtomicity
    fails = []

    k = GovernanceKernel()
    k.open_session()

    # Gate returning False must block effect() entirely
    effect_ran = []
    try:
        k.execute(
            op="crp_evidence",
            authority="test",
            parameters={"test": "enforce"},
            gate=lambda: False,
            effect=lambda: effect_ran.append(True), effect_atomicity=EffectAtomicity.NON_ATOMIC,
        )
        fails.append("execute() with gate=False did not raise GateRefusal")
    except GateRefusal:
        pass  # correct
    except Exception as e:
        fails.append(f"gate=False raised unexpected: {type(e).__name__}: {e}")

    if effect_ran:
        fails.append("effect() ran despite gate returning False (not fail-closed!)")

    # gate_refuse receipt must exist in the store
    refuse_receipts = k.store.receipts_by_op("gate_refuse")
    if not refuse_receipts:
        fails.append("No gate_refuse receipt written after gate=False (NBER-1 violation)")

    # Gate returning True must admit and effect must run
    effect_admitted = []
    try:
        k.execute(
            op="crp_evidence",
            authority="test",
            parameters={"test": "admit"},
            gate=lambda: True,
            # r105 (AD-39): callsite B (admit case) migrated NON_ATOMIC -> PURE. The effect is store-pure
            # by evidence (a local-list append; no store writes, no external state). GK-S-01 still asserts
            # "effect runs iff gate admits"; the per-callsite atomicity property is proven separately by
            # pure_migration_r105_gate. (Callsite A above stays NON_ATOMIC: gate=False, the effect never runs.)
            effect=lambda: effect_admitted.append(True), effect_atomicity=EffectAtomicity.PURE,
        )
    except Exception as e:
        fails.append(f"gate=True raised unexpected: {type(e).__name__}: {e}")

    if not effect_admitted:
        fails.append("effect() did not run when gate returned True")

    ok = not fails
    return ok, ("GK-S-01: gate=False blocks effect and writes gate_refuse receipt; "
                "gate=True admits and runs effect." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"enforcement_gate: {'PASS' if ok else 'FAIL'}  {detail}")
