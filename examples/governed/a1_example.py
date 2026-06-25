"""a1_example.py — A1 (set-valued authority) is DORMANT, opt-in (UGK v0.1.0).

Demonstrates: with A1 posture off (default) the verifier is a no-op ('a1-disabled');
turning it on activates set-valued authority verification. A1 is add-only and does not
change default kernel behavior.

Run:  python examples/governed/a1_example.py
"""
import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ugk.authority.a1_verifier import A1Posture, verify_a1, EffectClaim

def main():
    claim = EffectClaim(cc_version="c_c.v1", claimed_authorities=["A"])
    chain = ["A"]
    # admissibility_fn(chain)->bool: A is a genuine cut-set (e not admitted without A)
    adm = lambda chain: "A" in chain

    # 1. DORMANT by default — verifier is a no-op.
    off = A1Posture(a1_enabled=False)
    print("dormant (default):", verify_a1("op", "e", chain, claim, adm, off))  # 'a1-disabled'

    # 2. ENABLED (opt-in) — single-authority case reduces to the v1.0 check.
    on = A1Posture(a1_enabled=True)
    try:
        print("enabled, single-authority:", verify_a1("op", "e", chain, claim, adm, on))
    except Exception as ex:
        print("enabled:", type(ex).__name__, ex)

if __name__ == "__main__":
    main()
