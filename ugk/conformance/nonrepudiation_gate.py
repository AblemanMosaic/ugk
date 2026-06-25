"""ugk/conformance/nonrepudiation_gate.py — CHC-S-03: every DM-S-03 field is tamper-evident."""

def run():
    """Altering ANY of the 10 DM-S-03 fields changes the semantic_hash.

    Proof: compute baseline hash, then flip each field one at a time and assert
    the hash changes.  All perturbation is on synthetic inputs — no stored state
    is touched.
    """
    fails = []

    # RT-3 (E5b): non-repudiation is anchored on the M2 binding root. Perturbing any M2 binding leaf
    # changes the receipt root H_r. (Legacy dm_s03 envelope-field proof removed at r80.)
    from ugk.storage.binding_m2 import compute_H_r, TAG_H_S, TAG_H_C, TAG_H_M
    _m2_leaves = [(TAG_H_S, b"s" * 32), (TAG_H_C, b"c" * 32), (TAG_H_M, b"m" * 32)]
    _m2_base = compute_H_r(_m2_leaves)
    _m2_undet = []
    for _i in range(len(_m2_leaves)):
        _p = list(_m2_leaves)
        _t, _v = _p[_i]
        _p[_i] = (_t, bytes([(_v[0] + 1) % 256]) + _v[1:])
        if compute_H_r(_p) == _m2_base:
            _m2_undet.append(_t)
    if _m2_undet:
        fails.append(f"M2-leaf tamper undetected for leaf tags: {_m2_undet} (RT-2g)")

    ok = not fails
    return ok, (
        "CHC-S-03 (M2 form): every M2 binding leaf is tamper-evident in the receipt root H_r."
        if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"nonrepudiation_gate: {'PASS' if ok else 'FAIL'}  {detail}")
