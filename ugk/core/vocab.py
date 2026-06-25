"""ugk/core/vocab.py — Minimal semantic governance vocabulary.

Governance-generic semantic vocabulary: canonical intent types, jurisdiction
types, and authority tiers.  Makes intent declarations legible rather than
arbitrary strings.

Phase 12: SSA vocabulary expanded to full 17-verb canonical list (Governor-confirmed).
The 17 verbs are governance-generic epistemic/governance moves — not domain-specific.
Their inclusion enables SSA=1 on the SRSA vector.

NOT corpus machinery.  CMB/GMB spine structures are AbleTools concerns, not UGK's.
"""

INTENT_TYPES: frozenset[str] = frozenset({
    # Phase 1 — original 8
    "orient",       # situate within a framework
    "synthesize",   # combine disparate inputs into a unified result
    "verify",       # check against a declared standard
    "claim",        # assert a constitutional position
    "transform",    # change the form of an artifact while preserving meaning
    "conform",      # bring into alignment with a constraint
    "annotate",     # attach governed metadata to an artifact
    "observe",      # record a witnessed state without interpretation
    # Phase 12 — SSA vocabulary extension (9 additions, Governor-confirmed)
    "resolve",      # disambiguate or settle a contested state
    "propose",      # put forward a hypothesis or plan for evaluation
    "evaluate",     # assess against declared criteria
    "classify",     # assign to a category or type
    "derive",       # obtain by inference from prior evidence
    "compare",      # place in relational context
    "define",       # establish scope, boundary, or meaning
    "infer",        # draw conclusion from available evidence
    "enumerate",    # catalog or list the members of a set
})

JURISDICTION_TYPES: frozenset[str] = frozenset({
    "session",
    "corpus",
    "operator",
    "system",
    "kernel",
})

AUTHORITY_TIERS: dict[str, int] = {
    "system":    0,
    "agent":     1,
    "governor":  2,
    "root":      3,
}

SSA_CANONICAL_VERBS: tuple = tuple(sorted(INTENT_TYPES))
SSA_VERB_COUNT: int = len(INTENT_TYPES)

__all__ = [
    "INTENT_TYPES", "JURISDICTION_TYPES", "AUTHORITY_TIERS",
    "SSA_CANONICAL_VERBS", "SSA_VERB_COUNT",
]
