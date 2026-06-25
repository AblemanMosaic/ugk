"""ugk/fga/trace_vector.py — first-class FGA decision-surface / trace-vector layer.

SB-3a-core (additive substrate). Makes UGK's already-implicit FGA structure explicit:

  * an ENUMERABLE registry of the COMMITTED decision surfaces (the four axes that
    already have dedicated receipt commitments: h_s/h_c/h_m/h_j);
  * a first-class, canonically ordered, frame-bound TRACE VECTOR built FROM a receipt;
  * a NAMED, VERSIONED aggregation operator (conjunctive, monotone toward refusal);
  * an explicit trace<->receipt correspondence: every surface maps to a committed
    receipt field, h_body re-derivation is the whole-body integrity backstop.

Scope boundaries (Governor-ratified): committed surfaces ONLY. Will/intent (WILL-S-06)
has NO dedicated receipt commitment, so it is a DOCUMENTED sub-surface of D_c, NOT a
separate committed surface. The capability-evidence surface D_cap is CANDIDATE/design-only
and is intentionally NOT in this registry. No law/schema/legend move; reads receipts only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple

from ugk.storage.binding import canonical_json
from ugk.storage import binding_m2 as _m2
from ugk.storage.store import compute_h_body

# Identity of THIS surface set and aggregation operator. Both are bound into every
# trace vector so two vectors built under different registries/operators are never
# mistaken for the same constitutional fact (Governor requirement 4 + 5).
SURFACE_REGISTRY_VERSION = "fga.committed-surfaces.v1"
AGGREGATION_OPERATOR_ID = "conjunctive_refusal_monotone_v1"

PASS = "PASS"
REFUSE = "REFUSE"
ADMIT = "ADMIT"

# Reason-code taxonomy (deterministic, surface-scoped). Kept small and explicit.
R_OK = "ok"
R_STATE_MISMATCH = "state-commitment-mismatch"          # D_s pure re-derivation failed
R_COMMIT_ABSENT = "commitment-absent"                   # required committed field missing/empty
R_COMMIT_MALFORMED = "commitment-malformed"             # committed field not a 64-char hex digest
R_BODY_INTEGRITY = "whole-body-integrity-fail"          # h_body re-derivation mismatch (cross-cutting)
R_FRAME_MISMATCH = "frame-mismatch"                     # receipt frame != supplied frame

# The ONLY receipt fields that carry a real per-axis committed commitment today. The
# committed registry is CLOSED to exactly these: any surface whose commitment is not one
# of these fields (e.g. a capability-evidence D_cap, or a will/intent surface with no
# dedicated committed field) is REJECTED, never silently admitted into the committed vector.
COMMITTED_RECEIPT_FIELDS = frozenset({"h_s", "h_c", "h_m", "h_j"})

# Honest verification modes — NO OVERCLAIM. Only h_s (and the whole-body h_body) are purely
# re-derivable from stored values (AD-21 rejected H_c/H_m/H_j pipeline replay). So D_c/D_m/D_j
# are surfaced as COMMITTED axes bound by h_r/h_body — NOT as independently recomputed axes.
MODE_REDERIVED = "rederived"                 # commitment is recomputed from stored values (D_s)
MODE_COMMITTED_BODY_BOUND = "committed-body-bound"  # commitment present + bound by h_r/h_body, not re-derived


# ---------------------------------------------------------------------------
# Decision surfaces — the ENUMERABLE committed registry
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DecisionSurface:
    surface_id: str          # canonical id, e.g. "D_s"
    axis: str                # human axis name, e.g. "state"
    committed_field: str     # receipt attribute carrying the commitment, e.g. "h_s"
    commitment_id: str       # the m2 commitment-id label, e.g. "c_s.v1"
    rederivable: bool        # True ONLY where the commitment is purely re-derivable (D_s)
    optional: bool           # True ONLY where the commitment is phase-bound (D_j may be None)
    verification_mode: str   # MODE_REDERIVED | MODE_COMMITTED_BODY_BOUND (honesty: what is actually proven)


# Canonical ORDER is fixed (state, admissibility, meaning, locality). This is the only
# surface set; the aggregation consumes EXACTLY these — there is no hidden surface.
COMMITTED_SURFACES: Tuple[DecisionSurface, ...] = (
    DecisionSurface("D_s", "state",         "h_s", _m2.ID_C_S, rederivable=True,  optional=False, verification_mode=MODE_REDERIVED),
    DecisionSurface("D_c", "admissibility", "h_c", _m2.ID_C_C, rederivable=False, optional=False, verification_mode=MODE_COMMITTED_BODY_BOUND),
    DecisionSurface("D_m", "meaning",       "h_m", _m2.ID_C_M, rederivable=False, optional=False, verification_mode=MODE_COMMITTED_BODY_BOUND),
    DecisionSurface("D_j", "locality",      "h_j", _m2.ID_C_J, rederivable=False, optional=True,  verification_mode=MODE_COMMITTED_BODY_BOUND),
)


def validate_committed_registry(surfaces) -> None:
    """Fail closed if any surface is not backed by a real committed receipt field. This is
    the structural guard that keeps D_cap (capability-evidence) and any will/intent surface
    OUT of the committed trace vector until a committed field actually exists for them."""
    seen = set()
    for s in surfaces:
        if s.committed_field not in COMMITTED_RECEIPT_FIELDS:
            raise ValueError("uncommitted-surface-rejected:%s:%s" % (s.surface_id, s.committed_field))
        if s.rederivable and s.verification_mode != MODE_REDERIVED:
            raise ValueError("verification-mode-inconsistent:%s" % s.surface_id)
        if (not s.rederivable) and s.verification_mode != MODE_COMMITTED_BODY_BOUND:
            raise ValueError("verification-mode-overclaim:%s" % s.surface_id)
        if s.surface_id in seen:
            raise ValueError("duplicate-surface:%s" % s.surface_id)
        seen.add(s.surface_id)


# The canonical registry must itself satisfy the closed-registry guard (checked at import).
validate_committed_registry(COMMITTED_SURFACES)


# -- Lane 4b (AD-52): D_cap committed capability-evidence surface -- NON-AGGREGATING ----------
# D_cap is a COMMITTED CANDIDATE decision surface: it commits CGP capability evidence (h_cap)
# and is verified, but it is NOT a member of COMMITTED_SURFACES, is NOT consumed by
# conjunctive_refusal_monotone_v1 / aggregate(), and does NOT affect ADMIT/REFUSE. Decision
# authority for D_cap is a later, separately-authorized enforcement/law increment. The sibling
# registry below NEVER loosens the closed aggregating COMMITTED_RECEIPT_FIELDS guard.
CAPABILITY_COMMITTED_FIELDS = frozenset({"h_cap"})

CAPABILITY_SURFACES: Tuple[DecisionSurface, ...] = (
    DecisionSurface("D_cap", "capability", "h_cap", "c_cap.v1", rederivable=False,
                    optional=True, verification_mode=MODE_COMMITTED_BODY_BOUND),
)


def validate_capability_registry(surfaces) -> None:
    """Sibling guard for the NON-aggregating capability-evidence registry. Admits D_cap without
    touching the closed aggregating four-surface guard; rejects collisions with the aggregating set."""
    aggregating = {x.surface_id for x in COMMITTED_SURFACES}
    seen = set()
    for s in surfaces:
        if s.committed_field not in CAPABILITY_COMMITTED_FIELDS:
            raise ValueError("uncommitted-capability-surface-rejected:%s:%s" % (s.surface_id, s.committed_field))
        if s.surface_id in aggregating:
            raise ValueError("capability-surface-collides-with-aggregating:%s" % s.surface_id)
        if s.surface_id in seen:
            raise ValueError("duplicate-capability-surface:%s" % s.surface_id)
        seen.add(s.surface_id)


validate_capability_registry(CAPABILITY_SURFACES)


def verify_capability_surface(receipt, ledger=None):
    """Verify the D_cap commitment on a v3 receipt WITHOUT making it decision-authoritative.
    Returns (ok, reason). h_cap present + 64-hex (whole-body integrity covers its binding); if the
    originating ledger is supplied, h_cap must recompute from THAT exact ledger via the pure
    no-laundering binding helper. NEVER consulted by aggregate()."""
    h_cap = getattr(receipt, "h_cap", None)
    if not h_cap:
        return (False, "capability-commitment-absent")
    if len(h_cap) != 64:
        return (False, "capability-commitment-malformed")
    if ledger is not None:
        from ugk.cgp.dispatch import capability_evidence_commitment  # lazy
        if capability_evidence_commitment(ledger)["h_cap"] != h_cap:
            return (False, "capability-commitment-mismatch")
    return (True, "ok")


@dataclass(frozen=True)
class SurfaceResult:
    surface_id: str
    result: str        # PASS | REFUSE
    reason_code: str


@dataclass(frozen=True)
class FrameRef:
    """The constitutional frame a trace vector is evaluated under."""
    law_hash: str
    schema_hash: str
    legend_hash: str
    codex_hash: str


@dataclass(frozen=True)
class TraceVector:
    surfaces: Tuple[SurfaceResult, ...]      # canonical order, one per committed surface
    frame: FrameRef
    surface_registry_version: str
    aggregation_operator_id: str
    transition_op: str                       # the governed transition descriptor (receipt.op)
    receipt_h_r: str                         # receipt identity (binding root)
    receipt_h_body: str                      # whole-body commitment
    integrity_ok: bool                       # h_body re-derivation result (cross-cutting)
    frame_consistent: bool                   # receipt's stored frame matches `frame`
    trace_vector_hash: str                   # deterministic identity of this vector


# ---------------------------------------------------------------------------
# Re-derivation helpers (pure, from stored receipt values)
# ---------------------------------------------------------------------------
def _is_hexdigest(v: Optional[str]) -> bool:
    if not isinstance(v, str) or len(v) != 64:
        return False
    try:
        int(v, 16)
        return True
    except ValueError:
        return False


def _rederive_h_s(receipt) -> str:
    return _m2.H_s(receipt.op, receipt.parameters).hex()


def _rederive_h_body(receipt) -> str:
    return compute_h_body(
        op=receipt.op, authority=receipt.authority, parameters=receipt.parameters,
        intent=receipt.intent, jurisdiction=receipt.jurisdiction, confidence=receipt.confidence,
        timestamp=receipt.timestamp, failed=receipt.failed, session_dkn=receipt.session_dkn,
        law_hash=receipt.law_hash, legend_hash=receipt.legend_hash, warrant_id=receipt.warrant_id,
        intent_ref=receipt.intent_ref, h_s=receipt.h_s, h_c=receipt.h_c, h_m=receipt.h_m,
        h_j=receipt.h_j, h_r=receipt.h_r, parent_h_r=receipt.parent_h_r, mode=receipt.mode,
        version=receipt.version, id_c_s=receipt.id_c_s, id_c_c=receipt.id_c_c,
        id_c_m=receipt.id_c_m, id_c_j=receipt.id_c_j,
        terminal_outcome=getattr(receipt, "terminal_outcome", None),
        terminal_outcome_model_id=getattr(receipt, "terminal_outcome_model_id", None),
        terminal_outcome_reason=getattr(receipt, "terminal_outcome_reason", None),
        h_cap=getattr(receipt, "h_cap", None),
        capability_evidence_model_id=getattr(receipt, "capability_evidence_model_id", None),
        capability_ledger_hash=getattr(receipt, "capability_ledger_hash", None),
        capability_registry_version=getattr(receipt, "capability_registry_version", None),
        capability_scope_id=getattr(receipt, "capability_scope_id", None),
    )


def _verify_surface(surface: DecisionSurface, receipt) -> SurfaceResult:
    """Per-surface verification result for a receipt. Localized where the commitment is
    re-derivable (D_s); a presence/well-formedness check otherwise. The whole-body
    integrity backstop (h_body) is applied vector-wide in build_trace_vector, so an
    undetectable per-axis tamper of h_c/h_m/h_j still forces REFUSE via integrity."""
    committed = getattr(receipt, surface.committed_field, None)

    if surface.optional and (committed is None or committed == ""):
        # phase-unbound locality: no commitment required, surface passes vacuously
        return SurfaceResult(surface.surface_id, PASS, R_OK)

    if committed is None or committed == "":
        return SurfaceResult(surface.surface_id, REFUSE, R_COMMIT_ABSENT)
    if not _is_hexdigest(committed):
        return SurfaceResult(surface.surface_id, REFUSE, R_COMMIT_MALFORMED)

    if surface.rederivable:
        if _rederive_h_s(receipt) != committed:
            return SurfaceResult(surface.surface_id, REFUSE, R_STATE_MISMATCH)

    return SurfaceResult(surface.surface_id, PASS, R_OK)


# ---------------------------------------------------------------------------
# Trace vector construction
# ---------------------------------------------------------------------------
def _trace_vector_hash(*, surfaces, frame, registry_version, operator_id, transition_op,
                       receipt_h_r, receipt_h_body, integrity_ok, frame_consistent) -> str:
    body = {
        "surface_registry_version": registry_version,
        "aggregation_operator_id": operator_id,
        "frame": {
            "law_hash": frame.law_hash, "schema_hash": frame.schema_hash,
            "legend_hash": frame.legend_hash, "codex_hash": frame.codex_hash,
        },
        "transition_op": transition_op,
        "receipt_h_r": receipt_h_r,
        "receipt_h_body": receipt_h_body,
        "integrity_ok": bool(integrity_ok),
        "frame_consistent": bool(frame_consistent),
        "surfaces": [[s.surface_id, s.result, s.reason_code] for s in surfaces],
    }
    return hashlib.sha256(b"FGA-TRACE-v1" + canonical_json(body)).hexdigest()


def build_trace_vector(receipt, frame: FrameRef, surfaces=COMMITTED_SURFACES) -> TraceVector:
    """Build the first-class trace vector for `receipt` under constitutional `frame`.
    Reads only stored receipt values + the supplied frame. Deterministic. The surface set
    is validated against the closed committed registry (fails closed on any uncommitted
    surface) before anything else."""
    validate_committed_registry(surfaces)
    results = tuple(_verify_surface(s, receipt) for s in surfaces)

    integrity_ok = (_rederive_h_body(receipt) == receipt.h_body) and bool(receipt.h_body)
    frame_consistent = (receipt.law_hash == frame.law_hash
                        and receipt.legend_hash == frame.legend_hash)

    tvh = _trace_vector_hash(surfaces=results, frame=frame,
                             registry_version=SURFACE_REGISTRY_VERSION,
                             operator_id=AGGREGATION_OPERATOR_ID,
                             transition_op=receipt.op, receipt_h_r=receipt.h_r,
                             receipt_h_body=receipt.h_body, integrity_ok=integrity_ok,
                             frame_consistent=frame_consistent)
    return TraceVector(
        surfaces=results, frame=frame,
        surface_registry_version=SURFACE_REGISTRY_VERSION,
        aggregation_operator_id=AGGREGATION_OPERATOR_ID,
        transition_op=receipt.op, receipt_h_r=receipt.h_r, receipt_h_body=receipt.h_body,
        integrity_ok=integrity_ok, frame_consistent=frame_consistent,
        trace_vector_hash=tvh,
    )


# ---------------------------------------------------------------------------
# Aggregation — conjunctive_refusal_monotone_v1
# ---------------------------------------------------------------------------
def aggregate(tv: TraceVector) -> Tuple[str, str]:
    """conjunctive_refusal_monotone_v1: ADMIT iff the vector DISPLAYS the full committed
    surface set in canonical order, EVERY committed surface PASSes, and whole-body integrity
    + frame consistency hold; otherwise REFUSE (fail-closed). The result is the EXPLICIT
    conjunction of the per-surface results in `tv` — there is NO monolithic admit: a vector
    that omits, reorders, or hides a committed surface cannot ADMIT. Monotone toward refusal:
    any additional REFUSE keeps the verdict REFUSE."""
    if tv.aggregation_operator_id != AGGREGATION_OPERATOR_ID:
        return REFUSE, "operator-id-mismatch"
    # no-monolithic-admissibility: the displayed vector must BE the full committed registry,
    # in canonical order. No admit/refuse may be produced without the surface vector present.
    expected = tuple(s.surface_id for s in COMMITTED_SURFACES)
    displayed = tuple(s.surface_id for s in tv.surfaces)
    if displayed != expected:
        return REFUSE, "incomplete-or-reordered-surface-vector"
    for s in tv.surfaces:
        if s.result != PASS:
            return REFUSE, s.reason_code
    if not tv.integrity_ok:
        return REFUSE, R_BODY_INTEGRITY
    if not tv.frame_consistent:
        return REFUSE, R_FRAME_MISMATCH
    return ADMIT, R_OK
