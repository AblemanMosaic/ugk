"""SMH-I1 — Projection Registry Store (SMH Track B, increment 1).

Implements the accepted SMH-P1 model: an EXTERNAL, READ-ONLY projection-registry
store that records projection->canonical citations under CK-CANON-0.1 identity.

Discipline (SMH-I1 scope / halt conditions):
  * REUSES CK-CANON-0.1 (ck_canon.domain_hash / canonical_bytes) — never forks it.
  * Projection identity (H of the descriptor BODY) is DISTINCT from canonical identity
    (H of the cited source artifact).  projection_id is excluded from the body.
  * Typed canonical_source_refs: ck_ref | smh_archive_ref | external_hash_ref.
  * Read-only stale / corrupt / missing detection (§6): three checks on different
    objects — staleness (projection currency) is never conflated with corruption
    (canonical integrity) or missing.
  * Does NOT mutate canonical artifacts, does NOT hydrate archives, does NOT embed
    SMH receipts into the UGK chain, does NOT touch UGK law/schema/legend.
  * Does NOT claim UGK implements SMH.

This module imports ONLY ck_canon (the CK-CANON canonicalizer). It does not import ugk.*.
"""
import os, sys, json, hashlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ck_impl"))
sys.path.insert(0, "/home/claude/ck_impl")
import ck_canon  # CK-CANON-0.1 — reused, not forked

# ---- SMH-owned domain-tag namespace (NOT added to the CK-0.1 normative registry) ----
SMH_DESCRIPTOR_TAG = "smh.projection.descriptor.v1"   # §3 descriptor identity
SMH_ARCHIVE_TAG    = "smh.archive.v1"                 # §4 smh_archive_ref

PROJECTION_KINDS = {"derived_document", "derived_index", "lineage_projection",
                    "materialized_view", "search_index"}
FRESHNESS_BASES  = {"cited_hash_comparison", "re_derivation"}


class SMHError(Exception):
    pass


# ---------------------------------------------------------------- identity helpers
def smh_archive_hash(archive_bytes: bytes) -> str:
    """H('smh.archive.v1' || 0x00 || archive_bytes) — domain-separated over RAW archive
    bytes (the canonical bytes ARE the archive bytes; no JSON canonicalization pretended).
    Reuses the CK-CANON domain-separation discipline (tag || 0x00 || bytes)."""
    if not isinstance(archive_bytes, (bytes, bytearray)):
        raise SMHError("smh_archive_hash: bytes required")
    return hashlib.sha256(SMH_ARCHIVE_TAG.encode("ascii") + b"\x00" + bytes(archive_bytes)).hexdigest()


# ---------------------------------------------------------------- typed source refs
def ck_ref(domain_tag: str, ck_value) -> dict:
    """CK-CANON identity of a CK JSON value-model artifact (domain_tag:hexdigest over its
    CK-CANON canonical bytes). Reuses ck_canon.domain_hash directly (no fork)."""
    return {"ref_type": "ck_ref", "domain_tag": domain_tag,
            "digest": ck_canon.domain_hash(domain_tag, ck_value)}


def smh_archive_ref(archive_bytes: bytes) -> dict:
    """Domain-separated identity over canonical ARCHIVE BYTES (release tarball etc.)."""
    return {"ref_type": "smh_archive_ref", "domain_tag": SMH_ARCHIVE_TAG,
            "digest": smh_archive_hash(archive_bytes)}


def external_hash_ref(regime: str, digest: str, domain_tag: str = None) -> dict:
    """Opaque-bytes citation with an EXPLICITLY declared hash regime. Use ONLY where
    neither ck_ref nor smh_archive_ref applies."""
    if not regime:
        raise SMHError("external_hash_ref: explicit regime required (fail-closed)")
    r = {"ref_type": "external_hash_ref", "regime": regime, "digest": digest}
    if domain_tag is not None:
        r["domain_tag"] = domain_tag
    return r


