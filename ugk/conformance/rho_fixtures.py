"""ugk/conformance/rho_fixtures.py — FROZEN rho regression + adversarial fixtures.

R1-R5 (red-team regressions) + A1'-A5' (adversarial) + fail-closed completeness +
dormant-when-off. These are FROZEN: they encode rho's sound domain (C1∧C2∧C3) and its
fail-closed behavior. rho is DORMANT (rho_enabled=False) by default; these fixtures
exercise it only when explicitly enabled. NOT called by the kernel.
"""
from ugk.rho_hardened import (rho_hardened, ReuseBoundary, CanonicalAuthority,
    AdmissibilityStamp, RhoPosture, GateRefusal)

def _ca(cid, canonical=True, aliases=()): return CanonicalAuthority(cid, canonical, aliases)
def _b(eff="e", auth=None, t0=1, t1=5, bind=True, ref=True):
    return ReuseBoundary(eff, auth or _ca("A"), t0, t1, bind, ref)
def _s(reach, at, honest=True): return AdmissibilityStamp(reach, at, honest)

def run_fixtures():
    on = RhoPosture(rho_enabled=True); off = RhoPosture(rho_enabled=False); res = []
    def rf(n, b, s, reason):
        try: rho_hardened(b, s, on); res.append((n, False))
        except GateRefusal as g: res.append((n, g.reason == reason))
    def ad(n, b, s):
        try: res.append((n, rho_hardened(b, s, on) == "admit"))
        except GateRefusal: res.append((n, False))
    rf("R1", _b(auth=_ca("A", False)), _s(True, 5), "E3-RAW-AUTHORITY-HANDLE")
    rf("R2", _b(t1=5), _s(False, 1), "E2-STALE-STAMP")
    rf("R3", _b(ref=False), _s(False, 5), "E1-T1-DOES-NOT-REFERENCE-T0")
    ad("R4", _b(), _s(False, 5))
    rf("R5", _b(t0=1, t1=7), _s(False, 3), "E2-STALE-STAMP")
    ad("A1p", _b(auth=_ca("A", aliases=("A_v2",))), _s(False, 5))
    rf("A2p", _b(t1=5), AdmissibilityStamp(False, 5, False), "E2-STAMP-UNATTESTED")
    res.append(("A3p", True))  # C1 documented precondition (not rho-detectable by design)
    ad("A4p", _b(eff="inner", t0=5, t1=9), _s(False, 9))
    rf("A5p", _b(t1=5), _s(True, 5), "TEMPORAL-STALE-REUSE")
    rf("FC_no_stamp", _b(t1=5), None, "E2-NO-ADMISSIBILITY-STAMP")
    rf("FC_nonmono", _b(t0=5, t1=1), _s(False, 1), "E1-BOUNDARY-NONMONOTONIC")
    rf("FC_no_binding", _b(bind=False), _s(False, 5), "E1-NO-BINDING-AT-T0")
    res.append(("dormant_off", rho_hardened(_b(), _s(True, 5), off) == "rho-disabled"))
    return res

if __name__ == "__main__":
    r = run_fixtures(); ok = all(p for _, p in r)
    for n, p in r: print(f"  [{'PASS' if p else 'FAIL'}] {n}")
    print("ALL PASS" if ok else "FAIL"); import sys; sys.exit(0 if ok else 1)
