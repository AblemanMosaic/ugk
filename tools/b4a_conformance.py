#!/usr/bin/env python3
"""B4a conformance gate — writer serialization / single-writer safety (ships in archive).

Proves:
 1. Mutation-surface completeness + the AD-34 deferred-commit seam as an EXPLICITLY AUDITED surface
    — every runtime durable-write is inside `with self._lock`; the complete mutation surface matches
    the enumerated set (now including seam-opening methods); durable receipt writes flow only through
    write(); migrate_schema uses the audited seam with no direct commit; the seam is built on the
    MutationTransaction (A+E) primitive with no unmanaged outer commit; the only DDL helper is
    construction-only; and a failed transaction persists nothing (schema/receipts/stream/frontier).
 2. Concurrent linearity — concurrent in-process writers cannot produce duplicate-parent
    receipts or fork the chain.
 3. Deterministic ordering — legacy chain (verify_stream_hash) and M2 lineage (parent_h_r ==
    prior h_r) remain valid after concurrent stress.
 4. No constitutional drift — law_hash unchanged.

Run from repo root:  python3 tools/b4a_conformance.py   (expects all PASS, exit 0)
"""
import os, sys, ast, hashlib, threading, sqlite3
from pathlib import Path

REPO = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, REPO)
EXPECTED_LAW_HASH = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"

results = []
def check(n, ok, d=""):
    results.append((n, bool(ok), d))
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))

from ugk.storage.store import UGKReceiptStore

# ---------- Check 1: mutation-surface completeness (structural AST) ----------
src = open(os.path.join(REPO, "ugk", "storage", "store.py"), encoding="utf-8").read()
tree = ast.parse(src)
store = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "UGKReceiptStore")
M = {m.name: m for m in store.body if isinstance(m, ast.FunctionDef)}
MUT = ("INSERT INTO", "INSERT OR", "UPDATE ", "DELETE FROM", "CREATE TABLE", "ALTER TABLE", "REPLACE INTO", "DROP TABLE")

def commit_calls(fn):
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == "commit"]
def mut_strings(fn):
    s = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            up = n.value.upper()
            for p in MUT:
                if p in up:
                    s.add(p)
    return s
def lock_ranges(fn):
    rs = []
    for n in ast.walk(fn):
        if isinstance(n, ast.With):
            for it in n.items:
                ce = it.context_expr
                if (isinstance(ce, ast.Attribute) and ce.attr == "_lock"
                        and isinstance(ce.value, ast.Name) and ce.value.id == "self"):
                    rs.append((n.lineno, n.end_lineno))
    return rs
def mutating_execute_lines(fn):
    pts = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "execute"):
            txt = " ".join(a.value.upper() for a in ast.walk(n)
                           if isinstance(a, ast.Constant) and isinstance(a.value, str))
            if any(p in txt for p in MUT):
                pts.append(n.lineno)
    return pts
def all_writes_locked(fn):
    rs = lock_ranges(fn)
    pts = [c.lineno for c in commit_calls(fn)] + mutating_execute_lines(fn)
    return all(any(lo <= p <= hi for lo, hi in rs) for p in pts) if pts else True

# --- AD-34: the deferred-commit seam is an EXPLICITLY AUDITED mutation surface ---
# A method durably mutates if it has a direct commit, a literal mutation SQL, OR it composes durable
# mutations through the audited deferred-commit seam (self.transaction()). The seam is NOT a fifth
# UNAUDITED path: it is the deferred-commit counterpart of write()'s direct commit, built on the
# MutationTransaction (Invariant A+E) primitive, and proven admissible by the seam checks below.
# migrate_schema is detected via the seam (its ALTER is a dynamic statement and its commit moved
# INTO the seam), so EXPECTED is UNCHANGED - the topology is more precise, not looser.
def calls_self_transaction(fn):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "transaction"
               and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"
               for n in ast.walk(fn))
def has_receipt_insert(fn):
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            u = n.value.upper()
            if "INSERT INTO" in u and "RECEIPTS" in u:
                return True
    return False
