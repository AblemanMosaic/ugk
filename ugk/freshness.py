"""ugk/freshness.py — Epoch infrastructure (REV3 §Deliverable 1).

M2.3e replaces the M2.2-era placeholder FreshnessClaim with real
Governor-signed EpochIssuance artifacts. Per Governor ruling on R-14
(roadmap §5.4), EpochIssuance is signed with the existing Governor
authority key — no separate epoch-authority key is introduced.

Public surface:
  EpochIssuance        — dataclass; phase_id, epoch_counter, valid_from,
                         valid_until, issuer_key_id, signature
  EpochRetirement      — dataclass; phase_id, retired_epoch,
                         retirement_time, issuer_key_id, signature
  id_epoch_issuance()  — SHA-256(canonical_json(EI))
  id_epoch_retirement()
  sign_epoch_issuance()
  sign_epoch_retirement()
  verify_epoch_issuance()
  verify_epoch_retirement()
  build_freshness_claim_from_epoch()
  verify_freshness_claim()
  DEFAULT_TEST_KEY     — fixed test keypair for default-epoch determinism
  default_epoch()      — pre-signed wide-window EI for in-process tests

Determinism: the default test keypair is hardcoded (not regenerated at
import time) so that H_c values bound via signed FreshnessClaim are
stable across processes. Real production uses external Governor keys.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, replace
from typing import Optional

from ugk.vendor.ed25519 import sign as _ed25519_sign, verify as _ed25519_verify


# ─────────────────────────────────────────────────────────────────────────────
# Canonicalization helper (mirrors binding_m2._canonical_json)
# ─────────────────────────────────────────────────────────────────────────────

def _canonical_json_bytes(obj) -> bytes:
    """JCS-style canonical JSON encoder."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# EpochIssuance artifact
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EpochIssuance:
    """Governor-signed declaration that epoch `epoch_counter` is valid
    in phase `phase_id` from `valid_from` to `valid_until` (inclusive).

    The signature is over the canonical JSON of all fields EXCEPT
    `signature` itself — i.e., the unsigned payload.
    """
    phase_id:        str      # = id(Φ_0); hex string per M2.3d
    epoch_counter:   int      # monotonic per phase
    valid_from:      int      # inclusive lower bound (epoch units)
    valid_until:     int      # inclusive upper bound (epoch units)
    issuer_key_id:   str      # Ed25519 public key hex
    signature:       str      # Ed25519 signature hex (128 hex chars)

    def unsigned_payload(self) -> bytes:
        """Canonical bytes that get signed."""
        return _canonical_json_bytes({
            "phase_id":      self.phase_id,
            "epoch_counter": self.epoch_counter,
            "valid_from":    self.valid_from,
            "valid_until":   self.valid_until,
            "issuer_key_id": self.issuer_key_id,
        })


def id_epoch_issuance(ei: EpochIssuance) -> str:
    """id(EpochIssuance) := SHA-256(canonical_json(full artifact))."""
    return hashlib.sha256(_canonical_json_bytes(asdict(ei))).hexdigest()


def sign_epoch_issuance(
    *,
    phase_id:        str,
    epoch_counter:   int,
    valid_from:      int,
    valid_until:     int,
    issuer_key_id:   str,
    signer_privkey_hex: str,
) -> EpochIssuance:
    """Construct an EpochIssuance and sign it with the given Ed25519 private key.

    The signer_privkey_hex must correspond to the issuer_key_id (i.e., the
    issuer_key_id must be the public key derived from signer_privkey_hex).
    No structural check is enforced here; the verification step catches
    mismatch via signature failure.
    """
    unsigned = _canonical_json_bytes({
        "phase_id":      phase_id,
        "epoch_counter": epoch_counter,
        "valid_from":    valid_from,
        "valid_until":   valid_until,
        "issuer_key_id": issuer_key_id,
    })
    sig = _ed25519_sign(unsigned, signer_privkey_hex)
    return EpochIssuance(
        phase_id=phase_id,
        epoch_counter=epoch_counter,
        valid_from=valid_from,
        valid_until=valid_until,
        issuer_key_id=issuer_key_id,
        signature=sig,
    )


