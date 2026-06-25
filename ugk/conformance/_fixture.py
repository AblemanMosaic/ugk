"""ugk/conformance/_fixture.py — shared dev-fixture + posture helpers for gates.

Not a gate. The dev fixture keypair is deliberately public ("Coder-seen, not
production-secret"); its pubkey is derived, never hardcoded twice.

IMPORTANT: no ugk.kernel import at module level — kernel identity loads at
import time, and the batch runner's ephemeral founding must run first.
"""

DEV_FIXTURE_PRIVKEY = "cb181d9a650b7605b94602d0d6a2640a38fa1a0f1086c4896f98e40c21766857"

_SENTINEL_PREFIX = "GOVERNOR_KEY_UNSET"


def unfounded() -> bool:
    """True when the installed governor identity is the unset sentinel."""
    from ugk.kernel import GOVERNOR_PUBKEY_HEX  # lazy — see module docstring
    return str(GOVERNOR_PUBKEY_HEX).startswith(_SENTINEL_PREFIX)


def fixture_pubkey() -> str:
    """Derive the dev fixture's public key from its private key (Ed25519)."""
    import ugk.vendor.ed25519 as e
    h = e._sha512(bytes.fromhex(DEV_FIXTURE_PRIVKEY))
    a = e._clamp(bytearray(h[:32]))
    return e._compress(e._point_mul(a, e._G)).hex()
