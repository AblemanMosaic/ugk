"""ugk/amendment.py — AmendmentRecord: constitutional transition document (Grundnorm 444).

An AmendmentRecord documents a law_hash transition: what changed in invariants.py,
when, under whose authority. Stored in genesis/AMENDMENTS.json (append-only).

AMD-S-01: every law_hash transition has a corresponding AmendmentRecord;
the record is Governor-signed; the amendments file is append-only.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ugk.storage.binding import canonical_json as _cj


# E5a: lineage uniqueness/order is keyed on the successor FRAME (frame-triple), not just the
# law leg — admits a non-law leg move (e.g. schema) with law stationary. Feature-detect flag
# for cross-release verifiers (Proof Model B): present => is_admissible expects frame-triple
# prior_successor / existing_successors when supplied as tuples (law-hash callers still work).
_FRAME_KEYED_LINEAGE = True


@dataclass(frozen=True)
class AmendmentRecord:
    """Constitutional transition document.

    amendment_hash = SHA-256(canonical_json(body fields minus amendment_hash)).
    """
    amendment_hash:     str
    prior_law_hash:     str
    successor_law_hash: str
    invariants_added:   tuple    # invariant IDs added
    invariants_removed: tuple    # invariant IDs removed
    authority:          str      # MosaicID of authorizing Governor
    signature:          str      # Ed25519 sig over body (empty for Phase 7 dev path)
    phase_code:         str
    timestamp:          str
    amendment_kind:     str = "ordinary"  # genesis | ordinary — committed in signed/hashed body
    prior_legend_hash:     str = ""  # committed only when this record moves the legend leg
    successor_legend_hash: str = ""
    prior_schema_hash:     str = ""  # committed only when this record moves the schema leg
    successor_schema_hash: str = ""
    prior_amendment_hash:  str = ""  # R1: predecessor record's amendment_hash — committed only by
                                     # R1-and-later records (forward-only tamper-evident record-hash
                                     # chain, ADDITIVE to the authoritative law-hash lineage)

    @staticmethod
    def create(
        prior_law_hash:     str,
        successor_law_hash: str,
        invariants_added:   list,
        invariants_removed: list,
        authority:          str,
        phase_code:         str,
        signature:          str = "",
        timestamp:          Optional[str] = None,
        amendment_kind:     str = "ordinary",
        prior_legend_hash:     str = "",
        successor_legend_hash: str = "",
        prior_schema_hash:     str = "",
        successor_schema_hash: str = "",
        prior_amendment_hash:  str = "",
    ) -> "AmendmentRecord":
        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = {
            "amendment_kind":     amendment_kind,
            "authority":          authority,
            "invariants_added":   sorted(invariants_added),
            "invariants_removed": sorted(invariants_removed),
            "phase_code":         phase_code,
            "prior_law_hash":     prior_law_hash,
            "signature":          signature,
            "successor_law_hash": successor_law_hash,
            "timestamp":          ts,
        }
        for _k, _v in (("prior_legend_hash", prior_legend_hash), ("successor_legend_hash", successor_legend_hash),
                       ("prior_schema_hash", prior_schema_hash), ("successor_schema_hash", successor_schema_hash),
                       ("prior_amendment_hash", prior_amendment_hash)):
            if _v:
                body[_k] = _v
        ah = hashlib.sha256(_cj(body)).hexdigest()
        return AmendmentRecord(
            amendment_hash=ah,
            prior_law_hash=prior_law_hash,
            successor_law_hash=successor_law_hash,
            invariants_added=tuple(sorted(invariants_added)),
            invariants_removed=tuple(sorted(invariants_removed)),
            authority=authority,
            signature=signature,
            phase_code=phase_code,
            timestamp=ts,
            amendment_kind=amendment_kind,
            prior_legend_hash=prior_legend_hash, successor_legend_hash=successor_legend_hash,
            prior_schema_hash=prior_schema_hash, successor_schema_hash=successor_schema_hash,
            prior_amendment_hash=prior_amendment_hash,
        )

    def verify_hash(self) -> bool:
        body = {
            "amendment_kind":     self.amendment_kind,
            "authority":          self.authority,
            "invariants_added":   list(self.invariants_added),
            "invariants_removed": list(self.invariants_removed),
            "phase_code":         self.phase_code,
            "prior_law_hash":     self.prior_law_hash,
            "signature":          self.signature,
            "successor_law_hash": self.successor_law_hash,
            "timestamp":          self.timestamp,
        }
        for _k, _v in (("prior_legend_hash", self.prior_legend_hash), ("successor_legend_hash", self.successor_legend_hash),
                       ("prior_schema_hash", self.prior_schema_hash), ("successor_schema_hash", self.successor_schema_hash),
                       ("prior_amendment_hash", self.prior_amendment_hash)):
            if _v:
                body[_k] = _v
        return hashlib.sha256(_cj(body)).hexdigest() == self.amendment_hash


class AmendmentArchive:
    """Append-only archive of AmendmentRecords. Backed by genesis/AMENDMENTS.json."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._records: list[AmendmentRecord] = []
        if self._path.exists():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._path.read_text())
            for entry in data:
                self._records.append(AmendmentRecord(**{
                    k: tuple(v) if isinstance(v, list) else v
                    for k, v in entry.items()
                }))
        except Exception:
            pass

    def append(self, record: AmendmentRecord) -> None:
        self._records.append(record)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        import dataclasses
        self._path.write_text(
            json.dumps(
                [dataclasses.asdict(r) for r in self._records],
                indent=2, sort_keys=True
            )
        )

    def all_records(self) -> list[AmendmentRecord]:
        return list(self._records)

    def record_for_transition(self, prior: str, successor: str) -> Optional[AmendmentRecord]:
        for r in self._records:
            if r.prior_law_hash == prior and r.successor_law_hash == successor:
                return r
        return None

    @classmethod
    def open_from_genesis(cls, genesis_dir: str) -> "AmendmentArchive":
        return cls(str(Path(genesis_dir) / "AMENDMENTS.json"))


