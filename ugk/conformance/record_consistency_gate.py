"""ugk/conformance/record_consistency_gate.py — constitutional records match implementation.

Systemic fix for the prose-formula drift defect class (observed 4x pre-release:
AD-14 nested formula, store.py DKN order, charter.py comment, store.py envelope
listing). Three proofs:
  1. Stale-pattern blacklist: retired formula forms appear nowhere in ugk/*.py.
  2. Record-positive: AD-14's decision text carries the canonical formulas as
     implemented (flat dimension_id; WHO×WHAT×WHICH session_dkn).
  3. Behavioral anchor: the canonical formula strings in the records are TRUE —
     recomputed raw against binding.canonical_dkn / spawn_session_identity.
"""


def run():
    from pathlib import Path
    import hashlib
    fails = []
    pkg = Path(__file__).resolve().parent.parent  # ugk/

    # --- 1. Stale-pattern blacklist (retired record forms must not return) ---
    STALE = (
        "SHA-256(SHA-256(phase_code)",      # nested dimension_id (pre-correction AD-14 form)
        "phase_code:root:session",          # pre-AD-14 session_dkn ordering
        "phase_code:mosaic_root:session",   # pre-AD-14 session_dkn ordering (long form)
    )
    me = Path(__file__).name
    for py in sorted(pkg.rglob("*.py")):
        if py.name == me:
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        for pat in STALE:
            if pat in text:
                fails.append(f"stale record form {pat!r} in {py.relative_to(pkg)}")

    # --- 2. Record-positive: AD-14 carries the canonical formulas ---
    from ugk.module_registry import record_path
    adr_text = record_path().read_text(encoding="utf-8")
    if "SHA-256(phase_code \u2016 governor_pubkey)" not in adr_text:
        fails.append("AD-14 record lacks the canonical flat dimension_id formula")
    if "SHA-256(mosaic_root:phase_code:session_id)" not in adr_text:
        fails.append("AD-14 record lacks the canonical session_dkn ordering")

    # --- 3. Behavioral anchor: the recorded formulas are true ---
    from ugk.storage.binding import canonical_dkn, mosaic_id, spawn_session_identity, SEP
    _pc, _pk = "rcg-phase", "ab" * 32
    flat = hashlib.sha256((_pc + SEP + _pk).encode("utf-8")).hexdigest()
    if canonical_dkn(_pc, _pk) != flat:
        fails.append("canonical_dkn no longer matches the recorded flat formula")
    si = spawn_session_identity(_pk, _pc, "rcg-sid")
    dkn = hashlib.sha256(f"{mosaic_id(_pk)}:{_pc}:rcg-sid".encode("utf-8")).hexdigest()
    if si.session_dkn != dkn:
        fails.append("session_dkn no longer matches the recorded WHO×WHAT×WHICH ordering")

    ok = not fails
    return ok, (
        "record_consistency_gate: no stale record forms; AD-14 carries canonical "
        "formulas; recorded formulas behaviorally true." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"record_consistency_gate: {'PASS' if ok else 'FAIL'}  {detail}")
