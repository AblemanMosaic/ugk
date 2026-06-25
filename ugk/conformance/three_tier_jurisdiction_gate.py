"""ugk/conformance/three_tier_jurisdiction_gate.py — CM-OP-01: three-tier jurisdiction enforced."""


def run():
    from ugk.kernel import (
        GovernanceKernel, KernelInternalOp, GovernanceNotFounded, UndeclaredOp,
        STATUS_UNINITIALIZED, STATUS_ACTIVE,
    )
    from ugk.schema import _KERNEL_OPS, _UNIVERSAL_OPS
    fails = []

    # --- Tier 0: _KERNEL_OPS must raise KernelInternalOp ---
    k = GovernanceKernel()
    for tier0_op in _KERNEL_OPS:
        try:
            k.execute(op=tier0_op, authority="test", parameters={})
            fails.append(f"Tier 0 op {tier0_op!r} did not raise KernelInternalOp")
        except KernelInternalOp:
            pass  # correct
        except Exception as e:
            fails.append(f"Tier 0 op {tier0_op!r} raised wrong exception: {type(e).__name__}")

    # --- Tier 1: _UNIVERSAL_OPS available in UNINITIALIZED ---
    k2 = GovernanceKernel()
    assert k2.status == STATUS_UNINITIALIZED
    # session_open via kernel.open_session() is a direct write (not execute())
    # test via crp_evidence and test_checkpoint which DO go through execute()
    for tier1_op in ("crp_evidence", "test_checkpoint"):
        try:
            k2.execute(op=tier1_op, authority="test", parameters={"t": True})
        except Exception as e:
            fails.append(f"UNINITIALIZED Tier 1 op {tier1_op!r} raised: {type(e).__name__}: {e}")

    # --- Tier 2: APPLICATION op must raise GovernanceNotFounded in UNINITIALIZED ---
    from ugk import ops as _ops_module, schema as _schema
    original = dict(_ops_module.APPLICATION_OPS)
    _ops_module.APPLICATION_OPS["_t2_test"] = {"description": "t2", "tier": 2}
    _schema.GOVERNANCE_OPS["_t2_test"] = {"description": "t2", "tier": 2}
    try:
        k3 = GovernanceKernel()
        k3.execute(op="_t2_test", authority="test", parameters={})
        fails.append("APPLICATION op in UNINITIALIZED did not raise GovernanceNotFounded")
    except GovernanceNotFounded:
        pass
    except Exception as e:
        fails.append(f"APPLICATION op in UNINITIALIZED raised wrong: {type(e).__name__}")
    finally:
        _ops_module.APPLICATION_OPS.clear()
        _ops_module.APPLICATION_OPS.update(original)
        _schema.GOVERNANCE_OPS.pop("_t2_test", None)

    # --- Tier 2: APPLICATION op admitted in ACTIVE ---
    _ops_module.APPLICATION_OPS["_t2_active"] = {"description": "t2a", "tier": 2}
    _schema.GOVERNANCE_OPS["_t2_active"] = {"description": "t2a", "tier": 2}
    try:
        k4 = GovernanceKernel()
        k4._ceremony()  # transition to ACTIVE
        assert k4.status == STATUS_ACTIVE
        k4.open_session()
        k4.execute(op="_t2_active", authority="test", parameters={})
    except Exception as e:
        fails.append(f"APPLICATION op in ACTIVE raised: {type(e).__name__}: {e}")
    finally:
        _ops_module.APPLICATION_OPS.clear()
        _ops_module.APPLICATION_OPS.update(original)
        _schema.GOVERNANCE_OPS.pop("_t2_active", None)

    ok = not fails
    return ok, ("Three-tier jurisdiction enforced: Tier 0 raises KernelInternalOp, "
                "Tier 1 available in UNINITIALIZED, Tier 2 refused in UNINITIALIZED "
                "and admitted in ACTIVE." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"three_tier_jurisdiction_gate: {'PASS' if ok else 'FAIL'}  {detail}")
