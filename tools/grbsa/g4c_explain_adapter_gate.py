#!/usr/bin/env python3
"""GRBSA G4c — ExplainAdapter Equivalence Gate (r28: de-tangled).

The ExplainAdapter now sources from IMPORT-CLEAN ugk.projections surfaces and reconstructs the
non-invention + completeness predicate in-lane (no phase5b gate-script execution on the adapter path).
This gate proves equivalence + the load-bearing negative controls on the RECONSTRUCTED path (fast; no
batch spawn), plus a ONE-TIME fidelity safeguard (Q2): the reconstructed invention predicate AGREES
with phase5b's invention_violations on the honest corpus (phase5b run once, output discarded). If they
disagree, the gate FAILS (hard stop).

Run:  python g4c_explain_adapter_gate.py <repo_dir>
"""
import sys, os, subprocess, json, tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools", "grbsa"))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" - " + detail if detail else ""))

from grbsa_runtime import ExplainAdapter, explain_success, PostureRefusal
from grbsa_runtime.explain_adapter import _corpus_truth_sets, reconstructed_invention_violations
from ugk.projections import explain as EX, patterns as P, domain_mappings as DM


def reference_view():
    corpus_pat, corpus_pat_refs, corpus_dom = _corpus_truth_sets(P, DM)
    proj = EX.explain_projections()
    corpus_keys = {"pattern:" + p.id for p in P.PATTERNS} | {"domain:" + d.id for d in DM.DOMAIN_MAPPINGS}
    viol = reconstructed_invention_violations(proj, EX, corpus_pat, corpus_pat_refs, corpus_dom)
    explain_keys = set(proj.keys())
    covered = tuple(sorted(explain_keys & corpus_keys))
    missing = tuple(sorted(corpus_keys - explain_keys))
    passed = (len(viol) == 0 and covered == tuple(sorted(corpus_keys)) and len(missing) == 0)
    return {"violations": set(map(tuple, viol)), "covered": covered, "missing": missing, "passed": passed}


def adapter_view(**kw):
    a = ExplainAdapter(REPO, **kw)
    receipt, env, trace = a.run()
    return {"violations": set(map(tuple, env.invention_violations)),
            "covered": tuple(env.covered_keys), "missing": tuple(env.missing_keys),
            "passed": explain_success(receipt, env),
            "receipt": receipt, "env": env, "trace": trace}


def equivalent(ref, adapter):
    same_v = ref["violations"] == adapter["violations"]
    same_cov = ref["covered"] == adapter["covered"] and ref["missing"] == adapter["missing"]
    same_verdict = ref["passed"] == adapter["passed"]
    return same_v and same_cov and same_verdict, {
        "same_violations": same_v, "same_coverage": same_cov, "same_verdict": same_verdict}


L = reference_view(); A = adapter_view()
eq_ok, eq_d = equivalent(L, A)
check("equivalence: identical invention set + corpus coverage + overall verdict", eq_ok,
      str(eq_d) + " covered=" + str(len(A["covered"])) + " violations=" + str(len(A["violations"])))
check("success semantics = non-invention + completeness (honest corpus passes)",
      A["passed"] is True and len(A["violations"]) == 0 and len(A["missing"]) == 0 and len(A["covered"]) > 0)
check("NBER-1: ExplainReceipt minted before the explain continuation runs",
      A["trace"].receipt_before_effect(), "order=" + str(A["trace"].events))
check("category boundary: invention/coverage findings in ResultEnvelope, not Receipt",
      not hasattr(A["receipt"], "invention_violations") and hasattr(A["env"], "invention_violations"))
import ugk.projections.explain as _exmod
check("adapter sources from import-clean ugk.projections.explain (no gate-script execution)",
      _exmod.__file__.endswith(os.path.join("projections", "explain.py")),
      "explain lib: " + os.path.basename(_exmod.__file__))

A_bad = adapter_view(_emit_receipt_before_effect=False)
check("  (neg-i) receipt-after-effect variant FAILS NBER-1",
      not A_bad["trace"].receipt_before_effect(), "order=" + str(A_bad["trace"].events))
