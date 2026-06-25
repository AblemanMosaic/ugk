"""ugk/posture.py — GovernancePosture: Constitutional Governance Posture (444).

CGP-S-01: GovernancePosture is content-addressed. posture_hash = SHA-256(canonical_json(body)).
CGP-S-02: ugk health covers five sub-checks: chain, authority model, posture vector,
          disjunct coverage, and gate compliance.
CGP-S-03: Every gate has a GATE_GROUP annotation. Health report accounts for all gates.

The posture is both a queryable object and a receipted governance artifact.
'ugk posture --seal' enters the posture snapshot into the receipt chain.
"""
from __future__ import annotations
import hashlib, json, time
from dataclasses import dataclass, field
from typing import Optional
from ugk.storage.binding import canonical_json as _cj

@dataclass(frozen=True)
class GovernancePosture:
    posture_hash:     str
    authority_model:  str    # declared model_id
    phi:              float  # 0.0=fully constitutive, 1.0=fully ceremonial
    disjunct_a:       str    # "covered"|"partial"|"absent"
    disjunct_b:       str
    disjunct_c:       str
    require_gate:     bool
    require_warrant:  bool
    require_intent:   bool
    require_scoped_intent: bool
    matrix_cells:     str    # JSON-serialised dict
    chain_intact:     bool
    receipt_count:    int
    session_dkn:      str
    law_hash:         str
    computed_at:      str

    def verify_hash(self) -> bool:
        body = {
            "authority_model": self.authority_model, "chain_intact": self.chain_intact,
            "computed_at": self.computed_at, "disjunct_a": self.disjunct_a,
            "disjunct_b": self.disjunct_b, "disjunct_c": self.disjunct_c,
            "law_hash": self.law_hash, "matrix_cells": self.matrix_cells,
            "phi": self.phi, "receipt_count": self.receipt_count,
            "require_gate": self.require_gate, "require_intent": self.require_intent,
            "require_scoped_intent": self.require_scoped_intent,
            "require_warrant": self.require_warrant, "session_dkn": self.session_dkn,
        }
        return hashlib.sha256(_cj(body)).hexdigest() == self.posture_hash

    @classmethod
    def compute(cls, kernel) -> "GovernancePosture":
        """Compute the current governance posture from a kernel instance."""
        from ugk.schema import GOVERNANCE_OPS, _KERNEL_OPS, _UNIVERSAL_OPS
        from ugk.gate_probe import phi_score

        am = kernel._authority_model
        model_id = am.model_id if am else "undeclared"
        rg = am.require_gate if am else False
        rw = am.require_warrant if am else False
        ri = am.require_intent if am else False
        rsi = getattr(kernel, "_require_scoped_intent", False)

        chain_intact = kernel.store.verify_stream_hash() if kernel._session_dkn else True
        receipt_count = kernel.store.receipt_count() if kernel._session_dkn else 0
        law_hash = kernel._law_hash or ""
        session_dkn = kernel._session_dkn or ""

        # phi computation
        app_ops = {op: v for op, v in GOVERNANCE_OPS.items()
                   if op not in _KERNEL_OPS and op not in _UNIVERSAL_OPS}
        phi = phi_score(app_ops)

        # Disjunct status
        d_a = "covered" if chain_intact else "absent"
        d_b = ("covered" if rg and phi == 0.0 else
               "partial" if rg else "absent")
        d_c = ("covered" if ri else
               "partial" if getattr(kernel, "_will_store", None) is not None else "absent")

        # ALT section 8 matrix cells (honest-absent for cells outside kernel scope)
        cells = {
            "Identity_actor":      "constitutive-and-traced",
            "Identity_constitution":"constitutive-and-traced",
            "Identity_infra_ops":  "constitutive-and-traced",
            "Identity_app_ops":    "L-layer" if not app_ops else
                                   ("partial" if any(v.get("csil_id",0) for v in app_ops.values()) else "unguarded"),
            "Projection":          "constitutive-and-traced",
            "Binding":             "unguarded (honest-absent: kernel governs ops not bindings)",
            "Admission":           ("constitutive-and-traced" if rg and chain_intact
                                    else "traced-only" if chain_intact else "unguarded"),
            "Continuity_artifact": "constitutive-and-traced",
            "Continuity_actor":    "constitutive-and-traced",
            "Continuity_memory":   "unguarded (honest-absent)",
            "Procedure":           "constitutive-and-traced",
            "Execution":           "constitutive-and-traced",
            "Coverage":            ("constitutive-and-traced" if rg and phi == 0.0
                                    else "partial" if rg else "unguarded"),
        }
        cells_json = json.dumps(cells, sort_keys=True)

        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        body = {
            "authority_model": model_id, "chain_intact": chain_intact,
            "computed_at": ts, "disjunct_a": d_a, "disjunct_b": d_b, "disjunct_c": d_c,
            "law_hash": law_hash, "matrix_cells": cells_json,
            "phi": phi, "receipt_count": receipt_count,
            "require_gate": rg, "require_intent": ri, "require_scoped_intent": rsi,
            "require_warrant": rw, "session_dkn": session_dkn,
        }
        ph = hashlib.sha256(_cj(body)).hexdigest()
        return cls(posture_hash=ph, authority_model=model_id, phi=phi,
                   disjunct_a=d_a, disjunct_b=d_b, disjunct_c=d_c,
                   require_gate=rg, require_warrant=rw, require_intent=ri,
                   require_scoped_intent=rsi, matrix_cells=cells_json,
                   chain_intact=chain_intact, receipt_count=receipt_count,
                   session_dkn=session_dkn, law_hash=law_hash, computed_at=ts)

    def report(self, format: str = "text") -> str:
        cells = json.loads(self.matrix_cells)
        if format == "json":
            return json.dumps({
                "posture_hash": self.posture_hash, "authority_model": self.authority_model,
                "phi": self.phi,
                "disjuncts": {"a": self.disjunct_a, "b": self.disjunct_b, "c": self.disjunct_c},
                "enforcement": {"require_gate": self.require_gate, "require_warrant": self.require_warrant,
                                "require_intent": self.require_intent},
                "chain": {"intact": self.chain_intact, "receipts": self.receipt_count},
                "matrix": cells,
            }, indent=2)
        lines = [
            "UGK Constitutional Governance Posture",
            "=" * 42,
            f"authority_model:   {self.authority_model}",
            f"  require_gate:    {self.require_gate}",
            f"  require_warrant: {self.require_warrant}",
            f"  require_intent:  {self.require_intent}",
            f"",
            f"phi:               {self.phi:.2f}",
            f"",
            "Disjunct coverage:",
            f"  (a) trace:       {self.disjunct_a.upper()}   [chain_intact={self.chain_intact}, {self.receipt_count} receipts]",
            f"  (b) causal:      {self.disjunct_b.upper()}   [require_gate={self.require_gate}, phi={self.phi:.2f}]",
            f"  (c) will:        {self.disjunct_c.upper()}   [require_intent={self.require_intent}]",
            f"",
            "ALT section 8 matrix:",
        ]
        for cell, status in cells.items():
            lines.append(f"  {cell:<28} {status}")
        lines += ["", f"posture_hash:      {self.posture_hash[:16]}..."]
        return "\n".join(lines)


__all__ = ["GovernancePosture"]