def verify_epoch_issuance(
    ei: EpochIssuance,
    governor_pubkey_hex: str,
) -> tuple[bool, Optional[str]]:
    """Verify the Ed25519 signature on an EpochIssuance.

    Returns (ok, error_code). Error codes per REV3 §Deliverable 4:
      "IssuerMismatch"   — issuer_key_id != governor_pubkey_hex
      "SignatureInvalid" — Ed25519 verify failed
    """
    if ei.issuer_key_id != governor_pubkey_hex:
        return (False, "IssuerMismatch")
    try:
        ok = _ed25519_verify(ei.unsigned_payload(), ei.signature, governor_pubkey_hex)
    except Exception:
        return (False, "SignatureInvalid")
    return (ok, None if ok else "SignatureInvalid")


# ─────────────────────────────────────────────────────────────────────────────
# EpochRetirement artifact
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EpochRetirement:
    """Governor-signed declaration that epoch `retired_epoch` in phase
    `phase_id` is retired as of `retirement_time`.

    EpochRetirement is informational at M2.3e: it is structurally defined
    and verifiable, but no runtime enforcement consults it. Later subphases
    may add active retirement-aware verification.
    """
    phase_id:        str
    retired_epoch:   int
    retirement_time: int
    issuer_key_id:   str
    signature:       str

    def unsigned_payload(self) -> bytes:
        return _canonical_json_bytes({
            "phase_id":        self.phase_id,
            "retired_epoch":   self.retired_epoch,
            "retirement_time": self.retirement_time,
            "issuer_key_id":   self.issuer_key_id,
        })


def id_epoch_retirement(er: EpochRetirement) -> str:
    return hashlib.sha256(_canonical_json_bytes(asdict(er))).hexdigest()


def sign_epoch_retirement(
    *,
    phase_id:        str,
    retired_epoch:   int,
    retirement_time: int,
    issuer_key_id:   str,
    signer_privkey_hex: str,
) -> EpochRetirement:
    unsigned = _canonical_json_bytes({
        "phase_id":        phase_id,
        "retired_epoch":   retired_epoch,
        "retirement_time": retirement_time,
        "issuer_key_id":   issuer_key_id,
    })
    sig = _ed25519_sign(unsigned, signer_privkey_hex)
    return EpochRetirement(
        phase_id=phase_id,
        retired_epoch=retired_epoch,
        retirement_time=retirement_time,
        issuer_key_id=issuer_key_id,
        signature=sig,
    )


def verify_epoch_retirement(
    er: EpochRetirement,
    governor_pubkey_hex: str,
) -> tuple[bool, Optional[str]]:
    if er.issuer_key_id != governor_pubkey_hex:
        return (False, "IssuerMismatch")
    try:
        ok = _ed25519_verify(er.unsigned_payload(), er.signature, governor_pubkey_hex)
    except Exception:
        return (False, "SignatureInvalid")
    return (ok, None if ok else "SignatureInvalid")


# ─────────────────────────────────────────────────────────────────────────────
# FreshnessClaim — the dict that flows into H_c
# ─────────────────────────────────────────────────────────────────────────────
#
# Shape (M2.3e):
#   {
#     "phase_code":    id(Φ_0)              # hex
#     "epoch_counter": int
#     "valid_from":    int
#     "valid_until":   int
#     "window_sig":    Ed25519 signature    # hex (from EpochIssuance.signature)
#     "issuer_key_id": Governor pubkey      # hex
#   }
#
# The window_sig is exactly the EpochIssuance.signature. The verifier
# reconstructs the unsigned payload from (phase_code, epoch_counter,
# valid_from, valid_until, issuer_key_id) and verifies window_sig
# against the Governor pubkey.

def build_freshness_claim_from_epoch(ei: EpochIssuance) -> dict:
    """Construct a FreshnessClaim dict from a signed EpochIssuance.

    The resulting dict is the value that gets bound into H_c via c_c
    canonicalization. Determinism: same EpochIssuance → byte-identical
    canonical JSON → byte-identical H_c contribution.
    """
    return {
        "phase_code":    ei.phase_id,
        "epoch_counter": ei.epoch_counter,
        "valid_from":    ei.valid_from,
        "valid_until":   ei.valid_until,
        "window_sig":    ei.signature,
        "issuer_key_id": ei.issuer_key_id,
    }


