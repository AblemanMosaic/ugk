"""ugk/csh.py — Constitutional Semantic Hashing (CSH) finality layer (Grundnorm 444).

CSH is the 4th element of the 3+1 hash scheme per the UGK roadmap:
  +1  state_hash      — H(op ‖ inputs)
  CHC semantic_hash   — dm_s03 multidimensional binding
  DKN dimension_id    — canonical_dkn(phase_code ‖ governor_pubkey)
  CSH finality_hash   — MCIR hyperedge: quorum of MosaicID attestations

Phase 3 delivers N=1 quorum finality (single Governor with dev_temp key).
The protocol is correct for N≥1; rotation to N>1 uses the pre-declared
RotationRule without structural changes to this module.

Glossary:
  Attestation       — MosaicID-signed claim: "I attest law_hash is the active
                       constitutional framework under phase_code P."
  ValidatorSet      — sealed set of validator MosaicIDs (Governor-sealed)
  InceptionCertificate (IC) — founding governance certificate: "I found this
                       kernel under phase_code P with law_hash H, N validators,
                       sunset declared."
  RotationRule      — pre-declared A→B→C succession protocol
  MCIR              — Multi-Constellation Identity Relay hyperedge: the
                       finality artifact produced when quorum is achieved.
                       finality_hash = SHA-256(sorted attestation signatures).
  Equivocation      — a validator MosaicID that signs two different law_hashes
                       for the same epoch → constitutionally excluded.

Quorum rule: for N validators, quorum requires ceil((2N+1)/3) valid attestations
(BFT-style honest majority). For N=1: quorum = 1.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

from ugk.storage.binding import canonical_json, mosaic_id as _mosaic_id, dm_s03


# ---------------------------------------------------------------------------
# Attestation — MosaicID-signed constitutional attestation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Attestation:
    """A validator's MosaicID-signed attestation of the active constitutional hash.

    Fields bound in the Ed25519 signature:
      mosaic_root, constitutional_hash, phase_code, epoch, timestamp
    (canonical_json of the above, sorted keys)
    """
    mosaic_root:         str   # SHA-256(validator_pubkey) — attestor identity
    constitutional_hash: str   # law_hash being attested
    phase_code:          str
    epoch:               int   # monotonically increasing epoch counter
    timestamp:           str   # ISO-8601 UTC
    signature:           str   # Ed25519 sig (128-char hex) over sig_payload()
    pubkey_hex:          str   # attesting validator's Ed25519 pubkey (for verify)

    def sig_payload(self) -> bytes:
        """Canonical bytes that were signed (reproducible without privkey)."""
        body = {
            "constitutional_hash": self.constitutional_hash,
            "epoch":               self.epoch,
            "mosaic_root":         self.mosaic_root,
            "phase_code":          self.phase_code,
            "timestamp":           self.timestamp,
        }
        return canonical_json(body)

    def verify(self) -> bool:
        """Verify the Ed25519 signature over the attestation payload."""
        from ugk.vendor.ed25519 import verify as _verify
        return _verify(self.sig_payload(), self.signature, self.pubkey_hex)


def create_attestation(
    privkey_hex:         str,
    pubkey_hex:          str,
    constitutional_hash: str,
    phase_code:          str,
    epoch:               int = 0,
    timestamp:           str = "2026-06-09T08:30:00Z",
) -> Attestation:
    """Create and sign a constitutional attestation.

    Called by the Governor (or a validator) to attest that
    constitutional_hash is the active framework under phase_code.
    """
    from ugk.vendor.ed25519 import sign as _sign
    mosaic = _mosaic_id(pubkey_hex)
    body = {
        "constitutional_hash": constitutional_hash,
        "epoch":               epoch,
        "mosaic_root":         mosaic,
        "phase_code":          phase_code,
        "timestamp":           timestamp,
    }
    payload = canonical_json(body)
    sig = _sign(payload, privkey_hex)
    return Attestation(
        mosaic_root=mosaic,
        constitutional_hash=constitutional_hash,
        phase_code=phase_code,
        epoch=epoch,
        timestamp=timestamp,
        signature=sig,
        pubkey_hex=pubkey_hex,
    )


# ---------------------------------------------------------------------------
# ValidatorSet — Governor-sealed set of validator identities
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidatorSet:
    """Governor-sealed set of validator MosaicIDs.

    N=1 for Phase 3 (single Governor).  Rotation to N>1 is handled by
    issuing a new ValidatorSet sealed by the current Governor IC holder.

    sealed_hash = SHA-256(canonical_json(sorted(validators))) — content-addresses
    the validator set.  If the set is tampered, sealed_hash diverges.
    """
    validators:       tuple         # sorted tuple of MosaicID hex strings
    n_validators:     int
    sealed_by:        str           # MosaicID of the sealing Governor
    sealed_hash:      str           # SHA-256(canonical_json(sorted validators))
    seal_signature:   str           # Ed25519 sig over seal_payload()
    sealer_pubkey:    str           # Governor's Ed25519 pubkey

    def seal_payload(self) -> bytes:
        """Canonical bytes of the validator set declaration."""
        body = {
            "n_validators": self.n_validators,
            "sealed_by":    self.sealed_by,
            "validators":   list(self.validators),
        }
        return canonical_json(body)

    def verify_seal(self) -> bool:
        """Verify the Governor's seal signature."""
        from ugk.vendor.ed25519 import verify as _verify
        return _verify(self.seal_payload(), self.seal_signature, self.sealer_pubkey)

    def contains(self, mosaic_root: str) -> bool:
        """True if mosaic_root is in the sealed validator set."""
        return mosaic_root in self.validators

    @staticmethod
    def compute_sealed_hash(validators: list[str]) -> str:
        payload = canonical_json({"validators": sorted(validators)})
        return hashlib.sha256(payload).hexdigest()


