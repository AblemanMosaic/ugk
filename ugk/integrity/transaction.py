"""Atomic mutation block (IEL / AD-23) coupling two invariants:

  Invariant A (no mutation before validation): MutationTransaction REFUSES to open if the supplied
                ValidationResult is not ok — the body never runs and nothing is written.
  Invariant E (atomic multi-step write): the body runs inside a single SQLite SAVEPOINT; any
                exception rolls the whole body back (all-or-nothing), so no partially-committed
                state can survive a mid-write failure.

SAVEPOINT (not BEGIN/COMMIT) is used so the wrapper is correct regardless of the connection's
isolation_level and is safely nestable. This is a production-ready primitive; subsystems are
migrated onto it in a later phase (it is intentionally not yet wired into the kernel/store)."""
from __future__ import annotations
import itertools

from ugk.integrity.validation import ValidationResult
from ugk.integrity.levels import CorruptionKind

_counter = itertools.count()


class MutationRefused(Exception):
    """Raised by MutationTransaction.__enter__ when preflight validation is not ok (Invariant A).
    No SAVEPOINT is opened and no body runs."""
    def __init__(self, corruption, detail):
        self.corruption = corruption
        self.detail = detail
        super().__init__(f"mutation refused (validation not ok): {corruption}: {detail}")


class TransactionCommitError(Exception):
    """Raised by MutationTransaction.__exit__ when the CLEAN-path RELEASE (the durable commit of the
    savepoint into the surrounding transaction) fails (r102-b). A RELEASE failure means the block did
    NOT durably commit; the seam treats this as a FAILED transition (fail-closed), attempts
    ROLLBACK TO + RELEASE to leave a clean connection, restores the caller's frontier, and surfaces
    THIS distinct error so a commit/release failure is never reported as success."""
    def __init__(self, detail, cause=None):
        self.detail = detail
        self.cause = cause
        super().__init__(f"transaction commit (savepoint RELEASE) failed: {detail}")


class MutationTransaction:
    """Usage:
        with MutationTransaction(conn, validation, name="write_receipt"):
            conn.execute("INSERT ...")
            conn.execute("UPDATE ...")
    Refuses (raises MutationRefused, no writes) if validation is not ok. On clean exit the SAVEPOINT
    is RELEASEd (committed into the surrounding transaction); on ANY exception it is ROLLed BACK then
    RELEASEd, leaving no partial state. Exceptions are never suppressed."""

    def __init__(self, conn, validation: ValidationResult, *, name: str = ""):
        self.conn = conn
        self.validation = validation
        self.name = name
        self._sp = "iel_mut_%d" % next(_counter)

    def __enter__(self):
        if not self.validation.ok:
            raise MutationRefused(self.validation.corruption or CorruptionKind.UNVERIFIED,
                                  self.validation.detail or "preflight validation failed")
        self.conn.execute("SAVEPOINT %s" % self._sp)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            # CLEAN path: RELEASE commits the savepoint into the surrounding transaction. r102-b: a
            # RELEASE failure means the block did NOT durably commit. Fail closed — attempt
            # ROLLBACK TO + RELEASE to leave a clean, usable connection, then raise a DISTINCT
            # TransactionCommitError so the caller treats the transition as FAILED, never as success.
            try:
                self.conn.execute("RELEASE SAVEPOINT %s" % self._sp)
            except Exception as _rel_err:
                try:
                    self.conn.execute("ROLLBACK TO SAVEPOINT %s" % self._sp)
                    self.conn.execute("RELEASE SAVEPOINT %s" % self._sp)
                except Exception:
                    pass  # best-effort cleanup; the distinct error below is the load-bearing signal
                raise TransactionCommitError(
                    "clean-path RELEASE of %s failed; transition did not durably commit" % self._sp,
                    cause=_rel_err) from _rel_err
        else:
            self.conn.execute("ROLLBACK TO SAVEPOINT %s" % self._sp)
            self.conn.execute("RELEASE SAVEPOINT %s" % self._sp)
        return False  # never suppress
