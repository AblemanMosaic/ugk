#!/usr/bin/env python3
"""B1 conformance gate — governed epoch seal + prune (storage-frame; ships in archive).

Proves:
 1. seal commitment: S = boundary.h_r (the M2 chain already makes S commit to the prefix);
 2. TIP PRESERVED across the prune (deletion) step: tip_after_prune == tip_before_prune
    — pruning is observationally equivalent to retaining the prefix (the Governor's invariant);
 3. retained chain verifies from the seal: verify_from_seal(S) holds after pruning;
 4. anchor is the VALUE S, not a receipt: the boundary receipt is gone yet verification holds;
 5. the sealed prefix is actually pruned (receipt count drops by the sealed count);
 6. fail-closed: empty intent and unknown seal_hash are refused with ZERO mutation;
 7. frame triad + legend unmoved; schema_hash unchanged (no schema change).

Run from repo root:  python3 tools/b1_conformance.py   (expects PASS, exit 0)
"""
import os, sys, hashlib
from pathlib import Path
REPO = str(Path(__file__).resolve().parent.parent); sys.path.insert(0, REPO)
EXPECTED_LAW = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"
EXPECTED_LEGEND = "db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7"

results = []
def check(n, ok, d=""):
    results.append((n, bool(ok))); print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))

from ugk.storage.store import UGKReceiptStore, compute_schema_hash, EXPECTED_SCHEMA_HASH
from ugk.storage.binding import LEGEND_HASH

def fresh(n=6):
    s = UGKReceiptStore(":memory:")
    for i in range(n):
        s.write(op="test_checkpoint", authority="cli", parameters={"i": i})
    return s

# ---- build a chain; choose a mid boundary (prune first 3, retain last 3) ----
s = fresh(6)
rs = s.all_receipts()
boundary = rs[2]                     # 3rd receipt
S = boundary.h_r
count_before = len(rs)
schema_before = compute_schema_hash(s._conn)
tip_before_seal = s.stream_hash()

check("B1-1 seal commitment S = boundary.h_r (M2 chain commits the prefix)",
      S == boundary.h_r and S == rs[2].h_r)

res = s.seal_and_prune_epoch(S, intent="b1 test: seal+prune first 3")

# ---- 2. TIP PRESERVED across the deletion step ----
check("B1-2 tip preserved across prune (tip_after_prune == tip_before_prune)",
      res["tip_after_prune"] == res["tip_before_prune"],
      f"{res['tip_before_prune'][:10]}=={res['tip_after_prune'][:10]}")

# ---- 3. retained chain verifies from the seal ----
check("B1-3 verify_from_seal(S) holds after prune", s.verify_from_seal(S) is True)

# ---- 4. anchor is the VALUE S, not a receipt (boundary receipt is gone) ----
present = {r.h_r for r in s.all_receipts()}
check("B1-4 anchor is the value S, not a receipt (boundary receipt pruned, verification still holds)",
      S not in present and s.verify_from_seal(S) is True)

# ---- 5. the sealed prefix is actually pruned ----
# retained = original frontier (3) + epoch_sealed + epoch_pruned = 5; pruned 3
now = len(s.all_receipts())
ops_now = [r.op for r in s.all_receipts()]
check("B1-5 sealed prefix pruned; epoch_sealed + epoch_pruned recorded",
      now == 5 and res["pruned_count"] == 3 and "epoch_sealed" in ops_now and "epoch_pruned" in ops_now,
      f"count {count_before}->{now}, pruned={res['pruned_count']}")

# GENESIS-anchored verify is, by design, NOT expected to pass on a sealed store (anchor is the seal)
check("B1-3b GENESIS-anchored verify_stream_hash() not expected to pass post-seal (anchor is the seal)",
      s.verify_stream_hash() is False and s.verify_from_seal(S) is True)

# ---- 6. fail-closed: empty intent + unknown seal_hash refused, ZERO mutation ----
s2 = fresh(5); rs2 = s2.all_receipts(); S2 = rs2[1].h_r
c0 = len(rs2); t0 = s2.stream_hash()
def refused(fn):
    try: fn(); return False
    except ValueError: return True
empty_ref = refused(lambda: s2.seal_and_prune_epoch(S2, intent=""))
bad_ref = refused(lambda: s2.seal_and_prune_epoch("deadbeef" * 8, intent="probe"))
c1 = len(s2.all_receipts()); t1 = s2.stream_hash()
check("B1-6 fail-closed: empty intent + unknown seal_hash refused before mutation (zero drift)",
      empty_ref and bad_ref and c0 == c1 and t0 == t1, f"count {c0}=={c1} tip-stable={t0==t1}")

# ---- 7. frame triad + legend unmoved; schema unchanged (no schema change) ----
law = hashlib.sha256(open(os.path.join(REPO, "ugk", "invariants.py"), "rb").read()).hexdigest()
schema_after = compute_schema_hash(s._conn)
check("B1-7 law_hash + legend_hash unmoved", law == EXPECTED_LAW and LEGEND_HASH == EXPECTED_LEGEND)
check("B1-7 schema_hash unchanged by seal/prune (no schema change)",
      schema_before == schema_after == EXPECTED_SCHEMA_HASH, schema_after[:12])

ok = all(o for _, o in results)
print("\nB1 CONFORMANCE GATE:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
