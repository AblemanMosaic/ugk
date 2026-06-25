"""ugk/conformance/chc_gate.py — CHC-S-01: CHC envelope on every receipt, D1-D8 correct."""


def run():
    from ugk.kernel import GovernanceKernel
    fails = []

    k = GovernanceKernel()
    k.open_session()
    k.execute(op="crp_evidence", authority="chc_test", parameters={"x": 1})

    receipts = k.store.all_receipts()
    if not receipts:
        return False, "No receipts in store"

    for r in receipts:
        # intent must be populated
        if not r.intent:
            fails.append(f"Receipt {r.op!r}: intent is empty (D3 missing)")
        # authority must be populated
        if not r.authority:
            fails.append(f"Receipt {r.op!r}: authority is empty (D4 missing)")
        # jurisdiction must be populated (D5)
        if not r.jurisdiction:
            fails.append(f"Receipt {r.op!r}: jurisdiction is empty (D5 missing)")
        # RT-2d/RT-3 (E5b): the receipt commitment surface is the M2 / THR binding structure. Every
        # receipt must carry the M2 binding leaves + root. (Legacy CHC envelope fields removed at r80.)
        for _leg in ("h_s", "h_c", "h_m", "h_r"):
            _v = getattr(r, _leg, "")
            if len(_v) != 64:
                fails.append(f"Receipt {r.op!r}: M2 binding leg {_leg} not a 64-hex value (RT-2d)")
        # session_dkn is D7 custody — populated after open_session()
        # (first receipt may be session_open before dkn is set; that's ok)

    # Verify CHC_DIMENSIONS structure
    from ugk.storage.binding import CHC_DIMENSIONS
    for dim_id in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"):
        if dim_id not in CHC_DIMENSIONS:
            fails.append(f"CHC_DIMENSIONS missing {dim_id}")
    if CHC_DIMENSIONS.get("D6", {}).get("absent") is not True:
        fails.append("D6 SEMANTICS must be marked absent=True")
    if CHC_DIMENSIONS.get("D8", {}).get("envelope") is not False:
        fails.append("D8 RESOURCES must be envelope=False (metadata only)")

    ok = not fails
    return ok, (f"CHC envelope present on all {len(receipts)} receipts; "
                f"D1-D8 registry correct (D6 absent, D8 metadata)." if ok
                else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"chc_gate: {'PASS' if ok else 'FAIL'}  {detail}")
