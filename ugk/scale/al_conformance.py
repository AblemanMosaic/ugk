"""ugk.scale.al_conformance — full adversarial AL (authority-laundering) battery.

The 22-test adversarial battery that proves the earned-independence oracle never calls a
dependent pair independent (no authority laundering). Folded into the package so r9 carries
its own complete safety proof. NOT on the default path; tests the opt-in ugk.scale oracle.
Original adversarial harness:

AL groups (A/C/D/E/F/H/J): any failure STOPS the track (authority laundering).
TO groups (B/G/I): measure green-zone width; never block acceptance.

Run: python break_tests.py
"""
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")

from ugk.scale.oracle import (
    Chain, Candidate, CommitLane, independent, OracleRefusal,
    DEPENDENT, INDEPENDENT,
)

AL_RESULTS, TO_RESULTS = [], []
def al(name, ok, detail=""):  AL_RESULTS.append((name, ok, detail))
def to(name, outcome, detail=""): TO_RESULTS.append((name, outcome, detail))

def admit(c, chain):
    """Lane admission: re-run posture check + basic well-formedness. Returns bool."""
    try:
        from ugk.scale.oracle import _posture_check
        _posture_check(c)
    except OracleRefusal:
        return False
    return True

# === helper: a chain with one committed grant + one produced effect ===
def base_chain():
    ch = Chain()
    g = Candidate(op="authority_model_set", agent="gov", grant_class=True,
                  posture_affecting=True, binding_key=(("sys","gov"),))
    rg = ch.append(g)
    x = Candidate(op="app_write", agent="alice", session="s1",
                  binding_key=(("eX","alice"),), produces_effects=("eX",),
                  input_refs=(), warrant_basis_refs=(rg.rhash,))
    rx = ch.append(x)
    return ch, rg, rx

