"""ugk/conformance/admission_gate.py — GK-S-02: W/G/E fires gate before effect; blocked on refusal."""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal, EffectAtomicity
    fails = []

    k = GovernanceKernel()
    k.open_session()

    # -- Admit path: gate fires BEFORE effect, effect fires AFTER gate_admit receipt --
    gate_fired = []
    effect_fired = []
    gate_admit_before_effect = []

    def _gate():
        gate_fired.append(k.store.receipt_count())
        return True

    def _effect():
        # gate_admit receipt must already be in the store
        recs = k.store.receipts_by_op("gate_admit")
        gate_admit_before_effect.append(bool(recs))
        effect_fired.append(True)

    # r108/AD-41 (Path-A): the admit-path effect is store-pure by evidence (reads gate_admit + a
    # local append, no store write, no external state) -> PURE. GK-S-02 is order-agnostic w.r.t. the
    # success receipt, so the r103 success-after-effect change is benign. The refusal-path callsite
    # below stays NON_ATOMIC (gate=False, the effect never runs - its class is moot).
    k.execute(op="crp_evidence", authority="adm", parameters={}, gate=_gate, effect=_effect, effect_atomicity=EffectAtomicity.PURE)

    if not gate_fired:
        fails.append("gate() was never called")
    if not effect_fired:
        fails.append("effect() was never called on gate=True")
    if gate_admit_before_effect and not gate_admit_before_effect[0]:
        fails.append("gate_admit receipt was not in store when effect() fired")

    # -- Refusal path: effect must NOT fire when gate returns False --
    effect_after_refusal = []
    try:
        k.execute(
            op="crp_evidence", authority="adm", parameters={"r": True},
            gate=lambda: False,
            effect=lambda: effect_after_refusal.append(True), effect_atomicity=EffectAtomicity.NON_ATOMIC,
        )
        fails.append("execute() with gate=False did not raise GateRefusal")
    except GateRefusal:
        pass

    if effect_after_refusal:
        fails.append("effect() fired despite gate returning False (W/G/E order violated)")

    ok = not fails
    return ok, ("W/G/E: gate fires before effect, gate_admit receipt present when effect fires, "
                "effect blocked on refusal." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"admission_gate: {'PASS' if ok else 'FAIL'}  {detail}")
