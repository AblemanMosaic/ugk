"""ugk/conformance/bs01_gate.py — UL-S-03: undeclared op raises UndeclaredOp."""


def run():
    from ugk.kernel import GovernanceKernel, UndeclaredOp
    fails = []

    k = GovernanceKernel()
    k._ceremony()   # ACTIVE: GovernanceNotFounded no longer pre-empts UndeclaredOp
    k.open_session()

    undeclared_ops = [
        "fly_to_moon",
        "delete_everything",
        "_private_but_not_declared",
        "session_open_fake",
    ]
    for op in undeclared_ops:
        try:
            k.execute(op=op, authority="test", parameters={})
            fails.append(f"Undeclared op {op!r} did not raise UndeclaredOp")
        except UndeclaredOp:
            pass
        except Exception as e:
            fails.append(f"Undeclared op {op!r} raised {type(e).__name__} instead of UndeclaredOp")

    ok = not fails
    return ok, (f"BS-01: all {len(undeclared_ops)} undeclared ops raised UndeclaredOp" if ok
                else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"bs01_gate: {'PASS' if ok else 'FAIL'}  {detail}")
