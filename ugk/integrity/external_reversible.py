"""r132 / AD-55: EXTERNAL_REVERSIBLE (compensation / saga) in-doubt detector + compensation guard.

A PURE, DETERMINISTIC scan over a receipt list (no clock, no iteration-order dependence, no live
state), mirroring ugk/integrity/external_irreversible.py. It surfaces the irreducible in-doubt residue
of reversible external effects across BOTH arcs:

  FORWARD arc (identical in shape to EXTERNAL_IRREVERSIBLE):
    PREPARE   phase=prepare,  effect_atomicity=external_reversible   (intent-to-act, depth 0)
    COMMIT    phase=commit                                           (forward effect confirmed performed)
    ABORT     phase=abort, abort_reason=external_effect_not_performed (forward effect confirmed NOT performed)
    orphan PREPARE = a PREPARE with NO terminal (phase in {commit, abort}) sharing its idempotency_key
                     AND prepare_ref == its h_r. IN-DOUBT: the forward act may or may not have occurred.

  COMPENSATION arc (the reversible-class addition; separately governed, separately idempotent):
    COMPENSATE          phase=compensate            (intent-to-offset, depth 0, BEFORE the offsetting action)
    COMPENSATED         phase=compensated           (offset confirmed performed; the forward COMMIT STILL STANDS)
    COMPENSATION_FAILED phase=compensation_failed   (offset ran and failed -> unresolved business status)
    orphan COMPENSATE = a COMPENSATE with NO terminal (phase in {compensated, compensation_failed})
                        sharing its (compensate_ref, compensation_idempotency_key). IN-DOUBT: the
                        offsetting action may or may not have occurred.

The detector NEVER resolves an in-doubt (no auto-commit / auto-abort / auto-compensate / auto-retry) and
NEVER infers an outcome. It REPORTS. Any verifier requiring a clean terminal state treats outstanding
in-doubts as fail-closed (missing evidence fails closed). Resolution is a governed, out-of-band step.

NOTE: COMPENSATION_FAILED is a RESOLVED terminal (the offset is known to have run and failed), NOT an
orphan. It represents an UNRESOLVED business state -- the forward effect stands and was not offset -- but
it is execution status, never a constitutional REFUSE, and it is not in-doubt about whether the offsetting
action occurred. A reversible COMMIT is NEVER erased by a COMPENSATED terminal: COMPENSATED records an
OFFSET, never a physical undo.
"""
from __future__ import annotations

EXTERNAL_REVERSIBLE = "external_reversible"
_FORWARD_TERMINAL_PHASES = ("commit", "abort")
_COMP_TERMINAL_PHASES = ("compensated", "compensation_failed")


_M2C = {"effect_atomicity": "effect_atomicity", "phase": "effect_phase",
        "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
        "compensate_ref": "effect_compensate_ref",
        "compensation_idempotency_key": "effect_compensation_idempotency_key",
        "abort_reason": "effect_abort_reason", "gate_admit_ref": "effect_gate_admit_ref"}


def _params(r):
    """r142 (AD-65): COLUMN-FIRST effect-field view of a receipt, keyed by the legacy marker names so all
    existing trail-navigation logic is unchanged. v>=4 receipts carry the typed effect COLUMNS (the
    authoritative surface, and the ONLY effect surface on v5 after marker retirement); this reads those
    columns. v<4 marker-era receipts have no columns, so the parameter MARKERS are used as fallback.
    Non-effect parameters are passed through untouched (the trail logic ignores them)."""
    raw = getattr(r, "parameters", None)
    view = dict(raw) if isinstance(raw, dict) else {}
    for marker_key, col in _M2C.items():
        cv = getattr(r, col, None)
        if cv is not None:
            view[marker_key] = cv     # column-first (v>=4); else leave any marker (v<4 fallback)
    return view


def _is_rev_phase(p, phase):
    return p.get("effect_atomicity") == EXTERNAL_REVERSIBLE and p.get("phase") == phase


