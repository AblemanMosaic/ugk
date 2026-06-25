"""ugk/conformance/successor_lineage_gate.py — SUCC-S-01: succession proof verifiable without old key."""


def run():
    from ugk.successor import SuccessorLineage
    from ugk.storage.binding import mosaic_id as _mosaic_id
    from ugk.kernel import GOVERNOR_PUBKEY_HEX
    fails = []

    # Load SUCCESSOR_LINEAGE.json from genesis/
    sl = SuccessorLineage.load_from_package()
    if sl is None:
        # Lawful for any deployment that has never rotated (incl. neutral trees
        # and ephemeral conformance foundings). Prove SUCC-S-01 mechanics with
        # an ephemeral two-key lineage instead — typed, non-silent.
        import hashlib as _hl
        from ugk.vendor.ed25519 import generate_keypair, sign as _sign
        from ugk.storage.binding import canonical_json as _cj
        old_priv, old_pub = generate_keypair()
        _, new_pub = generate_keypair()
        body = {
            "amendment_hash":     "0" * 64,
            "authority":          _mosaic_id(old_pub),
            "predecessor_mosaic": _mosaic_id(old_pub),
            "successor_mosaic":   _mosaic_id(new_pub),
            "successor_pubkey":   new_pub,
            "timestamp":          "1970-01-01T00:00:00Z",
        }
        proof = _sign(_cj(body), old_priv)
        full = dict(body); full["succession_proof"] = proof
        eph = SuccessorLineage(
            lineage_hash=_hl.sha256(_cj(full)).hexdigest(),
            succession_proof=proof, **body)
        if not eph.verify_hash():
            fails.append("ephemeral lineage_hash verification failed")
        if not eph.verify_succession(old_pub):
            fails.append("ephemeral succession_proof does not verify under predecessor pubkey")
        if eph.verify_succession(new_pub):
            fails.append("ephemeral succession_proof verifies under the SUCCESSOR key (forgeable)")
        ok = not fails
        return ok, (
            "SUCC-S-01 (no rotation yet): mechanics proven with ephemeral two-key "
            "lineage — hash verifies, proof verifies under predecessor only; "
            "shipped-lineage proofs run on rotated deployments." if ok
            else "; ".join(fails)
        )

    # lineage_hash verifies
    if not sl.verify_hash():
        fails.append("SuccessorLineage.verify_hash() failed — lineage_hash mismatch")

    # succession_proof verifies using the predecessor pubkey (current GOVERNOR_PUBKEY_HEX)
    if not sl.verify_succession(GOVERNOR_PUBKEY_HEX):
        fails.append(
            f"succession_proof does not verify against predecessor pubkey "
            f"{GOVERNOR_PUBKEY_HEX[:16]!r}…"
        )

    # predecessor_mosaic == SHA-256(GOVERNOR_PUBKEY_HEX)
    expected_predecessor = _mosaic_id(GOVERNOR_PUBKEY_HEX)
    if sl.predecessor_mosaic != expected_predecessor:
        fails.append(
            f"predecessor_mosaic {sl.predecessor_mosaic[:16]!r}… "
            f"!= mosaic_id(GOVERNOR_PUBKEY_HEX) {expected_predecessor[:16]!r}…"
        )

    # successor_mosaic == SHA-256(successor_pubkey)
    expected_successor = _mosaic_id(sl.successor_pubkey)
    if sl.successor_mosaic != expected_successor:
        fails.append(
            f"successor_mosaic {sl.successor_mosaic[:16]!r}… "
            f"!= mosaic_id(successor_pubkey)"
        )

    # Predecessor and successor are distinct
    if sl.predecessor_mosaic == sl.successor_mosaic:
        fails.append("predecessor_mosaic == successor_mosaic (no rotation occurred)")

    # Succession proof does NOT verify under the successor key
    # (proves: only the old key could sign this, not any key)
    if sl.verify_succession(sl.successor_pubkey):
        fails.append(
            "succession_proof incorrectly verifies under the successor key "
            "(should only verify under predecessor)"
        )

    ok = not fails
    return ok, (
        f"SUCC-S-01: SuccessorLineage loaded; lineage_hash verifies; "
        f"succession_proof signed by predecessor {sl.predecessor_mosaic[:8]!r}…; "
        f"verifiable without old private key; successor {sl.successor_mosaic[:8]!r}… "
        f"distinct from predecessor." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"successor_lineage_gate: {'PASS' if ok else 'FAIL'}  {detail}")
