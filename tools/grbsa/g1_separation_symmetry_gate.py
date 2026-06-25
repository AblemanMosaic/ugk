#!/usr/bin/env python3
"""GRBSA G1 — Receipt/Envelope-Separation + Symmetry Gate.

Asserts (a) result/outcome fields map to the Envelope core, never the Receipt; (b) the Envelope core
is closed and structurally symmetric with the Receipt (domain data only via extensions); (c) success
semantics lives in NEITHER core NOR either extension. Read-only; fails closed.

Run:  python g1_separation_symmetry_gate.py <repo_dir>
"""
import sys, os, json

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
HERE = os.path.dirname(os.path.abspath(__file__))
results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

man = json.load(open(os.path.join(HERE, "core_mapping.json")))

# result/outcome concepts that must NOT appear as Receipt-core sources (they belong to the envelope)
RESULT_TERMS = ("ScenarioResult", "BatchResult", "SweepResult", ".passed", ".timing_ms",
                ".stream_hash", ".receipt_delta", "final_stream_hash", "checkpoint_hash")
SUCCESS_TERMS = ("success", "verdict", "anti_vacuity", "anti-vacuity", "fidelity_ok",
                 "non_invention", "passed_predicate")

def all_sources(core_key):
    out = []
    for fld, entry in man[core_key]["fields"].items():
        for s in entry.get("sources", []):
            out.append((fld, s))
    return out

# (a) separation: no result-shape source leaks into the Receipt core
recv_sources = all_sources("receipt_core")
leaks = [(f, s) for (f, s) in recv_sources if any(t in s for t in RESULT_TERMS)]
check("separation: no result/outcome source in the Receipt core", not leaks,
      "leaks=" + str(leaks) if leaks else "receipt core carries only admissibility sources")

# (b) symmetry: envelope core closed (5 named fields), domain data only via extensions
env_fields = set(man["envelope_core"]["fields"].keys())
sym_ok = env_fields == {"status", "evidence_refs", "timing", "result_hash", "lineage"}
seam = man.get("extension_seam", {})
has_both_seams = bool(seam.get("receipt_extensions")) and bool(seam.get("envelope_extensions"))
check("symmetry: Envelope core closed + both extension seams declared", sym_ok and has_both_seams,
      "env_fields=%s seams=%s" % (sorted(env_fields), has_both_seams))

# (c) success semantics in NEITHER core NOR either extension (it is a predicate, not a field)
def field_names(core_key):
    return set(man[core_key]["fields"].keys())
no_success_field = True
for core in ("receipt_core", "envelope_core"):
    for f in field_names(core):
        if any(t in f.lower() for t in SUCCESS_TERMS):
            no_success_field = False
# success_semantics must be declared as a RULE (predicate over receipt+envelope), not a field
ss = man.get("success_semantics", {})
declared_as_predicate = "predicate" in ss.get("rule", "").lower() and "not" in ss.get("rule", "").lower()
check("success semantics is a predicate, in neither core nor extension", no_success_field and declared_as_predicate,
      "rule=" + (ss.get("rule", "")[:60] + "…" if ss.get("rule") else "MISSING"))

# ---- negative controls (same checkers, malformed fixtures) ----
bad_leak = {"receipt_core": {"fields": dict(man["receipt_core"]["fields"],
            outcome={"sources": ["ugk.testing.headless_runner.ScenarioResult.passed"]})}}
leak2 = [(f, s) for f, e in bad_leak["receipt_core"]["fields"].items() for s in e.get("sources", [])
         if any(t in s for t in RESULT_TERMS)]
check("  (neg) result source injected into receipt core is detected", len(leak2) > 0)

bad_succ_field = {"receipt_core": {"fields": dict(man["receipt_core"]["fields"], success_verdict={"sources": []})}}
caught_succ = any(any(t in f.lower() for t in SUCCESS_TERMS) for f in bad_succ_field["receipt_core"]["fields"])
check("  (neg) success-verdict field in a core is detected", caught_succ)

bad_env_extra = set(man["envelope_core"]["fields"].keys()) | {"domain_payload"}
check("  (neg) extra (domain) field in the Envelope core breaks closure", bad_env_extra != {"status", "evidence_refs", "timing", "result_hash", "lineage"})

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G1 SEPARATION+SYMMETRY GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
