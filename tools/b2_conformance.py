#!/usr/bin/env python3
"""B2 conformance gate — governed storage-frame schema migration (Option 3; ships in archive).

Proves:
 1. bootstrap vs live distinction (bootstrap = construction-only; live = migrate_schema);
 2. migration emits an intent-bearing before/after schema_hash receipt;
 3. post-construction schema mutation cannot occur via an unreceipted raw ALTER path
    (intent required; migration always receipts; the only ALTER sites are bootstrap + governed);
 4. startup schema fingerprint remains observe-only and does not refuse;
 5. law_hash and legend_hash unchanged;
 6. EXPECTED_SCHEMA_HASH remains the release anchor (not moved by a migration);
 7. a migrated deployment reports drift from the anchor AND carries a migration receipt explaining it.

Run from repo root:  python3 tools/b2_conformance.py   (expects all PASS, exit 0)
"""
import os, sys, ast, hashlib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, REPO)
EXPECTED_LAW_HASH = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"
EXPECTED_LEGEND_HASH = "db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7"

results = []
def check(n, ok, d=""):
    results.append((n, bool(ok), d)); print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))

from ugk.storage.store import UGKReceiptStore, EXPECTED_SCHEMA_HASH, compute_schema_hash

# ---------- 1 + 3 (static): ALTER sites confined to bootstrap + governed; bootstrap is construction-only ----------
src = open(os.path.join(REPO, "ugk", "storage", "store.py"), encoding="utf-8", errors="replace").read()
tree = ast.parse(src)
store = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "UGKReceiptStore")
M = {m.name: m for m in store.body if isinstance(m, ast.FunctionDef)}
def execute_arg_kinds():
    """Classify each method's self._conn.execute(...) calls by first-arg kind:
    literal ALTER (hardcoded structure mutation) vs dynamic (variable/passed SQL)."""
    literal_alter, dynamic = set(), set()
    for name, fn in M.items():
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "execute" and node.args):
                a0 = node.args[0]
                lit = None
                if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                    lit = a0.value
                elif isinstance(a0, ast.JoinedStr):
                    lit = " ".join(v.value for v in a0.values
                                   if isinstance(v, ast.Constant) and isinstance(v.value, str))
                if lit is not None:
                    if "ALTER TABLE" in lit.upper():
                        literal_alter.add(name)
                else:
                    dynamic.add(name)  # executes a non-literal (variable) statement
    return literal_alter, dynamic
literal_alter, dynamic = execute_arg_kinds()
check("B2-3 only hardcoded-ALTER literal site is bootstrap (_migrate_m2_schema)",
      literal_alter == {"_migrate_m2_schema"}, str(sorted(literal_alter)))
check("B2-3 dynamic-SQL execution confined to bootstrap-construction (__init__) + governed migrate_schema",
      dynamic <= {"migrate_schema", "__init__"}, str(sorted(dynamic)))
callers = [n for n in ast.walk(store) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "_migrate_m2_schema"]
ilo, ihi = M["__init__"].lineno, M["__init__"].end_lineno
check("B2-1 bootstrap (_migrate_m2_schema) is construction-only; migrate_schema is the live path",
      len(callers) == 1 and ilo <= callers[0].lineno <= ihi and "migrate_schema" in M)

# ---------- 3 (runtime): intent required (fail-closed) ----------
s = UGKReceiptStore(":memory:")
refused = False
try:
    s.migrate_schema("ALTER TABLE receipts ADD COLUMN _x TEXT", intent="")
except ValueError:
    refused = True
check("B2-3 migration without explicit intent is refused (fail-closed)", refused)

# ---------- PERMANENT NEGATIVE CONTROL: the exact r47 failure class ----------
# `ALTER TABLE receipts ADD COLUMN x TEXT NOT NULL` committed schema drift before the
# migration receipt existed in r47. It must now be refused BEFORE any mutation, leaving the
# receipt store fully intact: schema, receipt count, AND chain verification all unchanged.
R47_CLASS = "ALTER TABLE receipts ADD COLUMN x TEXT NOT NULL"
sN = UGKReceiptStore(":memory:")
sN.write(op="seed", authority="cli", parameters={})       # non-empty chain to verify against
live0 = compute_schema_hash(sN._conn)
cnt0  = sN._conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
ver0  = sN.verify_stream_hash()
tip0  = sN.stream_hash()
neg_refused = False
try:
    sN.migrate_schema(R47_CLASS, intent="attempt receipt-breaking migration")
except ValueError:
    neg_refused = True
