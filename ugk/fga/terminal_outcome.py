"""ugk/fga/terminal_outcome.py — LM-2 terminal-outcome classifier (additive, read-only).

A PURE, DERIVATIONAL labeling layer over existing signals. It does NOT replace the kernel
decision path (gate_admit/gate_refuse/ProtocolError remain the authority), commit any receipt
field, move schema/law, or create a new admissibility regime. It LABELS exactly one of five
terminal outcomes from inputs the caller already has.

Guardrails (Governor-ratified):
  * defer_policy is an EXPLICIT per-call object; there is NO ambient/global/default policy.
    With no authorized policy, an incomplete evaluation resolves to STRUCTURAL_ERROR -- never
    DEFER, never REFUSE.
  * STRUCTURAL_ERROR preserves the ORIGINAL protocol/preflight/non-evaluable reason in the
    result basis (not-founded / undeclared / malformed-input / gate-exception / kernel-internal
    / non-evaluable). STRUCTURAL_ERROR is never a fog bank.

Outcome discipline:
  ADMIT / REFUSE     -- consume a COMPLETE SB-3a-core TraceVector (via conjunctive_refusal_monotone_v1)
  DEFER              -- authorized defer policy applies; carries a PartialEvaluationTrace; no effect
  STRUCTURAL_ERROR   -- no complete TraceVector can honestly be built and no authorized defer policy
  CRISIS             -- narrow root/frame/jurisdiction conflict; unreachable under single-root v0.1.0
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional, Tuple

from ugk.storage.binding import canonical_json
from ugk.fga.trace_vector import (
    TraceVector, aggregate, ADMIT as _TV_ADMIT, REFUSE as _TV_REFUSE,
)

MODEL_ID = "terminal_outcome_model_v1"

ADMIT = "ADMIT"
REFUSE = "REFUSE"
DEFER = "DEFER"
STRUCTURAL_ERROR = "STRUCTURAL_ERROR"
BRIDGE = "BRIDGE"  # Stage 4 / r162: native terminal disposition for an audited regime crossing (opt-in; BRIDGE-BINDING-gated at emit)
CRISIS = "CRISIS"
TERMINAL_OUTCOMES: Tuple[str, ...] = (ADMIT, REFUSE, DEFER, STRUCTURAL_ERROR, CRISIS)

# Diagnostic categories preserved from the protocol/preflight layer (guardrail 2). The classifier
# carries whatever category the caller passes; this set documents the known kernel categories.
STRUCTURAL_REASONS = frozenset({
    "not-founded", "undeclared", "malformed-input", "gate-exception",
    "kernel-internal", "non-evaluable",
})


@dataclass(frozen=True)
class PartialEvaluationTrace:
    """Diagnostic/continuation evidence for an evaluation that did NOT complete. NOT a TraceVector
    and never coercible to one: it can drive neither ADMIT nor REFUSE."""
    resolved: Tuple = ()       # surfaces already resolved (surface_id, result, reason_code)
    pending: Tuple = ()        # surface_ids / conditions not resolved
    reason: str = "non-evaluable"


@dataclass(frozen=True)
class RootConflict:
    """A root/frame/jurisdiction disambiguation conflict. Empty under single-root v0.1.0."""
    roots: Tuple = ()
    detail: str = ""


@dataclass(frozen=True)
class DeferPolicy:
    """An EXPLICIT, per-call defer authorization. There is no module-level default instance."""
    reason: str
    authority_boundary: str
    continuation_condition: str
    applies_to: Tuple = ()     # the structural/condition reasons this policy authorizes deferral for

    def authorizes(self, condition_reason: str) -> bool:
        return condition_reason in self.applies_to


@dataclass(frozen=True)
class TerminalOutcomeResult:
    outcome: str
    model_id: str
    reason: str                # specific diagnostic reason (esp. STRUCTURAL_ERROR / DEFER / CRISIS)
    carried_kind: str          # "trace_vector" | "partial" | "root_conflict" | "none"
    carried_identity: str      # identity of the carried evidence (no laundering of unknowns)
    basis: dict                # the displayed inputs that determined the outcome (no monolithic)
    identity: str              # deterministic result identity (binds model_id)


def _carried_identity(kind: str, obj) -> str:
    if kind == "trace_vector":
        return obj.trace_vector_hash
    if kind == "partial":
        return hashlib.sha256(b"LM2-PARTIAL-v1" + canonical_json({
            "resolved": list(obj.resolved), "pending": list(obj.pending), "reason": obj.reason,
        })).hexdigest()
    if kind == "root_conflict":
        return hashlib.sha256(b"LM2-ROOT-v1" + canonical_json({
            "roots": list(obj.roots), "detail": obj.detail,
        })).hexdigest()
    return ""


def _mk(outcome: str, reason: str, carried_kind: str, carried, basis: dict) -> TerminalOutcomeResult:
    cid = _carried_identity(carried_kind, carried) if carried is not None else ""
    identity = hashlib.sha256(b"LM2-OUTCOME-v1" + canonical_json({
        "model_id": MODEL_ID, "outcome": outcome, "reason": reason,
        "carried_kind": carried_kind, "carried_identity": cid, "basis": basis,
    })).hexdigest()
    return TerminalOutcomeResult(outcome=outcome, model_id=MODEL_ID, reason=reason,
                                 carried_kind=carried_kind, carried_identity=cid,
                                 basis=basis, identity=identity)


def classify(*, root_conflict: Optional[RootConflict] = None,
             trace: Optional[TraceVector] = None,
             partial: Optional[PartialEvaluationTrace] = None,
             structural_reason: Optional[str] = None,
             defer_policy: Optional[DeferPolicy] = None) -> TerminalOutcomeResult:
    """Pure classifier: maps the evaluation signals to EXACTLY ONE terminal outcome. No effects."""
    # explicit-only defer policy (guardrail 1): reject anything that is not a DeferPolicy or None
    if defer_policy is not None and not isinstance(defer_policy, DeferPolicy):
        raise TypeError("defer_policy must be an explicit DeferPolicy or None (no ambient policy)")
    # partial-not-complete: a PartialEvaluationTrace can never stand in for a complete TraceVector
    if isinstance(trace, PartialEvaluationTrace):
        raise TypeError("PartialEvaluationTrace cannot be used as a complete TraceVector")
    # fail-closed on contradictory inputs (a complete trace AND a structure-couldnt-evaluate claim)
    if trace is not None and structural_reason is not None:
        raise ValueError("contradictory inputs: complete trace with a structural_reason")

    # 1. CRISIS -- narrow root/frame/jurisdiction conflict (unreachable @ single-root: caller passes None)
    if root_conflict is not None:
        return _mk(CRISIS, reason="root-frame-jurisdiction-conflict",
                   carried_kind="root_conflict", carried=root_conflict,
                   basis={"root_conflict": True})

    # 2/3. incomplete -- no complete TraceVector could be built
    if trace is None:
        cond_reason = (structural_reason if structural_reason is not None
                       else (partial.reason if partial is not None else "non-evaluable"))
        if defer_policy is not None and defer_policy.authorizes(cond_reason):
            return _mk(DEFER, reason=cond_reason, carried_kind="partial", carried=partial,
                       basis={"root_conflict": False, "complete_trace": False, "defer_policy": True,
                              "authorizes": cond_reason,
                              "authority_boundary": defer_policy.authority_boundary,
                              "continuation_condition": defer_policy.continuation_condition})
        # no authorized policy -> STRUCTURAL_ERROR, PRESERVING the original diagnostic reason
        return _mk(STRUCTURAL_ERROR, reason=cond_reason,
                   carried_kind=("partial" if partial is not None else "none"),
                   carried=(partial if partial is not None else None),
                   basis={"root_conflict": False, "complete_trace": False, "defer_policy": False})

    # 4/5. complete TraceVector -> the named aggregation operator decides ADMIT vs REFUSE
    if not isinstance(trace, TraceVector):
        raise TypeError("trace must be a complete TraceVector")
    verdict, agg_reason = aggregate(trace)
    if verdict == _TV_ADMIT:
        return _mk(ADMIT, reason="ok", carried_kind="trace_vector", carried=trace,
                   basis={"root_conflict": False, "complete_trace": True, "aggregate": ADMIT})
    return _mk(REFUSE, reason=agg_reason, carried_kind="trace_vector", carried=trace,
               basis={"root_conflict": False, "complete_trace": True, "aggregate": REFUSE})
