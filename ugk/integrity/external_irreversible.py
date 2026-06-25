"""r115 / AD-44: EXTERNAL_IRREVERSIBLE orphan-PREPARE detector.

A PURE, DETERMINISTIC scan over a receipt list (no clock, no iteration-order dependence, no live
state). It surfaces the irreducible in-doubt residue of irreversible external effects: a PREPARE with
no matching terminal.

The four-state model (AD-44):
  PREPARE        phase=prepare, effect_atomicity=external_irreversible   (intent-to-act, depth 0)
  COMMIT         phase=commit                                            (confirmed performed)
  ABORT          phase=abort, abort_reason=external_effect_not_performed (confirmed NOT performed)
  orphan PREPARE = a PREPARE with NO terminal (phase in {commit,abort}) sharing its idempotency_key
                   and pointing back to its h_r via prepare_ref. This is the ABSENCE of a terminal,
                   not a written receipt. It is IN-DOUBT: the act may or may not have occurred.

The detector NEVER resolves an orphan (no auto-commit / auto-abort / auto-retry) and NEVER infers an
outcome. It reports. Any verifier that requires a clean terminal state treats outstanding orphans as
fail-closed (missing evidence fails closed). An orphan is resolved only by a governed, out-of-band
reconciliation that, after an EXTERNAL check, writes a COMMIT or ABORT for that prepare_ref —
deliberate, recorded, never automatic.
"""
from __future__ import annotations

EXTERNAL_IRREVERSIBLE = "external_irreversible"
_TERMINAL_PHASES = ("commit", "abort")


_M2C = {"effect_atomicity": "effect_atomicity", "phase": "effect_phase",
        "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
        "abort_reason": "effect_abort_reason", "gate_admit_ref": "effect_gate_admit_ref"}


def _params(r):
    """r142 (AD-65): COLUMN-FIRST effect-field view (see external_reversible._params). Reads the typed
    effect columns (authoritative for v>=4, the only surface on v5); falls back to parameter markers for
    v<4 marker-era receipts. Keyed by legacy marker names so trail logic is unchanged."""
    raw = getattr(r, "parameters", None)
    view = dict(raw) if isinstance(raw, dict) else {}
    for marker_key, col in _M2C.items():
        cv = getattr(r, col, None)
        if cv is not None:
            view[marker_key] = cv
    return view


def _is_ei_phase(p, phase):
    return p.get("effect_atomicity") == EXTERNAL_IRREVERSIBLE and p.get("phase") == phase


