"""ugk.integrity — Integrity Enforcement Layer (IEL), Phase 0 seed.

Phase 0 ratifies the shared VOCABULARY only (this module). It is deliberately the smallest
hard core — not the full IEL. Subsystems are migrated onto enforcement primitives in later
phases (see AD-23). The governing principle, confirmed against real code (finding #27,
`verify_stream_hash` linkage-only), is:

    THE CLAIM IS LARGER THAN THE PROOF.

Every verifier must state exactly what it established. `VerificationLevel` is that vocabulary;
`CorruptionKind` is the shared corruption taxonomy (corrupt is never silently downgraded to
missing — Invariant B).
"""
from ugk.integrity.levels import VerificationLevel, CorruptionKind, VerificationResult
from ugk.integrity.validation import ValidationResult
from ugk.integrity.transaction import MutationTransaction, MutationRefused, TransactionCommitError
from ugk.integrity.readonly import ReadOnlyGuard, ReadOnlyViolation
from ugk.integrity.context import ReceiptContext, ReceiptContextResolver, IntegrityContext

__all__ = ["VerificationLevel", "CorruptionKind", "VerificationResult",
           "ValidationResult", "MutationTransaction", "MutationRefused", "TransactionCommitError",
           "ReadOnlyGuard", "ReadOnlyViolation",
           "ReceiptContext", "ReceiptContextResolver", "IntegrityContext"]
