"""ugk/summary.py — SessionSummary: aggregate session closure document (Grundnorm 444).

SUM-S-01: SessionSummary is produced at close_session() when a WarrantStore is
attached. Summarizes receipt/warrant/refusal counts. Independently verifiable.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from ugk.storage.binding import canonical_json as _cj


@dataclass(frozen=True)
class SessionSummary:
    """Aggregate closure document for a governed session."""
    summary_hash:    str
    session_dkn:     str
    receipt_count:   int
    warrant_count:   int
    refusal_count:   int
    admitted_count:  int
    final_stream_hash: str
    law_hash:        str
    legend_hash:     str
    phase_code:      str
    timestamp:       str

    @staticmethod
    def create(
        session_dkn:      str,
        receipt_count:    int,
        warrant_count:    int,
        refusal_count:    int,
        admitted_count:   int,
        final_stream_hash: str,
        law_hash:         str,
        legend_hash:      str,
        phase_code:       str,
        timestamp:        Optional[str] = None,
    ) -> "SessionSummary":
        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = {
            "admitted_count":    admitted_count,
            "final_stream_hash": final_stream_hash,
            "law_hash":          law_hash,
            "legend_hash":       legend_hash,
            "phase_code":        phase_code,
            "receipt_count":     receipt_count,
            "refusal_count":     refusal_count,
            "session_dkn":       session_dkn,
            "timestamp":         ts,
            "warrant_count":     warrant_count,
        }
        sh = hashlib.sha256(_cj(body)).hexdigest()
        return SessionSummary(
            summary_hash=sh, session_dkn=session_dkn,
            receipt_count=receipt_count, warrant_count=warrant_count,
            refusal_count=refusal_count, admitted_count=admitted_count,
            final_stream_hash=final_stream_hash,
            law_hash=law_hash, legend_hash=legend_hash,
            phase_code=phase_code, timestamp=ts,
        )

    def verify_hash(self) -> bool:
        body = {
            "admitted_count":    self.admitted_count,
            "final_stream_hash": self.final_stream_hash,
            "law_hash":          self.law_hash,
            "legend_hash":       self.legend_hash,
            "phase_code":        self.phase_code,
            "receipt_count":     self.receipt_count,
            "refusal_count":     self.refusal_count,
            "session_dkn":       self.session_dkn,
            "timestamp":         self.timestamp,
            "warrant_count":     self.warrant_count,
        }
        return hashlib.sha256(_cj(body)).hexdigest() == self.summary_hash

    def is_consistent_with(self, store, warrant_store=None) -> bool:
        """Verify the summary is consistent with the actual store state."""
        ok = (
            store.receipt_count()  == self.receipt_count  and
            store.refusal_count()  == self.refusal_count  and
            store.stream_hash()    == self.final_stream_hash
        )
        if warrant_store is not None:
            ok = ok and (warrant_store.warrant_count() == self.warrant_count)
        return ok


__all__ = ["SessionSummary"]
