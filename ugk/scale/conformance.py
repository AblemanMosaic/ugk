"""ugk.scale.conformance — scale-lane conformance gate (opt-in subsystem).

Proves the safety properties the scheduler MUST satisfy. This gate exists because an earlier
integration shipped a scheduler that sorted the whole batch by priority, letting a high-
priority DEPENDENT candidate overtake what it depends on. The decisive property:

  PRIORITY MAY NEVER CHANGE THE RELATIVE ORDER OF A DEPENDENT PAIR.

Priority is a tie-break ONLY among oracle-proven-independent candidates; submission order is
the floor across every dependency edge. This gate is NOT on the default path; it tests the
opt-in ugk.scale subsystem.

Run: python -m ugk.scale.conformance   (or import run() )
"""
from __future__ import annotations
import random
from ugk.scale.oracle import (
    Chain, Candidate, independent, INDEPENDENT, DEPENDENT, OracleRefusal,
)
from ugk.scale.scheduler import GovernedScheduler, prio

def _admit(c, chain):
    from ugk.scale.oracle import _posture_check
    try:
        _posture_check(c)
    except OracleRefusal:
        return False
    return True

def _base():
    ch = Chain()
    rg = ch.append(Candidate(op="authority_model_set", agent="gov", grant_class=True,
                             posture_affecting=True, binding_key=(("sys","gov"),)))
    seed = ch.append(Candidate(op="app_write", agent="gov", binding_key=(("s0","gov"),),
                               produces_effects=("s0",), input_refs=(rg.rhash,),
                               warrant_basis_refs=(rg.rhash,)))
    return ch, rg, seed

def run():
    results = []
    def chk(name, ok, detail=""):
        results.append((name, ok, detail))

    # --- G0: full 22-test AL (authority-laundering) battery must be CLEAN ---
    from ugk.scale.al_conformance import run as al_run
    import io, contextlib
    _buf = io.StringIO()
    with contextlib.redirect_stdout(_buf):
        al_clean = al_run()
    chk("G0 full AL battery (22 tests) CLEAN — no authority laundering", al_clean,
        "see ugk.scale.al_conformance for per-test detail")

    # --- G1: priority never reorders the Governor's dependent pair (refusal-of-target) ---
    ch, rg, seed = _base()
    target = Candidate(op="app_write", agent="x", binding_key=(("etgt","x"),),
                       produces_effects=("etgt",), input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
    refusal = Candidate(op="gate_refuse", agent="gov", binding_key=(("rr","gov"),),
                        refusal_subject="etgt", input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
    assert independent(refusal, target, ch) == DEPENDENT
    sched = GovernedScheduler(ch)
    order = [cid for cid,_ in sched.schedule([target, refusal], ["target","refusal"], _admit, lambda c: None)]
    chk("G1 dependent refusal does NOT overtake submitted-first target",
        order == ["target","refusal"], f"order={order}")

    # --- G2: randomized stress — dependent pair relative order PRESERVED across 200 batches ---
    reorder_viol = 0
    for trial in range(200):
        random.seed(trial)
        ch, rg, seed = _base()
        t = Candidate(op="app_write", agent="x", binding_key=(("etgt","x"),), produces_effects=("etgt",),
                      input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
        r = Candidate(op="gate_refuse", agent="gov", binding_key=(("rr","gov"),), refusal_subject="etgt",
                      input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
        noise = [Candidate(op="app_write", agent=f"n{i}", binding_key=((f"en{i}",f"n{i}"),),
                           produces_effects=(f"en{i}",), input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
                 for i in range(3)]
        items = [(t,"target"),(r,"refusal")] + [(noise[i],f"n{i}") for i in range(3)]
        random.shuffle(items)
        batch = [c for c,_ in items]; ids = [i for _,i in items]; sub = list(ids)
        order = [cid for cid,_ in GovernedScheduler(ch).schedule(batch, ids, _admit, lambda c: None)]
        if (sub.index("refusal")<sub.index("target")) != (order.index("refusal")<order.index("target")):
            reorder_viol += 1
    chk("G2 dependent relative order preserved over 200 randomized batches",
        reorder_viol == 0, f"violations={reorder_viol}/200")

    # --- G3: priority IS applied among independents (P2 ahead of P3 when independent) ---
    ch, rg, seed = _base()
    bulk = Candidate(op="bulk", agent="b", binding_key=(("eblk","b"),), produces_effects=("eblk",),
                     input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
    app = Candidate(op="app_write", agent="a", binding_key=(("eapp","a"),), produces_effects=("eapp",),
                    input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
    assert independent(bulk, app, ch) == INDEPENDENT
    order = [cid for cid,_ in GovernedScheduler(ch).schedule([bulk, app], ["bulk","app"], _admit, lambda c: None)]
    chk("G3 priority promotes independent P2 ahead of P3", order == ["app","bulk"], f"order={order}")

    # --- G4: priority does NOT reorder a DEPENDENT P2/P3 pair (shared binding) ---
    ch, rg, seed = _base()
    b2 = Candidate(op="bulk", agent="b", binding_key=(("esh","owner"),), produces_effects=("esh",),
                   input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
    a2 = Candidate(op="app_write", agent="a", binding_key=(("esh","owner"),),
                   input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,))
    assert independent(b2, a2, ch) == DEPENDENT
    order = [cid for cid,_ in GovernedScheduler(ch).schedule([b2, a2], ["bulk","app"], _admit, lambda c: None)]
    chk("G4 dependent P2/P3 pair keeps submission order (no priority reorder)",
        order == ["bulk","app"], f"order={order}")

    # --- G5: every committed op = exactly one receipt (I2); lane is sole minter (I7) ---
    ch, rg, seed = _base()
    pre = len(ch.all())
    cs = [Candidate(op="app_write", agent=f"s{i}", binding_key=((f"e{i}",f"s{i}"),), produces_effects=(f"e{i}",),
                    input_refs=(seed.rhash,), warrant_basis_refs=(rg.rhash,)) for i in range(4)]
    committed = GovernedScheduler(ch).schedule(cs, [f"C{i}" for i in range(4)], _admit, lambda c: None)
    rh = [r for _,r in committed]
    chk("G5 one receipt per committed op (I2)", len(ch.all())-pre==4 and len(set(rh))==4,
        f"grew={len(ch.all())-pre}, unique={len(set(rh))}")
    import inspect, ugk.scale.scheduler as S
    chk("G5 scheduler never appends directly (I7: lane sole minter)",
        "self.chain.append" not in inspect.getsource(S.GovernedScheduler), "")

    # report
    fails = [n for n,ok,_ in results if not ok]
    print("="*70)
    print("UGK SCALE CONFORMANCE GATE (opt-in subsystem; priority-vs-dependency safety)")
    print("="*70)
    for n,ok,d in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}" + (f"  — {d}" if d else ""))
    print(f"\n  {len(results)-len(fails)}/{len(results)} pass" + (f"  | FAIL: {fails}" if fails else ""))
    print("  VERDICT:", "ALL PASS" if not fails else "FAILURES — scale subsystem not sound")
    return len(fails) == 0

if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
