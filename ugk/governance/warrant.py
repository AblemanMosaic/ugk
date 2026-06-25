"""ugk/warrant.py — Decision Warrant infrastructure (Grundnorm layer, 444).

A DecisionWarrant records WHY an operation was admissible — not merely THAT
it was admitted. It is a first-class, content-addressed, reusable artifact.
Many receipts may cite one warrant via receipt.warrant_id.

Three-level audit hierarchy:
  Level 1 — Receipt:  what happened (existing receipt store)
  Level 2 — Warrant:  why it was admissible (this module)
  Level 3 — Lineage:  which prior warrants does this warrant depend on
                       (DAG traversal via WarrantStore)

Warrant body fields:
  warrant_hash:          SHA-256(canonical_json(body without warrant_hash))
  prior_warrant_hash:    chain link ("0"*64 for genesis warrant in session)
  constitutional_basis:  sorted list of CSIL integer addresses from LEGEND
                         (invariants that were satisfied)
  authority_result:      CSIL integer (9101 = authority_tier_sufficient)
  jurisdiction_result:   CSIL integer (9102 = jurisdiction_valid)
  result:                CSIL integer (9001 = ADMIT, 9002 = REFUSE)
  law_hash:              constitutional frame at time of warrant
  legend_hash:           projection vocabulary at time of warrant
  timestamp:             ISO-8601 UTC string

Amendment queries enabled by warrant store:
  "Which receipts depended on CM-GS-01 (CSIL:1008) before law_hash X?"
  → receipts WHERE warrant_id IN
      (warrants WHERE constitutional_basis CONTAINS 1008 AND law_hash = X)

  "What constitutional basis changed between law_hash A and B?"
  → DIFF of warrant basis sets across law_hash boundary

Warrant production (caller-declared, not automatic):
  kernel.execute(op=..., warrant_basis=[1008, 1010, 1003])
  Returns warrant_hash in the receipt's warrant_id field.
  No warrant_basis → no warrant produced (normal receipt only).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Optional

from ugk.storage.binding import canonical_json as _cj


# ---------------------------------------------------------------------------
# Result CSIL addresses (from LEGEND tier "warrant_result")
# ---------------------------------------------------------------------------

RESULT_ADMIT               = 9001
RESULT_REFUSE              = 9002
ANALYSIS_AUTH_SUFFICIENT   = 9101
ANALYSIS_JURIS_VALID       = 9102
ANALYSIS_INV_SATISFIED     = 9103

GENESIS_WARRANT_HASH: str = "0" * 64


class WarrantStoreError(Exception):
    """Raised when a DecisionWarrant cannot be durably materialized."""


# ---------------------------------------------------------------------------
# DecisionWarrant
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionWarrant:
    """Content-addressed decision warrant.

    warrant_hash = SHA-256(canonical_json of all other fields, sorted keys).
    """
    warrant_hash:          str
    prior_warrant_hash:    str          # chain link; GENESIS_WARRANT_HASH for first
    constitutional_basis:  tuple        # sorted CSIL ints from LEGEND (invariants satisfied)
    authority_result:      int          # CSIL int: 9101 = sufficient
    jurisdiction_result:   int          # CSIL int: 9102 = valid
    result:                int          # CSIL int: 9001 = ADMIT | 9002 = REFUSE
    law_hash:              str
    legend_hash:           str
    timestamp:             str

    @staticmethod
    def create(
        constitutional_basis:  list[int],
        law_hash:              str,
        legend_hash:           str,
        prior_warrant_hash:    str = GENESIS_WARRANT_HASH,
        authority_result:      int = ANALYSIS_AUTH_SUFFICIENT,
        jurisdiction_result:   int = ANALYSIS_JURIS_VALID,
        result:                int = RESULT_ADMIT,
        timestamp:             Optional[str] = None,
    ) -> "DecisionWarrant":
        """Create and hash a DecisionWarrant."""
        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        basis = tuple(sorted(constitutional_basis))
        body = {
            "authority_result":     authority_result,
            "constitutional_basis": list(basis),
            "jurisdiction_result":  jurisdiction_result,
            "law_hash":             law_hash,
            "legend_hash":          legend_hash,
            "prior_warrant_hash":   prior_warrant_hash,
            "result":               result,
            "timestamp":            ts,
        }
        wh = hashlib.sha256(_cj(body)).hexdigest()
        return DecisionWarrant(
            warrant_hash=wh,
            prior_warrant_hash=prior_warrant_hash,
            constitutional_basis=basis,
            authority_result=authority_result,
            jurisdiction_result=jurisdiction_result,
            result=result,
            law_hash=law_hash,
            legend_hash=legend_hash,
            timestamp=ts,
        )

    def body_dict(self) -> dict:
        """Canonical body dict (excludes warrant_hash; used for hash verification)."""
        return {
            "authority_result":     self.authority_result,
            "constitutional_basis": list(self.constitutional_basis),
            "jurisdiction_result":  self.jurisdiction_result,
            "law_hash":             self.law_hash,
            "legend_hash":          self.legend_hash,
            "prior_warrant_hash":   self.prior_warrant_hash,
            "result":               self.result,
            "timestamp":            self.timestamp,
        }

    def verify_hash(self) -> bool:
        """Recompute warrant_hash and verify it matches."""
        expected = hashlib.sha256(_cj(self.body_dict())).hexdigest()
        return self.warrant_hash == expected

    def cites_invariant(self, csil_id: int) -> bool:
        """True if this warrant's constitutional basis includes csil_id."""
        return csil_id in self.constitutional_basis


