"""ugk/conformance/effect_trail_integrity_gate.py - r133 / AD-56 (binds EFFECT-S-01).

EFFECT-S-01 (effect-trail integrity) is a class-relative INTEGRITY invariant (the IEL species): where a
receipt declares an effect atomicity class or effect phase, the recorded effect trail must conform to the
realized protocol for that class. It is NOT a claim that every effect is atomic. This gate hosts the pure
recompute verifier verify_effect_trail_integrity(receipts) and proves it over BOTH real kernel-produced
trails (conformant; orphans exempt) and synthetic corrupt trails (flagged) -- the same dual strategy
TO-S-01 used in terminal_outcome_commit_gate.

The verifier is PURE/DETERMINISTIC and recomputes from the committed receipt bodies/parameters (which
IEL-S-01 already integrity-protects). It flags only malformed TERMINALS and class mismatches; it NEVER
flags a bare intent record (orphan PREPARE / orphan COMPENSATE), which is honest in-doubt residue, not
corruption.

Class-relative conformance:
  * PURE / STORE_LOCAL   -> atomic via the seam; MUST NOT carry any two-phase/compensation phase marker.
  * EXTERNAL_IRREVERSIBLE -> phases prepare/commit/abort only; terminals anchor to a PREPARE; NO
                            compensation phases.
  * EXTERNAL_REVERSIBLE  -> forward prepare/commit/abort (terminals anchor to a PREPARE) plus the
                            separately-governed compensate/compensated/compensation_failed (terminals
                            anchor to a COMPENSATE). COMPENSATED is an offset (no erasure marker), not an
                            erasure of the forward COMMIT; COMPENSATION_FAILED is failed=True (unresolved
                            execution status, not REFUSE).
  * NON_ATOMIC           -> explicit bridge; MUST NOT carry two-phase/compensation phase markers (it
                            claims no two-phase trail compliance).
"""

EXTERNAL = ("external_irreversible", "external_reversible")
TWO_PHASE_PHASES = ("prepare", "commit", "abort", "compensate", "compensated", "compensation_failed")
FORWARD_TERMINALS = ("commit", "abort")
COMP_PHASES = ("compensate", "compensated", "compensation_failed")
COMP_TERMINALS = ("compensated", "compensation_failed")
ERASURE_MARKERS = ("undone", "reversed", "erased", "rolled_back")


def _params(r):
    p = getattr(r, "parameters", None)
    return p if isinstance(p, dict) else {}


def verify_effect_trail_integrity(receipts):
    """PURE recompute of EFFECT-S-01 over a receipt list. Returns a deterministic, sorted list of
    violation tuples (empty == conformant). Never flags a bare orphan PREPARE/COMPENSATE."""
    violations = []
    # index intent anchors (forward PREPARE by (h_r, key); COMPENSATE by (compensate_ref, comp_key))
    prepare_anchors = set()
    compensate_anchors = set()
    for r in receipts:
        p = _params(r)
        cls = p.get("effect_atomicity"); ph = p.get("phase")
        if cls in EXTERNAL and ph == "prepare":
            prepare_anchors.add(((getattr(r, "h_r", "") or ""), p.get("idempotency_key")))
        if cls == "external_reversible" and ph == "compensate":
            compensate_anchors.add((p.get("compensate_ref"), p.get("compensation_idempotency_key")))

    for r in receipts:
        p = _params(r)
        cls = p.get("effect_atomicity"); ph = p.get("phase")
        hr = getattr(r, "h_r", "") or ""
        failed = bool(getattr(r, "failed", False))
        if ph not in TWO_PHASE_PHASES:
            continue  # not an effect-trail phase receipt; out of scope
        # class-relativity: only external classes may carry two-phase/compensation phase markers
        if cls not in EXTERNAL:
            violations.append(("class-mismatch-non-external-carries-phase", str(cls), ph, hr))
            continue
        # irreversible must not carry compensation phases
        if cls == "external_irreversible" and ph in COMP_PHASES:
            violations.append(("irreversible-carries-compensation-phase", ph, hr))
            continue
        # forward terminals: terminal => anchor (no false success / no fabricated terminal)
        if ph in FORWARD_TERMINALS:
            pref = p.get("prepare_ref"); key = p.get("idempotency_key")
            if not pref or (pref, key) not in prepare_anchors:
                violations.append(("forward-terminal-without-anchor", ph, hr))
            if ph == "commit" and failed:
                violations.append(("commit-marked-failed-contradiction", hr))
            if ph == "abort" and not failed:
                violations.append(("abort-not-marked-failed", hr))
        # compensation terminals: terminal => COMPENSATE anchor
        if ph in COMP_TERMINALS:
            cref = p.get("compensate_ref"); ck = p.get("compensation_idempotency_key")
            if not cref or (cref, ck) not in compensate_anchors:
                violations.append(("compensation-terminal-without-anchor", ph, hr))
            if ph == "compensated":
                if failed:
                    violations.append(("compensated-marked-failed-contradiction", hr))
                if any(p.get(m) for m in ERASURE_MARKERS):
                    violations.append(("compensated-claims-physical-erasure", hr))
            if ph == "compensation_failed" and not failed:
                violations.append(("compensation_failed-not-marked-failed", hr))
    violations.sort(key=lambda v: tuple(str(x) for x in v))
    return violations