def seal_validator_set(
    privkey_hex: str,
    pubkey_hex:  str,
    validators:  list[str],   # list of MosaicID hex strings
) -> ValidatorSet:
    """Create and seal a ValidatorSet with the Governor's private key."""
    from ugk.vendor.ed25519 import sign as _sign
    mosaic = _mosaic_id(pubkey_hex)
    sorted_v = sorted(validators)
    n = len(sorted_v)
    sealed_hash = ValidatorSet.compute_sealed_hash(sorted_v)
    body = {
        "n_validators": n,
        "sealed_by":    mosaic,
        "validators":   sorted_v,
    }
    payload = canonical_json(body)
    sig = _sign(payload, privkey_hex)
    return ValidatorSet(
        validators=tuple(sorted_v),
        n_validators=n,
        sealed_by=mosaic,
        sealed_hash=sealed_hash,
        seal_signature=sig,
        sealer_pubkey=pubkey_hex,
    )


# ---------------------------------------------------------------------------
# InceptionCertificate (IC) — founding governance certificate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InceptionCertificate:
    """Founding governance certificate (Launch IC).

    Declares: "I found this governance kernel under phase_code P with
    constitutional hash H, N validators, sunset declared."

    trusted-genesis type: N=1, Governor-held (dev_temp in Phase 3),
    sunset declared (this IC is replaced at full Governor ceremony).
    """
    ic_type:             str   # "trusted-genesis"
    phase_code:          str
    constitutional_hash: str   # law_hash at founding
    mosaic_root:         str   # founding Governor MosaicID
    dimension_id:        str   # canonical_dkn(phase_code, pubkey)
    n_validators:        int
    validator_set_hash:  str   # ValidatorSet.sealed_hash
    sunset_declared:     bool  # True = this IC is superseded at full ceremony
    timestamp:           str
    signature:           str   # Governor Ed25519 sig over ic_payload()
    governor_pubkey:     str

    def ic_payload(self) -> bytes:
        """Canonical bytes of the IC declaration (reproducible)."""
        body = {
            "constitutional_hash": self.constitutional_hash,
            "dimension_id":        self.dimension_id,
            "ic_type":             self.ic_type,
            "mosaic_root":         self.mosaic_root,
            "n_validators":        self.n_validators,
            "phase_code":          self.phase_code,
            "sunset_declared":     self.sunset_declared,
            "timestamp":           self.timestamp,
            "validator_set_hash":  self.validator_set_hash,
        }
        return canonical_json(body)

    def verify(self) -> bool:
        """Verify the Governor's signature on the IC."""
        from ugk.vendor.ed25519 import verify as _verify
        return _verify(self.ic_payload(), self.signature, self.governor_pubkey)

    def ic_hash(self) -> str:
        """Content-address the IC for reference in kernel state."""
        return hashlib.sha256(self.ic_payload()).hexdigest()


