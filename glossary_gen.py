#!/usr/bin/env python3
"""Generate GLOSSARY.md from GLOSSARY.json (deterministic, side-effect-free).

GLOSSARY.md is GENERATED. Do not hand-edit it. Edit GLOSSARY.json (or the cited source) and regenerate:
    python glossary_gen.py            # write GLOSSARY.md
    python glossary_gen.py --check    # exit 1 if GLOSSARY.md would change
The glossary is navigation, not law. The sources each entry cites are authority.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _src(ref: str) -> str:
    return f"`{ref}`"


def generate() -> str:
    doc = json.loads((ROOT / "GLOSSARY.json").read_text(encoding="utf-8"))
    terms = doc["terms"]
    by_cat = {}
    for e in terms:
        by_cat.setdefault(e["category"], []).append(e)
    lines = []
    lines.append("# UGK Glossary — generated term index")
    lines.append("")
    lines.append("**Generated from `GLOSSARY.json`. Do not hand-edit.** This is a navigation/lookup artifact, not law: "
                 "each term names where it lives, what it is, what it is not, and which source owns truth. "
                 "The cited sources are authority; this index is not.")
    lines.append("")
    lines.append(f"Verified against release: {doc.get('verified_against_release') or doc.get('release') or '?'} · {len(terms)} terms · {len(by_cat)} categories. "
                 "Authoritative projections: `ugk/codex/CODEX.md` (generated law projection), "
                 "`IMPLEMENTATION_CODEX.md` (human navigation). For live unknowns: `ugk explain <id>`.")
    lines.append("")
    # index
    lines.append("## Terms")
    lines.append("")
    for e in sorted(terms, key=lambda x: x["term"].lower()):
        anchor = e["term"].lower().replace(" ", "-").replace("/", "").replace("`", "").replace("_", "-")
        lines.append(f"- [{e['term']}](#{anchor}) — {e['short_definition']}")
    lines.append("")
    # entries by category
    for cat in sorted(by_cat):
        lines.append(f"## Category: {cat}")
        lines.append("")
        for e in sorted(by_cat[cat], key=lambda x: x["term"].lower()):
            lines.append(f"### {e['term']}")
            if e.get("aliases"):
                lines.append(f"*aliases:* {', '.join(e['aliases'])}  ")
            lines.append(f"*status:* {e['status']} · *introduced:* {e['introduced_release']} · "
                         f"*last verified:* {e['last_verified_release']}  ")
            lines.append("")
            lines.append(e["short_definition"])
            lines.append("")
            lines.append(f"- **is not:** {e['not_this']}")
            lines.append(f"- **agent rule:** {e['agent_rule']}")
            if e.get("authoritative_sources"):
                lines.append("- **authoritative sources:** " + ", ".join(_src(s) for s in e["authoritative_sources"]))
            if e.get("implementation_surfaces"):
                lines.append("- **surfaces:** " + ", ".join(_src(s) for s in e["implementation_surfaces"]))
            if e.get("related_invariants"):
                lines.append("- **invariants:** " + ", ".join(e["related_invariants"]))
            if e.get("related_adrs"):
                lines.append("- **ADRs:** " + ", ".join(e["related_adrs"]))
            if e.get("related_terms"):
                lines.append("- **related:** " + ", ".join(e["related_terms"]))
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    out = ROOT / "GLOSSARY.md"
    content = generate()
    if "--check" in sys.argv:
        cur = out.read_text(encoding="utf-8") if out.exists() else ""
        if cur != content:
            print("GLOSSARY.md is stale — run: python glossary_gen.py")
            return 1
        print("GLOSSARY.md is current.")
        return 0
    out.write_text(content, encoding="utf-8")
    print(f"GLOSSARY.md written ({len(content.splitlines())} lines, {len(content)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
