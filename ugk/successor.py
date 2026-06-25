"""ugk/successor.py — SuccessorLineage: cryptographic succession proof (Grundnorm 444).

SUCC-S-01: SuccessorLineage proves mosaic_root_2 is the legitimate cryptographic
           successor of mosaic_root_1. succession_proof = Ed25519 sig from the
           predecessor key over canonical_json(body). Verifiable without the
           predecessor private key once issued.

Security posture note:
  True non-forgeability requires the successor keypair to be generated in a context
  the Coder cannot observe. The current succession (bootstrap → dev-successor) is
  Coder-seen on both sides — same posture as the bootstrap key.
  Production hardening: Governor generates new key off-artifact and provides only
  the public key + a pre-computed succession_proof signed off-session.

Key rotation activation:
  The SuccessorLineage PROVES the succession is authorized but does NOT activate it.
  To activate: update GOVERNOR_PUBKEY_HEX in kernel.py (444), re-seal genesis
  artifacts with the new key (same ceremony as Phase 11), and re-run the gate suite.
  The SuccessorLineage artifact is the governance record that authorizes the swap.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ugk.storage.binding import canonical_json as _cj
from ugk.governance.governor import verify_governor


@dataclass(frozen=True)
class SuccessorLineage:
    """Cryptographic succession proof.

    lineage_hash = SHA-256(canonical_json(all fields including succession_proof)).
    succession_proof = Ed25519 sig from predecessor key over canonical_json(body_fields).
    Verifiable by anyone holding the predecessor_pubkey.
    """
    lineage_hash:        str
    predecessor_mosaic:  str   # SHA-256(predecessor_pubkey)
    successor_mosaic:    str   # SHA-256(new_pubkey)
    successor_pubkey:    str   # new Governor Ed25519 pubkey hex
    succession_proof:    str   # Ed25519 sig from old key over body fields
    authority:           str   # old mosaic_root (self-attested)
    amendment_hash:      str   # references the AmendmentRecord for this rotation
    timestamp:           str

    def _body(self) -> dict:
        return {
            "amendment_hash":     self.amendment_hash,
            "authority":          self.authority,
            "predecessor_mosaic": self.predecessor_mosaic,
            "successor_mosaic":   self.successor_mosaic,
            "successor_pubkey":   self.successor_pubkey,
            "timestamp":          self.timestamp,
        }

    def verify_succession(self, predecessor_pubkey: str) -> bool:
        """Verify the succession_proof using the predecessor public key.

        This is the critical property: anyone who knows the predecessor pubkey
        can verify the succession without the private key.
        """
        try:
            return verify_governor(predecessor_pubkey, _cj(self._body()), self.succession_proof)
        except Exception:
            return False

    def verify_hash(self) -> bool:
        """Verify lineage_hash over the full content including succession_proof."""
        full = dict(self._body())
        full["succession_proof"] = self.succession_proof
        return hashlib.sha256(_cj(full)).hexdigest() == self.lineage_hash

    @staticmethod
    def load_from_genesis(genesis_dir: str) -> Optional["SuccessorLineage"]:
        """Load SUCCESSOR_LINEAGE.json from genesis/ if present."""
        path = Path(genesis_dir) / "SUCCESSOR_LINEAGE.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return SuccessorLineage(**data)
        except Exception:
            return None

    @staticmethod
    def load_from_package() -> Optional["SuccessorLineage"]:
        """Load from genesis/ relative to this module."""
        from ugk._paths import genesis_dir as _gd; genesis_dir = _gd()
        return SuccessorLineage.load_from_genesis(str(genesis_dir))


__all__ = ["SuccessorLineage"]