def opens_transaction_lines(fn):
    return [n.lineno for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "transaction"
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"]
def seam_under_lock(fn):
    rs = lock_ranges(fn)
    return all(any(lo <= p <= hi for lo, hi in rs) for p in opens_transaction_lines(fn))

commit_methods = {name for name, fn in M.items() if commit_calls(fn)}
dml_methods = {name for name, fn in M.items() if mut_strings(fn)}
txn_methods = {name for name, fn in M.items() if calls_self_transaction(fn)}   # AD-34 seam users
mutation_surface = commit_methods | dml_methods | txn_methods
EXPECTED = {"__init__", "_migrate_m2_schema", "write", "seal_legend", "seal_scope", "seal_authority_model", "migrate_schema", "seal_and_prune_epoch"}
check("B4a-1 complete mutation surface == enumerated set (no fifth path)",
      mutation_surface == EXPECTED, str(sorted(mutation_surface)))

# (seam-i) every durable RECEIPT write flows through write(): the receipts INSERT literal is in write() ONLY
receipt_insert_methods = {name for name, fn in M.items() if has_receipt_insert(fn)}
check("B4a-1 (seam-i) durable receipt writes flow only through write() [sole INSERT INTO receipts]",
      receipt_insert_methods == {"write"}, str(sorted(receipt_insert_methods)))

# (seam-iii) migrate_schema uses the audited seam and has NO direct unmanaged commit
ms_fn = M["migrate_schema"]
check("B4a-1 (seam-iii) migrate_schema uses the seam (self.transaction) with no direct commit",
      calls_self_transaction(ms_fn) and len(commit_calls(ms_fn)) == 0)

# (seam-iii-2, AD-36) seal_and_prune_epoch is the SECOND seam-backed path - positively audited (not
# merely tolerated): it uses the audited seam with NO direct unmanaged commit (its provenance receipts
# go through write(), per seam-i), and its destructive DELETE executes ONLY INSIDE the
# store.transaction() block (so the deletion is part of the atomic governed transition, under the lock).
def transaction_with_ranges(fn):
    rs = []
    for n in ast.walk(fn):
        if isinstance(n, ast.With):
            for it in n.items:
                ce = it.context_expr
                if (isinstance(ce, ast.Call) and isinstance(ce.func, ast.Attribute)
                        and ce.func.attr == "transaction"
                        and isinstance(ce.func.value, ast.Name) and ce.func.value.id == "self"):
                    rs.append((n.lineno, n.end_lineno))
    return rs
sp_fn = M["seal_and_prune_epoch"]
check("B4a-1 (seam-iii-2) seal_and_prune_epoch uses the seam (self.transaction) with no direct commit",
      calls_self_transaction(sp_fn) and len(commit_calls(sp_fn)) == 0)
_sp_txn = transaction_with_ranges(sp_fn)
_sp_del = mutating_execute_lines(sp_fn)
check("B4a-1 (seam-iii-2) seal_and_prune_epoch destructive DELETE executes ONLY inside the audited seam",
      bool(_sp_del) and bool(_sp_txn) and all(any(lo <= d <= hi for lo, hi in _sp_txn) for d in _sp_del))

# (seam-audit) the seam is built on MutationTransaction (A+E) and issues NO unmanaged outer commit
# (clean exit = SAVEPOINT RELEASE commits; abort = ROLLBACK TO + RELEASE persists nothing)
txn_fn = M.get("transaction")
check("B4a-1 (seam-audit) transaction() built on MutationTransaction (A+E), no unmanaged outer commit",
      txn_fn is not None
      and any(isinstance(n, ast.Name) and n.id == "MutationTransaction" for n in ast.walk(txn_fn))
      and len(commit_calls(txn_fn)) == 0)

# (seam-ii PRIMARY, AD-35) the seam OWNS its lock discipline: transaction() acquires self._lock
# INTRINSICALLY (RLock), and the full savepoint lifecycle (MutationTransaction construction +
# __enter__/__exit__) executes inside that `with self._lock` - so serialization is a PROPERTY OF THE
# SEAM, not a caller convention, and every commit/release/rollback on the seam is under the lock.
def seam_owns_lock(fn):
    if fn is None:
        return False
    rs = lock_ranges(fn)
    if not rs:
        return False
    sav = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id == "MutationTransaction":
                sav.append(n.lineno)
            elif isinstance(f, ast.Attribute) and f.attr in ("__enter__", "__exit__"):
                sav.append(n.lineno)
    return bool(sav) and all(any(lo <= p <= hi for lo, hi in rs) for p in sav)
check("B4a-1 (seam-ii PRIMARY) the seam owns its lock discipline: transaction() acquires self._lock intrinsically over the full savepoint lifecycle",
      seam_owns_lock(M.get("transaction")))
# (seam-ii defense-in-depth) current seam-opening callsites ALSO open the seam under `with self._lock`
check("B4a-1 (seam-ii defense-in-depth) current seam-opening methods also open under `with self._lock`",
      all(seam_under_lock(M[n]) for n in txn_methods))

RUNTIME = {"write", "seal_legend", "seal_scope", "seal_authority_model", "__init__", "migrate_schema", "seal_and_prune_epoch"}
check("B4a-1 every runtime write+commit is inside a `with self._lock` section",
      all(all_writes_locked(M[n]) for n in RUNTIME))

callers = [n for n in ast.walk(store) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "_migrate_m2_schema"]
ilo, ihi = M["__init__"].lineno, M["__init__"].end_lineno
check("B4a-1 _migrate_m2_schema is construction-only (single caller inside __init__'s locked block)",
      len(callers) == 1 and ilo <= callers[0].lineno <= ihi)

check("B4a-1 lock is re-entrant (RLock)", type(UGKReceiptStore(":memory:")._lock).__name__ == "RLock")

# (seam-v) failed transaction paths persist NOTHING: schema, receipts, stream hash, AND Python
# frontier all match pre-transaction (verified from a FRESH connection), and the next write links
# to the pre-rollback frontier - the deferred-commit seam is all-or-nothing at the durable boundary.
import tempfile as _tf
from ugk.storage.store import compute_schema_hash as _csh
def _disk(db):
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    sh = _csh(c); n = c.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
    row = c.execute("SELECT h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1").fetchone(); c.close()
    return sh, n, (row[0] if row else None), UGKReceiptStore(db_path=db, read_only=True).stream_hash()
_db = os.path.join(_tf.mkdtemp(), "b4a_atom.db"); _s = UGKReceiptStore(db_path=_db)
_pre = _disk(_db); _pre_tip = _s._prior_h_r
_orig = _s.write
def _boom(*a, **k):
    raise RuntimeError("b4a injected receipt failure")
_s.write = _boom; _raised = False
try:
    _s.migrate_schema(["ALTER TABLE receipts ADD COLUMN b4a_rb TEXT"], intent="b4a rollback")
except RuntimeError:
    _raised = True
_s.write = _orig
_post = _disk(_db); _frontier_ok = (_s._prior_h_r == _pre_tip)
_s.write(op="test_checkpoint", authority="cli", parameters={})
_np = sqlite3.connect("file:%s?mode=ro" % _db, uri=True).execute(
    "SELECT parent_h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1").fetchone()[0]
check("B4a-1 (seam-v) failed transaction persists nothing (fresh-conn schema/count/stream + frontier restored + next write links pre-rollback)",
      _raised and _post[0] == _pre[0] and _post[1] == _pre[1] and _post[3] == _pre[3] and _frontier_ok and _np == _pre_tip)

# ---------- Check 2 + 3: concurrent linearity + invariants after stress ----------
s = UGKReceiptStore(":memory:")
NT, NW = 8, 60
def worker():
    for _ in range(NW):
        s.write(op="test_checkpoint", authority="cli", parameters={})
threads = [threading.Thread(target=worker) for _ in range(NT)]
for t in threads: t.start()
for t in threads: t.join()

total = s.receipt_count()
recs = s.all_receipts()
priors = [r.parent_h_r for r in recs]
no_dup_parent = len(set(priors)) == len(priors)         # a fork would reuse a parent
check("B4a-2 concurrent writers: no duplicate-parent receipts (no chain fork)",
      total == NT * NW and no_dup_parent, f"{total} receipts, distinct parents={len(set(priors))}")

m2_chain_linear = (recs[0].parent_h_r == UGKReceiptStore.GENESIS
                 and all(recs[i].parent_h_r == recs[i-1].h_r
                         for i in range(1, len(recs))))
check("B4a-3 M2 chain linear (parent_h_r==prior h_r) + verify_stream_hash() after concurrent stress",
      m2_chain_linear and s.verify_stream_hash())

rows = s._conn.execute("SELECT h_r, parent_h_r FROM receipts ORDER BY receipt_id ASC").fetchall()
m2_linear = (rows[0][1] == UGKReceiptStore.GENESIS
             and all(rows[i][1] == rows[i-1][0] for i in range(1, len(rows))))
check("B4a-3 M2 lineage contiguous (parent_h_r == prior h_r) after concurrent stress", m2_linear)

tss = [r[0] for r in s._conn.execute("SELECT timestamp FROM receipts ORDER BY receipt_id ASC").fetchall()]
ts_mono = all(tss[i] >= tss[i-1] for i in range(1, len(tss)))
check("B4a-3 timestamps monotonic by receipt (append) order after concurrent stress [r44]",
      ts_mono, f"n={len(tss)} non-decreasing={ts_mono}")

# fork-detector sensitivity (non-vacuous): a fabricated duplicate parent is caught
_fab = ["g", "h1", "h1"]
check("B4a-2 fork detector is non-vacuous (flags a fabricated duplicate parent)",
      len(set(_fab)) != len(_fab))

# ---------- Check 1 (seam-iii-3, r102-b/AD-38): kernel.execute() is the THIRD seam-backed caller ----------
# execute()'s PURE/STORE_LOCAL outcome transition routes [effect + success receipt] through the STORE
# seam (self._store.transaction()), with the success write INSIDE the seam (success-after-effect),
# gate_admit committed BEFORE the seam (durable decision-before-effect at depth 0), and the structural
# abort emitted via _emit_effect_abort -> self._store.write at depth 0. No direct conn.commit and no
# raw 'INSERT INTO receipts' in the kernel: mutation-surface discipline is TIGHTENED with a third
# positively-audited caller, NOT loosened.
ksrc = open(os.path.join(REPO, "ugk", "kernel.py"), encoding="utf-8").read()
ktree = ast.parse(ksrc)
kcls = next(n for n in ktree.body if isinstance(n, ast.ClassDef) and n.name == "GovernanceKernel")
KM = {m.name: m for m in kcls.body if isinstance(m, ast.FunctionDef)}
ex_fn = KM.get("execute")
abort_fn = KM.get("_emit_effect_abort")

def _store_attr_call(node, attr):
    # matches self._store.<attr>(...)
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == attr and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "_store"
            and isinstance(node.func.value.value, ast.Name) and node.func.value.value.id == "self")

