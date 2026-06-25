"""ugk/conformance/amendment_record_gate.py — AMD-S-01: AmendmentRecord content-addressed."""
import tempfile, os


def run():
    from ugk.amendment import AmendmentRecord, AmendmentArchive
    fails = []

    # Create an amendment record
    prior = "a" * 64
    succ  = "b" * 64
    rec = AmendmentRecord.create(
        prior_law_hash=prior,
        successor_law_hash=succ,
        invariants_added=["PERSIST-S-01"],
        invariants_removed=[],
        authority="test_authority",
        phase_code="ugk-phase7-v0.1.0",
    )

    if not rec.verify_hash():
        fails.append("amendment_hash does not verify against body")
    if len(rec.amendment_hash) != 64:
        fails.append(f"amendment_hash length {len(rec.amendment_hash)}")
    if rec.prior_law_hash != prior:
        fails.append("prior_law_hash mismatch")
    if rec.successor_law_hash != succ:
        fails.append("successor_law_hash mismatch")
    if "PERSIST-S-01" not in rec.invariants_added:
        fails.append("invariants_added missing PERSIST-S-01")

    # AmendmentArchive append + read roundtrip
    with tempfile.TemporaryDirectory() as td:
        arch = AmendmentArchive(os.path.join(td, "AMENDMENTS.json"))
        arch.append(rec)

        # Reload from disk
        arch2 = AmendmentArchive(os.path.join(td, "AMENDMENTS.json"))
        recs = arch2.all_records()
        if len(recs) != 1:
            fails.append(f"Archive reload: expected 1 record, got {len(recs)}")
        else:
            if not recs[0].verify_hash():
                fails.append("Reloaded record hash does not verify")
            r = arch2.record_for_transition(prior, succ)
            if r is None:
                fails.append("record_for_transition returned None for known transition")

    ok = not fails
    return ok, (
        "AMD-S-01: AmendmentRecord content-addressed; hash verifies; "
        "AmendmentArchive append/reload roundtrip correct." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"amendment_record_gate: {'PASS' if ok else 'FAIL'}  {detail}")
