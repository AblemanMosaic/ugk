"""grbsa verifier — in-process governed verifier (Phase 2, Track A).

Design: UGK_PHASE1_GRBSA_VERIFIER_DESIGN.md (rev r1). Ratified decisions:
  D-6 ephemeral verifier authority (self-verifying proof artifact, not a production governance act);
  D-7 anti-vacuity floor (required verdicts pass; required observations present).
Boundary (D-5 / 4.6): governs the CONFORMANCE CLAIM about the surface, not the verbs; promotes no
CR-04 site; mints nothing into the production chain; asserts NO substrate guarantee. The seal-and-
discard here is a LOCAL prototype (disposable chain), NOT the substrate epoch-seal (no B1 claim).
"""
from __future__ import annotations
import os, sys, io, json, hashlib, tempfile, shutil, importlib, contextlib, subprocess, secrets
from pathlib import Path

_HERE = Path(__file__).resolve().parent            # tools/grbsa
_REPO = _HERE.parent.parent                        # repo root
for _p in (str(_REPO), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from grbsa_runtime.gate_adapter import ReceiptCore, ResultEnvelopeCore
from grbsa_runtime.verification_adapter import (
    VerificationReceipt, VerificationResultEnvelope, verification_success,
)

# D-7 (refined, GOVLOG-5): the GRBSA aggregate verdict is derived from the canonical ATTESTATION
# artifacts for the target release — NOT by re-executing the GRBSA gates (which are release checks
# with invocation-context assumptions, not import-clean library functions). The verifier governs a
# conformance claim ABOUT the evidence artifacts; it is not a second release-gate runner.
EXPECTED_DOMAINS = ["a1", "determinism", "projection", "explain", "execution"]   # the 5 MigrationReceipts
EXPECTED_LAW_HASH = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"  # r17a lineage
# Unique verbs whose cold-start the legacy batch repeated; the cold smoke-test runs each ONCE.
# (A2: a full impl reads this set from run_gates_batch call sites; fixed here for the Phase-2 gate.)
SMOKE_VERBS = ["constitution", "health", "explain", "keygen"]


def _canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def compute_claim_hash(claim_body: dict) -> str:
    return hashlib.sha256(_canonical_json(claim_body).encode()).hexdigest()


def grbsa_attestation_verdict(repo_root=None):
    """C-fix (D-7 refined): derive the GRBSA verdict from canonical ATTESTATION artifacts, not by
    re-running gates. Deterministic, in-process (read JSON + one sha256), context-INDEPENDENT, and
    faithful to GRBSA's own architecture. Returns (ok, detail). Checks:
      present · valid JSON · evidence.equivalent==True (mirrors G6 §2, line 83) · domain-complete
      (all 5 expected) · tied to a target continuation · lineage-compatible (recomputed law_hash ==
      expected r17a lineage AND GRBSA_MANIFEST declares that lineage)."""
    repo_root = repo_root or str(_REPO)
    rt = os.path.join(repo_root, "tools", "grbsa", "grbsa_runtime")
    domains = {}
    for dom in EXPECTED_DOMAINS:
        path = os.path.join(rt, "migration_receipt_" + dom + ".json")
        present = os.path.exists(path)
        valid = equiv = False
        cont = None
        if present:
            try:
                d = json.load(open(path)); valid = True
                equiv = (d.get("evidence", {}).get("equivalent", None) is True)   # mirror G6 §2
                cont = d.get("to_continuation")
            except Exception:
                valid = False
        domains[dom] = {"present": present, "valid_json": valid,
                        "equivalent": equiv, "tied_to_continuation": bool(cont)}
    domain_complete = set(domains.keys()) == set(EXPECTED_DOMAINS)
    all_present = all(v["present"] for v in domains.values())
    all_valid   = all(v["valid_json"] for v in domains.values())
    all_equiv   = all(v["equivalent"] for v in domains.values())
    all_tied    = all(v["tied_to_continuation"] for v in domains.values())
    # lineage: recomputed law_hash must match the expected r17a lineage AND the manifest declaration.
    try:
        law_hash = hashlib.sha256(
            open(os.path.join(repo_root, "ugk", "invariants.py"), "rb").read()).hexdigest()
    except Exception:
        law_hash = ""
    try:
        mtext = open(os.path.join(repo_root, "tools", "grbsa", "GRBSA_MANIFEST.md")).read()
        manifest_declares = (EXPECTED_LAW_HASH in mtext) and ("r17a" in mtext)
    except Exception:
        manifest_declares = False
    lineage_ok = (law_hash == EXPECTED_LAW_HASH) and manifest_declares
    ok = all_present and all_valid and all_equiv and domain_complete and all_tied and lineage_ok
    detail = {
        "domains": {k: domains[k] for k in sorted(domains)},
        "domain_complete": domain_complete,
        "all_equivalent": all_equiv,
        "all_tied_to_continuation": all_tied,
        "law_hash": law_hash,
        "lineage_ok": lineage_ok,
    }
    return ok, detail


def schema_fingerprint(db_path: str):
    """Read-only schema_hash over PRAGMA table_info for each table (D-7 observation; criterion 6).
    Observe-and-report only: no refuse-on-mismatch, no writes."""
    import sqlite3
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) if os.path.exists(db_path) \
        else sqlite3.connect(db_path)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        shape = {}
        for t in tables:
            cols = con.execute(f"PRAGMA table_info('{t}')").fetchall()
            shape[t] = [[c[1], c[2]] for c in cols]      # [name, type]
    finally:
        con.close()
    return hashlib.sha256(_canonical_json(shape).encode()).hexdigest(), True