def _ref_digest(ref: dict) -> str:
    return ref.get("digest")


def _recompute_source_identity(ref: dict, current) -> str:
    """Recompute the identity of a cited source from its CURRENT content, per ref type.
    `current` is bytes (archive/external) or a CK JSON value (ck_ref). READ-ONLY: it only
    reads what the caller resolved; it never fetches/hydrates/materializes."""
    t = ref["ref_type"]
    if t == "ck_ref":
        return ck_canon.domain_hash(ref["domain_tag"], current)
    if t == "smh_archive_ref":
        return smh_archive_hash(current)
    if t == "external_hash_ref":
        regime = ref.get("regime")
        if regime != "sha-256":
            raise SMHError("external_hash_ref: unsupported declared regime %r" % regime)
        b = current if isinstance(current, (bytes, bytearray)) else str(current).encode("utf-8")
        dt = ref.get("domain_tag")
        if dt is not None:
            return hashlib.sha256(dt.encode("ascii") + b"\x00" + bytes(b)).hexdigest()
        return hashlib.sha256(bytes(b)).hexdigest()
    raise SMHError("unknown ref_type %r" % t)


# ---------------------------------------------------------------- descriptor / envelope
def make_descriptor_body(projection_kind: str, canonical_source_refs: list,
                         derivation_rule_ref: str, freshness_basis: str) -> dict:
    if projection_kind not in PROJECTION_KINDS:
        raise SMHError("bad projection_kind %r" % projection_kind)
    if freshness_basis not in FRESHNESS_BASES:
        raise SMHError("bad freshness_basis %r" % freshness_basis)
    if not canonical_source_refs:
        raise SMHError("at least one canonical_source_ref required (fail-closed)")
    for r in canonical_source_refs:
        if r.get("ref_type") not in ("ck_ref", "smh_archive_ref", "external_hash_ref"):
            raise SMHError("bad source ref type")
    # Body EXCLUDES projection_id (no self-hash fixed point). tier WARM, authoritative False.
    return {
        "projection_kind": projection_kind,
        "canonical_source_refs": list(canonical_source_refs),
        "derivation_rule_ref": derivation_rule_ref,
        "freshness_basis": freshness_basis,
        "tier": "WARM",
        "authoritative": False,
    }


def compute_projection_id(body: dict) -> str:
    """projection_id = H('smh.projection.descriptor.v1', canonical_bytes(body)) — CK-CANON §9,
    over the BODY only (projection_id is not a member of the body)."""
    if "projection_id" in body:
        raise SMHError("projection_id must NOT be a member of the body (self-hash forbidden)")
    return ck_canon.domain_hash(SMH_DESCRIPTOR_TAG, body)


def make_envelope(body: dict) -> dict:
    if body.get("tier") != "WARM" or body.get("authoritative") is not False:
        raise SMHError("invariant: projection tier=WARM, authoritative=false")
    return {"projection_id": compute_projection_id(body), "descriptor_body": body}


def verify_envelope(envelope: dict) -> dict:
    """Verify projection identity: recompute H over the body and compare to projection_id.
    A mismatch is a CORRUPT DESCRIPTOR (a projection-identity problem, distinct from any
    canonical finding)."""
    body = envelope.get("descriptor_body")
    pid = envelope.get("projection_id")
    if not isinstance(body, dict) or not isinstance(pid, str):
        return {"valid": False, "finding": "corrupt_descriptor", "detail": "malformed envelope"}
    try:
        recomputed = compute_projection_id(body)
    except SMHError as e:
        return {"valid": False, "finding": "corrupt_descriptor", "detail": str(e)}
    if recomputed != pid:
        return {"valid": False, "finding": "corrupt_descriptor",
                "detail": "projection_id mismatch", "declared": pid, "recomputed": recomputed}
    return {"valid": True, "finding": "intact_descriptor", "projection_id": pid}


