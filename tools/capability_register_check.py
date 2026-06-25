#!/usr/bin/env python3
"""A3 capability-register consistency check (classification only; ships in archive).

Mechanically verifies that the load-bearing classifications in docs/CAPABILITY_REGISTER.md match
the substrate code. A CONTRADICTION is any site whose implementation does not match its declared
kind. Run from repo root:  python3 tools/capability_register_check.py   (expects PASS, exit 0).
"""
import os, sys, inspect
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO = str(Path(__file__).resolve().parent.parent); sys.path.insert(0, REPO)

results = []
def check(site, kind, ok, detail=""):
    results.append((site, ok)); print("  %s  [%-22s %-10s] %s%s" %
        ("PASS" if ok else "CONTRADICTION", site, kind, "ok" if ok else "MISMATCH", (" — " + detail) if detail else ""))

import ugk.schema as schema
import ugk.kernel as kernel
from ugk.storage.store import UGKReceiptStore, compute_schema_hash, validate_migration_statement

# --- declared remainders (rows 1-4) ---
cr = getattr(kernel, "CLASSIFIED_REMAINDERS", [])
check("CR-01..04", "remainder", len(cr) == 4 and all(("CR-0%d:" % i) in " ".join(cr) for i in (1, 2, 3, 4)),
      "%d declared" % len(cr))

# --- governance op tiers (rows 18-20) ---
check("_KERNEL_OPS", "governance", set(schema._KERNEL_OPS) == {"gate_admit", "gate_refuse"}, str(sorted(schema._KERNEL_OPS)))
check("authority_model_set", "governance",
      "authority_model_set" in schema._APPLICATION_OPS and "authority_model_set" in schema.GOVERNANCE_OPS)
check("_UNIVERSAL_OPS", "governance", set(schema._UNIVERSAL_OPS) <= set(schema.GOVERNANCE_OPS) and len(schema._UNIVERSAL_OPS) >= 1,
      "%d universal ops in GOVERNANCE_OPS" % len(schema._UNIVERSAL_OPS))

# --- CRITICAL cross-check: schema_migrated is PROVENANCE, NOT a governance op (row 15 vs 16/18-20) ---
check("schema_migrated", "provenance",
      "schema_migrated" not in schema.GOVERNANCE_OPS and "schema_migrated" not in schema._KERNEL_OPS,
      "absent from GOVERNANCE_OPS/_KERNEL_OPS (provenance, not governance)")

# --- migration behavior: provenance receipt + refuse-before-mutation, NOT gate/refuse via execute (row 15) ---
s = UGKReceiptStore(":memory:")
intent_required = False
try: s.migrate_schema("CREATE TABLE t_ok (id INTEGER)", intent="")
except ValueError: intent_required = True
unsafe_refused = validate_migration_statement("ALTER TABLE receipts ADD COLUMN x TEXT NOT NULL") is not None
before = compute_schema_hash(s._conn)
res = s.migrate_schema("ALTER TABLE receipts ADD COLUMN _a3probe TEXT", intent="a3 register check")
emitted = any("schema_migrated" == str(v) for r in s._conn.execute("SELECT * FROM receipts").fetchall() for v in r)
check("migrate_schema", "provenance",
      intent_required and unsafe_refused and emitted and res["schema_hash_before"] != res["schema_hash_after"],
      "intent-required=%s unsafe-refused=%s receipt=%s" % (intent_required, unsafe_refused, emitted))

# --- observation/claim sites are read-only (rows 5-10): no receipt emitted by reading ---
s2 = UGKReceiptStore(":memory:")
n0 = s2._conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
_ = s2.schema_hash(); _ = s2.schema_frame_intact()
n1 = s2._conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
check("schema_hash/frame_intact", "claim", n0 == n1, "read-only (no receipt on read)")
check("kernel inspection verbs", "observation",
      all(hasattr(kernel.GovernanceKernel, m) for m in ("status", "snapshot", "snapshot_fast")),
      "status/snapshot/snapshot_fast present")

# --- seal surfaces present (rows 21-23) + capability attenuation (row 17) ---
check("seal_* surfaces", "governance",
      all(hasattr(UGKReceiptStore, m) for m in ("seal_legend", "seal_scope", "seal_authority_model")))
try:
    from ugk.authority.capabilities import attenuates, compute_effective_capabilities
    cap_ok = attenuates({"a"}, {"a"}) and not attenuates({"a"}, {"a", "b"})
except Exception as e:
    cap_ok = False
check("capability attenuation", "governance", cap_ok, "child⊆parent enforced")

# --- claim artifacts present (rows 13-14): verifier + Proof Model B ---
check("ContinuityB / verifier", "claim",
      os.path.exists(os.path.join(REPO, "tools", "grbsa", "proof_model_b.py")) and
      os.path.exists(os.path.join(REPO, "tools", "grbsa", "verifier.py")),
      "proof_model_b.py + verifier.py present")

# --- B1 epoch sites (rows 24-27) ---
check("epoch_sealed/epoch_pruned", "provenance",
      "epoch_sealed" not in schema.GOVERNANCE_OPS and "epoch_pruned" not in schema.GOVERNANCE_OPS,
      "storage-frame provenance, not governance ops")
sb = UGKReceiptStore(":memory:")
for i in range(4): sb.write(op="test_checkpoint", authority="cli", parameters={"i": i})
Sb = sb.all_receipts()[1].h_r            # RT-3 (r80): seal anchor re-anchored to M2 h_r
b1_intent = False
try: sb.seal_and_prune_epoch(Sb, intent="")
except ValueError: b1_intent = True
res_b1 = sb.seal_and_prune_epoch(Sb, intent="register check")
check("seal_and_prune_epoch", "governance",
      b1_intent and res_b1["tip_after_prune"] == res_b1["tip_before_prune"] and sb.verify_from_seal(Sb),
      "intent-required + tip-preserved + verify_from_seal")
n_before = len(sb.all_receipts()); _ = sb.verify_from_seal(Sb); n_after = len(sb.all_receipts())
check("verify_from_seal", "claim", n_before == n_after, "read-only")

contradictions = [s for s, ok in results if not ok]
print("\nCAPABILITY REGISTER CONSISTENCY:", "PASS — NO CONTRADICTIONS" if not contradictions
      else "CONTRADICTIONS: " + ", ".join(contradictions))
sys.exit(0 if not contradictions else 1)
