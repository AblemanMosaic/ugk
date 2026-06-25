#!/usr/bin/env python3
"""g6_bundle.py — release-cert bundle schema + PURE consumer verifier (r135).

THE BOUNDARY THIS FILE DRAWS
----------------------------
The release-cert orchestrator (tools/release/certify_release.py) is the only party that EXECUTES gates,
reads MigrationReceipts, runs hygiene/no-drift, and computes the incremental continuity frontier. It
records all of those outcomes into a single structured artifact: the release-cert BUNDLE.

This module owns:
  * the bundle SCHEMA (section builders + sealing/hashing), used by the orchestrator to ASSEMBLE a bundle;
  * verify_bundle(...), a PURE CONSUMER that reads a finished bundle and renders a verdict.

verify_bundle SPAWNS NOTHING. It runs no gate, founds no posture, opens no archive, touches no genesis.
It validates the bundle against (a) its own integrity hashes and (b) two EXTERNAL sources of truth that
are NOT derived from the bundle: the live conformance registry (ugk.conformance.run_gates_batch.GATES)
and the expected release frame. This is what lets G6 consume the bundle in bounded mode without becoming
an orchestrator again (req 4).

VERDICTS:  PASS · FAIL · UNFINISHED   (fail-closed precedence: FAIL > UNFINISHED > PASS)
  PASS        every section present + integral; conformance bound to live GATES; all GRBSA PASS;
              all MigrationReceipts equivalent; frame matches; hygiene/no-drift PASS; frontier HOLD.
  FAIL        any integrity break (tamper), missing/extra/stale section, GRBSA fail, receipt not
              equivalent, frame drift, hygiene/no-drift fail, missing/stale frontier, or frontier FAIL.
  UNFINISHED  bundle is otherwise clean but the continuity frontier is UNFINISHED (req 15: an
              unrecomputed frontier is never silently PASSed and never a generic FAIL).

NO SECOND HARDCODED UNIVERSE (req 5/7/8): conformance count, gate-id set, and expectation-profile hash
are all checked against the LIVE GATES list passed in by the caller. A bundle certified against a stale
gate universe fails closed.

This file is tooling; it ships. Its consumer posture (no execution) is the architectural fix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

BUNDLE_SCHEMA = "ugk-release-cert-bundle/1"

# Canonical section names; a bundle must carry exactly these (missing/extra -> FAIL).
SECTION_NAMES = ("conformance", "gates", "migration_receipts", "registry_identity",
                 "hygiene", "continuity_frontier")

# The 9 GRBSA leaf gates and 5 MigrationReceipts the orchestrator is expected to summarize.
# (Used only to check completeness of the recorded summaries — execution happens in the orchestrator.)
EXPECTED_GRBSA_GATES = ("g1_core_shape_gate", "g1_separation_symmetry_gate", "g2_substrate_naming_gate",
                        "g3_adapter_equivalence_gate", "g4a_adapter_generality_gate",
                        "g4b_projection_adapter_gate", "g4c_explain_adapter_gate",
                        "category_separation_gate", "g5_execution_adapter_gate")
EXPECTED_MIGRATION_RECEIPTS = ("migration_receipt_a1", "migration_receipt_determinism",
                               "migration_receipt_projection", "migration_receipt_explain",
                               "migration_receipt_execution")


# ---------------- hashing primitives ----------------

def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def section_hash(section: dict) -> str:
    """Hash a section over its content EXCLUDING its own section_hash field."""
    body = {k: v for k, v in section.items() if k != "section_hash"}
    return _sha256(_canon(body))


def seal_section(section: dict) -> dict:
    s = {k: v for k, v in section.items() if k != "section_hash"}
    s["section_hash"] = section_hash(s)
    return s


def compute_bundle_hash(bundle: dict) -> str:
    """Top-level hash binds the schema, release id, and every sealed section_hash. Editing any section
    body without re-sealing breaks that section_hash; re-sealing a section without recomputing the
    bundle_hash breaks this. Either way a post-hoc edit is caught (req 5)."""
    material = {
        "schema": bundle.get("schema"),
        "release": bundle.get("release"),
        "archive_sha256": bundle.get("archive_sha256"),
        "sections": {n: bundle.get("sections", {}).get(n, {}).get("section_hash")
                     for n in SECTION_NAMES},
    }
    return _sha256(_canon(material))


def expectation_profile_hash(gate_ids) -> str:
    """Stable hash of the conformance expectation profile = the sorted gate-id set."""
    return _sha256(_canon(sorted(gate_ids)))


# ---------------- section builders (used by the orchestrator) ----------------

def build_conformance(gate_ids, verdict: str) -> dict:
    gate_ids = list(gate_ids)
    return seal_section({
        "count": len(gate_ids),
        "gate_ids": gate_ids,
        "verdict": verdict,
        "expectation_profile_hash": expectation_profile_hash(gate_ids),
    })


def build_gates(results) -> dict:
    """results: iterable of {name, verdict, exit_code}. verdict expected 'PASS'/'FAIL'."""
    return seal_section({"gates": [
        {"name": r["name"], "verdict": r.get("verdict"), "exit_code": r.get("exit_code")}
        for r in results]})


def build_migration_receipts(results) -> dict:
    """results: iterable of {name, present, equivalent}."""
    return seal_section({"receipts": [
        {"name": r["name"], "present": bool(r.get("present")), "equivalent": r.get("equivalent")}
        for r in results]})


def build_registry_identity(*, law, schema, legend, codex, adr_count, registry_count) -> dict:
    return seal_section({"law": law, "schema": schema, "legend": legend, "codex": codex,
                         "adr_count": adr_count, "registry_count": registry_count})


def build_hygiene(*, archive_sha256, hygiene_verdict, nodrift_verdict) -> dict:
    return seal_section({"archive_sha256": archive_sha256,
                         "hygiene_verdict": hygiene_verdict,
                         "nodrift_verdict": nodrift_verdict})


def build_continuity_frontier(frontier_receipt: dict) -> dict:
    """Embed the frontier receipt produced by g6_proof_cache.verify_frontier. The section verdict is the
    receipt verdict (HOLD/FAIL/UNFINISHED)."""
    return seal_section({"verdict": frontier_receipt.get("verdict"),
                         "receipt": frontier_receipt})


def assemble_bundle(*, release, archive_sha256, conformance, gates, migration_receipts,
                    registry_identity, hygiene, continuity_frontier) -> dict:
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "release": release,
        "archive_sha256": archive_sha256,
        "sections": {
            "conformance": conformance,
            "gates": gates,
            "migration_receipts": migration_receipts,
            "registry_identity": registry_identity,
            "hygiene": hygiene,
            "continuity_frontier": continuity_frontier,
        },
    }
    bundle["bundle_hash"] = compute_bundle_hash(bundle)
    return bundle


# ---------------- pure consumer verifier ----------------

def verify_bundle(bundle_path: str, *, live_gates, expected_frame: dict) -> dict:
    """Render a verdict over a finished release-cert bundle. PURE: reads only the bundle file plus the
    two external truths passed in (live_gates list, expected_frame dict). Spawns nothing.

    expected_frame keys (all optional except where a comparison is desired):
        law, schema, legend, codex, adr_count, registry_count, archive_sha256
    """
    reasons = []
    fail = False
    unfinished = False

    def note(cond_ok, msg):
        nonlocal fail
        if not cond_ok:
            reasons.append(msg)
            fail = True
        return cond_ok

    # --- load ---
    try:
        bundle = json.load(open(bundle_path))
    except Exception as e:  # noqa: BLE001
        return {"verdict": "FAIL", "reasons": ["bundle unreadable: %s" % e]}

    if bundle.get("schema") != BUNDLE_SCHEMA:
        return {"verdict": "FAIL", "reasons": ["wrong bundle schema: %r" % bundle.get("schema")]}

    sections = bundle.get("sections", {})

    # --- 0. structural completeness: exactly the canonical sections ---
    have = set(sections)
    want = set(SECTION_NAMES)
    note(have == want, "section set mismatch: missing=%s extra=%s"
         % (sorted(want - have), sorted(have - want)))

    # --- 1. integrity: every section_hash recomputes; bundle_hash recomputes (tamper -> FAIL, req 5) ---
    for name in SECTION_NAMES:
        sec = sections.get(name)
        if not isinstance(sec, dict):
            note(False, "section %s missing/not-an-object" % name)
            continue
        if "section_hash" not in sec:
            note(False, "section %s missing section_hash" % name)
            continue
        note(sec["section_hash"] == section_hash(sec),
             "section %s integrity hash mismatch (tampered or unsealed)" % name)
    note(bundle.get("bundle_hash") == compute_bundle_hash(bundle),
         "bundle_hash mismatch (top-level tamper or stale section seal)")

    # If integrity is already broken, stop here — downstream field reads are not trustworthy.
    if fail:
        return {"verdict": "FAIL", "reasons": reasons, "release": bundle.get("release")}

    live_gates = list(live_gates)
    live_count = len(live_gates)
    live_profile = expectation_profile_hash(live_gates)

    # --- 2. conformance bound to LIVE GATES (req 7/8; no second universe) ---
    conf = sections["conformance"]
    note(conf.get("count") == live_count,
         "conformance count %s != live GATES %d (stale gate count)" % (conf.get("count"), live_count))
    note(set(conf.get("gate_ids", [])) == set(live_gates),
         "conformance gate-id set does not match live GATES registry")
    note(conf.get("expectation_profile_hash") == live_profile,
         "expectation profile hash drifted from live registry (stale expectation profile)")
    note(conf.get("verdict") == "PASS",
         "conformance verdict is not PASS: %r" % conf.get("verdict"))

    # --- 3. GRBSA gate summaries: all expected gates present + every verdict PASS (req 6) ---
    gate_recs = sections["gates"].get("gates", [])
    by_name = {g.get("name"): g for g in gate_recs}
    for g in EXPECTED_GRBSA_GATES:
        rec = by_name.get(g)
        if rec is None:
            note(False, "GRBSA gate summary missing: %s" % g)
            continue
        note(rec.get("verdict") == "PASS",
             "GRBSA gate %s verdict is %r (exit=%s)" % (g, rec.get("verdict"), rec.get("exit_code")))

    # --- 4. MigrationReceipts: all present + equivalent is true (req 6) ---
    mr_recs = sections["migration_receipts"].get("receipts", [])
    by_mr = {m.get("name"): m for m in mr_recs}
    for m in EXPECTED_MIGRATION_RECEIPTS:
        rec = by_mr.get(m)
        if rec is None:
            note(False, "MigrationReceipt summary missing: %s" % m)
            continue
        note(rec.get("present") is True, "MigrationReceipt %s not present" % m)
        note(rec.get("equivalent") is True,
             "MigrationReceipt %s equivalent != true: %r" % (m, rec.get("equivalent")))

    # --- 5. registry identity matches the expected frame ---
    ri = sections["registry_identity"]
    for key in ("law", "schema", "legend", "codex", "adr_count", "registry_count"):
        exp = expected_frame.get(key)
        if exp is None:
            continue
        note(ri.get(key) == exp, "registry %s drift: bundle=%r expected=%r" % (key, ri.get(key), exp))

    # --- 6. hygiene / no-drift (req 9) ---
    hyg = sections["hygiene"]
    note(hyg.get("hygiene_verdict") == "PASS",
         "hygiene verdict is not PASS: %r" % hyg.get("hygiene_verdict"))
    note(hyg.get("nodrift_verdict") == "PASS",
         "no-drift verdict is not PASS: %r" % hyg.get("nodrift_verdict"))
    expected_archive = expected_frame.get("archive_sha256") or bundle.get("archive_sha256")
    if expected_archive is not None:
        note(hyg.get("archive_sha256") == expected_archive,
             "hygiene archive sha %r != certified archive %r" % (hyg.get("archive_sha256"), expected_archive))

    # --- 7. continuity frontier (req 10/15): present, pertains to THIS archive, verdict propagates ---
    cf = sections["continuity_frontier"]
    receipt = cf.get("receipt") or {}
    fv = cf.get("verdict")
    note(fv == receipt.get("verdict"),
         "frontier section verdict %r disagrees with embedded receipt %r" % (fv, receipt.get("verdict")))

    # staleness: the frontier must cover the archive being certified.
    cert_sha = bundle.get("archive_sha256")
    frontier_links = receipt.get("frontier", [])
    attested = receipt.get("attested", {})
    if cert_sha is not None:
        if frontier_links:
            terminal = frontier_links[-1].get("identity", {}).get("candidate_sha256")
            note(terminal == cert_sha,
                 "frontier terminal candidate %r != certified archive %r (stale frontier)"
                 % (terminal, cert_sha))
        else:
            head = attested.get("head_candidate_sha256")
            note(head == cert_sha,
                 "no frontier and attested head %r != certified archive %r (stale frontier)"
                 % (head, cert_sha))

    # verdict propagation (only if no prior FAIL): HOLD->pass, UNFINISHED->unfinished, else FAIL
    if not fail:
        if fv == "HOLD":
            pass
        elif fv == "UNFINISHED":
            unfinished = True
            reasons.append("continuity frontier UNFINISHED (bounded recompute incomplete)")
        else:
            fail = True
            reasons.append("continuity frontier verdict is %r" % fv)

    verdict = "FAIL" if fail else ("UNFINISHED" if unfinished else "PASS")
    return {"verdict": verdict, "reasons": reasons, "release": bundle.get("release"),
            "archive_sha256": bundle.get("archive_sha256")}


# ---------------- CLI ----------------

def _load_live_gates(extract_dir):
    """Import the live GATES list from an extract WITHOUT founding anything (read-only registry read)."""
    import importlib
    sys.dont_write_bytecode = True
    saved = list(sys.path)
    try:
        if extract_dir not in sys.path:
            sys.path.insert(0, extract_dir)
        mod = importlib.import_module("ugk.conformance.run_gates_batch")
        return list(mod.GATES)
    finally:
        sys.path[:] = saved


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", required=True, metavar="BUNDLE.json")
    ap.add_argument("--extract", help="extract dir to import live GATES from (default: repo root of this file)")
    ap.add_argument("--expected-law")
    ap.add_argument("--expected-schema")
    ap.add_argument("--expected-legend")
    ap.add_argument("--expected-codex")
    ap.add_argument("--expected-adr-count", type=int)
    ap.add_argument("--expected-registry-count", type=int)
    ap.add_argument("--expected-archive-sha256")
    args = ap.parse_args(argv)

    extract = args.extract or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    try:
        live_gates = _load_live_gates(extract)
    except Exception as e:  # noqa: BLE001
        print("FATAL: could not load live GATES from %s: %s" % (extract, e))
        return 2

    expected = {"law": args.expected_law, "schema": args.expected_schema,
                "legend": args.expected_legend, "codex": args.expected_codex,
                "adr_count": args.expected_adr_count, "registry_count": args.expected_registry_count,
                "archive_sha256": args.expected_archive_sha256}
    r = verify_bundle(args.verify, live_gates=live_gates, expected_frame=expected)
    print("BUNDLE VERDICT: %s  (release=%s)" % (r["verdict"], r.get("release")))
    for why in r["reasons"]:
        print("  · %s" % why)
    return {"PASS": 0, "FAIL": 1, "UNFINISHED": 3}.get(r["verdict"], 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
