#!/usr/bin/env python3
"""GRBSA G6 — Aggregate Validation Gate (r135: bundle consumer).

ARCHITECTURE (r135). G6 is NO LONGER an orchestrator. The recurring bounded-environment hang and the
duplicate-orchestration problem are fixed by making G6 a CONSUMER:

  * In bounded certification mode G6 validates the release-cert BUNDLE produced by
    tools/release/certify_release.py. It SPAWNS NO gate forest, FOUNDS NO posture, and CREATES NO
    genesis/ contamination. The 9 GRBSA leaf gates, 5 MigrationReceipts, the conformance suite,
    hygiene / no-drift, and the continuity frontier are all EXECUTED BY THE ORCHESTRATOR and recorded
    into the bundle; G6 reads their recorded summaries and cross-checks them against the LIVE GATES
    registry and the expected release frame (g6_bundle.verify_bundle).

  * The heavy genesis->head continuity re-derivation is no longer part of the release-cert substrate.
    It survives ONLY as an explicit, NON-BLOCKING archival full-audit (--full-audit), delegated to
    g6_proof_cache.full_audit -> proof_model_b.py --full-audit. It never blocks a release by itself.

Modes:
  --bundle BUNDLE.json --extract DIR        BOUNDED CONSUMER (default cert posture).
                                            Verdict: PASS / FAIL / UNFINISHED.
  --full-audit --extract DIR --archives DIR ARCHIVAL continuity full-audit, NON-BLOCKING.
                                            Verdict: HOLD / FAIL / RESOURCE_TIMEOUT.

Called with neither mode -> FAIL-CLOSED refusal (G6 will not silently orchestrate — req 4).

Exit codes:  PASS/HOLD 0 · FAIL 1 · usage 2 · UNFINISHED 3 · RESOURCE_TIMEOUT 4.
"""
import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import g6_bundle          # noqa: E402  — bundle schema + pure consumer verifier
import g6_proof_cache     # noqa: E402  — incremental frontier + full-audit helper

# Canonical r134/r135 frame (frame-stationary lane: these are UNMOVED). Overridable via CLI so the
# orchestrator can pass the frame it certified against; defaults let G6 run standalone on the head.
DEFAULT_LAW = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"
DEFAULT_SCHEMA = "82d02279c39d5fa82d6bb18a2a12b0f85cc5210a93502d827a9f89c570327c99"
DEFAULT_LEGEND = "db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7"
DEFAULT_CODEX = "a67dba4106273a8c96018e2ed70f2e2987d3ea6669484094017bf51601ecddb5"
DEFAULT_ADR_COUNT = 55
DEFAULT_REGISTRY_COUNT = 82

# genesis founding / private-key material that must NEVER appear in a shipped extract (req 12/13).
_GENESIS_RUNTIME = {"GENESIS_PRIVKEY.hex", "GENESIS_KEY.pub", "DEPLOYMENT_MANIFEST.json",
                    "LAUNCH_IC.json", "VALIDATOR_SET.json"}


def scan_extract_contamination(extract):
    """READ-ONLY walk of the extract for genesis founding / private-key material. Founds nothing,
    writes nothing — G6 itself can never create contamination (req 13) while still detecting it (req 12)."""
    bad = []
    for dp, _, fs in os.walk(extract):
        if "__pycache__" in dp:
            continue
        for f in fs:
            rel = os.path.relpath(os.path.join(dp, f), extract)
            parts = rel.replace("\\", "/").split("/")
            if "genesis" in parts and (f in _GENESIS_RUNTIME or f.endswith(".hex")):
                bad.append(rel)
            elif f.startswith("GENESIS_PRIVKEY") or f.endswith(".hex"):
                bad.append(rel)
    return sorted(set(bad))


def _load_live_gates(extract):
    import importlib
    saved = list(sys.path)
    try:
        if extract and extract not in sys.path:
            sys.path.insert(0, extract)
        return list(importlib.import_module("ugk.conformance.run_gates_batch").GATES)
    finally:
        sys.path[:] = saved


