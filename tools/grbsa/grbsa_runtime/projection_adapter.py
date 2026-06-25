"""grbsa_runtime.projection_adapter — ProjectionAdapter (GRBSA G4b).

Wraps the EXISTING CGProj fidelity surface as a receipt-bound continuation. Success semantics is
FIDELITY (each artifact byte-matches its fresh render and embeds the corpus content_hash) — NOT
anti-vacuity. This is the first adapter with a non-gate success predicate, the real test that the
domain boundary is the success semantics.

r28/r29 (de-tangled): the fidelity check is reconstructed IN-LANE from the import-clean projection
library — content_hash from the live `ugk.projections.hash.content_hash()` anchor, and each artifact's
embedded hash must match it (exactly the CGProj fidelity rule) — see `reconstructed_fidelity_compare`
below. No gate script is executed on any path; the CGProj Phase-4 gate is NOT modified.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import sys, os, hashlib
from typing import Optional, Callable

from .gate_adapter import ReceiptCore, ResultEnvelopeCore, PostureRefusal, _Trace
try:
    from ugk.scale.oracle import POSTURE_OPS as _POSTURE_OPS
except Exception:  # pragma: no cover
    _POSTURE_OPS = set()


# ---- Projection domain extensions ----
@dataclass(frozen=True)
class ProjectionReceipt:
    core: ReceiptCore
    projection_identity: str
    content_hash: str           # the receipt's view of the corpus anchor (why admissible to verify)
    domain: str = "projection"  # explicit category tag (Category-Separation)


@dataclass(frozen=True)
class ProjectionResultEnvelope:
    core: ResultEnvelopeCore
    per_artifact: tuple         # ((name, fidelity_ok), ...) — what the fidelity check found
    content_hash: str           # the envelope's observed anchor (what happened)
    domain: str = "projection"  # explicit category tag (Category-Separation)


# ---- success semantics: a PREDICATE over receipt+envelope (in neither core/extension) ----
def projection_success(receipt: ProjectionReceipt, envelope: ProjectionResultEnvelope) -> bool:
    """FIDELITY: no content_hash drift (envelope anchor == receipt anchor) AND every per-artifact
    fidelity_ok is true AND >=1 artifact compared (anti-vacuity floor)."""
    # Category-Separation guard: certifies ONLY the projection domain; mismatch => CLEAN False.
    if getattr(receipt, "domain", None) != "projection" or getattr(envelope, "domain", None) != "projection":
        return False
    if envelope.content_hash != receipt.content_hash:
        return False                      # content_hash drift
    if len(envelope.per_artifact) == 0:
        return False                      # vacuous: zero artifacts compared
    return all(ok for _, ok in envelope.per_artifact)


import re as _re
_HASH_RE = _re.compile(r"^content-hash:\s*([0-9a-f]{64})\s*$", _re.M)


def reconstructed_fidelity_compare(name, on_disk_bytes, G, H):
    """In-lane reconstruction of phase4's fidelity check — uses ONLY import-clean ugk.projections
    surfaces (G.generate_artifact, H.content_hash). Executes NO gate script. Behavior validated by the
    G4b gate's import-clean fidelity fixture (honest→ok, body/hash tamper→fail)."""
    expected_bytes = G.generate_artifact(name).encode("utf-8")
    byte_match = (on_disk_bytes == expected_bytes)
    text = on_disk_bytes.decode("utf-8", errors="replace")
    m = _HASH_RE.search(text)
    hash_wellformed = m is not None
    embedded = m.group(1) if m else None
    recomputed = H.content_hash()
    hash_match = (embedded == recomputed) if embedded else False
    return {"byte_match": byte_match, "embedded_hash": embedded, "recomputed_hash": recomputed,
            "hash_match": hash_match, "hash_wellformed": hash_wellformed}


class ProjectionAdapter:
    """Wraps the CGProj fidelity surface as a receipt-bound continuation.

    Test seams (used ONLY by the equivalence gate's negative controls):
      _emit_receipt_before_effect=False  -> NBER-1 violation
      _drift_content_hash=True           -> envelope anchor drifts from receipt anchor
      _suppress_artifact=<name>          -> drop one artifact's fidelity verdict
    """
    def __init__(self, repo: str, *, op: str = "projection_verify",
                 projection_identity: str = "cgproj/patterns+domain_mappings/v1",
                 _emit_receipt_before_effect: bool = True,
                 _drift_content_hash: bool = False,
                 _suppress_artifact: Optional[str] = None):
        self.repo = repo
        self.op = op
        self.projection_identity = projection_identity
        self._emit_receipt_before_effect = _emit_receipt_before_effect
        self._drift_content_hash = _drift_content_hash
        self._suppress_artifact = _suppress_artifact

    def _admissibility(self) -> tuple:
        if self.op in _POSTURE_OPS:
            raise PostureRefusal("adapter attempted posture op: " + self.op)
        return ("c_projection.v1",)

    def run(self) -> tuple:
        trace = _Trace()
        criteria = self._admissibility()                  # may raise PostureRefusal
        sys.path.insert(0, self.repo)
        from ugk.projections import generate as G, hash as H
        anchor = H.content_hash()                          # live anchor (Q2)
        # FIX B: in-lane reconstruction from import-clean ugk.projections — NO gate-script execution.
        gen_dir = os.path.join(self.repo, "ugk", "projections", "generated")

        def _mint_receipt():
            core = ReceiptCore(
                proposal={"op": self.op, "projection_identity": self.projection_identity},
                criteria=criteria,
                evaluation=("admissible",),
                authority={"warrant": "projection-corpus", "law_ref": "law_hash"},
                outcome="admitted",
                lineage={"prior": "0" * 64, "position": 0, "produces_effects": ()},
            )
            return ProjectionReceipt(core=core, projection_identity=self.projection_identity,
                                     content_hash=anchor)

        def _verify():
            trace.mark("effect_ran")
            per = []
            for name in G.ARTIFACTS:
                disk = open(os.path.join(gen_dir, name), "rb").read()
                r = reconstructed_fidelity_compare(name, disk, G, H)   # import-clean (Fix B)
                fid_ok = bool(r["byte_match"] and r["hash_match"] and r["hash_wellformed"])
                per.append((name, fid_ok))
            if self._suppress_artifact is not None:        # NEG seam
                per = [(n, ok) for (n, ok) in per if n != self._suppress_artifact]
            return per

        if self._emit_receipt_before_effect:
            trace.mark("receipt_minted")
            receipt = _mint_receipt()
            per = _verify()
        else:                                              # NEG seam: effect before receipt
            per = _verify()
            trace.mark("receipt_minted")
            receipt = _mint_receipt()

        env_anchor = anchor if not self._drift_content_hash else ("f" * 64)  # NEG seam: drift
        env = ProjectionResultEnvelope(
            core=ResultEnvelopeCore(
                status="pass" if all(ok for _, ok in per) else "fail",
                evidence_refs=tuple(n for n, _ in per),
                timing={},
                result_hash=hashlib.sha256(repr(tuple(per)).encode()).hexdigest(),
                lineage={"produced_effects": (), "delta": len(per)},
            ),
            per_artifact=tuple(per),
            content_hash=env_anchor,
        )
        return receipt, env, trace
