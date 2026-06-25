"""ugk/storage/bridge_binding.py — BRIDGE-BINDING verification semantics (CK-BRIDGE Stage 3, law leg).

Pure, resolver-parameterized verifier for the committed UGK-BODY-v8 bridge surface. Binds the
VALIDITY of a present bridge surface; does NOT activate native BRIDGE emission (that is Stage 4 —
the terminal-outcome correspondence BRIDGE <=> valid BridgeRecord is inert here because BRIDGE is
non-emittable). Kernel-free and deterministic: the verdict is a pure function of receipt-local
bridge fields plus injected READ-ONLY resolver results. UGK imports neither MCIR nor SMH; the
verification context supplies resolvers (MCIR-I3 / SMH-I3 read-only verifiers). SMH resolution is
read-only ref-resolution, never authority; MCIR is representation, never authority.

verify_bridge_binding(fields, *, mcir_identity_resolver, mcir_divergence_resolver,
                      mcir_transformation_resolver, smh_evidence_resolver) -> (valid: bool, reason: str)

`fields` is a mapping with the six committed bridge keys (None throughout == no surface). Resolvers
are read-only callables; a resolver returning falsey REFUTES (fail-closed). A resolver itself raising
also REFUTES (fail-closed); the verifier never lets a resolver exception escape as validity.
"""
from ugk.storage.store import BRIDGE_DOWNGRADE_TAXONOMY

# Field keys (mirror the committed v8 columns; single source of truth is store's surface).
_ID = "bridge_record_id"
_SRC = "bridge_source_regime_ref"
_TGT = "bridge_target_regime_ref"
_XFORM = "bridge_transformation_ref"
_REASON = "bridge_downgrade_reason"
_EVIDENCE = "bridge_preserved_evidence_ref"
_ALL = (_ID, _SRC, _TGT, _XFORM, _REASON, _EVIDENCE)


def has_bridge_surface(fields) -> bool:
    """True iff any committed bridge field is present (non-None)."""
    return any(fields.get(k) is not None for k in _ALL)


def _safe(resolver, *args) -> bool:
    """Fail-closed resolver call: any exception or falsey result -> False (refute)."""
    try:
        return bool(resolver(*args))
    except Exception:
        return False


def verify_bridge_binding(fields, *, mcir_identity_resolver, mcir_divergence_resolver,
                          mcir_transformation_resolver, smh_evidence_resolver):
    """Deterministic BRIDGE-BINDING verdict over a (possibly absent) committed bridge surface.

    Receipt-LOCAL (no external import, deterministic from committed state):
      - surface absent -> VALID (N/A; ordinary receipt).
      - surface present -> all six fields well-formed (non-empty strings); id present;
        source != target (distinct); downgrade_reason in the closed taxonomy; required refs present.
    Resolver-DELEGATED (read-only, kernel-free; injected by the verification context):
      - identity:       committed id == mcir_identity_resolver(source, target, transformation, reason, evidence)
      - divergence:     mcir_divergence_resolver(source, target) is truthy (structural divergence under MCIR)
      - transformation: mcir_transformation_resolver(transformation) is truthy (valid MCIR transformation artifact)
      - evidence:       smh_evidence_resolver(evidence) is truthy (resolves under SMH read-only)
    Returns (valid, reason). Fail-closed throughout.
    """
    # (0) absent surface -> not constrained.
    if not has_bridge_surface(fields):
        return True, "no bridge surface present (N/A)"

    # (1) all six fields present + non-empty (a partial surface is malformed -> refuted).
    for k in _ALL:
        v = fields.get(k)
        if not (isinstance(v, str) and v != ""):
            return False, f"bridge surface field {k} missing/empty (malformed) -> REFUTED"

    src, tgt = fields[_SRC], fields[_TGT]
    xform, reason, ev = fields[_XFORM], fields[_REASON], fields[_EVIDENCE]

    # (2) closed downgrade taxonomy.
    if reason not in BRIDGE_DOWNGRADE_TAXONOMY:
        return False, f"downgrade_reason {reason!r} outside closed taxonomy -> REFUTED"

    # (3) required refs present (defensive; covered by (1)).
    if not (src and tgt and xform and ev):
        return False, "a required bridge ref is empty -> REFUTED"

    # (4) source/target DISTINCT (receipt-local).
    if src == tgt:
        return False, "source and target regime refs identical (not a crossing) -> REFUTED"

    # (5) MCIR identity: committed id must equal the resolver-derived identity (deterministic).
    try:
        expected = mcir_identity_resolver(src, tgt, xform, reason, ev)
    except Exception:
        return False, "identity resolver failed -> REFUTED"
    if not (isinstance(expected, str) and expected and expected == fields[_ID]):
        return False, "committed bridge_record_id does not match MCIR-derived identity -> REFUTED"

    # (6) MCIR structural divergence of source vs target.
    if not _safe(mcir_divergence_resolver, src, tgt):
        return False, "source/target do not structurally diverge under MCIR -> REFUTED"

    # (7) transformation resolves as a valid MCIR transformation artifact.
    if not _safe(mcir_transformation_resolver, xform):
        return False, "transformation ref does not resolve as a valid MCIR transformation -> REFUTED"

    # (8) preserved evidence resolves under SMH read-only (resolution != authority).
    if not _safe(smh_evidence_resolver, ev):
        return False, "preserved evidence ref does not resolve under SMH read-only -> REFUTED"

    return True, "bridge surface valid under BRIDGE-BINDING"
