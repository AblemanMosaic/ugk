"""ugk/conformance/capability_evidence_commit_gate.py — Lane 4b (AD-52) D_cap commitment gate.

Proves the D_cap COMMITTED CAPABILITY-EVIDENCE surface: CGP dispatcher evidence is body-committed
in UGK-BODY-v3 (h_cap binds the ledger) WITHOUT laundering, and D_cap is NON-AGGREGATING — it is
not consumed by conjunctive_refusal_monotone_v1 and does not affect ADMIT/REFUSE. trace_vector_hash
remains the r127/r128 FGA-TRACE-v1 post-body hash over the FOUR aggregating surfaces. This is a
schema commitment, not enforcement; decision-authority for D_cap is a later increment.
"""
from ugk.storage.store import (
    UGKReceiptStore, compute_h_body, EXPECTED_SCHEMA_HASH, _pinned_codex_hash,
)
from ugk.fga.trace_vector import (
    build_trace_vector, FrameRef, aggregate, ADMIT,
    COMMITTED_SURFACES, CAPABILITY_SURFACES, verify_capability_surface,
)
from ugk.cgp.dispatch import (
    capability_evidence_commitment, CapabilityEvidenceLedger, WaiverRecord,
    _ledger_body, _hash_body, VERDICTS,
)
from ugk.cgp.runner.types import EvidenceArtifact


def _ledger(cap3="ERROR"):
    arts = (
        EvidenceArtifact(invariant="CGP-ESA-Cap-1", verdict="PROVEN", evidence_class="gate-suite"),
        EvidenceArtifact(invariant="CGP-ESA-Cap-2", verdict="GAP", evidence_class="none"),
        EvidenceArtifact(invariant="CGP-ESA-Cap-3", verdict=cap3, evidence_class="gate-suite"),
        EvidenceArtifact(invariant="CGP-ESA-Cap-4", verdict="NOT-RUN", evidence_class="deferred"),
        EvidenceArtifact(invariant="CGP-ESA-Cap-5", verdict="BY-CONSTRUCTION", evidence_class="by-construction"),
    )
    waivers = (WaiverRecord(cap_id="CGP-ESA-Cap-6", authority="gov", reason="r", evidence_ref="e"),)
    oos = ("CGP-ESA-Cap-7",); gaps = ("CGP-ESA-Cap-8",)
    lh = _hash_body(_ledger_body("regv1", "s1", "all", "r1", "sh", arts, oos, waivers, gaps))
    return CapabilityEvidenceLedger("regv1", "s1", "all", "r1", "sh", arts, oos, waivers, (), gaps, lh)


def _store():
    return UGKReceiptStore(":memory:")


def _w(s, **kw):
    base = dict(op="crp_evidence", authority="a", parameters={"x": 1}, intent="t",
                jurisdiction="production", session_dkn="d", law_hash="L", legend_hash="G",
                warrant_id="W", intent_ref="r")
    base.update(kw)
    return s.write(**base)


def _frame(r):
    return FrameRef(law_hash=r.law_hash, schema_hash=EXPECTED_SCHEMA_HASH,
                    legend_hash=r.legend_hash, codex_hash=_pinned_codex_hash())


