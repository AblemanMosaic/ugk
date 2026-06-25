"""verifier_gate — Phase-2 gate for the GRBSA in-process verifier.

Validates the verifier against the ten §8 criteria of the Phase-1 design note. GRBSA gate style:
run() -> (ok, detail); __main__ prints PASS/FAIL. NOT added to the ratified G1-G6 set or the
manifest (that would be a governance-surface change requiring separate authorization); this is a
standalone Phase-2 validation gate.
"""
from __future__ import annotations
import os, sys, glob, tempfile, hashlib, subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
for _p in (str(_REPO), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import verifier as V


def run():
    checks = []
    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # C1 Determinism — identical claim_id across runs.
    b1 = V.verify(); b2 = V.verify()
    check("C1 determinism: identical claim_id across runs",
          b1["claim_id"] == b2["claim_id"], b1["claim_id"][:16] + "...")

    # C2 Boundedness — default path spawns ZERO `python -m ugk.cli` cold-starts.
    import subprocess as _sp
    spawned = {"ugk_cli": 0}
    real_run, real_popen = _sp.run, _sp.Popen
    def _wrap(factory):
        def _w(cmd, *a, **k):
            try:
                flat = " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
                if "ugk.cli" in flat:
                    spawned["ugk_cli"] += 1
            except Exception:
                pass
            return factory(cmd, *a, **k)
        return _w
    _sp.run, _sp.Popen = _wrap(real_run), _wrap(real_popen)
    try:
        V.verify(run_smoke=False)
    finally:
        _sp.run, _sp.Popen = real_run, real_popen
    check("C2 boundedness: zero ugk.cli cold-starts on default path",
          spawned["ugk_cli"] == 0, f"ugk.cli spawns={spawned['ugk_cli']}")

    # C3 Isolation / non-contamination — real genesis/ unchanged; no repo-level chain db written.
    genesis = _REPO / "genesis"
    before = sorted(p.name for p in genesis.iterdir()) if genesis.exists() else []
    V.verify()
    after = sorted(p.name for p in genesis.iterdir()) if genesis.exists() else []
    no_hex = not any(n.endswith(".hex") for n in after)
    repo_dbs = glob.glob(str(_REPO / "**" / "*.db"), recursive=True)
    check("C3 isolation: genesis/ unchanged + no .hex + no repo chain db",
          before == after and no_hex and len(repo_dbs) == 0,
          f"genesis stable={before == after}, repo_dbs={len(repo_dbs)}")

    # C4 Seal-to-claim — content-addressed claim_id recomputable from claim_body.
    b = V.verify()
    recomputed = hashlib.sha256(V._canonical_json(b["claim_body"]).encode()).hexdigest()
    check("C4 seal-to-claim: claim_id is content-addressed hash of claim_body",
          recomputed == b["claim_id"], "match")

    # C5 Seal-and-discard — no temp residue leaks (grbsa_verifier_* temp dirs not accumulated).
    tdir = tempfile.gettempdir()
    n_before = len(glob.glob(os.path.join(tdir, "grbsa_verifier_*")))
    for _ in range(3):
        V.verify()
    n_after = len(glob.glob(os.path.join(tdir, "grbsa_verifier_*")))
    check("C5 seal-and-discard: no isolated-chain temp residue leaks",
          n_after <= n_before, f"temp dirs before={n_before} after={n_after}")

    # C6 Read-only fingerprint — schema_fingerprint does not mutate the target db.
    with tempfile.TemporaryDirectory() as td:
        from ugk.storage.store import UGKReceiptStore
        dbp = os.path.join(td, "ro.db")
        UGKReceiptStore(db_path=dbp).write(op="x", authority="a", parameters={})
        h0 = hashlib.sha256(open(dbp, "rb").read()).hexdigest()
        V.schema_fingerprint(dbp); V.schema_fingerprint(dbp)
        h1 = hashlib.sha256(open(dbp, "rb").read()).hexdigest()
    check("C6 read-only fingerprint: target db byte-unchanged", h0 == h1, "db bytes stable")

    # C7 Cold smoke-test — one cold start per unique verb; SEPARATE from default path.
    default_bundle = V.verify(run_smoke=False)
    smoke = V.cold_smoke_test()
    one_per_verb = len(smoke) == len(V.SMOKE_VERBS) and {v for v, _ in smoke} == set(V.SMOKE_VERBS)
    separate = "cold_smoke_test" not in default_bundle
    check("C7 cold smoke-test: one-per-verb AND separate from default path",
          one_per_verb and separate,
          f"verbs={[v for v,_ in smoke]} reach={[ok for _,ok in smoke]} separate={separate}")

    # C8 No real-chain writes — covered structurally by C3 (no repo db); assert verify() opened no
    #    store at the repo default location.
    default_store = _REPO / ".ugk"
    check("C8 no real-chain writes: repo default store not created",
          not default_store.exists(), f".ugk exists={default_store.exists()}")

    # C9 Boundary documented — bundle states D-5 / no-substrate-guarantee / not-production-act.
    note = V.verify()["boundary_note"].lower()
    check("C9 boundary documented: D-5 + no substrate guarantee + not production act",
          ("d-5" in note and "substrate" in note and "production governance act" in note),
          "note present")

    # C10 Evidence reproducibility — third party recomputes from bundle ALONE; tamper flips it.
    b = V.verify()
    ok_repro = V.third_party_recompute(b)
    tampered = dict(b); tampered["claim_body"] = dict(b["claim_body"]); \
        tampered["claim_body"]["schema_fingerprint"] = "TAMPERED"
    neg = not V.third_party_recompute(tampered)
    check("C10 evidence reproducibility: third-party recompute holds; tamper detected",
          ok_repro and neg, f"repro={ok_repro} tamper_detected={neg}")

    # C11 GRBSA verdict faithfulness — the verifier's receipt-derived verdict must AGREE with the
    #     canonical GRBSA forest status for the SAME archive. r135: G6 is no longer a standalone
    #     aggregate orchestrator, so the canonical GRBSA verdict is taken directly from the 9 leaf
    #     gates (all-PASS) rather than from the removed `g6_aggregate_validation_gate <repo> --r17a`.
    v_ok, _ = V.grbsa_attestation_verdict()
    r17a = os.environ.get("UGK_R17A_BASELINE")
    if r17a and os.path.exists(r17a):
        env = dict(os.environ); env["PYTHONPATH"] = str(_REPO) + ":" + str(_REPO / "tools" / "grbsa")
        _LEAF = ["g1_core_shape_gate", "g1_separation_symmetry_gate", "g2_substrate_naming_gate",
                 "g3_adapter_equivalence_gate", "g4a_adapter_generality_gate", "g4b_projection_adapter_gate",
                 "g4c_explain_adapter_gate", "category_separation_gate", "g5_execution_adapter_gate"]
        g6_ok = True
        for _g in _LEAF:
            _r = subprocess.run([sys.executable, "tools/grbsa/%s.py" % _g, str(_REPO)],
                                cwd=str(_REPO), env=env, capture_output=True, timeout=300)
            if _r.returncode != 0:
                g6_ok = False
        check("C11 verdict faithfulness: verifier verdict agrees with canonical GRBSA forest",
              v_ok == g6_ok, f"verifier={v_ok} grbsa_forest={g6_ok}")
    else:
        check("C11 verdict faithfulness: REQUIRES baseline (set UGK_R17A_BASELINE)",
              False, "baseline not provided — criterion 11 unverified (fail-closed)")

    passed = all(ok for _, ok, _ in checks)
    return passed, checks


if __name__ == "__main__":
    ok, checks = run()
    print("GRBSA Phase-2 VERIFIER GATE\n" + "=" * 60)
    for name, c, detail in checks:
        print(f"  {'PASS' if c else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print("=" * 60)
    print(f"VERIFIER GATE: {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)
