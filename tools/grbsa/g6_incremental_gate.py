#!/usr/bin/env python3
"""g6_incremental_gate.py — UGK r135 focused self-test for the G6 checkpoint-aware verifier.

Proves that the r135 verification surface is NOT vacuous (a clean bundle PASSes; a byte-identical
continuity link HOLDs) and FAILS CLOSED on every adversarial mutation. This is certification
TOOLING (GRBSA-style, run directly), NOT a kernel/conformance invariant: it is not in any fixed
gate list and does not move the conformance gate count.

It exercises three layers with fully synthetic fixtures (no dependence on real release archives):

  A. bundle consumer (g6_bundle.verify_bundle) — pure, spawns nothing
     0  valid bundle                      -> PASS        (anti-vacuity)
     5  tampered section (not re-sealed)   -> FAIL        (integrity, req 5)
     6  missing GRBSA gate (re-sealed)     -> FAIL        (req 6)
     7  stale conformance count            -> FAIL        (req 7)
     8  stale expectation profile          -> FAIL        (req 8)
     9  stale hygiene verdict              -> FAIL        (req 9)
    10  missing/stale frontier             -> FAIL        (req 10)
    15u frontier UNFINISHED propagates     -> UNFINISHED  (req 15)
    15f frontier FAIL propagates           -> FAIL

  B. incremental frontier (g6_proof_cache) — synthetic attestation + archives
    H  byte-identical pair (shortcut S)    -> HOLD        (anti-vacuity)
    11 changed candidate identity          -> cache MISS  (forces recompute, req 11)
    11t tampered cache self-hash           -> cache MISS  (forces recompute)
    Ab archives absent                     -> UNFINISHED  (deferred to full-audit)
    Bx bounded budget exhausted            -> UNFINISHED  (never PASS/FAIL, req 15)
    12 genesis contamination in archive    -> detected    (req 12)
    16 full-audit timeout                  -> RESOURCE_TIMEOUT (req 16)

  C. no-spawn / no-contamination (real g6_aggregate_validation_gate.py CLI)
    NS G6 bounded consumer, poisoned gate stubs + sentinel in the extract
       -> PASS, sentinel never written, no genesis/ created (req 4 + req 13)

Usage:  g6_incremental_gate.py            (no args; self-contained)
Exit:   0 = PASS, 1 = FAIL
Final line: "GRBSA G6 INCREMENTAL SELF-TEST GATE: <PASS|FAIL>"
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import g6_bundle as gb           # noqa: E402
import g6_proof_cache as gpc     # noqa: E402
import proof_model_b as pmb      # noqa: E402

# Synthetic frame (NOT the live r134 frame; this gate proves mechanics, not the live values).
SYN_SHA = "a" * 64                       # stands in for the certified archive sha256
SYN_LAW = "1" * 64
SYN_SCHEMA = "2" * 64
SYN_LEGEND = "3" * 64
SYN_CODEX = "4" * 64
SYN_ADR = 55
SYN_REG = 82
LIVE_GATES = ["ugk.conformance.gate_alpha", "ugk.conformance.gate_beta", "ugk.conformance.gate_gamma"]


def _sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- layer A: synthetic bundle ----------------

def _frontier_receipt(verdict="HOLD", terminal_sha=SYN_SHA):
    return {
        "schema": gpc.FRONTIER_SCHEMA, "proof_model_version": gpc.PROOF_MODEL_VERSION,
        "verdict": verdict, "reasons": [],
        "attested": {"composed": "ContinuityChain[..] composed=HOLD", "n_links": 1,
                     "head_candidate": "syn-head.tar.gz", "head_candidate_sha256": "b" * 64},
        "frontier": [{"label": "syn->head", "verdict": verdict, "source": "recompute",
                      "identity": {"candidate_sha256": terminal_sha, "baseline_sha256": "b" * 64}}],
    }


def _valid_bundle(frontier_verdict="HOLD"):
    conf = gb.build_conformance(LIVE_GATES, "PASS")
    gates = gb.build_gates([{"name": g, "verdict": "PASS", "exit_code": 0} for g in gb.EXPECTED_GRBSA_GATES])
    mrs = gb.build_migration_receipts(
        [{"name": m, "present": True, "equivalent": True} for m in gb.EXPECTED_MIGRATION_RECEIPTS])
    ri = gb.build_registry_identity(law=SYN_LAW, schema=SYN_SCHEMA, legend=SYN_LEGEND,
                                    codex=SYN_CODEX, adr_count=SYN_ADR, registry_count=SYN_REG)
    hyg = gb.build_hygiene(archive_sha256=SYN_SHA, hygiene_verdict="PASS", nodrift_verdict="PASS")
    cf = gb.build_continuity_frontier(_frontier_receipt(frontier_verdict, SYN_SHA))
    return gb.assemble_bundle(release="syn-release", archive_sha256=SYN_SHA, conformance=conf,
                              gates=gates, migration_receipts=mrs, registry_identity=ri,
                              hygiene=hyg, continuity_frontier=cf)


def _expected_frame():
    return {"law": SYN_LAW, "schema": SYN_SCHEMA, "legend": SYN_LEGEND, "codex": SYN_CODEX,
            "adr_count": SYN_ADR, "registry_count": SYN_REG, "archive_sha256": SYN_SHA}


def _reseal(bundle, section_name):
    """Re-seal a mutated section + recompute the bundle hash (so the failure under test is the
    SEMANTIC check, not the integrity check)."""
    bundle["sections"][section_name] = gb.seal_section(bundle["sections"][section_name])
    bundle["bundle_hash"] = gb.compute_bundle_hash(bundle)
    return bundle


def _verify(bundle, workdir, tag):
    p = os.path.join(workdir, "bundle_%s.json" % tag)
    with open(p, "w") as f:
        json.dump(bundle, f)
    return gb.verify_bundle(p, live_gates=LIVE_GATES, expected_frame=_expected_frame())["verdict"]


def _layer_a(workdir, results):
    # 0 anti-vacuity: a clean bundle PASSes
    results.append(("A0-valid-bundle", _verify(_valid_bundle(), workdir, "valid"), "PASS"))

    # 5 integrity: edit a section field WITHOUT re-sealing -> FAIL
    b = _valid_bundle()
    b["sections"]["hygiene"]["hygiene_verdict"] = "FAIL"   # body changed, section_hash stale
    results.append(("A5-tamper-no-reseal", _verify(b, workdir, "tamper"), "FAIL"))

    # 6 missing GRBSA gate (re-sealed so integrity passes; semantic check must catch it)
    b = _valid_bundle()
    b["sections"]["gates"]["gates"] = b["sections"]["gates"]["gates"][:-1]   # drop one expected gate
    _reseal(b, "gates")
    results.append(("A6-missing-gate", _verify(b, workdir, "missgate"), "FAIL"))

    # 7 stale conformance count
    b = _valid_bundle()
    b["sections"]["conformance"]["count"] = len(LIVE_GATES) + 1
    _reseal(b, "conformance")
    results.append(("A7-stale-count", _verify(b, workdir, "count"), "FAIL"))

    # 8 stale expectation profile (gate-id set drift; count left correct on purpose)
    b = _valid_bundle()
    ids = list(b["sections"]["conformance"]["gate_ids"])
    ids[-1] = "ugk.conformance.gate_DELTA"               # same count, different profile
    b["sections"]["conformance"]["gate_ids"] = ids
    # leave the stored expectation_profile_hash as-is so it now mismatches the (drifted) ids AND live
    _reseal(b, "conformance")
    results.append(("A8-stale-profile", _verify(b, workdir, "profile"), "FAIL"))

    # 9 stale hygiene (re-sealed)
    b = _valid_bundle()
    b["sections"]["hygiene"]["hygiene_verdict"] = "FAIL"
    _reseal(b, "hygiene")
    results.append(("A9-stale-hygiene", _verify(b, workdir, "hyg"), "FAIL"))

    # 10 stale frontier: terminal candidate no longer pertains to the certified archive
    b = _valid_bundle()
    rec = b["sections"]["continuity_frontier"]["receipt"]
    rec["frontier"][-1]["identity"]["candidate_sha256"] = "f" * 64   # != SYN_SHA -> stale
    _reseal(b, "continuity_frontier")
    results.append(("A10-stale-frontier", _verify(b, workdir, "front"), "FAIL"))

    # 15u UNFINISHED frontier propagates to an UNFINISHED bundle (never silently PASS)
    results.append(("A15u-unfinished-prop", _verify(_valid_bundle("UNFINISHED"), workdir, "unf"), "UNFINISHED"))

    # 15f a non-HOLD/UNFINISHED frontier verdict propagates to FAIL
    results.append(("A15f-fail-prop", _verify(_valid_bundle("FAIL"), workdir, "ffail"), "FAIL"))


# ---------------- layer B: synthetic frontier fixtures ----------------

def _mk_archive(path, payload: bytes):
    """Write a tiny .tar.gz whose single member carries `payload` (content controls the sha256)."""
    with tarfile.open(path, "w:gz") as tf:
        data = payload
        ti = tarfile.TarInfo("payload.txt")
        ti.size = len(data)
        import io
        tf.addfile(ti, io.BytesIO(data))
    return path


def _frontier_fixture(archdir, base_payload, cand_payload):
    """Build a minimal attestation+surfaces pair that PASSES proof_model_b._verify_attestation:
    one attested HOLD link whose candidate sha == H, and one unattested frontier link 'b->c'
    whose baseline sha == H (chains to the attested head by content)."""
    base = _mk_archive(os.path.join(archdir, "b.tar.gz"), base_payload)
    cand = _mk_archive(os.path.join(archdir, "c.tar.gz"), cand_payload)
    h_base = _sha256_file(base)
    h_cand = _sha256_file(cand)
    attestation = {
        "composed": "ContinuityChain[r..] composed=HOLD",
        "links": [{"label": "a->b", "baseline": "a.tar.gz", "baseline_sha256": "0" * 64,
                   "candidate": "b.tar.gz", "candidate_sha256": h_base, "verdict": "HOLD"}],
    }
    surfaces = {"links": {
        "a->b": {"baseline": "a.tar.gz", "baseline_sha256": "0" * 64,
                 "candidate": "b.tar.gz", "candidate_sha256": h_base},
        "b->c": {"baseline": "b.tar.gz", "baseline_sha256": h_base,
                 "candidate": "c.tar.gz", "candidate_sha256": h_cand, "amendment_link": True},
    }}
    apath = os.path.join(archdir, "att.json")
    spath = os.path.join(archdir, "surf.json")
    json.dump(attestation, open(apath, "w"))
    json.dump(surfaces, open(spath, "w"))
    return apath, spath, h_base, h_cand


def _layer_b(workdir, results):
    # H anti-vacuity: a byte-IDENTICAL baseline/candidate pair -> shortcut S -> HOLD
    d = tempfile.mkdtemp(prefix="frontH-", dir=workdir)
    payload = b"identical-release-bytes-for-shortcut-S"
    apath, spath, h_base, h_cand = _frontier_fixture(d, payload, payload)   # identical content
    cache_path = os.path.join(d, "cache.json")
    r = gpc.verify_frontier(attestation_path=apath, surfaces_path=spath, archives_dir=d,
                            cache_path=cache_path, budget_s=120)
    results.append(("BH-shortcut-HOLD", r["verdict"], "HOLD"))

    # 11 changed candidate identity -> cache lookup MISSES (forces recompute). The HOLD run above
    # populated the cache for (b->c, h_base, h_cand). A changed candidate sha is a different key.
    cache = gpc.load_cache(cache_path)
    lbh = gpc.link_body_hash(json.load(open(spath))["links"]["b->c"])
    hit_same = gpc.cache_get(cache, "b->c", h_base, h_cand, lbh)
    hit_changed = gpc.cache_get(cache, "b->c", h_base, "e" * 64, lbh)   # candidate changed
    results.append(("B11-changed-cand-miss",
                    "MISS" if (hit_same is not None and hit_changed is None) else "HIT",
                    "MISS"))

    # 11t tampered cache self-hash -> rejected (recompute). Corrupt a stored verdict/legs in place.
    cache2 = gpc.load_cache(cache_path)
    key = next(iter(cache2["entries"]))
    cache2["entries"][key]["verdict"] = "FAIL"          # mutate without recomputing entry_hash
    e = cache2["entries"][key]
    tampered = gpc.cache_get(cache2, "b->c", e["baseline_sha256"], e["candidate_sha256"], e["link_body_hash"])
    results.append(("B11t-tampered-cache-miss", "MISS" if tampered is None else "HIT", "MISS"))

    # Ab archives absent -> UNFINISHED (recompute deferred to full-audit). Same fixture, empty dir.
    d2 = tempfile.mkdtemp(prefix="frontAb-", dir=workdir)
    a2, s2, _, _ = _frontier_fixture(d2, b"base-bytes", b"cand-bytes")
    empty = tempfile.mkdtemp(prefix="empty-", dir=workdir)   # no archives resolvable here
    r = gpc.verify_frontier(attestation_path=a2, surfaces_path=s2, archives_dir=empty,
                            cache_path=os.path.join(d2, "c.json"), budget_s=120)
    results.append(("BAb-archives-absent", r["verdict"], "UNFINISHED"))

    # Bx bounded budget exhausted -> UNFINISHED (never PASS/FAIL, req 15). Negative budget trips
    # the per-link budget gate on the first frontier link.
    d3 = tempfile.mkdtemp(prefix="frontBx-", dir=workdir)
    a3, s3, _, _ = _frontier_fixture(d3, b"xx", b"yy")
    r = gpc.verify_frontier(attestation_path=a3, surfaces_path=s3, archives_dir=d3,
                            cache_path=os.path.join(d3, "c.json"), budget_s=-1)
    results.append(("BBx-budget-UNFINISHED", r["verdict"], "UNFINISHED"))

    # 12 genesis contamination in an archive is DETECTED (read-only member-name scan)
    d4 = tempfile.mkdtemp(prefix="contam-", dir=workdir)
    contam_arch = os.path.join(d4, "poison.tar.gz")
    with tarfile.open(contam_arch, "w:gz") as tf:
        import io
        data = b"deadbeef"
        ti = tarfile.TarInfo("genesis/GENESIS_PRIVKEY.hex")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))
    clean_arch = _mk_archive(os.path.join(d4, "clean.tar.gz"), b"no-keys-here")
    offenders = gpc.archive_genesis_contamination(contam_arch)
    clean_off = gpc.archive_genesis_contamination(clean_arch)
    results.append(("B12-contam-detected",
                    "DETECTED" if (offenders and not clean_off) else "MISSED", "DETECTED"))

    # 16 full-audit timeout -> RESOURCE_TIMEOUT (reserved for full-audit; bounded never emits it).
    # A stub proof_model_b.py that sleeps past a tiny budget forces the bounded runner's 124 sentinel.
    d5 = tempfile.mkdtemp(prefix="fullaudit-", dir=workdir)
    stub_dir = os.path.join(d5, "tools", "grbsa")
    os.makedirs(stub_dir, exist_ok=True)
    with open(os.path.join(stub_dir, "proof_model_b.py"), "w") as f:
        f.write("import time\ntime.sleep(30)\nprint('CONTINUITY HOLDS')\n")
    r = gpc.full_audit(extract_dir=d5, archives_dir=d5, budget_s=1)
    results.append(("B16-fullaudit-timeout", r["verdict"], "RESOURCE_TIMEOUT"))


# ---------------- layer C: real G6 CLI, no-spawn / no-contamination ----------------

def _layer_c(workdir, results):
    """Run the REAL g6_aggregate_validation_gate.py in bounded consumer mode against a valid bundle
    and an extract whose GRBSA gate scripts are POISONED (exit 1 + write a sentinel). If G6 spawned
    the forest, the sentinel would appear and/or the verdict could not be PASS. We assert PASS, no
    sentinel, and no genesis/ directory created by G6 (req 4 + req 13)."""
    extract = tempfile.mkdtemp(prefix="nospawn-extract-", dir=workdir)
    # minimal live registry the consumer will import for expectation binding
    conf_pkg = os.path.join(extract, "ugk", "conformance")
    os.makedirs(conf_pkg, exist_ok=True)
    open(os.path.join(extract, "ugk", "__init__.py"), "w").close()
    open(os.path.join(conf_pkg, "__init__.py"), "w").close()
    with open(os.path.join(conf_pkg, "run_gates_batch.py"), "w") as f:
        f.write("GATES = %r\n" % LIVE_GATES)

    # poisoned GRBSA gate stubs: if EXECUTED they write the sentinel and exit 1
    sentinel = os.path.join(workdir, "POISON_SENTINEL")
    grbsa_dir = os.path.join(extract, "tools", "grbsa")
    os.makedirs(grbsa_dir, exist_ok=True)
    for g in gb.EXPECTED_GRBSA_GATES:
        with open(os.path.join(grbsa_dir, "%s.py" % g), "w") as f:
            f.write("import sys\nopen(%r, 'a').write('SPAWNED\\n')\nsys.exit(1)\n" % sentinel)

    # a valid bundle on disk
    bundle_path = os.path.join(workdir, "nospawn_bundle.json")
    with open(bundle_path, "w") as f:
        json.dump(_valid_bundle(), f)

    g6 = os.path.join(_HERE, "g6_aggregate_validation_gate.py")
    argv = [sys.executable, g6, "--bundle", bundle_path, "--extract", extract,
            "--expected-law", SYN_LAW, "--expected-schema", SYN_SCHEMA, "--expected-legend", SYN_LEGEND,
            "--expected-codex", SYN_CODEX, "--expected-adr-count", str(SYN_ADR),
            "--expected-registry-count", str(SYN_REG), "--expected-archive-sha256", SYN_SHA]
    env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
    verdict_pass = "GRBSA G6 AGGREGATE VALIDATION GATE: PASS" in proc.stdout and proc.returncode == 0
    sentinel_absent = not os.path.exists(sentinel)
    genesis_absent = not os.path.exists(os.path.join(extract, "genesis"))
    ok = verdict_pass and sentinel_absent and genesis_absent
    results.append(("C-no-spawn-no-contam",
                    "PASS" if ok else ("verdict=%s sentinel_absent=%s genesis_absent=%s"
                                       % (verdict_pass, sentinel_absent, genesis_absent)),
                    "PASS"))


# ---------------- driver ----------------

def main(argv):
    workdir = tempfile.mkdtemp(prefix="g6-selftest-")
    sys.dont_write_bytecode = True
    results = []
    try:
        _layer_a(workdir, results)
        _layer_b(workdir, results)
        _layer_c(workdir, results)
    finally:
        # leave nothing behind; this gate founds/writes nothing in the repo
        shutil.rmtree(workdir, ignore_errors=True)

    print("=" * 72)
    all_ok = True
    for case, got, expect in results:
        ok = (got == expect)
        all_ok = all_ok and ok
        print("  %-26s got=%-15s expect=%-15s %s" % (case, got, expect, "OK" if ok else "*FAIL*"))
    print("-" * 72)

    # explicit anti-vacuity: the gate must be able to say PASS on clean input AND distinguish a
    # broken one — otherwise a self-test that "passes everything" is meaningless.
    got = dict((c, g) for c, g, _ in results)
    vacuity_ok = (got.get("A0-valid-bundle") == "PASS"
                  and got.get("BH-shortcut-HOLD") == "HOLD"
                  and got.get("A5-tamper-no-reseal") == "FAIL")
    print("  anti-vacuity (clean PASS + HOLD reachable + tamper FAIL): %s" % ("OK" if vacuity_ok else "*FAIL*"))

    verdict = "PASS" if (all_ok and vacuity_ok) else "FAIL"
    print("=" * 72)
    print("GRBSA G6 INCREMENTAL SELF-TEST GATE: %s" % verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