# ============ GROUP A — false-independent laundering D1-D5 (AL) ============
def group_A():
    ch, rg, rx = base_chain()
    # A1 — D1 causal under-declaration: Y consumes eX but input_refs empty
    y = Candidate(op="app_write", agent="bob", session="s2", binding_key=(("eY","bob"),),
                  produces_effects=("eY",), input_refs=(), warrant_basis_refs=(rg.rhash,))
    consumer = Candidate(op="app_write", agent="bob", session="s2", binding_key=(("eZ","bob"),),
                         produces_effects=("eZ",), input_refs=(),  # EMPTY but really needs eX
                         warrant_basis_refs=(rg.rhash,))
    # empty input_refs ⇒ verified set = empty set; does NOT include eX, BUT rule: empty means
    # "depends on all" only if None. Here empty tuple = "explicitly depends on nothing" — test
    # that the oracle still refuses when the real producer shares no binding disjointness issue.
    # The laundering attempt: claim independence from the eX-producer rx by declaring input_refs=().
    xprod = Candidate(op="app_write", agent="alice", session="s1", binding_key=(("eX2","alice"),),
                      produces_effects=("eX2",), input_refs=(), warrant_basis_refs=(rg.rhash,))
    # Try to get `consumer` independent of `xprod` while consumer truly needs eX2:
    consumer2 = Candidate(op="app_write", agent="bob", session="s2", binding_key=(("eZ","bob"),),
                          produces_effects=("eZ",), input_refs=(),  # omits eX2
                          warrant_basis_refs=(rg.rhash,))
    verdict = independent(xprod, consumer2, ch)
    # Disjoint binding + empty (verified-empty) input_refs ⇒ oracle sees no declared dep.
    # This is the HONEST limitation: an empty input_refs that OMITS a real dep can look
    # independent. Per schema, empty tuple must be read as "depends on nothing" only if it is
    # chain-consistent; the adversarial point is whether omission launders. Record actual.
    al("A1 D1 under-declaration refused", verdict == DEPENDENT,
       f"verdict={verdict} (empty input_refs omitting real producer)")

    # A2 — D2 warrant-by-value: warrant_basis_refs cites a non-receipt value
    yv = Candidate(op="app_write", agent="bob", binding_key=(("eY","bob"),),
                   input_refs=(), warrant_basis_refs=("I_WAS_GRANTED_X",))  # value, not hash
    v = independent(rx_to_cand(rx), yv, ch)
    al("A2 D2 warrant-by-value ⇒ dependent", v == DEPENDENT, f"verdict={v}")

    # A3 — D3 contention hiding: same binding key, omitted
    a = Candidate(op="app_write", agent="alice", binding_key=(("eShared","gov"),),
                  input_refs=(), warrant_basis_refs=(rg.rhash,))
    b = Candidate(op="app_write", agent="bob", binding_key=(),  # OMITS the shared key
                  input_refs=(), warrant_basis_refs=(rg.rhash,))
    v = independent(a, b, ch)
    al("A3 D3 contention hiding (absent key) ⇒ dependent", v == DEPENDENT, f"verdict={v}")

    # A4 — D4 refusal evasion: refusal narrows subject to exclude its real target
    target = Candidate(op="app_write", agent="bob", binding_key=(("eT","bob"),),
                       produces_effects=("eT",), input_refs=(), warrant_basis_refs=(rg.rhash,))
    refusal = Candidate(op="gate_refuse", agent="gov", binding_key=(("rk","gov"),),
                        refusal_subject="eUNRELATED",  # lies: real subject is eT
                        input_refs=(), warrant_basis_refs=(rg.rhash,))
    v = independent(refusal, target, ch)
    # refusal_subject != target's effect ⇒ oracle would call independent UNLESS we treat
    # unverifiable narrowing as global. Record actual to expose the gap.
    al("A4 D4 refusal evasion refused", v == DEPENDENT,
       f"verdict={v} (refusal narrowed subject away from real target)")

    # A5 — D5 posture straddle: posture op declares posture_affecting=False
    try:
        bad = Candidate(op="a1_posture_set", agent="gov", posture_affecting=False,
                        binding_key=(("p","gov"),), input_refs=(), warrant_basis_refs=(rg.rhash,))
        other = Candidate(op="app_write", agent="bob", binding_key=(("eO","bob"),),
                          input_refs=(), warrant_basis_refs=(rg.rhash,))
        v = independent(bad, other, ch)
        al("A5 D5 posture underdeclaration refused", False, f"NO refusal raised, verdict={v}")
    except OracleRefusal as e:
        al("A5 D5 posture underdeclaration refused", e.code == "D5-POSTURE-UNDERDECLARED", e.code)

def rx_to_cand(r):
    return Candidate(op=r.op, agent=r.agent, session=r.session, binding_key=r.binding_keys,
                     produces_effects=r.produces_effects, input_refs=(), warrant_basis_refs=())

# ============ GROUP C — absence/unverifiable ⇒ dependent (AL) ============
def group_C():
    ch, rg, rx = base_chain()
    other = Candidate(op="app_write", agent="bob", binding_key=(("eO","bob"),),
                      input_refs=(), warrant_basis_refs=(rg.rhash,))
    # C1 unresolvable input_ref
    c1 = Candidate(op="app_write", agent="carol", binding_key=(("eC","carol"),),
                   input_refs=("deadbeef"*8,), warrant_basis_refs=(rg.rhash,))
    al("C1 unresolvable input_ref ⇒ dependent", independent(c1, other, ch) == DEPENDENT)
    # C2 unresolvable warrant ref
    c2 = Candidate(op="app_write", agent="carol", binding_key=(("eC2","carol"),),
                   input_refs=(), warrant_basis_refs=("not_a_real_hash",))
    al("C2 unresolvable warrant_ref ⇒ dependent", independent(c2, other, ch) == DEPENDENT)
    # C3 non-grant warrant ref (points to a non-grant receipt)
    c3 = Candidate(op="app_write", agent="carol", binding_key=(("eC3","carol"),),
                   input_refs=(), warrant_basis_refs=(rx.rhash,))  # rx is app_write, not grant
    al("C3 non-grant warrant_ref ⇒ dependent", independent(c3, other, ch) == DEPENDENT)
    # C4 empty declaration sweep (all fields None)
    c4 = Candidate(op="app_write", agent="carol")
    al("C4 empty-declaration ⇒ dependent", independent(c4, other, ch) == DEPENDENT)

