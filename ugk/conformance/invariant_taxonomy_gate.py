"""ugk/conformance/invariant_taxonomy_gate.py - INVARIANT_TAXONOMY freshness + source integrity.
GATE_GROUP = "structural"

Proves the generated invariant-taxonomy navigation layer is honest and source-bounded:
  1. JSON parses;                              7. no record claims law authority;
  2. generated markdown matches JSON;          8. last_verified_release within 2 releases of head;
  3. every live invariant represented once;    9. classification + gate match the live registry;
  4. no unknown invariant IDs present;        10. construction_lane matches introduced_in;
  5. every source ref resolves;               11. no IEL-A..E records exist;
  6. every record has required fields;        12. DKN-S-01 and CHARTER-S-01 not marked design-only.

NOT_ESTABLISHED if INVARIANT_TAXONOMY.json / invariant_taxonomy_gen.py are absent in a deployment.
The taxonomy is navigation; the cited invariant/ADR/gate/codex/release/file sources are authority.
"""
import json, re, importlib.util
from pathlib import Path
import ugk
from ugk.conformance import NOT_ESTABLISHED

REQUIRED_FIELDS = ("id","public_label","semantic_family","subsystem","classification","frame_role",
                   "authority_role","gate","effect_class_scope","continuity_status","construction_lane",
                   "source_refs","last_verified_release","explanation_summary")
FORBIDDEN_IDS = {"IEL-A","IEL-B","IEL-C","IEL-D","IEL-E"}
LIVE_LAW_BACKED = ("DKN-S-01","CHARTER-S-01")


def _root():
    return Path(ugk.__file__).resolve().parent.parent


def _head_release(root):
    m = re.search(r"\brelease:\s+r(\d+)\b", (root / "RELEASE.txt").read_text(encoding="utf-8", errors="replace"))
    return int(m.group(1)) if m else None


def _codex_concept_ids(root):
    ids = set()
    p = root / "IMPLEMENTATION_CODEX.md"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith('{"concept_id"'):
                try: ids.add(json.loads(s)["concept_id"])
                except Exception: pass
    return ids


def _ref_error(root, ref, inv_ids, adr_ids, codex_ids):
    scheme, _, val = ref.partition(":")
    if scheme == "invariant": return None if val in inv_ids else f"unknown invariant {ref}"
    if scheme == "adr":       return None if val in adr_ids else f"unknown ADR {ref}"
    if scheme == "codex":     return None if val in codex_ids else f"unknown codex concept {ref}"
    if scheme in ("file","doc"): return None if (root / val).exists() else f"missing path {ref}"
    if scheme == "gate":
        ok = (root/"ugk"/"conformance"/f"{val}.py").exists() or (root/"tools"/"grbsa"/f"{val}.py").exists()
        return None if ok else f"unknown gate {ref}"
    if scheme == "release":   return None if re.fullmatch(r"r\d+[a-z]?", val) else f"bad release {ref}"
    return f"unrecognized/forbidden ref scheme: {ref}"


