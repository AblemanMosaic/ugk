# rho — Sound-Domain Statement (in-tree record)
rho (ugk/rho_hardened.py) is a DORMANT, OPT-IN temporal-provenance checker. It is NOT
called by the kernel; execute() does not invoke it. It runs only when an explicit caller
sets RhoPosture(rho_enabled=True) and hands it a ReuseBoundary + AdmissibilityStamp.

SOUND DOMAIN: rho's verdict is trustworthy IFF
  C1 — every reuse boundary is presented to rho (boundary-set completeness; an
       enumerator precondition — rho catches only what it is shown);
  C2 — the admissibility stamp is honest (evaluator truly evaluated against live S_t1);
  C3 — canonical-ID assignment is correct relative to the declared invariant core.
OUTSIDE C1∧C2∧C3, rho FAILS CLOSED — it never emits a trusted verdict on an unmet
precondition. rho ENFORCES E1 (boundary validity), E2 (freshness match + attestation
presence), E3 (canonical-ID use), each fail-closed. C1/C2/C3 remain DECLARED
preconditions, not enforced by rho.

STATUS: dormant opt-in capability (mirrors A1). Tier-A reuse mediation, if/when built,
would USE rho as its checker; rho does NOT depend on Tier-A. No execute() wiring exists.
