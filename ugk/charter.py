"""ugk/charter.py — DeploymentManifest: deployment identity declaration (444).

CHARTER-S-01: DeploymentManifest is content-addressed. governor_pubkey and
              phase_code are runtime-loaded from genesis/ — not hardcoded in source.
              Kernel fails closed without genesis/GENESIS_KEY.pub.
CHARTER-S-02: ugk charter is the founding constitutional act. --pubkey required.
              manifest_hash carried on every session_open receipt.

The charter is the act that makes an anonymous UGK binary into a specific governed
deployment. Before charter: no identity, fail-closed. After charter: governed.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ugk.storage.binding import canonical_json as _cj, mosaic_id as _mosaic_id, canonical_dkn as _cdkn


def _genesis_dir():
    """Lazy resolver — picks up UGK_GENESIS_DIR set after module import."""
    from ugk._paths import genesis_dir
    return genesis_dir()

_PRESET_DESCRIPTIONS = {
    "alt_prevention": "All three ALT disjuncts enforced (trace + causal necessity + will). φ=0 target.",
    "alt_trace":      "Gate and warrant required. Will vacuous. Disjuncts (a) and (b) enforced.",
    "trace_only":     "Receipt chain only. Conservative default for new deployments.",
    "custom":         "Caller-declared compliance flags.",
}


@dataclass(frozen=True)
class DeploymentManifest:
    """Content-addressed deployment identity declaration.

    governor_pubkey: Ed25519 public key hex (64 chars). Source of mosaic_root.
    phase_code:      Deployment type identifier. Scopes the governance namespace.
    jurisdiction:    Governance domain. Carried on receipts.
    authority_model: Compliance posture preset.
    mosaic_root:     Derived from governor_pubkey (stored for convenience).
    dimension_id:    Derived compound anchor (governor + phase; for CSH/genesis).
    manifest_hash:   SHA-256(canonical_json(body fields)).
    """
    manifest_hash:   str
    governor_pubkey: str
    phase_code:      str
    jurisdiction:    str
    authority_model: str
    amendment_model: str   # higher_root | self — declared amendment model (AMD-S-02)
    mosaic_root:     str   # SHA-256(governor_pubkey) — derived, stored for convenience
    dimension_id:    str   # SHA-256(phase_code ‖ governor_pubkey), ‖=U+2016 — compound anchor
    timestamp:       str

    @staticmethod
    def create(
        governor_pubkey: str,
        phase_code:      str = "ugk-substrate",
        jurisdiction:    str = "kernel",
        authority_model: str = "trace_only",
        amendment_model: str = "higher_root",
        timestamp:       Optional[str] = None,
    ) -> "DeploymentManifest":
        ts   = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        root = _mosaic_id(governor_pubkey)
        dim  = _cdkn(phase_code, governor_pubkey)
        body = {
            "amendment_model": amendment_model,
            "authority_model": authority_model,
            "dimension_id":    dim,
            "governor_pubkey": governor_pubkey,
            "jurisdiction":    jurisdiction,
            "mosaic_root":     root,
            "phase_code":      phase_code,
            "timestamp":       ts,
        }
        mh = hashlib.sha256(_cj(body)).hexdigest()
        return DeploymentManifest(
            manifest_hash=mh, governor_pubkey=governor_pubkey,
            phase_code=phase_code, jurisdiction=jurisdiction,
            authority_model=authority_model, amendment_model=amendment_model, mosaic_root=root,
            dimension_id=dim, timestamp=ts,
        )

    def verify_hash(self) -> bool:
        body = {
            "amendment_model": self.amendment_model,
            "authority_model": self.authority_model,
            "dimension_id":    self.dimension_id,
            "governor_pubkey": self.governor_pubkey,
            "jurisdiction":    self.jurisdiction,
            "mosaic_root":     self.mosaic_root,
            "phase_code":      self.phase_code,
            "timestamp":       self.timestamp,
        }
        return hashlib.sha256(_cj(body)).hexdigest() == self.manifest_hash

    def verify_derived_fields(self) -> bool:
        """Verify mosaic_root and dimension_id match governor_pubkey + phase_code."""
        return (
            _mosaic_id(self.governor_pubkey) == self.mosaic_root and
            _cdkn(self.phase_code, self.governor_pubkey) == self.dimension_id
        )

    def to_dict(self) -> dict:
        return {
            "amendment_model": self.amendment_model,
            "authority_model": self.authority_model,
            "dimension_id":    self.dimension_id,
            "governor_pubkey": self.governor_pubkey,
            "jurisdiction":    self.jurisdiction,
            "manifest_hash":   self.manifest_hash,
            "mosaic_root":     self.mosaic_root,
            "phase_code":      self.phase_code,
            "timestamp":       self.timestamp,
        }

    @staticmethod
    def load(genesis_dir: Optional[str] = None) -> Optional["DeploymentManifest"]:
        """Load from genesis/DEPLOYMENT_MANIFEST.json if present."""
        path = Path(genesis_dir or _genesis_dir()) / "DEPLOYMENT_MANIFEST.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return DeploymentManifest(**data)
        except Exception:
            return None


def write_charter_artifacts(
    manifest: DeploymentManifest,
    genesis_dir: Optional[str] = None,
    force: bool = False,
) -> tuple[Path, Path]:
    """Write genesis/GENESIS_KEY.pub and genesis/DEPLOYMENT_MANIFEST.json.

    Returns (pub_path, manifest_path). Raises FileExistsError if artifacts
    already exist and force=False.
    """
    gdir = Path(genesis_dir or _genesis_dir())
    gdir.mkdir(parents=True, exist_ok=True)
    pub_path  = gdir / "GENESIS_KEY.pub"
    mani_path = gdir / "DEPLOYMENT_MANIFEST.json"
    if not force:
        existing = [p for p in (pub_path, mani_path) if p.exists()]
        if existing:
            raise FileExistsError(
                f"Charter artifacts already exist: {[str(p) for p in existing]}. "
                f"Use --force to overwrite."
            )
    pub_path.write_text(manifest.governor_pubkey + "\n")
    mani_path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n")
    return pub_path, mani_path


__all__ = ["DeploymentManifest", "write_charter_artifacts"]
