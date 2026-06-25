"""grbsa_runtime.verification_adapter — VerificationAdapter (GRBSA verification domain, Phase 2).

In-process governed verifier domain. Mirrors the execution adapter discipline:
  - no ugk/ change, no kernel.py change;
  - reuses the shared ReceiptCore / ResultEnvelopeCore (no second receipt/envelope implementation);
  - success is a PREDICATE over receipt+envelope with anti-vacuity (D-7), never a stored field;
  - Category-Separation: domain='verification'.

Authority is EPHEMERAL (D-6): the verifier's output is a self-verifying proof artifact, not a
production governance act. It mints into an isolated, disposable chain and seals a content-addressed
claim; it does NOT promote CR-04 sites (D-5) and asserts NO substrate guarantee.
"""
from __future__ import annotations
from dataclasses import dataclass

from .gate_adapter import ReceiptCore, ResultEnvelopeCore


@dataclass(frozen=True)
class VerificationReceipt:
    core: ReceiptCore
    claim_id: str               # content-addressed conformance claim id
    authority_ref: str          # REFERENCE to the ephemeral verifier authority (never a value)
    outcome: str                # 'admitted' | 'refused' | 'failed'
    domain: str = "verification"


@dataclass(frozen=True)
class VerificationResultEnvelope:
    core: ResultEnvelopeCore
    claim_id: str
    required_verdicts: tuple       # ((name, ok), ...)      verdict-bearing checks (D-7)
    required_observations: tuple   # ((name, present), ...) observation-bearing checks (D-7)
    domain: str = "verification"


def verification_success(receipt: VerificationReceipt,
                         envelope: VerificationResultEnvelope) -> bool:
    """D-7 anti-vacuity floor. Non-vacuous conformance holds iff:
       (a) domain match on both (Category-Separation),
       (b) at least one verdict-bearing check ran (non-vacuity guard),
       (c) all required verdict-bearing checks passed,
       (d) all required observation-bearing checks are present.
    Refusal / failure are first-class non-success, not errors."""
    if getattr(receipt, "domain", None) != "verification":
        return False
    if getattr(envelope, "domain", None) != "verification":
        return False
    if receipt.outcome != "admitted":
        return False
    verdicts = tuple(envelope.required_verdicts)
    observations = tuple(envelope.required_observations)
    if len(verdicts) < 1:
        return False                       # vacuous: no verdict ran
    if not all(bool(ok) for _, ok in verdicts):
        return False
    if not all(bool(present) for _, present in observations):
        return False
    return True