def detect_orphan_prepares(receipts):
    """Return a deterministic, sorted list of ENRICHED orphan-PREPARE descriptors.

    An orphan is a PREPARE for which no terminal receipt (phase in {commit, abort}) exists with the
    SAME idempotency_key AND prepare_ref == the PREPARE's h_r (BOTH conditions -- the STRICT per-attempt
    rule; r112 §7). That match rule is UNCHANGED in r119: a terminal sharing only the key but pointing at
    a DIFFERENT prepare_ref does NOT clear this PREPARE (a same-key terminal is a DIFFERENT attempt and
    never vouches for this one).

    Each descriptor (r119 enrichment -- ALL fields additive, read-only, drawn from data already in the
    receipts; NONE of the added fields feeds the orphan determination):
        op, idempotency_key, prepare_ref, prepare_h_r, state="in_doubt"   (unchanged)
        prepare_ts           -- the PREPARE receipt's stored timestamp (operator triage; NOT a match input)
        gate_admit_ref       -- the PREPARE's AD-44 gate_admit_ref marker (links to the admission receipt)
        key_has_terminal     -- True iff ANY terminal shares this key UNDER ANY prepare_ref. A triage
                                signal that the KEY was ultimately resolved somewhere; it does NOT clear
                                this per-attempt orphan and the state stays "in_doubt".
        key_terminal_phases  -- sorted distinct phases of the terminals sharing this key ([] if none)
    """
    prepares = []
    terminals = []  # (idempotency_key, prepare_ref, phase)
    for r in receipts:
        p = _params(r)
        if _is_ei_phase(p, "prepare"):
            prepares.append((r, p))
        elif p.get("effect_atomicity") == EXTERNAL_IRREVERSIBLE and p.get("phase") in _TERMINAL_PHASES:
            terminals.append((p.get("idempotency_key"), p.get("prepare_ref"), p.get("phase")))

    orphans = []
    for r, p in prepares:
        key = p.get("idempotency_key")
        h_r = getattr(r, "h_r", "") or ""
        # STRICT per-attempt orphan rule (UNCHANGED): a terminal clears this PREPARE only if it shares the
        # key AND points back to THIS prepare via prepare_ref. key-only matches are deliberately ignored.
        matched = any(tk == key and tref == h_r for (tk, tref, _tph) in terminals)
        if matched:
            continue
        # READ-ONLY triage annotation, computed SEPARATELY -- it never affects `matched` above. Does the
        # KEY have a terminal anywhere (under any prepare_ref)? If so, the key was resolved on some attempt,
        # but THIS attempt remains in-doubt (we do not silently clear it).
        key_terminal_phases = sorted({tph for (tk, _tref, tph) in terminals if tk == key and tph})
        orphans.append({
            "op": r.op,
            "idempotency_key": key,
            "prepare_ref": h_r,
            "prepare_h_r": h_r,
            "state": "in_doubt",
            "prepare_ts": getattr(r, "timestamp", None),
            "gate_admit_ref": p.get("gate_admit_ref"),
            "key_has_terminal": bool(key_terminal_phases),
            "key_terminal_phases": key_terminal_phases,
        })
    # Deterministic order on STABLE fields only (never on prepare_ts), so the list order does not vary
    # with wall-clock capture time.
    orphans.sort(key=lambda o: (o["op"] or "", o["idempotency_key"] or "", o["prepare_ref"] or ""))
    return orphans


def summarize(receipts):
    """Deterministic terminal-state census over the EXTERNAL_IRREVERSIBLE receipts: counts of
    prepare / commit / abort and the orphan list. Pure; for gate/probe reporting."""
    counts = {"prepare": 0, "commit": 0, "abort": 0}
    for r in receipts:
        p = _params(r)
        if p.get("effect_atomicity") == EXTERNAL_IRREVERSIBLE and p.get("phase") in counts:
            counts[p["phase"]] += 1
    orphans = detect_orphan_prepares(receipts)
    return {"counts": counts, "orphans": orphans, "n_orphans": len(orphans)}


# ---------------------------------------------------------------------------
# r119: reusable READ-ONLY probe + CLI. Reports in-doubt; NEVER resolves it.
# No auto-commit / auto-abort / auto-retry; no mutation. Resolution remains a
# governed, out-of-band reconciliation (a separate, not-yet-authorized increment).
# ---------------------------------------------------------------------------

def probe(receipts):
    """Read-only operator probe over a receipt list: the summarize() terminal-state census plus the
    enriched in-doubt orphan descriptors. A thin, pure alias giving callers/tools a stable 'probe'
    entrypoint. It READS; it never writes, resolves, retries, or mutates anything."""
    return summarize(receipts)


def _load_receipts_readonly(db_path):
    """Open an EXISTING receipt store and return its receipts WITHOUT writing. The probe performs no
    writes, no migration, and no resolution -- it only reads the chain."""
    from ugk.storage.store import UGKReceiptStore
    return UGKReceiptStore(db_path).all_receipts()


def main(argv=None):
    """CLI: `python -m ugk.integrity.external_irreversible <receipt-db>` -> a deterministic JSON report
    (sorted keys; orphan list already sorted on stable fields) of the EXTERNAL_IRREVERSIBLE terminal-state
    census and the enriched in-doubt orphan list. READ-ONLY: it makes in-doubt legible, it does NOT
    resolve it."""
    import sys, json
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("usage: python -m ugk.integrity.external_irreversible <receipt-db>\n")
        return 2
    report = probe(_load_receipts_readonly(args[0]))
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
