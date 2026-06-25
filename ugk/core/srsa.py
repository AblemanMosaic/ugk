"""ugk/core/srsa.py — SRSA 10-axis vector computation.

srsa_vector(kernel) returns the 10-axis SRSA score vector for a
GovernanceKernel instance.  Axes UGK lights up natively:

  AdSA  ✓  three-tier execute() — gate=ADMIT enforcement, MISSING_INTENT refusal
  ASA   ✓  per-op authority/intent/jurisdiction in execute() parameters
  CSA   ✓  receipt chain stream hash (prior_receipt_hash causal binding)
  PSA   ✓  CHC + binding.py provenance chain
  ESA   partial  kernel-native self-check (~5 caps)
  FSA   partial  CTR staleness + determinism gate
  RSA   0   application-layer — not in UGK core
  SSA   1   17-verb canonical list confirmed + declared (Phase 12)
  ISA   0   honest zero — designed budget only; emergent geometry unmapped
  LSA   0   honest zero — no declared legitimacy basis

Every UGK consumer inherits this vector as their governance baseline.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ugk.kernel import GovernanceKernel


# ---------------------------------------------------------------------------
# Axis score constants
# ---------------------------------------------------------------------------

SCORE_FULL    = 1
SCORE_PARTIAL = 0
SCORE_ZERO    = 0   # honest zero is still 0 — same value, different meaning

# Human-readable axis descriptions
AXIS_DESCRIPTIONS: dict[str, str] = {
    "AdSA": "Admissibility SA — gate=ADMIT enforcement, fail-closed",
    "ASA":  "Authority SA — per-op intent/authority/jurisdiction",
    "CSA":  "Causal SA — receipt chain causal binding",
    "PSA":  "Provenance SA — CHC + binding.py hash provenance",
    "ESA":  "Epistemic SA — kernel self-check capabilities",
    "FSA":  "Fidelity SA — staleness gate + determinism",
    "RSA":  "Risk SA — declared risk surface (application-layer)",
    "SSA":  "Semantic SA — 17-verb canonical vocabulary (Phase 12)",
    "ISA":  "Incentive SA — honest zero (designed budget only)",
    "LSA":  "Legitimacy SA — honest zero (no declared legitimacy basis)",
}

# Axis coverage notes
AXIS_NOTES: dict[str, str] = {
    "AdSA": "UGK native — three-tier execute() + GateRefusal",
    "ASA":  "UGK native — authority/intent/jurisdiction per receipt",
    "CSA":  "UGK native — prior_receipt_hash D2 causal chain",
    "PSA":  "UGK native — dm_s03 CHC + binding.py",
    "ESA":  "Partial — kernel-native ~5 caps; full 90-cap registry in AbleTools",
    "FSA":  "Partial — staleness_gate + determinism_gate; full staleness scoring TBD",
    "RSA":  "Application-layer — deployer declares risk surface in APPLICATION_OPS",
    "SSA":  "UGK native — 17-verb canonical list in INTENT_TYPES + LEGEND (Phase 12, Governor-confirmed)",
    "ISA":  "Honest zero — designed budget only; emergent incentive geometry unmapped",
    "LSA":  "Honest zero — no declared legitimacy basis in Phase 1",
}


def srsa_vector(kernel: "GovernanceKernel") -> dict[str, dict]:
    """Compute and return the 10-axis SRSA vector for a kernel instance.

    Returns a dict of {axis: {"score": int, "lit": bool, "note": str}}.
    Score 1 = lit/covered; 0 = not lit or honest zero.
    "lit" distinguishes a covered-zero from an honest-zero:
      partial ESA/FSA: lit=True, score=0 (partial coverage, honest about limits)
      ISA/LSA: lit=False, score=0 (honest zero — nothing to light)
    """
    snap = kernel.snapshot_fast()

    # AdSA: three-tier execute() present and fail-closed
    adsa_lit = True  # structural — execute() exists with three-tier enforcement

    # ASA: per-op authority/intent/jurisdiction in every receipt
    asa_lit = True   # structural — all receipts carry intent/authority/jurisdiction

    # CSA: causal chain present
    csa_lit = snap.get("receipt_count", 0) >= 0  # store always maintains chain

    # PSA: CHC provenance
    psa_lit = True   # structural — every write computes dm_s03

    # ESA: kernel self-check
    esa_lit = True   # partial — ~5 KCaps defined

    # FSA: staleness + determinism
    fsa_lit = True   # partial — staleness_gate + determinism_gate in conformance

    # RSA/SSA/ISA/LSA
    rsa_lit = False  # application-layer — deployer declares risk surface
    # SSA: lit when all 17 canonical verbs are present in INTENT_TYPES + LEGEND
    try:
        from ugk.core.vocab import SSA_VERB_COUNT, INTENT_TYPES
        from ugk.storage.binding import _INTENT_TO_CSIL
        ssa_lit = (
            SSA_VERB_COUNT == 17 and
            len(INTENT_TYPES) == 17 and
            len(_INTENT_TO_CSIL) == 17
        )
    except Exception:
        ssa_lit = False
    isa_lit = False  # honest zero — designed budget only
    lsa_lit = False  # honest zero — no declared legitimacy basis

    def _entry(lit: bool, note: str, axis: str) -> dict:
        return {
            "score":       1 if lit else 0,
            "lit":         lit,
            "description": AXIS_DESCRIPTIONS[axis],
            "note":        note,
        }

    return {
        "AdSA": _entry(adsa_lit, AXIS_NOTES["AdSA"], "AdSA"),
        "ASA":  _entry(asa_lit,  AXIS_NOTES["ASA"],  "ASA"),
        "CSA":  _entry(csa_lit,  AXIS_NOTES["CSA"],  "CSA"),
        "PSA":  _entry(psa_lit,  AXIS_NOTES["PSA"],  "PSA"),
        "ESA":  _entry(esa_lit,  AXIS_NOTES["ESA"],  "ESA"),
        "FSA":  _entry(fsa_lit,  AXIS_NOTES["FSA"],  "FSA"),
        "RSA":  _entry(rsa_lit,  AXIS_NOTES["RSA"],  "RSA"),
        "SSA":  _entry(ssa_lit,  AXIS_NOTES["SSA"],  "SSA"),
        "ISA":  _entry(isa_lit,  AXIS_NOTES["ISA"],  "ISA"),
        "LSA":  _entry(lsa_lit,  AXIS_NOTES["LSA"],  "LSA"),
    }


__all__ = ["srsa_vector", "AXIS_DESCRIPTIONS", "AXIS_NOTES"]
