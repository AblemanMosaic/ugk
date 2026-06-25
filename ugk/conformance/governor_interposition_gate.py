"""ugk/conformance/governor_interposition_gate.py — Phase 2: Governor interposition point structural proof."""


def run():
    """Prove the Governor interposition structural invariant:

    1. kernel._require_governor_sig is accessible and defaults to False.
    2. Flipping it to True gates ALL Tier 2 ops — Governor controls the
       interposition point, not callers.
    3. Tier 1 (Universal) ops are always interposition-exempt.
    4. The interposition flag is kernel-state — not a parameter that callers
       can bypass by omitting it.

    This gate proves the structural property: Governor CAN gate any
    application-layer operation.  It does not re-test signature mechanics
    (that is governor_enforcement_gate's responsibility).
    """
    from ugk.kernel import GovernanceKernel, STATUS_ACTIVE, _PHASE_CODE
    from ugk.governance.governor import GovernorSignatureRequired
    from ugk import ops as _ops_module, schema as _schema
    fails = []

    # --- Structural check 1: flag exists and defaults to False ---
    k = GovernanceKernel()
    if not hasattr(k, "_require_governor_sig"):
        return False, "kernel missing _require_governor_sig attribute"
    if k._require_governor_sig is not False:
        fails.append(f"_require_governor_sig default is {k._require_governor_sig!r}, expected False")

    # --- Structural check 2: interposition is kernel-state, not call-site ---
    # Register a Tier 2 op
    original = dict(_ops_module.APPLICATION_OPS)
    _ops_module.APPLICATION_OPS["_interpose_op"] = {"tier": 2}
    _schema.GOVERNANCE_OPS["_interpose_op"] = {"tier": 2}
    try:
        k._ceremony()
        k.open_session()
        assert k.status == STATUS_ACTIVE

        # Without flag: Tier 2 op passes without governor_sig
        try:
            k.execute(op="_interpose_op", authority="test", parameters={})
        except Exception as e:
            fails.append(f"Tier 2 op raised when flag=False: {type(e).__name__}: {e}")

        # Governor sets the flag — now ALL Tier 2 calls are intercepted
        k._require_governor_sig = True

        # Call without governor_sig param — intercepted at kernel level
        try:
            k.execute(op="_interpose_op", authority="test", parameters={})
            fails.append("Tier 2 op passed without sig after Governor set interposition flag")
        except GovernorSignatureRequired:
            pass  # correct: Governor controls the interposition point
        except Exception as e:
            fails.append(f"Wrong exception after Governor set flag: {type(e).__name__}: {e}")

        # --- Structural check 3: Tier 1 ops always exempt ---
        tier1_ops = ("crp_evidence", "test_checkpoint")
        for tier1_op in tier1_ops:
            try:
                k.execute(op=tier1_op, authority="test", parameters={"exempt": True})
            except GovernorSignatureRequired:
                fails.append(f"Tier 1 op {tier1_op!r} was gated by interposition (wrong)")
            except Exception as e:
                fails.append(f"Tier 1 op {tier1_op!r} raised unexpected: {type(e).__name__}: {e}")

        # --- Structural check 4: mosaic_root and dimension_id present post-ceremony ---
        snap = k.snapshot_fast()
        if not snap.get("mosaic_root"):
            fails.append("mosaic_root absent from snapshot_fast() after ceremony")
        if not snap.get("dimension_id"):
            fails.append("dimension_id absent from snapshot_fast() after ceremony")
        if snap.get("require_governor_sig") is not True:
            fails.append("require_governor_sig not surfaced in snapshot_fast()")

    finally:
        _ops_module.APPLICATION_OPS.clear()
        _ops_module.APPLICATION_OPS.update(original)
        _schema.GOVERNANCE_OPS.pop("_interpose_op", None)

    ok = not fails
    return ok, (
        "governor_interposition_gate: interposition point structural proof — "
        "flag defaults False; Governor sets it; Tier 1 exempt; "
        "mosaic_root + dimension_id in snapshot." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"governor_interposition_gate: {'PASS' if ok else 'FAIL'}  {detail}")
