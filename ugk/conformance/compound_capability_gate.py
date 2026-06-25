"""ugk/conformance/compound_capability_gate.py — ATLAS-S-02: compound capabilities valid."""


def run():
    from ugk.invariants import INVARIANT_REGISTRY
    from ugk.adr import compound_capabilities
    fails = []

    ids = set(INVARIANT_REGISTRY.keys())

    if not compound_capabilities:
        return False, "ATLAS-S-02: compound_capabilities is empty"

    for cap_name, inv_set in compound_capabilities.items():
        if not inv_set:
            fails.append(f"Capability {cap_name!r} has empty invariant set")
        for inv_id in inv_set:
            if inv_id not in ids:
                fails.append(
                    f"Capability {cap_name!r} references unknown invariant {inv_id!r}"
                )

    # Each capability requires ≥2 invariants (compound means more than one)
    for cap_name, inv_set in compound_capabilities.items():
        if len(inv_set) < 2:
            fails.append(
                f"Capability {cap_name!r} has only {len(inv_set)} invariant "
                f"(compound requires ≥2)"
            )

    ok = not fails
    return ok, (
        f"ATLAS-S-02: {len(compound_capabilities)} compound capabilities; "
        f"all {sum(len(v) for v in compound_capabilities.values())} "
        f"invariant references valid." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"compound_capability_gate: {'PASS' if ok else 'FAIL'}  {detail}")