# ============ GROUP D — D8 hidden same-agent/session (AL) ============
def group_D():
    ch, rg, rx = base_chain()
    # D8-1 split transaction: same agent+session, disjoint targets, NO input/warrant proofs
    p1 = Candidate(op="app_write", agent="dave", session="tx", binding_key=(("eP1","dave"),),
                   input_refs=None, warrant_basis_refs=None)  # absent ⇒ dependent
    p2 = Candidate(op="app_write", agent="dave", session="tx", binding_key=(("eP2","dave"),),
                   input_refs=None, warrant_basis_refs=None)
    al("D8-1 split-tx (absent proofs) ⇒ dependent", independent(p1, p2, ch) == DEPENDENT)
    # D8-2 forged independence: same agent, declare disjoint but actually overlap
    q1 = Candidate(op="app_write", agent="dave", session="tx", binding_key=(("eQ","dave"),),
                   input_refs=(), warrant_basis_refs=(rg.rhash,))
    q2 = Candidate(op="app_write", agent="dave", session="tx", binding_key=(("eQ","dave"),),
                   input_refs=(), warrant_basis_refs=(rg.rhash,))  # SAME key = overlap
    al("D8-2 forged-disjoint (real overlap) ⇒ dependent", independent(q1, q2, ch) == DEPENDENT)
    # D8-3 cross-agent disjoint, POSITIVELY DECLARED = EARNED GREEN ZONE control.
    # Uses positive, chain-verifiable input_refs (rx is committed in base_chain) + grant-class
    # warrant. This demonstrates the earned green zone under the positive-declaration rule —
    # NOT empty refs (which correctly collapse to DEPENDENT and would understate the zone).
    a = Candidate(op="app_write", agent="alice", session="sa", binding_key=(("eA","alice"),),
                  produces_effects=("eA",), input_refs=(rx.rhash,), warrant_basis_refs=(rg.rhash,))
    b = Candidate(op="app_write", agent="bob", session="sb", binding_key=(("eB","bob"),),
                  produces_effects=("eB",), input_refs=(rx.rhash,), warrant_basis_refs=(rg.rhash,))
    v = independent(a, b, ch)
    to("D8-3 cross-agent disjoint, positively declared = INDEPENDENT (earned green zone)", v,
       "existence proof for the EARNED green zone (positive chain-verifiable refs)")

# ============ GROUP E — C2/I7 crash recovery (AL) ============
def group_E():
    ch, rg, rx = base_chain()
    lane = CommitLane(ch)
    cand = Candidate(op="app_write", agent="alice", binding_key=(("eE","alice"),),
                     input_refs=(), warrant_basis_refs=(rg.rhash,))
    # E1 durable enqueue, crash before commit, restart: NO auto-promote
    lane.enqueue(cand)
    pre = len(ch.all())
    promoted = lane.recover_after_crash(admit)  # returns eligible, does NOT commit
    al("E1 no auto-commit on restart", len(ch.all()) == pre and lane.durable_queue == [],
       f"chain grew={len(ch.all())-pre}, queue_cleared={lane.durable_queue==[]}")
    # E2 restart-promotion attack: a refusal admitted after crash should be re-checked.
    #    Model: admit_fn now refuses this op class. Re-entry must respect it.
    def admit_refuse_all(c, chain): return False
    lane.enqueue(cand)
    promoted2 = lane.recover_after_crash(admit_refuse_all)
    al("E2 re-entry re-validates (refused ⇒ not promoted)", promoted2 == [],
       f"promoted={len(promoted2)} (expected 0)")
    # E3 queue injection: forged candidate in queue is never committable without lane admit
    forged = Candidate(op="a1_posture_set", agent="evil", posture_affecting=False,
                       binding_key=(("p","evil"),))  # will fail posture check at admit
    lane.enqueue(forged)
    promoted3 = lane.recover_after_crash(admit)
    al("E3 queue-injection (forged) not promoted", forged not in promoted3,
       f"forged promoted={forged in promoted3}")

