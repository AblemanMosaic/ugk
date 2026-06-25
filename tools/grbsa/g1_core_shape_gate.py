#!/usr/bin/env python3
"""GRBSA G1 — Core-Shape Gate.

Verifies the Receipt Core (6 fields) and ResultEnvelope Core (5 fields) are faithful projections over
EXISTING fields named in core_mapping.json, that every named source field actually exists in the
current tree (verified by inspecting real classes, not prose), and that G1 introduced NO second
receipt/envelope runtime object. Read-only; fails closed.

Run:  python g1_core_shape_gate.py <repo_dir>
"""
import sys, os, json, importlib, dataclasses as dc

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
HERE = os.path.dirname(os.path.abspath(__file__))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

RECEIPT_CORE_FIELDS = {"proposal", "criteria", "evaluation", "authority", "outcome", "lineage"}
ENVELOPE_CORE_FIELDS = {"status", "evidence_refs", "timing", "result_hash", "lineage"}

def load_manifest(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def source_exists(dotted):
    """dotted = 'pkg.mod.Class.field' — verify Class exists and has dataclass field `field`."""
    mod_class, field = dotted.rsplit(".", 1)
    mod, cls = mod_class.rsplit(".", 1)
    try:
        m = importlib.import_module(mod)
        c = getattr(m, cls)
    except Exception:
        return False
    if dc.is_dataclass(c):
        return field in {f.name for f in dc.fields(c)}
    # non-dataclass: accept attribute/annotation presence
    return field in getattr(c, "__annotations__", {}) or hasattr(c, field)

def verify_core(manifest, core_key, expected_fields):
    spec = manifest[core_key]["fields"]
    shape_ok = set(spec.keys()) == expected_fields
    missing_sources = []
    for fld, entry in spec.items():
        srcs = entry.get("sources", [])
        if not srcs:
            missing_sources.append((fld, "NO SOURCES"))
        for s in srcs:
            if not source_exists(s):
                missing_sources.append((fld, s))
    return shape_ok, missing_sources

# ---- real-tree verification ----
MANIFEST = os.path.join(HERE, "core_mapping.json")
man = load_manifest(MANIFEST)

r_shape, r_missing = verify_core(man, "receipt_core", RECEIPT_CORE_FIELDS)
check("Receipt Core has exactly its 6 fields", r_shape,
      "fields=" + str(sorted(man["receipt_core"]["fields"].keys())))
check("Receipt Core: every mapped source field exists in the tree", not r_missing,
      "unmapped=" + str(r_missing) if r_missing else "all sources verified present")

e_shape, e_missing = verify_core(man, "envelope_core", ENVELOPE_CORE_FIELDS)
check("ResultEnvelope Core has exactly its 5 fields", e_shape,
      "fields=" + str(sorted(man["envelope_core"]["fields"].keys())))
check("ResultEnvelope Core: every mapped source field exists in the tree", not e_missing,
      "unmapped=" + str(e_missing) if e_missing else "all sources verified present")

# ---- no second receipt/envelope implementation introduced by G1 ----
# G1 adds only tools/grbsa/* (+ provenance). Assert no new receipt/envelope CLASS was added under ugk/.
grbsa_only = True
for dp, dns, fs in os.walk(os.path.join(REPO, "ugk")):
    for f in fs:
        if not f.endswith(".py"):
            continue
        src = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        if "class ReceiptCore" in src or "class ResultEnvelopeCore" in src:
            grbsa_only = False
check("G1 introduced no second receipt/envelope runtime object under ugk/", grbsa_only,
      "no ReceiptCore/ResultEnvelopeCore class in ugk/")

# ---- negative controls (same checker, malformed fixtures) ----
bad1 = {"receipt_core": {"fields": dict(man["receipt_core"]["fields"], EXTRA={"sources": ["x.y.Z.q"]})}}
n1_shape, _ = verify_core(bad1, "receipt_core", RECEIPT_CORE_FIELDS)
check("  (neg) extra core field is rejected", not n1_shape)

bad2 = {"receipt_core": {"fields": {**man["receipt_core"]["fields"]}}}
bad2["receipt_core"]["fields"]["proposal"] = {"sources": ["ugk.storage.store.Receipt.DOES_NOT_EXIST"]}
_, n2_missing = verify_core(bad2, "receipt_core", RECEIPT_CORE_FIELDS)
check("  (neg) a source field that does not exist is rejected", len(n2_missing) > 0,
      "caught=" + str(n2_missing))

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G1 CORE-SHAPE GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
