#!/usr/bin/env python3
"""schema_hash conformance gate — structure frame-pin (ships in the canonical archive).

Scope: startup fingerprint anchoring + integrity-model frame binding ONLY.
Observe-and-report; never refuse-on-mismatch; never injected into individual receipts;
not live-migration machinery.

Proves:
 1. Determinism — schema_hash is stable within and across processes.
 2. Anchor — the shipped schema matches the pinned EXPECTED_SCHEMA_HASH (frame intact).
 3. Frame binding — the triad (law_hash, legend_hash, schema_hash) is exposed in the
    integrity model: CLI status (runtime) + kernel snapshot (wired to the store).
 4. Observe-only — schema drift changes the hash and flips schema_frame_intact to False
    but does NOT refuse, gate, or migrate; the store keeps writing.
 5. No per-receipt injection — schema_hash is not a receipts column.
 6. law_hash unchanged.

Run from repo root:  python3 tools/schema_hash_conformance.py   (expects all PASS, exit 0)
"""
import os, sys, io, ast, json, tempfile, sqlite3, hashlib, contextlib, subprocess
from pathlib import Path
from types import SimpleNamespace

REPO = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, REPO)
EXPECTED_LAW_HASH = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"

results = []
def check(n, ok, d=""):
    results.append((n, bool(ok), d))
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))

from ugk.storage.store import UGKReceiptStore, compute_schema_hash, EXPECTED_SCHEMA_HASH
from ugk import cli

# ---------- 1. Determinism (within + across processes) ----------
h1 = UGKReceiptStore(":memory:").schema_hash()
h2 = UGKReceiptStore(":memory:").schema_hash()
_scr = ("import os,sys;sys.path.insert(0,os.environ['REPO']);"
        "from ugk.storage.store import UGKReceiptStore;"
        "print(UGKReceiptStore(':memory:').schema_hash())")
hp = subprocess.check_output([sys.executable, "-c", _scr], env=dict(os.environ, REPO=REPO)).decode().strip()
check("schema_hash-1 deterministic within + across processes", h1 == h2 == hp, h1[:16] + "...")

# ---------- 2. Anchor: shipped schema matches the pinned EXPECTED ----------
s = UGKReceiptStore(":memory:")
check("schema_hash-2 shipped schema matches pinned anchor (frame intact)",
      s.schema_hash() == EXPECTED_SCHEMA_HASH and s.schema_frame_intact() is True,
      EXPECTED_SCHEMA_HASH[:16] + "...")

# ---------- 3. Frame binding: triad exposed in integrity model ----------
# (a) CLI status (runtime, read-only). Initialize a temporary READABLE state first: an unfounded
#     :memory: read-only store has no receipts table, so status must read a real (empty) state. This
#     does NOT mask schema drift — the observe-only drift checks below run against their own stores.
_status_dir = tempfile.mkdtemp(prefix="schema-status-")
UGKReceiptStore(db_path=os.path.join(_status_dir, "ugk.db"))  # creates the receipts table (readable empty state)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = cli._cmd_status(SimpleNamespace(state_dir=_status_dir))
snap = json.loads(buf.getvalue())
triad_cli = all(k in snap for k in ("law_hash", "legend_hash", "schema_hash")) and "schema_frame_intact" in snap
check("schema_hash-3 CLI status exposes frame triad (law/legend/schema)", rc == 0 and triad_cli)
# (b) kernel snapshot wires schema_hash to the store (structural)
ksrc = open(os.path.join(REPO, "ugk", "kernel.py")).read()
check("schema_hash-3 kernel snapshot binds schema_hash + schema_frame_intact to the store",
      '"schema_hash":' in ksrc and "self._store.schema_hash()" in ksrc
      and '"schema_frame_intact":' in ksrc and "self._store.schema_frame_intact()" in ksrc)

# ---------- 4. Observe-only: drift detected, never refused/migrated ----------
tmp = tempfile.mkdtemp(); dbp = os.path.join(tmp, "drift.db")
s1 = UGKReceiptStore(db_path=dbp)
base = compute_schema_hash(s1._conn)
s1._conn.execute("ALTER TABLE receipts ADD COLUMN _drift_probe TEXT")  # simulate structure drift
s1._conn.commit()
drifted = compute_schema_hash(s1._conn)
# the store keeps writing after drift — no refuse, no migration
wrote_after_drift = True
try:
    s1.write(op="test_checkpoint", authority="cli", parameters={})
except Exception:
    wrote_after_drift = False
# a fresh store on the drifted db reports drift (observe), still functions
s2 = UGKReceiptStore(db_path=dbp)
check("schema_hash-4 drift changes the hash and is reported (not intact), never refused",
      drifted != base and s2.schema_frame_intact() is False and wrote_after_drift,
      f"intact_after_drift={s2.schema_frame_intact()} wrote={wrote_after_drift}")

# ---------- 5. No per-receipt injection ----------
cols = [r[1] for r in UGKReceiptStore(":memory:")._conn.execute("PRAGMA table_info(receipts)").fetchall()]
check("schema_hash-5 schema_hash is NOT a receipts column (frame-level, not per-receipt)",
      "schema_hash" not in cols)

# ---------- 6. law_hash unchanged ----------
lh = hashlib.sha256(open(os.path.join(REPO, "ugk", "invariants.py"), "rb").read()).hexdigest()
check("schema_hash-6 law_hash unchanged (invariants.py untouched)", lh == EXPECTED_LAW_HASH, lh[:16] + "...")

ok_all = all(ok for _, ok, _ in results)
print("\nSCHEMA_HASH CONFORMANCE GATE:", "PASS" if ok_all else "FAIL")
sys.exit(0 if ok_all else 1)
