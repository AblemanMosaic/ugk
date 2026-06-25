"""ugk/conformance/srsa_vector_gate.py — SRSA-S-01: valid 10-axis SRSA vector from kernel."""


def run():
    from ugk.kernel import GovernanceKernel
    from ugk.core.srsa import srsa_vector, AXIS_DESCRIPTIONS
    fails = []

    k = GovernanceKernel()
    k.open_session()
    vec = srsa_vector(k)

    required_axes = ("AdSA", "ASA", "CSA", "PSA", "ESA", "FSA", "RSA", "SSA", "ISA", "LSA")

    if len(vec) != 10:
        fails.append(f"SRSA vector has {len(vec)} axes, expected 10")

    for axis in required_axes:
        if axis not in vec:
            fails.append(f"SRSA vector missing axis: {axis}")
            continue
        entry = vec[axis]
        if "score" not in entry:
            fails.append(f"Axis {axis}: missing 'score' field")
        if "lit" not in entry:
            fails.append(f"Axis {axis}: missing 'lit' field")
        if "note" not in entry:
            fails.append(f"Axis {axis}: missing 'note' field")
        if not isinstance(entry.get("score"), int):
            fails.append(f"Axis {axis}: score is not int")

    # Lit axes (UGK native): AdSA, ASA, CSA, PSA must be lit
    for lit_axis in ("AdSA", "ASA", "CSA", "PSA"):
        if lit_axis in vec and not vec[lit_axis]["lit"]:
            fails.append(f"Axis {lit_axis} should be lit (UGK native) but lit=False")

    # Honest zeros: ISA, LSA must be lit=False
    for zero_axis in ("ISA", "LSA"):
        if zero_axis in vec and vec[zero_axis]["lit"]:
            fails.append(f"Axis {zero_axis} is an honest zero but lit=True")

    ok = not fails
    lit_axes = [ax for ax in required_axes if vec.get(ax, {}).get("lit")]
    return ok, (
        f"SRSA-S-01: 10-axis vector complete; lit={lit_axes}; "
        f"honest zeros={{ISA, LSA}}." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"srsa_vector_gate: {'PASS' if ok else 'FAIL'}  {detail}")
