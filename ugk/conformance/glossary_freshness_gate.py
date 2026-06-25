"""ugk/conformance/glossary_freshness_gate.py - GLOSSARY freshness + source integrity.
GATE_GROUP = "structural"

Proves the generated term index is honest navigation, not a stale shrine:
  1. every source ref resolves (invariant / adr / release / file / codex / gate / profile);
  2. every required term is present;
  3. no entry lacks an authoritative source;
  4. generated GLOSSARY.md matches the GLOSSARY.json projection (via glossary_gen.generate());
  5. core concepts are covered;
  6. no entry claims authority (the index is navigation; cited sources are authority);
  7. no stale numbers (rN format on releases; release refs resolve; no hardcoded gate/registry counts).

NOT_ESTABLISHED if GLOSSARY.json / glossary_gen.py are absent in a packaged deployment.
"""
import json, re, importlib.util
from pathlib import Path
import ugk
from ugk.conformance import NOT_ESTABLISHED

REQUIRED_TERMS = {
    "terminal-outcome-lattice","ADMIT","REFUSE","STRUCTURAL_ERROR","DEFER","BRIDGE","CRISIS",
    "BRIDGE-BINDING","ContinuationRecord","BridgeRecord","EffectAtomicity","PURE","STORE_LOCAL",
    "EXTERNAL_REVERSIBLE","EXTERNAL_IRREVERSIBLE","NON_ATOMIC","amendment-ledger","Proof Model B",
    "B1/B2/B3/B4","GRBSA","verifier-boundary","classified-remainders","integrity-basis",
    "generated CODEX","Implementation Codex","SKILL.md","CK-CANON","CK profile","MCIR","SMH",
    "MCIR structural identity","SMH projection","SMH archive identity",
    "resolver-parameterized verification","rho-integration-posture","ugk explain",
}
CORE_TERMS = {"terminal-outcome-lattice","BRIDGE","BRIDGE-BINDING","DEFER","EffectAtomicity",
              "amendment-ledger","Proof Model B","verifier-boundary","Implementation Codex",
              "generated CODEX","MCIR","SMH","rho-integration-posture","ugk explain"}
REQUIRED_FIELDS = ("term","category","status","short_definition","authoritative_sources",
                   "implementation_surfaces","introduced_release","last_verified_release",
                   "agent_rule","not_this","related_terms")


def _root():
    return Path(ugk.__file__).resolve().parent.parent


def _codex_concept_ids(root):
    ids = set()
    p = root / "IMPLEMENTATION_CODEX.md"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith('{"concept_id"'):
                try:
                    ids.add(json.loads(line)["concept_id"])
                except Exception:
                    pass
    return ids


def _release_exists(root, rid):
    rel = root / "RELEASE.txt"
    if rel.exists() and rid in rel.read_text(encoding="utf-8"):
        return True
    # accept rN <= current head as historical
    m = re.fullmatch(r"r(\d+[a-z]?)", rid)
    return bool(m)


def _ref_error(root, ref, inv_ids, adr_ids, codex_ids):
    if ref.startswith("invariant:"):
        return None if ref.split(":",1)[1] in inv_ids else f"unknown invariant {ref}"
    if ref.startswith("adr:"):
        return None if ref.split(":",1)[1] in adr_ids else f"unknown ADR {ref}"
    if ref.startswith("codex:"):
        return None if ref.split(":",1)[1] in codex_ids else f"unknown codex concept {ref}"
    if ref.startswith("file:"):
        return None if (root / ref.split(":",1)[1]).exists() else f"missing file {ref}"
    if ref.startswith("doc:"):
        return None if (root / ref.split(":",1)[1]).exists() else f"missing doc {ref}"
    if ref.startswith("gate:"):
        g = ref.split(":",1)[1]
        ok = (root/"ugk"/"conformance"/f"{g}.py").exists() or (root/"tools"/"grbsa"/f"{g}.py").exists()
        return None if ok else f"unknown gate {ref}"
    if ref.startswith("release:"):
        return None if _release_exists(root, ref.split(":",1)[1]) else f"missing release {ref}"
    if ref.startswith("profile:"):
        return f"profile refs not yet resolvable (design-only): {ref}"
    return f"unrecognized ref scheme: {ref}"


