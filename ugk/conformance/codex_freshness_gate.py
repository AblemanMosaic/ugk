"""ugk/conformance/codex_freshness_gate.py — codex FRESHNESS (artifact matches source).

GATE_GROUP = "structural"

Distinct proposition from codex_integrity_gate:
  - INTEGRITY = artifact matches its pin           (sha(CODEX.md) == CODEX_HASH.txt)
  - FRESHNESS = artifact matches its source        (CODEX.md == projection of current sources)
Both must hold. codex_integrity_gate proves integrity; this gate proves freshness, so a future
change to invariants.py or sci_typing.json cannot silently outrun the projected codex.

It reuses the generator's projection path (NO second implementation): it loads the top-level
codex_gen.py and calls consistency_check() + generate(). It is deterministic and SIDE-EFFECT
FREE — it regenerates the projection IN MEMORY and compares; it never rewrites any artifact.

Three propositions, each localized on failure:
  (1) registry  -> typing     : sci_typing.json types INVARIANT_REGISTRY exactly once
  (2) typing    -> projection : FRESHNESS — regenerated projection == shipped CODEX.md
  (3) projection-> shipped    : INTEGRITY — sha(CODEX.md) == CODEX_HASH.txt pin

Precondition: the top-level codex_gen.py projection tool must be present (source/release tree).
A deployment that ships only the ugk/ package (no top-level tool) cannot evaluate freshness
against source; the gate then returns NOT_ESTABLISHED — no freshness/integrity claim asserted
here — mirroring the Grundnorm posture tri-state. (Integrity remains covered by
codex_integrity_gate, which needs no generator.)
"""
import hashlib
import importlib.util
from pathlib import Path

import ugk
from ugk.conformance import NOT_ESTABLISHED


def _load_generator():
    """Load the SAME projection tool the generator uses; None if not present in this deployment."""
    cg_path = Path(ugk.__file__).resolve().parent.parent / "codex_gen.py"
    if not cg_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("codex_gen", cg_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run():
    base = Path(ugk.__file__).resolve().parent  # ugk/
    codex_path = base / "codex" / "CODEX.md"
    pin_path = base / "codex" / "CODEX_HASH.txt"

    cg = _load_generator()
    if cg is None:
        return NOT_ESTABLISHED, (
            "codex freshness: top-level codex_gen.py not present in this deployment; "
            "freshness-vs-source is not evaluable (integrity is covered by codex_integrity_gate)."
        )

    fails = []

    # (1) registry -> typing : exactly-once SCI routing of the registry
    ok_typing, typing_errors = cg.consistency_check()
    if not ok_typing:
        fails.append("DRIFT registry->typing: " + "; ".join(typing_errors))

    # (2) typing -> projection : freshness (only project when typing is consistent; else generate
    #     would itself refuse). In-memory regeneration; no artifact is written.
    if ok_typing:
        projected = cg.generate()
        proj_hash = hashlib.sha256(projected.encode()).hexdigest()
        if not codex_path.exists():
            fails.append(f"DRIFT typing->projection: shipped CODEX.md not found at {codex_path}")
        else:
            shipped_hash = hashlib.sha256(codex_path.read_bytes()).hexdigest()
            if proj_hash != shipped_hash:
                fails.append(
                    "DRIFT typing->projection (FRESHNESS): shipped CODEX.md does not match the "
                    f"projection of current sources; projected={proj_hash[:16]}… "
                    f"shipped={shipped_hash[:16]}… (run codex_gen.py ugk/codex to regenerate + re-pin)"
                )

    # (3) projection -> shipped : integrity (artifact matches pin) — reported as a SEPARATE leg
    if codex_path.exists() and pin_path.exists():
        shipped_hash = hashlib.sha256(codex_path.read_bytes()).hexdigest()
        pin = pin_path.read_text().strip()
        if shipped_hash != pin:
            fails.append(
                "DRIFT projection->shipped (INTEGRITY): "
                f"sha(CODEX.md)={shipped_hash[:16]}… != pin={pin[:16]}…"
            )
    else:
        fails.append("INTEGRITY: CODEX.md or CODEX_HASH.txt missing")

    ok = not fails
    if ok:
        detail = (
            "registry->typing exactly-once OK; FRESHNESS PASS (projection == shipped); "
            "INTEGRITY PASS (artifact == pin)."
        )
    else:
        detail = " | ".join(fails)
    return ok, detail


if __name__ == "__main__":
    ok, detail = run()
    label = "PASS" if ok is True else ("NOT_ESTABLISHED" if ok == NOT_ESTABLISHED else "FAIL")
    print(f"codex_freshness_gate: {label}  {detail}")
