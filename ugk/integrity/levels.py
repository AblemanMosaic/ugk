"""Ratified integrity vocabulary (AD-23). Phase 0 of the Integrity Enforcement Layer.

A verifier must declare WHICH guarantee it established — never claim more than it proved.
Findings repeatedly showed verifiers whose name implied full verification while the proof was
narrower (e.g. #27: `verify_stream_hash` proves chain LINKAGE, not receipt BODY integrity).
"""
from __future__ import annotations
import enum
from dataclasses import dataclass
from typing import Optional


class VerificationLevel(enum.IntEnum):
    """What a verifier actually established, in increasing strength. Ordered so callers can
    require "at least BODY" etc. FULLY_VERIFIED is the release bar; anything less must be
    surfaced explicitly, never silently tolerated."""
    LINKAGE = 1          # chain ordering / parent linkage / no-truncation / no-relink
    BODY = 2             # each receipt's stored commitments recompute from its stored body
    CONTEXT = 3          # verified against receipt-TIME authority/policy/epoch (not live state)
    IDENTITY = 4         # identity bindings (keys, dkn, authority paths) checked
    QUORUM = 5           # validator-set / finality quorum verified
    FULLY_VERIFIED = 6   # all of the above established


class CorruptionKind(str, enum.Enum):
    """Shared corruption taxonomy (Invariant B: corrupt is never downgraded to missing).
    MISSING may bootstrap; everything else fails closed."""
    MISSING = "missing"          # state legitimately absent (may bootstrap)
    CORRUPT = "corrupt"          # present but integrity-broken (FAIL CLOSED)
    MALFORMED = "malformed"      # structurally unparseable
    FORGED = "forged"            # identifier/signature does not bind to claimed origin
    STALE = "stale"              # valid once, no longer current
    ORPHANED = "orphaned"        # references a parent/lineage that does not resolve
    AMBIGUOUS = "ambiguous"      # multiple conflicting interpretations
    UNVERIFIED = "unverified"    # not yet checked (absence of proof, not proof of absence)


@dataclass(frozen=True)
class VerificationResult:
    """The outcome of a verification: the level ACHIEVED, whether it met/exceeded the level
    REQUIRED, an optional corruption classification, and a human detail string."""
    achieved: VerificationLevel
    required: VerificationLevel
    corruption: Optional[CorruptionKind] = None
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.corruption is None and self.achieved >= self.required

    def __bool__(self) -> bool:
        return self.ok
