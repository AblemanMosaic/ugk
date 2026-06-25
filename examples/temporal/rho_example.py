"""rho_example.py — ρ is a DORMANT, opt-in temporal-provenance checker (UGK v0.1.0).

Demonstrates: ρ disabled (default) is a no-op; enabled, it admits a fresh reuse and
fails closed on a stale one. ρ is NOT wired into execute(); a caller invokes it directly.

Run:  python examples/temporal/rho_example.py
"""
import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ugk.rho_hardened import (rho_hardened, ReuseBoundary, CanonicalAuthority,
                              AdmissibilityStamp, RhoPosture, GateRefusal)

def main():
    A = CanonicalAuthority(canonical_id="A", canonical=True, aliases=())
    boundary = ReuseBoundary("effect", A, t0=1, t1=5, binding_at_t0=True,
                             t1_references_t0=True)
    fresh = AdmissibilityStamp(reachable_without_A=False, evaluated_at_position=5, attested_honest=True)
    stale = AdmissibilityStamp(reachable_without_A=False, evaluated_at_position=1, attested_honest=True)

    # 1. DORMANT by default — no-op regardless of input.
    off = RhoPosture(rho_enabled=False)
    print("dormant (default):", rho_hardened(boundary, fresh, off))  # 'rho-disabled'

    # 2. ENABLED (opt-in) — admits a fresh, freshly-stamped reuse.
    on = RhoPosture(rho_enabled=True)
    print("enabled, fresh reuse:", rho_hardened(boundary, fresh, on))  # 'admit'

    # 3. ENABLED — fails closed on a stale stamp (E2).
    try:
        rho_hardened(boundary, stale, on)
        print("enabled, stale reuse: ADMITTED (unexpected)")
    except GateRefusal as g:
        print("enabled, stale reuse: fail-closed ->", g.reason)

if __name__ == "__main__":
    main()
