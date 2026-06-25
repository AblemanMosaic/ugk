"""ugk/conformance/governor_key_unset_gate.py — CHARTER-S-01 fail-closed.

Re-enlivened 2026-06-10 (Option K): proves the unset sentinel can never found
governance. Posture-aware — on founded trees the sentinel is injected via
monkeypatch so the refusal path is proven on every run; on unfounded trees the
live identity itself is proven fail-closed.
"""


def run():
    import ugk.kernel as kmod
    from ugk.kernel import GovernanceKernel, STATUS_UNINITIALIZED, GovernanceNotFounded
    from ugk import ops as _ops, schema as _schema
    from ugk.conformance._fixture import unfounded
    fails = []
    posture = "unfounded" if unfounded() else "founded"

    _orig_key = kmod.GOVERNOR_PUBKEY_HEX
    _orig_ops = dict(_ops.APPLICATION_OPS)
    _ops.APPLICATION_OPS["_unset_test_op"] = {"description": "t", "tier": 2}
    _schema.GOVERNANCE_OPS["_unset_test_op"] = {"description": "t", "tier": 2}
    try:
        # Force the sentinel (no-op on unfounded trees; injection on founded)
        kmod.GOVERNOR_PUBKEY_HEX = "GOVERNOR_KEY_UNSET__RUN_UGK_CHARTER"

        k = GovernanceKernel()
        if k.status != STATUS_UNINITIALIZED:
            fails.append(f"fresh sentinel kernel status {k.status!r}, expected UNINITIALIZED")

        # Ceremony must refuse (Option K guard)
        try:
            k._ceremony()
            fails.append("sentinel ceremony ADMITTED — UNINITIALIZED→ACTIVE under unset key")
        except GovernanceNotFounded:
            pass
        except Exception as e:
            fails.append(f"sentinel ceremony wrong exception: {type(e).__name__}: {e}")

        if k.status != STATUS_UNINITIALIZED:
            fails.append(f"status {k.status!r} after refused ceremony, expected UNINITIALIZED")

        # Tier-2 must refuse in UNINITIALIZED
        k.open_session()  # Tier-1 UNIVERSAL — lawful under any identity
        try:
            k.execute(op="_unset_test_op", authority="test", parameters={})
            fails.append("Tier-2 op ADMITTED on sentinel/UNINITIALIZED kernel")
        except GovernanceNotFounded:
            pass
        except Exception as e:
            fails.append(f"Tier-2 refusal wrong exception: {type(e).__name__}: {e}")
    finally:
        kmod.GOVERNOR_PUBKEY_HEX = _orig_key
        _ops.APPLICATION_OPS.clear(); _ops.APPLICATION_OPS.update(_orig_ops)
        _schema.GOVERNANCE_OPS.pop("_unset_test_op", None)

    ok = not fails
    return ok, (
        f"CHARTER-S-01 fail-closed proven ({posture} tree, sentinel injected): "
        "ceremony refused; UNINITIALIZED held; Tier-2 refused; Tier-1 lawful."
        if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"governor_key_unset_gate: {'PASS' if ok else 'FAIL'}  {detail}")
