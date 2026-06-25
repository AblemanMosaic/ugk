"""ugk/binding.py — Cryptographic binding primitives (Grundnorm layer, 444).

Central cryptographic surface for UGK.  All hash computation routes here.

Layered API:
  L0  content_hash(data)                  — integrity / file digests
  L1  canonical_json(obj) / commit(bytes) — CSH commitment
  L2  dm_s03(...) / chc(...)              — governance identity (CHC envelope)
      state_hash(op, inputs)              — +1 object hash floor
  L3  canonical_dkn(phase, pubkey)        — dimension_id (per-build namespace)
      mosaic_id(pubkey)                   — MosaicID_root (Level 0 identity)
      spawn_session_identity(...)         — Level 2 per-session identity

CHC_DIMENSIONS — D1..D8 canonical registry.
SessionIdentity — frozen per-session identity struct.

Identity ≠ authority:
  MosaicID proves WHO (derivable from public key, no secret needed).
  Authorization requires verify_governor() with the off-artifact Ed25519 secret.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Optional

SEP = "\u2016"                 # DM-S-03 field separator (U+2016 DOUBLE VERTICAL LINE)
DEFAULT_ALGORITHM_ID = "sha256"


# ---------------------------------------------------------------------------
# Internal digest primitive
# ---------------------------------------------------------------------------

def _digest(data: bytes, algorithm_id: str = DEFAULT_ALGORITHM_ID) -> str:
    if algorithm_id == "sha256":
        return hashlib.sha256(data).hexdigest()
    raise ValueError(
        f"binding: algorithm_id {algorithm_id!r} not enabled "
        f"(SHA-256 is the conformance reference; BLAKE3 is a future versioned change)"
    )


# ---------------------------------------------------------------------------
# L0 — content / integrity
# ---------------------------------------------------------------------------

def content_hash(data: bytes | str,
                 algorithm_id: str = DEFAULT_ALGORITHM_ID) -> str:
    """Digest of raw bytes or UTF-8 string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return _digest(data, algorithm_id)


def hasher(algorithm_id: str = DEFAULT_ALGORITHM_ID):
    """Incremental hash object (usage: h = hasher(); h.update(b"..."); h.hexdigest())."""
    if algorithm_id == "sha256":
        return hashlib.sha256()
    raise ValueError(f"binding: algorithm_id {algorithm_id!r} not enabled")


# ---------------------------------------------------------------------------
# L1 — commitment / CSH
# ---------------------------------------------------------------------------

