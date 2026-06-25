"""
UGK Lite — Constitutional Test Runner (CTR)
TV-S-01..05: Testing invariants
CTR-S-01..09: CTR domain invariants

gate_test decorator: binds invariant metadata to test functions.
CTR: analyses test corpus for governance coverage.
CoverageReport: structured coverage analysis result.

CTR-S-09: evidence_source is mandatory — always declared, never None.
CTR-T-13: CoverageReport.evidence_source is always populated.
AMB-B4-02: HeadlessRunner instantiates CTR internally in run_gate_tests().
           Callers do not inject a CTR instance.
           Internal CTR receives evidence_source='governed_receipt_chain'.

D-TV-06 advisory: warn on untagged tests during initial corpus build.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ------------------------------------------------------------------
# gate_test decorator (CTR-S-01: Test-Invariant Binding)
# ------------------------------------------------------------------

def gate_test(
    invariant: str,
    evidence_class: str,
    super_family: str,
    sub_family: str = "",
    description: str = "",
) -> Callable:
    """
    Decorator that binds constitutional metadata to a test function.

    invariant:      e.g. "UL-S-01", "EH-S-02", "DM-S-03"
    evidence_class: behavioral | governance | negative | structural | performance
    super_family:   realization | reconstruction | representativeness | counterfactual
    sub_family:     optional finer classification within super_family
    description:    human-readable test purpose

    CTR-S-01: Test-Invariant Binding.
    CTR-S-03: Labeling Discipline — undecorated tests trigger D-TV-06 advisory.
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        wrapper._gate_test = True
        wrapper._invariant = invariant
        wrapper._evidence_class = evidence_class
        wrapper._super_family = super_family
        wrapper._sub_family = sub_family
        wrapper._description = description or fn.__doc__ or ""
        return wrapper
    return decorator


# ------------------------------------------------------------------
# CoverageReport (CTR-S-02)
# ------------------------------------------------------------------

@dataclass
class CoverageReport:
    """
    Structured governance coverage analysis result.
    CTR-T-13: evidence_source is always populated — never None.
    """
    evidence_source: str
    total_tests: int
    tagged_tests: int
    untagged_tests: int
    coverage_ratio: float
    invariants_covered: set
    invariants_missing: set
    evidence_classes_present: set
    gaps: list
    super_family_coverage: dict
    warnings: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.evidence_source is None:
            raise ValueError(
                "CTR-T-13 violation: CoverageReport.evidence_source must not be None."
            )


# ------------------------------------------------------------------
# CTR (CTR-S-01..09)
# ------------------------------------------------------------------

_PROOF_REQUIREMENTS: dict[str, set[str]] = {
    "UL-S-":   {"behavioral", "governance"},
    "S-":      {"behavioral", "governance"},
    "DM-S-":   {"behavioral", "governance"},
    "EH-S-":   {"behavioral", "governance", "negative"},
    "ST-S-":   {"behavioral", "governance", "negative"},
    "PC-S-":   {"behavioral", "performance"},
    "TV-S-":   {"structural", "behavioral"},
    "GK-S-":   {"behavioral", "governance"},
    "GK-THIN-": {"behavioral", "governance"},
}


def _prefix_for(invariant: str) -> Optional[str]:
    for prefix in sorted(_PROOF_REQUIREMENTS.keys(), key=len, reverse=True):
        if invariant.startswith(prefix):
            return prefix
    return None


class CTR:
    """
    Constitutional Test Runner.
    CTR-S-01..09 as specified in CTR Domain Codex v0.6.
    """

    def __init__(self, required_invariants: Optional[set] = None):
        self._required_invariants: set = required_invariants or set()

    def discover(self, module: Any) -> list:
        tests = []
        for name in dir(module):
            obj = getattr(module, name, None)
            if callable(obj) and getattr(obj, "_gate_test", False):
                tests.append(obj)
        return tests

    def analyse(
        self,
        test_functions: list,
        evidence_source: str,
        all_module_callables: Optional[list] = None,
    ) -> CoverageReport:
        """
        CTR-T-13: evidence_source is mandatory at call site.
        """
        if evidence_source is None:
            raise ValueError(
                "CTR-T-13: evidence_source is mandatory. "
                "Pass 'governed_receipt_chain' or 'pytest_plugin' explicitly."
            )

        tagged = [fn for fn in test_functions if getattr(fn, "_gate_test", False)]
        all_callables = all_module_callables or test_functions
        test_callables = [fn for fn in all_callables
                          if callable(fn) and fn.__name__.startswith("test_")]
        untagged = [fn for fn in test_callables
                    if not getattr(fn, "_gate_test", False)]

        total = len(test_callables)
        tagged_count = len(tagged)
        untagged_count = len(untagged)
        coverage_ratio = tagged_count / total if total > 0 else 0.0

        inv_evidence: dict[str, set] = {}
        super_family_coverage: dict[str, list] = {
            "realization": [], "reconstruction": [],
            "representativeness": [], "counterfactual": [],
        }

        for fn in tagged:
            inv = fn._invariant
            ec = fn._evidence_class
            sf = fn._super_family
            inv_evidence.setdefault(inv, set()).add(ec)
            if sf in super_family_coverage:
                super_family_coverage[sf].append(inv)

        invariants_covered = set(inv_evidence.keys())
        invariants_missing = self._required_invariants - invariants_covered

        # CTR-S-06: Evidence-Path Completeness — gap detection
        gaps: list[dict] = []
        seen_invs: set[str] = set()

        for inv, present_classes in inv_evidence.items():
            if inv in seen_invs:
                continue
            seen_invs.add(inv)
            prefix = _prefix_for(inv)
            if prefix is None:
                continue
            required = _PROOF_REQUIREMENTS[prefix]
            missing_classes = required - present_classes
            if missing_classes:
                gaps.append({
                    "invariant": inv,
                    "present": sorted(present_classes),
                    "missing": sorted(missing_classes),
                    "required": sorted(required),
                })

        for inv in self._required_invariants:
            if inv not in seen_invs:
                prefix = _prefix_for(inv)
                required = _PROOF_REQUIREMENTS.get(prefix, set()) if prefix else set()
                gaps.append({
                    "invariant": inv,
                    "present": [],
                    "missing": sorted(required) if required else ["any"],
                    "required": sorted(required) if required else ["any"],
                })

        all_evidence_classes = {fn._evidence_class for fn in tagged}

        warnings: list[str] = []
        for fn in untagged:
            warnings.append(
                f"D-TV-06: test {fn.__name__!r} has no @gate_test decoration"
            )

        return CoverageReport(
            evidence_source=evidence_source,
            total_tests=total,
            tagged_tests=tagged_count,
            untagged_tests=untagged_count,
            coverage_ratio=coverage_ratio,
            invariants_covered=invariants_covered,
            invariants_missing=invariants_missing,
            evidence_classes_present=all_evidence_classes,
            gaps=gaps,
            super_family_coverage=super_family_coverage,
            warnings=warnings,
        )
