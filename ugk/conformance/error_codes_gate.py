"""ugk/conformance/error_codes_gate.py — EH-S-01: typed exception hierarchy."""


def run():
    from ugk.kernel import (
        GovernanceKernel, GateRefusal, KernelInternalOp,
        GovernanceNotFounded, UndeclaredOp,
    )
    fails = []

    # Each exception is a distinct class, independently catchable
    for exc_class in (GateRefusal, KernelInternalOp, GovernanceNotFounded, UndeclaredOp):
        if not issubclass(exc_class, Exception):
            fails.append(f"{exc_class.__name__} is not an Exception subclass")
        # Instantiate to verify constructor
        try:
            if exc_class is GateRefusal:
                e = exc_class(op="test_op")
                assert e.op == "test_op"
            elif exc_class is KernelInternalOp:
                e = exc_class(op="gate_admit")
                assert e.op == "gate_admit"
            elif exc_class is GovernanceNotFounded:
                e = exc_class(op="write_data")
                assert e.op == "write_data"
            elif exc_class is UndeclaredOp:
                e = exc_class(op="unknown_op")
                assert e.op == "unknown_op"
        except Exception as ex:
            fails.append(f"{exc_class.__name__} constructor failed: {ex}")

    # KernelInternalOp is raised for Tier 0 ops
    k = GovernanceKernel()
    try:
        k.execute(op="gate_admit", authority="t", parameters={})
        fails.append("gate_admit did not raise KernelInternalOp")
    except KernelInternalOp:
        pass

    # GovernanceNotFounded for APPLICATION ops in UNINITIALIZED
    from ugk import ops as _ops_module, schema as _schema
    original = dict(_ops_module.APPLICATION_OPS)
    _ops_module.APPLICATION_OPS["_ec_test"] = {"t": 2}
    _schema.GOVERNANCE_OPS["_ec_test"] = {"t": 2}
    try:
        k2 = GovernanceKernel()
        k2.execute(op="_ec_test", authority="t", parameters={})
        fails.append("APPLICATION op in UNINITIALIZED did not raise GovernanceNotFounded")
    except GovernanceNotFounded:
        pass
    except Exception as e:
        fails.append(f"APPLICATION op raised {type(e).__name__} instead of GovernanceNotFounded")
    finally:
        _ops_module.APPLICATION_OPS.clear()
        _ops_module.APPLICATION_OPS.update(original)
        _schema.GOVERNANCE_OPS.pop("_ec_test", None)

    # UndeclaredOp for ops not in GOVERNANCE_OPS — requires ACTIVE kernel
    # (UNINITIALIZED triggers GovernanceNotFounded first per three-tier order)
    k3 = GovernanceKernel()
    k3._ceremony()
    try:
        k3.execute(op="totally_unknown", authority="t", parameters={})
        fails.append("Unknown op did not raise UndeclaredOp")
    except UndeclaredOp:
        pass

    # GateRefusal for gate returning False
    k4 = GovernanceKernel()
    k4.open_session()
    try:
        k4.execute(op="crp_evidence", authority="t", parameters={}, gate=lambda: False)
        fails.append("gate=False did not raise GateRefusal")
    except GateRefusal:
        pass

    ok = not fails
    return ok, ("All four typed exceptions present and raised correctly: "
                "KernelInternalOp, GovernanceNotFounded, UndeclaredOp, GateRefusal." if ok
                else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"error_codes_gate: {'PASS' if ok else 'FAIL'}  {detail}")