def verify_freshness_claim(
    claim: dict,
    *,
    current_epoch: int,
    current_phase_id: str,
    governor_pubkey_hex: str,
) -> tuple[bool, Optional[str]]:
    """Full FreshnessClaim verification: structural boundary + Ed25519 signature.

    This is the M2.3e successor to binding_m2.freshness_check, which
    performed structural checks only (no signature verification).
    binding_m2.freshness_check is retained for EV-N05 backward compat.

    Returns (ok, error_code). Error codes:
      "PhaseMismatch"     — claim phase_code != current_phase_id
      "NotYetAdmissible"  — current_epoch < valid_from
      "ExpiredEdge"       — current_epoch > valid_until
      "IssuerMismatch"    — claim issuer_key_id != governor_pubkey_hex
      "SignatureInvalid"  — Ed25519 verify failed
    """
    # Structural boundary
    if claim["phase_code"] != current_phase_id:
        return (False, "PhaseMismatch")
    if current_epoch < claim["valid_from"]:
        return (False, "NotYetAdmissible")
    if current_epoch > claim["valid_until"]:
        return (False, "ExpiredEdge")

    # Signature
    if claim.get("issuer_key_id") != governor_pubkey_hex:
        return (False, "IssuerMismatch")

    unsigned = _canonical_json_bytes({
        "phase_id":      claim["phase_code"],
        "epoch_counter": claim["epoch_counter"],
        "valid_from":    claim["valid_from"],
        "valid_until":   claim["valid_until"],
        "issuer_key_id": claim["issuer_key_id"],
    })
    try:
        ok = _ed25519_verify(unsigned, claim["window_sig"], governor_pubkey_hex)
    except Exception:
        return (False, "SignatureInvalid")
    return (ok, None if ok else "SignatureInvalid")


# ─────────────────────────────────────────────────────────────────────────────
# Default test key + default epoch — for determinism across processes
# ─────────────────────────────────────────────────────────────────────────────
#
# Real production: Governor supplies the private key out-of-band and signs
# EpochIssuance artifacts via sign_epoch_issuance(...).
#
# In-process tests / 78-gate suite: receipts need a stable signed default
# FreshnessClaim so that H_c (and therefore H_r) values are byte-stable
# across runs. The default test keypair below is hardcoded (NOT generated
# at import time) precisely for this determinism property.
#
# The default test keypair is NOT a security boundary. It is a test fixture.

DEFAULT_TEST_PRIVKEY_HEX = "78bb6a76a7b369ce5e4e0d607c9add1f407f9a501e3985eddafe772b21e056e1"
DEFAULT_TEST_PUBKEY_HEX  = "eb4bba3338cd3e2f4483ed4311e1fa24f7b86f2a0070b5b695534e13b85bc040"

DEFAULT_TEST_KEY = (DEFAULT_TEST_PRIVKEY_HEX, DEFAULT_TEST_PUBKEY_HEX)


def default_epoch(phase_id: str) -> EpochIssuance:
    """Return a default test EpochIssuance for the given phase.

    Valid window is intentionally wide (0 → 2^63-1) so that the 78-gate
    suite passes regardless of any specific epoch value. Signed with the
    fixed DEFAULT_TEST_KEY for determinism.

    Real epochs are constructed via sign_epoch_issuance(...) with the
    actual Governor private key + narrower validity windows.
    """
    return sign_epoch_issuance(
        phase_id=phase_id,
        epoch_counter=0,
        valid_from=0,
        valid_until=(1 << 63) - 1,
        issuer_key_id=DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=DEFAULT_TEST_PRIVKEY_HEX,
    )


__all__ = [
    "EpochIssuance", "EpochRetirement",
    "id_epoch_issuance", "id_epoch_retirement",
    "sign_epoch_issuance", "sign_epoch_retirement",
    "verify_epoch_issuance", "verify_epoch_retirement",
    "build_freshness_claim_from_epoch", "verify_freshness_claim",
    "DEFAULT_TEST_PRIVKEY_HEX", "DEFAULT_TEST_PUBKEY_HEX",
    "DEFAULT_TEST_KEY", "default_epoch",
]
