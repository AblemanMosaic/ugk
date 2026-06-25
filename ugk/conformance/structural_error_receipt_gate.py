"""ugk/conformance/structural_error_receipt_gate.py — FGA §15.5 structural-error receipts. GATE_GROUP = "integration"

Proves the third outcome class is now receipted and distinguishable:
  ADMIT (success)  ·  constitutional REFUSE (gate_refuse)  ·  PROTOCOL error (protocol_error)
For each structural/protocol failure the kernel must (a) raise the correct typed exception
(EH-S-01 unchanged) AND (b) leave a `protocol_error` receipt carrying the right `reason`,
distinct from `gate_refuse` and from success receipts. IR strengthening of EH-S-01 + receipt
semantics — no new invariant; frame triad unmoved.
"""
import json


def _last_protocol_error(store):
    pes = [r for r in store.all_receipts() if r.op == "protocol_error"]
    if not pes:
        return None
    p = pes[-1].parameters
    if isinstance(p, str):
        p = json.loads(p or "{}")
    return pes[-1], (p or {}).get("reason")


def run():
    from ugk.kernel import (GovernanceKernel, KernelInternalOp,
                            GovernanceNotFounded, UndeclaredOp)
    from ugk.governance.governor import GovernorSignatureRequired
    from ugk.authority.authority_model import AuthorityModel
    fails = []

    def check(label, kernel, trigger, exc_type, expected_reason):
        raised = None
        try:
            trigger()
        except exc_type:
            raised = True
        except Exception as e:  # noqa
            raised = type(e).__name__
        if raised is not True:
            fails.append(f"{label}: expected {exc_type.__name__}, got {raised}")
            return
        rec = _last_protocol_error(kernel._store)
        if rec is None:
            fails.append(f"{label}: no protocol_error receipt emitted")
            return
        receipt, reason = rec
        if receipt.op != "protocol_error":
            fails.append(f"{label}: op={receipt.op!r} != 'protocol_error'")
        if reason != expected_reason:
            fails.append(f"{label}: reason={reason!r}, expected {expected_reason!r}")
        if not receipt.failed:
            fails.append(f"{label}: receipt not marked failed")

    # 1. kernel_internal — Tier-0 op called externally
    k = GovernanceKernel()
    check("kernel_internal", k, lambda: k.execute(op="gate_admit"),
          KernelInternalOp, "kernel_internal")

    # 2. not_founded — Tier-2 op while UNINITIALIZED
    k = GovernanceKernel()
    check("not_founded", k, lambda: k.execute(op="authority_model_set"),
          GovernanceNotFounded, "not_founded")

    # 3. undeclared — op absent from GOVERNANCE_OPS (ACTIVE)
    k = GovernanceKernel(); k._ceremony(); k.open_session()
    check("undeclared", k, lambda: k.execute(op="totally_undeclared_op_xyz"),
          UndeclaredOp, "undeclared")

    # 4. governor_sig — interposition flag set, no signature (ACTIVE)
    k = GovernanceKernel(); k._ceremony(); k.open_session(); k._require_governor_sig = True
    check("governor_sig", k, lambda: k.execute(op="authority_model_set"),
          GovernorSignatureRequired, "governor_sig")

    # 5. require_gate — authority model requires a gate, none supplied (ACTIVE)
    k = GovernanceKernel(); k._ceremony()
    k.set_authority_model(AuthorityModel.custom(k._law_hash, k._authority,
                                                require_gate=True, require_warrant=False))
    k.open_session()
    check("require_gate", k, lambda: k.execute(op="authority_model_set", gate=None),
          KernelInternalOp, "require_gate")

    # 6. require_warrant — authority model requires warrant_basis, none supplied (ACTIVE)
    k = GovernanceKernel(); k._ceremony()
    k.set_authority_model(AuthorityModel.custom(k._law_hash, k._authority,
                                                require_gate=False, require_warrant=True))
    k.open_session()
    check("require_warrant", k, lambda: k.execute(op="authority_model_set", warrant_basis=None),
          KernelInternalOp, "require_warrant")

    # distinguishability — a constitutional REFUSE must emit gate_refuse, NOT protocol_error
    k = GovernanceKernel(); k._ceremony(); k.open_session()
    try:
        k.execute(op="authority_model_set", gate=lambda: False)
    except Exception:
        pass
    ops = {r.op for r in k._store.all_receipts()}
    if "gate_refuse" not in ops:
        fails.append("distinguishability: expected gate_refuse receipt absent")
    if "protocol_error" in ops:
        fails.append("distinguishability: REFUSE path wrongly emitted protocol_error")

    ok = not fails
    return ok, (
        "FGA §15.5: 6 structural-error classes receipted "
        "(kernel_internal/not_founded/governor_sig/undeclared/require_gate/require_warrant) "
        "with correct reasons; distinct from gate_refuse and success."
        if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"structural_error_receipt_gate: {'PASS' if ok else 'FAIL'}  {detail}")
