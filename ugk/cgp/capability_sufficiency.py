"""ugk/cgp/capability_sufficiency.py — D_cap sufficiency POLICY artifact (AD-68, Lane 2a).

PURE, TOTAL, DECLARATIVE policy over the EXISTING closed seven-verdict EvidenceArtifact
vocabulary (CTR-S-03; the same VERDICTS the CGP dispatcher emits). This artifact states WHAT
capability evidence is SUFFICIENT. It is consumed by NO decision path: D_cap remains recorded +
verified and OUTSIDE aggregate() / conjunctive_refusal_monotone_v1. Enforcement (a sibling refusal
precondition + the `insufficient-capability` refusal cause) is the SEPARATE Lane 2b increment; this
module opens NO refusal path and adds NO new refusal cause.

Policy (total over the closed vocabulary, default-deny):
  * PROVEN .................. the ONLY evidence-sufficient verdict.
  * FAIL / GAP / ERROR / NOT-RUN ... non-sufficient, fail closed.
  * WAIVED ................. an AUTHORITY DISPOSITION, never evidence; never sufficiency; never PROVEN.
  * BY-CONSTRUCTION ........ non-sufficient UNLESS a policy entry explicitly admits it WITH a named
                            backing internal proof/gate; it can NEVER launder into PROVEN.
  * external / Navigator evidence ... non-sufficient (it can never be PROVEN by mere existence); it
                            cannot satisfy sufficiency until a SEPARATE evidence-admission path admits it.
  * any UNKNOWN / out-of-vocabulary verdict ... fail closed (non-sufficient).
"""
from __future__ import annotations
from typing import Optional, Tuple
from ugk.cgp.dispatch import VERDICTS  # the canonical closed 7-verdict vocabulary (CTR-S-03)

POLICY_MODEL_ID = "capability_sufficiency_policy_v1"

# The ONLY evidence-sufficient verdict.
SUFFICIENT_VERDICTS: Tuple[str, ...] = ("PROVEN",)
# Verdicts that are non-sufficient and fail closed (no disposition can rescue them as EVIDENCE).
FAIL_CLOSED_VERDICTS: Tuple[str, ...] = ("FAIL", "GAP", "ERROR", "NOT-RUN")
# Authority disposition — never evidence sufficiency.
WAIVER_VERDICT = "WAIVED"
# Admissible ONLY with a named backing proof in the policy entry; never PROVEN.
BY_CONSTRUCTION_VERDICT = "BY-CONSTRUCTION"

# Disposition labels (pure classification; NOT decision outcomes).
SUFFICIENT = "SUFFICIENT"                                  # PROVEN
FAIL_CLOSED = "FAIL_CLOSED"                                # FAIL/GAP/ERROR/NOT-RUN/unknown
WAIVER_DISPOSITION = "WAIVER_DISPOSITION"                  # WAIVED (authority, not evidence)
BY_CONSTRUCTION_ADMITTED = "BY_CONSTRUCTION_ADMITTED"      # BY-CONSTRUCTION + named proof in entry
BY_CONSTRUCTION_UNBACKED = "BY_CONSTRUCTION_UNBACKED"      # BY-CONSTRUCTION without named proof


def is_evidence_sufficient(verdict: str) -> bool:
    """PROVEN-ONLY evidence sufficiency. Total + deterministic: every non-PROVEN verdict
    (including WAIVED, BY-CONSTRUCTION, and any unknown/out-of-vocabulary value) is False.
    This is the EVIDENCE question only -- it is NOT admissibility (waivers / by-construction
    admission are dispositions handled by classify(), never evidence)."""
    return verdict == "PROVEN"


def classify(verdict: str, *, policy_entry: Optional[dict] = None) -> Tuple[str, str]:
    """Total, pure policy classification of a verdict (optionally under an enumerated policy entry).
    Returns (disposition, reason). NEVER raises; unknown verdicts fail closed. This is the policy
    artifact's core; NOTHING on the admit/refuse decision path calls it in Lane 2a."""
    if verdict == "PROVEN":
        return SUFFICIENT, "evidence-sufficient:PROVEN"
    if verdict == WAIVER_VERDICT:
        # A waiver may (under enforcement) PERMIT despite non-sufficiency, but it is an AUTHORITY
        # disposition, NOT evidence, and is reported distinctly so it can never read as PROVEN.
        return WAIVER_DISPOSITION, "authority-disposition:WAIVED:not-evidence"
    if verdict == BY_CONSTRUCTION_VERDICT:
        named = bool(policy_entry and policy_entry.get("by_construction_proof"))
        if named:
            return BY_CONSTRUCTION_ADMITTED, "by-construction:named-proof:%s" % policy_entry["by_construction_proof"]
        return BY_CONSTRUCTION_UNBACKED, "by-construction:unbacked:non-sufficient"
    # FAIL / GAP / ERROR / NOT-RUN, and ANY unknown/out-of-vocabulary verdict -> fail closed.
    return FAIL_CLOSED, "non-sufficient:fail-closed:%s" % (verdict if verdict in VERDICTS else "unknown")


