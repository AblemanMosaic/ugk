"""ugk/conformance/dispatcher_gate.py — CGP evidence dispatcher conformance. GATE_GROUP = "integration"

Seven dispatcher properties, hardened:
  1 completeness     every in-scope cap -> exactly one verdict; every cap accounted
  2 no-silent-skip   no cap scored twice; scored ∪ out_of_scope == registry
  3 normalization    EvidenceArtifact only; VERDICTS aliases the EvidenceArtifact
                     vocabulary EXACTLY; evidence_class is str; registry_version
                     is content-sensitive (a changed binding changes it)
  4 scope-filtering  out-of-scope -> out_of_scope; selector-excluded -> NOT-RUN;
                     receipt-aggregation -> NOT-RUN (explicit deferral, not GAP)
  5 waiver-handling  waiver -> WAIVED w/ authority+reason; duplicate/unknown-cap/
                     malformed waivers fail closed; waiver order does not change hash
  6 determinism      stub AND real-runner dispatches reproduce ledger_hash; verify_hash
  7 anti-vacuity     empty scope/registry -> no PROVEN; malformed/unknown-class ->
                     explicit GAP/ERROR; always-ok runner proves only gate-resolved caps
"""


def run():
    import copy
    from ugk.cgp.dispatch import (
        dispatch_capability_evidence, DispatchScope, WaiverRecord, VERDICTS,
        verdict_vocabulary_matches_evidence_artifact, _registry_version,
    )
    from ugk.cgp.runner.types import EvidenceArtifact
    from ugk.cgp.esa.registry import REGISTRY

    fails = []
    stub = lambda n: (True, "stub")
    allkeys = set(REGISTRY.keys())
    keys_sorted = sorted(allkeys)
    one, two = keys_sorted[0], keys_sorted[1]

    def _cap(ev, gate):
        return {"class": "I", "realizations": {"UGK": {"path": "x", "status": "DONE",
                "deterministic": True, "gate": gate, "evidence_class": ev, "notes": ""}},
                "deterministic_layer": "", "notes": "", "interpretive_evidence_template": None}

    # 1 completeness
    led = dispatch_capability_evidence(registry=REGISTRY, scope=DispatchScope(scope_id="g"),
                                       selector="full", gate_runner=stub)
    scored = [a.invariant for a in led.artifacts]
    if set(scored) | set(led.out_of_scope) != allkeys:
        fails.append("1:completeness: not every cap accounted")
    if any(a.verdict not in VERDICTS for a in led.artifacts):
        fails.append("1:completeness: verdict outside vocabulary")

    # 2 no-silent-skip
    if len(scored) != len(set(scored)):
        fails.append("2:no-silent-skip: cap scored more than once")
    if set(scored) & set(led.out_of_scope):
        fails.append("2:no-silent-skip: cap both scored and out_of_scope")

    # 3 normalization + registry_version content sensitivity
    if not all(isinstance(a, EvidenceArtifact) for a in led.artifacts):
        fails.append("3:normalization: non-EvidenceArtifact present")
    if not verdict_vocabulary_matches_evidence_artifact():
        fails.append("3:normalization: VERDICTS does not alias EvidenceArtifact exactly")
    if any(not isinstance(a.evidence_class, str) for a in led.artifacts):
        fails.append("3:normalization: evidence_class not a str")
    mod = copy.deepcopy(REGISTRY)
    reals = mod[one].get("realizations")
    if isinstance(reals, dict) and reals:
        rk = sorted(reals)[0]
        reals[rk]["gate"] = "ZZ_changed_binding_gate"
    if not (set(mod) == allkeys and _registry_version(mod) != _registry_version(REGISTRY)):
        fails.append("3:normalization: registry_version insensitive to binding change")

    # 4 scope-filtering + receipt-aggregation deferral
    sub = dispatch_capability_evidence(registry=REGISTRY,
            scope=DispatchScope(scope_id="g", in_scope=frozenset({one})), selector="full", gate_runner=stub)
    if [a.invariant for a in sub.artifacts] != [one] or set(sub.out_of_scope) != (allkeys - {one}):
        fails.append("4:scope-filtering: in_scope subset not honored")
    cust = dispatch_capability_evidence(registry=REGISTRY,
            scope=DispatchScope(scope_id="g", custom_set=frozenset({one})), selector="custom", gate_runner=stub)
    nr = [a.invariant for a in cust.artifacts if a.verdict == "NOT-RUN"]
    if len(cust.artifacts) != len(allkeys) or one in nr or len(nr) != len(allkeys) - 1:
        fails.append("4:scope-filtering: custom selector NOT-RUN set wrong")
    ra = dispatch_capability_evidence(registry={"RA": _cap("receipt-aggregation", "agg")},
            scope=DispatchScope(scope_id="g"), selector="full", gate_runner=stub)
    if ra.artifacts[0].verdict != "NOT-RUN" or "deferred" not in ra.artifacts[0].details:
        fails.append("4:scope-filtering: receipt-aggregation not explicit NOT-RUN deferral")

    # 5 waiver-handling: WAIVED + fail-closed dup/unknown/malformed + order-independence
    wv = dispatch_capability_evidence(registry=REGISTRY,
            scope=DispatchScope(scope_id="g", waivers=(WaiverRecord(one, "Governor", "covered"),)),
            selector="full", gate_runner=stub)
    wmap = {a.invariant: a for a in wv.artifacts}
    if wmap[one].verdict != "WAIVED" or "Governor" not in wmap[one].details:
        fails.append("5:waiver-handling: waived cap not WAIVED with authority")
    if sum(1 for a in wv.artifacts if a.verdict == "WAIVED") != 1:
        fails.append("5:waiver-handling: a non-waived cap was WAIVED")
    for label, wvs in (("dup", (WaiverRecord(one, "G", "r"), WaiverRecord(one, "G", "r2"))),
                       ("unknown", (WaiverRecord("NOPE", "G", "r"),)),
                       ("malformed", (WaiverRecord(one, "", ""),))):
        try:
            dispatch_capability_evidence(registry=REGISTRY,
                scope=DispatchScope(scope_id="g", waivers=wvs), selector="full", gate_runner=stub)
            fails.append(f"5:waiver-handling: {label} waiver did not fail closed")
        except ValueError:
            pass
    wA = dispatch_capability_evidence(registry=REGISTRY, scope=DispatchScope(scope_id="g",
            waivers=(WaiverRecord(one, "G", "r"), WaiverRecord(two, "G", "r"))), selector="full", gate_runner=stub)
    wB = dispatch_capability_evidence(registry=REGISTRY, scope=DispatchScope(scope_id="g",
            waivers=(WaiverRecord(two, "G", "r"), WaiverRecord(one, "G", "r"))), selector="full", gate_runner=stub)
    if wA.ledger_hash != wB.ledger_hash:
        fails.append("5:waiver-handling: waiver order changed ledger_hash")

    # 6 determinism: stub AND real runner
    a1 = dispatch_capability_evidence(registry=REGISTRY, scope=DispatchScope(scope_id="g"), selector="full", gate_runner=stub)
    a2 = dispatch_capability_evidence(registry=REGISTRY, scope=DispatchScope(scope_id="g"), selector="full", gate_runner=stub)
    if a1.ledger_hash != a2.ledger_hash or not a1.verify_hash():
        fails.append("6:determinism: stub ledger_hash not reproducible")
    real = {"R": _cap("gate-suite", "zero_deps_gate")}
    r1 = dispatch_capability_evidence(registry=real, scope=DispatchScope(scope_id="g"), selector="full")
    r2 = dispatch_capability_evidence(registry=real, scope=DispatchScope(scope_id="g"), selector="full")
    if r1.ledger_hash != r2.ledger_hash:
        fails.append("6:determinism: REAL-runner ledger_hash drift")
    if r1.artifacts[0].verdict not in ("PROVEN", "FAIL"):
        fails.append("6:determinism: real gate did not yield a real outcome")

    # 7 anti-vacuity: empty scope/registry + malformed + always-ok proves only gate-resolved
    empty = dispatch_capability_evidence(registry=REGISTRY,
            scope=DispatchScope(scope_id="g", in_scope=frozenset()), selector="full", gate_runner=stub)
    if empty.artifacts or any(a.verdict == "PROVEN" for a in empty.artifacts):
        fails.append("7:anti-vacuity: empty scope produced artifacts/PROVEN")
    er = dispatch_capability_evidence(registry={}, scope=DispatchScope(scope_id="g"), selector="full")
    if er.artifacts:
        fails.append("7:anti-vacuity: empty registry produced artifacts")
    mal = {"M-INT": 7, "M-REAL": {"class": "I", "realizations": [1]},
           "M-NOEV": {"class": "I", "realizations": {"UGK": {"path": "x", "gate": "manual"}}},
           "M-UNK": _cap("weird", "manual")}
    lm = dispatch_capability_evidence(registry=mal, scope=DispatchScope(scope_id="g"),
                                      selector="full", gate_runner=stub)
    mv = {a.invariant: a.verdict for a in lm.artifacts}
    if mv.get("M-INT") != "ERROR" or mv.get("M-REAL") != "GAP" \
       or mv.get("M-NOEV") != "GAP" or mv.get("M-UNK") != "GAP":
        fails.append("7:anti-vacuity: malformed/unknown not explicit GAP/ERROR")
    if any(a.verdict == "PROVEN" for a in lm.artifacts):
        fails.append("7:anti-vacuity: malformed produced PROVEN")
    proven = [x for x in led.artifacts if x.verdict == "PROVEN"]
    nonproven = [x for x in led.artifacts if x.verdict in ("GAP", "NOT-RUN", "BY-CONSTRUCTION")]
    if not nonproven or len(proven) == len(led.artifacts):
        fails.append("7:anti-vacuity: always-ok runner PROVED non-resolved caps (vacuous)")

    ok = not fails
    if ok:
        c = led.verdict_counts()
        detail = ("7/7 checks pass (hardened); real registry stub-dist "
                  + ", ".join(f"{k}={c[k]}" for k in VERDICTS if c[k])
                  + f"; ledger_hash={led.ledger_hash[:12]}")
    else:
        detail = "; ".join(fails)
    return ok, detail


if __name__ == "__main__":
    ok, detail = run()
    print(f"dispatcher_gate: {'PASS' if ok else 'FAIL'}  {detail}")