def run():
    checks = []

    def chk(n, c):
        checks.append((n, bool(c)))

    led = _ledger()
    s = _store()
    r = _w(s, commit_capability_evidence=True, capability_ledger=led)

    # (1) h_cap recomputes from the EXACT dispatcher ledger
    chk("1.h_cap recomputes from exact ledger",
        capability_evidence_commitment(led)["h_cap"] == r.h_cap and len(r.h_cap) == 64)

    # (2) dispatcher ledger_hash verifies (and binding fails closed if it does not)
    chk("2.ledger_hash self-verifies", led.verify_hash())
    bad = _ledger()
    object.__setattr__(bad, "ledger_hash", "0" * 64)
    try:
        capability_evidence_commitment(bad); _failclosed = False
    except ValueError:
        _failclosed = True
    chk("2.corrupt ledger fails closed (never bound)", _failclosed)

    # (3) verdict census faithful + non-collapsing: any single verdict change moves h_cap
    chk("3.census faithful: ERROR->GAP changes h_cap",
        capability_evidence_commitment(_ledger("ERROR"))["h_cap"]
        != capability_evidence_commitment(_ledger("GAP"))["h_cap"])
    chk("3.census faithful: ERROR->FAIL changes h_cap",
        capability_evidence_commitment(_ledger("ERROR"))["h_cap"]
        != capability_evidence_commitment(_ledger("FAIL"))["h_cap"])

    # (4) the seven verdicts are kept DISTINCT (no class maps onto another) — pairwise h_cap distinct
    hs = {v: capability_evidence_commitment(_ledger(v))["h_cap"] for v in VERDICTS}
    chk("4.WAIVED/GAP/ERROR/NOT-RUN/BY-CONSTRUCTION/PROVEN/FAIL all distinct in commitment",
        len(set(hs.values())) == len(VERDICTS))

    # (5) no PROVEN synthesis: a cap that is NOT-RUN/GAP can never be recorded PROVEN by the binding.
    #     (the helper has no code path that sets PROVEN; it records verdicts verbatim.)
    led_nr = _ledger("NOT-RUN")
    chk("5.Navigator/external evidence cannot become PROVEN by existence",
        capability_evidence_commitment(led_nr)["h_cap"]
        != capability_evidence_commitment(_ledger("PROVEN"))["h_cap"])

    # (6) WAIVED stays AUTHORITY-MARKED, not evidence: dropping the waiver's authority changes h_cap.
    led_a = _ledger()
    arts = led_a.artifacts
    w2 = (WaiverRecord(cap_id="CGP-ESA-Cap-6", authority="DIFFERENT", reason="r", evidence_ref="e"),)
    lh2 = _hash_body(_ledger_body("regv1", "s1", "all", "r1", "sh", arts, ("CGP-ESA-Cap-7",), w2, ("CGP-ESA-Cap-8",)))
    led_a2 = CapabilityEvidenceLedger("regv1", "s1", "all", "r1", "sh", arts, ("CGP-ESA-Cap-7",), w2, (), ("CGP-ESA-Cap-8",), lh2)
    chk("6.WAIVED authority-marked: changing waiver authority changes h_cap",
        capability_evidence_commitment(led)["h_cap"] != capability_evidence_commitment(led_a2)["h_cap"])

    # (7) D_cap is ABSENT from the aggregating trace vector
    tv = build_trace_vector(r, _frame(r))
    chk("7.D_cap absent from aggregating trace vector",
        {x.surface_id for x in tv.surfaces} == {"D_s", "D_c", "D_m", "D_j"}
        and "D_cap" not in {x.surface_id for x in tv.surfaces})
    chk("7.D_cap not in aggregating registry; is in the sibling registry",
        "D_cap" not in {s.surface_id for s in COMMITTED_SURFACES}
        and "D_cap" in {s.surface_id for s in CAPABILITY_SURFACES})

    # (8) terminal_outcome unchanged by D_cap: a v3 receipt aggregates exactly as a v2 receipt
    s2 = _store(); r2 = _w(s2, commit_terminal_outcome=True)
    tv2 = build_trace_vector(r2, _frame(r2))
    chk("8.D_cap does not change ADMIT/REFUSE (v3 verdict == v2 verdict == ADMIT)",
        aggregate(tv)[0] == aggregate(tv2)[0] == ADMIT)
    chk("8.terminal_outcome committed on v3 equals the v2 derivation",
        r.terminal_outcome == r2.terminal_outcome == "ADMIT")

    # (9) trace_vector_hash remains FGA-TRACE-v1 over the FOUR aggregating surfaces
    chk("9.trace_vector_hash present (ADMIT) and over 4 aggregating surfaces",
        isinstance(r.trace_vector_hash, str) and len(r.trace_vector_hash) == 64
        and tuple(x.surface_id for x in tv.surfaces) == tuple(s.surface_id for s in COMMITTED_SURFACES))

    # (10) v1/v2 receipts are NOT reinterpreted. Uniform v5 (AD-65) forbids a live v1/v2 write, so this is
    # proven on SYNTHETIC v1/v2 fixtures: the version-aware body recomputes deterministically (what
    # verify_receipt_bodies asserts) AND the capability fields are genuinely ignored at version<3 (no h_cap
    # committed) -- i.e. the lower-version body is not reinterpreted by the v3 capability surface.
    base = dict(op="x", authority="a", parameters={"k": 1}, intent="i", jurisdiction="j",
                confidence="high", timestamp=1.0, failed=False, session_dkn="d", law_hash="L",
                legend_hash="G", warrant_id="", intent_ref="", h_s="a" * 64, h_c="b" * 64,
                h_m="c" * 64, h_j="d" * 64, h_r="e" * 64, parent_h_r="", mode="strict",
                id_c_s="c_s.v1", id_c_c="c_c.v1", id_c_m="c_m.v1+sigma_0", id_c_j="c_j.v1")
    hb_v1 = compute_h_body(version=1, **base)
    chk("10.v1 (synthetic) verifies + commits no h_cap (cap fields ignored at version<3)",
        compute_h_body(version=1, **base) == hb_v1 == compute_h_body(version=1, h_cap="z" * 64, **base))
    _to = dict(terminal_outcome="ADMIT", terminal_outcome_model_id="m", terminal_outcome_reason="r")
    hb_v2 = compute_h_body(version=2, **_to, **base)
    chk("10.v2 (synthetic) verifies + commits no h_cap (cap fields ignored at version<3)",
        compute_h_body(version=2, **_to, **base) == hb_v2 == compute_h_body(version=2, h_cap="z" * 64, **_to, **base))
    # v1/v2 body byte-identity: at version<3 the capability fields are ignored
    chk("10.v1 byte-identity (cap fields ignored)",
        compute_h_body(version=1, **base) == compute_h_body(version=1, h_cap="z" * 64, **base))
    chk("10.v2 byte-identity (cap fields ignored)",
        compute_h_body(version=2, terminal_outcome="ADMIT", terminal_outcome_model_id="m",
                       terminal_outcome_reason="r", **base)
        == compute_h_body(version=2, terminal_outcome="ADMIT", terminal_outcome_model_id="m",
                          terminal_outcome_reason="r", h_cap="z" * 64, **base))

    # (11) v3 receipts verify (full-body recompute) + capability surface verifies against the ledger
    chk("11.v3 verifies (full-body recompute)", s.verify_receipt_bodies())
    chk("11.verify_capability_surface(receipt, ledger) ok", verify_capability_surface(r, led)[0])
    chk("11.verify_capability_surface rejects a mismatched ledger",
        not verify_capability_surface(r, _ledger("FAIL"))[0])

    # (12) h_cap tamper fails full-body verification
    st = _store(); rt = _w(st, commit_capability_evidence=True, capability_ledger=led)
    st._conn.execute("UPDATE receipts SET h_cap=? WHERE receipt_id=?", ("f" * 64, rt.receipt_id))
    chk("12.h_cap tamper fails verify", not st.verify_receipt_bodies())

    # (13) schema downgrade/tamper fails: stripping committed v3 fields (version stays 3)
    sd = _store(); rd = _w(sd, commit_capability_evidence=True, capability_ledger=led)
    sd._conn.execute("UPDATE receipts SET h_cap=NULL WHERE receipt_id=?", (rd.receipt_id,))
    chk("13.v3 downgrade-strip h_cap fails verify", not sd.verify_receipt_bodies())

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    failed = [n for n, ok in checks if not ok]
    detail = "%d/%d checks pass" % (passed, total)
    if failed:
        detail += " | FAILED: " + "; ".join(failed)
    return (passed == total), detail


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS " if ok else "FAIL ") + detail)