def create_launch_ic(
    privkey_hex:         str,
    pubkey_hex:          str,
    constitutional_hash: str,
    dimension_id:        str,
    phase_code:          str,
    validator_set_hash:  str,
    n_validators:        int = 1,
    timestamp:           str = "2026-06-09T08:30:00Z",
) -> InceptionCertificate:
    """Mint and sign the Launch IC (trusted-genesis type)."""
    from ugk.vendor.ed25519 import sign as _sign
    mosaic = _mosaic_id(pubkey_hex)
    ic = InceptionCertificate(
        ic_type="trusted-genesis",
        phase_code=phase_code,
        constitutional_hash=constitutional_hash,
        mosaic_root=mosaic,
        dimension_id=dimension_id,
        n_validators=n_validators,
        validator_set_hash=validator_set_hash,
        sunset_declared=True,   # dev_temp: superseded at full ceremony
        timestamp=timestamp,
        signature="",           # filled below
        governor_pubkey=pubkey_hex,
    )
    # Sign the payload using a temp IC (signature field omitted from payload body)
    payload = ic.ic_payload()
    sig = _sign(payload, privkey_hex)
    # Return immutable frozen dataclass with signature filled
    return InceptionCertificate(
        ic_type=ic.ic_type, phase_code=ic.phase_code,
        constitutional_hash=ic.constitutional_hash,
        mosaic_root=ic.mosaic_root, dimension_id=ic.dimension_id,
        n_validators=ic.n_validators, validator_set_hash=ic.validator_set_hash,
        sunset_declared=ic.sunset_declared, timestamp=ic.timestamp,
        signature=sig, governor_pubkey=ic.governor_pubkey,
    )


# ---------------------------------------------------------------------------
# RotationRule — pre-declared validator rotation protocol
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RotationRule:
    """Pre-declared A→B→C rotation protocol.

    In Phase 3 (N=1), this is pre-declared but not exercised.
    Rotation is triggered by a new IC signed by the current IC-holder's key.

    rule_type:
      "single_successor" — A → B (one-step designation)
      "chain"            — A → B → C (pre-chained)
      "quorum_vote"      — N of M validators vote on successor (Phase 4+)
    """
    rule_type:        str
    current_holder:   str   # MosaicID of current IC holder
    successors:       tuple  # ordered MosaicIDs of pre-declared successors
    governed_by_ic:   str   # ic_hash of the IC that declares this rule
    declared_at:      str   # timestamp


def declare_rotation_rule(
    current_holder: str,
    successors:     list[str],
    ic_hash:        str,
    timestamp:      str = "2026-06-09T08:30:00Z",
) -> RotationRule:
    """Declare a pre-authorized rotation rule (Phase 3: chain type, N=1 holder)."""
    rule_type = "chain" if len(successors) > 1 else "single_successor"
    return RotationRule(
        rule_type=rule_type,
        current_holder=current_holder,
        successors=tuple(successors),
        governed_by_ic=ic_hash,
        declared_at=timestamp,
    )


# ---------------------------------------------------------------------------
# Equivocation detection
# ---------------------------------------------------------------------------