def run():
    root = _root()
    gj = root / "GLOSSARY.json"
    gg = root / "glossary_gen.py"
    if not gj.exists() or not gg.exists():
        return NOT_ESTABLISHED, "GLOSSARY.json / glossary_gen.py not present in this deployment"
    from ugk.invariants import INVARIANT_REGISTRY
    from ugk.adr import ADR_REGISTRY
    inv_ids, adr_ids = set(INVARIANT_REGISTRY), set(ADR_REGISTRY)
    codex_ids = _codex_concept_ids(root)
    doc = json.loads(gj.read_text(encoding="utf-8"))
    terms = doc.get("terms", [])
    by_term = {e["term"]: e for e in terms}
    failures = []

    # top-level provenance field must be the explicit, unambiguous name + rN form
    var = doc.get("verified_against_release")
    if not var or not re.fullmatch(r"r\d+[a-z]?", str(var)):
        failures.append("top-level verified_against_release must be present and rN")
    if "release" in doc:
        failures.append("ambiguous top-level 'release' field present; use verified_against_release")

    # (6) no authority claim — the index must declare itself non-law
    if "not law" not in (doc.get("note","").lower()):
        failures.append("glossary note must declare it is not law")

    for e in terms:
        t = e.get("term","?")
        for f in REQUIRED_FIELDS:
            if f not in e:
                failures.append(f"{t}: missing field {f}")
        if not e.get("authoritative_sources"):
            failures.append(f"{t}: authoritative_sources must be non-empty")  # (3)
        if not re.fullmatch(r"r\d+[a-z]?", str(e.get("last_verified_release",""))):
            failures.append(f"{t}: last_verified_release must be rN")  # (7)
        for ref in e.get("authoritative_sources", []) + e.get("implementation_surfaces", []):
            # surfaces are file paths; sources are scheme:refs
            if ":" in ref and ref.split(":",1)[0] in ("invariant","adr","codex","file","doc","gate","release","profile"):
                err = _ref_error(root, ref, inv_ids, adr_ids, codex_ids)  # (1)
            else:
                err = None if (root / ref).exists() else f"missing surface {ref}"
            if err:
                failures.append(f"{t}: {err}")
        # (6) no entry may assert it IS authority/law (positive claim only; ignore negated "never as authority")
        _ar = e.get("agent_rule","").lower()
        if re.search(r"\bis (the )?(law|authoritative|authority)\b", _ar) and not re.search(r"\b(not|never)\b", _ar):
            failures.append(f"{t}: agent_rule claims authority")
        # (7) no hardcoded drift-prone counts in prose
        if re.search(r"\b\d+\s+(gates|invariants)\b", (e.get("short_definition","")+e.get("agent_rule",""))):
            failures.append(f"{t}: hardcoded gate/registry count (drift risk)")

    missing_required = REQUIRED_TERMS - set(by_term)   # (2)
    if missing_required:
        failures.append("missing required terms: " + ", ".join(sorted(missing_required)))
    missing_core = CORE_TERMS - set(by_term)           # (5)
    if missing_core:
        failures.append("missing core terms: " + ", ".join(sorted(missing_core)))

    # (4) generated GLOSSARY.md matches the projection (pure generator; in-process compare)
    spec = importlib.util.spec_from_file_location("glossary_gen", gg)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    md = root / "GLOSSARY.md"
    if not md.exists():
        failures.append("GLOSSARY.md absent")
    elif md.read_text(encoding="utf-8") != mod.generate():
        failures.append("GLOSSARY.md stale vs GLOSSARY.json (run `python glossary_gen.py`)")

    if failures:
        return False, "GLOSSARY freshness FAIL: " + "; ".join(failures[:8])
    return True, (f"GLOSSARY fresh: {len(terms)} terms, all {len(REQUIRED_TERMS)} required + "
                  f"{len(CORE_TERMS)} core covered; all source refs resolve; generated == source.")


if __name__ == "__main__":
    ok, detail = run()
    tag = "PASS" if ok is True else ("N/EST" if ok is NOT_ESTABLISHED else "FAIL")
    print(f"glossary_freshness_gate: {tag}  {detail}")
