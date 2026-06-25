"""ugk/policy.py — Policy artifact infrastructure (REV3 §Deliverable 1 / Roadmap W-06).

M2.3g replaces the M2.2-era `jurisdiction` string proxy with real governed
Policy artifacts. Each Policy is signed by the Governor (same key as
EpochIssuance per R-14 ruling). id(P) becomes the cryptographic identity
that flows into H_c via policy_id, and into the id_P strict-mode leaf.

Public surface:
  Policy                  — dataclass (subjects, decision_rules, version,
                            issuer_key_id, signature)
  id_policy()             — SHA-256(canonical_json(full Policy))
  sign_policy()           — construct and sign a Policy with a private key
  verify_policy()         — Ed25519 signature verification
  lookup_policy()         — jurisdiction → Policy (with deterministic cache)
  default_policy_for()    — build the default signed Policy for a jurisdiction

Determinism: signed policies are cached by jurisdiction within a process,
and the signing inputs are deterministic (same fixed test key, same
canonical subjects/rules), so id(P) for any given jurisdiction is byte-
stable across processes. This preserves the 78-gate suite's hash stability.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Optional, Iterable

from ugk.vendor.ed25519 import sign as _ed25519_sign, verify as _ed25519_verify
# Reuse the test Governor key from freshness.py per R-14 ruling
# (single Governor key; no separate policy-authority key)
from ugk.freshness import (
    DEFAULT_TEST_PRIVKEY_HEX as _DEFAULT_PRIV,
    DEFAULT_TEST_PUBKEY_HEX as _DEFAULT_PUB,
)


# ─────────────────────────────────────────────────────────────────────────────
# Canonicalization helper (mirrors freshness._canonical_json_bytes)
# ─────────────────────────────────────────────────────────────────────────────

def _canonical_json_bytes(obj) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Policy artifact
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Policy:
    """Governor-signed policy artifact.

    Fields per Governor directive (M2.3g):
      subjects       — ordered tuple of subject identifiers this policy
                       applies to (e.g. jurisdictions, op categories)
      decision_rules — ordered tuple of rule identifiers; opaque at this
                       subphase (real decision-procedure machinery is M2.3l)
      version        — semantic version string (e.g. "v1", "v2")
      issuer_key_id  — "signer" field: Governor's Ed25519 public key hex
      signature      — Ed25519 signature hex (128 chars) over the unsigned
                       payload

    The signature covers canonical_json({subjects, decision_rules, version,
    issuer_key_id}); it does NOT cover the signature field itself.
    """
    subjects:       tuple
    decision_rules: tuple
    version:        str
    issuer_key_id:  str
    signature:      str

    def unsigned_payload(self) -> bytes:
        """Canonical bytes that get signed (excludes the signature field)."""
        return _canonical_json_bytes({
            "subjects":       list(self.subjects),
            "decision_rules": list(self.decision_rules),
            "version":        self.version,
            "issuer_key_id":  self.issuer_key_id,
        })

    def to_canonical_dict(self) -> dict:
        """Full canonical dict (including signature) used for id(P)."""
        return {
            "subjects":       list(self.subjects),
            "decision_rules": list(self.decision_rules),
            "version":        self.version,
            "issuer_key_id":  self.issuer_key_id,
            "signature":      self.signature,
        }


def id_policy(p: Policy) -> str:
    """id(P) := SHA-256(canonical_json(full Policy artifact))."""
    return hashlib.sha256(_canonical_json_bytes(p.to_canonical_dict())).hexdigest()


def sign_policy(
    *,
    subjects:       Iterable[str],
    decision_rules: Iterable[str],
    version:        str,
    issuer_key_id:  str,
    signer_privkey_hex: str,
) -> Policy:
    """Construct and sign a Policy with the given Ed25519 private key."""
    sbj = tuple(subjects)
    rls = tuple(decision_rules)
    unsigned = _canonical_json_bytes({
        "subjects":       list(sbj),
        "decision_rules": list(rls),
        "version":        version,
        "issuer_key_id":  issuer_key_id,
    })
    sig = _ed25519_sign(unsigned, signer_privkey_hex)
    return Policy(
        subjects=sbj,
        decision_rules=rls,
        version=version,
        issuer_key_id=issuer_key_id,
        signature=sig,
    )


def verify_policy(
    p: Policy,
    governor_pubkey_hex: str,
) -> tuple[bool, Optional[str]]:
    """Verify the Ed25519 signature on a Policy.

    Returns (ok, error_code). Reuses M2.3e error codes:
      "IssuerMismatch"   — issuer_key_id != governor_pubkey_hex
      "SignatureInvalid" — Ed25519 verify failed
    """
    if p.issuer_key_id != governor_pubkey_hex:
        return (False, "IssuerMismatch")
    try:
        ok = _ed25519_verify(p.unsigned_payload(), p.signature, governor_pubkey_hex)
    except Exception:
        return (False, "SignatureInvalid")
    return (ok, None if ok else "SignatureInvalid")


# ─────────────────────────────────────────────────────────────────────────────
# Per-jurisdiction lookup with deterministic caching
# ─────────────────────────────────────────────────────────────────────────────
#
# Receipt construction in store.write() calls lookup_policy(jurisdiction) to
# obtain a real Policy for the receipt's jurisdiction. The lookup caches
# signed policies by jurisdiction within the process, so signing cost is
# amortized to one Ed25519 sign per distinct jurisdiction string.
#
# The cache is process-local. Across processes, the same jurisdiction
# produces the same Policy (same fixed test key, same canonical fields,
# same signature) — determinism preserved.

_POLICY_CACHE: dict[str, Policy] = {}


def default_policy_for(jurisdiction: str) -> Policy:
    """Build (and sign) the canonical default Policy for `jurisdiction`.

    The jurisdiction string is folded into `subjects` so that distinct
    jurisdictions produce structurally distinct Policy artifacts → distinct
    id(P) values. `decision_rules` is the stub ("default-allow") until
    M2.3l introduces real decision procedures.
    """
    return sign_policy(
        subjects=(f"jurisdiction:{jurisdiction}",),
        decision_rules=("default-allow",),
        version="v1",
        issuer_key_id=_DEFAULT_PUB,
        signer_privkey_hex=_DEFAULT_PRIV,
    )


def lookup_policy(jurisdiction: str) -> Policy:
    """Return the Policy for `jurisdiction`, signing it on first lookup.

    Subsequent lookups for the same jurisdiction return the cached Policy.
    Cache is process-local but byte-deterministic across processes.
    """
    if jurisdiction not in _POLICY_CACHE:
        _POLICY_CACHE[jurisdiction] = default_policy_for(jurisdiction)
    return _POLICY_CACHE[jurisdiction]


def lookup_policy_id(jurisdiction: str) -> str:
    """Convenience: return id(P) hex for `jurisdiction` (uses lookup_policy)."""
    return id_policy(lookup_policy(jurisdiction))


def register_policy(jurisdiction: str, policy: Policy) -> None:
    """Override the cached policy for `jurisdiction` (test/admin use).

    The registered policy is used by subsequent lookup_policy calls in
    the same process. Useful for tests that need to demonstrate
    policy-version changes.
    """
    _POLICY_CACHE[jurisdiction] = policy


def clear_policy_cache() -> None:
    """Reset the policy cache (test use only)."""
    _POLICY_CACHE.clear()


__all__ = [
    "Policy",
    "id_policy", "sign_policy", "verify_policy",
    "lookup_policy", "lookup_policy_id",
    "default_policy_for", "register_policy", "clear_policy_cache",
]
