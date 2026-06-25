"""ugk/conformance/adr_gate.py — ATLAS-S-03: every ADR bound to invariants."""


def run():
    from ugk.invariants import INVARIANT_REGISTRY
    from ugk.adr import ADR_REGISTRY
    fails = []

    ids = set(INVARIANT_REGISTRY.keys())

    if not ADR_REGISTRY:
        return False, "ATLAS-S-03: ADR_REGISTRY is empty"

    # Every ADR has at least one bound_invariant in registry
    for adr_id, adr in ADR_REGISTRY.items():
        if not adr.bound_invariants:
            fails.append(f"ADR {adr_id} has no bound_invariants")
        for inv_id in adr.bound_invariants:
            if inv_id not in ids:
                fails.append(
                    f"ADR {adr_id} references unknown invariant {inv_id!r}"
                )

    # Every ADR has non-empty context, decision, consequences
    for adr_id, adr in ADR_REGISTRY.items():
        for field in ("context", "decision", "consequences"):
            if not getattr(adr, field).strip():
                fails.append(f"ADR {adr_id}.{field} is empty")
        if not adr.alternatives:
            fails.append(f"ADR {adr_id} has no alternatives (rejected options)")

    # Collect all bound invariants across all ADRs
    bound = set()
    for adr in ADR_REGISTRY.values():
        bound.update(adr.bound_invariants)

    # Core architectural invariants should be bound to at least one ADR
    expected_bound = {"UL-G-01", "UL-S-02", "UL-S-03", "CHC-S-01", "CTR-S-07",
                      "GK-S-01", "LEGEND-S-02", "AUDIT-S-01"}
    for inv_id in expected_bound:
        if inv_id not in bound:
            fails.append(f"Core invariant {inv_id} not bound to any ADR")

    ok = not fails
    return ok, (
        f"ATLAS-S-03: {len(ADR_REGISTRY)} ADRs covering {len(bound)} invariants; "
        f"all bound_invariants valid; all required fields present." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"adr_gate: {'PASS' if ok else 'FAIL'}  {detail}")