def detect_orphan_prepares(receipts):
    """Return a deterministic, sorted list of orphan-PREPARE descriptors for the FORWARD arc.

    An orphan is a PREPARE for which no forward terminal (phase in {commit, abort}) exists with the
    SAME idempotency_key AND prepare_ref == the PREPARE's h_r (BOTH conditions -- the strict per-attempt
    rule, mirroring external_irreversible). A terminal sharing only the key but pointing at a different
    prepare_ref does NOT clear this PREPARE.

    Each descriptor: op, idempotency_key, prepare_ref, prepare_h_r, state="in_doubt", arc="forward",
    gate_admit_ref. None of these fields feeds the determination beyond key + prepare_ref.
    """
    prepares = []
    terminals = []  # (idempotency_key, prepare_ref, phase)
    for r in receipts:
        p = _params(r)
        if _is_rev_phase(p, "prepare"):
            prepares.append((r, p))
        elif p.get("effect_atomicity") == EXTERNAL_REVERSIBLE and p.get("phase") in _FORWARD_TERMINAL_PHASES:
            terminals.append((p.get("idempotency_key"), p.get("prepare_ref"), p.get("phase")))

    orphans = []
    for r, p in prepares:
        key = p.get("idempotency_key")
        h_r = getattr(r, "h_r", "") or ""
        matched = any(tk == key and tref == h_r for (tk, tref, _tph) in terminals)
        if matched:
            continue
        orphans.append({
            "op": r.op,
            "idempotency_key": key,
            "prepare_ref": h_r,
            "prepare_h_r": h_r,
            "state": "in_doubt",
            "arc": "forward",
            "gate_admit_ref": p.get("gate_admit_ref"),
        })
    orphans.sort(key=lambda o: (o["op"] or "", o["idempotency_key"] or "", o["prepare_ref"] or ""))
    return orphans


def detect_orphan_compensates(receipts):
    """Return a deterministic, sorted list of orphan-COMPENSATE descriptors for the COMPENSATION arc.

    An orphan is a COMPENSATE for which no compensation terminal (phase in {compensated,
    compensation_failed}) exists sharing its (compensate_ref, compensation_idempotency_key). A
    COMPENSATION_FAILED terminal CLEARS the orphan (the offset is known to have run and failed -- not
    in-doubt), even though it leaves an UNRESOLVED business state.

    Each descriptor: op, compensate_ref, compensation_idempotency_key, compensate_h_r, state="in_doubt",
    arc="compensation".
    """
    compensates = []
    terminals = []  # (compensate_ref, compensation_idempotency_key, phase)
    for r in receipts:
        p = _params(r)
        if _is_rev_phase(p, "compensate"):
            compensates.append((r, p))
        elif p.get("effect_atomicity") == EXTERNAL_REVERSIBLE and p.get("phase") in _COMP_TERMINAL_PHASES:
            terminals.append((p.get("compensate_ref"), p.get("compensation_idempotency_key"), p.get("phase")))

    orphans = []
    for r, p in compensates:
        cref = p.get("compensate_ref")
        ckey = p.get("compensation_idempotency_key")
        matched = any(tref == cref and tk == ckey for (tref, tk, _tph) in terminals)
        if matched:
            continue
        orphans.append({
            "op": r.op,
            "compensate_ref": cref,
            "compensation_idempotency_key": ckey,
            "compensate_h_r": getattr(r, "h_r", "") or "",
            "state": "in_doubt",
            "arc": "compensation",
        })
    orphans.sort(key=lambda o: (o["op"] or "", o["compensate_ref"] or "",
                                o["compensation_idempotency_key"] or ""))
    return orphans


def detect_orphans(receipts):
    """Convenience: both in-doubt residues as a deterministic dict (forward + compensation)."""
    return {
        "orphan_prepares": detect_orphan_prepares(receipts),
        "orphan_compensates": detect_orphan_compensates(receipts),
    }


def find_committed_forward(receipts, prepare_ref):
    """Return {op, idempotency_key} for a forward EXTERNAL_REVERSIBLE effect that is currently
    COMPENSABLE -- i.e., it has a COMMIT terminal for `prepare_ref` AND no COMPENSATE has yet been
    written for it -- else None. Used by kernel.compensate_external_reversible as the fail-closed
    guard (compensation applies to a PERFORMED, not-yet-offset forward effect, never to an aborted,
    in-doubt, or already-compensated one). PURE: reads receipts, decides nothing, writes nothing.

    `prepare_ref` names the forward PREPARE's h_r. Already-compensated is detected by ANY COMPENSATE
    receipt whose compensate_ref == prepare_ref, guaranteeing at most one compensation arc per forward
    commit (a second compensation attempt fails closed)."""
    committed = None
    aborted = False
    already_compensated = False
    for r in receipts:
        p = _params(r)
        if p.get("effect_atomicity") != EXTERNAL_REVERSIBLE:
            continue
        phase = p.get("phase")
        if phase == "commit" and p.get("prepare_ref") == prepare_ref:
            committed = {"op": r.op, "idempotency_key": p.get("idempotency_key")}
        elif phase == "abort" and p.get("prepare_ref") == prepare_ref:
            aborted = True
        elif phase == "compensate" and p.get("compensate_ref") == prepare_ref:
            already_compensated = True
    if committed is None or aborted or already_compensated:
        return None
    return committed
