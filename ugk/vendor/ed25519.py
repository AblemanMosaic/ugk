"""ugk/vendor/ed25519.py — Pure-Python Ed25519 (RFC 8032). Vendored. Zero external deps.

Implements Ed25519 sign and verify using only Python stdlib (hashlib, os).
Based on the IETF RFC 8032 reference arithmetic over the Edwards25519 curve.

Public API:
    generate_keypair()                           -> (privkey_hex, pubkey_hex)
    sign(message: bytes, privkey_hex: str)       -> signature_hex
    verify(message: bytes, sig_hex, pubkey_hex)  -> bool

All key material is represented as lowercase hex strings:
    privkey_hex — 64 hex chars (32-byte seed)
    pubkey_hex  — 64 hex chars (32-byte compressed Ed25519 point)
    sig_hex     — 128 hex chars (64-byte signature = R ‖ S)

UL-S-01 compliance: no pip-installed package. Pure stdlib arithmetic only.
CM-DEP-01: selection = "stdlib_plus_vendored" (admissible).

Security note: This is a reference implementation for governance identity
purposes. It is correct per RFC 8032 but is NOT constant-time — not hardened
against timing side-channels. Suitable for governance sealing and verification
where the secret key is not under adversarial observation during signing.
For Phase 3+ production hardening, replace with a constant-time implementation.
"""
from __future__ import annotations

import hashlib
import os

# ---------------------------------------------------------------------------
# Field parameters (Ed25519 / Curve25519)
# ---------------------------------------------------------------------------

# Prime field modulus
_P = 2**255 - 19
# Group order
_L = 2**252 + 27742317777372353535851937790883648493
# Curve constant d = -121665 / 121666 mod P
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
# sqrt(-1) mod P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)
# Base point y-coordinate
_G_Y = 4 * pow(5, _P - 2, _P) % _P


def _sha512(b: bytes) -> bytes:
    return hashlib.sha512(b).digest()


def _recover_x(y: int, sign: int):
    """Recover x from y coordinate and sign bit. Returns None on failure."""
    if y >= _P:
        return None
    y2 = y * y % _P
    x2 = (y2 - 1) * pow(_D * y2 + 1, _P - 2, _P) % _P
    if x2 == 0:
        return 0 if sign == 0 else None
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if x & 1 != sign:
        x = _P - x
    return x


# Base point in extended coordinates (X, Y, Z, T)
_G_X = _recover_x(_G_Y, 0)
_G = (_G_X, _G_Y, 1, _G_X * _G_Y % _P)

# Neutral element
_NEUTRAL = (0, 1, 1, 0)


def _point_add(P, Q):
    """Extended twisted Edwards addition."""
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = (y1 - x1) * (y2 - x2) % _P
    b = (y1 + x1) * (y2 + x2) % _P
    c = t1 * 2 * _D * t2 % _P
    d = z1 * 2 * z2 % _P
    e, f, g, h = (b - a) % _P, (d - c) % _P, (d + c) % _P, (b + a) % _P
    return e * f % _P, g * h % _P, f * g % _P, e * h % _P


def _point_mul(s: int, P) -> tuple:
    """Scalar multiplication via double-and-add."""
    Q = _NEUTRAL
    while s > 0:
        if s & 1:
            Q = _point_add(Q, P)
        P = _point_add(P, P)
        s >>= 1
    return Q


def _compress(P) -> bytes:
    """Compress a point to 32 bytes."""
    x, y, z, _ = P
    zi = pow(z, _P - 2, _P)
    x, y = x * zi % _P, y * zi % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decompress(b: bytes):
    """Decompress 32 bytes to extended-coordinate point. Raises ValueError."""
    if len(b) != 32:
        raise ValueError("Ed25519: compressed point must be 32 bytes")
    y_raw = int.from_bytes(b, "little")
    sign = y_raw >> 255
    y = y_raw & ~(1 << 255)
    x = _recover_x(y, sign)
    if x is None:
        raise ValueError("Ed25519: invalid compressed point")
    return x, y, 1, x * y % _P


def _clamp(h32: bytearray) -> int:
    """Apply Ed25519 scalar clamping."""
    h32[0] &= 248
    h32[31] &= 127
    h32[31] |= 64
    return int.from_bytes(h32, "little")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_keypair() -> tuple[str, str]:
    """Generate a fresh Ed25519 keypair.

    Returns (privkey_hex, pubkey_hex) where:
        privkey_hex — 64-char hex of 32-byte random seed
        pubkey_hex  — 64-char hex of compressed public key point
    """
    seed = os.urandom(32)
    h = _sha512(seed)
    a = _clamp(bytearray(h[:32]))
    A = _compress(_point_mul(a, _G))
    return seed.hex(), A.hex()


def sign(message: bytes, privkey_hex: str) -> str:
    """Sign message with Ed25519 private key seed.

    Returns 128-char lowercase hex signature (64 bytes = R ‖ S).
    """
    seed = bytes.fromhex(privkey_hex)
    h = _sha512(seed)
    a = _clamp(bytearray(h[:32]))
    prefix = bytes(h[32:])
    A = _compress(_point_mul(a, _G))

    r = int.from_bytes(_sha512(prefix + message), "little") % _L
    R_bytes = _compress(_point_mul(r, _G))

    h_val = int.from_bytes(_sha512(R_bytes + A + message), "little") % _L
    s = (r + h_val * a) % _L

    return (R_bytes + s.to_bytes(32, "little")).hex()


def verify(message: bytes, sig_hex: str, pubkey_hex: str) -> bool:
    """Verify an Ed25519 signature.

    Returns True if the signature is valid for (message, pubkey). Never raises.
    """
    try:
        sig = bytes.fromhex(sig_hex)
        pubkey = bytes.fromhex(pubkey_hex)
        if len(sig) != 64 or len(pubkey) != 32:
            return False
        R_bytes, s_bytes = sig[:32], sig[32:]
        s = int.from_bytes(s_bytes, "little")
        if s >= _L:
            return False
        R = _decompress(R_bytes)
        A = _decompress(pubkey)
        h = int.from_bytes(
            _sha512(R_bytes + pubkey + message), "little"
        ) % _L
        # Check: s·G == R + h·A
        sG = _point_mul(s, _G)
        hA = _point_mul(h, A)
        return _compress(sG) == _compress(_point_add(R, hA))
    except Exception:
        return False


__all__ = ["generate_keypair", "sign", "verify"]