def cold_smoke_test(verbs=None, repo_root=None) -> list:
    """SEPARATE artifact-integrity check (criterion 7): one COLD `python -m ugk.cli <verb> --help`
    per unique verb. Proves entry-point / argparse REACHABILITY only — NOT gate logic, NOT full CLI
    coverage. This DOES spawn (by design); it is NOT the bounded default path."""
    verbs = verbs or SMOKE_VERBS
    repo_root = repo_root or str(_REPO)
    env = dict(os.environ); env["PYTHONPATH"] = repo_root
    out = []
    for v in verbs:
        try:
            p = subprocess.run([sys.executable, "-m", "ugk.cli", v, "--help"],
                               cwd=repo_root, env=env, capture_output=True, timeout=60)
            out.append((v, p.returncode == 0))
        except Exception:
            out.append((v, False))
    return out


def verify(*, run_smoke: bool = False) -> dict:
    """Default in-process verification. Mints into an ISOLATED, disposable store (the chain), seals a
    content-addressed conformance claim, then DISCARDS the per-check detail (seal-and-discard).
    Returns a SELF-CONTAINED bundle (criterion 10: third party recomputes claim_id from it alone).
    Spawns NO ugk.cli on this path (criterion 2)."""
    from ugk.storage.store import UGKReceiptStore

    tmp = tempfile.mkdtemp(prefix="grbsa_verifier_")
    iso_db = os.path.join(tmp, "verifier_chain.db")
    authority_ref = "ephemeral:verifier:" + secrets.token_hex(8)   # D-6: ephemeral, a ref not a value
    store = None
    try:
        store = UGKReceiptStore(db_path=iso_db)

        attest_ok, attest_detail = grbsa_attestation_verdict()
        verdicts = [("grbsa_attestation", attest_ok)]

        # per-domain attestation receipts into the isolated (disposable) chain
        for dom in sorted(attest_detail["domains"]):
            store.write(op="verify_attestation", authority=authority_ref,
                        parameters={"domain": dom, "equivalent": attest_detail["domains"][dom]["equivalent"]},
                        intent="verification")

        fp, present = schema_fingerprint(iso_db)        # observation over the isolated chain's schema
        observations = [("schema_fingerprint", present)]

        # content-addressed claim body — fully self-contained for third-party recompute (criterion 10).
        # NB: the random authority_ref is deliberately EXCLUDED so claim_id is deterministic (criterion 1).
        # Verdict source is the canonical ATTESTATION SET (receipts + lineage), not gate re-execution,
        # so the body is CONTEXT-INDEPENDENT (the prior determinism defect is removed at the source).
        claim_body = {
            "domain": "verification",
            "required_verdicts": sorted([[n, bool(o)] for n, o in verdicts]),
            "required_observations": sorted([[n, bool(p)] for n, p in observations]),
            "grbsa_attestation": attest_detail,
            "schema_fingerprint": fp,
            "authority_kind": "ephemeral",
        }
        claim_id = compute_claim_hash(claim_body)

        # seal the claim into the isolated chain (one governed claim-receipt; modeled on posture --seal)
        store.write(op="verification_claim", authority=authority_ref,
                    parameters={"claim_id": claim_id}, intent="verification_seal")

        rc = ReceiptCore(proposal={"op": "verify"}, criteria=("D7-anti-vacuity",),
                         evaluation=(("anti_vacuity", "applied"),),
                         authority={"kind": "ephemeral", "ref": authority_ref},
                         outcome="admitted",
                         lineage={"chain": "isolated", "sealed_claim": claim_id})
        rec = VerificationReceipt(core=rc, claim_id=claim_id,
                                  authority_ref=authority_ref, outcome="admitted")
        evc = ResultEnvelopeCore(status="pass" if attest_ok else "fail",
                                 evidence_refs=tuple("attest:" + d for d in sorted(attest_detail["domains"]))
                                               + ("grbsa_lineage", "schema_fingerprint"),
                                 timing={}, result_hash=claim_id, lineage={"sealed_claim": claim_id})
        env = VerificationResultEnvelope(core=evc, claim_id=claim_id,
                                         required_verdicts=tuple(verdicts),
                                         required_observations=tuple(observations))
        success = verification_success(rec, env)

        bundle = {
            "claim_id": claim_id,
            "claim_body": claim_body,
            "success": success,
            "evidence_refs": list(evc.evidence_refs),
            "authority_kind": "ephemeral",
            "boundary_note": ("self-verifying proof artifact; not a production governance act (D-6); "
                              "verbs remain CR-04 remainders, claim is ABOUT them not OVER them (D-5); "
                              "no CR-04 promotion (4.6); no substrate guarantee; seal-and-discard is a "
                              "LOCAL prototype, not the substrate epoch-seal (no B1 claim)."),
        }
        if run_smoke:
            bundle["cold_smoke_test"] = [[v, ok] for v, ok in cold_smoke_test()]
        return bundle
    finally:
        # seal-and-discard: drop per-check detail with the isolated chain (criterion 5)
        try:
            close = getattr(store, "close", None)
            if callable(close):
                close()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


def third_party_recompute(bundle: dict) -> bool:
    """Criterion 10: an independent party recomputes claim_id from the retained bundle ALONE."""
    return compute_claim_hash(bundle["claim_body"]) == bundle["claim_id"]


if __name__ == "__main__":
    b = verify(run_smoke=("--smoke" in sys.argv))
    print(json.dumps(b, indent=2))
