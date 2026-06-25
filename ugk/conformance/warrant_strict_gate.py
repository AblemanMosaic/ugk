"""ugk/conformance/warrant_strict_gate.py — load-bearing warrant under require_warrant.

Proves the strengthened CM-S-03 semantics (closing the auditor/attacker
"tiny crack" — warrant_basis declared but no durable warrant emitted):

  1. trace_only (require_warrant=False): warrant production failure
     (e.g. no WarrantStore attached) is permissive — the op completes,
     no warrant materialized. This is the existing semantics.
  2. require_warrant=True without warrant_basis: KernelInternalOp.
     (Existing CM-S-03; reproved here for completeness.)
  3. require_warrant=True with warrant_basis but failing materialization:
     KernelInternalOp (the strengthening — warrant_basis can never mean
     "we intended a warrant but didn't get one" in strict mode).
  4. require_warrant=True with warrant_basis + WarrantStore attached:
     op succeeds AND a durable warrant is in the store.
"""


def run():
    import tempfile, os
    from ugk.kernel import GovernanceKernel, KernelInternalOp, _UNIVERSAL_OPS
    from ugk.governance.warrant import WarrantStore
    from ugk.authority.authority_model import AuthorityModel
    from ugk import ops as _ops, schema as _schema
    fails = []

    # Declare a Tier-2 test op so we exercise the require_warrant code path
    # (kernel/universal-tier ops bypass the authority-model checks).
    _ops.APPLICATION_OPS["_warrant_strict_test"] = {
        "description": "warrant_strict_gate probe op",
        "tier": 2,
    }
    _schema.GOVERNANCE_OPS["_warrant_strict_test"] = _ops.APPLICATION_OPS["_warrant_strict_test"]
    try:
        # --- 1. trace_only: missing WarrantStore is permissive ---
        k = GovernanceKernel()
        k._ceremony(); k.open_session()
        # default AuthorityModel is trace_only; ensure no WarrantStore attached
        k._warrant_store = None
        try:
            k.execute(op="_warrant_strict_test", authority="test",
                      parameters={"x": 1}, warrant_basis=["LEGEND-S-01"])
        except Exception as e:
            fails.append(f"trace_only: op should not fail with missing WarrantStore, got {type(e).__name__}: {e}")

        # --- 2. require_warrant=True without warrant_basis: KernelInternalOp ---
        k2 = GovernanceKernel()
        k2._ceremony(); k2.open_session()
        am = AuthorityModel.create(
            "strict_test", require_gate=False, require_warrant=True,
            require_intent=False, description="test", rationale="test",
            law_hash=k2._law_hash, authority="test")
        k2._authority_model = am
        try:
            k2.execute(op="_warrant_strict_test", authority="test", parameters={})
            fails.append("require_warrant=True without warrant_basis: should have raised")
        except KernelInternalOp:
            pass
        except Exception as e:
            fails.append(f"require_warrant=True without warrant_basis: wrong exception {type(e).__name__}: {e}")

        # --- 3. require_warrant=True with warrant_basis but no WarrantStore: KernelInternalOp ---
        # The materialization itself fails because there's nothing to persist into,
        # but more critically: the test verifies that the strengthening fires —
        # under require_warrant the op refuses rather than silently succeeding without a durable warrant.
        # Inject failure by replacing the WarrantStore with one that raises on write.
        k3 = GovernanceKernel()
        k3._ceremony(); k3.open_session()
        k3._authority_model = am
        class _PoisonStore:
            def write(self, _w): raise RuntimeError("simulated materialization failure")
        k3._warrant_store = _PoisonStore()
        try:
            k3.execute(op="_warrant_strict_test", authority="test",
                       parameters={"x": 2}, warrant_basis=["LEGEND-S-01"])
            fails.append("require_warrant=True + materialization failure: should have raised")
        except KernelInternalOp as e:
            if "warrant materialization failed" not in str(e):
                fails.append(f"wrong message: {e}")
        except Exception as e:
            fails.append(f"materialization-failure: wrong exception {type(e).__name__}: {e}")

        # --- 4. require_warrant=True with warrant_basis + real WarrantStore: succeeds + durable ---
        k4 = GovernanceKernel()
        k4._ceremony(); k4.open_session()
        k4._authority_model = am
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "warrants.db")
            with WarrantStore(db_path) as ws:
                k4._warrant_store = ws
                try:
                    k4.execute(op="_warrant_strict_test", authority="test",
                               parameters={"x": 3}, warrant_basis=["LEGEND-S-01"])
                except Exception as e:
                    fails.append(f"happy path failed: {type(e).__name__}: {e}")
                else:
                    # Verify a warrant is durably present and the receipt points at it.
                    stored = k4._warrant_store.all_warrants()
                    last = k4._store.all_receipts()[-1]
                    if not stored:
                        fails.append("happy path: op succeeded but no durable warrant in store")
                    elif not last.warrant_id or k4._warrant_store.get(last.warrant_id) is None:
                        fails.append("happy path: receipt warrant_id is not durably readable")
            k4._warrant_store = None
    finally:
        _ops.APPLICATION_OPS.pop("_warrant_strict_test", None)
        _schema.GOVERNANCE_OPS.pop("_warrant_strict_test", None)

    ok = not fails
    return ok, (
        "warrant_strict_gate: trace_only permissive; require_warrant=True "
        "refuses on (missing warrant_basis | materialization failure); "
        "happy path succeeds with durable warrant in store."
        if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"warrant_strict_gate: {'PASS' if ok else 'FAIL'}  {detail}")
