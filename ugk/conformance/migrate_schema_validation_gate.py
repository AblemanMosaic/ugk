"""ugk/conformance/migrate_schema_validation_gate.py — migrate_schema input validation
(IEL / AD-27, Invariant A: validate-before-mutate).

Proves ValidationResult is WIRED into migrate_schema as a preflight gate: a None statements
argument is refused with a clean error (not a raw TypeError; #60), an empty migration is refused
with NO spurious receipt (#59), a VALID migration still applies and is receipted (no regression /
anti-vacuity), and the pre-existing empty-intent refusal is preserved (governance not weakened)."""
from __future__ import annotations
from ugk.storage.store import UGKReceiptStore


def run():
    # #60: None -> clean ValueError, NOT a raw TypeError
    s = UGKReceiptStore(":memory:")
    try:
        s.migrate_schema(None, intent="probe")
        return False, "Invariant A FAIL: migrate_schema(None) did not refuse"
    except TypeError:
        return False, "#60 NOT closed: migrate_schema(None) still raises a raw TypeError"
    except ValueError:
        pass

    # #59: empty migration -> refused, and NO receipt written
    s2 = UGKReceiptStore(":memory:")
    n0 = len(s2.all_receipts())
    try:
        s2.migrate_schema([], intent="probe")
        return False, "#59 NOT closed: migrate_schema([]) did not refuse"
    except ValueError:
        pass
    if len(s2.all_receipts()) != n0:
        return False, "#59 NOT closed: empty migration wrote a spurious receipt"

    # anti-vacuity / no regression: a VALID migration still applies AND is receipted
    s3 = UGKReceiptStore(":memory:")
    n0 = len(s3.all_receipts())
    res = s3.migrate_schema("ALTER TABLE receipts ADD COLUMN _msvg TEXT", intent="valid probe")
    if len(s3.all_receipts()) != n0 + 1:
        return False, "regression: a valid migration did not write its receipt"
    if "schema_hash_after" not in res:
        return False, "regression: valid migration result missing schema_hash_after"

    # pre-existing refusal preserved: empty intent still refused (no governance weakening)
    s4 = UGKReceiptStore(":memory:")
    try:
        s4.migrate_schema("CREATE TABLE _t(id INT)", intent="")
        return False, "regression: empty-intent migration was not refused"
    except ValueError:
        pass

    return True, ("ValidationResult wired into migrate_schema: None refused cleanly (#60), empty "
                  "refused with no receipt (#59), valid migration still applies+receipted, "
                  "empty-intent still refused (no governance regression)")


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + "  migrate_schema_validation_gate — " + detail)
    raise SystemExit(0 if ok else 1)
