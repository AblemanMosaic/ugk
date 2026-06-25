"""ugk/conformance/esa_selfcheck_gate.py — UL-S-04: kernel ESA self-check ≥4/5 KCaps pass."""


def run():
    """KCap-2 (Grundnorm read-only) gates on file permissions set by make_release.sh.
    During development (pre-release), files may be writable — allow KCap-2 to be
    advisory (pass if ≥4/5 caps pass).  KCap-1,3,4,5 must always pass.
    """
    from ugk.kernel import GovernanceKernel
    from ugk.core.esa import run_selfcheck
    fails = []

    k = GovernanceKernel()
    k.open_session()
    report = run_selfcheck(k)

    required_pass = ("KCap-1", "KCap-3", "KCap-4", "KCap-5")
    for cap_id in required_pass:
        if not report.results.get(cap_id, False):
            fails.append(f"{cap_id} failed: {[f for f in report.failures if cap_id in f]}")

    if report.caps_passed < 4:
        fails.append(
            f"Only {report.caps_passed}/{report.caps_checked} KCaps passed — minimum is 4. "
            f"Failures: {report.failures}"
        )

    ok = not fails
    return ok, (
        f"UL-S-04: {report.caps_passed}/{report.caps_checked} KCaps passed "
        f"({report.overall}); required KCap-1,3,4,5 all pass." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"esa_selfcheck_gate: {'PASS' if ok else 'FAIL'}  {detail}")
