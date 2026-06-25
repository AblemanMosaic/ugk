"""ugk/conformance/mutation_atomicity_gate.py — atomic-mutation + preflight gate (IEL / AD-24).

Proves the MutationTransaction primitive enforces two invariants on an isolated SQLite connection:

  Invariant A (no mutation before validation): an invalid ValidationResult makes the block REFUSE
    to open (MutationRefused) and the body never runs — zero writes.
  Invariant E (atomic multi-step write): an exception raised mid-body rolls the ENTIRE block back,
    leaving no partially-committed state; a clean block commits.

This is the adversarial evidence that atomicity/preflight are enforced by the primitive, not merely
documented. The gate uses its own throwaway DB; it does not touch the grundnorm store.
"""
from __future__ import annotations
import sqlite3

from ugk.integrity import ValidationResult, MutationTransaction, MutationRefused, CorruptionKind


def run():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE t(x INTEGER)")
    c.execute("INSERT INTO t VALUES (1)")
    c.commit()
    rows = lambda: c.execute("SELECT COUNT(*) FROM t").fetchone()[0]

    if rows() != 1:
        return False, "fixture broken: expected 1 row"

    # (A) invalid validation -> refuse, body never runs, no write
    refused = False
    try:
        with MutationTransaction(c, ValidationResult.invalid(CorruptionKind.MALFORMED, "bad input"), name="A"):
            c.execute("INSERT INTO t VALUES (99)")  # MUST NOT execute
    except MutationRefused:
        refused = True
    if not refused:
        return False, "Invariant A FAIL: MutationTransaction did not refuse an invalid ValidationResult"
    if rows() != 1:
        return False, "Invariant A FAIL: a refused mutation still wrote to the store"

    # (B) exception mid-body -> full rollback
    try:
        with MutationTransaction(c, ValidationResult.valid(), name="B"):
            c.execute("INSERT INTO t VALUES (2)")
            raise RuntimeError("boom mid-write")
    except RuntimeError:
        pass
    if rows() != 1:
        return False, "Invariant E FAIL: partial write survived a mid-body exception (no rollback)"

    # (C) clean block commits
    with MutationTransaction(c, ValidationResult.valid(), name="C"):
        c.execute("INSERT INTO t VALUES (3)")
    if rows() != 2:
        return False, "commit FAIL: a clean MutationTransaction did not persist its write"

    # (D) exception must not be suppressed
    propagated = False
    try:
        with MutationTransaction(c, ValidationResult.valid(), name="D"):
            raise ValueError("must propagate")
    except ValueError:
        propagated = True
    if not propagated:
        return False, "FAIL: MutationTransaction suppressed an exception (must never suppress)"

    return True, ("MutationTransaction enforces Invariant A (refuse-if-unvalidated, no write) and "
                  "Invariant E (mid-body exception rolls back fully; clean block commits; exceptions propagate)")


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + "  mutation_atomicity_gate — " + detail)
    raise SystemExit(0 if ok else 1)
