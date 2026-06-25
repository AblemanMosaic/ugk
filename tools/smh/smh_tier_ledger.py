"""SMH-I2 — Tier-Transition Receipt Ledger (SMH Track B, increment 2).

Implements the accepted SMH-P2 model: an EXTERNAL, append-only ledger of tier-transition
receipts. A receipt is emitted ONLY where canonical authority/provenance MOVES between
strata; ordinary HOT frontier movement and read-only cold access are RECEIPT-FREE (anti-spam).

Discipline (SMH-I2 scope / halt conditions):
  * Single GENERIC identity tag `smh.tier.transition.receipt.v1`; `movement_kind` inside the
    body distinguishes hydration / eviction / tier_transition / projection_rebuild /
    deep_export / restore. Per-type tags are reserved profile aliases only (not used for id).
  * receipt_id = H(tag, canonical_bytes(body)) via CK-CANON §9 (ck_canon) — reused, not forked.
  * Receipts CITE canonical artifacts via the SMH-P1 CanonicalSourceRef union (a byte archive
    is cited as smh_archive_ref, never dressed as ck_ref).
  * ANTI-SPAM: ordinary HOT frontier movement and read-only cold access emit NO receipt;
    rebuildable-projection eviction / generic tier_transition / projection_rebuild are OPTIONAL.
  * External to UGK; does NOT embed receipts in the UGK chain; does NOT move UGK law/schema/legend.
  * Timestamps are NON-identity-bearing (not in the body) — deterministic identity.
  * Does NOT claim UGK implements SMH.

Imports only ck_canon (canonicalizer) and smh_projection_registry (SMH-P1 ref union). No ugk.*.
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/claude/ck_impl")
import ck_canon
import smh_projection_registry as P1   # SMH-P1: ck_ref / smh_archive_ref / external_hash_ref

TIER_TRANSITION_TAG = "smh.tier.transition.receipt.v1"     # the ONE identity tag
RESERVED_PROFILE_ALIASES = (                               # reserved only — NOT used for receipt_id
    "smh.archive.hydration.v1", "smh.archive.eviction.v1", "smh.projection.rebuild.v1",
    "smh.archive.deepexport.v1", "smh.archive.restore.v1")

MOVEMENT_KINDS = {"hydration", "eviction", "tier_transition",
                  "projection_rebuild", "deep_export", "restore"}
TIERS = {"HOT", "WARM", "COLD", "DEEP"}

# Receipt classes (§2/§3)
REQUIRED = "receipt_required"
OPTIONAL = "receipt_optional"
NO_RECEIPT = "no_receipt"


class SMHError(Exception):
    pass


# ---------------------------------------------------------------- §2 receipt-required test
def classify_movement(movement: str, *, eviction_target: str = None) -> str:
    """The single test (§2): a receipt is required IFF canonical authority/provenance MOVES
    between strata. `movement` may be one of the six receipt movement_kinds OR a pseudo-movement
    ('hot_frontier_update', 'readonly_cold_access') that is RECEIPT-FREE."""
    if movement in ("hot_frontier_update", "readonly_cold_access"):
        return NO_RECEIPT                       # ordinary live computation / verification — anti-spam
    if movement == "hydration":
        return REQUIRED                         # COLD/DEEP -> WARM/HOT materialization
    if movement == "deep_export":
        return REQUIRED                         # COLD -> DEEP preservation (incl. release bundle)
    if movement == "restore":
        return REQUIRED                         # DEEP -> COLD/working
    if movement == "eviction":
        if eviction_target == "canonical":
            return REQUIRED                     # removing/relocating canonical material
        if eviction_target == "rebuildable_projection":
            return OPTIONAL                     # rebuildable from COLD; no canonical loss
        raise SMHError("eviction requires eviction_target in {canonical, rebuildable_projection}")
    if movement == "tier_transition":
        return OPTIONAL                         # generic optional
    if movement == "projection_rebuild":
        return OPTIONAL                         # no canonical authority moves; self-verifying envelope
    raise SMHError("unknown movement %r" % movement)


# ---------------------------------------------------------------- receipt body / envelope
def make_receipt_body(movement_kind: str, from_tier: str, to_tier: str,
                      subject_refs: list, prior_ref: str = None) -> dict:
    if movement_kind not in MOVEMENT_KINDS:
        raise SMHError("bad movement_kind %r" % movement_kind)
    if from_tier not in TIERS or to_tier not in TIERS:
        raise SMHError("bad tier")
    if not subject_refs:
        raise SMHError("at least one subject_ref required (fail-closed)")
    for r in subject_refs:
        if r.get("ref_type") not in ("ck_ref", "smh_archive_ref", "external_hash_ref"):
            raise SMHError("bad subject ref type")
    body = {
        "movement_kind": movement_kind,
        "from_tier": from_tier,
        "to_tier": to_tier,
        "subject_refs": list(subject_refs),
    }
    if prior_ref is not None:
        body["prior_ref"] = prior_ref          # ledger lineage link (optional)
    return body


def compute_receipt_id(body: dict) -> str:
    """receipt_id = H('smh.tier.transition.receipt.v1', canonical_bytes(body)) — CK-CANON §9.
    The body carries NO timestamp/iteration/runtime field, so identity is deterministic."""
    if "receipt_id" in body:
        raise SMHError("receipt_id must NOT be a member of the body (self-hash forbidden)")
    return ck_canon.domain_hash(TIER_TRANSITION_TAG, body)


def make_envelope(body: dict) -> dict:
    return {"receipt_id": compute_receipt_id(body), "receipt_body": body}


def verify_envelope(envelope: dict) -> dict:
    body = envelope.get("receipt_body"); rid = envelope.get("receipt_id")
    if not isinstance(body, dict) or not isinstance(rid, str):
        return {"valid": False, "finding": "corrupt_receipt", "detail": "malformed envelope"}
    try:
        recomputed = compute_receipt_id(body)
    except SMHError as e:
        return {"valid": False, "finding": "corrupt_receipt", "detail": str(e)}
    if recomputed != rid:
        return {"valid": False, "finding": "corrupt_receipt",
                "declared": rid, "recomputed": recomputed}
    return {"valid": True, "finding": "intact_receipt", "receipt_id": rid}


# ---------------------------------------------------------------- the external ledger
class TierTransitionLedger:
    """EXTERNAL, append-only ledger of tier-transition receipts (JSON-persisted). It records
    coarse, deliberate strata movements ONLY; it emits NO receipt for ordinary HOT frontier
    movement or read-only cold access (anti-spam). It is NOT the UGK receipt chain and embeds
    nothing into it."""

    def __init__(self, path: str = None):
        self._path = path
        self._chain = []
        if path and os.path.exists(path):
            self._chain = json.load(open(path)).get("receipts", [])

    def record_movement(self, movement: str, *, from_tier: str = None, to_tier: str = None,
                        subject_refs: list = None, eviction_target: str = None,
                        emit_optional: bool = False) -> dict:
        """Classify the movement and emit a receipt iff required (or optional+emit_optional).
        Returns {emitted, class, ...}. HOT frontier / read-only -> emitted=False (anti-spam)."""
        cls = classify_movement(movement, eviction_target=eviction_target)
        if cls == NO_RECEIPT:
            return {"emitted": False, "class": NO_RECEIPT,
                    "reason": "ordinary HOT frontier / read-only cold access — no tier receipt (anti-spam)"}
        if cls == OPTIONAL and not emit_optional:
            return {"emitted": False, "class": OPTIONAL, "reason": "optional movement not requested (anti-spam default)"}
        prior = self._chain[-1]["receipt_id"] if self._chain else None
        body = make_receipt_body(movement, from_tier, to_tier, subject_refs or [], prior_ref=prior)
        env = make_envelope(body)
        self._chain.append(env)
        self._flush()
        return {"emitted": True, "class": cls, "receipt_id": env["receipt_id"], "movement_kind": movement}

    def verify_chain(self) -> dict:
        """Each envelope self-verifies (receipt_id == H(body)) and prior_ref links the lineage."""
        prev = None
        for i, env in enumerate(self._chain):
            v = verify_envelope(env)
            if not v["valid"]:
                return {"valid": False, "at": i, "finding": v["finding"]}
            pr = env["receipt_body"].get("prior_ref")
            if pr != prev:
                return {"valid": False, "at": i, "finding": "broken_lineage", "expected": prev, "got": pr}
            prev = env["receipt_id"]
        return {"valid": True, "n": len(self._chain)}

    def receipts(self):
        return list(self._chain)

    def _flush(self):
        if self._path:
            json.dump({"model": "smh.tier.transition.ledger.v1", "receipts": self._chain},
                      open(self._path, "w"), indent=2, sort_keys=True)