_EFFECT_COLS = ("effect_atomicity", "effect_phase", "effect_prepare_ref", "effect_compensate_ref",
                "effect_idempotency_key", "effect_compensation_idempotency_key",
                "effect_abort_reason", "effect_gate_admit_ref")


def _ecol(r, col):
    return getattr(r, col, None)


# r142 (AD-65): v5-aware identification accessor for TEST SCAFFOLDING. Reads the typed effect COLUMN
# (authoritative for v>=4, the only surface on v5), falling back to the parameter MARKER only when the
# column is absent (v<4 marker-era fixtures). Marker key -> column name per the store's _EFFECT_MARKER_MAP.
_MARKER_TO_COL = {"phase": "effect_phase", "effect_atomicity": "effect_atomicity",
                  "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
                  "compensate_ref": "effect_compensate_ref",
                  "compensation_idempotency_key": "effect_compensation_idempotency_key",
                  "abort_reason": "effect_abort_reason", "gate_admit_ref": "effect_gate_admit_ref"}
def _efield(r, marker_key):
    v = getattr(r, _MARKER_TO_COL[marker_key], None)
    if v is not None:
        return v
    return (r.parameters or {}).get(marker_key)


def verify_effect_trail_integrity_typed(receipts):
    """EFFECT-S-02 (r138/AD-61): PURE recompute of effect-trail integrity over the body-committed TYPED
    effect COLUMNS, for v>=4 receipts only. NON-RETROACTIVE: v<4 receipts carry no typed surface and are
    skipped here (they remain under EFFECT-S-01 marker semantics). Mirrors verify_effect_trail_integrity
    field-for-field, sourcing every STRUCTURAL field from the columns instead of the parameter markers.
    The no-physical-erasure prohibition has NO typed column and is retained as a BOUNDED parameter-hygiene
    residual (read from parameters) -- this recompute makes no claim of pure column closure. Returns a
    deterministic, sorted violation list ([] == conformant). The r134 marker<->column consistency bridge
    (verify_effect_column_marker_consistency) guarantees, for v>=4, that the columns equal the markers, so
    on consistent receipts this recompute is equivalent to the marker recompute by construction."""
    def _v4(r):
        return int(getattr(r, "version", 1) or 1) >= 4
    violations = []
    prepare_anchors = set()
    compensate_anchors = set()
    for r in receipts:
        if not _v4(r):
            continue
        cls = _ecol(r, "effect_atomicity"); ph = _ecol(r, "effect_phase")
        if cls in EXTERNAL and ph == "prepare":
            prepare_anchors.add(((getattr(r, "h_r", "") or ""), _ecol(r, "effect_idempotency_key")))
        if cls == "external_reversible" and ph == "compensate":
            compensate_anchors.add((_ecol(r, "effect_compensate_ref"),
                                    _ecol(r, "effect_compensation_idempotency_key")))
    for r in receipts:
        if not _v4(r):
            continue
        cls = _ecol(r, "effect_atomicity"); ph = _ecol(r, "effect_phase")
        hr = getattr(r, "h_r", "") or ""
        failed = bool(getattr(r, "failed", False))
        if ph not in TWO_PHASE_PHASES:
            continue
        if cls not in EXTERNAL:
            violations.append(("class-mismatch-non-external-carries-phase", str(cls), ph, hr))
            continue
        if cls == "external_irreversible" and ph in COMP_PHASES:
            violations.append(("irreversible-carries-compensation-phase", ph, hr))
            continue
        if ph in FORWARD_TERMINALS:
            pref = _ecol(r, "effect_prepare_ref"); key = _ecol(r, "effect_idempotency_key")
            if not pref or (pref, key) not in prepare_anchors:
                violations.append(("forward-terminal-without-anchor", ph, hr))
            if ph == "commit" and failed:
                violations.append(("commit-marked-failed-contradiction", hr))
            if ph == "abort" and not failed:
                violations.append(("abort-not-marked-failed", hr))
        if ph in COMP_TERMINALS:
            cref = _ecol(r, "effect_compensate_ref"); ck = _ecol(r, "effect_compensation_idempotency_key")
            if not cref or (cref, ck) not in compensate_anchors:
                violations.append(("compensation-terminal-without-anchor", ph, hr))
            if ph == "compensated":
                if failed:
                    violations.append(("compensated-marked-failed-contradiction", hr))
                # residual no-erasure guard: no typed column -> bounded parameter-hygiene read
                p = r.parameters if isinstance(getattr(r, "parameters", None), dict) else {}
                if any(p.get(m) for m in ERASURE_MARKERS):
                    violations.append(("compensated-claims-physical-erasure", hr))
            if ph == "compensation_failed" and not failed:
                violations.append(("compensation_failed-not-marked-failed", hr))
    violations.sort(key=lambda v: tuple(str(x) for x in v))
    return violations