def run_bounded(bundle_path, extract, expected_frame):
    print("  G6 mode: BOUNDED BUNDLE CONSUMER (no gate-forest spawn, no founding, no genesis write)")
    if not bundle_path or not os.path.exists(bundle_path):
        print("  FAIL  bundle not found: %r" % bundle_path)
        return "FAIL"
    # req 12/13: read-only contamination scan of the extract (the archive under certification).
    if extract:
        contam = scan_extract_contamination(extract)
        if contam:
            print("  FAIL  genesis/key contamination in extract: %s" % contam[:5])
            return "FAIL"
        print("  contamination scan: clean (%s)" % extract)
    # bind expectations to the LIVE registry (no second hardcoded universe).
    live = _load_live_gates(extract or os.path.join(_HERE, "..", ".."))
    r = g6_bundle.verify_bundle(bundle_path, live_gates=live, expected_frame=expected_frame)
    for why in r["reasons"]:
        print("  · %s" % why)
    print("  bundle verdict: %s  (release=%s, live_gates=%d)" % (r["verdict"], r.get("release"), len(live)))
    return r["verdict"]


def run_full_audit(extract, archives, budget):
    print("  G6 mode: ARCHIVAL FULL-AUDIT (NON-BLOCKING; continuity-only; no gate forest)")
    r = g6_proof_cache.full_audit(extract_dir=extract, archives_dir=archives, budget_s=budget)
    print("  full-audit verdict: %s (exit=%s, elapsed=%ss, blocking=%s)"
          % (r["verdict"], r["exit_code"], r["elapsed_s"], r["blocking"]))
    return r["verdict"]


_EXIT = {"PASS": 0, "HOLD": 0, "FAIL": 1, "UNFINISHED": 3, "RESOURCE_TIMEOUT": 4}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle")
    ap.add_argument("--extract")
    ap.add_argument("--full-audit", dest="full_audit", action="store_true")
    ap.add_argument("--archives")
    ap.add_argument("--budget", type=float, default=g6_proof_cache.DEFAULT_FULL_AUDIT_BUDGET_S)
    ap.add_argument("--expected-law", default=DEFAULT_LAW)
    ap.add_argument("--expected-schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--expected-legend", default=DEFAULT_LEGEND)
    ap.add_argument("--expected-codex", default=DEFAULT_CODEX)
    ap.add_argument("--expected-adr-count", type=int, default=DEFAULT_ADR_COUNT)
    ap.add_argument("--expected-registry-count", type=int, default=DEFAULT_REGISTRY_COUNT)
    ap.add_argument("--expected-archive-sha256", default=None)
    args = ap.parse_args(argv)

    print("=" * 64)
    print(" GRBSA G6 — Aggregate Validation Gate (r135 bundle consumer)")
    print("=" * 64)

    if args.full_audit:
        if not (args.extract and args.archives):
            print("usage: --full-audit --extract DIR --archives DIR")
            return 2
        verdict = run_full_audit(args.extract, args.archives, args.budget)
        print("\n  GRBSA G6 FULL-AUDIT: " + verdict)
        return _EXIT.get(verdict, 1)

    if args.bundle:
        expected_frame = {"law": args.expected_law, "schema": args.expected_schema,
                          "legend": args.expected_legend, "codex": args.expected_codex,
                          "adr_count": args.expected_adr_count,
                          "registry_count": args.expected_registry_count,
                          "archive_sha256": args.expected_archive_sha256}
        verdict = run_bounded(args.bundle, args.extract, expected_frame)
        print("\n  GRBSA G6 AGGREGATE VALIDATION GATE: " + verdict)
        return _EXIT.get(verdict, 1)

    # fail-closed: G6 will not silently orchestrate a gate forest (req 4).
    print("  REFUSAL  G6 is a bundle consumer. Provide --bundle BUNDLE.json --extract DIR for bounded")
    print("           release-cert verification, or --full-audit --extract DIR --archives DIR for the")
    print("           non-blocking archival continuity audit. G6 no longer spawns the GRBSA/conformance")
    print("           gate forest (the orchestrator certify_release.py owns gate execution).")
    print("\n  GRBSA G6 AGGREGATE VALIDATION GATE: FAIL")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
