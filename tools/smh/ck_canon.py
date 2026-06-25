"""CK-I2 — CK-CANON-0.1 canonicalizer (CK-P2).

Maps the restricted CK value model (object, array, string, integer, boolean,
null) to unique canonical UTF-8 bytes, and computes the domain-separated
identity hash  H = SHA-256( domain_tag_ascii || 0x00 || canonical_bytes ).

Faithful to CK-P2:
  §2  UTF-8 no BOM; NFC; RFC 8785 (JCS) escaping (escape only " \\ and C0;
      short forms \\b \\t \\n \\f \\r; else \\u00xx lowercase; all other
      chars, incl. non-ASCII, literal UTF-8 — e.g. 'é' = C3 A9).
  §3  float ban (float_present); minimal-decimal integers;
      |value| > 2^53-1 as a JSON number -> oversized_integer_as_number.
  §4  object keys sorted as UTF-16 code-unit sequences (JCS); arrays keep order.
  §5  no insignificant whitespace.
  §6  lowercase true/false/null.
  §7  a top-level `ext` member is removed before canonicalization (excluded
      from identity).
  §9  domain-separated SHA-256; reference form domain_tag:hexdigest (64 hex).

Boundary (no silent semantics): this is the value-model -> bytes layer. The
SCHEMA-dependent failure classes (unknown_governance_field, missing_required_field,
null_for_non_nullable, ext_in_governance_region, bad_domain_tag) require schema /
profile / registry knowledge and are enforced by CK-I1 (validators) and the
ref/registry layer, NOT by this canonicalizer. The value-model failure classes
(float_present, oversized_integer_as_number, invalid_string_encoding) are here.

Pure, deterministic, read-only: never hydrates, executes, or mutates (§13).
This is the portable CK-CANON-0.1 rule — it does NOT depend on UGK's
`_canonical_json`.
"""

import hashlib
import unicodedata

_MAX_SAFE = (1 << 53) - 1  # 2^53 - 1


class CanonError(Exception):
    """A CK-CANON protocol failure (CK-R16): never a governance refusal."""
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


# ---- string escaping (RFC 8785 / JCS) --------------------------------------

_SHORT = {0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r"}


def _escape_string(s):
    try:
        s = unicodedata.normalize("NFC", s)
        s.encode("utf-8")  # validate encodability (lone surrogates raise)
    except (UnicodeError, ValueError):
        raise CanonError("invalid_string_encoding")
    out = ['"']
    for ch in s:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif cp in _SHORT:
            out.append(_SHORT[cp])
        elif cp <= 0x1F:
            out.append("\\u%04x" % cp)  # lowercase hex
        else:
            out.append(ch)  # literal, incl. non-ASCII -> UTF-8 bytes
    out.append('"')
    return "".join(out)


# ---- integer encoding ------------------------------------------------------

def _encode_integer(n):
    if abs(n) > _MAX_SAFE:
        raise CanonError("oversized_integer_as_number")
    return str(int(n))  # minimal decimal; no leading zeros; '-' only for neg; no -0


# ---- recursive serializer --------------------------------------------------

def _serialize(value):
    # bool MUST be checked before int (bool is a subclass of int in Python)
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, float):
        raise CanonError("float_present")
    if isinstance(value, int):
        return _encode_integer(value)
    if isinstance(value, dict):
        # keys sorted as UTF-16 code-unit sequences (JCS): utf-16-be byte order
        # equals code-unit order. (At the root, `ext` is stripped by canonical_bytes.)
        keys = sorted(value.keys(), key=lambda k: k.encode("utf-16-be"))
        members = []
        for k in keys:
            if not isinstance(k, str):
                raise CanonError("invalid_string_encoding")
            members.append(_escape_string(k) + ":" + _serialize(value[k]))
        return "{" + ",".join(members) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize(v) for v in value) + "]"
    # value model permits only object/array/string/integer/boolean/null
    raise CanonError("unsupported_type")  # impl guard beyond the JSON value model


def canonical_bytes(value):
    """Return the canonical UTF-8 bytes for the governance region of `value`.
    A top-level `ext` member is excluded from identity (§7)."""
    if isinstance(value, dict) and "ext" in value:
        value = {k: v for k, v in value.items() if k != "ext"}
    return _serialize(value).encode("utf-8")


# ---- hashing (§9) ----------------------------------------------------------

def domain_hash(domain_tag, value):
    """H = SHA-256( domain_tag_ascii || 0x00 || canonical_bytes ) -> 64-hex."""
    try:
        tag = domain_tag.encode("ascii")
    except (UnicodeError, AttributeError):
        raise CanonError("bad_domain_tag")
    cb = canonical_bytes(value)
    return hashlib.sha256(tag + b"\x00" + cb).hexdigest()


def ref_form(domain_tag, value):
    """Reference form domain_tag:hexdigest (§9.3)."""
    return "%s:%s" % (domain_tag, domain_hash(domain_tag, value))