def _store_txn_with_ranges(fn):
    rs = []
    for n in ast.walk(fn):
        if isinstance(n, ast.With):
            for it in n.items:
                if _store_attr_call(it.context_expr, "transaction"):
                    rs.append((n.lineno, n.end_lineno))
    return rs

def _store_write_lines(fn):
    return [n.lineno for n in ast.walk(fn) if _store_attr_call(n, "write")]

def _raw_receipt_inserts(fn):
    return [n.lineno for n in ast.walk(fn)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and "INSERT INTO" in n.value.upper() and "RECEIPTS" in n.value.upper()]

def _gate_admit_write_line(fn):
    for n in ast.walk(fn):
        if _store_attr_call(n, "write"):
            for kw in n.keywords:
                if kw.arg == "op" and isinstance(kw.value, ast.Constant) and kw.value.value == "gate_admit":
                    return n.lineno
    return None

_ex_txn = _store_txn_with_ranges(ex_fn) if ex_fn else []
# (a) execute() opens the store seam; no direct conn.commit; no raw receipts INSERT (no fifth path)
check("B4a-1 (seam-iii-3) kernel.execute() opens the store seam (self._store.transaction) with no direct commit and no raw receipts INSERT",
      bool(ex_fn) and bool(_ex_txn) and len(commit_calls(ex_fn)) == 0 and not _raw_receipt_inserts(ex_fn))
