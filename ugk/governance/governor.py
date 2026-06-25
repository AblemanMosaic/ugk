"""ugk/governor.py — Governor identity and signature verification (Grundnorm layer, 444).

Phase 2 additions:
  verify_governor(pubkey_hex, message, sig_hex) → bool
  governor_key_status()  → "unset" | "dev_temp" | "ceremony_complete"
  load_genesis_seal()    → dict (genesis seal body + signature)
  validate_genesis_seal(seal_json) → bool

The Governor key is the root of constitutional identity in UGK.
Identity ≠ authority:
  MosaicID (SHA-256(pubkey)) proves WHO across sessions — derivable from
  the public key alone, requires no secret.
  verify_governor() proves authority over a specific op — requires a live
  Ed25519 signature from the holder of the private key.

Key status semantics:
  "unset"            — GOVERNOR_PUBKEY_HEX is the Phase 1 sentinel string
  "dev_temp"         — Real Ed25519 pubkey, Coder-generated for Phase 2 dev
  "ceremony_complete"— Governor-held key installed via full ceremony (Phase 2+)

Require-Governor-Sig interposition:
  GovernanceKernel accepts a `require_governor_sig` flag.  When True, any
  Tier 2 APPLICATION op must be accompanied by a valid Governor signature
  over canonical_json({"op": op, "parameters": parameters}).
  This is the Governor interposition mechanism: the Governor can veto any
  application-layer operation by withholding their signature.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ugk.vendor.ed25519 import verify as _ed25519_verify
from ugk.storage.binding import canonical_json, mosaic_id as _mosaic_id


# ---------------------------------------------------------------------------
# Typed exception
# ---------------------------------------------------------------------------

class GovernorSignatureRequired(Exception):
    """Raised when a Tier 2 op requires a Governor signature but none is provided
    or the provided signature fails verification.

    Carries the op name and reason for structured handling.
    """
    def __init__(self, op: str, reason: str = "signature absent or invalid"):
        self.op = op
        self.reason = reason
        super().__init__(
            f"GovernorSignatureRequired: op={op!r} requires a valid "
            f"Governor Ed25519 signature. reason={reason!r}"
        )


# ---------------------------------------------------------------------------
# Governor key status
# ---------------------------------------------------------------------------

def governor_key_status(pubkey_hex: str) -> str:
    """Derive key status from the GOVERNOR_PUBKEY_HEX constant.

    Returns:
        "unset"             — sentinel string (Phase 1)
        "dev_temp"          — valid hex pubkey, Coder-generated
        "ceremony_complete" — valid hex pubkey, genesis seal present in genesis/
    """
    if pubkey_hex.startswith("GOVERNOR_KEY_UNSET"):
        return "unset"
    # Validate: must be 64 lowercase hex chars
    if len(pubkey_hex) != 64:
        return "unset"
    try:
        bytes.fromhex(pubkey_hex)
    except ValueError:
        return "unset"
    # Check if genesis seal exists and has key_status == "ceremony_complete"
    from ugk._paths import genesis_dir as _gd
    genesis_path = _gd() / "GENESIS_SEAL.json"
    if genesis_path.exists():
        try:
            with genesis_path.open() as f:
                data = json.load(f)
            if data.get("key_status") == "ceremony_complete":
                return "ceremony_complete"
        except Exception:
            pass
    return "dev_temp"


# ---------------------------------------------------------------------------
# Governor signature verification
# ---------------------------------------------------------------------------

def verify_governor(
    pubkey_hex: str,
    message:    bytes,
    sig_hex:    str,
) -> bool:
    """Verify an Ed25519 signature attributed to the Governor.

    pubkey_hex: the GOVERNOR_PUBKEY_HEX constant value
    message:    canonical bytes that were signed
    sig_hex:    128-char lowercase hex Ed25519 signature

    Returns False for unset sentinel, invalid hex, or bad signature.
    Never raises.
    """
    if pubkey_hex.startswith("GOVERNOR_KEY_UNSET"):
        return False  # sentinel key — no signature can be valid
    try:
        return _ed25519_verify(message, sig_hex, pubkey_hex)
    except Exception:
        return False


def sign_as_governor(
    privkey_hex: str,
    message:     bytes,
) -> str:
    """Sign a message with the Governor private key.

    This is a DEV-ONLY helper.  In production the Governor holds the private
    key off-artifact — sign_as_governor() would be called interactively by
    the Governor, not by the kernel.  It is intentionally in governor.py
    (not kernel.py) to make the architectural distinction explicit.

    Returns 128-char lowercase hex signature.
    """
    from ugk.vendor.ed25519 import sign as _ed25519_sign
    return _ed25519_sign(message, privkey_hex)


# ---------------------------------------------------------------------------
# Genesis seal
# ---------------------------------------------------------------------------

def load_genesis_seal() -> Optional[dict]:
    """Load the genesis seal from genesis/GENESIS_SEAL.json relative to package.

    Returns the parsed dict, or None if the file is absent.
    """
    from ugk._paths import genesis_dir as _gd
    genesis_path = _gd() / "GENESIS_SEAL.json"
    if not genesis_path.exists():
        return None
    try:
        with genesis_path.open() as f:
            return json.load(f)
    except Exception:
        return None


def validate_genesis_seal(seal_data: dict, expected_pubkey: str) -> bool:
    """Validate a genesis seal dict:
      1. Signature over canonical_json(seal_data["seal"]) verifies against
         seal_data["seal"]["governor_pubkey"].
      2. seal_data["seal"]["governor_pubkey"] matches expected_pubkey.
      3. seal_data["seal"]["phase_code"] matches _PHASE_CODE from kernel.

    Returns True iff all checks pass.  Never raises.
    """
    try:
        seal_body = seal_data["seal"]
        sig_hex   = seal_data["signature"]
        pubkey    = seal_body["governor_pubkey"]

        # Check 2: pubkey in seal matches expected
        if pubkey != expected_pubkey:
            return False

        # Check 1: signature verifies
        message = canonical_json(seal_body)
        if not verify_governor(pubkey, message, sig_hex):
            return False

        # Check 3: phase_code matches (imported locally to avoid circular import)
        from ugk.kernel import _PHASE_CODE
        if seal_body.get("phase_code") != _PHASE_CODE:
            return False

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MosaicID helper (re-exports binding)
# ---------------------------------------------------------------------------

def mosaic_id_from_pubkey(pubkey_hex: str) -> str:
    """Derive MosaicID from Governor pubkey hex.

    MosaicID = SHA-256(pubkey_bytes) — stable across sessions,
    changes only on key rotation.  Proves identity (WHO), not authority.
    """
    return _mosaic_id(pubkey_hex)


__all__ = [
    "GovernorSignatureRequired",
    "governor_key_status",
    "verify_governor",
    "sign_as_governor",
    "load_genesis_seal",
    "validate_genesis_seal",
    "mosaic_id_from_pubkey",
]