live1 = compute_schema_hash(sN._conn)
cnt1  = sN._conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
ver1  = sN.verify_stream_hash()
tip1  = sN.stream_hash()
check("B2-NEG[r47] receipt-breaking migration refused BEFORE mutation", neg_refused)
check("B2-NEG[r47] schema_hash unchanged", live0 == live1 and sN.schema_frame_intact() is True)
check("B2-NEG[r47] receipt count unchanged", cnt0 == cnt1, f"{cnt0}->{cnt1}")
check("B2-NEG[r47] chain verification unchanged", ver0 is True and ver1 is True and tip0 == tip1)
# Supplementary: other dangerous forms are likewise refused before mutation, each zero-drift:
extra = []
for bad in ["DROP TABLE receipts", "DELETE FROM receipts", "UPDATE receipts SET op='x'",
            "ALTER TABLE receipts RENAME TO old", "ALTER TABLE receipts DROP COLUMN op",
            "PRAGMA journal_mode=WAL", "ALTER TABLE receipts ADD COLUMN a TEXT; DROP TABLE receipts"]:
    h = compute_schema_hash(sN._conn)
    try:
        sN.migrate_schema(bad, intent="probe"); ok = False           # should not reach here
    except ValueError:
        ok = compute_schema_hash(sN._conn) == h                      # refused, zero drift
    extra.append((bad, ok))
check("B2-NEG DROP/DML/RENAME/DROP-COLUMN/PRAGMA/multi-statement all refused before mutation, zero drift",
      all(ok for _, ok in extra) and sN.verify_stream_hash(), str([b[:24] for b, ok in extra if not ok]))

# ---------- 2 + 7: migration emits intent-bearing before/after receipt; drift carries explanation ----------
s2 = UGKReceiptStore(":memory:")
before_live = s2.schema_hash()
res = s2.migrate_schema("ALTER TABLE receipts ADD COLUMN _b2_probe TEXT",
                        intent="b2 test: add probe column", description="conformance migration")
moved = res["schema_hash_before"] != res["schema_hash_after"]
# find the schema_migrated receipt in the chain and confirm it carries intent + both hashes
rows = s2._conn.execute("SELECT * FROM receipts").fetchall()
mig_rows = [r for r in rows if any("schema_migrated" == str(v) for v in r)]
mig_text = " ".join(str(v) for r in mig_rows for v in r)
receipt_ok = (len(mig_rows) == 1
              and res["schema_hash_before"] in mig_text
              and res["schema_hash_after"] in mig_text
              and "b2 test: add probe column" in mig_text)
check("B2-2 migration emits one intent-bearing receipt with before/after schema_hash",
      moved and receipt_ok, f"moved={moved} receipt={len(mig_rows)}")

# ---------- 7: migrated deployment reports drift AND the receipt explains it ----------
drift_reported = (s2.schema_frame_intact() is False) and (s2.schema_hash() == res["schema_hash_after"])
explains = res["drift_from_release_anchor"] is True and ("release_anchor" in mig_text)
check("B2-7 migrated deployment reports drift from release anchor, receipt explains the drift",
      drift_reported and explains, f"intact={s2.schema_frame_intact()} drift={res['drift_from_release_anchor']}")

# ---------- 4: startup fingerprint observe-only — drift never refuses; store keeps writing ----------
wrote_after = True
try:
    s2.write(op="test_checkpoint", authority="cli", parameters={})
except Exception:
    wrote_after = False
check("B2-4 startup fingerprint observe-only: drift does not refuse; store keeps writing",
      wrote_after and s2.verify_stream_hash())

# ---------- 5: law_hash + legend_hash unchanged ----------
lh = hashlib.sha256(open(os.path.join(REPO, "ugk", "invariants.py"), "rb").read()).hexdigest()
from ugk.storage.binding import LEGEND_HASH
check("B2-5 law_hash + legend_hash unchanged", lh == EXPECTED_LAW_HASH and LEGEND_HASH == EXPECTED_LEGEND_HASH,
      f"law={lh[:12]} legend={LEGEND_HASH[:12]}")

# ---------- 6: EXPECTED_SCHEMA_HASH remains the release anchor (a migration did not move it) ----------
check("B2-6 EXPECTED_SCHEMA_HASH remains the release anchor (not moved by migration)",
      EXPECTED_SCHEMA_HASH == "82d02279c39d5fa82d6bb18a2a12b0f85cc5210a93502d827a9f89c570327c99"
      and UGKReceiptStore(":memory:").schema_frame_intact() is True,
      EXPECTED_SCHEMA_HASH[:12])

ok_all = all(ok for _, ok, _ in results)
print("\nB2 CONFORMANCE GATE:", "PASS" if ok_all else "FAIL")
sys.exit(0 if ok_all else 1)
