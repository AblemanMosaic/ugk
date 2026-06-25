"""ugk/conformance/ssa_vocabulary_gate.py — SSA-VOCAB-S-01: 17 canonical SSA verbs declared."""


SSA_CANONICAL_17 = frozenset({
    # Phase 1 (original 8)
    "orient", "synthesize", "verify", "claim",
    "transform", "conform", "annotate", "observe",
    # Phase 12 (9 additions, Governor-confirmed)
    "resolve", "propose", "evaluate", "classify",
    "derive", "compare", "define", "infer", "enumerate",
})


def run():
    from ugk.core.vocab import INTENT_TYPES, SSA_VERB_COUNT
    from ugk.storage.binding import _INTENT_TO_CSIL
    from ugk.kernel import GovernanceKernel
    import ugk
    fails = []

    # INTENT_TYPES contains exactly the 17 canonical verbs
    if INTENT_TYPES != SSA_CANONICAL_17:
        missing = SSA_CANONICAL_17 - INTENT_TYPES
        extra   = INTENT_TYPES - SSA_CANONICAL_17
        if missing: fails.append(f"Missing from INTENT_TYPES: {sorted(missing)}")
        if extra:   fails.append(f"Extra in INTENT_TYPES: {sorted(extra)}")

    if SSA_VERB_COUNT != 17:
        fails.append(f"SSA_VERB_COUNT={SSA_VERB_COUNT}, expected 17")

    # All 17 verbs have CSIL integers in the compress map
    for verb in SSA_CANONICAL_17:
        if verb not in _INTENT_TO_CSIL:
            fails.append(f"Verb {verb!r} missing from LEGEND compress map")

    # CSIL IDs are in the expected range (4001–4017)
    for verb, csil_id in _INTENT_TO_CSIL.items():
        if not (4001 <= csil_id <= 4017):
            fails.append(f"CSIL id for {verb!r} out of range: {csil_id}")

    # SSA axis is lit on the SRSA vector
    k = GovernanceKernel()
    k._ceremony()
    v = ugk.srsa_vector(k)
    ssa = v.get("SSA", {})
    if not ssa.get("lit"):
        fails.append(f"SSA axis not lit: {ssa}")
    if ssa.get("score") != 1:
        fails.append(f"SSA score={ssa.get('score')}, expected 1")

    ok = not fails
    return ok, (
        f"SSA-VOCAB-S-01: all 17 canonical verbs in INTENT_TYPES and LEGEND; "
        f"CSIL range 4001–4017; SSA axis lit (score=1)." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"ssa_vocabulary_gate: {'PASS' if ok else 'FAIL'}  {detail}")
