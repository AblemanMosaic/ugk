"""ugk/conformance/primitive_dependency_gate.py — ATLAS-S-01: invariant DAG is valid and acyclic."""


def run():
    from ugk.invariants import INVARIANT_REGISTRY
    fails = []

    ids = set(INVARIANT_REGISTRY.keys())

    # All depends_on members exist in registry
    for inv_id, inv in INVARIANT_REGISTRY.items():
        for dep in inv.depends_on:
            if dep not in ids:
                fails.append(f"{inv_id}.depends_on contains unknown ID {dep!r}")

    # All have introduced_in set
    for inv_id, inv in INVARIANT_REGISTRY.items():
        if not inv.introduced_in:
            fails.append(f"{inv_id} has empty introduced_in")

    # DAG is acyclic (DFS)
    visited, in_stack = set(), set()

    def dfs(nid):
        if nid in in_stack:
            return False
        if nid in visited:
            return True
        in_stack.add(nid)
        inv = INVARIANT_REGISTRY.get(nid)
        if inv:
            for dep in inv.depends_on:
                if not dfs(dep):
                    fails.append(f"Cycle detected involving {nid} -> {dep}")
                    return False
        in_stack.discard(nid)
        visited.add(nid)
        return True

    for inv_id in ids:
        dfs(inv_id)

    # Verify phase lineage makes sense (Phase 1 invariants don't depend on Phase 6+)
    phase_order = {"phase1": 1, "phase2": 2, "phase3": 3, "phase4": 4,
                   "phase5": 5, "phase6": 6, "phase7": 7, "phase8": 8,
                   "phase9": 9, "phase10": 10}
    for inv_id, inv in INVARIANT_REGISTRY.items():
        p = phase_order.get(inv.introduced_in, 99)
        for dep in inv.depends_on:
            dep_inv = INVARIANT_REGISTRY.get(dep)
            if dep_inv:
                dp = phase_order.get(dep_inv.introduced_in, 99)
                if dp > p:
                    fails.append(
                        f"{inv_id} ({inv.introduced_in}) depends on "
                        f"{dep} ({dep_inv.introduced_in}) — phase ordering violated"
                    )

    ok = not fails
    n = len(INVARIANT_REGISTRY)
    return ok, (
        f"ATLAS-S-01: {n} invariants; all depends_on members valid; "
        f"DAG acyclic; phase lineage consistent." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"primitive_dependency_gate: {'PASS' if ok else 'FAIL'}  {detail}")
