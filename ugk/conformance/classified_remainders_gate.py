"""ugk/conformance/classified_remainders_gate.py — CR-S-01: CR-01..04 declared in kernel."""


def run():
    from ugk.kernel import CLASSIFIED_REMAINDERS, GovernanceKernel
    fails = []

    expected_prefixes = ["CR-01:", "CR-02:", "CR-03:", "CR-04:"]
    for prefix in expected_prefixes:
        if not any(r.startswith(prefix) for r in CLASSIFIED_REMAINDERS):
            fails.append(f"Missing classified remainder: {prefix}")

    # Verify surfaced via snapshot() and snapshot_fast()
    k = GovernanceKernel()
    fast = k.snapshot_fast()
    if "classified_remainders" not in fast:
        fails.append("classified_remainders absent from snapshot_fast()")
    elif len(fast["classified_remainders"]) < 4:
        fails.append(f"Only {len(fast['classified_remainders'])} remainders in snapshot_fast(), expected >= 4")

    snap = k.snapshot()
    if "classified_remainders" not in snap:
        fails.append("classified_remainders absent from snapshot()")

    if fails:
        return False, "; ".join(fails)
    return True, f"CR-01..04 declared and surfaced in both snapshot tiers ({len(CLASSIFIED_REMAINDERS)} entries)"


if __name__ == "__main__":
    ok, detail = run()
    print(f"classified_remainders_gate: {'PASS' if ok else 'FAIL'}  {detail}")
