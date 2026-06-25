"""ugk/conformance/liveness_gate.py — UL-L-01: all UGK modules import in one process, no side effects."""


def run():
    fails = []
    modules_to_check = [
        "ugk",
        "ugk.storage.binding",
        "ugk.schema",
        "ugk.storage.store",
        "ugk.kernel",
        "ugk.transport.broker",
        "ugk.invariants",
        "ugk.dimensions",
        "ugk.ops",
        "ugk.core",
        "ugk.core.vocab",
        "ugk.core.esa",
        "ugk.core.srsa",
        "ugk.ctr",
        "ugk.testing",
        "ugk.testing.headless_runner",
    ]
    for modname in modules_to_check:
        try:
            import importlib
            importlib.import_module(modname)
        except Exception as e:
            fails.append(f"{modname}: {type(e).__name__}: {e}")

    if fails:
        return False, f"Import failures: {fails}"
    return True, f"All {len(modules_to_check)} UGK modules import cleanly in one process"


if __name__ == "__main__":
    ok, detail = run()
    print(f"liveness_gate: {'PASS' if ok else 'FAIL'}  {detail}")
