"""ReadOnlyGuard (IEL / AD-25). Invariant D: read-only operations never mutate state.

A verifier/status/attestation path must never create a database or open a session. This guard is
fail-closed and detection-based: `require_existing` refuses up front if a read-only op targets a
non-existent on-disk DB (preventing accidental creation), and the context manager raises if the op
nonetheless brought a DB file into existence. ":memory:" / None are ephemeral and exempt (no
persistent state to protect). A deeper prevention variant (a read-only store CONNECTION via
sqlite mode=ro) is a follow-on; this v1 makes the read-path-mutation class LOUD and fail-closed."""
from __future__ import annotations
import os


class ReadOnlyViolation(Exception):
    """A read-only operation created or destroyed persistent state (Invariant D breach)."""


def _is_ephemeral(db_path) -> bool:
    return db_path is None or db_path == ":memory:"


class ReadOnlyGuard:
    def __init__(self, db_path, *, name: str = ""):
        self.db_path = db_path
        self.name = name

    @staticmethod
    def require_existing(db_path, *, name: str = "") -> None:
        """Fail closed if a read-only op targets a non-existent on-disk DB. Prevents the verifier/
        status/attestation path from silently creating state. :memory:/None are exempt."""
        if not _is_ephemeral(db_path) and not os.path.exists(db_path):
            raise ReadOnlyViolation(
                "read-only op %r requires an existing database; none at %s" % (name, db_path))

    def __enter__(self):
        self._existed = _is_ephemeral(self.db_path) or os.path.exists(self.db_path)
        return self

    def __exit__(self, exc_type, exc, tb):
        if not _is_ephemeral(self.db_path):
            exists_now = os.path.exists(self.db_path)
            if not self._existed and exists_now:
                raise ReadOnlyViolation(
                    "read-only op %r CREATED a database at %s" % (self.name, self.db_path))
            if self._existed and not exists_now:
                raise ReadOnlyViolation(
                    "read-only op %r DESTROYED the database at %s" % (self.name, self.db_path))
        return False  # never suppress
