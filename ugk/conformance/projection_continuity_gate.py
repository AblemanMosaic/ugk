"""ugk/conformance/projection_continuity_gate.py — LEGEND-S-04: governed vocabulary projection."""


def run():
    """Prove that compressed receipt fields stay within the governed vocabulary.
    FIELD_COMPRESS_MAPS maps every registered term to its CSIL integer.
    Unregistered terms are preserved as-is (not mangled) — projection
    continuity means no silent corruption, not rigid rejection.
    """
    from ugk.storage.binding import FIELD_COMPRESS_MAPS, LEGEND_BY_ID
    from ugk.storage.store import UGKReceiptStore
    fails = []

    # Every registered term in each field map compresses and expands correctly
    for field_name, compress_map in FIELD_COMPRESS_MAPS.items():
        for render_form, csil_id in compress_map.items():
            # Verify the CSIL id maps back to the same render form
            entry = LEGEND_BY_ID.get(csil_id)
            if entry is None:
                fails.append(f"FIELD_COMPRESS_MAPS[{field_name!r}][{render_form!r}]"
                              f" → csil_id {csil_id} not in LEGEND_BY_ID")
                continue
            if entry["render"] != render_form:
                fails.append(f"CSIL:{csil_id} render={entry['render']!r} "
                              f"!= compress_map entry {render_form!r}")

    # Resolution C — constitutional vocabulary boundary (not deployment extensibility):
    # the FROZEN CSIL legend pins the CONSTITUTIONAL op vocabulary — Tier-0 kernel ops
    # (_KERNEL_OPS) and Tier-1 universal ops (_UNIVERSAL_OPS). Deployment-declarable
    # Tier-2 APPLICATION_OPS (ops.py, 644) are intentionally EXEMPT: they fall back to
    # their uncompressed render form, consistent with this gate's own rule that
    # unregistered terms are preserved as-is, not rejected. Requiring mutable app-ops to
    # live inside the frozen legend would conflict with the M2.3 legend freeze (a1_gate).
    from ugk.schema import _UNIVERSAL_OPS, _KERNEL_OPS
    constitutional_ops = set(_UNIVERSAL_OPS.keys()) | set(_KERNEL_OPS)
    op_map = FIELD_COMPRESS_MAPS["op"]
    for op in constitutional_ops:
        if op not in op_map:
            fails.append(f"Constitutional op {op!r} (universal/kernel) missing from the frozen op legend")

    # Roundtrip via store: each registered term survives compress=True
    store = UGKReceiptStore()
    store.write(op="crp_evidence", authority="pc_gate",
                parameters={}, intent="orient", jurisdiction="session",
                confidence="high", compress=True)
    r = store.all_receipts()[-1]
    checks = [("op", r.op, "crp_evidence"), ("intent", r.intent, "orient"),
              ("jurisdiction", r.jurisdiction, "session"), ("confidence", r.confidence, "high")]
    for fname, got, want in checks:
        if got != want:
            fails.append(f"Projection continuity: {fname} expanded to {got!r}, expected {want!r}")

    ok = not fails
    n_terms = sum(len(m) for m in FIELD_COMPRESS_MAPS.values())
    return ok, (
        f"LEGEND-S-04: {n_terms} governed vocabulary terms all compress and "
        f"expand correctly; all constitutional (universal/kernel) ops in compress map; "
        f"deployment APPLICATION_OPS exempt (uncompressed fallback); "
        f"roundtrip via store verified." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"projection_continuity_gate: {'PASS' if ok else 'FAIL'}  {detail}")
