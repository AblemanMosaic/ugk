"""ugk.cgp.ctr — canonical CGP-facing CTR surface.

Constitutional Test Runner discipline (CTR-S-01..09 per the CTR
Domain Codex v0.6 implemented by UGK). This module is the canonical
CGP-facing import path; the implementation lives at ``ugk.ctr`` and
remains valid as a compatibility alias.

CTR is RUNNER-AGNOSTIC COVERAGE DISCIPLINE. It does not execute tests;
it analyses a population of tests for governance coverage. The
discovery and execution are the responsibility of a CGPRunner
implementation (e.g., HeadlessRunner from ugk.cgp.runner) or any
other test executor (pytest, etc.).

Public surface:

    gate_test(invariant, evidence_class, super_family, sub_family,
              ...)
        Decorator that tags a function as bound to a governance
        invariant (CTR-S-01 Test-Invariant Binding).

    CoverageReport
        Structured governance coverage analysis result. The
        ``evidence_source`` field is mandatory (CTR-T-13) and must be
        explicitly set to one of e.g. ``"governed_receipt_chain"``,
        ``"pytest_plugin"``, or ``"coverage_map_dispatch"``.

    CTR
        The runner-agnostic coverage analyzer.

            ctr = CTR(required_invariants={...})
            tests = ctr.discover(test_module)
            report = ctr.analyse(
                test_functions=tests,
                evidence_source="governed_receipt_chain",
                all_module_callables=...
            )
            # report is a CoverageReport (CTR-S-02 Coverage Reporting)

Canonical import:
    from ugk.cgp.ctr import gate_test, CTR, CoverageReport

Compatibility alias (preserved, no deprecation):
    from ugk.ctr import gate_test, CTR, CoverageReport

See ``ugk/docs/CGP_EXECUTION_SUBSTRATE.md`` for orientation on how
CTR fits with CGPRunner and capability_evidence.
"""
from ugk.ctr import (
    gate_test,
    CoverageReport,
    CTR,
)

__all__ = ["gate_test", "CoverageReport", "CTR"]