# ---------------------------------------------------------------------------
# WarrantStore
# ---------------------------------------------------------------------------

_CREATE_WARRANTS = """
CREATE TABLE IF NOT EXISTS warrants (
    warrant_hash        TEXT PRIMARY KEY,
    prior_warrant_hash  TEXT    NOT NULL DEFAULT '',
    constitutional_basis TEXT   NOT NULL DEFAULT '[]',
    authority_result    INTEGER NOT NULL DEFAULT 9101,
    jurisdiction_result INTEGER NOT NULL DEFAULT 9102,
    result              INTEGER NOT NULL DEFAULT 9001,
    law_hash            TEXT    NOT NULL DEFAULT '',
    legend_hash         TEXT    NOT NULL DEFAULT '',
    timestamp           TEXT    NOT NULL DEFAULT ''
);
"""


class WarrantStore:
    """Append-only store for DecisionWarrants. Backed by SQLite (in-memory default).

    Public API:
      write(warrant)                        → str (warrant_hash; raises WarrantStoreError on non-durable write)
      get(warrant_hash)                     → Optional[DecisionWarrant]
      all_warrants()                        → list[DecisionWarrant]
      basis_query(csil_id)                  → list[DecisionWarrant]
      basis_query_for_law(csil_id, law_hash)→ list[DecisionWarrant]
      lineage_from(warrant_hash)            → list[DecisionWarrant]
      is_acyclic()                          → bool
      warrant_count()                       → int
    """

    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_CREATE_WARRANTS)
        self._conn.commit()
        self._prior_hash: str = GENESIS_WARRANT_HASH

    def write(self, warrant: DecisionWarrant) -> str:
        """Append a warrant and verify it is durably readable.

        Duplicate warrant_hash values remain idempotent, but write failures are
        load-bearing: callers must not emit a receipt pointing at a warrant that
        was not materialized.
        """
        if not isinstance(warrant, DecisionWarrant):
            raise WarrantStoreError("write() requires a DecisionWarrant")
        if not warrant.verify_hash():
            raise WarrantStoreError("warrant_hash does not verify")
        basis_json = json.dumps(list(warrant.constitutional_basis), separators=(",", ":"))
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO warrants "
                "(warrant_hash, prior_warrant_hash, constitutional_basis, "
                " authority_result, jurisdiction_result, result, "
                " law_hash, legend_hash, timestamp) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (warrant.warrant_hash, warrant.prior_warrant_hash, basis_json,
                 warrant.authority_result, warrant.jurisdiction_result,
                 warrant.result, warrant.law_hash, warrant.legend_hash,
                 warrant.timestamp),
            )
            self._conn.commit()
        except Exception as exc:
            raise WarrantStoreError("warrant write failed: %s" % exc) from exc
        stored = self.get(warrant.warrant_hash)
        if stored is None or stored.body_dict() != warrant.body_dict():
            raise WarrantStoreError("warrant write did not materialize durably")
        return warrant.warrant_hash

    def get(self, warrant_hash: str) -> Optional[DecisionWarrant]:
        """Retrieve a warrant by its hash."""
        row = self._conn.execute(
            "SELECT * FROM warrants WHERE warrant_hash = ?", (warrant_hash,)
        ).fetchone()
        return self._row_to_warrant(row) if row else None

    def all_warrants(self) -> list[DecisionWarrant]:
        """Return all warrants in insertion order."""
        rows = self._conn.execute("SELECT * FROM warrants").fetchall()
        return [self._row_to_warrant(r) for r in rows]

    def basis_query(self, csil_id: int) -> list[DecisionWarrant]:
        """Return all warrants whose constitutional_basis contains csil_id."""
        # Load all warrants and filter in Python — warrant stores are small,
        # and JSON-in-SQLite integer array membership is error-prone with LIKE.
        return [w for w in self.all_warrants() if csil_id in w.constitutional_basis]

    def basis_query_for_law(self, csil_id: int, law_hash: str) -> list[DecisionWarrant]:
        """Return warrants citing csil_id under a specific law_hash."""
        return [w for w in self.basis_query(csil_id) if w.law_hash == law_hash]

    def lineage_from(self, warrant_hash: str,
                     max_depth: int = 100) -> list[DecisionWarrant]:
        """Return the chain of warrants from warrant_hash back to genesis.

        Traverses prior_warrant_hash links. Returns in reverse-chronological order
        (most recent first). Stops at GENESIS_WARRANT_HASH or max_depth.
        """
        result = []
        current_hash = warrant_hash
        visited: set[str] = set()
        depth = 0
        while (current_hash and
               current_hash != GENESIS_WARRANT_HASH and
               current_hash not in visited and
               depth < max_depth):
            visited.add(current_hash)
            w = self.get(current_hash)
            if w is None:
                break
            result.append(w)
            current_hash = w.prior_warrant_hash
            depth += 1
        return result

    def is_acyclic(self) -> bool:
        """Verify the warrant DAG has no cycles via prior_warrant_hash links.

        Uses DFS with a visited+in-stack check. Returns True iff acyclic.
        """
        warrants = self.all_warrants()
        if not warrants:
            return True
        by_hash = {w.warrant_hash: w for w in warrants}
        visited: set[str] = set()
        in_stack: set[str] = set()

        def _dfs(wh: str) -> bool:
            if wh in in_stack:
                return False  # cycle detected
            if wh in visited or wh == GENESIS_WARRANT_HASH:
                return True
            in_stack.add(wh)
            w = by_hash.get(wh)
            if w and w.prior_warrant_hash != GENESIS_WARRANT_HASH:
                if not _dfs(w.prior_warrant_hash):
                    return False
            in_stack.discard(wh)
            visited.add(wh)
            return True

        return all(_dfs(w.warrant_hash) for w in warrants)

    def warrant_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM warrants").fetchone()[0]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "WarrantStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False

    @staticmethod
    def _row_to_warrant(row) -> DecisionWarrant:
        (wh, prior, basis_json, auth_r, juris_r, result, lh, leg_h, ts) = row
        basis = tuple(sorted(json.loads(basis_json)))
        return DecisionWarrant(
            warrant_hash=wh,
            prior_warrant_hash=prior,
            constitutional_basis=basis,
            authority_result=auth_r,
            jurisdiction_result=juris_r,
            result=result,
            law_hash=lh,
            legend_hash=leg_h,
            timestamp=ts,
        )


def create_refusal_warrant(
    constitutional_basis: list[int],
    law_hash: str,
    legend_hash: str,
    prior_warrant_hash: str = GENESIS_WARRANT_HASH,
) -> DecisionWarrant:
    """Convenience factory for refusal warrants."""
    return DecisionWarrant.create(
        constitutional_basis=constitutional_basis,
        law_hash=law_hash,
        legend_hash=legend_hash,
        prior_warrant_hash=prior_warrant_hash,
        authority_result=ANALYSIS_AUTH_SUFFICIENT,
        jurisdiction_result=ANALYSIS_JURIS_VALID,
        result=RESULT_REFUSE,
    )


__all__ = [
    "DecisionWarrant", "WarrantStore",
    "WarrantStoreError",
    "RESULT_ADMIT", "RESULT_REFUSE",
    "ANALYSIS_AUTH_SUFFICIENT", "ANALYSIS_JURIS_VALID",
    "ANALYSIS_INV_SATISFIED",
    "GENESIS_WARRANT_HASH",
    "create_refusal_warrant",
]
