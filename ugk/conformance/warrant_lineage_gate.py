"""ugk/conformance/warrant_lineage_gate.py — DW-S-02: warrant DAG acyclic; lineage queries correct."""


def run():
    from ugk.governance.warrant import DecisionWarrant, WarrantStore, GENESIS_WARRANT_HASH
    from ugk.storage.binding import LEGEND_HASH
    fails = []

    ws = WarrantStore()
    law = "l" * 64

    # Build a small warrant chain: W1 → W2 → W3 (prior_warrant_hash links)
    w1 = DecisionWarrant.create([1001, 1008], law_hash=law, legend_hash=LEGEND_HASH)
    w2 = DecisionWarrant.create([1008, 1010], law_hash=law, legend_hash=LEGEND_HASH,
                                prior_warrant_hash=w1.warrant_hash)
    w3 = DecisionWarrant.create([1010, 1003], law_hash=law, legend_hash=LEGEND_HASH,
                                prior_warrant_hash=w2.warrant_hash)

    ws.write(w1); ws.write(w2); ws.write(w3)

    # --- 1. is_acyclic() on well-formed DAG ---
    if not ws.is_acyclic():
        fails.append("is_acyclic() returned False on well-formed chain")

    # --- 2. basis_query(csil_id) returns correct warrants ---
    q_1008 = ws.basis_query(1008)
    if set(w.warrant_hash for w in q_1008) != {w1.warrant_hash, w2.warrant_hash}:
        fails.append(
            f"basis_query(1008): expected w1+w2, got "
            f"{[w.warrant_hash[:8] for w in q_1008]}"
        )

    q_1010 = ws.basis_query(1010)
    if set(w.warrant_hash for w in q_1010) != {w2.warrant_hash, w3.warrant_hash}:
        fails.append(f"basis_query(1010): expected w2+w3")

    q_absent = ws.basis_query(9999)
    if q_absent:
        fails.append("basis_query(9999) returned non-empty (no warrant cites 9999)")

    # --- 3. basis_query_for_law() filters by law_hash ---
    q_law = ws.basis_query_for_law(1008, law)
    if len(q_law) != 2:
        fails.append(f"basis_query_for_law(1008, law): expected 2, got {len(q_law)}")

    # Different law_hash returns nothing
    q_other_law = ws.basis_query_for_law(1008, "other" + "x" * 59)
    if q_other_law:
        fails.append("basis_query_for_law with wrong law_hash returned results")

    # --- 4. lineage_from() traverses prior_warrant_hash chain ---
    lineage = ws.lineage_from(w3.warrant_hash)
    if len(lineage) != 3:
        fails.append(f"lineage_from(w3): expected 3 warrants, got {len(lineage)}")
    if lineage[0].warrant_hash != w3.warrant_hash:
        fails.append("lineage_from(w3)[0] should be w3 (most recent first)")
    if lineage[-1].warrant_hash != w1.warrant_hash:
        fails.append("lineage_from(w3)[-1] should be w1 (genesis)")

    # lineage_from genesis warrant stops immediately
    lineage_w1 = ws.lineage_from(w1.warrant_hash)
    if len(lineage_w1) != 1:
        fails.append(f"lineage_from(w1): expected 1 (just w1), got {len(lineage_w1)}")

    # --- 5. Cycle detection ---
    # Construct a cycle-creating warrant (self-reference is simplest test)
    # We can't create a real cycle via content-addressing without pre-knowledge
    # of warrant_hash, so test the is_acyclic() method via structural test:
    # inject a fake cyclic row directly into SQLite
    ws2 = WarrantStore()
    w_a = DecisionWarrant.create([1001], law_hash=law, legend_hash=LEGEND_HASH)
    ws2.write(w_a)
    # Manually insert a warrant that points to itself (cycle)
    ws2._conn.execute(
        "INSERT OR IGNORE INTO warrants "
        "(warrant_hash, prior_warrant_hash, constitutional_basis, "
        " authority_result, jurisdiction_result, result, "
        " law_hash, legend_hash, timestamp) "
        "VALUES (?,?,?,9101,9102,9001,?,?,'2026-01-01T00:00:00Z')",
        ("cycle_" * 8 + "abcd", "cycle_" * 8 + "abcd",
         "[1001]", law, LEGEND_HASH),
    )
    ws2._conn.commit()
    if ws2.is_acyclic():
        fails.append("is_acyclic() returned True with self-referencing warrant (cycle)")

    ok = not fails
    return ok, (
        "DW-S-02: warrant DAG is acyclic; basis_query correct (CSIL:1008→w1,w2; "
        "CSIL:1010→w2,w3); law_hash filtering works; lineage_from traverses "
        "prior_warrant_hash chain; cycle detection catches self-reference." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"warrant_lineage_gate: {'PASS' if ok else 'FAIL'}  {detail}")