# Declarative policy artifact. `enforced_scopes` is EMPTY in Lane 2a: NO (jurisdiction/scope,
# operation/capability-class) pair is enforced, and NO decision path consumes this structure.
# Lane 2b populates + binds it. Default posture is FAIL CLOSED: only explicitly enumerated entries
# are ever enforced (no ambient permit, no global default allow).
CAPABILITY_SUFFICIENCY_POLICY = {
    "policy_model_id": POLICY_MODEL_ID,
    "vocabulary": list(VERDICTS),                       # the closed CTR-S-03 vocabulary
    "sufficient_verdicts": list(SUFFICIENT_VERDICTS),   # PROVEN only
    "fail_closed_verdicts": list(FAIL_CLOSED_VERDICTS),
    "waiver_is_evidence": False,                        # WAIVED is an authority disposition, not evidence
    "by_construction_requires_named_proof": True,       # cannot launder; named proof required to admit
    "external_evidence_sufficient": False,              # never sufficient absent a future admission path
    "unknown_fails_closed": True,
    # AD-70 (r147) -- FIRST NON-VACUOUS ACTIVATION. Bounded, explicit (jurisdiction/scope,
    # operation, capability-class) entries: governance-consequential AUTHORITY-mutating governed ops,
    # scoped to the externally-consequential governance scope, each requiring a real compound capability
    # (compound_capabilities, ATLAS-S-02). NOT global: only operations executed in the
    # "external-consequential" scope are enforced; the same ops in any other scope (session/namespace/
    # production/...) are UNENUMERATED and UNCHANGED. No ambient permit; no global default allow.
    "enforced_scopes": [
        {"jurisdiction": "external-consequential", "op": "authority_model_set",
         "capability_class": "fail_closed_governance"},
        {"jurisdiction": "external-consequential", "op": "namespace_allocate",
         "capability_class": "fail_closed_governance"},
        {"jurisdiction": "external-consequential", "op": "namespace_delegate",
         "capability_class": "fail_closed_governance"},
        {"jurisdiction": "external-consequential", "op": "namespace_revoke",
         "capability_class": "fail_closed_governance"},
    ],
    "default_posture": "fail-closed",                   # only enumerated entries enforced; no ambient permit
    "non_aggregating": True,                            # D_cap stays outside aggregate()/COMMITTED_SURFACES
    "enforcement_increment": "lane-2b-separate",        # decision-authority is a separate authorized lane
}


# ---------------------------------------------------------------------------
# Lane 2b (AD-69, DCAP-S-01) — ENFORCEMENT decision (sibling precondition).
# PURE + TOTAL + fail-closed. Consumed by the kernel as a precondition OUTSIDE aggregate();
# h_cap is NOT consulted by conjunctive_refusal_monotone_v1 and is NOT in COMMITTED_SURFACES.
# This function decides ONLY whether an operation in an ENUMERATED scope must REFUSE for
# insufficient capability. Unenumerated (jurisdiction, op/capability-class) -> NO enforcement
# (returns admit). Default-deny WITHIN an enumerated scope; no ambient permit; no global allow.
# ---------------------------------------------------------------------------

REFUSAL_CAUSE_INSUFFICIENT_CAPABILITY = "insufficient-capability"


def find_enforced_entry(policy: dict, jurisdiction: str, op: str):
    """Return the enumerated policy entry for (jurisdiction, op/capability-class), or None.
    ONLY explicitly enumerated entries are enforced; everything else is unenforced (returns None).
    No wildcard, no ambient match, no global default."""
    for e in (policy.get("enforced_scopes") or ()):
        if e.get("jurisdiction") == jurisdiction and e.get("op") == op:
            return e
    return None


def enforce_decision(*, jurisdiction: str, op: str, verdict, policy: dict = None):
    """SIBLING enforcement precondition. Returns (refuse: bool, cause: str).

    * If (jurisdiction, op) is NOT an enumerated enforced entry -> (False, "") : unenforced, behavior unchanged.
    * If enumerated: recompute the disposition of the required capability's `verdict` under the policy
      entry (law-only: pure function of verdict + the policy entry; the committed h_cap binds the ledger
      the verdict came from, so the decision is deterministic + auditable -- no committed determination column):
        - SUFFICIENT (PROVEN) ............................ admit (False, "")
        - BY_CONSTRUCTION_ADMITTED (entry names proof) ... admit (False, "")
        - WAIVER_DISPOSITION + entry permits a waiver + a waiver is present ... admit, but the waiver stays
          DISTINCT from evidence sufficiency (it never reads as PROVEN; recorded as a waiver permit)
        - everything else (FAIL_CLOSED, BY_CONSTRUCTION_UNBACKED, WAIVED w/o permit, unknown) ... REFUSE
      A missing/None verdict in an enumerated scope -> REFUSE (fail closed). External evidence cannot be
      PROVEN, so it can never be SUFFICIENT here."""
    pol = policy if policy is not None else CAPABILITY_SUFFICIENCY_POLICY
    entry = find_enforced_entry(pol, jurisdiction, op)
    if entry is None:
        return (False, "")                      # unenforced scope: unchanged
    if verdict is None:
        return (True, REFUSAL_CAUSE_INSUFFICIENT_CAPABILITY)   # enumerated + no evidence -> fail closed
    disp, _reason = classify(verdict, policy_entry=entry)
    if disp == SUFFICIENT:
        return (False, "")
    if disp == BY_CONSTRUCTION_ADMITTED:        # only because the entry named a backing proof
        return (False, "")
    if disp == WAIVER_DISPOSITION and entry.get("waiver_permits"):
        return (False, "")                      # authority waiver permit -- distinct from evidence sufficiency (never PROVEN)
    return (True, REFUSAL_CAUSE_INSUFFICIENT_CAPABILITY)       # fail closed
