"""ugk/conformance/dimension_selection_gates.py — CM-DIM-01: all CM selections admissible."""


def run():
    """For every Dimension in DIMENSION_REGISTRY:
      - selection ∈ admissible
      - selection ∉ inadmissible
    """
    from ugk.dimensions import DIMENSION_REGISTRY
    fails = []

    if not DIMENSION_REGISTRY:
        return False, "DIMENSION_REGISTRY is empty"

    for dim_id, dim in DIMENSION_REGISTRY.items():
        # selection must be in admissible
        if dim.selection not in dim.admissible:
            fails.append(
                f"{dim_id} ({dim.axis}): selection {dim.selection!r} "
                f"not in admissible {dim.admissible}"
            )
        # selection must not be in inadmissible
        if dim.selection in dim.inadmissible:
            fails.append(
                f"{dim_id} ({dim.axis}): selection {dim.selection!r} "
                f"IS in inadmissible {dim.inadmissible}"
            )
        # Every dimension must have at least one admissible value
        if not dim.admissible:
            fails.append(f"{dim_id}: admissible is empty")
        # Every dimension must have at least one inadmissible value
        if not dim.inadmissible:
            fails.append(f"{dim_id}: inadmissible is empty")

    ok = not fails
    n = len(DIMENSION_REGISTRY)
    return ok, (
        f"CM-DIM-01: all {n} dimension selections are admissible and "
        f"outside inadmissible sets ({', '.join(DIMENSION_REGISTRY.keys())})." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"dimension_selection_gates: {'PASS' if ok else 'FAIL'}  {detail}")
