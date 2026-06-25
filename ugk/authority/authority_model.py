"""ugk/authority_model.py — AuthorityModel: declared governance compliance posture (444).

CM-S-01: Content-addressed. model_hash = SHA-256(canonical_json(body)).
CM-S-02: require_gate=True → APPLICATION_OPs without a gate raise KernelInternalOp.
CM-S-03: require_warrant=True → execute() without warrant_basis raises KernelInternalOp.
CM-S-04: model_hash on every session_open receipt; stored in authority_model_archive.

Presets: alt_prevention (all three disjuncts enforced) | alt_trace (gate+warrant) |
         trace_only (receipt chain only) | custom (caller-declared flags).
"""
from __future__ import annotations
import hashlib, sqlite3, time
from dataclasses import dataclass
from typing import Optional
from ugk.storage.binding import canonical_json as _cj

@dataclass(frozen=True)
class AuthorityModel:
    model_hash:str; model_id:str; require_gate:bool; require_warrant:bool
    require_intent:bool; description:str; rationale:str; law_hash:str
    authority:str; timestamp:str

    @staticmethod
    def create(model_id,require_gate,require_warrant,require_intent,
               description,rationale,law_hash,authority,timestamp=None):
        ts=timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
        body={"authority":authority,"description":description,"law_hash":law_hash,
              "model_id":model_id,"rationale":rationale,"require_gate":require_gate,
              "require_intent":require_intent,"require_warrant":require_warrant,"timestamp":ts}
        mh=hashlib.sha256(_cj(body)).hexdigest()
        return AuthorityModel(model_hash=mh,model_id=model_id,require_gate=require_gate,
            require_warrant=require_warrant,require_intent=require_intent,
            description=description,rationale=rationale,law_hash=law_hash,
            authority=authority,timestamp=ts)

    @staticmethod
    def alt_prevention(law_hash,authority):
        return AuthorityModel.create("alt_prevention",True,True,True,
            "ALT Prevention Theorem: all three disjuncts enforced. φ=0 target.",
            "Full ALT §11 compliance: trace + causal necessity + will.",law_hash,authority)

    @staticmethod
    def alt_trace(law_hash,authority):
        return AuthorityModel.create("alt_trace",True,True,False,
            "ALT trace + causal: gate and warrant required; will vacuous.",
            "Disjuncts (a) and (b) enforced; will layer not yet adopted.",law_hash,authority)

    @staticmethod
    def trace_only(law_hash,authority):
        return AuthorityModel.create("trace_only",False,False,False,
            "Trace only: receipt chain enforced. Substrate/test posture.",
            "Honest declaration for substrate usage and test environments.",law_hash,authority)

    @staticmethod
    def custom(law_hash,authority,require_gate=False,require_warrant=False,
               require_intent=False,description="Custom authority model.",
               rationale="Deployer-declared compliance flags."):
        return AuthorityModel.create("custom",require_gate,require_warrant,require_intent,
            description,rationale,law_hash,authority)

    def verify_hash(self):
        body={"authority":self.authority,"description":self.description,"law_hash":self.law_hash,
              "model_id":self.model_id,"rationale":self.rationale,"require_gate":self.require_gate,
              "require_intent":self.require_intent,"require_warrant":self.require_warrant,
              "timestamp":self.timestamp}
        return hashlib.sha256(_cj(body)).hexdigest()==self.model_hash


_CREATE_AM_ARCHIVE="""
CREATE TABLE IF NOT EXISTS authority_model_archive (
    model_hash TEXT PRIMARY KEY, model_id TEXT NOT NULL DEFAULT '',
    require_gate INTEGER NOT NULL DEFAULT 0, require_warrant INTEGER NOT NULL DEFAULT 0,
    require_intent INTEGER NOT NULL DEFAULT 0, description TEXT NOT NULL DEFAULT '',
    rationale TEXT NOT NULL DEFAULT '', law_hash TEXT NOT NULL DEFAULT '',
    authority TEXT NOT NULL DEFAULT '', timestamp TEXT NOT NULL DEFAULT ''
);"""

__all__=["AuthorityModel","_CREATE_AM_ARCHIVE"]
