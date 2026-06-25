"""ugk/conformance/determinism_gate.py — CHC-S-02: CHC is deterministic (reproducible)."""


def run():
    """Identical (op, authority, parameters, intent, jurisdiction, confidence,
    session_dkn, timestamp, law_hash) → byte-identical semantic_hash.

    Proves reproducibility without any secret or external state.
    Uses binding.dm_s03 directly to avoid timestamp non-determinism.
    """
    from ugk.storage.binding import dm_s03, state_hash
    fails = []

    base_args = dict(
        state_hash="abcd1234" * 8,
        parent="0" * 64,
        intent="crp_evidence",
        authority="system",
        jurisdiction="session",
        confidence="high",
        session_id="sess-dkn-test-value",
        agent_id="sess-dkn-test-value",
        ts="1700000000.123456",
        law_hash="deadbeef" * 8,
    )

    # Run 50 times — must produce byte-identical output
    first = dm_s03(**base_args)
    if len(first) != 64:
        fails.append(f"dm_s03 returned {len(first)}-char string, expected 64")

    for i in range(49):
        result = dm_s03(**base_args)
        if result != first:
            fails.append(f"Run {i+2}: dm_s03 non-deterministic: {result!r} != {first!r}")
            break

    # Verify state_hash determinism too
    sh1 = state_hash("crp_evidence", '{"x":1}')
    for i in range(19):
        sh2 = state_hash("crp_evidence", '{"x":1}')
        if sh2 != sh1:
            fails.append(f"state_hash non-deterministic on run {i+2}")
            break

    # Different inputs must produce different outputs (collision-sensitivity)
    different_ts   = dm_s03(**{**base_args, "ts": "1700000001.999999"})
    different_auth = dm_s03(**{**base_args, "authority": "other_authority"})
    if different_ts == first:
        fails.append("dm_s03 produced same hash for different ts (not collision-sensitive)")
    if different_auth == first:
        fails.append("dm_s03 produced same hash for different authority")
    if different_ts == different_auth:
        fails.append("dm_s03 produced same hash for different ts vs different authority")

    ok = not fails
    return ok, ("CHC-S-02: dm_s03 is deterministic (50/50 identical runs) and "
                "collision-sensitive across ts, authority." if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"determinism_gate: {'PASS' if ok else 'FAIL'}  {detail}")
