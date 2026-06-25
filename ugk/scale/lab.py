"""ugk.scale.lab — diagnostic workload laboratory for the opt-in scale subsystem.

Implements SCALE_WORKLOAD_LAB_DESIGN.md Parts 2-7:
  - 7 workload profiles (6 measured + 1 adversarial AL guard)
  - dependency-cause decomposition (WHY a pair is dependent), mirroring oracle order
  - declarability sweep (reorderable% vs provenance quality)
  - permanent AL guard (no TO numbers emitted unless AL-clean)
  - pre-committed pass/fail gate

North star: measure the CAUSE of seriality, not just the amount of parallelism.
Deterministic (seeded). Operates on the shipped ugk.scale oracle; demonstrates per-profile
earned-independence using positive, chain-verifiable declarations. Diagnostic only — does not
mutate substrate, does not run on the default path.
"""
from __future__ import annotations
import random, itertools
from ugk.scale.oracle import (
    Chain, Candidate, independent, INDEPENDENT, DEPENDENT, OracleRefusal,
    _is_barrier, _verified_input_refs, _verified_warrant, SAFETY_OPS,
)

SEED = 11

# ---- seeded chain with grants + referenceable seed effects ----
def seeded_chain(n_seed=24):
    ch = Chain()
    rg = ch.append(Candidate(op="authority_model_set", agent="gov", grant_class=True,
                             posture_affecting=True, binding_key=(("sys","gov"),)))
    seeds = []
    for i in range(n_seed):
        rs = ch.append(Candidate(op="app_write", agent="gov", binding_key=((f"seed{i}","gov"),),
                                 produces_effects=(f"seed{i}",), input_refs=(rg.rhash,),
                                 warrant_basis_refs=(rg.rhash,)))
        seeds.append(rs.rhash)
    return ch, rg, seeds

# ---- decomposer: mirror the oracle's short-circuit order to attribute the CAUSE ----
def dependency_cause(x: Candidate, y: Candidate, chain: Chain) -> str:
    """Return the FIRST dependency class that forces DEPENDENT, matching oracle order.
    Only called on pairs the oracle ruled DEPENDENT (or raised). Mirrors independent()."""
    for a, b in ((x, y), (y, x)):
        if a.is_aggregate and a.member_range:
            return "D7"
    if _is_barrier(x, chain) or _is_barrier(y, chain):
        # distinguish posture (D5) vs safety/refusal (D4) barrier
        for c in (x, y):
            if c.op in ({"authority_model_set","a1_posture_set","rho_posture_set","constitution_set"}) or c.posture_affecting is True:
                return "D5"
        return "D4"
    for a, b in ((x, y), (y, x)):
        if a.op in SAFETY_OPS and a.refusal_subject not in (None, "ALL_PENDING"):
            subj = a.refusal_subject
            if subj in b.produces_effects or subj in list(b.binding_key):
                return "D4"
    if set(x.binding_key) & set(y.binding_key):
        return "D3"
    if not x.binding_key or not y.binding_key:
        return "D3"
    if _verified_input_refs(x, chain) is None or _verified_input_refs(y, chain) is None:
        return "D1"
    xin, yin = _verified_input_refs(x, chain), _verified_input_refs(y, chain)
    if (set(y.produces_effects) & xin) or (set(x.produces_effects) & yin):
        return "D1"
    if _verified_warrant(x, chain) is None or _verified_warrant(y, chain) is None:
        return "D2"
    for a, b in ((x, y), (y, x)):
        if a.session_marker in ("open","close") and b.session == a.session:
            return "D6"
    # same agent+session reaching here without disjointness proof = D8 pressure
    if x.agent == y.agent and x.session == y.session and x.session is not None:
        return "D8"
    return "D8"  # residual catch (shouldn't reach if INDEPENDENT)

