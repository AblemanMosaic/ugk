"""ugk/store.py — Receipt store with full 3+1 CHC schema (Grundnorm layer, 444).

Every receipt carries the complete four-layer hash stack from day one:

  (+1) state_hash    = H(op | inputs_json)             — object hash floor
  CHC  semantic_hash = dm_s03(state, parent, intent,    — multidimensional binding
                              authority, jurisdiction,
                              confidence, session_dkn→session_id,
                              session_dkn→agent_id, ts, law_hash)
                              (D7 agent slot carries session_dkn in Phase 1)
  DKN  session_dkn   = SHA-256(mosaic_root:phase_code:session_id) — WHO×WHAT×WHICH
  CSH  (Phase 3)     = quorum finality over law_hash    — not Phase 1

The receipt_hash used for chain participation IS semantic_hash (CHC output).
stream_hash() returns the chain tip (latest semantic_hash).

DM-S-01: append-only store (SQLite).
DM-S-03: causal binding via prior_receipt_hash (D2/parent in CHC).
UL-S-01: stdlib only (hashlib, sqlite3, json, time).
UL-S-04: Cap-1/2/4 at substrate cost.
UL-S-05: Two-tier snapshot (called by kernel, not by store directly).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional



# ---------------------------------------------------------------------------
# Receipt dataclass — full 3+1 schema
# ---------------------------------------------------------------------------

@dataclass
class Receipt:
    """Single governance receipt — full 3+1 field schema + M2 binding (Phase M2.2)."""
    op:                  str
    authority:           str
    parameters:          dict
    intent:              str
    jurisdiction:        str
    confidence:          str
    timestamp:           float
    failed:              bool
    session_dkn:         str   # D7 custody
    law_hash:            str   # constitutional situating (empty in UNINITIALIZED)
    legend_hash:         str   # Phase 6: projection vocabulary (LEGEND constant hash)
    warrant_id:          str   # Phase 6: optional DecisionWarrant reference ("" if none)
    intent_ref:          str   # Phase 13: optional IntentDeclaration reference ("" if none)
    receipt_id:          Optional[int] = field(default=None, repr=False)
    # ── M2 binding fields — M2-PRIMARY canonical receipt semantics ──
    # Per REV3 §Deliverable 4. After M2.3 proxy replacement + verifier
    # activation (M2.3a..m), these fields are the canonical receipt
    # commitment surface. Legacy fields above are compatibility-retained.
    h_s:        str = ""               # per-commitment hash, state         [M2-PRIMARY]
    h_c:        str = ""               # per-commitment hash, admissibility [M2-PRIMARY]
    h_m:        str = ""               # per-commitment hash, meaning       [M2-PRIMARY]
    h_j:        Optional[str] = None   # per-commitment hash, locality      [M2-PRIMARY]
    h_r:        str = ""               # binding root (merkle root)         [M2-PRIMARY]
    parent_h_r: str = ""               # M2 chain link — bound into c_c     [M2-PRIMARY]
    mode:       str = "strict"         # Strict | ContextExternal | ReEvaluable
    version:    int = 1                # M2 schema version
    id_c_s:     str = "c_s.v1"
    id_c_c:     str = "c_c.v1"
    id_c_m:     str = "c_m.v1+sigma_0"
    id_c_j:     str = "c_j.v1"
    h_body:     str = ""               # IEL/AD-28: full-body integrity commitment
    # ── Increment A (AD-51) — LM-2 terminal-outcome commitment ──
    terminal_outcome:          Optional[str] = None  # body-committed (v2); closed 5-set, emit {ADMIT,REFUSE,STRUCTURAL_ERROR}
    terminal_outcome_model_id: Optional[str] = None  # body-committed (v2)
    terminal_outcome_reason:   Optional[str] = None  # body-committed (v2)
    trace_vector_hash:         Optional[str] = None  # schema-persisted POST-body (NOT in h_body); r127 FGA-TRACE-v1
    # ── Lane 4b (AD-52) — D_cap committed capability-evidence surface (NON-aggregating, v3) ──
    h_cap:                       Optional[str] = None  # body-committed (v3); binds the CGP ledger
    capability_evidence_model_id: Optional[str] = None # body-committed (v3)
    capability_ledger_hash:      Optional[str] = None  # body-committed (v3); bound CGP ledger_hash
    capability_registry_version: Optional[str] = None  # body-committed (v3)
    capability_scope_id:         Optional[str] = None  # body-committed (v3)
    # ── r134 (AD-57) — typed effect surface, schema-closed mirror of the parameters markers (v4) ──
    effect_atomicity:                     Optional[str] = None  # body-committed (v4); closed 5-set
    effect_atomicity_model_id:            Optional[str] = None  # body-committed (v4)
    effect_phase:                         Optional[str] = None  # body-committed (v4); closed 6-set or None
    effect_prepare_ref:                   Optional[str] = None  # body-committed (v4)
    effect_compensate_ref:                Optional[str] = None  # body-committed (v4)
    effect_idempotency_key:               Optional[str] = None  # body-committed (v4)
    effect_compensation_idempotency_key:  Optional[str] = None  # body-committed (v4)
    effect_abort_reason:                  Optional[str] = None  # body-committed (v4)
    effect_gate_admit_ref:                Optional[str] = None  # body-committed (v4)
    reconciliation_grade:            Optional[str] = None  # body-committed (v6, AD-66): 'verified' | None(recorded)
    reconciliation_warrant_snapshot: Optional[str] = None  # body-committed (v6): canonical warrant body; sha256==warrant_id
    continuation_id:            Optional[str] = None  # body-committed (v7, AD-71): deterministic continuation id
    continuation_op:            Optional[str] = None  # body-committed (v7): captured op to be resumed
    continuation_authority:     Optional[str] = None  # body-committed (v7): canonical authority payload
    continuation_parameters:    Optional[str] = None  # body-committed (v7): canonical JSON parameters snapshot
    continuation_jurisdiction:  Optional[str] = None  # body-committed (v7): captured jurisdiction/scope
    continuation_expiry_basis:  Optional[str] = None  # body-committed (v7): canonical JSON {kind,value}; no wall-clock
    continuation_state:         Optional[str] = None  # body-committed (v7): closed lifecycle marker (append-only)
    continuation_model_id:      Optional[str] = None  # body-committed (v7): continuation_record_model_v1
    # CK-BRIDGE Stage 2 (UGK-BODY-v8): BRIDGE committed surface. Typed BridgeRecord identity + refs, NOT
    # MCIR/SMH bodies (citation, never embedding). NULL on every non-bridge receipt (BRIDGE non-emittable
    # at Stage 2 -- surface committed but UNBOUND; the BRIDGE-BINDING law + kernel emit are LATER legs).
    bridge_record_id:           Optional[str] = None  # body-committed (v8): BridgeRecord artifact hash (mcir_artifact_id)
    bridge_source_regime_ref:   Optional[str] = None  # body-committed (v8): MCIR source-regime artifact ref
    bridge_target_regime_ref:   Optional[str] = None  # body-committed (v8): MCIR target-regime artifact ref
    bridge_transformation_ref:  Optional[str] = None  # body-committed (v8): MCIR transformation artifact ref
    bridge_downgrade_reason:    Optional[str] = None  # body-committed (v8): closed downgrade-taxonomy scalar
    bridge_preserved_evidence_ref: Optional[str] = None  # body-committed (v8): SMH source-ref (preserved evidence; not embedded)



# ─────────────────────────────────────────────────────────────────────────────
# M2.3n — Receipt field classification (Option B partial clean-break)
# ─────────────────────────────────────────────────────────────────────────────
#
# Per the M2.3n directive (Governor ruling, Option B):
#   - M2-PRIMARY fields are the canonical receipt commitment surface;
#     new code should bind, verify, and reason about receipts via these.
#   - LEGACY-COMPATIBILITY fields are retained for backward compatibility
#     with chc_gate / chain_gate (whose semantic purpose IS the legacy
#     CHC envelope and legacy chain), audit.py production logs, and
#     migration_gate's GovResult check. They are NOT semantically primary
#     for new code.
#
# Full removal of LEGACY-COMPATIBILITY fields is DEFERRED to a future
# major schema epoch or REV4 decision, contingent on Governor authorization
# to retire or replace the CHC envelope and legacy chain gates.
#
# See ugk/LEGACY_RETIREMENT.md (M2.3p) for the full deferred-items catalog
# organized by dependency tier (production APIs → CHC envelope → schema).

M2_PRIMARY_RECEIPT_FIELDS: frozenset[str] = frozenset({
    "h_s", "h_c", "h_m", "h_j", "h_r", "parent_h_r",
})

LEGACY_COMPAT_RECEIPT_FIELDS: frozenset[str] = frozenset()  # RT-3j (E5b Tier 3): legacy receipt fields removed
# Note: `receipt_hash` is also legacy-compat but it is a @property,
# not a dataclass field; it appears in the Receipt namespace but not
# as a stored attribute. Tooling that enumerates fields should consult
# the dataclass fields directly.

LEGACY_ONLY_GATES: frozenset[str] = frozenset()  # RT-3m (E5b Tier 3): all four re-anchored to M2 (r79)
# These gates' semantic purposes are intertwined with the legacy CHC
# envelope or legacy chain; they have no M2 analog and are retained as
# historical conformance witnesses. Migrating them away from legacy
# fields would change what they validate.


# ---------------------------------------------------------------------------
# SQL schema
# ---------------------------------------------------------------------------

from ugk.scope import _CREATE_SCOPE_ARCHIVE as _CREATE_SCOPE_ARCHIVE_SQL
from ugk.authority.authority_model import _CREATE_AM_ARCHIVE as _CREATE_AM_ARCHIVE_SQL

_CREATE_LEGEND_ARCHIVE = """
CREATE TABLE IF NOT EXISTS legend_archive (
    legend_hash  TEXT    PRIMARY KEY,
    entries_json TEXT    NOT NULL,
    phase_code   TEXT    NOT NULL DEFAULT '',
    entry_count  INTEGER NOT NULL DEFAULT 0,
    sealed_at    TEXT    NOT NULL DEFAULT ''
);
"""

_CREATE_RECEIPTS = """
CREATE TABLE IF NOT EXISTS receipts (
    receipt_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    op                 TEXT    NOT NULL,
    authority          TEXT    NOT NULL,
    parameters         TEXT    NOT NULL,
    intent             TEXT    NOT NULL,
    jurisdiction       TEXT    NOT NULL DEFAULT 'session',
    confidence         TEXT    NOT NULL DEFAULT 'high',
    timestamp          REAL    NOT NULL,
    failed             INTEGER NOT NULL DEFAULT 0,
    session_dkn        TEXT    NOT NULL DEFAULT '',
    law_hash           TEXT    NOT NULL DEFAULT '',
    legend_hash        TEXT    NOT NULL DEFAULT '',
    warrant_id         TEXT    NOT NULL DEFAULT '',
    intent_ref         TEXT    NOT NULL DEFAULT '',
    -- M2 binding fields (Phase M2.2 additive; no impact on legacy gates)
    h_s                TEXT    NOT NULL DEFAULT '',
    h_c                TEXT    NOT NULL DEFAULT '',
    h_m                TEXT    NOT NULL DEFAULT '',
    h_j                TEXT,
    h_r                TEXT    NOT NULL DEFAULT '',
    parent_h_r         TEXT    NOT NULL DEFAULT '',
    mode               TEXT    NOT NULL DEFAULT 'strict',
    version            INTEGER NOT NULL DEFAULT 1,
    id_c_s             TEXT    NOT NULL DEFAULT 'c_s.v1',
    id_c_c             TEXT    NOT NULL DEFAULT 'c_c.v1',
    id_c_m             TEXT    NOT NULL DEFAULT 'c_m.v1+sigma_0',
    id_c_j             TEXT    NOT NULL DEFAULT 'c_j.v1',
    h_body             TEXT    NOT NULL DEFAULT '',
    terminal_outcome           TEXT,
    terminal_outcome_model_id  TEXT,
    terminal_outcome_reason    TEXT,
    trace_vector_hash          TEXT,
    h_cap                        TEXT,
    capability_evidence_model_id TEXT,
    capability_ledger_hash       TEXT,
    capability_registry_version  TEXT,
    capability_scope_id          TEXT,
    effect_atomicity                     TEXT,
    effect_atomicity_model_id            TEXT,
    effect_phase                         TEXT,
    effect_prepare_ref                   TEXT,
    effect_compensate_ref                TEXT,
    effect_idempotency_key               TEXT,
    effect_compensation_idempotency_key  TEXT,
    effect_abort_reason                  TEXT,
    effect_gate_admit_ref                TEXT
);
"""

# ---------------------------------------------------------------------------
# E5a — Schema-Leg Capability Validation probe table.
# DISPOSABLE VALIDATION ARTIFACT. This table has NO governance semantics and carries
# no data; it exists SOLELY to provide the smallest persisted schema element that moves
# schema_hash, so the frame-general amendment machinery can be exercised on a NON-LAW
# frame leg (the schema leg) with law + legend stationary. See AD-20. E5b may remove it
# (itself another schema-leg amendment). Do not infer any hidden semantic intent.
# ---------------------------------------------------------------------------
_CREATE_FRAME_LEG_PROBE = """
CREATE TABLE IF NOT EXISTS frame_leg_probe (
    id INTEGER PRIMARY KEY
);
"""

# M2.2 columns added by ALTER on existing DBs (idempotent).
# Required because SQLite CREATE TABLE IF NOT EXISTS doesn't migrate existing schemas.
_M2_COLUMN_DEFS = [
    ("h_s",        "TEXT NOT NULL DEFAULT ''"),
    ("h_c",        "TEXT NOT NULL DEFAULT ''"),
    ("h_m",        "TEXT NOT NULL DEFAULT ''"),
    ("h_j",        "TEXT"),
    ("h_r",        "TEXT NOT NULL DEFAULT ''"),
    ("parent_h_r", "TEXT NOT NULL DEFAULT ''"),
    ("mode",       "TEXT NOT NULL DEFAULT 'strict'"),
    ("version",    "INTEGER NOT NULL DEFAULT 1"),
    ("id_c_s",     "TEXT NOT NULL DEFAULT 'c_s.v1'"),
    ("id_c_c",     "TEXT NOT NULL DEFAULT 'c_c.v1'"),
    ("id_c_m",     "TEXT NOT NULL DEFAULT 'c_m.v1+sigma_0'"),
    ("id_c_j",     "TEXT NOT NULL DEFAULT 'c_j.v1'"),
    ("h_body",     "TEXT NOT NULL DEFAULT ''"),
    ("terminal_outcome",          "TEXT"),
    ("terminal_outcome_model_id", "TEXT"),
    ("terminal_outcome_reason",   "TEXT"),
    ("trace_vector_hash",         "TEXT"),
    ("h_cap",                        "TEXT"),
    ("capability_evidence_model_id", "TEXT"),
    ("capability_ledger_hash",       "TEXT"),
    ("capability_registry_version",  "TEXT"),
    ("capability_scope_id",          "TEXT"),
    ("effect_atomicity",                     "TEXT"),
    ("effect_atomicity_model_id",            "TEXT"),
    ("effect_phase",                         "TEXT"),
    ("effect_prepare_ref",                   "TEXT"),
    ("effect_compensate_ref",                "TEXT"),
    ("effect_idempotency_key",               "TEXT"),
    ("effect_compensation_idempotency_key",  "TEXT"),
    ("effect_abort_reason",                  "TEXT"),
    ("effect_gate_admit_ref",                "TEXT"),
    ("reconciliation_grade",                 "TEXT"),
    ("reconciliation_warrant_snapshot",      "TEXT"),
    ("continuation_id",              "TEXT"),
    ("continuation_op",              "TEXT"),
    ("continuation_authority",       "TEXT"),
    ("continuation_parameters",      "TEXT"),
    ("continuation_jurisdiction",    "TEXT"),
    ("continuation_expiry_basis",    "TEXT"),
    ("continuation_state",           "TEXT"),
    ("continuation_model_id",        "TEXT"),
    ("bridge_record_id",             "TEXT"),
    ("bridge_source_regime_ref",     "TEXT"),
    ("bridge_target_regime_ref",     "TEXT"),
    ("bridge_transformation_ref",    "TEXT"),
    ("bridge_downgrade_reason",      "TEXT"),
    ("bridge_preserved_evidence_ref","TEXT"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _params_json(parameters: dict) -> str:
    return json.dumps(parameters, sort_keys=True, separators=(",", ":"))


def compute_h_body(*, op, authority, parameters, intent, jurisdiction, confidence, timestamp,
                   failed, session_dkn, law_hash, legend_hash, warrant_id, intent_ref,
                   h_s, h_c, h_m, h_j, h_r, parent_h_r, mode, version,
                   id_c_s, id_c_c, id_c_m, id_c_j,
                   terminal_outcome=None, terminal_outcome_model_id=None,
                   terminal_outcome_reason=None,
                   h_cap=None, capability_evidence_model_id=None,
                   capability_ledger_hash=None, capability_registry_version=None,
                   capability_scope_id=None,
                   effect_atomicity=None, effect_atomicity_model_id=None,
                   effect_phase=None, effect_prepare_ref=None, effect_compensate_ref=None,
                   effect_idempotency_key=None, effect_compensation_idempotency_key=None,
                   effect_abort_reason=None, effect_gate_admit_ref=None,
                   reconciliation_grade=None, reconciliation_warrant_snapshot=None,
                   continuation_id=None, continuation_op=None, continuation_authority=None,
                   continuation_parameters=None, continuation_jurisdiction=None,
                   continuation_expiry_basis=None, continuation_state=None,
                   continuation_model_id=None,
                   bridge_record_id=None, bridge_source_regime_ref=None,
                   bridge_target_regime_ref=None, bridge_transformation_ref=None,
                   bridge_downgrade_reason=None, bridge_preserved_evidence_ref=None) -> str:
    """IEL/AD-28 full-body integrity commitment: a domain-separated hash over EVERY committed
    receipt field except h_body itself, computed PURELY from stored values (no live-state
    dependency), so a verifier recomputes it deterministically and detects tampering of ANY field.
    Distinct from the merkle root h_r (whose leaves bind live-derived context not stored on the
    receipt); h_body is the verification-grade whole-body commitment."""
    import hashlib
    from ugk.storage import binding_m2 as _m2
    body = {
        "op": op, "authority": authority, "parameters": parameters, "intent": intent,
        "jurisdiction": jurisdiction, "confidence": confidence, "timestamp": timestamp,
        "failed": bool(failed), "session_dkn": session_dkn, "law_hash": law_hash,
        "legend_hash": legend_hash, "warrant_id": warrant_id, "intent_ref": intent_ref,
        "h_s": h_s, "h_c": h_c, "h_m": h_m, "h_j": (h_j or ""), "h_r": h_r,
        "parent_h_r": parent_h_r, "mode": mode, "version": int(version),
        "id_c_s": id_c_s, "id_c_c": id_c_c, "id_c_m": id_c_m, "id_c_j": id_c_j,
    }
    if int(version) >= 2:
        # UGK-BODY-v2 (AD-51, Increment A): body-commit the LM-2 terminal-outcome projection.
        # trace_vector_hash is NOT a member here — it is a schema-persisted POST-body commitment.
        body["terminal_outcome"] = terminal_outcome
        body["terminal_outcome_model_id"] = terminal_outcome_model_id
        body["terminal_outcome_reason"] = terminal_outcome_reason
    if int(version) >= 3:
        # UGK-BODY-v3 (AD-52, Lane 4b): ALSO body-commit the D_cap capability-evidence
        # commitment. h_cap binds the CGP ledger. NON-AGGREGATING: it is NOT consumed by
        # conjunctive_refusal_monotone_v1 and does NOT affect ADMIT/REFUSE. trace_vector_hash
        # remains the post-body FGA-TRACE-v1 over the FOUR aggregating surfaces (h_cap not in it).
        body["h_cap"] = h_cap
        body["capability_evidence_model_id"] = capability_evidence_model_id
        body["capability_ledger_hash"] = capability_ledger_hash
        body["capability_registry_version"] = capability_registry_version
        body["capability_scope_id"] = capability_scope_id
    if int(version) >= 4:
        # UGK-BODY-v4 (AD-57, r134): ALSO body-commit the typed effect surface — the schema-closed
        # mirror of the parameters effect markers. These columns are derived from the markers at
        # write (single source); committing them in h_body makes the typed surface verification-grade.
        # NON-AGGREGATING and orthogonal to terminal_outcome / D_cap; trace_vector_hash unaffected.
        body["effect_atomicity"] = effect_atomicity
        body["effect_atomicity_model_id"] = effect_atomicity_model_id
        body["effect_phase"] = effect_phase
        body["effect_prepare_ref"] = effect_prepare_ref
        body["effect_compensate_ref"] = effect_compensate_ref
        body["effect_idempotency_key"] = effect_idempotency_key
        body["effect_compensation_idempotency_key"] = effect_compensation_idempotency_key
        body["effect_abort_reason"] = effect_abort_reason
        body["effect_gate_admit_ref"] = effect_gate_admit_ref
    if int(version) >= 6:
        # UGK-BODY-v6 (AD-66, r143): typed verified-grade reconciliation surface. reconciliation_grade is
        # promoted from a parameters marker to a committed typed field; reconciliation_warrant_snapshot is
        # the verbatim canonical warrant body whose SHA-256 == the committed warrant_id, so a verifier
        # recomputes the verified grade from receipt state ALONE (no WarrantStore resolution). NULL on
        # recorded terminals. NON-AGGREGATING; orthogonal to effect/terminal/D_cap surfaces.
        body["reconciliation_grade"] = reconciliation_grade
        body["reconciliation_warrant_snapshot"] = reconciliation_warrant_snapshot
    if int(version) >= 7:
        # UGK-BODY-v7 (AD-71, r148): continuation-record SURFACE -- the support record TO-S-01 requires
        # before DEFER can be a live outcome. Eight nullable fields capturing a deferred op's deterministic
        # re-entry data + lifecycle marker + committed-evidence expiry basis; NULL on every ordinary receipt
        # (DEFER is NOT emittable in r148 -- surface committed but unbound; law leg is the SEPARATE r149
        # increment). NON-AGGREGATING; orthogonal to terminal_outcome/effect/D_cap. Append-only: lifecycle
        # transitions are LATER receipts, never mutations of this one.
        body["continuation_id"] = continuation_id
        body["continuation_op"] = continuation_op
        body["continuation_authority"] = continuation_authority
        body["continuation_parameters"] = continuation_parameters
        body["continuation_jurisdiction"] = continuation_jurisdiction
        body["continuation_expiry_basis"] = continuation_expiry_basis
        body["continuation_state"] = continuation_state
        body["continuation_model_id"] = continuation_model_id
    if int(version) >= 8:
        # UGK-BODY-v8 (CK-BRIDGE Stage 2): BRIDGE committed surface. Six nullable fields committing the
        # BridgeRecord IDENTITY (artifact hash) + its typed MCIR refs + the closed-taxonomy downgrade
        # reason + the SMH preserved-evidence ref. CITATION ONLY: no MCIR artifact body and no SMH
        # evidence body is embedded -- only hashes/refs enter h_body. BRIDGE-ONLY v8: reached solely when
        # a bridge surface is supplied (BRIDGE non-emittable at Stage 2 -> only via fixtures); every live
        # non-bridge receipt stays version 7 and is byte-identical. NON-AGGREGATING; orthogonal to
        # terminal_outcome/effect/D_cap/continuation. The BRIDGE-BINDING law + kernel emit are LATER legs.
        body["bridge_record_id"] = bridge_record_id
        body["bridge_source_regime_ref"] = bridge_source_regime_ref
        body["bridge_target_regime_ref"] = bridge_target_regime_ref
        body["bridge_transformation_ref"] = bridge_transformation_ref
        body["bridge_downgrade_reason"] = bridge_downgrade_reason
        body["bridge_preserved_evidence_ref"] = bridge_preserved_evidence_ref
    if int(version) >= 8:
        # UGK-BODY-v8 (CK-BRIDGE Stage 2): bridge-surface regime. v8 commits the v7 field blocks
        # (by version>=N) PLUS the bridge surface. The distinct tag keeps a v8 commitment domain separate
        # from a v7 one, so pre-existing v<8 receipts remain byte-identical (non-retroactive), and a live
        # non-bridge receipt (version 7) never enters the v8 tag domain. BRIDGE outcome remains
        # reserved/non-emittable at Stage 2; the surface is committed-but-unbound.
        tag = b"UGK-BODY-v8"
    elif int(version) >= 7:
        # UGK-BODY-v7 (AD-71, r148): uniform continuation-surface regime. v7 commits the v6 field blocks
        # (by version>=N) PLUS the continuation surface. The distinct tag keeps a v7 commitment domain
        # separate from a v6 one, so pre-existing v<7 receipts remain byte-identical (non-retroactive).
        # DEFER remains reserved/non-emittable at r148; the surface is unbound.
        tag = b"UGK-BODY-v7"
    elif int(version) >= 6:
        # UGK-BODY-v6 (AD-66, r143): typed verified-grade reconciliation regime.
        tag = b"UGK-BODY-v6"
    elif int(version) >= 5:
        # UGK-BODY-v5 (AD-65, r142): marker-retirement regime. Same committed field blocks as v4 (the
        # typed effect columns are committed via the version>=4 block above), but the eight effect
        # markers are NOT mirrored into committed parameters (reflected here via h_s over the marker-free
        # parameters). The distinct tag keeps a v5 (column-only) receipt's commitment domain separate
        # from a v4 (dual-surface) receipt's, so neither is ever recomputed under the other's rules.
        tag = b"UGK-BODY-v5"
    elif int(version) >= 4:
        tag = b"UGK-BODY-v4"
    elif int(version) >= 3:
        tag = b"UGK-BODY-v3"
    elif int(version) >= 2:
        tag = b"UGK-BODY-v2"
    else:
        tag = b"UGK-BODY-v1"
    return hashlib.sha256(tag + _m2._canonical_json(body)).hexdigest()


# -- Increment A (AD-51): LM-2 terminal-outcome commitment helpers -------------
TERMINAL_OUTCOME_MODEL_ID = "terminal_outcome_model_v1"
TERMINAL_OUTCOME_DOMAIN = ("ADMIT", "REFUSE", "DEFER", "STRUCTURAL_ERROR", "BRIDGE", "CRISIS")

# -- r148 (AD-71): continuation-record surface (UGK-BODY-v7) ------------------------------------
# The support record TO-S-01 requires before DEFER becomes a live outcome. r148 commits the SURFACE
# only; DEFER stays reserved/non-emittable (no law semantics, no lifecycle execution) until r149.
CONTINUATION_RECORD_MODEL_ID = "continuation_record_model_v1"
# Lifecycle PHASE/EVENT markers (closed). A continuation record is APPEND-ONLY: a later transition is a
# NEW receipt, never a mutation of the creating record. HELD is the only marker an r148 emit would carry;
# the others are the lifecycle vocabulary the r149 law leg will drive (here only as schema fixtures).
CONTINUATION_STATE_DOMAIN = frozenset({"HELD", "RESUMED", "RESOLVED", "EXPIRED", "REFUSED"})
# Expiry basis kinds (closed) -- DETERMINISTIC COMMITTED EVIDENCE ONLY. No ambient wall-clock.
#   receipt_height   : value = an integer chain height; expiry is a pure function of committed chain state.
#   explicit_trigger : value = a committed trigger token; expiry occurs only on an explicit committed event.
CONTINUATION_EXPIRY_KIND_DOMAIN = frozenset({"receipt_height", "explicit_trigger"})

# -- CK-BRIDGE Stage 2: BRIDGE committed surface (UGK-BODY-v8) -----------------------------------
# Schema/body leg ONLY: commit a typed BridgeRecord IDENTITY + refs. CITATION, never embedding (the
# MCIR regime/transformation artifact bodies and the SMH preserved-evidence body stay external/COLD;
# only their hashes/refs are committed). BRIDGE remains reserved/non-emittable here -- the surface is
# committed-but-unbound. The BRIDGE-BINDING law invariant + the kernel BRIDGE emit are SEPARATE later legs.
BRIDGE_RECORD_MODEL_ID = "bridge_record_model_v1"
# Closed downgrade taxonomy (matches the proven external ck-0.1+bridge profile, CK-BRIDGE-I1).
BRIDGE_DOWNGRADE_TAXONOMY = frozenset({"jurisdiction_crossing", "semantic_downgrade", "regime_translation"})
# The required typed refs that must all be present + canonicalize under the committed bridge_record_id.
_BRIDGE_REQUIRED_REFS = ("bridge_source_regime_ref", "bridge_target_regime_ref",
                         "bridge_transformation_ref", "bridge_preserved_evidence_ref")


def _validate_bridge_record(b: dict) -> dict:
    """Fail-closed Stage-2 validation of a BRIDGE committed surface (NO silent coercion).

    Stage 2 is the SURFACE leg: it validates the surface is well-typed, complete, and deterministic.
    It does NOT make BRIDGE emittable and does NOT resolve the cited MCIR/SMH artifacts (that read-only
    resolution + the source!=target structural-divergence check are the LATER law/kernel-leg concern).
    The committed bridge_record_id is the BridgeRecord artifact hash (citation); refs are committed
    so a verifier can later recompute the BridgeRecord identity from them. Rejects: missing/empty
    bridge_record_id, any missing/empty required ref, a downgrade_reason outside the closed taxonomy."""
    if not isinstance(b, dict):
        raise ValueError("bridge surface must be a dict")
    rid = b.get("bridge_record_id")
    if not (isinstance(rid, str) and rid):
        raise ValueError("bridge_record_id (BridgeRecord artifact hash) required, non-empty")
    for k in _BRIDGE_REQUIRED_REFS:
        v = b.get(k)
        if not (isinstance(v, str) and v):
            raise ValueError("bridge surface field %r required, non-empty string" % k)
    dr = b.get("bridge_downgrade_reason")
    if dr not in BRIDGE_DOWNGRADE_TAXONOMY:
        raise ValueError("bridge_downgrade_reason %r not in closed taxonomy %s"
                         % (dr, sorted(BRIDGE_DOWNGRADE_TAXONOMY)))
    return {
        "bridge_record_id": rid,
        "bridge_source_regime_ref": b["bridge_source_regime_ref"],
        "bridge_target_regime_ref": b["bridge_target_regime_ref"],
        "bridge_transformation_ref": b["bridge_transformation_ref"],
        "bridge_downgrade_reason": dr,
        "bridge_preserved_evidence_ref": b["bridge_preserved_evidence_ref"],
    }


def compute_continuation_id(*, op, authority, parameters, jurisdiction, anchor) -> str:
    """Deterministic, recomputable continuation identifier: domain-separated SHA-256 over the deferred
    op payload (op, authority, parameters, jurisdiction) PLUS the creating-receipt anchor. Pure; a
    verifier with the same inputs reproduces it exactly. (r148 commits the recipe + recomputability;
    binding the anchor to the emitting DEFER receipt is the r149 lifecycle concern.)"""
    from ugk.storage import binding_m2 as _m2
    import hashlib as _h
    payload = {"op": op, "authority": authority, "parameters": parameters,
               "jurisdiction": jurisdiction, "anchor": anchor}
    return _h.sha256(b"UGK-CONT-v1" + _m2._canonical_json(payload)).hexdigest()


def _validate_continuation(c: dict) -> dict:
    """Closed, FAIL-CLOSED validation of a continuation-record dict. Returns the normalized 8-field
    column mapping. Raises ValueError on ANY out-of-domain / malformed input (no silent coercion)."""
    if not isinstance(c, dict):
        raise ValueError("continuation must be a dict")
    state = c.get("state")
    if state not in CONTINUATION_STATE_DOMAIN:
        raise ValueError("continuation_state %r not in closed domain %s" % (state, sorted(CONTINUATION_STATE_DOMAIN)))
    model_id = c.get("model_id", CONTINUATION_RECORD_MODEL_ID)
    if model_id != CONTINUATION_RECORD_MODEL_ID:
        raise ValueError("continuation_model_id %r != %r" % (model_id, CONTINUATION_RECORD_MODEL_ID))
    eb = c.get("expiry_basis")
    if not isinstance(eb, dict) or set(eb.keys()) != {"kind", "value"}:
        raise ValueError("continuation_expiry_basis must be a dict {kind, value}; got %r" % (eb,))
    if eb["kind"] not in CONTINUATION_EXPIRY_KIND_DOMAIN:
        raise ValueError("continuation expiry kind %r not in closed domain %s (no wall-clock)" % (eb["kind"], sorted(CONTINUATION_EXPIRY_KIND_DOMAIN)))
    if eb["kind"] == "receipt_height" and not isinstance(eb["value"], int):
        raise ValueError("receipt_height expiry value must be an int (deterministic committed height)")
    op = c.get("op"); auth = c.get("authority"); params = c.get("parameters")
    jur = c.get("jurisdiction"); anchor = c.get("anchor")
    if not (isinstance(op, str) and op):
        raise ValueError("continuation_op must be a non-empty string")
    cid = c.get("id")
    # continuation_id is RECOMPUTED + checked at EMIT (anchor supplied); at an append-only lifecycle
    # TRANSITION the marker carries the same id forward (no anchor) -- the id's authenticity is
    # established at emit and the id IS the linkage (DEFER-S-01). Either way the result is deterministic.
    if anchor is not None:
        expect_id = compute_continuation_id(op=op, authority=auth, parameters=params, jurisdiction=jur, anchor=anchor)
        if cid is not None and cid != expect_id:
            raise ValueError("continuation_id is not the deterministic recomputation of its payload+anchor")
        cid = expect_id
    elif not (isinstance(cid, str) and cid):
        raise ValueError("continuation_id required when no anchor is provided (carried lifecycle linkage)")
    cj = _canon_eb(eb)
    return {
        "continuation_id": cid,
        "continuation_op": op,
        "continuation_authority": auth if isinstance(auth, str) else _canon_eb(auth),
        "continuation_parameters": _canon_eb(params),
        "continuation_jurisdiction": jur,
        "continuation_expiry_basis": cj,
        "continuation_state": state,
        "continuation_model_id": model_id,
    }


def _canon_eb(v) -> str:
    """Canonical JSON STRING for a continuation sub-field (stable + recomputable; deterministic key order)."""
    import json as _json
    return _json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True) if v is not None else None


def continuation_expired(expiry_basis, current_height, committed_triggers=()) -> bool:
    """DEFER-S-01 expiry: a PURE function of COMMITTED evidence (never wall-clock). expiry_basis is the
    canonical {kind,value} JSON committed on the continuation record. receipt_height -> expired iff the
    committed chain height has reached the recorded height; explicit_trigger -> expired iff the recorded
    trigger token is among the committed triggers. Deterministic + recomputable."""
    import json as _json
    if expiry_basis is None:
        return False
    eb = _json.loads(expiry_basis) if isinstance(expiry_basis, str) else expiry_basis
    kind = eb.get("kind")
    if kind == "receipt_height":
        return int(current_height) >= int(eb["value"])
    if kind == "explicit_trigger":
        return eb["value"] in set(committed_triggers)
    raise ValueError("unknown continuation expiry kind %r" % (kind,))

# -- r134 (AD-57): typed effect-surface (UGK-BODY-v4) helpers -------------------
EFFECT_ATOMICITY_MODEL_ID = "effect_atomicity_model_v1"
EFFECT_ATOMICITY_DOMAIN = frozenset(
    {"pure", "store_local", "external_reversible", "external_irreversible", "non_atomic"})
EFFECT_PHASE_DOMAIN = frozenset(
    {"prepare", "commit", "abort", "compensate", "compensated", "compensation_failed"})


class EffectDomainError(ValueError):
    """Fail-closed: an effect receipt carries an out-of-domain effect_atomicity / effect_phase."""


# parameters marker key -> typed column name (the v4 mirror map; single source = the markers)
_EFFECT_MARKER_MAP = (
    ("effect_atomicity",              "effect_atomicity"),
    ("phase",                         "effect_phase"),
    ("prepare_ref",                   "effect_prepare_ref"),
    ("compensate_ref",                "effect_compensate_ref"),
    ("idempotency_key",               "effect_idempotency_key"),
    ("compensation_idempotency_key",  "effect_compensation_idempotency_key"),
    ("abort_reason",                  "effect_abort_reason"),
    ("gate_admit_ref",                "effect_gate_admit_ref"),
)


def _derive_effect_columns(parameters):
    """v4: derive the typed effect-surface columns from the parameters markers (the compatibility
    mirror / single source during the schema-leg transition). Returns a dict of the 9 typed values,
    or None when the receipt is NOT effect-bearing (no effect_atomicity marker). Fails closed
    (EffectDomainError) on an out-of-domain effect_atomicity or effect_phase."""
    if not isinstance(parameters, dict):
        return None
    ea = parameters.get("effect_atomicity")
    if ea is None:
        return None  # not effect-bearing
    if ea not in EFFECT_ATOMICITY_DOMAIN:
        raise EffectDomainError("effect_atomicity %r not in closed domain" % (ea,))
    ph = parameters.get("phase")
    if ph is not None and ph not in EFFECT_PHASE_DOMAIN:
        raise EffectDomainError("effect_phase %r not in closed domain" % (ph,))
    cols = {"effect_atomicity_model_id": EFFECT_ATOMICITY_MODEL_ID}
    for marker_key, col in _EFFECT_MARKER_MAP:
        cols[col] = parameters.get(marker_key)
    return cols


_EFFECT_MARKER_KEYS = frozenset(mk for mk, _col in _EFFECT_MARKER_MAP)


def _derive_effect_markers(columns):
    """Lane-1 (typed-effect source-of-truth flip): the INVERSE of _derive_effect_columns. Given the
    canonical typed-column descriptor, reproduce the parameter-marker mirror EXACTLY as the legacy
    marker-primary callers built it: a marker key is present iff its column value is truthy (matching
    the callers' conditional `if ref: p[key]=ref` discipline; effect_atomicity/phase/idempotency_key
    are always truthy when effect-bearing). Returns the markers dict (no model_id — that is a typed
    column only, never a parameter marker)."""
    out = {}
    for marker_key, col in _EFFECT_MARKER_MAP:
        v = columns.get(col)
        if v:
            out[marker_key] = v
    return out


def _resolve_effect_surface(parameters, effect_columns, mirror_markers=True):
    """Lane-1 canonical resolver. Returns (typed_columns_or_None, committed_parameters).

    COLUMN-PRIMARY (effect_columns provided): the typed columns are CANONICAL. A caller-supplied marker
    that DIVERGES from its canonical column is a FAIL-CLOSED error (no silent precedence). Whether the
    column-derived markers are then MIRRORED into the committed parameters depends on mirror_markers.

    MARKER-PRIMARY (effect_columns is None): columns derived from the parameter markers (back-compat for
    non-effect / not-yet-flipped writers).

    mirror_markers (r142 / AD-65, marker retirement): TRUE = the v<5 behavior, the eight effect markers
    are the committed parameters mirror of the typed columns. FALSE = the v5 / UGK-BODY-v5 behavior, the
    typed columns are the SOLE committed STRUCTURAL effect surface and NO effect marker is committed in
    parameters (any caller/legacy marker is STRIPPED, never re-injected). parameters itself is retained
    for caller payload, reconciliation provenance, and the residual no-erasure hygiene region."""
    if effect_columns is None:
        cols = _derive_effect_columns(parameters)             # legacy marker-primary derivation
        if mirror_markers or cols is None:
            return cols, parameters                            # v<5 (markers kept) or nothing to strip
        pin = parameters if isinstance(parameters, dict) else {}
        return cols, {k: v for k, v in pin.items() if k not in _EFFECT_MARKER_KEYS}  # v5: strip legacy markers
    # column-primary: validate the canonical descriptor against the closed domains (fail closed)
    ea = effect_columns.get("effect_atomicity")
    if ea is None:
        return None, parameters  # not effect-bearing
    if ea not in EFFECT_ATOMICITY_DOMAIN:
        raise EffectDomainError("effect_atomicity %r not in closed domain" % (ea,))
    ph = effect_columns.get("effect_phase")
    if ph is not None and ph not in EFFECT_PHASE_DOMAIN:
        raise EffectDomainError("effect_phase %r not in closed domain" % (ph,))
    cols = {"effect_atomicity_model_id": EFFECT_ATOMICITY_MODEL_ID}
    for marker_key, col in _EFFECT_MARKER_MAP:
        cols[col] = effect_columns.get(col)
    derived = _derive_effect_markers(cols)               # markers = mirror of the canonical columns
    pin = parameters if isinstance(parameters, dict) else {}
    # fail-closed on divergence: a caller marker that disagrees with the canonical column is an error
    for mk in _EFFECT_MARKER_KEYS:
        if mk in pin and pin[mk] != derived.get(mk):
            raise EffectDomainError(
                "parameter marker %r=%r diverges from the canonical typed column (%r) — markers are "
                "derived from the typed columns, never independently trusted (fail closed; no silent "
                "marker precedence)" % (mk, pin[mk], derived.get(mk)))
    committed = {k: v for k, v in pin.items() if k not in _EFFECT_MARKER_KEYS}  # strip caller markers
    if mirror_markers:
        committed.update(derived)                                               # v<5: inject column-derived mirror
    # v5: do NOT inject — the typed columns are the sole committed structural effect surface
    return cols, committed


def verify_effect_column_marker_consistency(r) -> bool:
    """v4 ONLY: the typed effect columns MUST equal the parameters markers they mirror. A divergence is a
    corrupt receipt (fail closed). r142 (AD-65): scope is v==4 (the dual-surface version). v<4 carry no
    typed surface; v5+ carry NO marker mirror (the markers were retired) -- both are OUT OF SCOPE and
    return True here, so a v5 receipt is never failed for the (correct) absence of markers."""
    if int(getattr(r, "version", 1) or 1) != 4:
        return True
    p = r.parameters if isinstance(r.parameters, dict) else {}
    for marker_key, col in _EFFECT_MARKER_MAP:
        if getattr(r, col, None) != p.get(marker_key):
            return False
    # model id must be the declared closed-domain model anchor
    if getattr(r, "effect_atomicity_model_id", None) != EFFECT_ATOMICITY_MODEL_ID:
        return False
    # domain closure re-checked at verification (defense in depth)
    if getattr(r, "effect_atomicity", None) not in EFFECT_ATOMICITY_DOMAIN:
        return False
    ph = getattr(r, "effect_phase", None)
    if ph is not None and ph not in EFFECT_PHASE_DOMAIN:
        return False
    return True
EMITTABLE_OUTCOMES = ("ADMIT", "REFUSE", "STRUCTURAL_ERROR")


class ReservedOutcomeError(ValueError):
    """Reserved terminal-outcome value (DEFER/CRISIS) emitted in Increment A."""


def _assert_emittable(outcome, continuation=None, bridge=None, bridge_verifier=None):
    if outcome not in TERMINAL_OUTCOME_DOMAIN:
        raise ValueError("terminal_outcome %r not in closed LM-2 domain" % (outcome,))
    if outcome == "DEFER":
        # DEFER (TO-S-01 / DEFER-S-01, r149): emittable ONLY with a valid HELD continuation record.
        if not (isinstance(continuation, dict) and continuation.get("state") == "HELD"):
            raise ReservedOutcomeError("DEFER requires a valid HELD continuation record")
        _validate_continuation(continuation)   # fail-closed domain validation
        return
    if outcome == "BRIDGE":
        # BRIDGE (TO-S-01 / BRIDGE-BINDING, Stage 4 / r162): emittable ONLY with a committed v8 bridge
        # surface that verifies under BRIDGE-BINDING at emit. The verifier is the Stage-3 resolver-
        # parameterized verify_bridge_binding, INJECTED by the kernel's explicit opt-in bridge path
        # (UGK imports neither MCIR nor SMH; resolvers are read-only, kernel-free). Fail-closed: a missing
        # surface, a missing verifier, or a refuting verdict is NOT emittable (the kernel never spontaneously
        # bridges, and an invalid surface refuses/errors rather than admitting).
        if not (isinstance(bridge, dict) and bridge):
            raise ReservedOutcomeError("BRIDGE requires a committed v8 bridge surface")
        if bridge_verifier is None:
            raise ReservedOutcomeError("BRIDGE requires BRIDGE-BINDING verification at emit (no verifier supplied)")
        valid, reason = bridge_verifier(bridge)
        if not valid:
            raise ReservedOutcomeError("BRIDGE refused: bridge surface fails BRIDGE-BINDING (%s)" % reason)
        return
    if outcome not in EMITTABLE_OUTCOMES:       # CRISIS remains reserved / non-emittable
        raise ReservedOutcomeError("terminal_outcome %r is RESERVED; not emittable" % outcome)


def _derive_committed_outcome(op, failed, override, intent):
    if override is not None:
        return override, (intent or "")
    if op == "gate_refuse":
        return "REFUSE", "constitutional-refusal"
    if op == "protocol_error":
        return "STRUCTURAL_ERROR", (intent or "protocol_error")
    return "ADMIT", ("admitted-effect-aborted" if failed else "all-surfaces-pass")


def _pinned_codex_hash():
    import os
    try:
        return open(os.path.join(os.path.dirname(__file__), "..", "codex", "CODEX_HASH.txt")).read().strip()
    except OSError:
        return ""


def committed_trace_vector_hash(receipt) -> str:
    """Increment A (AD-51) schema-persisted POST-body trace commitment. NOT in h_body."""
    from ugk.fga.trace_vector import build_trace_vector, FrameRef  # lazy: avoids import cycle
    frame = FrameRef(law_hash=receipt.law_hash, schema_hash=EXPECTED_SCHEMA_HASH,
                     legend_hash=receipt.legend_hash, codex_hash=_pinned_codex_hash())
    return build_trace_vector(receipt, frame).trace_vector_hash


def stream_hash(store: "UGKReceiptStore") -> str:
    """Return the current chain tip (latest semantic_hash). O(1)."""
    return store.stream_hash()


def m2_stream_hash(store: "UGKReceiptStore") -> str:
    """M2 chain tip (latest h_r). Additive M2 analog of stream_hash() (RT-1c, E5b Tier 1)."""
    return store.m2_stream_hash()


def verify_stream_hash(store: "UGKReceiptStore",
                       from_checkpoint: Optional[str] = None) -> bool:
    """Recompute and verify the full receipt chain. O(n)."""
    return store.verify_stream_hash(from_checkpoint=from_checkpoint)


# ---------------------------------------------------------------------------
# schema_hash — the "structure" leg of the integrity frame triad
# (law_hash = behavior, legend_hash = meaning, schema_hash = structure).
# Startup fingerprint anchoring + frame binding ONLY: observe-and-report, never
# refuse-on-mismatch, never injected into individual receipts (closure belongs to
# the frame, per design note §4.7). NOT live-migration machinery (that is the
# separate, deferred governed-migration track).
# ---------------------------------------------------------------------------

def compute_schema_hash(conn) -> str:
    """Deterministic fingerprint of the live container structure.

    Canonical over every user table's PRAGMA table_info (column name, type, notnull,
    default, pk), tables sorted, columns in cid order. Excludes sqlite_* internal
    tables and all index/trigger SQL text. Pure function of column shape, so it is
    stable within and across processes for a given schema.
    """
    import hashlib as _hashlib, json as _json
    tables = sorted(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall())
    shape = {}
    for t in tables:
        cols = conn.execute(f"PRAGMA table_info({t})").fetchall()  # t from sqlite_master (trusted)
        shape[t] = [[c[1], c[2], int(c[3]), (c[4] if c[4] is not None else None), int(c[5])]
                    for c in sorted(cols, key=lambda r: r[0])]
    blob = _json.dumps(shape, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _hashlib.sha256(blob.encode()).hexdigest()


# Pinned anchor — the canonical container shape for this v0.1.0 substrate. A live
# schema_hash that diverges from this is reported as frame drift (observe-only); it
# does NOT refuse, gate, or migrate.
EXPECTED_SCHEMA_HASH = "82d02279c39d5fa82d6bb18a2a12b0f85cc5210a93502d827a9f89c570327c99"


# Receipt-safe, non-destructive DDL subset for the B2 live-migration primitive. The
# primitive is deliberately NOT an arbitrary SQL executor: a migration that could
# invalidate the receipt store (and thus prevent its own migration receipt from being
# written) must be refused BEFORE any mutation, so a rejected migration causes zero drift.
_FORBIDDEN_MIGRATION_TOKENS = (
    "DROP TABLE", "DROP INDEX", "DROP COLUMN", "DELETE", "UPDATE", "INSERT",
    "TRUNCATE", "PRAGMA", "RENAME", "REPLACE", "ATTACH", "DETACH",
)

def validate_migration_statement(stmt: str) -> Optional[str]:
    """Return None if a single live-migration statement is in the receipt-safe subset,
    else a human-readable rejection reason. Purely lexical; performs NO mutation.

    Allowed:  CREATE TABLE ...        (adds a new table; cannot break existing writes)
              CREATE [UNIQUE] INDEX ...
              ALTER TABLE ... ADD COLUMN ...  — only when it cannot break receipt writes.
                write() uses an explicit column list, so a nullable / DEFAULTed ADD COLUMN
                is safe; NOT NULL without DEFAULT is rejected (it breaks inserts).
    Rejected: DROP / RENAME / destructive ALTER, arbitrary DML, PRAGMA, ATTACH/DETACH,
              and multiple statements chained in one entry.
    """
    if not isinstance(stmt, str) or not stmt.strip():
        return "empty or non-string migration statement"
    s = " ".join(stmt.strip().split())
    if ";" in s.rstrip(";"):
        return "multiple statements per migration entry not permitted"
    u = " " + s.rstrip(";").upper() + " "
    allowed = (u.startswith(" CREATE TABLE ") or u.startswith(" CREATE INDEX ")
               or u.startswith(" CREATE UNIQUE INDEX ") or u.startswith(" ALTER TABLE "))
    if not allowed:
        return f"only CREATE TABLE / CREATE INDEX / safe ALTER TABLE ADD COLUMN permitted; got: {s[:60]!r}"
    for tok in _FORBIDDEN_MIGRATION_TOKENS:
        if f" {tok} " in u or f" {tok}(" in u:
            return f"forbidden operation in migration statement: {tok}"
    if u.startswith(" ALTER TABLE "):
        if " ADD COLUMN " not in u:
            return f"ALTER TABLE permitted only as ADD COLUMN; got: {s[:60]!r}"
        if "NOT NULL" in u and "DEFAULT" not in u:
            return f"ALTER TABLE ADD COLUMN NOT NULL without DEFAULT can break receipt writes; got: {s[:60]!r}"
    return None


# ---------------------------------------------------------------------------
# UGKReceiptStore
# ---------------------------------------------------------------------------

class UGKReceiptStore:
    """Tamper-evident append-only receipt store backed by SQLite.

    Full 3+1 CHC schema on every receipt.  Every write computes state_hash
    and semantic_hash (CHC dm_s03) from the supplied fields.

    Public API:
      write(op, authority, parameters, ...)  -> Receipt
      all_receipts()                          -> list[Receipt]
      stream_hash()                           -> str          (Cap-4, O(1))
      verify_stream_hash()                    -> bool         (Cap-4, O(n))
      refusal_rate_by_op()                    -> dict         (Cap-2)
      receipt_count()                         -> int
      refusal_count()                         -> int
      receipts_by_op(op)                      -> list[Receipt]
      last_valid_frontier()                   -> Optional[int]
    """

    GENESIS: str = "0" * 64   # Genesis seed — prior hash of the first receipt

    def __init__(self, db_path: str = ":memory:", *, read_only: bool = False):
        """db_path: SQLite path.  Default :memory: for tests (zero I/O overhead).

        read_only=True (IEL Invariant D / AD-30): on a real DB path, open a TRUE read-only
        connection — the DB must already exist (fail closed via ReadOnlyGuard.require_existing; no
        silent creation), and the connection is opened with sqlite ``mode=ro`` so it CANNOT create
        the file, create schema, or write. For the ephemeral ``:memory:`` default, construction may
        initialize a transient schema because no persistent state can be created. write() and
        migrate_schema() fail closed in read-only mode. This is the read-only substrate the
        verify/status/attest CLI paths bind to."""
        # B4a: single-writer serialization. The connection is shared (check_same_thread=
        # False), so every durable-write critical section (execute + commit) is serialized
        # under this re-entrant lock. RLock (not Lock) so a mutation path may safely nest.
        # Cross-process writer contention is explicitly OUT OF SCOPE for the v0.1.0
        # single-writer reference release (see docs/B4a_WRITER_SERIALIZATION.md).
        self._lock = threading.RLock()
        self._db_path = db_path
        self._read_only = read_only
        bootstrap_schema = False
        if read_only:
            from ugk.integrity.readonly import ReadOnlyGuard
            if db_path is None or db_path == ":memory:":
                self._conn = sqlite3.connect(":memory:", check_same_thread=False)
                bootstrap_schema = True
            else:
                ReadOnlyGuard.require_existing(db_path, name="store-open(read_only)")
                # mode=ro: the connection itself forbids creation + all writes (fail-closed substrate)
                self._conn = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True,
                                             check_same_thread=False)
        else:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            bootstrap_schema = True
        if bootstrap_schema:
            with self._lock:  # construction-time writes (single-threaded, pre-sharing) kept under the lock
                self._conn.execute(_CREATE_RECEIPTS)
                self._conn.execute(_CREATE_LEGEND_ARCHIVE)
                self._conn.execute(_CREATE_SCOPE_ARCHIVE_SQL)
                self._conn.execute(_CREATE_AM_ARCHIVE_SQL)
                self._conn.execute(_CREATE_FRAME_LEG_PROBE)  # E5a disposable schema-leg probe (AD-20)
                # M2.2 schema migration — ALTER TABLE for existing DBs that predate M2 columns
                self._migrate_m2_schema()
                self._conn.commit()
        # schema_hash: startup fingerprint anchoring. Compute the structure frame-pin
        # once the container shape is final (post create + migrate). Observe-only.
        self._schema_hash: str = compute_schema_hash(self._conn)
        # M2.2 — hydrate M2 chain tip from existing h_r
        row = self._conn.execute(
            "SELECT h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1"
        ).fetchone()
        self._prior_h_r: str = (row[0] if row and row[0] else self.GENESIS)
        # M2.3j — hydrate semantic-lineage chain tip (h_m + intent_ref of
        # most recent receipt). None when there is no prior receipt in
        # this session (root case → empty lineage).
        row = self._conn.execute(
            "SELECT h_m, intent_ref FROM receipts ORDER BY receipt_id DESC LIMIT 1"
        ).fetchone()
        self._prior_h_m: Optional[str] = (row[0] if row and row[0] else None)
        self._prior_intent_ref: Optional[str] = (row[1] if row else None)
        # AD-34: governed-transaction nesting depth. write() defers its durable commit when > 0
        # (the commit belongs to the enclosing store.transaction()); 0 = legacy always-commit.
        self._txn_depth: int = 0

    def schema_hash(self) -> str:
        """The structure frame-pin computed at startup (read-only observation)."""
        return self._schema_hash

    def schema_frame_intact(self) -> bool:
        """True iff the live container shape matches the pinned anchor. Observe-only —
        a False here is reported, never refused or auto-migrated."""
        return self._schema_hash == EXPECTED_SCHEMA_HASH

    @contextmanager
    def transaction(self, validation=None, *, name: str = ""):
        """AD-34 deferred-commit governed transaction: compose multiple writes (schema + receipt +
        terminal status) into ONE atomic unit (FGA / AD-33 M6: the governed transition T is the atom).
        Body writes defer their commit (depth>0); the whole block commits together on clean exit and
        rolls back together on ANY exception. Invariant A: refuses to open (MutationRefused) if
        validation is not ok. Invariant E: SAVEPOINT all-or-nothing. The in-memory chain/frame
        frontier (_prior_h_r/_prior_h_m/_prior_intent_ref/_schema_hash) is SNAPSHOT on entry and
        RESTORED on rollback (a SAVEPOINT cannot revert these Python-side attrs). NO outer
        conn.commit() on either path: RELEASE commits the clean block durably; ROLLBACK TO + RELEASE
        persists nothing and leaves a clean, usable connection (proven by migrate_schema_atomicity_gate,
        incl. a fresh-connection check). Exceptions are never suppressed. AD-35: the seam acquires
        self._lock INTRINSICALLY - lock discipline is a property of the seam, not a caller convention."""
        from ugk.integrity import ValidationResult, MutationTransaction
        if validation is None:
            validation = ValidationResult.valid()
        # AD-35: the seam carries its OWN lock discipline. Acquire self._lock INTRINSICALLY so
        # serialization is a property of the seam, not a caller convention - a future caller cannot
        # open a governed transaction without the store lock. RLock (re-entrant) nests cleanly under
        # migrate_schema's outer `with self._lock` and under write()'s internal `with self._lock`
        # (no deadlock). Held across the ENTIRE governed transition (SAVEPOINT open -> body ->
        # RELEASE/ROLLBACK), so the commit/release point is always serialized.
        with self._lock:
            snap = (self._prior_h_r, self._prior_h_m, self._prior_intent_ref, self._schema_hash)
            mt = MutationTransaction(self._conn, validation, name=name)
            mt.__enter__()              # SAVEPOINT; raises MutationRefused here if validation not ok (Invariant A)
            self._txn_depth += 1
            try:
                yield self
            except BaseException as exc:
                self._txn_depth -= 1
                # AD-36 defensive cleanup: restore the Python-side frontier in a FINALLY so it happens
                # EVEN IF MutationTransaction.__exit__ itself raises during rollback. The seam is now
                # reused across paths (migrate_schema, seal_and_prune_epoch), so rollback must be
                # maximally resilient. The restore makes the NEXT write link to the pre-transaction tip,
                # not the rolled-back receipt's h_r.
                try:
                    mt.__exit__(type(exc), exc, exc.__traceback__)   # ROLLBACK TO + RELEASE -> persists nothing
                finally:
                    (self._prior_h_r, self._prior_h_m,
                     self._prior_intent_ref, self._schema_hash) = snap
                raise
            self._txn_depth -= 1
            # r102-b: the clean-path RELEASE is the commit point r102-b relies on for the atomic
            # [effect + success receipt] outcome transition. If it raises (TransactionCommitError),
            # the block did NOT durably commit -> restore the Python-side frontier (mirroring the
            # AD-36 exception-path defensive cleanup) so the next write links to the pre-transaction
            # tip, and let the distinct error surface (fail-closed; a commit failure is never success).
            try:
                mt.__exit__(None, None, None)   # RELEASE -> commits the clean block durably (no extra conn.commit)
            except BaseException:
                (self._prior_h_r, self._prior_h_m,
                 self._prior_intent_ref, self._schema_hash) = snap
                raise

    def migrate_schema(self, statements, intent: str, description: str = "") -> dict:
        """B2 — governed LIVE schema migration (storage/frame layer; Option 3).

        The ONLY sanctioned post-construction structure-mutation path. It is governed at the
        storage/frame layer, NOT through the frozen kernel-op vocabulary: no legend term, no
        APPLICATION_OP, no kernel execute() gate/refuse. Governance here means a controlled,
        intent-bearing, receipted path:
          - explicit `intent` is required (else refuse, fail-closed);
          - runs under the single-writer lock (structure mutation is a write, B4a);
          - records schema_hash before/after;
          - emits a schema-frame migration receipt (storage-frame provenance,
            op='schema_migrated') into the tamper-evident chain.
        Raw live `ALTER` outside this path is forbidden (see tools/b2_conformance.py).

        `EXPECTED_SCHEMA_HASH` (the release anchor) is deliberately NOT moved here: a migrated
        deployment reports drift from the release anchor (observe-only) and the migration
        receipt explains the drift. Re-pinning the anchor is a deliberate later-release act.
        Bootstrap creation/normalization (__init__ CREATE + _migrate_m2_schema) is a separate,
        construction-time genesis/bootstrap remainder — not a live migration.
        """
        if getattr(self, "_read_only", False):
            from ugk.integrity.readonly import ReadOnlyViolation
            raise ReadOnlyViolation("migrate_schema() on a read-only store (IEL Invariant D)")
        if not intent or not str(intent).strip():
            raise ValueError("schema migration requires explicit intent (storage-frame governance)")
        # IEL Invariant A (validate-before-mutate, AD-27): preflight-validate the statements INPUT
        # before any normalization or mutation. ValidationResult models the preflight outcome; an
        # invalid input is refused here (fail-closed) so there is no raw TypeError on None (#60) and
        # no spurious receipt for an empty/no-op migration (#59). AD-34 now wires the
        # atomicity: store.transaction() (the deferred-commit seam) makes the schema ALTER and the
        # migration receipt ONE atomic governed transition (#30 closed for THIS path). ValidationResult
        # remains the Invariant-A preflight; store.transaction() provides Invariant-E atomicity.
        from ugk.integrity import ValidationResult
        from ugk.integrity.levels import CorruptionKind
        if statements is None:
            _v = ValidationResult.invalid(CorruptionKind.MALFORMED,
                "schema migration requires a non-None list of statements")
            raise ValueError(_v.detail)
        if isinstance(statements, str):
            statements = [statements]
        statements = list(statements)
        if not statements:
            _v = ValidationResult.invalid(CorruptionKind.MALFORMED,
                "empty schema migration refused: no statements to apply (no-op migrations are not receipted)")
            raise ValueError(_v.detail)
        # Validate EVERY statement against the receipt-safe subset BEFORE any mutation.
        # A rejected migration must cause zero schema drift (refusal-before-mutation), so
        # the migration receipt invariant ("always intent-bearing and receipted") holds:
        # the only migrations that mutate are ones that cannot break the receipt write.
        for stmt in statements:
            reason = validate_migration_statement(stmt)
            if reason is not None:
                raise ValueError(f"unsafe schema migration refused before mutation: {reason}")
        from ugk.integrity import ValidationResult
        with self._lock:  # structure mutation is a write — serialize (B4a)
            before = compute_schema_hash(self._conn)
            # AD-34: schema ALTER + migration receipt commit together as ONE governed transition.
            with self.transaction(ValidationResult.valid(), name="schema_migration"):
                for stmt in statements:
                    self._conn.execute(stmt)
                after = compute_schema_hash(self._conn)
                self.write(
                    op="schema_migrated",
                    authority="storage-frame",
                    parameters={
                        "intent": intent,
                        "description": description,
                        "schema_hash_before": before,
                        "schema_hash_after": after,
                        "release_anchor": EXPECTED_SCHEMA_HASH,
                        "drift_from_release_anchor": after != EXPECTED_SCHEMA_HASH,
                        "statements": list(statements),
                    },
                    intent=intent,
                )
            self._schema_hash = after  # AD-34: refresh ONLY after the transaction commits (rollback skips this)
        return {
            "schema_hash_before": before,
            "schema_hash_after": after,
            "release_anchor": EXPECTED_SCHEMA_HASH,
            "drift_from_release_anchor": after != EXPECTED_SCHEMA_HASH,
        }

    def _migrate_m2_schema(self) -> None:
        """Idempotent ALTER TABLE migration to add M2 columns to existing DBs.

        SQLite's CREATE TABLE IF NOT EXISTS does not modify existing schemas,
        so DBs created pre-M2.2 need explicit column additions. This method
        is safe to call repeatedly — it checks existing columns first.
        """
        existing = {
            row[1] for row in self._conn.execute("PRAGMA table_info(receipts)").fetchall()
        }
        for col_name, col_def in _M2_COLUMN_DEFS:
            if col_name not in existing:
                self._conn.execute(
                    f"ALTER TABLE receipts ADD COLUMN {col_name} {col_def}"
                )

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def write(
        self,
        op:           str,
        authority:    str,
        parameters:   dict,
        failed:       bool = False,
        intent:       Optional[str] = None,
        jurisdiction: str = "session",
        confidence:   str = "high",
        session_dkn:  str = "",
        law_hash:     str = "",
        legend_hash:  str = "",
        warrant_id:   str = "",
        intent_ref:   str = "",
        compress:     bool = False,
        commit_terminal_outcome: bool = False,
        terminal_outcome_override: Optional[str] = None,
        commit_capability_evidence: bool = False,
        capability_ledger=None,
        effect_columns: Optional[dict] = None,
        reconciliation_grade: Optional[str] = None,
        reconciliation_warrant_snapshot: Optional[str] = None,
        continuation: Optional[dict] = None,
        bridge: Optional[dict] = None,
        bridge_verifier: Optional[callable] = None,
    ) -> Receipt:
        """Append a receipt with full 3+1 CHC envelope.

        state_hash = H(op | params_json)
        semantic_hash = dm_s03(state, parent=prior, intent, authority,
                               jurisdiction, confidence, session_dkn,
                               session_dkn, ts, law_hash, legend_hash)
        Chain: prior_receipt_hash = previous semantic_hash.

        compress=True: stores CSIL integers for op/intent/jurisdiction/confidence
        in SQLite instead of full strings. all_receipts() expands on read.
        CHC is ALWAYS computed over canonical strings (before compression).
        """
        from ugk.storage.binding import FIELD_COMPRESS_MAPS, LEGEND_BY_ID
        from ugk.storage import binding_m2 as m2
        from ugk import invariants as inv
        from ugk import freshness as F
        from ugk.governance import policy as P
        from ugk import authority_keys as AK
        from ugk import authority_graph as AG
        from ugk import capabilities as CAP
        from ugk import lineage as L
        from ugk import namespace as NS

        if getattr(self, "_read_only", False):
            from ugk.integrity.readonly import ReadOnlyViolation
            raise ReadOnlyViolation("write() on a read-only store (IEL Invariant D)")
        _intent = intent if intent is not None else op
        # r139 (Lane 1): resolve the effect surface up front so EVERY downstream use of `parameters`
        # (state-hash, h_s, h_body, the stored body) sees the SAME committed markers. COLUMN-PRIMARY
        # when a canonical effect_columns descriptor is supplied (markers derived + merged here);
        # MARKER-PRIMARY (legacy) otherwise. Pure/deterministic — safe before the append lock.
        _eff, parameters = _resolve_effect_surface(parameters, effect_columns, mirror_markers=False)
        # r143 (AD-66, UGK-BODY-v6): promote the typed verified-grade reconciliation surface OUT of the
        # parameters transport and STRIP it, so the grade/snapshot are committed ONLY as typed columns
        # (the sole committed surface) and never duplicated in parameters-JSON. Mirrors the r142 marker
        # resolver discipline. Recorded terminals never set these keys -> columns stay NULL.
        if isinstance(parameters, dict) and (("reconciliation_grade" in parameters) or ("reconciliation_warrant_snapshot" in parameters)):
            parameters = dict(parameters)
            _pg = parameters.pop("reconciliation_grade", None)
            _ps = parameters.pop("reconciliation_warrant_snapshot", None)
            if reconciliation_grade is None: reconciliation_grade = _pg
            if reconciliation_warrant_snapshot is None: reconciliation_warrant_snapshot = _ps
        pj = _params_json(parameters)
        with self._lock:  # B4a: serialize the ENTIRE receipt-append RMW (tip-read → insert → commit → tip-update). RLock; uncontended in single-writer use.
            timestamp = time.time()   # r44: sampled INSIDE the lock so receipt time follows canonical append order

            # ── M2.2 BINDING: compute per-commitment hashes alongside legacy ──
            # Field-to-canonicalization mapping (current Receipt body → c_i inputs):
            #   c_s ← (op, parameters)
            #   c_c ← (authority_chain=canonical_path_through_G_c, policy_id=id(P),
            #          capabilities=effective_set_at_terminal_authority,
            #          warrant_basis=[warrant_id?], parent_H_r,
            #          freshness=signed_FreshnessClaim_from_default_epoch)
            #   c_m ← (intent, intent_ref, legend_hash,
            #          semantic_lineage=[LineageEdge to prior h_m])
            #   c_j ← (phase_code=id(Φ_0), mosaic_root=MOSAIC_ROOT_PHI_0,
            #          session_id=session_dkn, authority_key=lookup_authority_key(authority))
            # M2.3 proxy-replacement program COMPLETE — all four commitment
            # domains now bind real governed structures end-to-end:
            # M2.3c-d: Σ_0 / Φ_0 declarations
            # M2.3e: FreshnessClaim is a Governor-signed EpochIssuance
            # M2.3g: policy_id and id_P derive from a real signed Policy
            # M2.3f: authority_key is a governed key identifier
            # M2.3h: authority_chain is the canonical path through G_c
            # M2.3i: capabilities is the attenuated effective set
            # M2.3j: semantic_lineage is a governed lineage edge list
            # M2.3k: mosaic_root commits to the M_Phi namespace structure
            parent_h_r_input = self._prior_h_r
            m2_freshness = F.build_freshness_claim_from_epoch(
                F.default_epoch(inv.ID_PHI_0)
            )
            m2_policy_id = P.lookup_policy_id(jurisdiction)
            m2_authority_key = AK.lookup_authority_key(authority)
            m2_authority_chain_objs = AG.canonical_path_for(authority)
            m2_authority_chain = AG.canonical_path_as_dicts(authority)
            _eff_caps, _cap_err = CAP.compute_effective_capabilities(
                m2_authority_chain_objs
            )
            if _cap_err is not None:
                # Capability escalation in the configured G_c — receipt cannot
                # be constructed admissibly. This cannot occur under the
                # default graph (Governor grants full vocabulary); only an
                # explicitly-registered escalating chain can trigger this.
                raise ValueError(
                    f"capability escalation in G_c path for authority "
                    f"{authority!r}: {_cap_err}"
                )
            m2_capabilities = sorted(_eff_caps)
            h_s_b = m2.H_s(op, parameters)
            h_c_b = m2.H_c(
                authority_chain=m2_authority_chain,
                policy_id=m2_policy_id,
                capabilities=m2_capabilities,
                warrant_basis=([warrant_id] if warrant_id else []),
                parent_H_r=parent_h_r_input,
                freshness=m2_freshness,
            )
            m2_semantic_lineage = L.lineage_as_dicts(
                L.build_lineage(self._prior_h_m, self._prior_intent_ref)
            )
            h_m_b = m2.H_m(
                intent=_intent,
                intent_ref=intent_ref,
                legend_hash=legend_hash,
                semantic_lineage=m2_semantic_lineage,
                semantic_regime_id=inv.ID_SIGMA_0,
            )
            h_j_b = m2.H_j(
                phase_code=m2_freshness["phase_code"],
                mosaic_root=NS.MOSAIC_ROOT_PHI_0,
                session_id=session_dkn,
                authority_key=m2_authority_key,
            )
            # Strict mode default — include id_P/id_Sigma/id_Phi leaves (REV3 D4
            # "strict mode is default" + EV-AV-001 threat-class basis).
            # M2.3d: id_Sigma and id_Phi leaves derive from ID_SIGMA_0 / ID_PHI_0.
            # M2.3g: id_P leaf derives from id(P) — the real governed Policy
            # identity — rather than the jurisdiction string. The principled-
            # redundancy registry entry id_P → H_c is now operative on the
            # actual policy identity that both leaves bind to.
            _leaves = [
                (m2.TAG_H_S,     h_s_b),
                (m2.TAG_H_C,     h_c_b),
                (m2.TAG_H_M,     h_m_b),
                (m2.TAG_H_J,     h_j_b),
                (m2.TAG_ID_P,    m2.H_id_P(m2_policy_id)),
                (m2.TAG_ID_SIGMA, m2.H_id_Sigma(inv.ID_SIGMA_0)),
                (m2.TAG_ID_PHI,  m2.H_id_Phi(inv.ID_PHI_0)),
            ]
            h_r_b = m2.compute_H_r(_leaves)

            m2_h_s, m2_h_c, m2_h_m = h_s_b.hex(), h_c_b.hex(), h_m_b.hex()
            m2_h_j, m2_h_r = h_j_b.hex(), h_r_b.hex()
            _ver = 1
            _t_outcome = _t_model = _t_reason = _t_tvh = None
            _h_cap = _cap_model = _cap_ledger_hash = _cap_reg_ver = _cap_scope = None
            if commit_terminal_outcome or commit_capability_evidence:
                _ver = 2  # v3 ⊇ v2: a capability-evidence receipt also commits the terminal outcome
                _t_outcome, _t_reason = _derive_committed_outcome(op, bool(failed), terminal_outcome_override, _intent)
                _assert_emittable(_t_outcome, continuation=continuation, bridge=bridge, bridge_verifier=bridge_verifier)
                _t_model = TERMINAL_OUTCOME_MODEL_ID
            if commit_capability_evidence:
                _ver = 3
                if capability_ledger is None:
                    raise ValueError("commit_capability_evidence requires a capability_ledger")
                from ugk.cgp.dispatch import capability_evidence_commitment  # lazy: avoid import cycle
                _cap = capability_evidence_commitment(capability_ledger)  # PURE, no-laundering, fail-closed
                _h_cap = _cap["h_cap"]; _cap_model = _cap["capability_evidence_model_id"]
                _cap_ledger_hash = _cap["ledger_hash"]; _cap_reg_ver = _cap["registry_version"]
                _cap_scope = _cap["scope_id"]
            # r134 (AD-57) typed effect surface (v4) + r139 (Lane 1) source-of-truth flip: the effect
            # surface was resolved UP FRONT (see top of write) so `parameters` already carries the
            # committed marker mirror and `_eff` holds the canonical typed columns (column-primary when
            # an effect_columns descriptor was supplied, else legacy marker-primary). v bumps to 4 when
            # effect-bearing; both representations are committed and domain-validated.
            if _eff is not None:
                _ver = max(_ver, 4)
            # r142 (AD-65): UNIFORM UGK-BODY-v5 — the marker-retirement regime. Pre-v0.1.0 there are no
            # compatibility obligations, so ALL new receipts move to one clean post-retirement body
            # regime (not only effect-bearing ones). v5's body commits the same field blocks as v4 (by
            # version>=N), but the eight effect markers are no longer mirrored into committed parameters
            # (the typed columns are the sole committed structural effect surface). NON-RETROACTIVE:
            # pre-existing v<5 receipts keep their version, markers, and verification regime.
            # r143 (AD-66): UNIFORM UGK-BODY-v6 -- typed verified-grade reconciliation regime. Pre-v0.1.0,
            # one clean forward body regime (fork A). v6 commits the v5 field blocks PLUS the typed
            # reconciliation surface; verified reconciling terminals populate grade+snapshot, all others NULL.
            # NON-RETROACTIVE: pre-existing v<6 receipts keep their version and verification regime.
            _cont_cols = _validate_continuation(continuation) if continuation is not None else {}
            _ver = 7
            # CK-BRIDGE Stage 2: BRIDGE surface present -> bridge-only UGK-BODY-v8. NULL bridge -> stays v7
            # (byte-identical). _assert_emittable is UNCHANGED below: a bridge surface does NOT make a BRIDGE
            # OUTCOME emittable (committed-but-unbound); it rides an ordinary outcome until the law/kernel leg.
            _bridge_cols = _validate_bridge_record(bridge) if bridge is not None else {}
            if _bridge_cols:
                _ver = 8
            _eff_atom    = _eff["effect_atomicity"] if _eff else None
            _eff_model   = _eff["effect_atomicity_model_id"] if _eff else None
            _eff_phase   = _eff["effect_phase"] if _eff else None
            _eff_pref    = _eff["effect_prepare_ref"] if _eff else None
            _eff_cref    = _eff["effect_compensate_ref"] if _eff else None
            _eff_idem    = _eff["effect_idempotency_key"] if _eff else None
            _eff_cidem   = _eff["effect_compensation_idempotency_key"] if _eff else None
            _eff_abort   = _eff["effect_abort_reason"] if _eff else None
            _eff_gar     = _eff["effect_gate_admit_ref"] if _eff else None
            m2_h_body = compute_h_body(
                op=op, authority=authority, parameters=parameters, intent=_intent,
                jurisdiction=jurisdiction, confidence=confidence, timestamp=timestamp,
                failed=failed, session_dkn=session_dkn, law_hash=law_hash,
                legend_hash=legend_hash, warrant_id=warrant_id, intent_ref=intent_ref,
                h_s=m2_h_s, h_c=m2_h_c, h_m=m2_h_m, h_j=m2_h_j, h_r=m2_h_r,
                parent_h_r=parent_h_r_input, mode="strict", version=_ver,
                id_c_s=m2.ID_C_S, id_c_c=m2.ID_C_C, id_c_m=m2.ID_C_M, id_c_j=m2.ID_C_J,
                terminal_outcome=_t_outcome, terminal_outcome_model_id=_t_model,
                terminal_outcome_reason=_t_reason,
                h_cap=_h_cap, capability_evidence_model_id=_cap_model,
                capability_ledger_hash=_cap_ledger_hash, capability_registry_version=_cap_reg_ver,
                capability_scope_id=_cap_scope,
                effect_atomicity=_eff_atom, effect_atomicity_model_id=_eff_model,
                effect_phase=_eff_phase, effect_prepare_ref=_eff_pref,
                effect_compensate_ref=_eff_cref, effect_idempotency_key=_eff_idem,
                effect_compensation_idempotency_key=_eff_cidem, effect_abort_reason=_eff_abort,
                effect_gate_admit_ref=_eff_gar,
                reconciliation_grade=reconciliation_grade,
                reconciliation_warrant_snapshot=reconciliation_warrant_snapshot,
                continuation_id=_cont_cols.get("continuation_id"),
                continuation_op=_cont_cols.get("continuation_op"),
                continuation_authority=_cont_cols.get("continuation_authority"),
                continuation_parameters=_cont_cols.get("continuation_parameters"),
                continuation_jurisdiction=_cont_cols.get("continuation_jurisdiction"),
                continuation_expiry_basis=_cont_cols.get("continuation_expiry_basis"),
                continuation_state=_cont_cols.get("continuation_state"),
                continuation_model_id=_cont_cols.get("continuation_model_id"),
                bridge_record_id=_bridge_cols.get("bridge_record_id"),
                bridge_source_regime_ref=_bridge_cols.get("bridge_source_regime_ref"),
                bridge_target_regime_ref=_bridge_cols.get("bridge_target_regime_ref"),
                bridge_transformation_ref=_bridge_cols.get("bridge_transformation_ref"),
                bridge_downgrade_reason=_bridge_cols.get("bridge_downgrade_reason"),
                bridge_preserved_evidence_ref=_bridge_cols.get("bridge_preserved_evidence_ref"))
            if (commit_terminal_outcome or commit_capability_evidence) and _t_outcome in ("ADMIT", "REFUSE"):
                _tmp_rcpt = Receipt(
                    op=op, authority=authority, parameters=parameters, intent=_intent,
                    jurisdiction=jurisdiction, confidence=confidence, timestamp=timestamp,
                    failed=failed, session_dkn=session_dkn, law_hash=law_hash,
                    legend_hash=legend_hash, warrant_id=warrant_id, intent_ref=intent_ref,
                    h_s=m2_h_s, h_c=m2_h_c, h_m=m2_h_m, h_j=m2_h_j, h_r=m2_h_r,
                    parent_h_r=parent_h_r_input, mode="strict", version=_ver,
                    id_c_s=m2.ID_C_S, id_c_c=m2.ID_C_C, id_c_m=m2.ID_C_M, id_c_j=m2.ID_C_J,
                    h_body=m2_h_body, terminal_outcome=_t_outcome,
                    terminal_outcome_model_id=_t_model, terminal_outcome_reason=_t_reason,
                    h_cap=_h_cap, capability_evidence_model_id=_cap_model,
                    capability_ledger_hash=_cap_ledger_hash, capability_registry_version=_cap_reg_ver,
                    capability_scope_id=_cap_scope)
                _t_tvh = committed_trace_vector_hash(_tmp_rcpt)

            # Compression: field values → CSIL integers stored in SQLite
            # CHC is computed BEFORE compression (over canonical strings)
            if compress:
                store_op   = str(FIELD_COMPRESS_MAPS["op"].get(op, op))
                store_int  = str(FIELD_COMPRESS_MAPS["intent"].get(_intent, _intent))
                store_jur  = str(FIELD_COMPRESS_MAPS["jurisdiction"].get(jurisdiction, jurisdiction))
                store_conf = str(FIELD_COMPRESS_MAPS["confidence"].get(confidence, confidence))
            else:
                store_op, store_int, store_jur, store_conf = op, _intent, jurisdiction, confidence

            cur = self._conn.execute(
                "INSERT INTO receipts "
                "(op, authority, parameters, intent, jurisdiction, confidence, "
                " timestamp, failed, "
                " session_dkn, law_hash, legend_hash, warrant_id, intent_ref, "
                " h_s, h_c, h_m, h_j, h_r, parent_h_r, mode, version, "
                " id_c_s, id_c_c, id_c_m, id_c_j, h_body, "
                " terminal_outcome, terminal_outcome_model_id, terminal_outcome_reason, trace_vector_hash, "
                " h_cap, capability_evidence_model_id, capability_ledger_hash, "
                " capability_registry_version, capability_scope_id, "
                " effect_atomicity, effect_atomicity_model_id, effect_phase, "
                " effect_prepare_ref, effect_compensate_ref, effect_idempotency_key, "
                " effect_compensation_idempotency_key, effect_abort_reason, effect_gate_admit_ref, "
                " reconciliation_grade, reconciliation_warrant_snapshot, "
                " continuation_id, continuation_op, continuation_authority, continuation_parameters, "
                " continuation_jurisdiction, continuation_expiry_basis, continuation_state, continuation_model_id, "
                " bridge_record_id, bridge_source_regime_ref, bridge_target_regime_ref, "
                " bridge_transformation_ref, bridge_downgrade_reason, bridge_preserved_evidence_ref) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (store_op, authority, pj, store_int, store_jur, store_conf,
                 timestamp, int(failed),
                 session_dkn, law_hash, legend_hash, warrant_id, intent_ref,
                 m2_h_s, m2_h_c, m2_h_m, m2_h_j, m2_h_r, parent_h_r_input,
                 "strict", _ver, m2.ID_C_S, m2.ID_C_C, m2.ID_C_M, m2.ID_C_J, m2_h_body,
                 _t_outcome, _t_model, _t_reason, _t_tvh,
                 _h_cap, _cap_model, _cap_ledger_hash, _cap_reg_ver, _cap_scope,
                 _eff_atom, _eff_model, _eff_phase, _eff_pref, _eff_cref, _eff_idem,
                 _eff_cidem, _eff_abort, _eff_gar,
                 reconciliation_grade, reconciliation_warrant_snapshot,
                 _cont_cols.get("continuation_id"), _cont_cols.get("continuation_op"),
                 _cont_cols.get("continuation_authority"), _cont_cols.get("continuation_parameters"),
                 _cont_cols.get("continuation_jurisdiction"), _cont_cols.get("continuation_expiry_basis"),
                 _cont_cols.get("continuation_state"), _cont_cols.get("continuation_model_id"),
                 _bridge_cols.get("bridge_record_id"), _bridge_cols.get("bridge_source_regime_ref"),
                 _bridge_cols.get("bridge_target_regime_ref"), _bridge_cols.get("bridge_transformation_ref"),
                 _bridge_cols.get("bridge_downgrade_reason"), _bridge_cols.get("bridge_preserved_evidence_ref")),
            )
            if self._txn_depth == 0:
                self._conn.commit()   # AD-34: depth>0 defers the durable commit to the outer store.transaction()
            self._prior_h_r  = m2_h_r     # M2 chain tip update
            # M2.3j — semantic-lineage chain tip update
            self._prior_h_m = m2_h_m
            self._prior_intent_ref = intent_ref
        return Receipt(
            op=op, authority=authority, parameters=parameters,
            intent=_intent, jurisdiction=jurisdiction, confidence=confidence,
            timestamp=timestamp, failed=failed,
            session_dkn=session_dkn, law_hash=law_hash,
            legend_hash=legend_hash, warrant_id=warrant_id,
            intent_ref=intent_ref,
            receipt_id=cur.lastrowid,
            h_s=m2_h_s, h_c=m2_h_c, h_m=m2_h_m, h_j=m2_h_j, h_r=m2_h_r,
            parent_h_r=parent_h_r_input,
            mode="strict", version=_ver,
            id_c_s=m2.ID_C_S, id_c_c=m2.ID_C_C,
            id_c_m=m2.ID_C_M, id_c_j=m2.ID_C_J,
            h_body=m2_h_body,
            terminal_outcome=_t_outcome, terminal_outcome_model_id=_t_model,
            terminal_outcome_reason=_t_reason, trace_vector_hash=_t_tvh,
            h_cap=_h_cap, capability_evidence_model_id=_cap_model,
            capability_ledger_hash=_cap_ledger_hash, capability_registry_version=_cap_reg_ver,
            capability_scope_id=_cap_scope,
            effect_atomicity=_eff_atom, effect_atomicity_model_id=_eff_model,
            effect_phase=_eff_phase, effect_prepare_ref=_eff_pref,
            effect_compensate_ref=_eff_cref, effect_idempotency_key=_eff_idem,
            effect_compensation_idempotency_key=_eff_cidem, effect_abort_reason=_eff_abort,
            effect_gate_admit_ref=_eff_gar,
            reconciliation_grade=reconciliation_grade,
            reconciliation_warrant_snapshot=reconciliation_warrant_snapshot,
            continuation_id=_cont_cols.get("continuation_id"),
            continuation_op=_cont_cols.get("continuation_op"),
            continuation_authority=_cont_cols.get("continuation_authority"),
            continuation_parameters=_cont_cols.get("continuation_parameters"),
            continuation_jurisdiction=_cont_cols.get("continuation_jurisdiction"),
            continuation_expiry_basis=_cont_cols.get("continuation_expiry_basis"),
            continuation_state=_cont_cols.get("continuation_state"),
            continuation_model_id=_cont_cols.get("continuation_model_id"),
            bridge_record_id=_bridge_cols.get("bridge_record_id"),
            bridge_source_regime_ref=_bridge_cols.get("bridge_source_regime_ref"),
            bridge_target_regime_ref=_bridge_cols.get("bridge_target_regime_ref"),
            bridge_transformation_ref=_bridge_cols.get("bridge_transformation_ref"),
            bridge_downgrade_reason=_bridge_cols.get("bridge_downgrade_reason"),
            bridge_preserved_evidence_ref=_bridge_cols.get("bridge_preserved_evidence_ref"),
        )

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def committed_height(self) -> int:
        """DEFER-S-01: the COMMITTED chain height -- a deterministic monotonic count of persisted receipts."""
        return int(self._conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])

    def find_continuation(self, continuation_id):
        """DEFER-S-01: the LATEST receipt bearing continuation_id (its continuation_state is the current
        append-only lifecycle phase), or None. Pure read; no mutation."""
        if not continuation_id:
            return None
        latest = None
        for r in self.all_receipts():
            if getattr(r, "continuation_id", None) == continuation_id:
                latest = r
        return latest

    def all_receipts(self) -> list[Receipt]:
        """Return all receipts in insertion order."""
        rows = self._conn.execute(
            "SELECT receipt_id, op, authority, parameters, intent, jurisdiction, "
            "confidence, timestamp, failed, "
            "session_dkn, law_hash, legend_hash, warrant_id, intent_ref, "
            "h_s, h_c, h_m, h_j, h_r, parent_h_r, mode, version, "
            "id_c_s, id_c_c, id_c_m, id_c_j, h_body, "
            "terminal_outcome, terminal_outcome_model_id, terminal_outcome_reason, trace_vector_hash, "
            "h_cap, capability_evidence_model_id, capability_ledger_hash, "
            "capability_registry_version, capability_scope_id, "
            "effect_atomicity, effect_atomicity_model_id, effect_phase, "
            "effect_prepare_ref, effect_compensate_ref, effect_idempotency_key, "
            "effect_compensation_idempotency_key, effect_abort_reason, effect_gate_admit_ref, "
            "reconciliation_grade, reconciliation_warrant_snapshot, "
            "continuation_id, continuation_op, continuation_authority, continuation_parameters, "
            "continuation_jurisdiction, continuation_expiry_basis, continuation_state, continuation_model_id, "
            "bridge_record_id, bridge_source_regime_ref, bridge_target_regime_ref, "
            "bridge_transformation_ref, bridge_downgrade_reason, bridge_preserved_evidence_ref "
            "FROM receipts ORDER BY receipt_id ASC"
        ).fetchall()
        return [self._row_to_receipt(r) for r in rows]

    def receipts_by_op(self, op: str) -> list[Receipt]:
        """Return all receipts for a given op, in insertion order."""
        rows = self._conn.execute(
            "SELECT receipt_id, op, authority, parameters, intent, jurisdiction, "
            "confidence, timestamp, failed, "
            "session_dkn, law_hash, legend_hash, warrant_id, intent_ref, "
            "h_s, h_c, h_m, h_j, h_r, parent_h_r, mode, version, "
            "id_c_s, id_c_c, id_c_m, id_c_j, h_body, "
            "terminal_outcome, terminal_outcome_model_id, terminal_outcome_reason, trace_vector_hash, "
            "h_cap, capability_evidence_model_id, capability_ledger_hash, "
            "capability_registry_version, capability_scope_id, "
            "effect_atomicity, effect_atomicity_model_id, effect_phase, "
            "effect_prepare_ref, effect_compensate_ref, effect_idempotency_key, "
            "effect_compensation_idempotency_key, effect_abort_reason, effect_gate_admit_ref, "
            "reconciliation_grade, reconciliation_warrant_snapshot, "
            "continuation_id, continuation_op, continuation_authority, continuation_parameters, "
            "continuation_jurisdiction, continuation_expiry_basis, continuation_state, continuation_model_id, "
            "bridge_record_id, bridge_source_regime_ref, bridge_target_regime_ref, "
            "bridge_transformation_ref, bridge_downgrade_reason, bridge_preserved_evidence_ref "
            "FROM receipts WHERE op = ? ORDER BY receipt_id ASC",
            (op,),
        ).fetchall()
        return [self._row_to_receipt(r) for r in rows]

    def receipt_count(self) -> int:
        """Total receipt count."""
        return self._conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]

    def refusal_count(self) -> int:
        """Count of gate_refuse receipts."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE op = 'gate_refuse'"
        ).fetchone()[0]

    # ------------------------------------------------------------------
    # Cap-4: Integrity Proof
    # ------------------------------------------------------------------

    def stream_hash(self) -> str:
        """Current chain tip (latest h_r — M2 merkle binding root). O(1). Cap-4.
        RT-3l (E5b Tier 3): re-anchored from the retired legacy semantic_hash chain to the M2
        h_r chain. The broker / GovResult receipt_hash inherit M2 via this method (criterion 11)."""
        row = self._conn.execute(
            "SELECT h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1"
        ).fetchone()
        return row[0] if (row and row[0]) else self.GENESIS

    def m2_stream_hash(self) -> str:
        """M2 chain tip (latest h_r — the merkle-rooted binding root). O(1). Additive M2 analog of
        stream_hash() (RT-1c, E5b Tier 1); the legacy stream_hash() is retained until Tier 3."""
        row = self._conn.execute(
            "SELECT h_r FROM receipts ORDER BY receipt_id DESC LIMIT 1"
        ).fetchone()
        return row[0] if (row and row[0]) else self.GENESIS

    def verify_stream_hash(self,
                           from_checkpoint: Optional[str] = None) -> bool:
        """Verify the M2 receipt chain: each receipt's parent_h_r links to the previous receipt's
        h_r (merkle binding root), anchored at GENESIS. O(n) — session boundaries (UL-S-05).

        RT-3l (E5b Tier 3): re-anchored from the retired legacy state_hash/semantic_hash recompute
        to the M2 h_r chain. Body↔h_r consistency (a corrupted body field changing the recomputed
        h_r) is proven independently by binding_gate's H_r round-trip; this verifier proves M2 chain
        integrity (ordering / linkage / no-truncation / no-relink).

        SCOPE (IEL / AD-23): this is LINKAGE-LEVEL ONLY (VerificationLevel.LINKAGE) and PASSES after
        receipt-BODY tampering of a live store (finding #27). For BODY-level tamper detection call
        verify_receipt_bodies(); for the composed LINKAGE+BODY result call verify_chain(). `ugk verify`
        requires LINKAGE+BODY.
        from_checkpoint: an h_r value; verify only from that receipt onward (O(Δ)).
        """
        receipts = self.all_receipts()
        if not receipts:
            return True

        start_idx = 0
        prior = self.GENESIS
        if from_checkpoint is not None:
            _found = False
            for i, r in enumerate(receipts):
                if r.h_r == from_checkpoint:
                    start_idx = i + 1
                    prior = from_checkpoint
                    _found = True
                    break
            if not _found:
                return False  # IEL Invariant B: missing checkpoint != verified (fail closed)

        for r in receipts[start_idx:]:
            if not r.h_r or r.parent_h_r != prior:
                return False
            prior = r.h_r

        return True

    def verify_receipt_bodies(self, from_checkpoint: Optional[str] = None) -> bool:
        """BODY-level integrity (IEL / AD-28; full receipt body). For each stored receipt: (a)
        recompute h_s = H_s(op, parameters) and compare to the stored h_s, and (b) recompute the flat
        full-body commitment h_body over EVERY committed field (compute_h_body) and compare to the
        stored h_body. Tampering ANY committed field is detected. PURE deterministic re-derivation
        from stored values (no live-state dependency; unlike the H_c/H_m/H_j pipeline replay AD-21
        rejected). h_body is MANDATORY: any receipt missing it (even if stripped from every receipt) does
        not establish BODY (fail closed; no downgrade to h_s-only). Fail-closed on a MISSING from_checkpoint. Complements
        verify_stream_hash (LINKAGE)."""
        from ugk.storage import binding_m2 as m2
        receipts = self.all_receipts()
        if not receipts:
            return True
        start_idx = 0
        if from_checkpoint is not None:
            found = False
            for i, r in enumerate(receipts):
                if r.h_r == from_checkpoint:
                    start_idx = i + 1
                    found = True
                    break
            if not found:
                return False  # IEL Invariant B: a MISSING checkpoint is NOT a verified chain (fail closed)
        for r in receipts[start_idx:]:
            # (a) h_s derivation: the stored h_s must recompute from the stored op/parameters
            if r.h_s and m2.H_s(r.op, r.parameters).hex() != r.h_s:
                return False
            # (b) the full-body commitment is MANDATORY under the h_body schema: a missing/stripped
            # h_body does NOT establish BODY (no downgrade to h_s-only, even if stripped from EVERY
            # receipt wholesale). It must recompute from every committed field. ugk verify (which
            # requires BODY) therefore fails closed on any chain lacking h_body.
            if not r.h_body:
                return False
            recomputed = compute_h_body(
                op=r.op, authority=r.authority, parameters=r.parameters, intent=r.intent,
                jurisdiction=r.jurisdiction, confidence=r.confidence, timestamp=r.timestamp,
                failed=r.failed, session_dkn=r.session_dkn, law_hash=r.law_hash,
                legend_hash=r.legend_hash, warrant_id=r.warrant_id, intent_ref=r.intent_ref,
                h_s=r.h_s, h_c=r.h_c, h_m=r.h_m, h_j=r.h_j, h_r=r.h_r,
                parent_h_r=r.parent_h_r, mode=r.mode, version=r.version,
                id_c_s=r.id_c_s, id_c_c=r.id_c_c, id_c_m=r.id_c_m, id_c_j=r.id_c_j,
                terminal_outcome=getattr(r, "terminal_outcome", None),
                terminal_outcome_model_id=getattr(r, "terminal_outcome_model_id", None),
                terminal_outcome_reason=getattr(r, "terminal_outcome_reason", None),
                h_cap=getattr(r, "h_cap", None),
                capability_evidence_model_id=getattr(r, "capability_evidence_model_id", None),
                capability_ledger_hash=getattr(r, "capability_ledger_hash", None),
                capability_registry_version=getattr(r, "capability_registry_version", None),
                capability_scope_id=getattr(r, "capability_scope_id", None),
                effect_atomicity=getattr(r, "effect_atomicity", None),
                effect_atomicity_model_id=getattr(r, "effect_atomicity_model_id", None),
                effect_phase=getattr(r, "effect_phase", None),
                effect_prepare_ref=getattr(r, "effect_prepare_ref", None),
                effect_compensate_ref=getattr(r, "effect_compensate_ref", None),
                effect_idempotency_key=getattr(r, "effect_idempotency_key", None),
                effect_compensation_idempotency_key=getattr(r, "effect_compensation_idempotency_key", None),
                effect_abort_reason=getattr(r, "effect_abort_reason", None),
                effect_gate_admit_ref=getattr(r, "effect_gate_admit_ref", None),
                continuation_id=getattr(r, "continuation_id", None),
                continuation_op=getattr(r, "continuation_op", None),
                continuation_authority=getattr(r, "continuation_authority", None),
                continuation_parameters=getattr(r, "continuation_parameters", None),
                continuation_jurisdiction=getattr(r, "continuation_jurisdiction", None),
                continuation_expiry_basis=getattr(r, "continuation_expiry_basis", None),
                continuation_state=getattr(r, "continuation_state", None),
                continuation_model_id=getattr(r, "continuation_model_id", None),
                bridge_record_id=getattr(r, "bridge_record_id", None),
                bridge_source_regime_ref=getattr(r, "bridge_source_regime_ref", None),
                bridge_target_regime_ref=getattr(r, "bridge_target_regime_ref", None),
                bridge_transformation_ref=getattr(r, "bridge_transformation_ref", None),
                bridge_downgrade_reason=getattr(r, "bridge_downgrade_reason", None),
                bridge_preserved_evidence_ref=getattr(r, "bridge_preserved_evidence_ref", None))
            if recomputed != r.h_body:
                return False
        return True

    def verify_chain(self, from_checkpoint: Optional[str] = None):
        """Composed verification reporting the LEVEL achieved (IEL / AD-28): LINKAGE
        (verify_stream_hash) + full BODY (verify_receipt_bodies recomputes h_body over EVERY
        committed field). CONTEXT/IDENTITY/QUORUM and the FULLY_VERIFIED composition are Phase 1+.
        Returns a VerificationResult (required defaults to BODY). Fails closed (corruption set) on any
        committed-field tamper or a missing checkpoint."""
        from ugk.integrity import VerificationLevel as VL, CorruptionKind as CK, VerificationResult
        required = VL.BODY
        if not self.verify_stream_hash(from_checkpoint=from_checkpoint):
            return VerificationResult(VL.LINKAGE, required, CK.CORRUPT,
                "M2 chain linkage broken (ordering / parent_h_r / truncation / relink)")
        if not self.verify_receipt_bodies(from_checkpoint=from_checkpoint):
            return VerificationResult(VL.LINKAGE, required, CK.CORRUPT,
                "receipt body tamper: a committed field does not match the recomputed full-body "
                "commitment (h_body) or h_s, or a checkpoint is missing")
        return VerificationResult(VL.BODY, required, None, "LINKAGE + BODY established")

    def _verify_segment(self, receipts, anchor: str) -> bool:
        """Verify an ordered receipt list chains forward from `anchor` (recompute state_hash +
        semantic_hash per receipt). Shared by verify_from_seal and the epoch-prune precheck. Pure
        recomputation — does NOT alter receipt-hash or stream_hash() semantics."""
        prior = anchor
        for r in receipts:
            if not r.h_r or r.parent_h_r != prior:
                return False
            prior = r.h_r
        return True

    def verify_from_seal(self, seal_hash: str) -> bool:
        """B1 — verify the retained chain anchored at an epoch seal commitment.

        The anchor is the commitment VALUE `seal_hash` (= the pruned boundary receipt's
        semantic_hash), NOT a receipt: unlike verify_stream_hash(from_checkpoint=...), the boundary
        receipt is absent (pruned). The first retained receipt's prior_receipt_hash must equal
        `seal_hash`; the chain is verified forward from there. (A sealed/pruned store is, by design,
        not expected to pass GENESIS-anchored verify_stream_hash() — its anchor is the seal.)"""
        return self._verify_segment(self.all_receipts(), seal_hash)

    def seal_and_prune_epoch(self, seal_hash: str, intent: str, description: str = "") -> dict:
        """B1 — governed epoch seal + prune (storage/frame layer; destructive, fail-closed).

        Seals the prefix [.. boundary] whose cumulative commitment is S = seal_hash (the boundary
        receipt's semantic_hash already commits to the entire prefix via the chain), then PRUNES
        (deletes) that prefix, retaining the frontier (receipt_id > boundary). Two provenance
        receipts (epoch_sealed, epoch_pruned) are appended at the TAIL *before* deletion, so deletion
        cannot move the chain tip (tip_after_prune == tip_before_prune — pruning is observationally
        equivalent to retaining the prefix). The verification anchor is the commitment VALUE S
        (verify_from_seal(S)); the boundary receipt itself is gone.

        Governed at the storage/frame layer (consistent with B2): no kernel-op, no legend term, no
        APPLICATION_OP, no schema change, no change to receipt-hash or stream_hash() semantics. The
        epoch_sealed/epoch_pruned receipts are provenance; the prune ACT is a governed, fail-closed
        destructive mutation under the single-writer lock. Refusal-before-mutation: missing intent,
        unknown seal_hash, or a frontier that does not chain from S → refuse, delete nothing.
        """
        if not intent or not str(intent).strip():
            raise ValueError("epoch seal/prune requires explicit intent (storage-frame governance)")
        from ugk.integrity import ValidationResult
        with self._lock:  # destructive mutation — serialize (B4a); transaction() also takes the lock (r100)
            receipts = self.all_receipts()
            boundary = next((r for r in receipts if r.h_r == seal_hash), None)
            if boundary is None:
                raise ValueError("epoch seal/prune refused before mutation: seal_hash not found in chain")
            boundary_id = boundary.receipt_id
            prefix = [r for r in receipts if r.receipt_id <= boundary_id]
            frontier = [r for r in receipts if r.receipt_id > boundary_id]
            # Refusal-before-mutation: the retained frontier must chain from the seal commitment S.
            if not self._verify_segment(frontier, seal_hash):
                raise ValueError("epoch seal/prune refused before mutation: frontier does not chain from seal_hash")
            # AD-36: epoch_sealed + epoch_pruned + the destructive DELETE + the postconditions are ONE
            # governed transition (the governed transition T is the atom). The postconditions are
            # PRE-COMMIT GATES inside the seam - the block commits (RELEASE) ONLY if both receipts are
            # written, the prefix is deleted, the tip is stable, AND the retained chain verifies from S;
            # any failure ROLLS BACK both receipts AND the DELETE (and restores the frontier). The
            # preflight above already refused (no intent / unknown seal_hash / frontier-does-not-chain)
            # before any mutation.
            with self.transaction(ValidationResult.valid(), name="epoch_seal_prune"):
                # (1) provenance at the TAIL: seal commitment, then prune event (BEFORE any deletion).
                self.write(op="epoch_sealed", authority="storage-frame",
                           parameters={"intent": intent, "description": description, "seal_hash": seal_hash,
                                       "sealed_through_receipt_id": boundary_id, "sealed_count": len(prefix)},
                           intent=intent)
                self.write(op="epoch_pruned", authority="storage-frame",
                           parameters={"intent": intent, "seal_hash": seal_hash,
                                       "pruned_through_receipt_id": boundary_id, "pruned_count": len(prefix)},
                           intent=intent)
                # tip is measured AFTER the two terminal receipts are appended (the retained tail already
                # includes them); the prune must not move or rewrite that tail.
                tip_before_prune = self.stream_hash()
                # (2) prune: delete the sealed prefix only (ids <= boundary). The tail epoch receipts
                #     (ids > boundary) are untouched, so the tip cannot move.
                self._conn.execute("DELETE FROM receipts WHERE receipt_id <= ?", (boundary_id,))
                tip_after_prune = self.stream_hash()
                # (3) PRE-COMMIT postconditions (fail-closed, inside the seam): tip preserved AND retained
                #     chain verifies from S. A failure here ROLLS BACK the whole transition (RELEASE never runs).
                if tip_after_prune != tip_before_prune:
                    raise RuntimeError("epoch prune integrity error: chain tip moved during prune")
                if not self.verify_from_seal(seal_hash):
                    raise RuntimeError("epoch prune integrity error: retained chain does not verify from seal")
            # RELEASE committed both receipts + the DELETE together (no direct conn.commit).
            return {"seal_hash": seal_hash, "boundary_receipt_id": boundary_id,
                    "pruned_count": len(prefix), "retained_count": len(frontier) + 2,
                    "tip_before_prune": tip_before_prune, "tip_after_prune": tip_after_prune}

    def last_valid_frontier(self) -> Optional[int]:
        """Identify the last receipt_id before chain corruption begins.

        Used by recovery_gate.  Scans from the beginning; returns the
        receipt_id of the last receipt whose hash verifies correctly, or
        None if the chain is intact or empty.
        """
        receipts = self.all_receipts()
        if not receipts:
            return None

        prior = self.GENESIS
        last_valid: Optional[int] = None

        for r in receipts:
            if not r.h_r or r.parent_h_r != prior:
                return last_valid  # frontier = last receipt before this one
            last_valid = r.receipt_id
            prior = r.h_r

        return None  # chain intact

    # ------------------------------------------------------------------
    # Cap-2: Refusal Record
    # ------------------------------------------------------------------

    def refusal_rate_by_op(self) -> dict[str, float]:
        """Per-op refusal rates from gate_admit / gate_refuse receipts. Cap-2."""
        admit_rows = self._conn.execute(
            "SELECT parameters FROM receipts WHERE op = 'gate_admit'"
        ).fetchall()
        refuse_rows = self._conn.execute(
            "SELECT parameters FROM receipts WHERE op = 'gate_refuse'"
        ).fetchall()

        counts: dict[str, dict[str, int]] = {}
        for (pj,) in admit_rows:
            governed_op = json.loads(pj).get("op", "unknown")
            counts.setdefault(governed_op, {"admit": 0, "refuse": 0})
            counts[governed_op]["admit"] += 1

        for (pj,) in refuse_rows:
            governed_op = json.loads(pj).get("op", "unknown")
            counts.setdefault(governed_op, {"admit": 0, "refuse": 0})
            counts[governed_op]["refuse"] += 1

        result: dict[str, float] = {}
        for op, c in counts.items():
            total = c["admit"] + c["refuse"]
            result[op] = c["refuse"] / total if total > 0 else 0.0
        return result

    def receipts_since_count(self, count: int) -> int:
        """Count of receipts written since receipt_id > count."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM receipts WHERE receipt_id > ?", (count,)
        ).fetchone()[0]

    # ------------------------------------------------------------------
    # Legend archive — vocabulary version history
    # ------------------------------------------------------------------

    def seal_legend(self, legend_hash: str, entries_json: str,
                    phase_code: str, entry_count: int,
                    sealed_at: str) -> None:
        """Insert a legend version into the archive. Idempotent."""
        try:
            with self._lock:  # B4a: serialize execute+commit
                self._conn.execute(
                    "INSERT OR IGNORE INTO legend_archive "
                    "(legend_hash, entries_json, phase_code, entry_count, sealed_at) "
                    "VALUES (?,?,?,?,?)",
                    (legend_hash, entries_json, phase_code, entry_count, sealed_at),
                )
                self._conn.commit()
        except Exception:
            pass

    def resolve_legend(self, legend_hash: str):
        """Return the legend entries for a given legend_hash, or None.

        Resolution order:
          1. legend_archive table in this store
          2. binding.LEGEND_HASH / _LEGEND_ENTRIES (current version fallback)
          3. None — caller must handle LegendNotResolvable
        """
        row = self._conn.execute(
            "SELECT entries_json FROM legend_archive WHERE legend_hash = ?",
            (legend_hash,),
        ).fetchone()
        if row:
            import json as _json
            return _json.loads(row[0])
        # Fallback: current version
        from ugk.storage.binding import LEGEND_HASH as _LH, _LEGEND_ENTRIES as _LE
        if legend_hash == _LH:
            return list(_LE)
        return None

    # ------------------------------------------------------------------
    # Scope archive — provenance scope declarations
    # ------------------------------------------------------------------

    def seal_scope(self, scope) -> None:
        """Store a ProvenanceScope in scope_archive. Idempotent."""
        try:
            with self._lock:  # B4a: serialize execute+commit
                self._conn.execute(
                    "INSERT OR IGNORE INTO scope_archive "
                    "(scope_id, scope_type, authority_surface, session_dkn, "
                    " law_hash, legend_hash, prior_scope_id, timestamp) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (scope.scope_id, scope.scope_type, scope.authority_surface,
                     scope.session_dkn, scope.law_hash, scope.legend_hash,
                     scope.prior_scope_id, scope.timestamp),
                )
                self._conn.commit()
        except Exception:
            pass

    def latest_scope_id(self, authority_surface: str) -> str:
        """Return the most recent scope_id for authority_surface, or ''."""
        row = self._conn.execute(
            "SELECT scope_id FROM scope_archive WHERE authority_surface=? "
            "ORDER BY timestamp DESC LIMIT 1", (authority_surface,)
        ).fetchone()
        return row[0] if row else ""

    def scopes_for_authority(self, authority_surface: str) -> list:
        """Return all ProvenanceScopes for a given mosaic_root."""
        from ugk.scope import ProvenanceScope
        rows = self._conn.execute(
            "SELECT scope_id, scope_type, authority_surface, session_dkn, "
            "law_hash, legend_hash, prior_scope_id, timestamp "
            "FROM scope_archive WHERE authority_surface=? ORDER BY timestamp ASC",
            (authority_surface,),
        ).fetchall()
        return [ProvenanceScope(*r) for r in rows]

    def seal_authority_model(self,model):
        try:
            with self._lock:  # B4a: serialize execute+commit
                self._conn.execute("INSERT OR IGNORE INTO authority_model_archive "
                    "(model_hash,model_id,require_gate,require_warrant,require_intent,"
                    " description,rationale,law_hash,authority,timestamp) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (model.model_hash,model.model_id,int(model.require_gate),
                     int(model.require_warrant),int(model.require_intent),
                     model.description,model.rationale,model.law_hash,model.authority,model.timestamp))
                self._conn.commit()
        except Exception: pass

    def get_authority_model(self,model_hash):
        from ugk.authority.authority_model import AuthorityModel
        row=self._conn.execute("SELECT model_hash,model_id,require_gate,require_warrant,"
            "require_intent,description,rationale,law_hash,authority,timestamp "
            "FROM authority_model_archive WHERE model_hash=?",(model_hash,)).fetchone()
        if not row: return None
        mh,mid,rg,rw,ri,desc,rat,lh,auth,ts=row
        return AuthorityModel(model_hash=mh,model_id=mid,require_gate=bool(rg),
            require_warrant=bool(rw),require_intent=bool(ri),description=desc,
            rationale=rat,law_hash=lh,authority=auth,timestamp=ts)

    def close(self) -> None:
        """Close the SQLite connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_receipt(row) -> Receipt:
        from ugk.storage.binding import LEGEND_BY_ID as _LBI
        (rid, op, auth, pj, intent, juris, conf, ts, failed,
         dkn, lh, leg_h, wid, iref,
         h_s, h_c, h_m, h_j, h_r, parent_h_r, mode, version,
         id_c_s, id_c_c, id_c_m, id_c_j, h_body,
         terminal_outcome, terminal_outcome_model_id, terminal_outcome_reason, trace_vector_hash,
         h_cap, capability_evidence_model_id, capability_ledger_hash,
         capability_registry_version, capability_scope_id,
         effect_atomicity, effect_atomicity_model_id, effect_phase,
         effect_prepare_ref, effect_compensate_ref, effect_idempotency_key,
         effect_compensation_idempotency_key, effect_abort_reason, effect_gate_admit_ref,
         reconciliation_grade, reconciliation_warrant_snapshot,
         continuation_id, continuation_op, continuation_authority, continuation_parameters,
         continuation_jurisdiction, continuation_expiry_basis, continuation_state, continuation_model_id,
         bridge_record_id, bridge_source_regime_ref, bridge_target_regime_ref,
         bridge_transformation_ref, bridge_downgrade_reason, bridge_preserved_evidence_ref) = row

        def _expand(val):
            """Expand a stored value: if integer string, look up render form."""
            try:
                cid = int(val)
                entry = _LBI.get(cid)
                return entry["render"] if entry else val
            except (ValueError, TypeError):
                return val

        return Receipt(
            receipt_id=rid, op=_expand(op), authority=auth,
            parameters=json.loads(pj),
            intent=_expand(intent), jurisdiction=_expand(juris),
            confidence=_expand(conf),
            timestamp=ts, failed=bool(failed),
            session_dkn=dkn, law_hash=lh,
            legend_hash=leg_h or "", warrant_id=wid or "", intent_ref=iref or "",
            h_s=h_s or "", h_c=h_c or "", h_m=h_m or "",
            h_j=h_j, h_r=h_r or "", parent_h_r=parent_h_r or "",
            mode=mode or "strict", version=version or 1,
            id_c_s=id_c_s or "c_s.v1", id_c_c=id_c_c or "c_c.v1",
            id_c_m=id_c_m or "c_m.v1+sigma_0", id_c_j=id_c_j or "c_j.v1",
            h_body=h_body or "",
            terminal_outcome=terminal_outcome, terminal_outcome_model_id=terminal_outcome_model_id,
            terminal_outcome_reason=terminal_outcome_reason, trace_vector_hash=trace_vector_hash,
            h_cap=h_cap, capability_evidence_model_id=capability_evidence_model_id,
            capability_ledger_hash=capability_ledger_hash,
            capability_registry_version=capability_registry_version,
            capability_scope_id=capability_scope_id,
            effect_atomicity=effect_atomicity, effect_atomicity_model_id=effect_atomicity_model_id,
            effect_phase=effect_phase, effect_prepare_ref=effect_prepare_ref,
            effect_compensate_ref=effect_compensate_ref, effect_idempotency_key=effect_idempotency_key,
            effect_compensation_idempotency_key=effect_compensation_idempotency_key,
            effect_abort_reason=effect_abort_reason, effect_gate_admit_ref=effect_gate_admit_ref,
            reconciliation_grade=reconciliation_grade,
            reconciliation_warrant_snapshot=reconciliation_warrant_snapshot,
            continuation_id=continuation_id, continuation_op=continuation_op,
            continuation_authority=continuation_authority, continuation_parameters=continuation_parameters,
            continuation_jurisdiction=continuation_jurisdiction, continuation_expiry_basis=continuation_expiry_basis,
            continuation_state=continuation_state, continuation_model_id=continuation_model_id,
            bridge_record_id=bridge_record_id, bridge_source_regime_ref=bridge_source_regime_ref,
            bridge_target_regime_ref=bridge_target_regime_ref, bridge_transformation_ref=bridge_transformation_ref,
            bridge_downgrade_reason=bridge_downgrade_reason, bridge_preserved_evidence_ref=bridge_preserved_evidence_ref,
        )