# ---------------------------------------------------------------- §6 freshness detection
# Per-source resolver contract (READ-ONLY): resolver(ref) -> one of
#   None / {"present": False}                     -> the cited source is absent
#   {"present": True, "current": <bytes|value>,   -> current content to recompute identity from
#    "declared_identity": <hex|None>}             -> the source's CURRENTLY-declared identity (h_self);
#                                                    None => self-identifying (h_self := h_recomputed)
# The registry NEVER fetches/hydrates; the caller supplies what it already has on hand.

def assess_source(ref: dict, resolved) -> dict:
    """Three read-only checks (§6), in order, on ONE cited source.
    Returns a finding in {missing, corrupt, fresh, stale}."""
    h_cited = _ref_digest(ref)
    if not resolved or not resolved.get("present"):
        return {"finding": "missing", "ref_type": ref["ref_type"], "h_cited": h_cited}
    h_recomputed = _recompute_source_identity(ref, resolved["current"])
    h_self = resolved.get("declared_identity")
    if h_self is None:
        h_self = h_recomputed   # self-identifying source (identity == bytes hash)
    # 1. CANONICAL INTEGRITY
    if h_recomputed != h_self:
        return {"finding": "corrupt", "ref_type": ref["ref_type"],
                "h_self": h_self, "h_recomputed": h_recomputed, "h_cited": h_cited}
    # 2. PROJECTION CURRENCY (only against an INTACT canonical)
    if h_cited == h_self:
        return {"finding": "fresh", "ref_type": ref["ref_type"], "h_self": h_self}
    return {"finding": "stale", "ref_type": ref["ref_type"],
            "h_self": h_self, "h_cited": h_cited}   # behind a VALID, advanced canonical


def assess_projection(envelope: dict, resolver) -> dict:
    """Read-only assessment of a projection envelope. First verifies projection identity
    (corrupt_descriptor), then assesses each cited source (§6). Aggregate currency:
    STALE only if every cited canonical is INTACT and at least one is STALE; a MISSING/
    CORRUPT canonical leaves currency UNDETERMINED (do NOT assert stale)."""
    v = verify_envelope(envelope)
    if not v["valid"]:
        return {"projection_finding": "corrupt_descriptor", "descriptor": v, "sources": []}
    refs = envelope["descriptor_body"]["canonical_source_refs"]
    src = [assess_source(r, resolver(r)) for r in refs]
    findings = {s["finding"] for s in src}
    if "missing" in findings:
        agg = "undetermined_missing_source"
    elif "corrupt" in findings:
        agg = "undetermined_corrupt_source"
    elif "stale" in findings:
        agg = "stale"            # projection behind an intact, advanced canonical
    else:
        agg = "fresh"
    return {"projection_finding": agg, "descriptor": v, "sources": src,
            "authority_note": ("resolve to cited canonical (now advanced); flag projection for rebuild"
                               if agg == "stale" else None)}


# ---------------------------------------------------------------- the external store
class ProjectionRegistry:
    """READ-ONLY index projection_id -> ProjectionDescriptorEnvelope, persisted as JSON.
    It records CITATIONS; it holds NO canonical truth and performs NO hydration/mutation
    of canonical artifacts. `register` verifies projection identity before recording."""

    def __init__(self, path: str = None):
        self._path = path
        self._index = {}
        if path and os.path.exists(path):
            with open(path) as f:
                self._index = json.load(f).get("projections", {})

    def register(self, envelope: dict) -> str:
        v = verify_envelope(envelope)
        if not v["valid"]:
            raise SMHError("refusing to register a corrupt descriptor: %s" % v.get("detail"))
        pid = envelope["projection_id"]
        self._index[pid] = envelope
        self._flush()
        return pid

    def get(self, projection_id: str):
        return self._index.get(projection_id)

    def list_ids(self):
        return sorted(self._index.keys())

    def _flush(self):
        if self._path:
            with open(self._path, "w") as f:
                json.dump({"model": "smh.projection.registry.v1", "projections": self._index},
                          f, indent=2, sort_keys=True)
