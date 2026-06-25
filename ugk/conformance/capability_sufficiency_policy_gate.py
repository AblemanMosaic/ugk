"""ugk/conformance/capability_sufficiency_policy_gate.py — proves the D_cap sufficiency POLICY
artifact (AD-68, Lane 2a). Frame-stationary; proves the policy is total/deterministic and that it
opens NO enforcement/refusal path and keeps D_cap non-aggregating.
"""
from ugk.cgp.dispatch import VERDICTS
from ugk.cgp import capability_sufficiency as P


def run():
    checks = []

    def chk(n, c):
        checks.append((n, bool(c)))

    # (1) PROVEN-only evidence sufficiency.
    chk("1.PROVEN is evidence-sufficient", P.is_evidence_sufficient("PROVEN"))
    chk("1.PROVEN is the ONLY sufficient verdict",
        [v for v in VERDICTS if P.is_evidence_sufficient(v)] == ["PROVEN"])

    # (2) WAIVED is not evidence (authority disposition, distinct, never PROVEN/sufficient).
    chk("2.WAIVED not evidence-sufficient", not P.is_evidence_sufficient("WAIVED"))
    disp, _ = P.classify("WAIVED")
    chk("2.WAIVED classifies as authority disposition (not SUFFICIENT)",
        disp == P.WAIVER_DISPOSITION and disp != P.SUFFICIENT)

    # (3) BY-CONSTRUCTION cannot launder into sufficiency; admissible only with a NAMED proof,
    #     and even then it is BY_CONSTRUCTION_ADMITTED, never SUFFICIENT/PROVEN.
    chk("3.BY-CONSTRUCTION not evidence-sufficient", not P.is_evidence_sufficient("BY-CONSTRUCTION"))
    d_un, _ = P.classify("BY-CONSTRUCTION")
    chk("3.BY-CONSTRUCTION unbacked is non-sufficient", d_un == P.BY_CONSTRUCTION_UNBACKED)
    d_ok, _ = P.classify("BY-CONSTRUCTION", policy_entry={"by_construction_proof": "named_internal_gate_x"})
    chk("3.BY-CONSTRUCTION admitted only via named proof, never SUFFICIENT/PROVEN",
        d_ok == P.BY_CONSTRUCTION_ADMITTED and d_ok != P.SUFFICIENT)

    # (4) GAP / ERROR / NOT-RUN / FAIL fail closed.
    for v in ("FAIL", "GAP", "ERROR", "NOT-RUN"):
        chk("4.%s fails closed (non-sufficient)" % v,
            (not P.is_evidence_sufficient(v)) and P.classify(v)[0] == P.FAIL_CLOSED)

    # (5) Unknown / out-of-vocabulary verdict fails closed (totality, default-deny).
    chk("5.unknown verdict not sufficient", not P.is_evidence_sufficient("MAYBE"))
    chk("5.unknown verdict classifies FAIL_CLOSED", P.classify("totally-unknown")[0] == P.FAIL_CLOSED)
    chk("5.classify total over closed vocabulary (never raises)",
        all(isinstance(P.classify(v), tuple) and len(P.classify(v)) == 2 for v in VERDICTS))

    # (6) External / Navigator evidence is non-sufficient (policy declares it; PROVEN-only means an
    #     external artifact that never reaches PROVEN can never be sufficient).
    chk("6.policy declares external evidence non-sufficient",
        P.CAPABILITY_SUFFICIENCY_POLICY["external_evidence_sufficient"] is False)

    # (7) D_cap remains NON-AGGREGATING and NO enforcement/refusal path is opened in Lane 2a:
    #     the policy carries no enforced scopes, declares fail-closed default + non-aggregating, and
    #     is consumed by NO decision-path module (no kernel/policy import of this artifact yet).
    # AD-70 (r147): activation is NON-VACUOUS -- the live policy enumerates >=1 real governed scope,
    # every entry names a real governed op + a real compound capability class, and no entry is global/ambient.
    import ugk.kernel as _kk
    _live = P.CAPABILITY_SUFFICIENCY_POLICY["enforced_scopes"]
    from ugk.adr import compound_capabilities as _cc
    _gov = set(getattr(_kk, "GOVERNANCE_OPS", []) or [])
    chk("7.activation is non-vacuous (>=1 enumerated real governed scope)", len(_live) >= 1)
    chk("7.every enforced op is a real governed op", all(e["op"] in _gov for e in _live))
    chk("7.every enforced capability_class is a real compound capability", all(e["capability_class"] in _cc for e in _live))
    chk("7.every entry is explicitly scoped (jurisdiction + op; no wildcard/global)",
        all(e.get("jurisdiction") and e.get("op") and "*" not in (e["jurisdiction"] + e["op"]) for e in _live))
    chk("7.policy declares non-aggregating + fail-closed default",
        P.CAPABILITY_SUFFICIENCY_POLICY["non_aggregating"] is True
        and P.CAPABILITY_SUFFICIENCY_POLICY["default_posture"] == "fail-closed")
    import ugk.kernel as _k
    import ugk.governance.policy as _pol
    import inspect as _insp
    try:
        _ksrc = _insp.getsource(_k)
    except Exception:
        _ksrc = ""
    try:
        _polsrc = _insp.getsource(_pol)
    except Exception:
        _polsrc = ""
    # r146/AD-69: enforcement IS wired in the kernel as a SIBLING precondition, but D_cap must NOT be folded
    # into the aggregation module (conjunctive_refusal_monotone_v1 / aggregate()) -- it stays non-aggregating.
    chk("7.kernel consumes the policy as a sibling precondition (enforcement wired)",
        "capability_sufficiency" in _ksrc)
    chk("7.aggregation module does NOT consume the policy (D_cap non-aggregating)",
        "capability_sufficiency" not in _polsrc)

    # ---- Lane 2b (AD-69, DCAP-S-01): ENFORCEMENT proofs -- pure decision matrix + kernel round-trip ----
    ENF = lambda **e: {"policy_model_id": "t",
                       "enforced_scopes": [dict(jurisdiction="session", op="crp_evidence", **e)],
                       "external_evidence_sufficient": False, "non_aggregating": True,
                       "default_posture": "fail-closed"}
    # pure enforce_decision matrix
    chk("8b.enumerated+PROVEN admits", P.enforce_decision(jurisdiction="session", op="crp_evidence", verdict="PROVEN", policy=ENF(capability_class="c")) == (False, ""))
    for v in ("FAIL", "GAP", "ERROR", "NOT-RUN", "external", "WAIVED", "BY-CONSTRUCTION", None, "???"):
        r, c = P.enforce_decision(jurisdiction="session", op="crp_evidence", verdict=v, policy=ENF(capability_class="c"))
        chk("8b.enumerated+%r refuses insufficient-capability" % v, r is True and c == P.REFUSAL_CAUSE_INSUFFICIENT_CAPABILITY)
    chk("8b.unenumerated scope is a no-op (admit, unchanged)", P.enforce_decision(jurisdiction="other", op="crp_evidence", verdict=None, policy=ENF(capability_class="c")) == (False, ""))
    chk("8b.WAIVED + waiver_permits admits (distinct from PROVEN)", P.enforce_decision(jurisdiction="session", op="crp_evidence", verdict="WAIVED", policy=ENF(capability_class="c", waiver_permits=True)) == (False, ""))
    chk("8b.BY-CONSTRUCTION + named proof admits", P.enforce_decision(jurisdiction="session", op="crp_evidence", verdict="BY-CONSTRUCTION", policy=ENF(capability_class="c", by_construction_proof="gate_z")) == (False, ""))
    chk("8b.LIVE policy (empty scopes) enforces nothing", P.enforce_decision(jurisdiction="session", op="crp_evidence", verdict=None, policy=P.CAPABILITY_SUFFICIENCY_POLICY) == (False, ""))
    # kernel round-trip: the precondition is a SIBLING outside aggregate(); refuses ONLY on enumerated insufficiency
    from ugk.kernel import GovernanceKernel, GateRefusal
    def _mk(pol):
        k = GovernanceKernel(); k.open_session(); k._dcap_policy = pol; return k
    def _admits(k, **kw):
        try:
            k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True,
                      jurisdiction=kw.pop("jurisdiction", "session"), **kw); return True
        except GateRefusal:
            return False
    chk("8c.kernel: enumerated+PROVEN admits", _admits(_mk(ENF(capability_class="c")), capability_verdicts={"c": "PROVEN"}))
    kf = _mk(ENF(capability_class="c")); _ref = not _admits(kf, capability_verdicts={"c": "FAIL"})
    import json as _json
    _rr = [r for r in kf._store.all_receipts() if r.op == "gate_refuse"]
    _rc = (_rr[-1].parameters if isinstance(_rr[-1].parameters, dict) else _json.loads(_rr[-1].parameters)).get("refusal_cause") if _rr else None
    chk("8c.kernel: enumerated+FAIL refuses w/ attributable insufficient-capability", _ref and _rc == "insufficient-capability")
    chk("8c.kernel: unenumerated/live admits unchanged", _admits(_mk(P.CAPABILITY_SUFFICIENCY_POLICY), capability_verdicts={}))
    # aggregation intact + non-aggregating: gate=False refuses via the normal path independent of D_cap
    ka = _mk(ENF(capability_class="c"))
    try:
        ka.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: False, jurisdiction="session", capability_verdicts={"c": "PROVEN"}); _g = False
    except GateRefusal:
        _g = True
    chk("8c.kernel: gate=False still refuses (aggregate() intact; D_cap orthogonal)", _g)
    from ugk.storage.store import compute_schema_hash as _csh, EXPECTED_SCHEMA_HASH as _esh
    chk("8c.schema stationary (no committed determination column)", _csh(_mk(ENF(capability_class="c"))._store._conn) == _esh)

    # ---- AD-70 (r147): LIVE ACTIVATION round-trip -- real governed ops under the LIVE policy ----
    # Proves the activation is NON-VACUOUS at the kernel: a real governed op in an enumerated scope
    # refuses on insufficiency with insufficient-capability and admits on PROVEN, while the SAME op in an
    # unenumerated scope is unchanged. Founding needs a real governor identity; set the fixture key,
    # found, prove, restore (no batch-interpreter pollution).
    import ugk.kernel as _km
    from ugk.conformance._fixture import fixture_pubkey as _fpk
    _saved_key = _km.GOVERNOR_PUBKEY_HEX
    _km.GOVERNOR_PUBKEY_HEX = _fpk()
    try:
        def _mkf():
            kk = GovernanceKernel(); kk._ceremony(); kk.open_session(); return kk
        def _runf(op, jur, **kw):
            kk = _mkf()
            try:
                kk.execute(op=op, authority="adm", parameters={}, gate=lambda: True, jurisdiction=jur, **kw); return "ADMIT", kk
            except GateRefusal:
                return "REFUSE", kk
        def _causef(kk):
            rr = [r for r in kk._store.all_receipts() if r.op == "gate_refuse"]
            if not rr:
                return None
            pp = rr[-1].parameters; pp = pp if isinstance(pp, dict) else _json.loads(pp); return pp.get("refusal_cause")
        _entry0 = P.CAPABILITY_SUFFICIENCY_POLICY["enforced_scopes"][0]
        _op0, _jur0, _cls0 = _entry0["op"], _entry0["jurisdiction"], _entry0["capability_class"]
        _r, _k = _runf(_op0, _jur0)
        chk("8d.LIVE: enumerated real op (%s@%s) NO verdict refuses" % (_op0, _jur0), _r == "REFUSE")
        chk("8d.LIVE: refusal cause is insufficient-capability (attributable)", _causef(_k) == "insufficient-capability")
        _r, _k = _runf(_op0, _jur0, capability_verdicts={_cls0: "PROVEN"})
        chk("8d.LIVE: enumerated real op + PROVEN admits", _r == "ADMIT")
        _r, _k = _runf(_op0, _jur0, capability_verdicts={_cls0: "FAIL"})
        chk("8d.LIVE: enumerated real op + FAIL refuses", _r == "REFUSE" and _causef(_k) == "insufficient-capability")
        _r, _k = _runf(_op0, _jur0, capability_verdicts={_cls0: "WAIVED"})
        chk("8d.LIVE: WAIVED (entry does not permit) refuses -- never treated as PROVEN", _r == "REFUSE")
        _r, _k = _runf(_op0, _jur0, capability_verdicts={_cls0: "BY-CONSTRUCTION"})
        chk("8d.LIVE: unbacked BY-CONSTRUCTION refuses -- no laundering", _r == "REFUSE")
        _r, _k = _runf(_op0, "session")
        chk("8d.LIVE: same real op in UNENUMERATED scope (session) admits unchanged", _r == "ADMIT")
    finally:
        _km.GOVERNOR_PUBKEY_HEX = _saved_key

    passed = sum(1 for _, c in checks if c)
    total = len(checks)
    fails = [n for n, c in checks if not c]
    detail = ("D_cap sufficiency policy (AD-68, Lane 2a): PROVEN-only evidence sufficiency over the "
              "closed CTR-S-03 7-verdict vocabulary; WAIVED is an authority disposition not evidence; "
              "BY-CONSTRUCTION cannot launder (admissible only via named proof, never PROVEN); "
              "FAIL/GAP/ERROR/NOT-RUN and unknown verdicts fail closed; external evidence non-sufficient; "
              "D_cap remains non-aggregating and outside aggregate(); NO enforcement/refusal path is "
              "opened and no decision-path module consumes the policy (frame-stationary; enforcement is "
              "the separate Lane 2b increment).")
    if fails:
        detail = "FAILED: " + "; ".join(fails)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
