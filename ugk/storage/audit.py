"""ugk/audit.py — AuditSession: governed read-only audit entrypoint (Grundnorm 444).

AUDIT-S-01: AuditSession is strictly read-only. It must never call store.write(),
kernel.execute(), or any method that produces receipts, warrants, or modifications
to any store. Enforced behaviorally by audit_session_gate (receipt count invariant).

Usage:
    session = AuditSession.open(state_dir)
    receipts = session.receipts_in_session(session_dkn)
    warrants = session.warrants_for_invariant(csil_id)
    receipts = session.receipts_for_warrant(warrant_hash)
    ok = session.verify_full_chain()
    att = session.attest()
    session.close()
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


class LegendNotResolvable(Exception):
    """Raised when a receipt's legend_hash cannot be resolved to legend entries."""
    def __init__(self, legend_hash: str):
        self.legend_hash = legend_hash
        super().__init__(
            f"LegendNotResolvable: legend_hash {legend_hash[:16]!r}… is not in the "
            f"legend_archive and does not match the current LEGEND_HASH. "
            f"Provide the historical binding.py or export the legend archive."
        )


class AuditSession:
    """Read-only governed audit surface over UGKReceiptStore + WarrantStore.

    Opens both stores from state_dir. Provides a unified query API.
    Never writes. All public methods are queries; none produce side effects.

    AUDIT-S-01 enforcement: audit_session_gate calls all public methods and
    asserts that receipt_count() and warrant_count() are unchanged afterward.
    """

    def __init__(self, receipt_store, warrant_store=None):
        self._rs = receipt_store
        self._ws = warrant_store

    @classmethod
    def open(cls, state_dir: str) -> "AuditSession":
        """Open an AuditSession from a state directory.

        Loads ugk.db (receipts + legend_archive) and ugk_warrants.db (warrants)
        if present. Validates legend consistency for all unique legend_hashes in
        the receipt store.
        """
        from ugk.storage.store import UGKReceiptStore
        from ugk.governance.warrant import WarrantStore

        state = Path(state_dir)
        receipt_db = str(state / "ugk.db")
        warrant_db = str(state / "ugk_warrants.db")

        if not os.path.exists(receipt_db):
            raise FileNotFoundError(
                f"AuditSession.open: no ugk.db found at {receipt_db}"
            )

        rs = UGKReceiptStore(db_path=receipt_db)
        ws = WarrantStore(db_path=warrant_db) if os.path.exists(warrant_db) else None

        session = cls(rs, ws)

        # Validate legend consistency — raise early if any legend_hash is unresolvable
        for lh in session._unique_legend_hashes():
            if lh and rs.resolve_legend(lh) is None:
                raise LegendNotResolvable(lh)

        return session

    # ------------------------------------------------------------------
    # Chain integrity
    # ------------------------------------------------------------------

    def verify_full_chain(self) -> bool:
        """Verify the full receipt chain integrity. O(n)."""
        return self._rs.verify_stream_hash()

    def attest(self) -> dict:
        """Return a 3+1 hash attestation proof over the stored chain."""
        from ugk.storage.binding import LEGEND_HASH
        snap_hash = self._rs.stream_hash()
        chain_ok  = self._rs.verify_stream_hash()
        receipts  = self._rs.all_receipts()
        law_hashes   = {r.law_hash    for r in receipts if r.law_hash}
        legend_hashes = {r.legend_hash for r in receipts if r.legend_hash}
        return {
            "stream_hash":     snap_hash,
            "hash_verified":   chain_ok,
            "receipt_count":   self._rs.receipt_count(),
            "law_hashes":      sorted(law_hashes),
            "legend_hashes":   sorted(legend_hashes),
            "current_legend":  LEGEND_HASH,
        }

    # ------------------------------------------------------------------
    # Receipt queries
    # ------------------------------------------------------------------

    def receipts_in_session(self, session_dkn: str):
        """Return all receipts in a given session (by session_dkn)."""
        return [r for r in self._rs.all_receipts()
                if r.session_dkn == session_dkn]

    def receipts_for_warrant(self, warrant_hash: str):
        """Return all receipts that cite a given warrant_hash."""
        return [r for r in self._rs.all_receipts()
                if r.warrant_id == warrant_hash]

    def receipts_by_law_hash(self, law_hash: str):
        """Return all receipts governed under a specific law_hash."""
        return [r for r in self._rs.all_receipts() if r.law_hash == law_hash]

    def all_receipts(self):
        return self._rs.all_receipts()

    # ------------------------------------------------------------------
    # Warrant queries (requires WarrantStore)
    # ------------------------------------------------------------------

    def warrants_for_invariant(self, csil_id: int):
        """Return all warrants whose constitutional_basis contains csil_id."""
        if self._ws is None:
            return []
        return self._ws.basis_query(csil_id)

    def warrants_for_invariant_and_law(self, csil_id: int, law_hash: str):
        """Return warrants citing csil_id under a specific law_hash."""
        if self._ws is None:
            return []
        return self._ws.basis_query_for_law(csil_id, law_hash)

    def warrant_lineage(self, warrant_hash: str):
        """Return the warrant lineage chain from warrant_hash to genesis."""
        if self._ws is None:
            return []
        return self._ws.lineage_from(warrant_hash)

    def all_warrants(self):
        if self._ws is None:
            return []
        return self._ws.all_warrants()

    # ------------------------------------------------------------------
    # Legend
    # ------------------------------------------------------------------

    def resolve_legend(self, legend_hash: str):
        """Return the legend entries for a given legend_hash, or raise."""
        entries = self._rs.resolve_legend(legend_hash)
        if entries is None:
            raise LegendNotResolvable(legend_hash)
        return entries

    def expand_receipt(self, receipt) -> dict:
        """Return receipt fields with CSIL integers expanded via the correct legend.
        Fields already contain canonical strings (store expands on read);
        this method returns a structured dict with legend metadata attached.
        """
        from ugk.storage.binding import LEGEND_HASH
        return {
            "op":            receipt.op,
            "intent":        receipt.intent,
            "jurisdiction":  receipt.jurisdiction,
            "confidence":    receipt.confidence,
            "authority":     receipt.authority,
            "timestamp":     receipt.timestamp,
            "failed":        receipt.failed,
            "law_hash":      receipt.law_hash,
            "legend_hash":   receipt.legend_hash,
            "warrant_id":    receipt.warrant_id,
            "h_r":           receipt.h_r,   # RT-1b (E5b Tier 1): additive M2 analog; legacy kept
            "session_dkn":   receipt.session_dkn,
            "legend_current": receipt.legend_hash == LEGEND_HASH,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _unique_legend_hashes(self) -> set:
        rows = self._rs._conn.execute(
            "SELECT DISTINCT legend_hash FROM receipts WHERE legend_hash != ''"
        ).fetchall()
        return {row[0] for row in rows}

    def close(self) -> None:
        self._rs.close()
        if self._ws is not None:
            try:
                self._ws._conn.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


__all__ = ["AuditSession", "LegendNotResolvable"]
