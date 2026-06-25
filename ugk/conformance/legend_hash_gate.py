"""ugk/conformance/legend_hash_gate.py — LEGEND-S-01: LEGEND constant stable and content-addressed."""


def run():
    from ugk.storage.binding import (
        LEGEND_BY_ID, LEGEND_BY_SLUG, LEGEND_HASH, LEGEND_ENTRY_COUNT,
        _LEGEND_ENTRIES,
    )
    import hashlib, json
    fails = []

    # Bidirectionality
    for cid, entry in LEGEND_BY_ID.items():
        slug = entry["slug"]
        if LEGEND_BY_SLUG.get(slug, {}).get("csil_id") != cid:
            fails.append(f"LEGEND_BY_ID[{cid}] → slug {slug!r} does not round-trip")

    for slug, entry in LEGEND_BY_SLUG.items():
        cid = entry["csil_id"]
        if LEGEND_BY_ID.get(cid, {}).get("slug") != slug:
            fails.append(f"LEGEND_BY_SLUG[{slug!r}] → csil_id {cid} does not round-trip")

    # LEGEND_HASH is SHA-256(canonical sorted entries)
    canonical = json.dumps(
        sorted(_LEGEND_ENTRIES, key=lambda e: e["csil_id"]),
        sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    expected_hash = hashlib.sha256(canonical).hexdigest()
    if LEGEND_HASH != expected_hash:
        fails.append(f"LEGEND_HASH mismatch: {LEGEND_HASH[:16]!r} != {expected_hash[:16]!r}")

    # Hash is stable (deterministic — run twice)
    if hashlib.sha256(canonical).hexdigest() != LEGEND_HASH:
        fails.append("LEGEND_HASH non-deterministic")

    # Each entry has required fields
    for entry in _LEGEND_ENTRIES:
        for field in ("csil_id", "slug", "render", "tier"):
            if field not in entry or not str(entry[field]).strip():
                fails.append(f"Entry {entry.get('csil_id')} missing field {field!r}")

    # Entry count sanity
    if LEGEND_ENTRY_COUNT < 70:
        fails.append(f"Only {LEGEND_ENTRY_COUNT} entries — expected ≥ 70")

    ok = not fails
    return ok, (
        f"LEGEND-S-01: {LEGEND_ENTRY_COUNT} entries, bidirectionally consistent, "
        f"LEGEND_HASH={LEGEND_HASH[:16]}… stable." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"legend_hash_gate: {'PASS' if ok else 'FAIL'}  {detail}")
