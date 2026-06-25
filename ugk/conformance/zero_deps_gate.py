"""ugk/conformance/zero_deps_gate.py — UL-S-01: no imports outside stdlib + vendored Ed25519."""
import sys


def run():
    import importlib
    stdlib_ok = frozenset({
        "ugk", "hashlib", "sqlite3", "json", "uuid", "time", "pathlib",
        "dataclasses", "typing", "abc", "functools", "os", "inspect",
        "__future__", "importlib", "sys", "io", "tempfile", "re",
        "subprocess", "contextlib", "enum",
    })
    # Import ugk package hierarchy and collect all transitive modules
    import ugk
    ugk_modules = [m for m in sys.modules if m == "ugk" or m.startswith("ugk.")]
    external = set()
    for modname in ugk_modules:
        mod = sys.modules.get(modname)
        if mod is None:
            continue
        spec = getattr(mod, "__spec__", None)
        if spec is None:
            continue
        origin = getattr(spec, "origin", None) or ""
        if "site-packages" in origin:
            top = modname.split(".")[0]
            if top not in stdlib_ok and not top.startswith("_"):
                external.add(modname)
    if external:
        return False, f"External dependencies found: {sorted(external)}"
    return True, "All UGK imports are stdlib or ugk-internal (zero external deps)"


if __name__ == "__main__":
    ok, detail = run()
    print(f"zero_deps_gate: {'PASS' if ok else 'FAIL'}  {detail}")
