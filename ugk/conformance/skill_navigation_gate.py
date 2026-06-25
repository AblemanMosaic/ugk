"""ugk/conformance/skill_navigation_gate.py - SKILL.md navigation-seam integrity.
GATE_GROUP = "structural"

The agent-facing seam that the docs review flagged: SKILL.md must route an agent onward, and the targets it
names must exist. This gate proves SKILL.md references each navigation surface AND that each referenced
artifact is present, so the boot document cannot silently become a dead end.

NOT_ESTABLISHED if SKILL.md is absent in a packaged deployment.
"""
from pathlib import Path
import ugk
from ugk.conformance import NOT_ESTABLISHED

# (mention-token, must-exist-path or None for CLI/concept tokens)
REQUIRED = [
    ("IMPLEMENTATION_CODEX.md", "IMPLEMENTATION_CODEX.md"),
    ("GLOSSARY.md", "GLOSSARY.md"),
    ("ugk/codex/CODEX.md", "ugk/codex/CODEX.md"),
    ("ugk explain", None),
    ("examples/governed/a1_example.py", "examples/governed/a1_example.py"),
    ("INTEGRITY_BASIS.md", "INTEGRITY_BASIS.md"),
    ("effect-atomicity", None),
    ("ck-canon-float-ban", None),
    ("rho-integration-posture", None),
]


def run():
    root = Path(ugk.__file__).resolve().parent.parent
    skill = root / "SKILL.md"
    if not skill.exists():
        return NOT_ESTABLISHED, "SKILL.md not present in this deployment"
    text = skill.read_text(encoding="utf-8")
    failures = []
    for token, must_exist in REQUIRED:
        if token not in text:
            failures.append(f"SKILL.md does not reference '{token}'")
        if must_exist and not (root / must_exist).exists():
            failures.append(f"referenced artifact missing: {must_exist}")
    if failures:
        return False, "SKILL navigation FAIL: " + "; ".join(failures[:8])
    return True, ("SKILL.md routes the agent onward: implementation codex + glossary + generated codex + "
                  "`ugk explain` + direct example + integrity basis; all targets present.")


if __name__ == "__main__":
    ok, detail = run()
    tag = "PASS" if ok is True else ("N/EST" if ok is NOT_ESTABLISHED else "FAIL")
    print(f"skill_navigation_gate: {tag}  {detail}")
