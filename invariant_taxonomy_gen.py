#!/usr/bin/env python3
"""Generate INVARIANT_TAXONOMY.md from INVARIANT_TAXONOMY.json (deterministic, side-effect-free).

INVARIANT_TAXONOMY.md is GENERATED. Do not hand-edit it. Edit INVARIANT_TAXONOMY.json (or the cited
source) and regenerate:
    python invariant_taxonomy_gen.py            # write INVARIANT_TAXONOMY.md
    python invariant_taxonomy_gen.py --check    # exit 1 if it would change
The taxonomy is navigation, not law. Each record's cited source_refs are authority; this index is not.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def generate() -> str:
    doc = json.loads((ROOT / "INVARIANT_TAXONOMY.json").read_text(encoding="utf-8"))
    recs = doc["records"]
    by_fam: dict[str, list] = {}
    for r in recs:
        by_fam.setdefault(r["semantic_family"], []).append(r)
    L = []
    L.append("# UGK Invariant Taxonomy — generated navigation layer")
    L.append("")
    L.append("**Generated from `INVARIANT_TAXONOMY.json`. Do not hand-edit.** This maps every live UGK "
             "invariant to a curated semantic family, subsystem, frame role, gate, source refs, construction "
             "provenance, and a short explanation. It is **navigation, not law**: the cited sources "
             "(invariant / ADR / gate / codex / release / file) are authority; this index is not. Stable "
             "invariant IDs are unchanged; `construction_lane` (the build lane that introduced each invariant) "
             "is provenance, not semantic standing.")
    L.append("")
    L.append(f"Verified against: {doc['last_verified_release']} · {len(recs)} invariants · "
             f"{len(by_fam)} semantic families. For live constitutional facts use `ugk explain <id>`.")
    L.append("")
    # family index
    L.append("## Semantic families")
    L.append("")
    for fam in sorted(by_fam):
        L.append(f"- **{fam}** — {len(by_fam[fam])} invariants")
    L.append("")
    # entries grouped by family -> subsystem -> id
    for fam in sorted(by_fam):
        L.append(f"## {fam}")
        L.append("")
        rows = sorted(by_fam[fam], key=lambda r: (r["subsystem"], r["id"]))
        for r in rows:
            L.append(f"### {r['id']} — {r['public_label']}")
            L.append(f"*subsystem:* {r['subsystem']} · *classification:* {r['classification']} · "
                     f"*frame role:* {r['frame_role']} · *authority role:* {r['authority_role']}  ")
            if r.get("effect_class_scope"):
                L.append(f"*effect-class scope:* {', '.join(r['effect_class_scope'])}  ")
            L.append(f"*continuity:* {r['continuity_status']} · *last verified:* {r['last_verified_release']}  ")
            L.append("")
            L.append(r["explanation_summary"])
            L.append("")
            L.append(f"- **gate:** `{r['gate']}`")
            L.append(f"- **sources (authority):** " + ", ".join(f"`{s}`" for s in r["source_refs"]))
            L.append(f"- **provenance (build lane, not semantic standing):** `{r['construction_lane']}`")
            L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    out = ROOT / "INVARIANT_TAXONOMY.md"
    content = generate()
    if "--check" in sys.argv:
        cur = out.read_text(encoding="utf-8") if out.exists() else ""
        if cur != content:
            print("INVARIANT_TAXONOMY.md is stale — run: python invariant_taxonomy_gen.py")
            return 1
        print("INVARIANT_TAXONOMY.md is current.")
        return 0
    out.write_text(content, encoding="utf-8")
    print(f"INVARIANT_TAXONOMY.md written ({len(content.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