# (b) a success receipt write executes INSIDE the seam (atomic [effect+success], success-after-effect)
_ex_writes = _store_write_lines(ex_fn) if ex_fn else []
_writes_in_seam = [w for w in _ex_writes if any(lo <= w <= hi for lo, hi in _ex_txn)]
check("B4a-1 (seam-iii-3) execute() writes the success receipt INSIDE the seam (atomic [effect+success], success-after-effect)",
      bool(_writes_in_seam))
# (c) gate_admit is written BEFORE the seam block (durable decision-before-effect at depth 0)
_ga = _gate_admit_write_line(ex_fn) if ex_fn else None
_seam_start = min((lo for lo, hi in _ex_txn), default=None)
check("B4a-1 (seam-iii-3) gate_admit written BEFORE the seam (decision-before-effect at depth 0)",
      _ga is not None and _seam_start is not None and _ga < _seam_start)
# (d) the structural abort flows through _emit_effect_abort -> self._store.write (depth 0, no raw mutation)
_calls_abort = (any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "_emit_effect_abort" for n in ast.walk(ex_fn))) if ex_fn else False
check("B4a-1 (seam-iii-3) execute() records the structural abort via _emit_effect_abort -> self._store.write (no raw mutation, depth 0)",
      _calls_abort and bool(abort_fn) and bool(_store_write_lines(abort_fn))
      and len(commit_calls(abort_fn)) == 0 and not _raw_receipt_inserts(abort_fn))

# ---------- Check 4: law_hash unchanged ----------
lh = hashlib.sha256(open(os.path.join(REPO, "ugk", "invariants.py"), "rb").read()).hexdigest()
check("B4a-4 law_hash unchanged (invariants.py untouched)", lh == EXPECTED_LAW_HASH, lh[:16] + "...")

ok_all = all(ok for _, ok, _ in results)
print("\nB4a CONFORMANCE GATE:", "PASS" if ok_all else "FAIL")
sys.exit(0 if ok_all else 1)
