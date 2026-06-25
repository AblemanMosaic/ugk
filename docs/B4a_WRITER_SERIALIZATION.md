# B4a — Writer Serialization / Single-Writer Safety (v0.1.0)

**Status:** implemented and gated (`tools/b4a_conformance.py`).

## What B4a guarantees

The receipt store shares one `sqlite3` connection (`check_same_thread=False`). B4a makes
the single-writer assumption *real within a process* by serializing the complete mutation
surface under a re-entrant lock (`self._lock = threading.RLock()`):

- **`write()`** — the critical section spans the **entire receipt-append read-modify-write**:
  the chain-tip reads (`_prior_hash`, `_prior_h_r`, `_prior_h_m`, `_prior_intent_ref`), the
  receipt computation, the `INSERT`, the `commit()`, and the chain-tip updates. This is the
  real atomic unit — locking only the `INSERT` would still allow two writers to observe the
  same tip and fork the chain.
- **`seal_legend` / `seal_scope` / `seal_authority_model`** — idempotent `INSERT OR IGNORE`
  archive writes; their `execute + commit` is the critical section.
- **construction** (`__init__`, and `_migrate_m2_schema`, which has the single caller
  `__init__`) — schema creation/migration runs under the lock too; it is single-threaded and
  pre-sharing, so it cannot race, but it is kept inside the lock so that *every* commit in the
  store is lexically under serialization.

`RLock` (not `Lock`) is used so a mutation path may safely nest without self-deadlock.

## Explicitly OUT OF SCOPE for v0.1.0

**Cross-process writer contention.** WAL mode permits one writer at a time at the SQLite
file-lock level, but with no `busy_timeout` a second *process* writing the same database may
receive an immediate "database is locked". v0.1.0 is a **single-writer reference release**;
multiple concurrent OS processes writing one store is not a supported configuration.

No `busy_timeout` and no cross-process advisory lock are part of B4a. Cross-process writer
policy is a separate architectural question and is deferred. If a future release supports
multi-process writers, that work must define the contention/timeout/ownership policy
explicitly — it is not implied by B4a.