# ---- profile generators (shape fixed; declarability via p_input/p_warr params) ----
AGENTS = [f"svc{i}" for i in range(10)]
def make_profile(name):
    """Return a generator fn(p_input, p_warr) -> list[Candidate], shape fixed per profile."""
    def gen(p_input, p_warr, seeds, rg, n=180, *, shape):
        cands = []
        for k in range(n):
            same = shape["same_agent_session"]
            agent = "appA" if same else random.choice(AGENTS)
            session = "tx" if same else f"s{random.randint(0,40)}"
            # op mix: governance-heavy injects posture/refusal/session ops
            r = random.random()
            if shape.get("gov_rate",0) and r < shape["gov_rate"]:
                kind = random.choice(["a1_posture_set","gate_refuse","session_boundary"])
                if kind == "a1_posture_set":
                    cands.append(Candidate(op="a1_posture_set", agent="gov", posture_affecting=True,
                                           binding_key=((f"p{k}","gov"),), input_refs=(rg,),
                                           warrant_basis_refs=(rg,)))
                elif kind == "gate_refuse":
                    cands.append(Candidate(op="gate_refuse", agent="gov",
                                           binding_key=((f"r{k}","gov"),),
                                           refusal_subject="ALL_PENDING",  # unsubjected ⇒ barrier
                                           input_refs=(rg,), warrant_basis_refs=(rg,)))
                else:
                    cands.append(Candidate(op="app_write", agent=agent, session=session,
                                           session_marker=random.choice(["open","close"]),
                                           binding_key=((f"e{k}",agent),), input_refs=(rg,),
                                           warrant_basis_refs=(rg,)))
                continue
            # binding: contention requires FULL (effect,authority) match under a shared owner
            if random.random() < shape["shared_binding"]:
                binding = ((f"shared{random.randint(0,3)}","shared_owner"),)
            else:
                binding = ((f"e{k}",agent),)
            # provenance: positive input_refs reference seeds. BUT for a real same-agent
            # transaction, each step causally consumes the PRIOR step's effect — model that
            # genuine chaining (D1) rather than artificially-disjoint seeds.
            if same and cands and random.random() < 0.7:
                # consume the previous same-session step's produced effect (true causal chain)
                prev_eff = cands[-1].produces_effects[0] if cands[-1].produces_effects else None
                input_refs = (prev_eff,) if prev_eff else ((random.choice(seeds),) if random.random() < p_input else None)
            else:
                input_refs = (random.choice(seeds),) if random.random() < p_input else (
                    () if random.random() < 0.5 else None)
            warrant = (rg,) if random.random() < p_warr else None
            cands.append(Candidate(op="app_write", agent=agent, session=session,
                                   binding_key=binding, produces_effects=(binding[0][0],),
                                   input_refs=input_refs, warrant_basis_refs=warrant))
        return cands
    return gen

SHAPES = {
    "1_ideal_disjoint":        dict(same_agent_session=False, shared_binding=0.0,  gov_rate=0.0),
    "2_microservice":          dict(same_agent_session=False, shared_binding=0.05, gov_rate=0.0),
    "3_shared_contention":     dict(same_agent_session=False, shared_binding=0.55, gov_rate=0.0),
    "4_single_agent_tx":       dict(same_agent_session=True,  shared_binding=0.10, gov_rate=0.0),
    "5_governance_heavy":      dict(same_agent_session=False, shared_binding=0.05, gov_rate=0.30),
    "6_weak_provenance":       dict(same_agent_session=False, shared_binding=0.05, gov_rate=0.0),
}
# realistic declarability assumptions per profile (the "plausible" point for the gate)
REALISTIC_DECL = {
    "1_ideal_disjoint":     (0.99, 0.99),
    "2_microservice":       (0.90, 0.90),
    "3_shared_contention":  (0.85, 0.85),
    "4_single_agent_tx":    (0.70, 0.75),
    "5_governance_heavy":   (0.85, 0.85),
    "6_weak_provenance":    (0.20, 0.40),
}

def measure(cands, chain, sample=4000):
    pairs = list(itertools.combinations(range(len(cands)), 2)); random.shuffle(pairs)
    pairs = pairs[:sample]
    indep = 0; causes = {k:0 for k in ("D1","D2","D3","D4","D5","D6","D7","D8")}
    dep = refused = 0
    for i,j in pairs:
        try:
            v = independent(cands[i], cands[j], chain)
        except OracleRefusal:
            refused += 1; continue
        if v == INDEPENDENT: indep += 1
        else:
            dep += 1; causes[dependency_cause(cands[i], cands[j], chain)] += 1
    total = indep+dep+refused
    return indep, dep, refused, total, causes

# ---- AL guard (Part 5): must be clean before ANY TO numbers ----
def al_guard(chain, rg):
    checks = []
    # empty input_refs omitting real producer, same agent+session
    x = Candidate(op="app_write", agent="a", binding_key=(("egx","a"),), produces_effects=("egx",),
                  input_refs=(), warrant_basis_refs=(rg,))
    y = Candidate(op="app_write", agent="a", session="tx", binding_key=(("egy","a"),),
                  input_refs=(), warrant_basis_refs=(rg,))
    checks.append(independent(x,y,chain) == DEPENDENT)
    # narrowed-false refusal subject
    t = Candidate(op="app_write", agent="b", binding_key=(("et","b"),), produces_effects=("et",),
                  input_refs=(), warrant_basis_refs=(rg,))
    rf = Candidate(op="gate_refuse", agent="gov", binding_key=(("rk","gov"),),
                   refusal_subject="eUNRELATED", input_refs=(), warrant_basis_refs=(rg,))
    checks.append(independent(rf,t,chain) == DEPENDENT)
    # forged disjoint, same agent, real overlap
    q1 = Candidate(op="app_write", agent="c", session="tx", binding_key=(("eq","c"),),
                   input_refs=(), warrant_basis_refs=(rg,))
    q2 = Candidate(op="app_write", agent="c", session="tx", binding_key=(("eq","c"),),
                   input_refs=(), warrant_basis_refs=(rg,))
    checks.append(independent(q1,q2,chain) == DEPENDENT)
    # posture underdeclaration ⇒ refusal
    try:
        bad = Candidate(op="a1_posture_set", agent="gov", posture_affecting=False,
                        binding_key=(("p","gov"),))
        other = Candidate(op="app_write", agent="d", binding_key=(("eo","d"),),
                          input_refs=(), warrant_basis_refs=(rg,))
        independent(bad, other, chain); checks.append(False)  # should have raised
    except OracleRefusal:
        checks.append(True)
    return all(checks), checks

