"""ugk/authority_keys.py — Authority key registry (Roadmap W-05).

M2.3f replaces the M2.2-era authority-name-as-key proxy in H_j with a
real authority key identifier. Each authority has a deterministic
identifier derived from a domain-separated SHA-256 of its name. The
identifier slot is forward-compatible: when per-authority Ed25519
keypairs are introduced in a later subphase, the same H_j slot will
hold actual public-key references using the same canonical form
(64-char lowercase hex).

The directive (M2.3f) explicitly permits "real key identifier or public
key reference"; M2.3f delivers the key-identifier form. No Ed25519
derivation is performed here — the Governor key (used by EpochIssuance
and Policy signing) remains the only signing key in the system, per
R-14 ruling.

Public surface:
  derive_authority_key_id(name) — deterministic 64-hex identifier
  lookup_authority_key(name)    — name → key_id with cache
  register_authority_key(...)   — override the default (test/admin)
  clear_authority_key_cache()   — test surface
  AUTHORITY_KEY_ID_DS           — domain-separation prefix constant

Determinism: the derivation is pure SHA-256 with a fixed DS prefix, so
the key id for any given authority name is byte-stable across processes.
The cache exists for clarity and forward-compatibility (e.g., when real
keypairs replace the deterministic derivation), not for performance —
the hash itself is fast.
"""

from __future__ import annotations

import hashlib
from typing import Optional


# Domain-separation prefix for authority key identifier derivation.
# Distinct from any other domain-separation tag in UGK; ensures that
# hash collisions between this and other DS-tagged hashes are
# cryptographically improbable.
AUTHORITY_KEY_ID_DS: bytes = b"UGK-authority-key-id-v1"


_AUTHORITY_KEY_CACHE: dict[str, str] = {}


def derive_authority_key_id(authority_name: str) -> str:
    """Derive the deterministic key identifier for an authority name.

    Returns a 64-character lowercase hex string (SHA-256 output).
    Stable across processes; same input → same output.

    The identifier is computed as:
        SHA-256(AUTHORITY_KEY_ID_DS || authority_name.encode("utf-8"))

    This is a "key identifier" in the directive's sense — it identifies
    the key associated with an authority without itself being a usable
    Ed25519 public key. A later subphase may replace this with actual
    pubkey references; the slot shape (64-hex string) is preserved.
    """
    return hashlib.sha256(
        AUTHORITY_KEY_ID_DS + authority_name.encode("utf-8")
    ).hexdigest()


def lookup_authority_key(authority_name: str) -> str:
    """Return the key identifier for `authority_name`, cached per-process.

    Subsequent lookups for the same authority return the cached id.
    The cache permits register_authority_key(...) to override the default
    derivation (useful for tests and for future admin operations that
    rotate authority keys).
    """
    if authority_name not in _AUTHORITY_KEY_CACHE:
        _AUTHORITY_KEY_CACHE[authority_name] = derive_authority_key_id(authority_name)
    return _AUTHORITY_KEY_CACHE[authority_name]


def register_authority_key(authority_name: str, key_id: str) -> None:
    """Override the cached key identifier for `authority_name`.

    Future lookup_authority_key calls for this authority return `key_id`
    rather than the default-derived value. Useful for:
      - testing (e.g., EV-AK-01 demonstrates key rotation effects on H_j)
      - future admin operations (e.g., key rotation as a governance event)

    The provided key_id should be 64 lowercase-hex chars (an enforcement
    layer is not added here; this is a low-level surface).
    """
    _AUTHORITY_KEY_CACHE[authority_name] = key_id


def clear_authority_key_cache() -> None:
    """Reset the cache (test surface only)."""
    _AUTHORITY_KEY_CACHE.clear()


def get_registered_authority_key(authority_name: str) -> Optional[str]:
    """Return the cached value WITHOUT triggering default derivation.

    Returns None if the authority has not been looked up or registered.
    Useful for tests that need to distinguish "explicitly registered"
    from "never seen".
    """
    return _AUTHORITY_KEY_CACHE.get(authority_name)


__all__ = [
    "AUTHORITY_KEY_ID_DS",
    "derive_authority_key_id",
    "lookup_authority_key",
    "register_authority_key",
    "clear_authority_key_cache",
    "get_registered_authority_key",
]
