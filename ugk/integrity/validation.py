"""Preflight validation outcome (IEL / AD-23). Invariant A: no mutation before all refusal
conditions are known. A ValidationResult is produced by a subsystem's preflight check and handed
to MutationTransaction, which refuses to mutate unless ok."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from ugk.integrity.levels import CorruptionKind


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of preflight validation. ok=True means every refusal condition was checked and none
    fired; mutation may proceed. ok=False carries a CorruptionKind classification (fail closed)."""
    ok: bool
    corruption: Optional[CorruptionKind] = None
    detail: str = ""

    @staticmethod
    def valid(detail: str = "") -> "ValidationResult":
        return ValidationResult(True, None, detail)

    @staticmethod
    def invalid(corruption: CorruptionKind, detail: str = "") -> "ValidationResult":
        return ValidationResult(False, corruption, detail)

    def __bool__(self) -> bool:
        return self.ok
