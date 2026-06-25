"""ugk/conformance/codex_integrity_gate.py — ATLAS-S-04: CODEX.md hash pinned."""
import hashlib, os
from pathlib import Path


def run():
    base = Path(__file__).parent.parent
    codex_path = base / "codex" / "CODEX.md"
    hash_path  = base / "codex" / "CODEX_HASH.txt"
    fails = []

    if not codex_path.exists():
        return False, f"ATLAS-S-04: CODEX.md not found at {codex_path}"
    if not hash_path.exists():
        return False, f"ATLAS-S-04: CODEX_HASH.txt not found at {hash_path}"

    content = codex_path.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()
    pinned_hash = hash_path.read_text().strip()

    if actual_hash != pinned_hash:
        fails.append(
            f"CODEX.md hash mismatch: actual {actual_hash[:16]}… "
            f"!= pinned {pinned_hash[:16]}… "
            f"(Codex has drifted from implementation — regenerate and re-pin)"
        )

    # Codex must reference the current LEGEND_HASH
    from ugk.storage.binding import LEGEND_HASH
    codex_text = content.decode("utf-8")
    if LEGEND_HASH not in codex_text:
        fails.append(f"CODEX.md does not contain current LEGEND_HASH {LEGEND_HASH[:16]}…")

    # Codex must reference all 7 ADRs
    from ugk.adr import ADR_REGISTRY
    for adr_id in ADR_REGISTRY:
        if adr_id not in codex_text:
            fails.append(f"CODEX.md missing ADR {adr_id}")

    ok = not fails
    size_kb = len(content) / 1024
    return ok, (
        f"ATLAS-S-04: CODEX.md ({size_kb:.1f}KB) hash verified ({pinned_hash[:16]}…); "
        f"LEGEND_HASH present; all {len(ADR_REGISTRY)} ADRs referenced." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"codex_integrity_gate: {'PASS' if ok else 'FAIL'}  {detail}")
