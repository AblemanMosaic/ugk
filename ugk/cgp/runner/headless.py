"""ugk.cgp.runner.headless — canonical CGP-facing HeadlessRunner surface.

Re-exports the existing HeadlessRunner implementation from
``ugk.testing.headless_runner`` unchanged. This module is the
canonical CGP-facing import path; the implementation module remains
valid as a compatibility alias.

Canonical import:
    from ugk.cgp.runner.headless import HeadlessRunner
    from ugk.cgp.runner import HeadlessRunner       # also valid

Compatibility alias (preserved, no deprecation):
    from ugk.testing.headless_runner import HeadlessRunner
    from ugk.testing import HeadlessRunner

HeadlessRunner is the reference Pattern A implementation of the
CGPRunner Protocol. 16 canonical methods (HR Domain Codex v0.5):

  Scenario / batch execution:
    1.  run_scenario(scenario_fn, profile)      -> ScenarioResult
    2.  run_batch(scenarios)                    -> BatchResult
    3.  run_gate_tests(module)                  -> SweepResult

  Domain sweeps:
    4.  structural_sweep(target)                -> SweepResult
    5.  cap52_sweep(target)                     -> SweepResult
    6.  with_warm_corpus(n_files)               -> SweepResult
    7.  filesystem_sweep(target)                -> SweepResult
    8.  epistemic_sweep(target)                 -> SweepResult

  Assertion + introspection:
    9.  assert_clean(result)                    -> None (raises)
    10. snapshot_at(checkpoint_hash)            -> dict
    11. verify_stream_hash(from_checkpoint)     -> bool
    12. make_epistemic_profile(name, ops)       -> dict
    13. get_receipt_delta(result)               -> int
    14. get_anomaly_score(result)               -> float
    15. get_checkpoint_hashes(result)           -> list[str]
    16. verify_convergence_fingerprint(store,
                                       fingerprint) -> bool

Per HR-S-01 (Real Machinery Execution): receipts are written to the
actual UGK receipt store; no simulation.
"""
from ugk.testing.headless_runner import (
    HeadlessRunner,
    ScenarioResult,
    BatchResult,
    SweepResult,
    ConvergenceFingerprint,
)

__all__ = [
    "HeadlessRunner",
    "ScenarioResult",
    "BatchResult",
    "SweepResult",
    "ConvergenceFingerprint",
]
