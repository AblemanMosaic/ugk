"""ugk/conformance/dkn_gate.py — MosaicID, dimension_id, session_dkn ordering. GATE_GROUP = "unit" """


def run():
    """Prove five DKN properties:

    1. MosaicID = SHA-256(governor_pubkey) — derivable without secret.
    2. dimension_id = canonical_dkn(phase_code, governor_pubkey) — compound anchor.
    3. session_dkn = SHA-256(mosaic_root:phase_code:session_id) — WHO×WHAT×WHICH ordering.
    4. Unsquattability: different pubkeys → different MosaicIDs and dimension_ids.
    5. Identity ≠ authority: knowing pubkey does NOT let you pass verify_governor().
    """
    from ugk.kernel import GovernanceKernel, GOVERNOR_PUBKEY_HEX, _PHASE_CODE
    from ugk.storage.binding import mosaic_id, canonical_dkn, spawn_session_identity
    from ugk.governance.governor import verify_governor
    from ugk.vendor.ed25519 import generate_keypair
    import hashlib
    fails = []

    # --- Proof 1: MosaicID derivation ---
    computed_mosaic = mosaic_id(GOVERNOR_PUBKEY_HEX)
    expected_mosaic = hashlib.sha256(GOVERNOR_PUBKEY_HEX.encode("utf-8")).hexdigest()
    if computed_mosaic != expected_mosaic:
        fails.append(f"MosaicID mismatch: {computed_mosaic[:16]!r}… vs {expected_mosaic[:16]!r}…")

    k = GovernanceKernel()
    k._ceremony()
    if k._mosaic_root != expected_mosaic:
        fails.append(f"kernel._mosaic_root {k._mosaic_root[:16]!r}… != expected")

    # --- Proof 2: dimension_id is the compound anchor (NOT in session_dkn) ---
    expected_dim = canonical_dkn(_PHASE_CODE, GOVERNOR_PUBKEY_HEX)
    # Independent derivation (raw hashlib, no ugk.binding): the AD-14 record form —
    # dimension_id = SHA-256(phase_code ‖ governor_pubkey), ‖ = U+2016 DM-S-03 separator.
    # Catches canonical_dkn construction drift from the constitutional record.
    independent_dim = hashlib.sha256(
        (_PHASE_CODE + "\u2016" + GOVERNOR_PUBKEY_HEX).encode("utf-8")
    ).hexdigest()
    if expected_dim != independent_dim:
        fails.append(
            "canonical_dkn drifted from AD-14 record form "
            f"(flat phase_code‖SEP‖pubkey): {expected_dim[:16]!r}… vs {independent_dim[:16]!r}…"
        )
    if k._dimension_id != expected_dim:
        fails.append(f"kernel._dimension_id mismatch")
    if len(k._dimension_id) != 64:
        fails.append(f"dimension_id length {len(k._dimension_id)}, expected 64")

    # --- Proof 3: session_dkn = SHA-256(mosaic_root:phase_code:session_id) WHO×WHAT×WHICH ---
    k.open_session()
    si = spawn_session_identity(GOVERNOR_PUBKEY_HEX, _PHASE_CODE, k._session_dkn[:8])
    # Independent derivation using known ordering
    _root = mosaic_id(GOVERNOR_PUBKEY_HEX)
    _sid = k._session_dkn[:8]
    expected_dkn = hashlib.sha256(f"{_root}:{_PHASE_CODE}:{_sid}".encode("utf-8")).hexdigest()
    # Note: k._session_dkn is derived with actual UUID, not this test sid
    # Verify the ordering property via spawn_session_identity directly
    si2 = spawn_session_identity(GOVERNOR_PUBKEY_HEX, _PHASE_CODE, "fixed-session-id")
    expected2 = hashlib.sha256(f"{_root}:{_PHASE_CODE}:fixed-session-id".encode("utf-8")).hexdigest()
    if si2.session_dkn != expected2:
        fails.append(
            f"session_dkn ordering incorrect: got {si2.session_dkn[:16]!r}… "
            f"expected SHA-256(mosaic_root:phase_code:session_id) = {expected2[:16]!r}…"
        )
    # Verify dimension_id is NOT in session_dkn computation (independent derivation)
    # If dimension_id were in the derivation, changing phase_code but not pubkey
    # would change dimension_id AND session_dkn through dimension_id.
    # We verify: session_dkn depends only on mosaic_root + phase_code + session_id.
    si3 = spawn_session_identity(GOVERNOR_PUBKEY_HEX, "different-phase", "fixed-session-id")
    expected3 = hashlib.sha256(f"{_root}:different-phase:fixed-session-id".encode("utf-8")).hexdigest()
    if si3.session_dkn != expected3:
        fails.append("session_dkn with different phase_code does not match expected three-layer hash")
    if si2.session_dkn == si3.session_dkn:
        fails.append("Different phase_code produced same session_dkn (phase not bound)")

    # --- Proof 4: Unsquattability ---
    _, other_pub1 = generate_keypair()
    _, other_pub2 = generate_keypair()
    m1, m2 = mosaic_id(other_pub1), mosaic_id(other_pub2)
    d1, d2 = canonical_dkn(_PHASE_CODE, other_pub1), canonical_dkn(_PHASE_CODE, other_pub2)
    if m1 == computed_mosaic: fails.append("Different pubkey → same MosaicID")
    if m1 == m2: fails.append("Two random pubkeys → same MosaicID")
    if d1 == expected_dim: fails.append("Different pubkey → same dimension_id as Governor")
    if d1 == d2: fails.append("Two random pubkeys → same dimension_id")
    if canonical_dkn("other-phase", GOVERNOR_PUBKEY_HEX) == expected_dim:
        fails.append("Different phase_code → same dimension_id")

    # --- Proof 5: Identity ≠ authority ---
    msg = b"forge-attempt"
    if verify_governor(GOVERNOR_PUBKEY_HEX, msg, "00" * 64):
        fails.append("All-zero forged signature verified")
    other_priv, _ = generate_keypair()
    from ugk.vendor.ed25519 import sign as _sign
    if verify_governor(GOVERNOR_PUBKEY_HEX, msg, _sign(msg, other_priv)):
        fails.append("Wrong-key signature verified against Governor pubkey")

    ok = not fails
    return ok, (
        f"DKN-S-01: MosaicID={computed_mosaic[:16]}…; "
        f"dimension_id={expected_dim[:16]}… (compound anchor, not in session_dkn); "
        f"session_dkn=SHA-256(mosaic_root:phase_code:session_id) WHO×WHAT×WHICH; "
        "unsquattability; identity≠authority." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"dkn_gate: {'PASS' if ok else 'FAIL'}  {detail}")