FRAME_LEGS = ("law_hash", "legend_hash", "schema_hash")


def signed_payload(authority, invariants_added, invariants_removed, phase_code,
                   prior_law_hash, successor_law_hash, amendment_kind, timestamp,
                   prior_legend_hash="", successor_legend_hash="",
                   prior_schema_hash="", successor_schema_hash="",
                   prior_amendment_hash="") -> bytes:
    """Canonical bytes the Governor signature commits (all body fields except signature and
    amendment_hash). amendment_kind is included — genesis vs ordinary is admissibility-relevant
    and must be signed, not annotated externally."""
    _p = {
        "amendment_kind":     amendment_kind,
        "authority":          authority,
        "invariants_added":   sorted(invariants_added),
        "invariants_removed": sorted(invariants_removed),
        "phase_code":         phase_code,
        "prior_law_hash":     prior_law_hash,
        "successor_law_hash": successor_law_hash,
        "timestamp":          timestamp,
    }
    for _k, _v in (("prior_legend_hash", prior_legend_hash), ("successor_legend_hash", successor_legend_hash),
                   ("prior_schema_hash", prior_schema_hash), ("successor_schema_hash", successor_schema_hash),
                   ("prior_amendment_hash", prior_amendment_hash)):
        if _v:
            _p[_k] = _v
    return _cj(_p)


def _mosaic(pubkey_hex: str) -> str:
    """MosaicID of a Governor pubkey = SHA-256(pubkey bytes). Matches AmendmentRecord.authority and
    SuccessorLineage.*_mosaic construction (no new cryptography; pure addressing)."""
    return hashlib.sha256(bytes.fromhex(pubkey_hex)).hexdigest()