class _R:
    """Minimal synthetic receipt for adversarial corrupt-trail construction."""
    def __init__(self, op, failed, h_r, parameters):
        self.op = op; self.failed = failed; self.h_r = h_r; self.parameters = parameters


class _RT:
    """Synthetic receipt carrying BOTH parameter markers and v4 typed effect columns + a version, for
    EFFECT-S-02 column-mode adversarial / non-retroactivity construction."""
    def __init__(self, op, failed, h_r, version, parameters, **cols):
        self.op = op; self.failed = failed; self.h_r = h_r
        self.version = version; self.parameters = parameters
        for c in _EFFECT_COLS:
            setattr(self, c, cols.get(c))
        self.effect_atomicity_model_id = cols.get("effect_atomicity_model_id")


def run():
    import tempfile
    from ugk.kernel import (GovernanceKernel, EffectAtomicity, ExternalEffectNotPerformed)
    from ugk.storage.store import UGKReceiptStore
    fails = []
    OP = "crp_evidence"

    def mk():
        db = tempfile.mktemp(suffix=".db")
        k = GovernanceKernel(store=UGKReceiptStore(db_path=db)); k.open_session()
        return k

    # ---- (1) REAL conformant mixed trail -> ZERO violations; orphans exempt ----
    k = mk()
    # PURE + STORE_LOCAL (atomic seam, no phase markers)
    k.execute(op=OP, authority="a", parameters={"x": 1}, gate=lambda: True,
              effect=lambda: None, effect_atomicity=EffectAtomicity.PURE)
    # EXTERNAL_IRREVERSIBLE success (prepare->commit)
    k.execute(op=OP, authority="a", parameters={"x": 2}, gate=lambda: True,
              effect=lambda: None, effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE,
              idempotency_key="I1")
    # EXTERNAL_REVERSIBLE forward success + compensation
    k.execute(op=OP, authority="a", parameters={"x": 3}, gate=lambda: True,
              effect=lambda: None, effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE,
              idempotency_key="R1")
    rcs = k._store.all_receipts()
    pref = [r for r in rcs if _efield(r, "phase") == "commit"
            and _efield(r, "idempotency_key") == "R1"][0]
    pref = _efield(pref, "prepare_ref")
    k.compensate_external_reversible(prepare_ref=pref, compensation_effect=lambda: None,
                                     compensation_idempotency_key=k.compose_compensation_key("R1"),
                                     authority="a")
    # an orphan PREPARE (irreversible effect that crashes uncertainly) + a clean ABORT
    try:
        k.execute(op=OP, authority="a", parameters={"x": 4}, gate=lambda: True,
                  effect=lambda: (_ for _ in ()).throw(RuntimeError("uncertain")),
                  effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE, idempotency_key="I-orphan")
    except RuntimeError:
        pass
    try:
        k.execute(op=OP, authority="a", parameters={"x": 5}, gate=lambda: True,
                  effect=lambda: (_ for _ in ()).throw(ExternalEffectNotPerformed("np")),
                  effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE, idempotency_key="R-abort")
    except ExternalEffectNotPerformed:
        pass
    # r142 (AD-65): live writes are UGK-BODY-v5 (marker-retired) -> the AUTHORITATIVE proof of this real
    # conformant trail is the TYPED-column recompute (EFFECT-S-02), NOT the now-vacuous marker recompute.
    if not all(int(getattr(r, "version", 1) or 1) == 7 for r in k._store.all_receipts()):
        fails.append("(1) live writes are not uniformly v6 (continuation-surface regime v7 not in effect)")
    v = verify_effect_trail_integrity_typed(k._store.all_receipts())
    if v:
        fails.append("(1) conformant real v5 trail flagged by the typed recompute (orphan exemption / class-relativity broken): %r" % v[:4])

    # ---- (2) orphan-only trail (PREPARE + COMPENSATE, no terminals) -> ZERO violations ----
    orphan_only = [
        _R(OP, False, "hp1", {"effect_atomicity": "external_reversible", "phase": "prepare",
                              "idempotency_key": "K"}),
        _R(OP, False, "hc1", {"effect_atomicity": "external_reversible", "phase": "compensate",
                              "compensate_ref": "hp1", "compensation_idempotency_key": "K::compensate"}),
    ]
    if verify_effect_trail_integrity(orphan_only):
        fails.append("(2) bare orphan PREPARE/COMPENSATE flagged as corruption (must be exempt)")

    # ---- (3) adversarial corruptions each flagged ----
    def flagged(trail, needle):
        return any(needle in v[0] for v in verify_effect_trail_integrity(trail))

    # 3a: forward terminal with NO anchoring PREPARE (fabricated COMMIT / false success)
    t = [_R(OP, False, "hx", {"effect_atomicity": "external_irreversible", "phase": "commit",
                              "prepare_ref": "does-not-exist", "idempotency_key": "Z"})]
    if not flagged(t, "forward-terminal-without-anchor"):
        fails.append("(3a) fabricated COMMIT without anchor not flagged")
    # 3b: class-mismatch -- PURE carrying a two-phase phase marker
    t = [_R(OP, False, "hy", {"effect_atomicity": "pure", "phase": "commit"})]
    if not flagged(t, "class-mismatch"):
        fails.append("(3b) PURE carrying a commit phase not flagged")
    # 3c: NON_ATOMIC claiming a two-phase trail
    t = [_R(OP, False, "hn", {"effect_atomicity": "non_atomic", "phase": "prepare"})]
    if not flagged(t, "class-mismatch"):
        fails.append("(3c) NON_ATOMIC claiming a two-phase phase not flagged")
    # 3d: irreversible carrying a compensation phase
    t = [_R(OP, False, "hi", {"effect_atomicity": "external_irreversible", "phase": "compensated",
                              "compensate_ref": "x", "compensation_idempotency_key": "y"})]
    if not flagged(t, "irreversible-carries-compensation-phase"):
        fails.append("(3d) irreversible carrying a compensation phase not flagged")
    # 3e: COMPENSATED claiming physical erasure
    t = [
        _R(OP, False, "hp", {"effect_atomicity": "external_reversible", "phase": "compensate",
                             "compensate_ref": "fwd", "compensation_idempotency_key": "ck"}),
        _R(OP, False, "ht", {"effect_atomicity": "external_reversible", "phase": "compensated",
                             "compensate_ref": "fwd", "compensation_idempotency_key": "ck",
                             "erased": True}),
    ]
    if not flagged(t, "compensated-claims-physical-erasure"):
        fails.append("(3e) COMPENSATED claiming erasure not flagged")
    # 3f: compensation terminal with no COMPENSATE anchor
    t = [_R(OP, False, "hct", {"effect_atomicity": "external_reversible", "phase": "compensated",
                               "compensate_ref": "ghost", "compensation_idempotency_key": "ck"})]
    if not flagged(t, "compensation-terminal-without-anchor"):
        fails.append("(3f) compensation terminal without anchor not flagged")
    # 3g: COMMIT marked failed (contradiction)
    t = [
        _R(OP, False, "hp2", {"effect_atomicity": "external_reversible", "phase": "prepare",
                              "idempotency_key": "Q"}),
        _R(OP, True, "hc2", {"effect_atomicity": "external_reversible", "phase": "commit",
                             "prepare_ref": "hp2", "idempotency_key": "Q"}),
    ]
    if not flagged(t, "commit-marked-failed-contradiction"):
        fails.append("(3g) COMMIT marked failed not flagged")

    # ---- (4) PURE/STORE_LOCAL rollback-backed behavior still holds (failing PURE -> structural abort,
    #          no false success) and EFFECT-S-01 stays conformant on that trail ----
    k = mk()
    try:
        k.execute(op=OP, authority="a", parameters={"x": 9}, gate=lambda: True,
                  effect=lambda: (_ for _ in ()).throw(RuntimeError("pure fail")),
                  effect_atomicity=EffectAtomicity.PURE)
    except Exception:
        pass
    rcs = k._store.all_receipts()
    nonfailed_success = [r for r in rcs if r.op == OP and not r.failed
                         and not (r.parameters or {}).get("effect_aborted")]
    if nonfailed_success:
        fails.append("(4) failing PURE effect left a false (non-failed) success receipt")
    if verify_effect_trail_integrity_typed(rcs):
        fails.append("(4) EFFECT-S-02 flagged a clean PURE structural-abort v5 trail")

    # ---- (5) TO-S-01 effect-abort separation preserved: post-admit effect abort is ADMIT, not REFUSE ----
    if [r for r in rcs if r.op == "gate_refuse"]:
        fails.append("(5) a failing PURE effect produced a gate_refuse (effect-abort must remain ADMIT)")
    if not [r for r in rcs if r.op == "gate_admit" and not r.failed]:
        fails.append("(5) gate_admit (ADMIT decision) absent after a PURE effect abort")

    # ================================================================== r138 / AD-61 (EFFECT-S-02)
    #   typed-column trail integrity is AUTHORITATIVE for v>=4; markers remain for v<4; bridge holds
    # ==================================================================
    from ugk.storage.store import verify_effect_column_marker_consistency

    # ---- (E1) EQUIVALENCE on a SYNTHETIC v4 DUAL-SURFACE trail (markers + matching columns): the marker
    #          recompute (EFFECT-S-01) and the typed recompute (EFFECT-S-02) agree, and the v4 bridge holds.
    #          Live writes are now v5-only (markers retired), so this dual-surface equivalence is proven on
    #          an explicit v4 fixture -- legacy coverage preserved, not assumed from new writes. ----
    MID = "effect_atomicity_model_v1"
    v4fix = [
        _RT(OP, False, "e1p", 4, {"effect_atomicity": "external_irreversible", "phase": "prepare",
                                  "idempotency_key": "K"},
            effect_atomicity="external_irreversible", effect_atomicity_model_id=MID,
            effect_phase="prepare", effect_idempotency_key="K"),
        _RT(OP, False, "e1c", 4, {"effect_atomicity": "external_irreversible", "phase": "commit",
                                  "prepare_ref": "e1p", "idempotency_key": "K"},
            effect_atomicity="external_irreversible", effect_atomicity_model_id=MID,
            effect_phase="commit", effect_prepare_ref="e1p", effect_idempotency_key="K"),
    ]
    marker_v = verify_effect_trail_integrity(v4fix)
    typed_v = verify_effect_trail_integrity_typed(v4fix)
    if marker_v:
        fails.append("(E1) marker recompute flagged a conformant v4 dual-surface trail: %r" % marker_v[:3])
    if typed_v:
        fails.append("(E1) typed recompute flagged a conformant v4 dual-surface trail: %r" % typed_v[:3])
    if marker_v != typed_v:
        fails.append("(E1) typed recompute diverged from marker recompute on a conformant v4 trail")
    if not all(verify_effect_column_marker_consistency(r) for r in v4fix):
        fails.append("(E1) marker<->column consistency bridge failed on a conformant v4 dual-surface receipt")

    # ---- (E1-v5) LIVE v5 conformant trail: the AUTHORITATIVE typed recompute is clean, the receipts are
    #          v5 with columns and NO structural effect markers, and the bridge does NOT false-fail them. ----
    k = mk()
    k.execute(op=OP, authority="a", parameters={"x": 1}, gate=lambda: True, effect=lambda: None,
              effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE, idempotency_key="E1-I")
    k.execute(op=OP, authority="a", parameters={"x": 2}, gate=lambda: True, effect=lambda: None,
              effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE, idempotency_key="E1-R")
    rcs = k._store.all_receipts()
    prefE = [r for r in rcs if _efield(r, "phase") == "commit" and _efield(r, "idempotency_key") == "E1-R"][0]
    prefE = _efield(prefE, "prepare_ref")
    k.compensate_external_reversible(prepare_ref=prefE, compensation_effect=lambda: None,
                                     compensation_idempotency_key=k.compose_compensation_key("E1-R"),
                                     authority="a")
    rcs = k._store.all_receipts()
    eff = [r for r in rcs if _ecol(r, "effect_atomicity") is not None]
    if not eff or not all(int(getattr(r, "version", 1) or 1) == 7 for r in eff):
        fails.append("(E1-v5) live effect receipts are not uniformly v5")
    from ugk.storage.store import _EFFECT_MARKER_KEYS as _MK
    if any(m in (r.parameters or {}) for r in eff for m in _MK):
        fails.append("(E1-v5) a v5 effect receipt still carries structural effect markers in parameters")
    if verify_effect_trail_integrity_typed(rcs):
        fails.append("(E1-v5) typed recompute flagged a conformant live v5 trail")
    if not all(verify_effect_column_marker_consistency(r) for r in rcs):
        fails.append("(E1-v5) bridge false-failed a marker-absent v5 receipt")

    # ---- (E2) typed recompute flags the SAME structural corruption as markers (column-sourced) ----
    t = [_RT(OP, False, "ce2", 4, {"effect_atomicity": "external_irreversible", "phase": "commit",
                                   "prepare_ref": "ghost", "idempotency_key": "Z"},
             effect_atomicity="external_irreversible", effect_phase="commit",
             effect_prepare_ref="ghost", effect_idempotency_key="Z")]
    if not any("forward-terminal-without-anchor" in v[0] for v in verify_effect_trail_integrity_typed(t)):
        fails.append("(E2) typed recompute did not flag a fabricated COMMIT (column-sourced)")

    # ---- (E3) adversarial column<->marker DIVERGENCE fails closed via the r134 bridge ----
    diverge = _RT(OP, False, "cd", 4,
                  {"effect_atomicity": "external_reversible", "phase": "commit",
                   "prepare_ref": "p", "idempotency_key": "K"},
                  effect_atomicity="external_reversible", effect_phase="abort",  # column != marker
                  effect_prepare_ref="p", effect_idempotency_key="K")
    if verify_effect_column_marker_consistency(diverge):
        fails.append("(E3) a column<->marker divergence was NOT caught by the consistency bridge")

    # ---- (E4) RESIDUAL no-erasure guard still effective under the typed recompute ----
    t = [
        _RT(OP, False, "rp", 4, {"effect_atomicity": "external_reversible", "phase": "compensate",
                                 "compensate_ref": "fwd", "compensation_idempotency_key": "ck"},
            effect_atomicity="external_reversible", effect_phase="compensate",
            effect_compensate_ref="fwd", effect_compensation_idempotency_key="ck"),
        _RT(OP, False, "rt", 4, {"effect_atomicity": "external_reversible", "phase": "compensated",
                                 "compensate_ref": "fwd", "compensation_idempotency_key": "ck",
                                 "erased": True},
            effect_atomicity="external_reversible", effect_phase="compensated",
            effect_compensate_ref="fwd", effect_compensation_idempotency_key="ck"),
    ]
    if not any("compensated-claims-physical-erasure" in v[0] for v in verify_effect_trail_integrity_typed(t)):
        fails.append("(E4) residual no-erasure guard not effective under the typed recompute")

    # ---- (E5) NON-RETROACTIVITY: a v<4 effect receipt is invisible to EFFECT-S-02 but still governed
    #          by EFFECT-S-01 markers (no reinterpretation of pre-v4 receipts) ----
    v3bad = [_RT(OP, False, "v3", 3, {"effect_atomicity": "external_irreversible", "phase": "commit",
                                      "prepare_ref": "ghost", "idempotency_key": "Z"},
                 effect_atomicity=None, effect_phase=None)]  # v<4: no columns
    if verify_effect_trail_integrity_typed(v3bad):
        fails.append("(E5) EFFECT-S-02 (typed) reinterpreted a v<4 receipt (must be non-retroactive)")
    if not any("forward-terminal-without-anchor" in v[0] for v in verify_effect_trail_integrity(v3bad)):
        fails.append("(E5) EFFECT-S-01 (markers) failed to still govern the v<4 receipt")

    ok = not fails
    return ok, (
        "EFFECT-S-01 effect-trail integrity (r133/AD-56): class-relative trail conformance recomputed "
        "purely from committed bodies/parameters -- PURE/STORE_LOCAL atomic-seam (no phase markers), "
        "EXTERNAL_IRREVERSIBLE prepare/commit/abort, EXTERNAL_REVERSIBLE forward + separately-governed "
        "compensate/compensated/compensation_failed; terminal=>anchor; no false success; no class "
        "mismatch; COMPENSATED is offset not erasure; COMPENSATION_FAILED is failed execution status not "
        "REFUSE; orphan PREPARE/COMPENSATE are honest in-doubt residue and exempt; effect-abort stays "
        "ADMIT (TO-S-01 preserved). r138/AD-61 EFFECT-S-02 typed-column trail integrity: the "
        "body-committed typed effect columns are authoritative for v>=4 receipts (column recompute "
        "equals the marker recompute on conformant trails; flags the same structural corruption; the "
        "r134 marker<->column consistency bridge fails closed on divergence); the no-erasure prohibition "
        "is retained as a bounded parameter-hygiene residual (no pure column closure claimed); v<4 "
        "receipts are non-retroactive and stay under EFFECT-S-01 markers." if ok else "; ".join(str(f) for f in fails))