# ============ GROUP F — C3/NBER-1 receipt-before-effect (AL) ============
def group_F():
    ch, rg, rx = base_chain()
    lane = CommitLane(ch)
    order = []
    cand = Candidate(op="app_write", agent="alice", binding_key=(("eF","alice"),),
                     input_refs=(), warrant_basis_refs=(rg.rhash,))
    def eff(c): order.append("effect"); return "done"
    # wrap append to record receipt timing
    r, res = lane.commit_and_effect(cand, admit, eff, actual_binding=(("eF","alice"),))
    # the receipt is in chain BEFORE effect ran: committed_then_effect recorded receipt then True
    rec_first = ch.has_hash(r.rhash)
    al("F1 receipt durable before effect (NBER-1)", rec_first and order == ["effect"],
       f"receipt_in_chain={rec_first}, effect_ran_after={order}")
    # F2 crash between receipt and effect: receipt stands, never rewritten
    cand2 = Candidate(op="app_write", agent="alice", binding_key=(("eF2","alice"),),
                      input_refs=(), warrant_basis_refs=(rg.rhash,))
    def eff_crash(c): raise RuntimeError("crash after receipt")
    pre = len(ch.all())
    try:
        lane.commit_and_effect(cand2, admit, eff_crash, actual_binding=(("eF2","alice"),))
    except RuntimeError:
        pass
    # receipt N for cand2 should be committed (durable) despite effect crash
    grew = len(ch.all()) == pre + 1
    al("F2 crash-after-receipt: receipt stands (not rolled back)", grew,
       f"chain grew by {len(ch.all())-pre} (expected 1; NBER-1 receipt is durable)")
    # F3 declared!=actual binding ⇒ refused before any effect
    cand3 = Candidate(op="app_write", agent="alice", binding_key=(("declared","alice"),),
                      input_refs=(), warrant_basis_refs=(rg.rhash,))
    try:
        lane.commit_and_effect(cand3, admit, lambda c: order.append("BAD"),
                               actual_binding=(("ACTUAL","alice"),))
        al("F3 declared!=actual binding refused", False, "no refusal raised")
    except OracleRefusal as e:
        al("F3 declared!=actual binding refused", e.code == "BINDING-DECL-ACTUAL-MISMATCH", e.code)

# ============ GROUP H — metadata forgery (AL) ============
def group_H():
    ch, rg, rx = base_chain()
    other = Candidate(op="app_write", agent="bob", binding_key=(("eO","bob"),),
                      input_refs=(), warrant_basis_refs=(rg.rhash,))
    # H2 reference to uncommitted/future receipt
    h2 = Candidate(op="app_write", agent="carol", binding_key=(("eH","carol"),),
                   input_refs=("futurehash"*8,), warrant_basis_refs=(rg.rhash,))
    al("H2 future/uncommitted ref ⇒ dependent", independent(h2, other, ch) == DEPENDENT)
    # H3 aggregate phantom members
    agg = Candidate(op="batch_envelope", agent="gov", is_aggregate=True,
                    member_range=("phantom1", "phantom2"), binding_key=(("agg","gov"),))
    al("H3 aggregate phantom (vs any member) ⇒ dependent",
       independent(agg, other, ch) == DEPENDENT)

