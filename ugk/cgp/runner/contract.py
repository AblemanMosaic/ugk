"""ugk.cgp.runner.contract — CGPRunner Protocol declaration.

Canonical execution-substrate contract for CGP consumers. Two
complementary patterns of execution evidence are unified under a
single Protocol:

  Pattern A — Scenario execution + checkpoint receipts
    Input:    scenario function or test module
    Process:  sweep through scenarios; write checkpoint receipts
              between them; aggregate into structured results
    Output:   ScenarioResult / SweepResult
              (pass/fail/skip/hang/refuse + receipt deltas +
               anomaly scores + checkpoint hashes)
    Reference impl: ugk.cgp.runner.headless.HeadlessRunner
                    (adapted from build4 lineage; substrate-clean,
                     no GUI dependency)

  Pattern B — Coverage-map dispatched instrument execution
    Input:    selector ("core" / "live" / "full")
    Process:  read codex-projected coverage_map; for each binding,
              spawn instrument as subprocess; collect verdict
    Output:   per-invariant verdict table (EvidenceArtifact tuple)
    Reference impl: AbleTools governed_runner (not in UGK)

The CGPRunner Protocol declares the minimum surface a CGP-conformant
runner must satisfy. Implementations may be classes (HeadlessRunner)
or structural (a module providing the right callables); the Protocol
is runtime_checkable.

Pattern A is the PREFERRED CGP evidence runner pattern (per ratified
Governor ruling) — but consumers with different shapes (Pattern B,
or hybrid) may implement the Protocol independently. The CTR
coverage-analysis layer (ugk.cgp.ctr) operates over either output.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable, Any, Callable, Optional

from ugk.cgp.runner.types import (
    ScenarioInput,
    ScenarioResult,
    SweepResult,
    EvidenceArtifact,
)


@runtime_checkable
class CGPRunner(Protocol):
    """Canonical CGP execution-substrate runner contract.

    A CGPRunner produces governed execution evidence. The minimum
    Pattern A surface (run_scenario / run_batch / assert_clean) is
    required; Pattern B surface (dispatch_coverage / coverage_report)
    is optional and may raise NotImplementedError on Pattern-A-only
    implementations.

    Existing implementations satisfying this contract (verified at
    runtime via isinstance against the Protocol):
      - ugk.cgp.runner.headless.HeadlessRunner   (Pattern A, full)
      - HR-Nav (Semantic Navigator HeadlessRunner v0.7) (Pattern A, full)
      - AbleTools governed_runner                 (Pattern B, scoped)

    The Protocol is runtime_checkable; `isinstance(my_runner, CGPRunner)`
    confirms minimum surface satisfaction.
    """

    # ------------------------------------------------------------------
    # Pattern A — scenario execution
    # ------------------------------------------------------------------
    def run_scenario(
        self,
        scenario_fn: Callable[..., None],
        *args: Any,
        **kwargs: Any,
    ) -> ScenarioResult:
        """Execute a single scenario; emit checkpoint receipts;
        return a structured ScenarioResult (HR-S-02)."""
        ...

    def run_gate_tests(self, module: Any) -> SweepResult:
        """Discover @gate_test-tagged functions on module and execute
        each as a scenario. Returns SweepResult aggregating outcomes
        (HR-S-06 governed test discovery)."""
        ...

    def assert_clean(
        self,
        result: SweepResult,
        allow_anomaly: bool = False,
    ) -> None:
        """Raise if the SweepResult contains any failure or (unless
        allow_anomaly) any anomaly score above zero. Idempotent
        assertion gate for scenario sweeps."""
        ...


__all__ = ["CGPRunner"]