def detect_equivocation(attestations: list[Attestation]) -> list[str]:
    """Return MosaicIDs that signed two different constitutional_hashes in same epoch.

    Equivocation = signing conflicting attestations.  In the BFT model,
    an equivocating validator is constitutionally excluded from future quorums.
    """
    by_validator: dict[tuple, set] = {}
    for a in attestations:
        key = (a.mosaic_root, a.epoch)
        by_validator.setdefault(key, set()).add(a.constitutional_hash)

    equivocators = []
    for (mosaic_root, epoch), hashes in by_validator.items():
        if len(hashes) > 1:
            equivocators.append(mosaic_root)
    return sorted(set(equivocators))


# ---------------------------------------------------------------------------
# MCIR — Multi-Constellation Identity Relay hyperedge (finality artifact)
# ---------------------------------------------------------------------------

def _quorum_threshold(n_validators: int) -> int:
    """BFT quorum: ceil((2N+1)/3). For N=1: 1."""
    return max(1, (2 * n_validators + 1 + 2) // 3)


@dataclass
class MCIR:
    """MCIR hyperedge — finality artifact produced when quorum is achieved.

    finality_hash = SHA-256(canonical_json(sorted attestation signatures))
    quorum_achieved = True iff valid attestation count >= quorum threshold

    This is the CSH output: the proof that N-of-M validators agree on the
    active constitutional framework.
    """
    constitutional_hash: str
    valid_attestations:  list[Attestation]
    invalid_attestations: list[Attestation]
    equivocators:        list[str]
    quorum_threshold:    int
    quorum_achieved:     bool
    finality_hash:       str   # SHA-256 of sorted valid sig bytes; "" if not achieved


def achieve_finality(
    attestations:  list[Attestation],
    validator_set: ValidatorSet,
    constitutional_hash: str,
) -> MCIR:
    """Evaluate attestations against the validator set and produce an MCIR.

    Steps:
      1. Filter: only attestations from sealed validators
      2. Verify: only cryptographically valid attestations
      3. Check constitutional_hash consistency
      4. Detect equivocation
      5. Count valid unique validators
      6. Compare to quorum threshold
      7. Compute finality_hash iff quorum achieved
    """
    equivocators = detect_equivocation(attestations)

    valid: list[Attestation] = []
    invalid: list[Attestation] = []

    seen_validators: set[str] = set()

    for a in attestations:
        # Exclude equivocators
        if a.mosaic_root in equivocators:
            invalid.append(a)
            continue
        # Must be in sealed validator set
        if not validator_set.contains(a.mosaic_root):
            invalid.append(a)
            continue
        # Must attest the correct hash
        if a.constitutional_hash != constitutional_hash:
            invalid.append(a)
            continue
        # Signature must verify
        if not a.verify():
            invalid.append(a)
            continue
        # One attestation per validator per finality check
        if a.mosaic_root in seen_validators:
            continue
        seen_validators.add(a.mosaic_root)
        valid.append(a)

    threshold = _quorum_threshold(validator_set.n_validators)
    quorum_ok = len(valid) >= threshold

    if quorum_ok:
        # finality_hash = SHA-256(canonical_json of sorted signatures)
        sigs = sorted(a.signature for a in valid)
        finality_hash = hashlib.sha256(
            canonical_json({"signatures": sigs})
        ).hexdigest()
    else:
        finality_hash = ""

    return MCIR(
        constitutional_hash=constitutional_hash,
        valid_attestations=valid,
        invalid_attestations=invalid,
        equivocators=equivocators,
        quorum_threshold=threshold,
        quorum_achieved=quorum_ok,
        finality_hash=finality_hash,
    )


__all__ = [
    "Attestation", "create_attestation",
    "ValidatorSet", "seal_validator_set",
    "InceptionCertificate", "create_launch_ic",
    "RotationRule", "declare_rotation_rule",
    "MCIR", "achieve_finality",
    "detect_equivocation",
]
