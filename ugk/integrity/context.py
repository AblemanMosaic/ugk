"""Receipt-time context + the live integrity frame (IEL / AD-25).

ReceiptContextResolver addresses CONTEXT DRIFT: a receipt commits the law_hash and legend_hash in
force WHEN IT WAS WRITTEN; verification must bind to that receipt-time frame, not to whatever the
runtime now holds (which may have moved through amendments). IntegrityContext bundles the live frame
triad + genesis anchor + the required verification bar so subsystems pass one object."""
from __future__ import annotations
from dataclasses import dataclass

from ugk.integrity.levels import VerificationLevel


@dataclass(frozen=True)
class ReceiptContext:
    """The frame in force at the time a receipt was written, read from receipt-bound evidence."""
    law_hash: str
    legend_hash: str
    timestamp: float


class ReceiptContextResolver:
    @staticmethod
    def resolve(receipt) -> ReceiptContext:
        """Reconstruct the receipt-time frame from the receipt's own committed fields (not live state)."""
        return ReceiptContext(law_hash=receipt.law_hash,
                              legend_hash=receipt.legend_hash,
                              timestamp=receipt.timestamp)

    @staticmethod
    def drifted(receipt, *, live_law_hash: str, live_legend_hash: str) -> bool:
        """True if the receipt-time frame differs from the live frame (the receipt predates an
        amendment). Verification MUST still bind to the receipt-time frame; this only reports drift."""
        return receipt.law_hash != live_law_hash or receipt.legend_hash != live_legend_hash


@dataclass(frozen=True)
class IntegrityContext:
    """A read-only snapshot of the live constitutional frame the IEL operates against."""
    law_hash: str
    legend_hash: str
    schema_hash: str
    genesis_amendment_hash: str = ""
    required_level: VerificationLevel = VerificationLevel.BODY
