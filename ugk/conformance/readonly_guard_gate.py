"""ugk/conformance/readonly_guard_gate.py — read-only enforcement gate (IEL / AD-25, Invariant D).

Proves ReadOnlyGuard is fail-closed: it refuses a read-only op against a non-existent on-disk DB
(prevents accidental creation), detects a DB brought into existence inside a guarded block, exempts
ephemeral :memory:, and is transparent to a genuine read against an existing DB."""
from __future__ import annotations
import os
import tempfile

from ugk.integrity import ReadOnlyGuard, ReadOnlyViolation


def run():
    d = tempfile.mkdtemp()
    db = os.path.join(d, "ugk.db")

    # (1) require_existing on an absent DB -> fail closed
    try:
        ReadOnlyGuard.require_existing(db, name="verify")
        return False, "Invariant D FAIL: require_existing did not refuse a non-existent DB"
    except ReadOnlyViolation:
        pass

    # (2) a guarded block that creates a DB file -> detected and raised
    try:
        with ReadOnlyGuard(db, name="verify"):
            open(db, "wb").close()  # simulate accidental DB creation
        return False, "Invariant D FAIL: guard did not detect DB creation on a read path"
    except ReadOnlyViolation:
        pass

    # (3) ephemeral :memory: is exempt (no persistent state)
    with ReadOnlyGuard(":memory:", name="verify"):
        pass

    # (4) transparent to a genuine read of an existing DB (db now exists from step 2)
    if not os.path.exists(db):
        return False, "fixture broken: expected db to exist after step 2"
    with ReadOnlyGuard(db, name="verify"):
        _ = open(db, "rb").read()  # pure read, no mutation
    # require_existing must now PASS (db exists)
    ReadOnlyGuard.require_existing(db, name="verify")

    return True, ("ReadOnlyGuard fail-closed: refuses absent DB (require_existing), detects DB creation "
                  "in a guarded block, exempts :memory:, transparent to genuine reads")


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + "  readonly_guard_gate — " + detail)
    raise SystemExit(0 if ok else 1)