# ---- run lab ----
def run():
    ch, rg, seeds = seeded_chain()
    ok, checks = al_guard(ch, rg.rhash)
    print("="*78)
    print("SCALE WORKLOAD LAB — diagnostic + prescriptive (copy-only, v1 oracle)")
    print("="*78)
    print(f"AL GUARD: {'CLEAN' if ok else 'FAILED'}  checks={checks}")
    if not ok:
        print("\nAL FAILURE — halting. No TO numbers emitted on an unsound oracle.")
        return
    print()

    # Part 3+4: per-profile reorderable %, cause decomposition, at REALISTIC declarability
    print("PER-PROFILE @ realistic declarability  (reorderable% + dependency-cause distribution)")
    print("-"*78)
    gen = make_profile("x")
    profile_realistic = {}
    for name, shape in SHAPES.items():
        random.seed(SEED)
        pin, pwr = REALISTIC_DECL[name]
        cands = gen(pin, pwr, seeds, rg.rhash, shape=shape)
        indep, dep, refused, total, causes = measure(cands, ch)
        ip = 100*indep/total
        profile_realistic[name] = ip
        # top causes
        depc = {k:v for k,v in causes.items() if v}
        top = sorted(depc.items(), key=lambda kv:-kv[1])[:3]
        causestr = ", ".join(f"{k}:{100*v/max(dep,1):.0f}%" for k,v in top) if dep else "—"
        print(f"  {name:22} reorderable={ip:5.1f}%  decl=({pin},{pwr})  causes[{causestr}]")
    print()

    # Part 4: declarability sweep (reorderable% vs p_input=p_warr swept together)
    print("DECLARABILITY SWEEP  (reorderable% as provenance quality rises 0.0→1.0)")
    print("-"*78)
    sweep_pts = [0.0,0.2,0.4,0.6,0.8,1.0]
    print(f"  {'profile':22} " + " ".join(f"{p:>5.1f}" for p in sweep_pts) + "   curve")
    ceilings = {}
    for name, shape in SHAPES.items():
        row = []
        for p in sweep_pts:
            random.seed(SEED)
            cands = gen(p, p, seeds, rg.rhash, shape=shape)
            indep, dep, refused, total, _ = measure(cands, ch, sample=2500)
            row.append(100*indep/total)
        ceilings[name] = row[-1]  # safe-parallelism ceiling at declarability=1.0
        steep = row[-1]-row[0]
        shape_lbl = "STEEP" if steep>=30 else "flat" if steep<10 else "moderate"
        print(f"  {name:22} " + " ".join(f"{v:5.1f}" for v in row) + f"   {shape_lbl}(Δ{steep:.0f})")
    print()

    # Part 6: pre-committed gate verdict per profile
    print("PRE-COMMITTED GATE VERDICT")
    print("-"*78)
    realistic_profiles = [n for n in SHAPES if n != "1_ideal_disjoint"]
    any_justify = False
    for name in SHAPES:
        ip = profile_realistic[name]
        ceil = ceilings[name]
        # recompute steepness from sweep ends
        random.seed(SEED); c0 = gen(0.0,0.0,seeds,rg.rhash,shape=SHAPES[name])
        i0,_,_,t0,_ = measure(c0,ch,sample=2000)
        steep = ceil - 100*i0/t0
        if name == "1_ideal_disjoint":
            note = "(idealized — sanity ceiling, cannot justify scheduler alone)"
            verdict = "IDEAL-CEILING"
        elif ip >= 60:
            verdict = "JUSTIFY SCHEDULER (this profile)"; any_justify = True; note=""
        elif ceil >= 60 and steep >= 30:
            verdict = "IMPROVE DECLARABILITY FIRST"; note=f"(ceiling {ceil:.0f}%, steep Δ{steep:.0f})"
        elif ip < 25 and steep < 10:
            verdict = "PARK (structural seriality)"; note=f"(flat Δ{steep:.0f})"
        else:
            verdict = "MARGINAL — judgment required"; note=f"(ip {ip:.0f}%, ceiling {ceil:.0f}%, Δ{steep:.0f})"
        print(f"  {name:22} {verdict} {note}")
    print()
    print("OVERALL RECOMMENDATION")
    print("-"*78)
    if any_justify:
        js = [n for n in realistic_profiles if profile_realistic[n]>=60]
        print(f"  JUSTIFY SCHEDULER for realistic profile(s): {js}")
        print(f"  Scheduler/I5 design becomes justified FOR THOSE PROFILES only.")
    else:
        improvers = [n for n in realistic_profiles if ceilings[n]>=60]
        if improvers:
            print(f"  No realistic profile reaches 60% at plausible declarability, but {improvers}")
            print(f"  have high ceilings ⇒ IMPROVE DECLARABILITY FIRST before scheduler design.")
        else:
            print(f"  No realistic profile reaches 60% and ceilings are bounded ⇒ PARK scheduler design.")
            print(f"  Record scale as safe but not worth building yet.")

if __name__ == "__main__":
    run()
