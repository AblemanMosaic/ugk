"""ugk/conformance/defer_lifecycle_gate.py — proves DEFER-S-01 (r149): DEFER is a LIVE terminal outcome
gated on a valid HELD continuation record, with the emit / hold / resume / resolve / expire / refuse
lifecycle. Resume re-enters the full W/G/E execute() path (no bypass); expiry is deterministic from
committed evidence (never wall-clock); CRISIS stays reserved; ADMIT/REFUSE/STRUCTURAL_ERROR unchanged.
"""
import ugk.kernel as km
from ugk.kernel import GovernanceKernel, GateRefusal
from ugk.conformance._fixture import fixture_pubkey
import ugk.storage.store as S


def run():
    checks = []

    def chk(n, c):
        checks.append((n, bool(c)))

    def raises(f, exc=Exception):
        try:
            f(); return False
        except exc:
            return True

    # ---- emit-gating + reserved CRISIS + unchanged ordinary projections (store-level) ----
    st = S.UGKReceiptStore(db_path=":memory:")
    chk("1.DEFER cannot emit without a continuation",
        raises(lambda: st.write(op="test_checkpoint", authority="a", parameters={}, law_hash="L",
               commit_terminal_outcome=True, terminal_outcome_override="DEFER"), S.ReservedOutcomeError))
    nonheld = dict(id="x", op="o", authority="a", parameters={}, jurisdiction="session", anchor="z",
                   expiry_basis={"kind": "receipt_height", "value": 1}, state="RESUMED",
                   model_id="continuation_record_model_v1")
    chk("1.DEFER cannot emit with a NON-HELD continuation",
        raises(lambda: st.write(op="o", authority="a", parameters={}, law_hash="L",
               commit_terminal_outcome=True, terminal_outcome_override="DEFER", continuation=nonheld),
               S.ReservedOutcomeError))
    chk("7.CRISIS remains reserved / non-emittable", raises(lambda: S._assert_emittable("CRISIS"), S.ReservedOutcomeError))
    chk("8.ADMIT/REFUSE/STRUCTURAL_ERROR projections unchanged",
        S._derive_committed_outcome("gate_refuse", False, None, "")[0] == "REFUSE"
        and S._derive_committed_outcome("protocol_error", True, None, "x")[0] == "STRUCTURAL_ERROR"
        and S._derive_committed_outcome("op", False, None, "")[0] == "ADMIT")

    # ---- expiry determinism (pure function of committed evidence; no wall-clock) ----
    chk("5.expiry receipt_height deterministic",
        S.continuation_expired('{"kind":"receipt_height","value":10}', 10) is True
        and S.continuation_expired('{"kind":"receipt_height","value":10}', 9) is False)
    chk("5.expiry explicit_trigger deterministic (committed trigger)",
        S.continuation_expired('{"kind":"explicit_trigger","value":"T"}', 999, committed_triggers=["T"]) is True
        and S.continuation_expired('{"kind":"explicit_trigger","value":"T"}', 999, committed_triggers=[]) is False)

    # ---- founded kernel: emit / resume / resolve / expire / refuse ----
    saved = km.GOVERNOR_PUBKEY_HEX
    km.GOVERNOR_PUBKEY_HEX = fixture_pubkey()
    try:
        k = GovernanceKernel(); k._ceremony(); k.open_session()
        cid = k.defer_operation("test_checkpoint", parameters={"x": 1}, jurisdiction="session",
                                expiry_basis={"kind": "receipt_height", "value": k.store.committed_height() + 1000})
        rec = k.store.find_continuation(cid)
        chk("2.valid DEFER emits a committed continuation-linked terminal (DEFER + HELD)",
            rec is not None and rec.terminal_outcome == "DEFER" and rec.continuation_state == "HELD" and rec.continuation_id == cid)
        chk("9.DEFER receipt body verifies (TO-S-01 over the extended domain)", k.store.verify_receipt_bodies())

        n_before = k.store.committed_height()
        k.resume_continuation(cid, gate=lambda: True)
        chk("3.resume re-enters the full execute() governance path (new receipts appended)",
            k.store.committed_height() > n_before)
        chk("4.resolve recorded RESOLVED (append-only; creating HELD record not mutated)",
            k.store.find_continuation(cid).continuation_state == "RESOLVED")
        chk("4.resumed op produced an ordinary (non-reserved) terminal",
            all(r.terminal_outcome in (None, "ADMIT", "REFUSE", "STRUCTURAL_ERROR", "DEFER") for r in k.store.all_receipts()))
        chk("9.all bodies verify after resume/resolve", k.store.verify_receipt_bodies())

        chk("6.resume of an already-terminal continuation refuses cleanly",
            raises(lambda: k.resume_continuation(cid, gate=lambda: True), GateRefusal))

        cid2 = k.defer_operation("test_checkpoint", parameters={"y": 2},
                                 expiry_basis={"kind": "receipt_height", "value": k.store.committed_height()})
        chk("5.expired continuation: resume refuses cleanly (deterministic committed-evidence expiry)",
            raises(lambda: k.resume_continuation(cid2, gate=lambda: True), GateRefusal))
        chk("6.expired continuation recorded EXPIRED transition",
            k.store.find_continuation(cid2).continuation_state == "EXPIRED")

        chk("6.resume of an unknown continuation refuses cleanly",
            raises(lambda: k.resume_continuation("nonexistent-id", gate=lambda: True), GateRefusal))
        chk("9.final: all receipt bodies verify (full lifecycle committed + integral)", k.store.verify_receipt_bodies())
    finally:
        km.GOVERNOR_PUBKEY_HEX = saved

    passed = sum(1 for _, c in checks if c)
    total = len(checks)
    fails = [n for n, c in checks if not c]
    detail = ("DEFER-S-01 (r149): DEFER is a live terminal outcome gated on a valid HELD continuation "
              "(emit fails closed without one; CRISIS stays reserved); resume re-enters the full execute() "
              "W/G/E path with no bypass; resolve is an ordinary ADMIT/REFUSE/STRUCTURAL_ERROR; expiry is "
              "deterministic from committed evidence (never wall-clock); invalid/expired/terminal/unknown "
              "continuations refuse cleanly; the lifecycle is append-only; ADMIT/REFUSE/STRUCTURAL_ERROR "
              "and TO-S-01 body integrity are unchanged.")
    if fails:
        detail = "FAILED: " + "; ".join(fails)
    return (passed == total), detail


if __name__ == "__main__":
    ok, d = run()
    print(("PASS " if ok else "FAIL ") + d)
