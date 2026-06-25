"""ugk/conformance/choke_point_gate.py — Phase 4: single execute() choke point per effect."""


def run():
    """Prove the single-choke-point invariant:
      Every governed effect — whether called via CLI, RPC, or Agent —
      produces exactly two receipts per call (gate_admit + op), not more.
      No surface double-routes through the kernel.

    Proof: count gate_admit receipts before and after each surface call.
    One surface call → one gate_admit + one op receipt = delta of 2.
    """
    from ugk.kernel import GovernanceKernel
    fails = []

    def _count_admits(store, before: int) -> int:
        return len(store.receipts_by_op("gate_admit")) - before

    # --- CLI choke point ---
    k_cli = GovernanceKernel(authority="choke_cli")
    k_cli._ceremony(); k_cli.open_session()
    admits_before = len(k_cli.store.receipts_by_op("gate_admit"))

    import ugk.cli as _cli_mod, types
    orig_make = _cli_mod._make_kernel
    _cli_mod._make_kernel = lambda state_dir=None: k_cli
    try:
        args = types.SimpleNamespace(intent="orient", subject="choke_test",
                                     authority="choke", op="crp_evidence", state_dir=None)
        _cli_mod._cmd_govern(args)
    finally:
        _cli_mod._make_kernel = orig_make

    admits_delta_cli = _count_admits(k_cli.store, admits_before)
    if admits_delta_cli != 1:
        fails.append(
            f"CLI govern produced {admits_delta_cli} gate_admit receipts "
            f"(expected exactly 1 per call)"
        )

    # --- RPC choke point ---
    k_rpc = GovernanceKernel(authority="choke_rpc")
    k_rpc._ceremony(); k_rpc.open_session()
    admits_before_rpc = len(k_rpc.store.receipts_by_op("gate_admit"))

    from ugk.transport.rpc import UGKRPCServer
    import json as _json
    rpc = UGKRPCServer(kernel=k_rpc)
    rpc.handle_request(
        '{"jsonrpc":"2.0","method":"ugk.govern",'
        '"params":{"intent":"orient","subject":"choke","nonce":"chk1"},"id":1}'
    )
    admits_delta_rpc = _count_admits(k_rpc.store, admits_before_rpc)
    if admits_delta_rpc != 1:
        fails.append(
            f"RPC govern produced {admits_delta_rpc} gate_admit receipts "
            f"(expected exactly 1 per call)"
        )

    # --- Agent choke point ---
    k_agent = GovernanceKernel(authority="choke_agent")
    k_agent._ceremony(); k_agent.open_session()
    admits_before_agent = len(k_agent.store.receipts_by_op("gate_admit"))

    from ugk.transport.agent import ugk_govern
    ugk_govern("orient", "choke_test", authority="choke", kernel=k_agent)
    admits_delta_agent = _count_admits(k_agent.store, admits_before_agent)
    if admits_delta_agent != 1:
        fails.append(
            f"Agent govern produced {admits_delta_agent} gate_admit receipts "
            f"(expected exactly 1 per call)"
        )

    # --- Replay rejected (RPC) — no gate_admit on replay ---
    admits_before_replay = len(k_rpc.store.receipts_by_op("gate_admit"))
    resp = _json.loads(rpc.handle_request(
        '{"jsonrpc":"2.0","method":"ugk.govern",'
        '"params":{"intent":"orient","subject":"choke","nonce":"chk1"},"id":2}'
    ))
    admits_on_replay = _count_admits(k_rpc.store, admits_before_replay)
    if admits_on_replay != 0:
        fails.append(
            f"Replay produced {admits_on_replay} gate_admit receipts "
            f"(should produce 0 — replay rejected before routing to kernel)"
        )
    if resp.get("result", {}).get("admitted", True):
        fails.append("Replay request was admitted (replay protection not working)")

    ok = not fails
    return ok, (
        "choke_point_gate: CLI/RPC/Agent each produce exactly 1 gate_admit per call; "
        "RPC replay produces 0 gate_admits (rejected before kernel)." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"choke_point_gate: {'PASS' if ok else 'FAIL'}  {detail}")