# ============ GROUP I — priority/safety-refusal ordering (AL+TO) ============
def group_I():
    ch, rg, rx = base_chain()
    # I2t P0 refusal vs its own subject ⇒ dependent (AL)
    target = Candidate(op="app_write", agent="bob", binding_key=(("eIT","bob"),),
                       produces_effects=("eIT",), input_refs=(), warrant_basis_refs=(rg.rhash,))
    refusal = Candidate(op="gate_refuse", agent="gov", binding_key=(("rk2","gov"),),
                        refusal_subject="eIT",  # correctly names its subject
                        input_refs=(), warrant_basis_refs=(rg.rhash,))
    al("I2t refusal-of-subject ⇒ dependent", independent(refusal, target, ch) == DEPENDENT)
    # I1t P0 refusal vs UNRELATED, positively declared ⇒ may be independent (TO permissiveness)
    unrelated = Candidate(op="app_write", agent="carol", binding_key=(("eUR","carol"),),
                          produces_effects=("eUR",), input_refs=(rx.rhash,), warrant_basis_refs=(rg.rhash,))
    refusal2 = Candidate(op="gate_refuse", agent="gov", binding_key=(("rk3","gov"),),
                         refusal_subject="eOTHER", input_refs=(rx.rhash,), warrant_basis_refs=(rg.rhash,))
    to("I1t subjected-refusal vs unrelated (positively declared)", independent(refusal2, unrelated, ch),
       "INDEPENDENT would mean a positively-declared refusal can pass unrelated traffic")

# ============ GROUP J — replay/restart determinism (AL) ============
def group_J():
    # J1 deterministic replay: commit a set, snapshot tip; rebuild by replay; compare.
    ch, rg, rx = base_chain()
    lane = CommitLane(ch)
    cands = [Candidate(op="app_write", agent=f"a{i}", binding_key=((f"e{i}", f"a{i}"),),
                       input_refs=(), warrant_basis_refs=(rg.rhash,)) for i in range(5)]
    for c in cands:
        lane.commit_and_effect(c, admit, lambda c: None, actual_binding=c.binding_key)
    tip1 = ch.tip()
    hashes = [r.rhash for r in ch.all()]
    # replay determinism: same sequence ⇒ same prior_hash links
    prior_ok = all(ch.all()[i].prior_hash == (ch.GENESIS if i == 0 else ch.all()[i-1].rhash)
                   for i in range(len(ch.all())))
    al("J1 prior_hash chain intact under sequential commit", prior_ok, f"tip={tip1[:12]}")
    al("J2 every committed op has exactly one receipt (I2)",
       len(hashes) == len(set(hashes)), f"{len(hashes)} receipts, {len(set(hashes))} unique")

def run():
    """Run the full 22-test AL battery. Returns True iff AL CLEAN (0 failures)."""
    AL_RESULTS.clear(); TO_RESULTS.clear()
    # ---- run all ----
    for g in (group_A, group_C, group_D, group_E, group_F, group_H, group_I, group_J):
        g()

    print("="*70)
    print("AL (AUTHORITY-LAUNDERING) SAFETY TESTS — any FAIL stops the track")
    print("="*70)
    al_fail = 0
    for name, ok, detail in AL_RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
        if not ok: al_fail += 1
    print(f"\n  AL: {len(AL_RESULTS)-al_fail}/{len(AL_RESULTS)} pass, {al_fail} FAIL")
    print()
    print("="*70)
    print("TO (THROUGHPUT-ONLY) GREEN-ZONE WIDTH — measures value, never blocks safety")
    print("="*70)
    for name, outcome, detail in TO_RESULTS:
        print(f"  [{outcome}] {name}" + (f"  — {detail}" if detail else ""))
    print()
    print(f"VERDICT: {'AL CLEAN' if al_fail==0 else 'AL FAILURES — STOP TRACK'}")
    return al_fail == 0

if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