def run():
    root = _root()
    tj = root / "INVARIANT_TAXONOMY.json"
    tg = root / "invariant_taxonomy_gen.py"
    if not tj.exists() or not tg.exists():
        return NOT_ESTABLISHED, "INVARIANT_TAXONOMY.json / invariant_taxonomy_gen.py not present"
    from ugk.invariants import INVARIANT_REGISTRY
    from ugk.adr import ADR_REGISTRY
    inv_ids, adr_ids = set(INVARIANT_REGISTRY), set(ADR_REGISTRY)
    codex_ids = _codex_concept_ids(root)
    try:
        doc = json.loads(tj.read_text(encoding="utf-8"))   # (1)
    except Exception as e:
        return False, f"INVARIANT_TAXONOMY.json does not parse: {e}"
    recs = doc.get("records", [])
    f = []

    # (7) no authority claim at the doc level
    if "not law" not in (doc.get("standing","").lower()):
        f.append("taxonomy standing must declare it is not law")

    seen = {}
    for r in recs:
        cid = r.get("id","?")
        for fld in REQUIRED_FIELDS:                                    # (6)
            if fld not in r: f.append(f"{cid}: missing field {fld}")
        if cid in seen: f.append(f"{cid}: duplicate record")          # (3 dup)
        seen[cid] = True
        if cid in FORBIDDEN_IDS: f.append(f"{cid}: forbidden non-UGK id present")   # (11)
        if cid not in inv_ids: f.append(f"{cid}: unknown invariant id (not in registry)")  # (4)
        else:
            live = INVARIANT_REGISTRY[cid]
            if r.get("classification") != live.classification:        # (9)
                f.append(f"{cid}: classification {r.get('classification')!r} != registry {live.classification!r}")
            if r.get("gate") != live.gate:                            # (9)
                f.append(f"{cid}: gate {r.get('gate')!r} != registry {live.gate!r}")
            if r.get("construction_lane") != live.introduced_in:      # (10)
                f.append(f"{cid}: construction_lane {r.get('construction_lane')!r} != introduced_in {live.introduced_in!r}")
        if not r.get("source_refs"): f.append(f"{cid}: source_refs must be non-empty")  # (5)
        for ref in r.get("source_refs", []):
            err = _ref_error(root, ref, inv_ids, adr_ids, codex_ids)  # (5)
            if err: f.append(f"{cid}: {err}")
        if not re.fullmatch(r"r\d+", str(r.get("last_verified_release",""))):
            f.append(f"{cid}: last_verified_release must be rN")
        if re.search(r"\bis (the )?(law|authoritative|authority)\b", str(r.get("explanation_summary","")).lower()):
            f.append(f"{cid}: explanation_summary claims authority")   # (7)
        if cid in LIVE_LAW_BACKED:                                    # (12)
            if r.get("continuity_status") == "design-only" or r.get("frame_role") == "design-profile":
                f.append(f"{cid}: must be live law-backed, not design-only")

    # (3) exact-once coverage of all live invariants
    missing = inv_ids - set(seen)
    if missing: f.append("invariants not represented: " + ", ".join(sorted(missing)[:8]))
    if len(recs) != len(inv_ids): f.append(f"record count {len(recs)} != live invariants {len(inv_ids)}")

    # (8) staleness within 2 releases of head
    head = _head_release(root)
    if head is not None:
        for r in recs:
            m = re.fullmatch(r"r(\d+)", str(r.get("last_verified_release","")))
            if m and head - int(m.group(1)) > 2:
                f.append(f"{r.get('id')}: last_verified_release {r.get('last_verified_release')} > 2 releases behind r{head}")
                break

    # (2) generated markdown matches JSON (pure generator; in-process)
    spec = importlib.util.spec_from_file_location("invariant_taxonomy_gen", tg)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    md = root / "INVARIANT_TAXONOMY.md"
    if not md.exists():
        f.append("INVARIANT_TAXONOMY.md absent")
    elif md.read_text(encoding="utf-8") != mod.generate():
        f.append("INVARIANT_TAXONOMY.md stale vs JSON (run `python invariant_taxonomy_gen.py`)")

    if f:
        return False, "invariant taxonomy FAIL: " + "; ".join(f[:8]) + (f"; +{len(f)-8} more" if len(f) > 8 else "")
    return True, (f"invariant taxonomy fresh: {len(recs)} invariants represented exactly once across "
                  f"{len({r['semantic_family'] for r in recs})} families; classification/gate/construction_lane "
                  f"match registry; all source refs resolve; generated == source; DKN-S-01/CHARTER-S-01 live; no IEL-A..E.")


if __name__ == "__main__":
    ok, detail = run()
    tag = "PASS" if ok is True else ("N/EST" if ok is NOT_ESTABLISHED else "FAIL")
    print(f"invariant_taxonomy_gate: {tag}  {detail}")
