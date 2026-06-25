"""ugk/conformance/invariant_registry_gate.py — CTR-S-01: invariant registry is the coverage map."""


def run():
    """Prove the invariant registry IS the coverage map — no JSON binding layer.

    Checks:
      1. Every Invariant in INVARIANT_REGISTRY has id, statement, gate, classification,
         adjacency_target (all non-empty).
      2. Every declared gate name corresponds to an actual file in conformance/.
      3. CTR.discover() + analyse() can consume the registry without raising.
      4. The total invariant count matches the declared Phase 1 scope (≥ 20).
    """
    from ugk.invariants import INVARIANT_REGISTRY
    from pathlib import Path
    fails = []

    if len(INVARIANT_REGISTRY) < 20:
        fails.append(f"Only {len(INVARIANT_REGISTRY)} invariants declared, expected ≥ 20")

    conformance_dir = Path(__file__).parent

    for inv_id, inv in INVARIANT_REGISTRY.items():
        # All fields must be non-empty
        for field_name in ("id", "statement", "gate", "classification", "adjacency_target"):
            val = getattr(inv, field_name, "")
            if not val or not val.strip():
                fails.append(f"{inv_id}: field {field_name!r} is empty")
        # id must match registry key
        if inv.id != inv_id:
            fails.append(f"Registry key {inv_id!r} != Invariant.id {inv.id!r}")
        # gate file must exist in conformance/
        gate_file = conformance_dir / f"{inv.gate}.py"
        if not gate_file.exists():
            fails.append(f"{inv_id}: gate file conformance/{inv.gate}.py not found")
        # classification must be one of the three declared values
        if inv.classification not in ("DOMAIN_PHYSICS", "MIXED", "ABI_CONFIG"):
            fails.append(f"{inv_id}: unknown classification {inv.classification!r}")

    # CTR.discover() + analyse() on a dummy module (no gate_test functions)
    from ugk.ctr import CTR
    import types
    dummy = types.ModuleType("dummy_invariants_test")
    ctr = CTR(required_invariants=set(INVARIANT_REGISTRY.keys()))
    discovered = ctr.discover(dummy)
    try:
        report = ctr.analyse(
            test_functions=discovered,
            evidence_source="invariant_registry_gate",
        )
        if report.evidence_source is None:
            fails.append("CTR analyse() returned report with evidence_source=None")
    except Exception as e:
        fails.append(f"CTR.analyse() raised: {type(e).__name__}: {e}")

    ok = not fails
    n = len(INVARIANT_REGISTRY)
    return ok, (
        f"CTR-S-01: invariant registry is the coverage map — "
        f"{n} invariants, all fields populated, all gate files present; "
        f"CTR.analyse() consumed registry without error." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"invariant_registry_gate: {'PASS' if ok else 'FAIL'}  {detail}")
