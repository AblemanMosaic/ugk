"""ugk/conformance/docs_index_gate.py - docs/index.md freshness + link integrity.
GATE_GROUP = "structural"

Proves the generated documentation index is honest and complete:
  1. docs_index_gen.py is present;
  2. generated docs/index.md matches the generator output (not hand-edited / not stale);
  3. every link in the index resolves to a real file;
  4. every in-scope documentation file (root *.md + docs/**/*.md, excluding the index) is represented.

NOT_ESTABLISHED if docs_index_gen.py / docs/index.md are absent in a packaged deployment.
The index is navigation; each linked document is its own authority.
"""
import re, importlib.util
from pathlib import Path
import ugk
from ugk.conformance import NOT_ESTABLISHED


def _root():
    return Path(ugk.__file__).resolve().parent.parent


def run():
    root = _root()
    gen = root / "docs_index_gen.py"
    idx = root / "docs" / "index.md"
    if not gen.exists() or not idx.exists():
        return NOT_ESTABLISHED, "docs_index_gen.py / docs/index.md not present in this deployment"
    failures = []

    # (2) generated == source (pure stdlib generator; in-process)
    spec = importlib.util.spec_from_file_location("docs_index_gen", gen)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    text = idx.read_text(encoding="utf-8")
    if text != mod.generate():
        failures.append("docs/index.md stale vs source (run `python docs_index_gen.py`)")

    # (3) every link resolves (links are relative to docs/)
    linked = set()
    for m in re.finditer(r"\]\(([^)]+)\)", text):
        href = m.group(1)
        target = (root / "docs" / href).resolve()
        linked.add(target)
        if not target.exists():
            failures.append(f"dangling link: {href}")

    # (4) every in-scope doc is represented
    scope = mod._scope()
    for rel in scope:
        target = (root / rel).resolve()
        if target not in linked:
            failures.append(f"doc not represented in index: {rel}")

    if failures:
        return False, "docs index FAIL: " + "; ".join(failures[:8]) + (f"; +{len(failures)-8} more" if len(failures) > 8 else "")
    return True, f"docs index fresh: {len(scope)} documents indexed, all links resolve, generated == source."


if __name__ == "__main__":
    ok, detail = run()
    tag = "PASS" if ok is True else ("N/EST" if ok is NOT_ESTABLISHED else "FAIL")
    print(f"docs_index_gate: {tag}  {detail}")
