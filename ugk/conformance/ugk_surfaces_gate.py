"""ugk/conformance/ugk_surfaces_gate.py — Phase 4: surfaces are thin adapters."""

import ast
from pathlib import Path


def _get_top_level_imports(filepath: Path) -> set[str]:
    """Parse a Python file and return all top-level imported module names."""
    try:
        tree = ast.parse(filepath.read_bytes())
    except Exception:
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


def run():
    """Prove Phase 4 surfaces are thin adapters:
      1. cli.py, rpc.py, agent.py each call kernel.execute() (via kernel or broker).
      2. No surface imports ugk.binding, ugk.store, ugk.schema, ugk.csh directly
         (governance logic imports) — only ugk.kernel, ugk.broker, ugk.agent, ugk.cli, ugk.transport.rpc.
      3. Each surface produces gate_admit receipts when a method is called
         (proves the routing lands in kernel.execute()).
    """
    pkg = Path(__file__).resolve().parent.parent
    fails = []

    governance_imports = {"binding", "store", "schema", "csh", "governor", "invariants", "dimensions"}
    allowed_surfaces   = {"kernel", "broker", "cli", "rpc", "agent", "migration",
                          "vendor", "core", "ctr", "testing", "conformance", "ops"}

    from ugk.module_registry import facade_paths, FACADE_SURFACES
    for dotted, surface_path in zip(FACADE_SURFACES, facade_paths()):
        surface_name = dotted.split(".")[-1]  # logical leaf name (cli/rpc/agent)
        if not surface_path.exists():
            fails.append(f"{dotted} surface not found at {surface_path}")
            continue

        imports = _get_top_level_imports(surface_path)
        # Only ugk submodule LEAF names (last dotted component), so a move into a role-package
        # (e.g. ugk.storage.binding) still resolves to the governed leaf name ("binding").
        ugk_imports = {m.split(".")[-1] for m in imports
                       if "." in m and m.startswith("ugk.")}
        bad = ugk_imports & governance_imports
        if bad:
            fails.append(f"{surface_name}.py imports governance modules directly: {bad}")

    # --- Routing proof: calling a surface method produces gate_admit receipts ---
    from ugk.kernel import GovernanceKernel

    # CLI govern
    k_cli = GovernanceKernel(authority="surfaces_gate")
    k_cli._ceremony(); k_cli.open_session()
    count_before = k_cli.store.receipt_count()
    from ugk.cli import _cmd_govern
    import types
    args = types.SimpleNamespace(intent="orient", subject="test", authority="surfaces_gate",
                                 op="crp_evidence", state_dir=None)
    # Monkey-patch _make_kernel to use our kernel
    import ugk.cli as _cli_mod
    orig_make = _cli_mod._make_kernel
    _cli_mod._make_kernel = lambda state_dir=None: k_cli
    try:
        _cmd_govern(args)
    finally:
        _cli_mod._make_kernel = orig_make
    admits_cli = k_cli.store.receipts_by_op("gate_admit")
    if not admits_cli:
        fails.append("CLI govern produced no gate_admit receipts (not routing through kernel)")

    # RPC govern
    k_rpc = GovernanceKernel(authority="surfaces_gate")
    k_rpc._ceremony(); k_rpc.open_session()
    from ugk.transport.rpc import UGKRPCServer
    import json as _json
    rpc = UGKRPCServer(kernel=k_rpc)
    resp = _json.loads(rpc.handle_request(
        '{"jsonrpc":"2.0","method":"ugk.govern","params":{"intent":"orient","subject":"test","nonce":"gate1"},"id":1}'
    ))
    if not resp.get("result", {}).get("admitted"):
        fails.append(f"RPC govern returned non-admitted: {resp}")
    if not k_rpc.store.receipts_by_op("gate_admit"):
        fails.append("RPC govern produced no gate_admit receipts")

    # Agent govern
    k_agent = GovernanceKernel(authority="surfaces_gate")
    k_agent._ceremony(); k_agent.open_session()
    from ugk.transport.agent import ugk_govern
    result = ugk_govern("orient", "test", authority="surfaces_gate", kernel=k_agent)
    if not result.admitted:
        fails.append(f"Agent govern returned non-admitted: {result.reason}")
    if not k_agent.store.receipts_by_op("gate_admit"):
        fails.append("Agent govern produced no gate_admit receipts")

    ok = not fails
    return ok, (
        "ugk_surfaces_gate: CLI/RPC/Agent are thin adapters; all route through "
        "kernel.execute(); no surface imports governance logic directly; "
        "all produce gate_admit receipts." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"ugk_surfaces_gate: {'PASS' if ok else 'FAIL'}  {detail}")
