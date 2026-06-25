"""ugk.cgp.runner.types — CGP runner type surface.

Frozen dataclasses for the CGPRunner Protocol surface. The Pattern A
types (ScenarioResult, SweepResult, ConvergenceFingerprint) re-export
the existing HR-UGK implementations from ugk.testing.headless_runner
unchanged. The Pattern B types (EvidenceArtifact, InterpretiveEvidencePack)
are new declarations for the canonical evidence-artifact shape that
coverage-dispatch runners and interpretive evidence packs produce.

Re-exported (Pattern A — impl in ugk.testing.headless_runner):
    ScenarioResult                pass/fail/skip/hang/refuse per scenario
    BatchResult                   per-batch aggregation
    SweepResult                   per-sweep aggregation
    ConvergenceFingerprint        typed fingerprint for HR-T-16
                                  anti-fabrication verification

New (canonical CGP runner types):
    ScenarioInput                 scenario specification for run_scenario
    EvidenceArtifact              per-invariant verdict + evidence
                                  (Pattern B / coverage-dispatch output)
    InterpretiveEvidencePack      Class III interpretive evidence
                                  (for caps requiring human/LLM judgment)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional, Any

# Re-export Pattern A types unchanged from the implementation module
from ugk.testing.headless_runner import (
    ScenarioResult,
    BatchResult,
    SweepResult,
    ConvergenceFingerprint,
)


@dataclass(frozen=True)
class ScenarioInput:
    """Specification for a single scenario run.

    The minimal CGP surface: a scenario is a callable plus an
    identifying name. Optional fields support HR-S-04 profile-based
    injection and HR-S-02 expected-receipt declarations.

    Fields:
        scenario_fn:   the scenario callable; receives a runner-
                       provided context per HR-S-04
        name:          identifying name for receipt emission and
                       result attribution
        profile:       optional EpistemicProfile (ops expected to be
                       emitted during the scenario)
        expected_ops:  optional tuple of op names expected to fire
                       (subset of HR-S-02 expectation surface)
        timeout_s:     optional per-scenario timeout
    """
    scenario_fn:   Callable[..., None]
    name:          str
    profile:       Optional[dict]              = None
    expected_ops:  Optional[tuple[str, ...]]   = None
    timeout_s:     Optional[float]             = None


@dataclass(frozen=True)
class EvidenceArtifact:
    """Per-invariant evidence verdict.

    Pattern B coverage-dispatch runners produce one EvidenceArtifact
    per binding in the coverage map. Pattern A scenario sweeps can
    also produce EvidenceArtifacts by mapping ScenarioResult outcomes
    onto invariant verdicts (one ScenarioResult → one or more
    EvidenceArtifacts).

    Verdict vocabulary (CTR-S-03 labeling discipline, AbleTools-aligned):
        PROVEN           the bound instrument returned success
        FAIL             the bound instrument returned failure
        GAP              declared but no resolvable evidence
        WAIVED           explicitly waived (with reason)
        BY-CONSTRUCTION  realized by the binding map itself
        NOT-RUN          binding exists; not executed this run
        ERROR            instrument errored (distinct from FAIL)

    Fields:
        invariant:       invariant identifier ("CGP-ESA-Cap-22" /
                         "UL-S-01" / etc.)
        verdict:         one of the seven verdicts above
        evidence_class:  e.g. "gate-suite", "scenario-sweep",
                         "coverage-map", "interpretive-pack"
        details:         free-text diagnostic
        scenario_result: optional ScenarioResult (Pattern A)
        instrument_exit: optional subprocess exit code (Pattern B)
    """
    invariant:       str
    verdict:         Literal["PROVEN", "FAIL", "GAP", "WAIVED",
                             "BY-CONSTRUCTION", "NOT-RUN", "ERROR"]
    evidence_class:  str
    details:         str                                = ""
    scenario_result: Optional[ScenarioResult]            = None
    instrument_exit: Optional[int]                       = None


@dataclass(frozen=True)
class InterpretiveEvidencePack:
    """Signed interpretive evidence for Class III capabilities.

    Capabilities whose evidence requires human or LLM judgment (per
    the CGP-ESA Class III definition: deterministic_layer +
    interpretive_layer) emit an InterpretiveEvidencePack alongside
    their deterministic EvidenceArtifact.

    Fields:
        cap_id:                 capability identifier
        interpretive_question:  the question the pack answers
        input_artifacts:        deterministic evidence the pack
                                interprets
        narrative:              prose response (human or LLM)
        classification:         cap-specific labels emitted by
                                the pack (e.g. "complete",
                                "partial-but-acceptable")
        citations:              external references the pack relies on
        signature:              signature over the canonical pack
                                serialization
        reviewer_authority:     "Governor" / "designated_auditor" /
                                "LLM_with_disclosure"
    """
    cap_id:                 str
    interpretive_question:  str
    input_artifacts:        tuple[EvidenceArtifact, ...]
    narrative:              str
    classification:         str
    citations:              tuple[str, ...]
    signature:              str
    reviewer_authority:     str


__all__ = [
    # Re-exports (Pattern A — impl in ugk.testing.headless_runner)
    "ScenarioResult",
    "BatchResult",
    "SweepResult",
    "ConvergenceFingerprint",
    # New canonical types
    "ScenarioInput",
    "EvidenceArtifact",
    "InterpretiveEvidencePack",
]
