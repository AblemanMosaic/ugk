"""ugk/scope.py — ProvenanceScope: explicit session scope declaration (Grundnorm 444).

SCOPE-S-01: ProvenanceScope is emitted at session_open and stored in scope_archive.
            scope_id = SHA-256(canonical_json(body)). Part of the operational continuity chain.
SCOPE-S-02: Replay admissibility: receipts from a closed session are scope-bounded.
            A receipt from scope S is not admissible as a new-session operation.

ProvenanceScope makes the implicit provenance boundary of a UGK session explicit.
session_dkn and law_hash act as implicit scopes; ProvenanceScope declares them
formally with a prior_scope_id that chains sessions into an operational lineage —
the attribution continuity structure described in §8 of the identity paper.

prior_scope_id: "" for the first session under a mosaic_root; the scope_id of the
immediately prior session otherwise. Chains sessions into proof-carrying continuity.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from ugk.storage.binding import canonical_json as _cj


@dataclass(frozen=True)
class ProvenanceScope:
    """Explicit session scope declaration.

    scope_id = SHA-256(canonical_json of all body fields).
    authority_surface = mosaic_root (SHA-256(governor_pubkey)).
    prior_scope_id chains sessions into operational continuity lineage.
    """
    scope_id:          str
    scope_type:        str   # "session"
    authority_surface: str   # mosaic_root
    session_dkn:       str
    law_hash:          str
    legend_hash:       str
    prior_scope_id:    str   # "" for first session; predecessor scope_id otherwise
    timestamp:         str

    @staticmethod
    def create(
        authority_surface: str,
        session_dkn:       str,
        law_hash:          str,
        legend_hash:       str,
        prior_scope_id:    str = "",
        scope_type:        str = "session",
        timestamp:         Optional[str] = None,
    ) -> "ProvenanceScope":
        ts   = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = {
            "authority_surface": authority_surface,
            "law_hash":          law_hash,
            "legend_hash":       legend_hash,
            "prior_scope_id":    prior_scope_id,
            "scope_type":        scope_type,
            "session_dkn":       session_dkn,
            "timestamp":         ts,
        }
        sid = hashlib.sha256(_cj(body)).hexdigest()
        return ProvenanceScope(
            scope_id=sid, scope_type=scope_type,
            authority_surface=authority_surface, session_dkn=session_dkn,
            law_hash=law_hash, legend_hash=legend_hash,
            prior_scope_id=prior_scope_id, timestamp=ts,
        )

    def verify_id(self) -> bool:
        body = {
            "authority_surface": self.authority_surface,
            "law_hash":          self.law_hash,
            "legend_hash":       self.legend_hash,
            "prior_scope_id":    self.prior_scope_id,
            "scope_type":        self.scope_type,
            "session_dkn":       self.session_dkn,
            "timestamp":         self.timestamp,
        }
        return hashlib.sha256(_cj(body)).hexdigest() == self.scope_id


_CREATE_SCOPE_ARCHIVE = """
CREATE TABLE IF NOT EXISTS scope_archive (
    scope_id          TEXT PRIMARY KEY,
    scope_type        TEXT NOT NULL DEFAULT 'session',
    authority_surface TEXT NOT NULL DEFAULT '',
    session_dkn       TEXT NOT NULL DEFAULT '',
    law_hash          TEXT NOT NULL DEFAULT '',
    legend_hash       TEXT NOT NULL DEFAULT '',
    prior_scope_id    TEXT NOT NULL DEFAULT '',
    timestamp         TEXT NOT NULL DEFAULT ''
);
"""


class ScopeArchive:
    """Queryable archive of ProvenanceScope artifacts. Backed by SQLite.

    Colocated with receipts in ugk.db (added as a table in UGKReceiptStore).
    Also usable standalone for testing.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_CREATE_SCOPE_ARCHIVE)
        self._conn.commit()

    def seal(self, scope: ProvenanceScope) -> None:
        """Store a ProvenanceScope. Idempotent."""
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO scope_archive "
                "(scope_id, scope_type, authority_surface, session_dkn, "
                " law_hash, legend_hash, prior_scope_id, timestamp) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (scope.scope_id, scope.scope_type, scope.authority_surface,
                 scope.session_dkn, scope.law_hash, scope.legend_hash,
                 scope.prior_scope_id, scope.timestamp),
            )
            self._conn.commit()
        except Exception:
            pass

    def get(self, scope_id: str) -> Optional[ProvenanceScope]:
        row = self._conn.execute(
            "SELECT * FROM scope_archive WHERE scope_id=?", (scope_id,)
        ).fetchone()
        return self._row_to_scope(row) if row else None

    def scopes_for_authority(self, authority_surface: str) -> list[ProvenanceScope]:
        """Return all scopes for a given mosaic_root, ordered by timestamp."""
        rows = self._conn.execute(
            "SELECT * FROM scope_archive WHERE authority_surface=? ORDER BY timestamp ASC",
            (authority_surface,),
        ).fetchall()
        return [self._row_to_scope(r) for r in rows]

    def latest_scope_id(self, authority_surface: str) -> str:
        """Return the scope_id of the most recent scope for authority_surface, or ''."""
        row = self._conn.execute(
            "SELECT scope_id FROM scope_archive WHERE authority_surface=? "
            "ORDER BY timestamp DESC LIMIT 1",
            (authority_surface,),
        ).fetchone()
        return row[0] if row else ""

    def session_is_in_scope(self, session_dkn: str, scope_id: str) -> bool:
        """True if session_dkn belongs to the given scope."""
        row = self._conn.execute(
            "SELECT scope_id FROM scope_archive WHERE session_dkn=? AND scope_id=?",
            (session_dkn, scope_id),
        ).fetchone()
        return row is not None

    @staticmethod
    def _row_to_scope(row) -> ProvenanceScope:
        (sid, stype, auth, dkn, lh, legh, prior, ts) = row
        return ProvenanceScope(
            scope_id=sid, scope_type=stype, authority_surface=auth,
            session_dkn=dkn, law_hash=lh, legend_hash=legh,
            prior_scope_id=prior, timestamp=ts,
        )


__all__ = ["ProvenanceScope", "ScopeArchive", "_CREATE_SCOPE_ARCHIVE"]
