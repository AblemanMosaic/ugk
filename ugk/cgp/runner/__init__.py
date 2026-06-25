"""ugk.cgp.runner — canonical CGP-facing execution-substrate surface.

The canonical import path for CGP execution-substrate consumers:

    from ugk.cgp.runner import HeadlessRunner       # reference impl
    from ugk.cgp.runner import CGPRunner            # Protocol
    from ugk.cgp.runner import ScenarioInput, ScenarioResult, SweepResult
    from ugk.cgp.runner import EvidenceArtifact, InterpretiveEvidencePack
    from ugk.cgp.runner import ConvergenceFingerprint

Two execution patterns are supported by the same Protocol:

  Pattern A — scenario execution + checkpoint receipts
    HeadlessRunner (Pattern A reference implementation, full)

  Pattern B — coverage-map dispatched instruments
    External implementations (e.g., AbleTools governed_runner);
    structurally conformant via the CGPRunner Protocol

The CGPRunner Protocol is runtime_checkable; any object exposing
the minimum surface (run_scenario, run_gate_tests, assert_clean)
satisfies it. Use ``isinstance(my_runner, CGPRunner)`` to verify.

See ``ugk/docs/CGP_EXECUTION_SUBSTRATE.md`` for orientation.
"""
from ugk.cgp.runner.contract import CGPRunner
from ugk.cgp.runner.types import (
    ScenarioInput,
    ScenarioResult,
    BatchResult,
    SweepResult,
    ConvergenceFingerprint,
    EvidenceArtifact,
    InterpretiveEvidencePack,
)
from ugk.cgp.runner.headless import HeadlessRunner

__all__ = [
    # Contract
    "CGPRunner",
    # Reference impl
    "HeadlessRunner",
    # Types
    "ScenarioInput",
    "ScenarioResult",
    "BatchResult",
    "SweepResult",
    "ConvergenceFingerprint",
    "EvidenceArtifact",
    "InterpretiveEvidencePack",
]
