#!/usr/bin/env python3
"""B5 + B5a conformance gate (ships in the canonical archive).

B5  — authority-model --set is a governed, receipted, refusable op (ungoverned rewrite removed).
B5a — the active authority model is attached at the CLI boundary so Tier-2 governed ops actually
      enforce the declared posture (CM-S-02/03), which was dormant before B5a.

Run from the repo root:  python3 tools/b5a_conformance.py   (expects all PASS, exit 0)
Founds isolated deployments via the sanctioned governor-key test injection (see
ugk/conformance/governor_key_unset_gate.py for the same pattern).
"""
import os, sys, ast, re, tempfile, sqlite3, hashlib
from pathlib import Path
from types import SimpleNamespace

REPO = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, REPO)
EXPECTED_LAW_HASH = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"

results = []
def check(n, ok, d=""):
    results.append((n, bool(ok), d))
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))

import ugk.kernel as kmod
import ugk.schema as schema
from ugk.vendor.ed25519 import generate_keypair
from ugk.charter import DeploymentManifest, write_charter_artifacts
from ugk.storage.store import UGKReceiptStore
from ugk import cli

def receipts(db):
    con = sqlite3.connect(db)
    try: return con.execute("SELECT * FROM receipts").fetchall()
    finally: con.close()
def mentions(db, s):
    return sum(1 for r in receipts(db) if any(s in str(v) for v in r))
def found(model_id, pub):
    tmp = tempfile.mkdtemp(); g = str(Path(tmp) / "genesis")
    os.environ["UGK_STATE_DIR"] = tmp; os.environ["UGK_GENESIS_DIR"] = g
    write_charter_artifacts(DeploymentManifest.create(pub, "b5a-test", "session", model_id),
                            genesis_dir=g, force=True)
    return tmp, g

_priv, pub = generate_keypair()
_orig = kmod.GOVERNOR_PUBKEY_HEX
try:
    kmod.GOVERNOR_PUBKEY_HEX = pub

    # --- B5 carry-forward (static): ungoverned rewrite removed; routed; op declared ---
    src = open(os.path.join(REPO, "ugk", "cli.py")).read()
    f = next(n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.FunctionDef) and n.name == "_cmd_authority_model")
    fsrc = ast.get_source_segment(src, f)
    check("B5 routed through execute(op=authority_model_set); ungoverned rewrite removed",
          "authority_model_set" in fsrc and re.search(r"\.execute\(", fsrc) is not None
          and len(re.findall(r"write_charter_artifacts\(new_m", fsrc)) == 1
          and len(re.findall(r"effect=\(lambda: write_charter_artifacts\(new_m", fsrc)) == 1)
    check("B5 authority_model_set declared in GOVERNANCE_OPS", "authority_model_set" in schema.GOVERNANCE_OPS)

    # --- B5a-1: _make_kernel attaches the active model ---
    tmp, g = found("alt_trace", pub)
    k = cli._make_kernel(tmp)
    check("B5a-1 _make_kernel attaches active model",
          k._authority_model is not None and k._authority_model.model_id == "alt_trace",
          f"model={getattr(k._authority_model,'model_id',None)}")

    # --- B5a-2: govern & authority_model_set share the same construction path with the model ---
    k2 = cli._make_kernel(tmp)
    check("B5a-2 shared _make_kernel path carries the active model (govern + authority_model_set)",
          k2._authority_model is not None and k2._authority_model.model_id == "alt_trace")

    # --- determinism: model_hash stable across constructions (timestamp bound to manifest) ---
    check("B5a determinism: model_hash stable across _make_kernel calls",
          k._authority_model.model_hash == k2._authority_model.model_hash,
          k._authority_model.model_hash[:16] + "...")

    # --- B5a-3: stricter model, missing required warrant => REFUSED (fail-closed) ---
    rc = cli._cmd_authority_model(SimpleNamespace(
        set_model="trace_only", intent="attempt change under alt_trace",
        format="text", state_dir=tmp, authority="cli"))
    still = DeploymentManifest.load().authority_model
    check("B5a-3 stricter model: change missing required warrant is REFUSED (no effect)",
          rc != 0 and still == "alt_trace", f"rc={rc} model_still={still}")

    # --- B5a-4: gate-False refusal => gate_refuse receipt + no effect ---
    from ugk.kernel import GateRefusal, GovernanceKernel, EffectAtomicity
    rdb = str(Path(tmp) / "refuse.db")
    kk = GovernanceKernel(store=UGKReceiptStore(db_path=rdb), authority="cli")
    kk._ceremony(); kk.open_session()
    before = DeploymentManifest.load().authority_model
    refused = False
    try:
        kk.execute(op="authority_model_set", authority="cli", parameters={"intent": ""},
                   gate=(lambda: False),
                   effect=(lambda: write_charter_artifacts(
                       DeploymentManifest.create(pub, "x", "session", "alt_prevention"),
                       genesis_dir=g, force=True)), effect_atomicity=EffectAtomicity.NON_ATOMIC)
    except GateRefusal:
        refused = True
    after = DeploymentManifest.load().authority_model
    check("B5a-4 gate-False refusal: GateRefusal + gate_refuse receipt + no effect",
          refused and before == after and mentions(rdb, "gate_refuse") >= 1,
          f"refused={refused} {before}=={after} gate_refuse={mentions(rdb,'gate_refuse')}")

    # --- B5a-5: show/read-only path remains an unreceipted observation ---
    tmp2, g2 = found("trace_only", pub)
    db2 = str(Path(tmp2) / "ugk.db")
    cli._cmd_authority_model(SimpleNamespace(set_model="alt_trace", intent="prime",
                                             format="text", state_dir=tmp2, authority="cli"))
    n0 = len(receipts(db2))
    rcs = cli._cmd_authority_model(SimpleNamespace(set_model=None, intent=None,
                                                   format="text", state_dir=tmp2))
    n1 = len(receipts(db2))
    check("B5a-5 show/read-only path emits no receipt (observation preserved)",
          rcs == 0 and n1 == n0, f"rc={rcs} {n0}->{n1}")

    # --- regression: under trace_only the governed change still works ---
    tmp3, g3 = found("trace_only", pub)
    rcok = cli._cmd_authority_model(SimpleNamespace(set_model="alt_trace",
        intent="regression check", format="text", state_dir=tmp3, authority="cli"))
    check("regression: under trace_only, governed posture change still admitted",
          rcok == 0 and DeploymentManifest.load().authority_model == "alt_trace", f"rc={rcok}")
finally:
    kmod.GOVERNOR_PUBKEY_HEX = _orig

# --- B5a-6: law_hash unchanged ---
lh = hashlib.sha256(open(os.path.join(REPO, "ugk", "invariants.py"), "rb").read()).hexdigest()
check("B5a-6 law_hash unchanged (invariants.py untouched)", lh == EXPECTED_LAW_HASH, lh[:16] + "...")

ok_all = all(ok for _, ok, _ in results)
print("\nB5+B5a CONFORMANCE GATE:", "PASS" if ok_all else "FAIL")
sys.exit(0 if ok_all else 1)
