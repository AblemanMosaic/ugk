"""ugk/conformance/governor_signature_gate.py — Ed25519 sign/verify roundtrip."""

# Dev fixture — bootstrap keypair (Coder-seen, not production-secret).
# Matches the GOVERNOR_PUBKEY_HEX shipped in kernel.py for this build.
# When the Governor rotates to an off-artifact key, update this constant
# or rewrite to use ephemeral-only testing.
_DEV_FIXTURE_PRIVKEY = "cb181d9a650b7605b94602d0d6a2640a38fa1a0f1086c4896f98e40c21766857"


def run():
    from ugk.kernel import GOVERNOR_PUBKEY_HEX
    from ugk.governance.governor import verify_governor, sign_as_governor, validate_genesis_seal, load_genesis_seal
    from ugk.vendor.ed25519 import generate_keypair
    from ugk.conformance._fixture import unfounded, fixture_pubkey
    fails = []
    _unf = unfounded()
    fpub = fixture_pubkey()

    msg = b"ugk-governor-signature-test"

    # --- Mechanism test with dev fixture key (founding-independent) ---
    sig = sign_as_governor(_DEV_FIXTURE_PRIVKEY, msg)
    if not verify_governor(fpub, msg, sig):
        fails.append("verify_governor() rejected fixture sig against the fixture's own derived pubkey")
    if len(sig) != 128:
        fails.append(f"signature length {len(sig)}, expected 128")

    # --- Posture branch ---
    if _unf:
        # Unfounded: the installed sentinel must never verify anything (fail-closed)
        if verify_governor(GOVERNOR_PUBKEY_HEX, msg, sig):
            fails.append("verify_governor() accepted a sig against the unset sentinel (fail-open)")
    else:
        # Founded: this build's fixture must match the installed identity
        if not verify_governor(GOVERNOR_PUBKEY_HEX, msg, sig):
            fails.append(
                "verify_governor() rejected dev fixture sig against GOVERNOR_PUBKEY_HEX "
                "(fixture key does not match installed pubkey — rotate _DEV_FIXTURE_PRIVKEY)"
            )

    # --- Tampered message fails ---
    if verify_governor(fpub, msg + b"_TAMPERED", sig):
        fails.append("verify_governor() accepted tampered message")

    # --- Different ephemeral key fails ---
    _, other_pub = generate_keypair()
    if verify_governor(other_pub, msg, sig):
        fails.append("verify_governor() accepted sig under wrong pubkey")

    # --- Sentinel never verifies ---
    if verify_governor("GOVERNOR_KEY_UNSET__RUN_GENESIS_CEREMONY", msg, sig):
        fails.append("verify_governor() accepted unset sentinel")

    # --- Invalid hex fails gracefully ---
    if verify_governor(GOVERNOR_PUBKEY_HEX, msg, "not_valid_hex"):
        fails.append("verify_governor() accepted invalid hex without raising")

    # --- Genesis seal validates without privkey (public-key-only verification) ---
    seal_data = load_genesis_seal()
    if seal_data:
        if not validate_genesis_seal(seal_data, GOVERNOR_PUBKEY_HEX):
            fails.append("genesis seal validation failed against GOVERNOR_PUBKEY_HEX")

    ok = not fails
    _posture = "unfounded: sentinel fail-closed proven" if _unf else "founded: fixture matches installed identity"
    return ok, (
        f"Ed25519 sign/verify roundtrip correct ({_posture}); "
        "tampered message, wrong key, sentinel, invalid hex all rejected; "
        "genesis seal validated when present." if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"governor_signature_gate: {'PASS' if ok else 'FAIL'}  {detail}")
