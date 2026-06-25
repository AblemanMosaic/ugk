"""ugk/conformance/staleness_gate.py — CTR-S-07: invariants.py is pinned and ACTIVE receipts carry it."""


def run():
    """Two proofs:
      1. _ceremony() computes law_hash = SHA-256(invariants.py) — matches independent computation.
      2. ACTIVE receipts carry that law_hash — constitutional drift is detectable per receipt.
    """
    import hashlib
    from pathlib import Path
    from ugk.kernel import GovernanceKernel
    fails = []

    # --- Proof 1: law_hash = SHA-256(invariants.py) ---
    pkg_root = Path(__file__).resolve().parent.parent
    from ugk.module_registry import law_path as _lp; inv_path = _lp()

    if not inv_path.exists():
        return False, f"invariants.py not found at {inv_path}"

    expected_law_hash = hashlib.sha256(inv_path.read_bytes()).hexdigest()

    k = GovernanceKernel()
    k._ceremony()

    if k._law_hash != expected_law_hash:
        fails.append(
            f"law_hash mismatch: kernel has {k._law_hash[:16]!r}…, "
            f"independent SHA-256(invariants.py) = {expected_law_hash[:16]!r}…"
        )

    # --- Proof 2: ACTIVE receipts carry law_hash ---
    k.open_session()
    k.execute(op="crp_evidence", authority="staleness_t", parameters={"x": 1})

    receipts_with_law_hash = [
        r for r in k.store.all_receipts()
        if r.law_hash == expected_law_hash
    ]
    if not receipts_with_law_hash:
        fails.append(
            "No receipts carry the expected law_hash after _ceremony() — "
            "ACTIVE receipts are not self-situating (CTR-S-07 violated)"
        )

    # Verify that receipts written BEFORE ceremony have empty law_hash
    k2 = GovernanceKernel()
    k2.open_session()
    k2.execute(op="crp_evidence", authority="before_ceremony", parameters={"pre": True})
    pre_receipts = k2.store.all_receipts()
    pre_with_law_hash = [r for r in pre_receipts if r.law_hash]
    if pre_with_law_hash:
        fails.append(
            f"Receipts before ceremony carry non-empty law_hash: "
            f"{[r.op for r in pre_with_law_hash]}"
        )

    ok = not fails
    return ok, (
        f"CTR-S-07: law_hash={expected_law_hash[:16]!r}… matches SHA-256(invariants.py); "
        f"{len(receipts_with_law_hash)} ACTIVE receipt(s) carry it; "
        f"pre-ceremony receipts have empty law_hash." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"staleness_gate: {'PASS' if ok else 'FAIL'}  {detail}")
