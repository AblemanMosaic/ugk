"""ugk/conformance/csh_mcir_gate.py — Phase 3: MCIR hyperedge finality + equivocation + IC."""


def __genesis_dir():
    from ugk._paths import genesis_dir; return genesis_dir()


def run():
    """Prove MCIR hyperedge properties:
      1. finality_hash is a function of sorted valid signatures (deterministic).
      2. Adding an invalid attestation does not change finality_hash.
      3. Equivocation (double-signing) is detected and equivocator excluded.
      4. InceptionCertificate verifies and ic_hash is stable.
      5. RotationRule is pre-declared on the kernel after ceremony.
    """
    from ugk.csh import (
        create_attestation, seal_validator_set, achieve_finality,
        detect_equivocation, InceptionCertificate,
    )
    from ugk.kernel import GovernanceKernel, GOVERNOR_PUBKEY_HEX, _PHASE_CODE
    from ugk.storage.binding import mosaic_id
    from ugk.vendor.ed25519 import generate_keypair
    from pathlib import Path
    import hashlib, json
    fails = []

    # Dev fixture — pub DERIVED from priv (founding-independent). The priv is
    # written to genesis/ only on founded trees, only for the rotation proof,
    # and removed in a finally block (exception-safe).
    from ugk.conformance._fixture import DEV_FIXTURE_PRIVKEY, fixture_pubkey, unfounded
    priv_hex    = DEV_FIXTURE_PRIVKEY
    _unf        = unfounded()
    _priv_path  = __genesis_dir() / "GENESIS_PRIVKEY.hex"
    _had_privkey = _priv_path.exists()
    pub_hex     = fixture_pubkey()
    ic_path     = __genesis_dir() / "LAUNCH_IC.json"
    law_hash    = hashlib.sha256(
        __import__("ugk.module_registry",fromlist=["law_path"]).law_path().read_bytes()
    ).hexdigest()
    mosaic_root = mosaic_id(pub_hex)
    vs          = seal_validator_set(priv_hex, pub_hex, [mosaic_root])
    att1        = create_attestation(priv_hex, pub_hex, law_hash, _PHASE_CODE, epoch=0)
    mcir1       = achieve_finality([att1], vs, law_hash)

    # --- 1. Determinism of finality_hash ---
    att1b = create_attestation(priv_hex, pub_hex, law_hash, _PHASE_CODE, epoch=0)
    mcir1b = achieve_finality([att1b], vs, law_hash)
    if mcir1.finality_hash != mcir1b.finality_hash:
        fails.append("finality_hash non-deterministic (same inputs, different outputs)")

    # --- 2. Invalid attestation does not affect finality_hash ---
    _, other_pub = generate_keypair()
    other_priv, _ = generate_keypair()
    # Attestation from a non-validator pubkey — not in validator set
    bad_att = create_attestation(other_priv, other_pub, law_hash, _PHASE_CODE, epoch=0)
    mcir_with_bad = achieve_finality([att1, bad_att], vs, law_hash)
    if not mcir_with_bad.quorum_achieved:
        fails.append("Quorum lost when invalid attestation was added (should be unaffected)")
    if mcir_with_bad.finality_hash != mcir1.finality_hash:
        fails.append("finality_hash changed when invalid attestation was added")
    if bad_att not in mcir_with_bad.invalid_attestations:
        fails.append("Non-validator attestation was not in invalid_attestations")

    # --- 3. Equivocation: double-signing different hashes → exclusion ---
    att_eq1 = create_attestation(priv_hex, pub_hex, law_hash, _PHASE_CODE, epoch=1)
    att_eq2 = create_attestation(priv_hex, pub_hex, "b" * 64, _PHASE_CODE, epoch=1)
    equivocators = detect_equivocation([att_eq1, att_eq2])
    if mosaic_root not in equivocators:
        fails.append("Equivocating validator not detected by detect_equivocation()")
    # MCIR excludes equivocators → quorum fails for N=1
    mcir_equivocated = achieve_finality([att_eq1, att_eq2], vs, law_hash)
    if mcir_equivocated.quorum_achieved:
        fails.append("MCIR achieved quorum despite equivocation (equivocator not excluded)")
    if mosaic_root not in mcir_equivocated.equivocators:
        fails.append("Equivocator not surfaced in MCIR.equivocators")

    # --- 4. InceptionCertificate — posture-aware ---
    if _unf:
        if ic_path.exists():
            fails.append("genesis/LAUNCH_IC.json present on an unfounded tree (inconsistent neutral state)")
    elif not ic_path.exists():
        fails.append("genesis/LAUNCH_IC.json not found")
    else:
        ic_data = json.loads(ic_path.read_text())
        ic = InceptionCertificate(**ic_data)
        if not ic.verify():
            fails.append("InceptionCertificate.verify() returned False")
        ic_hash_1 = ic.ic_hash()
        ic_hash_2 = ic.ic_hash()  # determinism
        if ic_hash_1 != ic_hash_2:
            fails.append("ic_hash() non-deterministic")
        if ic.ic_type != "trusted-genesis":
            fails.append(f"IC type is {ic.ic_type!r}, expected 'trusted-genesis'")
        if not ic.sunset_declared:
            fails.append("Launch IC sunset_declared is False (should be True for dev_temp)")

    # --- 5. RotationRule — posture-aware ---
    if _unf:
        from ugk.kernel import GovernanceNotFounded as _GNF
        k = GovernanceKernel()
        try:
            k._ceremony()
            fails.append("sentinel ceremony ADMITTED — rotation surface reachable unfounded")
        except _GNF:
            pass
    else:
        try:
            if not _had_privkey:
                _priv_path.write_text(priv_hex + "\n")
            k = GovernanceKernel()
            k._ceremony()
            if not hasattr(k, "_rotation_rule") or k._rotation_rule is None:
                fails.append("kernel._rotation_rule absent after ceremony")
            else:
                rr = k._rotation_rule
                if rr.current_holder != k._mosaic_root:
                    fails.append(f"RotationRule.current_holder mismatch")
                if not rr.governed_by_ic:
                    fails.append("RotationRule.governed_by_ic is empty")
        finally:
            if not _had_privkey:
                _priv_path.unlink(missing_ok=True)

    ok = not fails
    _p = ("unfounded: IC absent (consistent), ceremony refused (fail-closed)" if _unf
          else "IC verifies (trusted-genesis, sunset); RotationRule pre-declared")
    return ok, (
        "csh_mcir_gate: finality_hash deterministic; invalid attestation excluded; "
        "equivocation detected (equivocator excluded, quorum fails); "
        f"{_p}." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"csh_mcir_gate: {'PASS' if ok else 'FAIL'}  {detail}")
