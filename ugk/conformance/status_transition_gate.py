"""ugk/conformance/status_transition_gate.py — CM-GS-01: UNINITIALIZED → ACTIVE via ceremony."""


def run():
    from ugk.kernel import (
        GovernanceKernel, GovernanceNotFounded,
        STATUS_UNINITIALIZED, STATUS_ACTIVE,
    )
    fails = []

    # Fresh kernel is UNINITIALIZED
    k = GovernanceKernel()
    if k.status != STATUS_UNINITIALIZED:
        fails.append(f"Fresh kernel is {k.status!r}, expected UNINITIALIZED")

    # CRYSTALLIZED must not be a reachable state — verify no constant for it
    from ugk import kernel as _km
    if hasattr(_km, "STATUS_CRYSTALLIZED"):
        fails.append("STATUS_CRYSTALLIZED exists — CRYSTALLIZED state must not be declared")

    # After _ceremony(), status is ACTIVE
    k._ceremony()
    if k.status != STATUS_ACTIVE:
        fails.append(f"After _ceremony(), status is {k.status!r}, expected ACTIVE")

    # law_hash must be populated in ACTIVE
    if not k._law_hash:
        fails.append("law_hash is empty after _ceremony() — should be SHA-256(invariants.py)")

    # law_hash must be a valid 64-char hex string
    lh = k._law_hash
    if len(lh) != 64 or not all(c in "0123456789abcdef" for c in lh):
        fails.append(f"law_hash {lh!r} is not a valid SHA-256 hex digest")

    # ACTIVE kernel must accept APPLICATION ops (even with empty registry)
    # Verify by declaring one temporarily
    from ugk import ops as _ops_module, schema as _schema
    original = dict(_ops_module.APPLICATION_OPS)
    _ops_module.APPLICATION_OPS["_st_active"] = {"t": 2}
    _schema.GOVERNANCE_OPS["_st_active"] = {"t": 2}
    try:
        k.open_session()
        k.execute(op="_st_active", authority="test", parameters={})
    except GovernanceNotFounded:
        fails.append("APPLICATION op raised GovernanceNotFounded in ACTIVE status")
    except Exception as e:
        fails.append(f"APPLICATION op in ACTIVE raised unexpected: {type(e).__name__}: {e}")
    finally:
        _ops_module.APPLICATION_OPS.clear()
        _ops_module.APPLICATION_OPS.update(original)
        _schema.GOVERNANCE_OPS.pop("_st_active", None)

    ok = not fails
    return ok, ("Status lifecycle: UNINITIALIZED → ACTIVE via ceremony; "
                "CRYSTALLIZED not reachable; law_hash populated in ACTIVE." if ok
                else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"status_transition_gate: {'PASS' if ok else 'FAIL'}  {detail}")
