"""ugk/intent.py — Intent declarations and revocations (Grundnorm 444).

The will layer closes ALT disjunct (c): the teleological condition.
e ∈ Authority(A) ∧ e ∉ R_int(I_A) ⇒ laundered.

An authorized, admitted operation that was not declared as intended is
operationally laundered — legally clean in form, teleologically untethered.
IntentDeclaration closes the gap.

WILL-S-01: IntentDeclaration is content-addressed. Identity is its content hash.
           Silent edits are constitutionally impossible.
WILL-S-04: IntentRevocation is permanent. Revoked declarations never seed R_int.
WILL-S-09 (DI-WILL-09): DeclareIntent / RevokeIntent are Config-layer acts —
           not subject to coverage themselves (no regress).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

from ugk.storage.binding import canonical_json as _cj


# ---------------------------------------------------------------------------
# Refusal codes (WILL-S-03)
# ---------------------------------------------------------------------------

WL_001 = "WL-001"  # EFFECT_OUTSIDE_INTENT — non-empty R_int, op excluded
WL_002 = "WL-002"  # INTENT_DECLARATION_NOT_FOUND — unresolvable intent_ref
WL_003 = "WL-003"  # INTENT_REVOKED — only cover is a revoked declaration
WL_004 = "WL-004"  # INTENT_SCOPE_MALFORMED — scope cannot be evaluated
WL_005 = "WL-005"  # NO_ACTIVE_INTENT — empty R_int (fail-closed)


# ---------------------------------------------------------------------------
# IntentDeclaration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentDeclaration:
    """Content-addressed Config-layer intent artifact.

    declared_ops: the seed of R_int — ops the Governor declares as intended.
    scope_type:   "session" | "epoch" | "corpus" | "kernel"
    scope_ref:    session_dkn, law_hash, or "" (open scope, valid across sessions)
    authority:    mosaic_root of declaring Governor

    declaration_hash = SHA-256(canonical_json(all fields except declaration_hash))
    """
    declaration_hash: str
    declared_ops:     tuple    # op names (strings)
    scope_type:       str
    scope_ref:        str      # "" = open scope
    authority:        str      # mosaic_root
    timestamp:        str

    @staticmethod
    def create(
        declared_ops: list[str],
        authority:    str,
        scope_type:   str = "session",
        scope_ref:    str = "",
        timestamp:    Optional[str] = None,
    ) -> "IntentDeclaration":
        ts   = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        ops  = tuple(sorted(set(declared_ops)))
        body = {
            "authority":    authority,
            "declared_ops": list(ops),
            "scope_ref":    scope_ref,
            "scope_type":   scope_type,
            "timestamp":    ts,
        }
        dh = hashlib.sha256(_cj(body)).hexdigest()
        return IntentDeclaration(
            declaration_hash=dh, declared_ops=ops,
            scope_type=scope_type, scope_ref=scope_ref,
            authority=authority, timestamp=ts,
        )

    def verify_hash(self) -> bool:
        body = {
            "authority":    self.authority,
            "declared_ops": list(self.declared_ops),
            "scope_ref":    self.scope_ref,
            "scope_type":   self.scope_type,
            "timestamp":    self.timestamp,
        }
        return hashlib.sha256(_cj(body)).hexdigest() == self.declaration_hash

    def covers_op(self, op: str) -> bool:
        """True if op is in the literal declared set (depth=0 check)."""
        return op in self.declared_ops


# ---------------------------------------------------------------------------
# IntentRevocation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntentRevocation:
    """Permanent, unfalsifiable revocation of an IntentDeclaration.

    WILL-S-04: once revoked, the declaration never seeds R_int again.
    No un-revoke. No expiry.
    """
    revocation_hash:          str
    revoked_declaration_hash: str
    authority:                str   # must match original declaration authority
    timestamp:                str

    @staticmethod
    def create(
        revoked_declaration_hash: str,
        authority: str,
        timestamp: Optional[str] = None,
    ) -> "IntentRevocation":
        ts   = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = {
            "authority":                authority,
            "revoked_declaration_hash": revoked_declaration_hash,
            "timestamp":                ts,
        }
        rh = hashlib.sha256(_cj(body)).hexdigest()
        return IntentRevocation(
            revocation_hash=rh,
            revoked_declaration_hash=revoked_declaration_hash,
            authority=authority,
            timestamp=ts,
        )


# ---------------------------------------------------------------------------
# IntentStore
# ---------------------------------------------------------------------------

_CREATE_INTENTS = """
CREATE TABLE IF NOT EXISTS intent_declarations (
    declaration_hash  TEXT PRIMARY KEY,
    declared_ops_json TEXT NOT NULL DEFAULT '[]',
    scope_type        TEXT NOT NULL DEFAULT 'session',
    scope_ref         TEXT NOT NULL DEFAULT '',
    authority         TEXT NOT NULL DEFAULT '',
    timestamp         TEXT NOT NULL DEFAULT '',
    revoked           INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_REVOCATIONS = """
CREATE TABLE IF NOT EXISTS intent_revocations (
    revocation_hash          TEXT PRIMARY KEY,
    revoked_declaration_hash TEXT NOT NULL,
    authority                TEXT NOT NULL DEFAULT '',
    timestamp                TEXT NOT NULL DEFAULT ''
);
"""


class IntentStore:
    """Append-only store for IntentDeclarations and IntentRevocations.

    DI-WILL-09: DeclareIntent / RevokeIntent are not themselves subject to
    will coverage — they are Config-layer acts that terminate the potential
    infinite regress of intent-covers-its-own-declaration.
    """

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_CREATE_INTENTS)
        self._conn.execute(_CREATE_REVOCATIONS)
        self._conn.commit()

    def declare(self, declaration: IntentDeclaration) -> None:
        """Store an IntentDeclaration. Idempotent on duplicate hash."""
        ops_json = json.dumps(list(declaration.declared_ops), separators=(",", ":"))
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO intent_declarations "
                "(declaration_hash, declared_ops_json, scope_type, scope_ref, "
                " authority, timestamp) VALUES (?,?,?,?,?,?)",
                (declaration.declaration_hash, ops_json, declaration.scope_type,
                 declaration.scope_ref, declaration.authority, declaration.timestamp),
            )
            self._conn.commit()
        except Exception:
            pass

    def revoke(self, revocation: IntentRevocation) -> None:
        """Permanently revoke a declaration. Idempotent."""
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO intent_revocations "
                "(revocation_hash, revoked_declaration_hash, authority, timestamp) "
                "VALUES (?,?,?,?)",
                (revocation.revocation_hash, revocation.revoked_declaration_hash,
                 revocation.authority, revocation.timestamp),
            )
            self._conn.execute(
                "UPDATE intent_declarations SET revoked=1 WHERE declaration_hash=?",
                (revocation.revoked_declaration_hash,),
            )
            self._conn.commit()
        except Exception:
            pass

    def get(self, declaration_hash: str) -> Optional[IntentDeclaration]:
        """Retrieve a declaration by hash."""
        row = self._conn.execute(
            "SELECT declaration_hash, declared_ops_json, scope_type, scope_ref, "
            "authority, timestamp FROM intent_declarations WHERE declaration_hash=?",
            (declaration_hash,),
        ).fetchone()
        return self._row_to_declaration(row) if row else None

    def is_revoked(self, declaration_hash: str) -> bool:
        row = self._conn.execute(
            "SELECT revoked FROM intent_declarations WHERE declaration_hash=?",
            (declaration_hash,),
        ).fetchone()
        return bool(row and row[0])

    def active_declarations(self, scope_ref: str = "") -> list[IntentDeclaration]:
        """Return unrevoked declarations matching scope_ref (or open-scope ones).

        An open-scope declaration (scope_ref='') is active in any context.
        A scoped declaration is active only when its scope_ref matches.
        """
        rows = self._conn.execute(
            "SELECT declaration_hash, declared_ops_json, scope_type, scope_ref, "
            "authority, timestamp FROM intent_declarations "
            "WHERE revoked=0 AND (scope_ref='' OR scope_ref=?)",
            (scope_ref,),
        ).fetchall()
        return [self._row_to_declaration(r) for r in rows]

    def all_declarations(self) -> list[IntentDeclaration]:
        rows = self._conn.execute(
            "SELECT declaration_hash, declared_ops_json, scope_type, scope_ref, "
            "authority, timestamp FROM intent_declarations"
        ).fetchall()
        return [self._row_to_declaration(r) for r in rows]

    @staticmethod
    def _row_to_declaration(row) -> IntentDeclaration:
        dh, ops_json, stype, sref, auth, ts = row
        return IntentDeclaration(
            declaration_hash=dh,
            declared_ops=tuple(sorted(json.loads(ops_json))),
            scope_type=stype,
            scope_ref=sref,
            authority=auth,
            timestamp=ts,
        )


__all__ = [
    "IntentDeclaration", "IntentRevocation", "IntentStore",
    "WL_001", "WL_002", "WL_003", "WL_004", "WL_005",
]
