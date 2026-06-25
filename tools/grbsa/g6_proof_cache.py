#!/usr/bin/env python3
"""g6_proof_cache.py — checkpoint-aware continuity helper for the release-cert bundle (r135).

This module gives the release-cert orchestrator (and G6) an INCREMENTAL continuity verdict without the
full genesis->head re-derivation. It has three jobs:

  1. PER-LINK CACHE (fail-closed). A cache entry is reused ONLY when its full identity matches:
        (label, effective_baseline_sha256, effective_candidate_sha256, link_body_hash, proof_model_version)
     and its self-hash (which ALSO commits the B1-B4 verdict tuple) verifies. Any changed archive hash,
     changed link body, changed B1-B4 tuple, or changed proof-model version invalidates the entry and
     FORCES recompute. A corrupt/garbled cache is treated as empty (never trusted) — fail-closed.

  2. INCREMENTAL FRONTIER VERIFIER. Trust the rolling attestation checkpoint
     (CONTINUITY_ATTESTATION.json, verified internally consistent), then recompute ONLY the unattested
     frontier (links in continuity_surfaces.json not present in the attestation). Returns exactly one of:
        HOLD       — attestation valid AND every frontier link recomputes/cache-hits to HOLD
        FAIL       — attestation invalid/absent, a frontier link FAILs behaviourally, a chain break,
                     or genesis contamination in a frontier archive   (fail-closed)
        UNFINISHED — bounded mode could not behaviourally complete a frontier link (its archive(s)
                     absent) OR the time budget was exhausted. Never PASS, never a generic FAIL.

     STRICTER THAN proof_model_b's corpus-absent fallback BY DESIGN: that fallback returns HOLD on
     attestation + content-chaining alone; here content-chaining proves only ANCHORING of the frontier,
     not its BEHAVIOUR, so an unrecomputable frontier link is UNFINISHED (claim <= proof). The honest
     full re-derivation is full-audit.

  3. FULL-AUDIT HELPER (archival, NON-BLOCKING). Runs proof_model_b.py --full-audit under a bounded
     runner. On budget exhaustion it returns RESOURCE_TIMEOUT (reserved for full-audit — NEVER returned
     by the bounded incremental frontier, which returns UNFINISHED instead).

Expectation source: the frontier model is derived from the SHIPPED continuity_surfaces.json +
CONTINUITY_ATTESTATION.json (no second hardcoded universe of links).

This file and its on-disk cache (g6_proof_cache.json) are REGENERABLE build artifacts and MUST NOT
ship in a release archive — mint_release.sh excludes *g6_proof_cache.json.

CLI:
  g6_proof_cache.py --frontier --attestation A.json --surfaces S.json --archives DIR \
      [--cache F.json] [--emit OUT.json] [--budget SECONDS]
  g6_proof_cache.py --full-audit --extract EXTRACT_DIR --archives DIR [--budget SECONDS]

Exit codes: 0 HOLD · 1 FAIL · 3 UNFINISHED · 4 RESOURCE_TIMEOUT · 2 usage/error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import proof_model_b as pmb  # noqa: E402  — single source for evaluate_link / attestation / version

PROOF_MODEL_VERSION = pmb.PROOF_MODEL_VERSION
CACHE_SCHEMA = "ugk-g6-proof-cache/1"
FRONTIER_SCHEMA = "ugk-g6-frontier-receipt/1"
DEFAULT_CACHE = os.path.join(_HERE, "g6_proof_cache.json")
DEFAULT_BUDGET_S = 120          # bounded incremental budget
DEFAULT_FULL_AUDIT_BUDGET_S = 1500

# Genesis founding / key material that must NEVER be inside a shipped archive (req 12).
_GENESIS_RUNTIME = {"GENESIS_PRIVKEY.hex", "GENESIS_KEY.pub", "DEPLOYMENT_MANIFEST.json",
                    "LAUNCH_IC.json", "VALIDATOR_SET.json"}


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- link body hash ----------------

def link_body_hash(spec: dict) -> str:
    """Stable hash of the continuity link spec body. Any edit to the declared surfaces / archives /
    amendment flags changes this hash and (via cache identity) forces recompute."""
    return _sha256_bytes(_canon(spec).encode())


# ---------------- per-link fail-closed cache ----------------

def _identity(label, base_sha, cand_sha, lbh) -> dict:
    return {"label": label, "baseline_sha256": base_sha, "candidate_sha256": cand_sha,
            "link_body_hash": lbh, "proof_model_version": PROOF_MODEL_VERSION}


def _identity_key(ident: dict) -> str:
    return _canon([ident["label"], ident["baseline_sha256"], ident["candidate_sha256"],
                   ident["link_body_hash"], ident["proof_model_version"]])


def entry_hash(ident: dict, verdict: str, path: str, legs) -> str:
    """Self-hash committing identity + verdict + path + B1-B4 legs. Because the legs (B1-B4 tuple) are
    inside this hash, a tampered cached tuple breaks the self-hash and forces recompute (fail-closed)."""
    return _sha256_bytes(_canon({"identity": ident, "verdict": verdict, "path": path, "legs": legs}).encode())


def make_entry(label, base_sha, cand_sha, lbh, verdict, path, legs) -> dict:
    ident = _identity(label, base_sha, cand_sha, lbh)
    e = dict(ident)
    e.update({"verdict": verdict, "path": path, "legs": legs})
    e["entry_hash"] = entry_hash(ident, verdict, path, legs)
    return e


def load_cache(path: str) -> dict:
    """Load a cache file. A missing OR corrupt OR version-foreign cache returns an EMPTY cache
    (fail-closed: garbage is never trusted; everything recomputes)."""
    base = {"schema": CACHE_SCHEMA, "proof_model_version": PROOF_MODEL_VERSION, "entries": {}}
    if not path or not os.path.exists(path):
        return base
    try:
        d = json.load(open(path))
        if (d.get("schema") != CACHE_SCHEMA or d.get("proof_model_version") != PROOF_MODEL_VERSION
                or not isinstance(d.get("entries"), dict)):
            return base
        return d
    except Exception:
        return base


def save_cache(cache: dict, path: str) -> None:
    if not path:
        return
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cache, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def cache_get(cache: dict, label, base_sha, cand_sha, lbh):
    """Return a cached entry ONLY if identity matches AND its self-hash verifies. Else None (recompute).
    None on: missing entry, version drift, identity drift (changed archive sha / link body), or a
    tampered B1-B4 tuple / verdict (self-hash mismatch)."""
    ident = _identity(label, base_sha, cand_sha, lbh)
    e = cache.get("entries", {}).get(_identity_key(ident))
    if not e:
        return None
    # identity must match field-for-field (defensive; key already encodes it)
    for k, v in ident.items():
        if e.get(k) != v:
            return None
    if e.get("entry_hash") != entry_hash(ident, e.get("verdict"), e.get("path"), e.get("legs")):
        return None  # tampered / stale self-hash -> force recompute
    return e


def cache_put(cache: dict, entry: dict) -> None:
    ident = {k: entry[k] for k in ("label", "baseline_sha256", "candidate_sha256",
                                   "link_body_hash", "proof_model_version")}
    cache.setdefault("entries", {})[_identity_key(ident)] = entry


# ---------------- genesis contamination scan over an archive ----------------

def archive_genesis_contamination(archive_path: str) -> list:
    """Return offending member names if a release archive carries genesis founding / key material.
    Read-only: inspects tar member NAMES only, founds nothing (req 12 / req 13)."""
    bad = []
    try:
        with tarfile.open(archive_path, "r:*") as tf:
            for name in tf.getnames():
                parts = name.replace("\\", "/").split("/")
                if "genesis" in parts:
                    base = parts[-1]
                    if base in _GENESIS_RUNTIME or base.endswith(".hex"):
                        bad.append(name)
                elif parts[-1].startswith("GENESIS_PRIVKEY") or parts[-1].endswith(".hex"):
                    bad.append(name)
    except Exception as e:  # unreadable archive is itself fail-closed at the caller
        return ["<unreadable: %s>" % e]
    return sorted(set(bad))


# ---------------- incremental frontier verifier ----------------

def verify_frontier(*, attestation_path: str, surfaces_path: str, archives_dir: str,
                    cache_path: str | None = None, budget_s: float = DEFAULT_BUDGET_S,
                    recompute: bool = True) -> dict:
    """Verify the unattested continuity frontier incrementally. Returns a structured frontier receipt
    whose `verdict` is exactly one of HOLD / FAIL / UNFINISHED."""
    t0 = time.time()
    receipt = {"schema": FRONTIER_SCHEMA, "proof_model_version": PROOF_MODEL_VERSION,
               "verdict": "FAIL", "reasons": [], "attested": {}, "frontier": [],
               "budget_s": budget_s, "elapsed_s": None,
               "attestation_path": attestation_path, "surfaces_path": surfaces_path,
               "archives_dir": os.path.abspath(archives_dir) if archives_dir else None}

    def done(v):
        receipt["verdict"] = v
        receipt["elapsed_s"] = round(time.time() - t0, 2)
        return receipt

    # --- load surfaces + attestation (missing/corrupt -> FAIL, req 10) ---
    try:
        surf = json.load(open(surfaces_path))
        links = surf["links"]
    except Exception as e:
        receipt["reasons"].append("surfaces unreadable: %s" % e)
        return done("FAIL")
    if not os.path.exists(attestation_path):
        receipt["reasons"].append("attestation ABSENT (no rolling checkpoint to anchor the frontier)")
        return done("FAIL")
    try:
        att = json.load(open(attestation_path))
    except Exception as e:
        receipt["reasons"].append("attestation unreadable: %s" % e)
        return done("FAIL")

    composed = str(att.get("composed", ""))
    alinks = att.get("links", [])
    attested_labels = {a.get("label") for a in alinks}
    head = alinks[-1] if alinks else None
    receipt["attested"] = {"composed": composed, "n_links": len(alinks),
                           "head_candidate": (head or {}).get("candidate"),
                           "head_candidate_sha256": (head or {}).get("candidate_sha256")}
    if "HOLD" not in composed:
        receipt["reasons"].append("attestation composed verdict is not HOLD: %r" % composed)
        return done("FAIL")

    # --- attestation internal consistency (reuse proof_model_b._verify_attestation) ---
    # It checks: every attested verdict == HOLD; contiguous sha chain; and that each NON-attested
    # (current) link's baseline content-chains to the attested head. That is the rolling checkpoint.
    att_ok, att_lines = _verify_attestation_at(attestation_path, links)
    receipt["attested"]["consistency_lines"] = att_lines
    if not att_ok:
        receipt["reasons"].append("attestation failed internal-consistency / content-chaining")
        return done("FAIL")

    # --- frontier = links not yet attested ---
    frontier = [(lab, links[lab]) for lab in links if lab not in attested_labels]
    if not frontier:
        receipt["reasons"].append("no unattested frontier (attestation covers head) -> HOLD")
        return done("HOLD")

    cache = load_cache(cache_path) if cache_path else {"schema": CACHE_SCHEMA,
                                                       "proof_model_version": PROOF_MODEL_VERSION,
                                                       "entries": {}}
    index = pmb._content_index(archives_dir)
    any_unfinished = False
    any_fail = False

    for label, spec in frontier:
        item = {"label": label, "verdict": None, "source": None,
                "baseline": spec.get("baseline"), "candidate": spec.get("candidate")}
        # budget gate (bounded: timeout -> UNFINISHED, never PASS/FAIL — req 15)
        if time.time() - t0 > budget_s:
            item["verdict"] = "UNFINISHED"; item["source"] = "budget_exhausted"
            receipt["frontier"].append(item); any_unfinished = True
            receipt["reasons"].append("bounded budget exhausted before completing %s" % label)
            break

        base_arch = pmb._resolve_arch(archives_dir, spec.get("baseline_sha256"), spec.get("baseline"), index)
        cand_arch = pmb._resolve_arch(archives_dir, spec.get("candidate_sha256"), spec.get("candidate"), index)
        # effective shas come from actual bytes when resolvable (so a changed candidate forces recompute)
        eff_base = _sha256_file(base_arch) if base_arch and os.path.exists(base_arch) else spec.get("baseline_sha256")
        eff_cand = _sha256_file(cand_arch) if cand_arch and os.path.exists(cand_arch) else spec.get("candidate_sha256")
        lbh = link_body_hash(spec)
        item["identity"] = {"baseline_sha256": eff_base, "candidate_sha256": eff_cand,
                            "link_body_hash": lbh, "proof_model_version": PROOF_MODEL_VERSION}

        # 1) cache hit?
        hit = cache_get(cache, label, eff_base, eff_cand, lbh)
        if hit is not None:
            item["verdict"] = hit["verdict"]; item["source"] = "cache"; item["legs"] = hit.get("legs")
            item["path"] = hit.get("path")
            receipt["frontier"].append(item)
            if hit["verdict"] != "HOLD":
                any_fail = True
                receipt["reasons"].append("cached verdict for %s is %s" % (label, hit["verdict"]))
            continue

        # 2) behavioural recompute (needs both archives present)
        if not (recompute and base_arch and cand_arch and os.path.exists(base_arch) and os.path.exists(cand_arch)):
            item["verdict"] = "UNFINISHED"; item["source"] = "archives_absent"
            receipt["frontier"].append(item); any_unfinished = True
            receipt["reasons"].append(
                "%s: baseline/candidate archive absent — behavioural recompute deferred to full-audit" % label)
            continue

        # genesis contamination in a frontier archive is a real FAIL (req 12)
        contam = archive_genesis_contamination(cand_arch) + archive_genesis_contamination(base_arch)
        if contam:
            item["verdict"] = "FAIL"; item["source"] = "genesis_contamination"; item["contamination"] = contam[:10]
            receipt["frontier"].append(item); any_fail = True
            receipt["reasons"].append("%s: genesis/key contamination in archive: %s" % (label, contam[:5]))
            continue

        ok, path, _lines, legs = pmb.evaluate_link(label, spec, archives_dir, index)
        verdict = "HOLD" if ok else "FAIL"
        item["verdict"] = verdict; item["source"] = "recompute"; item["path"] = path; item["legs"] = legs
        receipt["frontier"].append(item)
        cache_put(cache, make_entry(label, eff_base, eff_cand, lbh, verdict, path, legs))
        if not ok:
            any_fail = True
            receipt["reasons"].append("%s: behavioural recompute FAILED (path=%s legs=%s)" % (label, path, legs))

    if cache_path:
        save_cache(cache, cache_path)

    # aggregate (fail-closed precedence: FAIL > UNFINISHED > HOLD)
    if any_fail:
        return done("FAIL")
    if any_unfinished:
        return done("UNFINISHED")
    return done("HOLD")


def _verify_attestation_at(attestation_path: str, links: dict):
    """Call proof_model_b._verify_attestation with ATTEST pointed at the given file (so the frontier
    verifier works on any attestation, including test fixtures), restoring it afterwards."""
    saved = pmb.ATTEST
    try:
        pmb.ATTEST = attestation_path
        return pmb._verify_attestation(links)
    finally:
        pmb.ATTEST = saved


# ---------------- full-audit helper (archival, non-blocking) ----------------

def full_audit(*, extract_dir: str, archives_dir: str, budget_s: float = DEFAULT_FULL_AUDIT_BUDGET_S) -> dict:
    """Run proof_model_b.py --full-audit (full genesis->head). NON-BLOCKING archival authority.
    Returns verdict in {HOLD, FAIL, RESOURCE_TIMEOUT}. RESOURCE_TIMEOUT is reserved for full-audit
    (req 16); the bounded incremental frontier never returns it."""
    t0 = time.time()
    pmb_path = os.path.join(extract_dir, "tools", "grbsa", "proof_model_b.py")
    env = dict(os.environ); env["PYTHONPATH"] = extract_dir; env["PYTHONDONTWRITEBYTECODE"] = "1"
    rc, out = pmb._bounded_run([sys.executable, pmb_path, "--full-audit", "--archives", os.path.abspath(archives_dir)],
                               env, cwd=extract_dir, timeout=budget_s)
    elapsed = round(time.time() - t0, 2)
    if rc == 124:  # bounded runner timeout sentinel
        verdict = "RESOURCE_TIMEOUT"
    elif rc == 0 and "CONTINUITY HOLDS" in out:
        verdict = "HOLD"
    else:
        verdict = "FAIL"
    return {"schema": "ugk-g6-full-audit/1", "verdict": verdict, "exit_code": rc,
            "elapsed_s": elapsed, "budget_s": budget_s, "blocking": False,
            "proof_model_version": PROOF_MODEL_VERSION}


# ---------------- CLI ----------------

_EXIT = {"HOLD": 0, "FAIL": 1, "UNFINISHED": 3, "RESOURCE_TIMEOUT": 4}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frontier", action="store_true")
    ap.add_argument("--full-audit", dest="full_audit", action="store_true")
    ap.add_argument("--attestation")
    ap.add_argument("--surfaces")
    ap.add_argument("--archives", required=True)
    ap.add_argument("--extract")
    ap.add_argument("--cache")
    ap.add_argument("--emit")
    ap.add_argument("--budget", type=float)
    args = ap.parse_args(argv)

    if args.frontier:
        if not (args.attestation and args.surfaces):
            print("usage: --frontier --attestation A.json --surfaces S.json --archives DIR"); return 2
        r = verify_frontier(attestation_path=args.attestation, surfaces_path=args.surfaces,
                            archives_dir=args.archives, cache_path=args.cache,
                            budget_s=args.budget or DEFAULT_BUDGET_S)
        if args.emit:
            json.dump(r, open(args.emit, "w"), indent=2)
        print("FRONTIER VERDICT: %s  (attested head=%s, frontier links=%d, elapsed=%ss)" % (
            r["verdict"], r["attested"].get("head_candidate"), len(r["frontier"]), r["elapsed_s"]))
        for it in r["frontier"]:
            print("  %-12s %-11s [%s]" % (it["label"], it["verdict"], it["source"]))
        for why in r["reasons"]:
            print("  · %s" % why)
        return _EXIT.get(r["verdict"], 1)

    if args.full_audit:
        if not args.extract:
            print("usage: --full-audit --extract DIR --archives DIR"); return 2
        r = full_audit(extract_dir=args.extract, archives_dir=args.archives,
                       budget_s=args.budget or DEFAULT_FULL_AUDIT_BUDGET_S)
        if args.emit:
            json.dump(r, open(args.emit, "w"), indent=2)
        print("FULL-AUDIT VERDICT: %s (exit=%s, elapsed=%ss, NON-BLOCKING)" % (r["verdict"], r["exit_code"], r["elapsed_s"]))
        return _EXIT.get(r["verdict"], 1)

    print("usage: g6_proof_cache.py (--frontier | --full-audit) ..."); return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