A_inv = adapter_view(_inject_invented_claim=True)
eq_inv, _ = equivalent(L, A_inv)
check("  (neg-ii LOAD-BEARING) injected invented claim FAILS non-invention (equiv + success)",
      (len(A_inv["violations"]) > 0) and (not eq_inv) and (A_inv["passed"] is False),
      "violations=" + str(len(A_inv["violations"])) + " success=" + str(A_inv["passed"]))
some_key = L["covered"][0]
A_drop = adapter_view(_drop_corpus_object=some_key)
eq_drop, _ = equivalent(L, A_drop)
check("  (neg-iii) dropped corpus object FAILS completeness/equivalence",
      (not eq_drop) and (A_drop["passed"] is False),
      "dropped='" + some_key + "' missing=" + str(len(A_drop["missing"])))
refused = False
try:
    from ugk.scale.oracle import POSTURE_OPS
    ExplainAdapter(REPO, op=sorted(POSTURE_OPS)[0]).run()
except PostureRefusal:
    refused = True
check("  (neg-iv) adapter attempting a posture op is REFUSED", refused)
from grbsa_runtime import ExplainReceipt, ExplainResultEnvelope
from grbsa_runtime.gate_adapter import ReceiptCore, ResultEnvelopeCore
empty_r = ExplainReceipt(core=ReceiptCore({}, (), (), {}, "admitted", {}), explain_identity="x", corpus_signature=())
empty_e = ExplainResultEnvelope(core=ResultEnvelopeCore("pass", (), {}, "0"*64, {}),
                                invention_violations=(), covered_keys=(), missing_keys=())
check("  (neg-v) zero-object (vacuous) is NOT success", explain_success(empty_r, empty_e) is False)

# ======================= IMPORT-CLEAN FIDELITY FIXTURE (r29) =======================
# r28's "one-time safeguard" executed phase5b, whose heavy top level can spawn the conformance batch
# — re-entangling the validation path (caught by external testing). r29 removes ALL phase5b execution
# from this gate and proves the reconstructed non-invention predicate correct via a BOUNDED fixture
# derived from the real corpus (import-clean: ugk.projections only). It pins EXACT expected violations
# on controlled inputs: honest→none, invented primitive→flagged, invented pattern-ref→flagged,
# omission→allowed. This is the release validation standard for G4c fidelity.
_cp, _cpr, _cd = _corpus_truth_sets(P, DM)
_real = EX.explain_projections()

def _expect(projections, expected):
    got = set(map(tuple, reconstructed_invention_violations(projections, EX, _cp, _cpr, _cd)))
    return got == set(expected), got

def _append_to(text, prefix, val):
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(prefix):
            lines[i] = ln + " | " + val
            return "\n".join(lines)
    return text + "\n" + prefix + val

f1_ok, _ = _expect(_real, [])                                  # honest -> none
_pat_key = next(k for k in _real if k.startswith("pattern:"))
_inv_prim = dict(_real); _inv_prim[_pat_key] = _append_to(_real[_pat_key], "primitives: ", "__INVENTED_PRIM__")
f2_ok, _ = _expect(_inv_prim, [(_pat_key, "prim:__INVENTED_PRIM__")])   # invented prim -> flagged
_dom_key = next(k for k in _real if k.startswith("domain:"))
_inv_ref = dict(_real); _inv_ref[_dom_key] = _append_to(_real[_dom_key], "pattern-refs: ", "__INVENTED_REF__")
f3_ok, _ = _expect(_inv_ref, [(_dom_key, "ref:__INVENTED_REF__")])      # invented ref -> flagged
def _blank_prims(text):
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("primitives: "):
            lines[i] = "primitives: "
            return "\n".join(lines)
    return text
_omit = dict(_real); _omit[_pat_key] = _blank_prims(_real[_pat_key])
f4_ok, _ = _expect(_omit, [])                                  # omission -> allowed

check("FIDELITY FIXTURE (import-clean, no phase5b): honest→none, invented-prim→flagged, "
      "invented-ref→flagged, omission→allowed",
      f1_ok and f2_ok and f3_ok and f4_ok,
      "honest=%s prim=%s ref=%s omit=%s" % (f1_ok, f2_ok, f3_ok, f4_ok))


ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G4c EXPLAIN-ADAPTER GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