def canonical_json(obj, ensure_ascii: bool = True) -> bytes:
    """Canonical JSON bytes (sort_keys=True, ensure_ascii=True)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=ensure_ascii).encode("utf-8")


def commit(canonical_bytes: bytes,
           algorithm_id: str = DEFAULT_ALGORITHM_ID) -> str:
    """Commit pre-canonicalized bytes → hex digest."""
    return _digest(canonical_bytes, algorithm_id)


# ---------------------------------------------------------------------------
# L2 — governance identity (DM-S-03 / CHC)
# ---------------------------------------------------------------------------

def dm_s03(
    state_hash: str,
    parent: str,
    intent,
    authority,
    jurisdiction,
    confidence,
    session_id,
    agent_id,
    ts,
    law_hash: str = "",
    legend_hash: str = "",
    intent_ref: str = "",
    algorithm_id: str = DEFAULT_ALGORITHM_ID,
) -> str:
    """Unified DM-S-03 semantic_hash (CHC envelope).

    Field order (canonical, never reordered):
      D1 state_hash | D2 parent | D3 intent | D4 authority | D5 jurisdiction |
      confidence | D7 session_id | D7 agent_id | ts | [D_law law_hash]
                                                     | [D_L legend_hash]

    D6 SEMANTICS: absent (investigation corpora bind 7 of 8).
    D8 RESOURCES: M1-observable metadata, NOT an envelope member (parsimony).
    law_hash:    SRT v2 — constitutional framework (invariants.py hash).
    legend_hash: Phase 6 — projection vocabulary (LEGEND constant hash).
    intent_ref:  Phase 13 — will layer (IntentDeclaration.declaration_hash).
    All default to "" for backward compatibility.
    """
    _fields = [
        str(state_hash), str(parent), str(intent), str(authority),
        str(jurisdiction), str(confidence), str(session_id),
        str(agent_id), str(ts),
    ]
    if law_hash:
        _fields.append(str(law_hash))
    if legend_hash:
        _fields.append(str(legend_hash))
    if intent_ref:
        _fields.append(str(intent_ref))
    payload = SEP.join(_fields)
    return _digest(payload.encode("utf-8"), algorithm_id)


# CHC is dm_s03 realized — same bytes, named entry point.
chc = dm_s03


def state_hash(op_name: str, inputs_repr: str = "",
               algorithm_id: str = DEFAULT_ALGORITHM_ID) -> str:
    """BYTE_HASH floor: H(op_name | inputs_repr) — the +1 object hash."""
    return _digest(f"{op_name}|{inputs_repr}".encode("utf-8"), algorithm_id)


# ---------------------------------------------------------------------------
# CHC_DIMENSIONS — 8 canonical governance dimensions
# ---------------------------------------------------------------------------

CHC_DIMENSIONS: dict[str, dict] = {
    "D1": {"name": "STATE",     "field": "state_hash",            "envelope": True},
    "D2": {"name": "CAUSAL",    "field": "parent",                "envelope": True},
    "D3": {"name": "INTENT",    "field": "intent",                "envelope": True},
    "D4": {"name": "AUTHORITY", "field": "authority",             "envelope": True},
    "D5": {"name": "CONTEXT",   "field": "jurisdiction",          "envelope": True},
    "D6": {"name": "SEMANTICS", "field": None,                    "envelope": False,
           "absent": True},
    "D7": {"name": "CUSTODY",   "field": "agent_id",              "envelope": True},
    "D8": {"name": "RESOURCES", "field": "metadata.output_bytes", "envelope": False,
           "metadata": True},
}


# ---------------------------------------------------------------------------
# L3 — namespace / identity hierarchy
# ---------------------------------------------------------------------------

def mosaic_id(governor_pubkey: str | bytes,
              algorithm_id: str = DEFAULT_ALGORITHM_ID) -> str:
    """MosaicID_root = SHA-256(governor_pubkey_bytes).

    Level 0 identity — stable across sessions, changes only on key rotation.
    Identity (proves WHO), not authority (requires Ed25519 secret).
    """
    if isinstance(governor_pubkey, str):
        governor_pubkey = governor_pubkey.encode("utf-8")
    return _digest(governor_pubkey, algorithm_id)


def canonical_dkn(phase_code: str, governor_pubkey: str,
                  algorithm_id: str = DEFAULT_ALGORITHM_ID) -> str:
    """dimension_id = HASH(phase_code ‖ SEP ‖ governor_pubkey).

    Level 1 identity — per build/phase namespace.  Distinct keys → distinct
    namespaces; collision-resistant, unsquattable through signed lineage.
    """
    return _digest((phase_code + SEP + governor_pubkey).encode("utf-8"), algorithm_id)


# ---------------------------------------------------------------------------
# SessionIdentity — per-session cryptographic identity (Level 2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionIdentity:
    """Immutable per-session identity struct.

    Encodes: WHO (mosaic_root), WHICH PHASE (phase_code), WHICH SESSION (session_id).
    Receipts across sessions carry different session_dkn values — mathematical
    differentiation, not convention.
    """
    mosaic_root: str   # SHA-256(governor_pubkey) — lineage anchor
    phase_code:  str   # semantic namespace selector (constitutional phase ref)
    session_id:  str   # UUID4 — 122-bit uniqueness
    session_dkn: str   # SHA-256(mosaic_root ‖ phase_code ‖ session_id)  WHO×WHAT×WHICH
    lineage:     tuple  # (mosaic_root, session_dkn) — derivation ancestry


def spawn_session_identity(
    governor_pubkey: str,
    phase_code: str,
    session_id: Optional[str] = None,
    algorithm_id: str = DEFAULT_ALGORITHM_ID,
) -> SessionIdentity:
    """Derive per-session identity from Governor root + phase_code + UUID4.

    Called by GovernanceKernel.open_session().  Kernel-injected — callers
    do not declare session_dkn; it flows into D7 (custody) on every receipt.

    phase_code triple duty:
      (1) semantic namespace selector
      (2) anti-replay nonce (strictly-increasing high-water mark)
      (3) constitutional phase reference
    """
    root = mosaic_id(governor_pubkey, algorithm_id)
    sid  = session_id or str(uuid.uuid4())
    dkn  = _digest(
        f"{root}:{phase_code}:{sid}".encode("utf-8"), algorithm_id
    )
    return SessionIdentity(
        mosaic_root=root,
        phase_code=phase_code,
        session_id=sid,
        session_dkn=dkn,
        lineage=(root, dkn),
    )


__all__ = [
    "SEP", "DEFAULT_ALGORITHM_ID",
    "content_hash", "hasher",
    "canonical_json", "commit",
    "dm_s03", "chc", "state_hash",
    "CHC_DIMENSIONS",
    "mosaic_id", "canonical_dkn",
    "SessionIdentity", "spawn_session_identity",
    # Phase 6 legend
    "LEGEND_BY_ID", "LEGEND_BY_SLUG", "LEGEND_BY_RENDER",
    "LEGEND_HASH", "LEGEND_ENTRY_COUNT",
    "COMPRESSED_FIELDS", "FIELD_COMPRESS_MAPS",
]


# ---------------------------------------------------------------------------
# L E G E N D — Constitutional projection vocabulary (RPZ0, governance terms)
# ---------------------------------------------------------------------------
# Each entry: csil_id (stable integer), slug (RPZ0 canonical), render (current
# string form), tier (invariant | dimension | op | vocab | status | warrant_result).
# Compressed fields in receipts: op, intent, jurisdiction, confidence.
# Dynamic fields (authority, parameters, hashes, timestamp) are NOT compressed.
#
# LEGEND_HASH = SHA-256(canonical_json(entries sorted by csil_id)).
# Different from law_hash: law_hash answers "what are the rules?";
# legend_hash answers "what is the admissible projection vocabulary?"
# Both are CHC dimensions; independent change rates.

_LEGEND_ENTRIES: list = [
    # ── Invariants (tier: invariant, 1000-range) ──────────────────────────
    {"csil_id": 1001, "slug": "inv-ul-g-01",   "render": "UL-G-01",   "tier": "invariant"},
    {"csil_id": 1002, "slug": "inv-ul-s-01",   "render": "UL-S-01",   "tier": "invariant"},
    {"csil_id": 1003, "slug": "inv-ul-s-02",   "render": "UL-S-02",   "tier": "invariant"},
    {"csil_id": 1004, "slug": "inv-ul-s-03",   "render": "UL-S-03",   "tier": "invariant"},
    {"csil_id": 1005, "slug": "inv-ul-s-04",   "render": "UL-S-04",   "tier": "invariant"},
    {"csil_id": 1006, "slug": "inv-gk-s-01",   "render": "GK-S-01",   "tier": "invariant"},
    {"csil_id": 1007, "slug": "inv-gk-s-02",   "render": "GK-S-02",   "tier": "invariant"},
    {"csil_id": 1008, "slug": "inv-cm-gs-01",  "render": "CM-GS-01",  "tier": "invariant"},
    {"csil_id": 1009, "slug": "inv-cm-gs-02",  "render": "CM-GS-02",  "tier": "invariant"},
    {"csil_id": 1010, "slug": "inv-cm-op-01",  "render": "CM-OP-01",  "tier": "invariant"},
    {"csil_id": 1011, "slug": "inv-chc-s-01",  "render": "CHC-S-01",  "tier": "invariant"},
    {"csil_id": 1012, "slug": "inv-chc-s-02",  "render": "CHC-S-02",  "tier": "invariant"},
    {"csil_id": 1013, "slug": "inv-chc-s-03",  "render": "CHC-S-03",  "tier": "invariant"},
    {"csil_id": 1014, "slug": "inv-dm-s-01",   "render": "DM-S-01",   "tier": "invariant"},
    {"csil_id": 1015, "slug": "inv-dm-s-03",   "render": "DM-S-03",   "tier": "invariant"},
    {"csil_id": 1016, "slug": "inv-cr-s-01",   "render": "CR-S-01",   "tier": "invariant"},
    {"csil_id": 1017, "slug": "inv-cr-s-02",   "render": "CR-S-02",   "tier": "invariant"},
    {"csil_id": 1018, "slug": "inv-esa-s-01",  "render": "ESA-S-01",  "tier": "invariant"},
    {"csil_id": 1019, "slug": "inv-eh-s-01",   "render": "EH-S-01",   "tier": "invariant"},
    {"csil_id": 1020, "slug": "inv-eh-s-02",   "render": "EH-S-02",   "tier": "invariant"},
    {"csil_id": 1021, "slug": "inv-adv-s-01",  "render": "ADV-S-01",  "tier": "invariant"},
    {"csil_id": 1022, "slug": "inv-cm-dim-01", "render": "CM-DIM-01", "tier": "invariant"},
    {"csil_id": 1023, "slug": "inv-ctr-s-07",  "render": "CTR-S-07",  "tier": "invariant"},
    {"csil_id": 1024, "slug": "inv-ctr-s-01",  "render": "CTR-S-01",  "tier": "invariant"},
    {"csil_id": 1025, "slug": "inv-srsa-s-01", "render": "SRSA-S-01", "tier": "invariant"},
    {"csil_id": 1026, "slug": "inv-ul-l-01",   "render": "UL-L-01",   "tier": "invariant"},
    # Phase 6 invariants
    {"csil_id": 1027, "slug": "inv-legend-s-01", "render": "LEGEND-S-01", "tier": "invariant"},
    {"csil_id": 1028, "slug": "inv-legend-s-02", "render": "LEGEND-S-02", "tier": "invariant"},
    {"csil_id": 1029, "slug": "inv-legend-s-03", "render": "LEGEND-S-03", "tier": "invariant"},
    {"csil_id": 1030, "slug": "inv-legend-s-04", "render": "LEGEND-S-04", "tier": "invariant"},
    {"csil_id": 1031, "slug": "inv-dw-s-01",     "render": "DW-S-01",     "tier": "invariant"},
    {"csil_id": 1032, "slug": "inv-dw-s-02",     "render": "DW-S-02",     "tier": "invariant"},
    # ── Dimensions (tier: dimension, 2000-range) ──────────────────────────
    {"csil_id": 2001, "slug": "dim-cm-gs-01",  "render": "CM-GS-01",  "tier": "dimension"},
    {"csil_id": 2002, "slug": "dim-cm-op-01",  "render": "CM-OP-01",  "tier": "dimension"},
    {"csil_id": 2003, "slug": "dim-cm-dm-01",  "render": "CM-DM-01",  "tier": "dimension"},
    {"csil_id": 2004, "slug": "dim-cm-dep-01", "render": "CM-DEP-01", "tier": "dimension"},
    {"csil_id": 2005, "slug": "dim-cm-fm-01",  "render": "CM-FM-01",  "tier": "dimension"},
    {"csil_id": 2006, "slug": "dim-cm-st-01",  "render": "CM-ST-01",  "tier": "dimension"},
    {"csil_id": 2007, "slug": "dim-cm-br-01",  "render": "CM-BR-01",  "tier": "dimension"},
    {"csil_id": 2008, "slug": "dim-cm-sn-01",  "render": "CM-SN-01",  "tier": "dimension"},
    {"csil_id": 2009, "slug": "dim-cm-cr-01",  "render": "CM-CR-01",  "tier": "dimension"},
    {"csil_id": 2010, "slug": "dim-cm-gk-01",  "render": "CM-GK-01",  "tier": "dimension"},
    {"csil_id": 2011, "slug": "dim-cm-vs-01",  "render": "CM-VS-01",  "tier": "dimension"},
    {"csil_id": 2012, "slug": "dim-cm-ic-01",  "render": "CM-IC-01",  "tier": "dimension"},
    # ── Op names (tier: op, 3000-range) ───────────────────────────────────
    {"csil_id": 3001, "slug": "op-session-open",     "render": "session_open",     "tier": "op"},
    {"csil_id": 3002, "slug": "op-session-close",    "render": "session_close",    "tier": "op"},
    {"csil_id": 3003, "slug": "op-crp-evidence",     "render": "crp_evidence",     "tier": "op"},
    {"csil_id": 3004, "slug": "op-test-checkpoint",  "render": "test_checkpoint",  "tier": "op"},
    {"csil_id": 3005, "slug": "op-gate-admit",       "render": "gate_admit",       "tier": "op"},
    {"csil_id": 3006, "slug": "op-gate-refuse",      "render": "gate_refuse",      "tier": "op"},
    {"csil_id": 3007, "slug": "op-legend-seal",      "render": "legend_seal",      "tier": "op"},
    {"csil_id": 3008, "slug": "op-session-summary",  "render": "session_summary",  "tier": "op"},
    # ── Vocab: intent types (tier: vocab, 4001-4099) ──────────────────────
    {"csil_id": 4001, "slug": "intent-orient",     "render": "orient",     "tier": "vocab"},
    {"csil_id": 4002, "slug": "intent-synthesize", "render": "synthesize", "tier": "vocab"},
    {"csil_id": 4003, "slug": "intent-verify",     "render": "verify",     "tier": "vocab"},
    {"csil_id": 4004, "slug": "intent-claim",      "render": "claim",      "tier": "vocab"},
    {"csil_id": 4005, "slug": "intent-transform",  "render": "transform",  "tier": "vocab"},
    {"csil_id": 4006, "slug": "intent-conform",    "render": "conform",    "tier": "vocab"},
    {"csil_id": 4007, "slug": "intent-annotate",   "render": "annotate",   "tier": "vocab"},
    {"csil_id": 4008, "slug": "intent-observe",    "render": "observe",    "tier": "vocab"},
    # Phase 12 — SSA vocabulary extension (verbs 9-17, Governor-confirmed)
    {"csil_id": 4009, "slug": "intent-resolve",    "render": "resolve",    "tier": "vocab"},
    {"csil_id": 4010, "slug": "intent-propose",    "render": "propose",    "tier": "vocab"},
    {"csil_id": 4011, "slug": "intent-evaluate",   "render": "evaluate",   "tier": "vocab"},
    {"csil_id": 4012, "slug": "intent-classify",   "render": "classify",   "tier": "vocab"},
    {"csil_id": 4013, "slug": "intent-derive",     "render": "derive",     "tier": "vocab"},
    {"csil_id": 4014, "slug": "intent-compare",    "render": "compare",    "tier": "vocab"},
    {"csil_id": 4015, "slug": "intent-define",     "render": "define",     "tier": "vocab"},
    {"csil_id": 4016, "slug": "intent-infer",      "render": "infer",      "tier": "vocab"},
    {"csil_id": 4017, "slug": "intent-enumerate",  "render": "enumerate",  "tier": "vocab"},
    # Meta-governance vocabulary (Phase 19, 4018-4028)
    {"csil_id": 4018, "slug": "meta-effective-authority",  "render": "effective_authority",  "tier": "vocab"},
    {"csil_id": 4019, "slug": "meta-latent-authority",     "render": "latent_authority",     "tier": "vocab"},
    {"csil_id": 4020, "slug": "meta-enabler-orientation",  "render": "enabler_orientation",  "tier": "vocab"},
    {"csil_id": 4021, "slug": "meta-phi-scalar",           "render": "phi_scalar",           "tier": "vocab"},
    {"csil_id": 4022, "slug": "meta-authority-model",      "render": "authority_model",      "tier": "vocab"},
    {"csil_id": 4023, "slug": "meta-constitutive-gate",    "render": "constitutive_gate",    "tier": "vocab"},
    {"csil_id": 4024, "slug": "meta-ceremonial-gate",      "render": "ceremonial_gate",      "tier": "vocab"},
    {"csil_id": 4025, "slug": "meta-probe-result",         "render": "constitutive_probe_result","tier": "vocab"},
    {"csil_id": 4026, "slug": "meta-posture-claim",        "render": "posture_claim",        "tier": "vocab"},
    {"csil_id": 4027, "slug": "meta-governance-posture",   "render": "governance_posture",   "tier": "vocab"},
    {"csil_id": 4028, "slug": "meta-posture-vector",       "render": "posture_vector",       "tier": "vocab"},
    # CSIL self-description (meta tier, 6001-6005)
    {"csil_id": 6001, "slug": "csil-layer",                "render": "CSIL",                 "tier": "meta"},
    {"csil_id": 6002, "slug": "gti-resolver",              "render": "GTI",                  "tier": "meta"},
    {"csil_id": 6003, "slug": "csil-coordinate",           "render": "csil_coordinate",      "tier": "meta"},
    {"csil_id": 6004, "slug": "coordinate-shadowing",      "render": "coordinate_shadowing", "tier": "meta"},
    {"csil_id": 6005, "slug": "semantic-topology",         "render": "semantic_topology",    "tier": "meta"},
    {"csil_id": 6006, "slug": "leg-ex-marker",             "render": "LEG-EX",               "tier": "meta"},  # E6 LEG-EX (r81): legend-leg exercise marker — meta tier, NO governance semantics
    # Vocab: jurisdiction types (4101-4199)
    {"csil_id": 4101, "slug": "juris-session",  "render": "session",  "tier": "vocab"},
    {"csil_id": 4102, "slug": "juris-corpus",   "render": "corpus",   "tier": "vocab"},
    {"csil_id": 4103, "slug": "juris-operator", "render": "operator", "tier": "vocab"},
    {"csil_id": 4104, "slug": "juris-system",   "render": "system",   "tier": "vocab"},
    {"csil_id": 4105, "slug": "juris-kernel",   "render": "kernel",   "tier": "vocab"},
    # Vocab: confidence levels (4301-4399)
    {"csil_id": 4301, "slug": "conf-high",   "render": "high",   "tier": "vocab"},
    {"csil_id": 4302, "slug": "conf-medium", "render": "medium", "tier": "vocab"},
    {"csil_id": 4303, "slug": "conf-low",    "render": "low",    "tier": "vocab"},
    # ── Status constants (tier: status, 5000-range) ────────────────────────
    {"csil_id": 5001, "slug": "status-uninitialized", "render": "UNINITIALIZED", "tier": "status"},
    {"csil_id": 5002, "slug": "status-active",         "render": "ACTIVE",        "tier": "status"},
    # ── Warrant result terms (tier: warrant_result, 9000-range) ───────────
    {"csil_id": 9001, "slug": "result-admit",             "render": "ADMIT",                    "tier": "warrant_result"},
    {"csil_id": 9002, "slug": "result-refuse",            "render": "REFUSE",                   "tier": "warrant_result"},
    {"csil_id": 9101, "slug": "analysis-auth-sufficient", "render": "authority_tier_sufficient", "tier": "warrant_result"},
    {"csil_id": 9102, "slug": "analysis-juris-valid",     "render": "jurisdiction_valid",        "tier": "warrant_result"},
    {"csil_id": 9103, "slug": "analysis-inv-satisfied",   "render": "invariant_satisfied",       "tier": "warrant_result"},
]

# Bidirectional maps — O(1) lookup in both directions
LEGEND_BY_ID:    dict = {e["csil_id"]: e for e in _LEGEND_ENTRIES}
LEGEND_BY_SLUG:  dict = {e["slug"]:    e for e in _LEGEND_ENTRIES}
LEGEND_BY_RENDER: dict = {}  # render → list[entry] (render may be non-unique across tiers)
for _e in _LEGEND_ENTRIES:
    LEGEND_BY_RENDER.setdefault(_e["render"], []).append(_e)

# Compressed field slugs — maps field_name → lookup_tier for receipt compression
COMPRESSED_FIELDS: dict = {
    "op":           "op",
    "intent":       "vocab",     # intent-* slugs
    "jurisdiction": "vocab",     # juris-* slugs
    "confidence":   "vocab",     # conf-* slugs
}

# Convenience: op-name → csil_id for the four compressed receipt fields
_OP_TO_CSIL:    dict = {e["render"]: e["csil_id"] for e in _LEGEND_ENTRIES if e["tier"] == "op"}
_INTENT_TO_CSIL: dict = {e["render"]: e["csil_id"] for e in _LEGEND_ENTRIES
                         if e["tier"] == "vocab" and e["slug"].startswith("intent-")}
_JURIS_TO_CSIL:  dict = {e["render"]: e["csil_id"] for e in _LEGEND_ENTRIES
                         if e["tier"] == "vocab" and e["slug"].startswith("juris-")}
_CONF_TO_CSIL:   dict = {e["render"]: e["csil_id"] for e in _LEGEND_ENTRIES
                         if e["tier"] == "vocab" and e["slug"].startswith("conf-")}

FIELD_COMPRESS_MAPS: dict = {
    "op":           _OP_TO_CSIL,
    "intent":       _INTENT_TO_CSIL,
    "jurisdiction": _JURIS_TO_CSIL,
    "confidence":   _CONF_TO_CSIL,
}

import hashlib as _hashlib, json as _json_mod

def _legend_canonical() -> bytes:
    """Canonical JSON of legend entries sorted by csil_id."""
    return _json_mod.dumps(
        sorted(_LEGEND_ENTRIES, key=lambda e: e["csil_id"]),
        sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

LEGEND_HASH: str = _hashlib.sha256(_legend_canonical()).hexdigest()

del _hashlib, _json_mod  # keep binding.py namespace clean

LEGEND_ENTRY_COUNT: int = len(_LEGEND_ENTRIES)