def _authorized_keys(governor_pubkey: str, succession=None) -> list:
    """R2 / SUCC-S-01: ordered list of authorized Governor signing keys [K0, K1, ...] derived from the
    succession lineage, rooted at the installed/genesis key K0 = governor_pubkey.

    A successor key is authorized iff the link's predecessor_mosaic == SHA-256(current authorized key)
    AND its predecessor-signed succession_proof verifies under the current key (verify_succession).
    The walk STOPS at the first link that fails continuity or proof — an unlinked/forged successor is
    never added (fail-closed). With succession=None the set is exactly {K0}, preserving current
    behavior. Reuses SUCC-S-01 verify_succession; introduces no new cryptography.
    """
    keys = [governor_pubkey]
    if not succession:
        return keys
    chain = succession if isinstance(succession, (list, tuple)) else [succession]
    current = governor_pubkey
    for link in chain:
        if link.predecessor_mosaic != _mosaic(current):
            break  # chain discontinuity → fail-closed (stop authorizing further keys)
        if not link.verify_succession(current):
            break  # succession_proof does not verify under the predecessor key → fail-closed
        keys.append(link.successor_pubkey)
        current = link.successor_pubkey
    return keys


def is_admissible(record, prior_frame: dict, successor_frame: dict, governor_pubkey: str,
                  prior_successor: Optional[str] = None,
                  existing_successors: Optional[set] = None,
                  succession=None, record_is_historical: bool = False,
                  predecessor_amendment_hash: Optional[str] = None) -> tuple:
    """AMD-S-03 frame-general admissibility. prior_frame / successor_frame are dicts of the three
    frame legs (law_hash, legend_hash, schema_hash). The record commits the law leg; legs that did
    not move are verified equal directly between the two frames. Fail-closed. Returns (admitted, detail).

    Note on documentary vs authoritative: invariants_added / invariants_removed are DOCUMENTARY
    only. The authoritative transition proof is the successor-frame-leg hash match (condition 2),
    which uniformly covers additions, removals, AND statement modifications. A missing
    invariants_modified field is therefore NOT missing verification.
    """
    k = record.amendment_kind
    if k not in ("genesis", "ordinary"):
        return False, f"amendment_kind={k!r} invalid (must be genesis|ordinary)"
    if not record.verify_hash():
        return False, "amendment_hash does not match body (integrity)"
    # (1) prior frame — law leg committed; non-moving legs checked below
    if record.prior_law_hash != prior_frame["law_hash"]:
        return False, "prior_law_hash != c_n law leg"
    # (2) successor frame leg — AUTHORITATIVE (added/removed are documentary only)
    if record.successor_law_hash != successor_frame["law_hash"]:
        return False, ("successor_law_hash != c_{n+1} law leg — the successor law-frame hash is the "
                       "AUTHORITATIVE transition proof; invariants_added/removed are documentary only")
    # (2b) legend/schema legs — frame-general: a record may COMMIT a moved leg (prior/successor present),
    # else the leg must be unchanged. Law leg handled above; this generalizes admissibility to any leg.
    _legmap = {"legend_hash": (record.prior_legend_hash, record.successor_legend_hash),
               "schema_hash": (record.prior_schema_hash, record.successor_schema_hash)}
    for leg, (_cp, _cs) in _legmap.items():
        if _cs:  # record COMMITS this leg
            if _cp != prior_frame[leg]:
                return False, f"{leg}: committed prior != c_n {leg}"
            if _cs != successor_frame[leg]:
                return False, (f"{leg}: committed successor != c_{{n+1}} {leg} — successor-frame-leg hash "
                               f"is the authoritative transition proof")
        else:    # uncommitted leg must be unchanged
            if prior_frame[leg] != successor_frame[leg]:
                return False, (f"{leg} moved but the record commits no successor for it — a moved leg "
                               f"must be committed (frame-general admissibility)")
    # (3) Era-appropriate Governor authority + signature (AMD-S-03 condition 3, R2 / SUCC-S-01).
    #     The authorizing key must be the ERA-APPROPRIATE key authorized by the succession lineage:
    #     the genesis key K0, or a validly predecessor-signed successor. The record declares its signer
    #     by authority = SHA-256(signing pubkey); we resolve that key against the authorized set and
    #     verify the signature under THAT key. succession=None ⇒ authorized={K0} ⇒ identical to prior
    #     behavior. Strict era: a retired (non-active) authorized key may sign HISTORICAL records but is
    #     NOT authorized for NEW amendments after its successor became active.
    if not record.signature:
        return False, "no Governor signature (admission requires signed authority)"
    from ugk.governance.governor import verify_governor
    payload = signed_payload(record.authority, record.invariants_added, record.invariants_removed,
                             record.phase_code, record.prior_law_hash, record.successor_law_hash,
                             record.amendment_kind, record.timestamp,
                             record.prior_legend_hash, record.successor_legend_hash,
                             record.prior_schema_hash, record.successor_schema_hash,
                             record.prior_amendment_hash)
    authorized = _authorized_keys(governor_pubkey, succession)
    matches = [k for k in authorized if _mosaic(k) == record.authority]
    if not matches:
        return False, ("authority not authorized by the succession lineage — signing key is neither the "
                       "genesis key nor a validly predecessor-signed successor (forged/unlinked → fail-closed)")
    signing_key = matches[0]
    # strict era: the active key is the head of the authorized chain. A non-active (retired) authorized
    # key is admissible ONLY for a record explicitly attested as historical (pre-rotation); using a
    # retired key for a NEW amendment after rotation fails closed.
    active_key = authorized[-1]
    if signing_key != active_key and not record_is_historical:
        return False, ("retired era key used for a new amendment — after Governor key rotation only the "
                       "active successor key authorizes new amendments (historical records excepted)")
    if not verify_governor(signing_key, payload, record.signature):
        return False, "Governor signature does not verify under the resolved era-appropriate key"
    # (4) append-only lineage — GENERALIZED to the FRAME (frame-triple) key. The law-hash lineage is
    #     the authoritative special case; while only the law leg moves, frame-keying and law-keying are
    #     equivalent (legend/schema constant). Frame-keying is what admits a NON-LAW leg move with the
    #     law leg stationary (E5a: successor_law == prior_law, but the schema leg moves -> distinct
    #     successor FRAME -> admissible). Legacy callers passing law hashes get identical behavior.
    _succ_triple = (successor_frame.get("law_hash", ""), successor_frame.get("legend_hash", ""),
                    successor_frame.get("schema_hash", ""))
    _prior_triple = (prior_frame.get("law_hash", ""), prior_frame.get("legend_hash", ""),
                     prior_frame.get("schema_hash", ""))
    if prior_successor is not None:
        if isinstance(prior_successor, tuple):
            if _prior_triple != prior_successor:
                return False, "append-only lineage broken: prior frame != predecessor successor frame"
        elif record.prior_law_hash != prior_successor:
            return False, "append-only lineage broken: prior != predecessor successor"
    if existing_successors:
        if any(isinstance(e, tuple) for e in existing_successors):
            if _succ_triple in existing_successors:
                return False, "successor frame already present (not append-only)"
        elif record.successor_law_hash in existing_successors:
            return False, "successor already present (not append-only)"
    # (4b) R1 record-hash lineage — ADDITIVE and FORWARD-ONLY. A record that COMMITS prior_amendment_hash
    #      (R1-and-later) must match the predecessor record's amendment_hash, giving a tamper-evident
    #      record-hash chain on top of the authoritative law-hash lineage. Records that do NOT commit it
    #      (genesis + all pre-R1 records) are unaffected — no retroactive rehashing, no reinterpretation.
    if record.prior_amendment_hash:
        if predecessor_amendment_hash is None:
            return False, ("record commits prior_amendment_hash but no predecessor record was supplied "
                           "to verify the record-hash lineage")
        if record.prior_amendment_hash != predecessor_amendment_hash:
            return False, ("prior_amendment_hash != predecessor record amendment_hash — record-hash "
                           "lineage broken (additive tamper-evidence; law-hash lineage authoritative)")
    return True, f"ADMITTED ({k}) {record.prior_law_hash[:12]}->{record.successor_law_hash[:12]}"


__all__ = ["AmendmentRecord", "AmendmentArchive"]
