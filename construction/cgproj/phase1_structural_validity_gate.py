"""Phase 1 Structural Validity Gate — CGProj inert metadata objects.
Each check exercises the real condition; vacuity-prone checks carry negative controls.
"""
import sys, dataclasses

ROOT = sys.argv[1]
sys.path.insert(0, ROOT)

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    tag = "PASS" if ok else "FAIL"
    line = "  " + tag + "  " + name
    if detail:
        line += " — " + detail
    print(line)

# ---- 1. Objects construct ----
from ugk.projections.types import BoundaryStatement, IntegrationSeam, GovernancePattern, DomainMapping
from ugk.projections.patterns import PATTERNS, PATTERNS_BY_ID
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS, DOMAIN_MAPPINGS_BY_ID
check("objects construct (expect 7 patterns, 5 domains)",
      len(PATTERNS) == 7 and len(DOMAIN_MAPPINGS) == 5,
      str(len(PATTERNS)) + " patterns, " + str(len(DOMAIN_MAPPINGS)) + " domains")

# ---- 2. Objects are frozen (mutation raises) — with negative control ----
froze = []
for cls, inst, field_try in [
        ("GovernancePattern", PATTERNS[0], "id"),
        ("DomainMapping", DOMAIN_MAPPINGS[0], "id"),
        ("IntegrationSeam", PATTERNS[0].seams[0], "summary"),
        ("BoundaryStatement", PATTERNS[0].boundaries[0], "text")]:
    try:
        setattr(inst, field_try, "MUTATED")
        froze.append((cls, False))
    except dataclasses.FrozenInstanceError:
        froze.append((cls, True))
all_frozen = all(f for _, f in froze)
check("objects are frozen (mutation raises FrozenInstanceError)", all_frozen, str(froze))

@dataclasses.dataclass
class _NotFrozen:
    x: int = 0
nf = _NotFrozen()
try:
    nf.x = 1
    neg_ok = True
except dataclasses.FrozenInstanceError:
    neg_ok = False
check("  (neg-control) a non-frozen object IS mutable (frozen-test has teeth)", neg_ok)

# ---- 3. Domain mappings reference patterns UPWARD only; pattern IDs resolve ----
unresolved = []
for d in DOMAIN_MAPPINGS:
    for pid in d.patterns:
        if pid not in PATTERNS_BY_ID:
            unresolved.append((d.id, pid))
total_refs = sum(len(d.patterns) for d in DOMAIN_MAPPINGS)
check("pattern IDs referenced by domains all resolve", len(unresolved) == 0,
      ("unresolved: " + str(unresolved)) if unresolved else ("all " + str(total_refs) + " refs resolve"))
check("  (neg-control) a bogus pattern id does NOT resolve", "no-such-pattern" not in PATTERNS_BY_ID)

# ---- 4. Patterns do NOT reference domains (hierarchy upward only) ----
domain_ids = set(DOMAIN_MAPPINGS_BY_ID)
leak = []
for p in PATTERNS:
    for f in dataclasses.fields(p):
        v = getattr(p, f.name)
        vals = v if isinstance(v, tuple) else (v,)
        for item in vals:
            if isinstance(item, str) and item in domain_ids:
                leak.append((p.id, f.name, item))
check("patterns do not reference any domain id (no downward ref)", len(leak) == 0,
      ("leak: " + str(leak)) if leak else "no pattern field contains a domain id")

# ---- 5. Boundary statements present ----
dom_b = all(isinstance(d.boundary, BoundaryStatement) and d.boundary.text.strip() for d in DOMAIN_MAPPINGS)
pat_b = all(len(p.boundaries) >= 1 and all(b.text.strip() for b in p.boundaries) for p in PATTERNS)
check("boundary statements present (every domain non-empty; every pattern >=1)", dom_b and pat_b,
      "domains_ok=" + str(dom_b) + " patterns_ok=" + str(pat_b))

# ---- 6. Primitive references are STRING LABELS only ----
notstr = []
for p in PATTERNS:
    for s in (p.primitives + tuple(x for seam in p.seams for x in seam.ugk_primitives)):
        if not isinstance(s, str):
            notstr.append((p.id, repr(s)))
for d in DOMAIN_MAPPINGS:
    for seam in d.integration_points:
        for s in seam.ugk_primitives:
            if not isinstance(s, str):
                notstr.append((d.id, repr(s)))
check("primitive references are string labels only (no imports/objects)", len(notstr) == 0,
      ("non-string: " + str(notstr)) if notstr else "all primitive refs are str")

ok = all(r[1] for r in results)
print("\n  PHASE 1 STRUCTURAL VALIDITY GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
