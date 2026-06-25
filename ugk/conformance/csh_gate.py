"""ugk/conformance/csh_gate.py — Phase 3: CSH quorum over the constitutional frame."""


def __genesis_dir():
    from ugk._paths import genesis_dir; return genesis_dir()


def run():
    """Prove CSH constitutional finality:
      1. Governor creates a valid Attestation over law_hash.
      2. ValidatorSet contains the Governor's MosaicID.
      3. achieve_finality() produces MCIR with quorum_achieved=True (N=1 threshold=1).
      4. kernel._ceremony() produces csh_finality_hash and csh_quorum_achieved=True.
      5. csh_finality_hash is deterministic: same inputs produce same hash.
      6. Wrong constitutional_hash fails quorum (bad attestation rejected).
    """
    from ugk.kernel import GovernanceKernel, GOVERNOR_PUBKEY_HEX, _PHASE_CODE
    from ugk.csh import create_attestation, seal_validator_set, achieve_finality
    from ugk.storage.binding import mosaic_id
    from pathlib import Path
    import hashlib
    fails = []

    # Dev fixture — bootstrap keypair (Coder-seen, not production-secret).
    # pub is DERIVED from the fixture priv (founding-independent); the priv is
    # written to genesis/ only on founded trees, only for the kernel-ceremony
    # proof, and removed in a finally block (exception-safe).
    from ugk.conformance._fixture import DEV_FIXTURE_PRIVKEY, fixture_pubkey, unfounded
    priv_hex    = DEV_FIXTURE_PRIVKEY
    _unf        = unfounded()
    pub_hex     = fixture_pubkey()
    _priv_path  = __genesis_dir() / "GENESIS_PRIVKEY.hex"
    _had_privkey = _priv_path.exists()

    law_hash    = hashlib.sha256(
        __import__("ugk.module_registry",fromlist=["law_path"]).law_path().read_bytes()
    ).hexdigest()
    mosaic_root = mosaic_id(pub_hex)

    # --- 1. Attestation verifies ---
    att = create_attestation(priv_hex, pub_hex, law_hash, _PHASE_CODE, epoch=0)
    if not att.verify():
        fails.append("Attestation.verify() returned False")
    if att.constitutional_hash != law_hash:
        fails.append(f"Attestation.constitutional_hash mismatch")
    if att.mosaic_root != mosaic_root:
        fails.append(f"Attestation.mosaic_root mismatch")

    # --- 2 + 3. ValidatorSet + MCIR quorum ---
    vs = seal_validator_set(priv_hex, pub_hex, [mosaic_root])
    if not vs.verify_seal():
        fails.append("ValidatorSet.verify_seal() returned False")
    if not vs.contains(mosaic_root):
        fails.append("ValidatorSet does not contain Governor's MosaicID")

    mcir = achieve_finality([att], vs, law_hash)
    if not mcir.quorum_achieved:
        fails.append(f"MCIR quorum not achieved (threshold={mcir.quorum_threshold}, valid={len(mcir.valid_attestations)})")
    if not mcir.finality_hash or len(mcir.finality_hash) != 64:
        fails.append(f"MCIR finality_hash invalid: {mcir.finality_hash!r}")
    if mcir.invalid_attestations:
        fails.append(f"MCIR has {len(mcir.invalid_attestations)} invalid attestations (expected 0)")

    # --- 4. Kernel ceremony — posture-aware ---
    if _unf:
        # Unfounded: ceremony must refuse (CHARTER-S-01 fail-closed); no
        # privkey is written, no CSH artifacts are generated.
        from ugk.kernel import GovernanceNotFounded as _GNF
        k = GovernanceKernel()
        try:
            k._ceremony()
            fails.append("sentinel ceremony ADMITTED — CSH reachable on unfounded kernel")
        except _GNF:
            pass
        if getattr(k, "_csh_quorum_achieved", False):
            fails.append("csh_quorum_achieved True on unfounded kernel")
    else:
        try:
            if not _had_privkey:
                _priv_path.write_text(priv_hex + "\n")
            k = GovernanceKernel()
            k._ceremony()
            if not k._csh_quorum_achieved:
                fails.append("kernel._csh_quorum_achieved is False after ceremony")
            if not k._csh_finality_hash:
                fails.append("kernel._csh_finality_hash is empty after ceremony")
            snap = k.snapshot_fast()
            if not snap.get("csh_quorum_achieved"):
                fails.append("csh_quorum_achieved absent/False in snapshot_fast()")
            if not snap.get("csh_finality_hash"):
                fails.append("csh_finality_hash absent in snapshot_fast()")
            if not snap.get("launch_ic_hash"):
                fails.append("launch_ic_hash absent in snapshot_fast()")
        finally:
            if not _had_privkey:
                _priv_path.unlink(missing_ok=True)

    # --- 5. Determinism: same inputs → same finality_hash ---
    att2 = create_attestation(priv_hex, pub_hex, law_hash, _PHASE_CODE, epoch=0)
    mcir2 = achieve_finality([att2], vs, law_hash)
    if mcir2.finality_hash != mcir.finality_hash:
        fails.append("CSH finality_hash is non-deterministic (two runs differ)")

    # --- 6. Wrong constitutional_hash → quorum fails ---
    bad_att = create_attestation(priv_hex, pub_hex, "a" * 64, _PHASE_CODE, epoch=0)
    bad_mcir = achieve_finality([bad_att], vs, law_hash)  # law_hash is the truth
    if bad_mcir.quorum_achieved:
        fails.append("MCIR achieved quorum with wrong constitutional_hash (should fail)")

    ok = not fails
    _p = ("unfounded: ceremony refused, CSH unreachable (fail-closed)" if _unf
          else "kernel ceremony surfaces CSH")
    return ok, (
        f"csh_gate: N=1 quorum achieved; finality_hash={mcir.finality_hash[:16]}…; "
        f"deterministic; wrong hash rejected; {_p}." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"csh_gate: {'PASS' if ok else 'FAIL'}  {detail}")
