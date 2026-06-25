"""ugk/conformance/commitment_minimality_gate.py — CHC-S-04 (M2.3a).

Phase M2.3b — bridge surface that restores invariant_registry_gate by
providing a gate file for the gate name referenced by CHC-S-04's statement.

This gate exercises the mechanical predicate implemented in
ugk.storage.binding_m2.commitment_minimality_gate against:
  1. The strict-mode 7-leaf leaf set that M2.2 receipts carry (must pass —
     id_P/id_Sigma/id_Phi are registered principled redundancies).
  2. The minimal 3-leaf set H_s/H_c/H_m (must pass — no redundancy at all).
  3. A synthetic unregistered-redundancy leaf set (must fail with explicit
     reason naming both the offending leaf and the carrier leaf).
  4. Cross-consistency: invariants.py CANONICALIZATION_DOMAINS and
     PRINCIPLED_REDUNDANCY_REGISTRY agree with binding_m2.py runtime mirrors
     (constitutional drift detector).

The gate enforces the mechanical predicate only. Threat-class novelty is a
design-time Governor obligation (ADR threat_class field) and is NOT checked
here — see CHC-S-04 statement for the split.
"""

from __future__ import annotations


def run():
    from ugk.storage.binding_m2 import (
        commitment_minimality_gate,
        CANONICALIZATION_DOMAINS as C_M2,
        PRINCIPLED_REDUNDANCY_REGISTRY as P_M2,
    )
    from ugk.invariants import (
        CANONICALIZATION_DOMAINS as C_INV,
        PRINCIPLED_REDUNDANCY_REGISTRY as P_INV,
    )

    fails = []

    # ── (1) Strict-mode 7-leaf set must pass ──
    ok, reason = commitment_minimality_gate(
        {"H_s", "H_c", "H_m", "H_j", "id_P", "id_Sigma", "id_Phi"}
    )
    if not ok:
        fails.append(f"strict-mode 7-leaf set rejected: {reason}")

    # ── (2) Minimal 3-leaf set must pass ──
    ok, reason = commitment_minimality_gate({"H_s", "H_c", "H_m"})
    if not ok:
        fails.append(f"minimal 3-leaf set rejected: {reason}")

    # ── (3) 4-leaf context-external (no strict pins) must pass ──
    ok, reason = commitment_minimality_gate({"H_s", "H_c", "H_m", "H_j"})
    if not ok:
        fails.append(f"4-leaf context-external set rejected: {reason}")

    # ── (4) Synthetic unregistered redundancy must fail with explicit reason ──
    extended_domains = dict(C_M2)
    extended_domains["H_hypothetical_redundant"] = frozenset({"policy_id"})
    # registry default — H_hypothetical_redundant is NOT in PRINCIPLED_REDUNDANCY_REGISTRY
    ok, reason = commitment_minimality_gate(
        {"H_s", "H_c", "H_m", "H_hypothetical_redundant"},
        domains=extended_domains,
    )
    if ok:
        fails.append("gate accepted unregistered redundancy (should reject)")
    elif "H_hypothetical_redundant" not in (reason or ""):
        fails.append(f"rejection reason doesn't name offending leaf: {reason!r}")
    elif "H_c" not in (reason or ""):
        fails.append(f"rejection reason doesn't name carrier leaf: {reason!r}")

    # ── (5) Cross-consistency: invariants.py vs binding_m2.py constitutional copies ──
    # This is the drift detector that M2.3b inherits from M2.3a's documented
    # dual-location state. A future subphase will eliminate the duplication
    # by having binding_m2.py import from invariants.py; until then, this
    # check enforces byte-equality.
    if C_INV != C_M2:
        fails.append(
            "CANONICALIZATION_DOMAINS drift between invariants.py "
            "(constitutional) and binding_m2.py (runtime mirror)"
        )
    if P_INV != P_M2:
        fails.append(
            "PRINCIPLED_REDUNDANCY_REGISTRY drift between invariants.py "
            "and binding_m2.py"
        )

    # ── REV4/M2.3c FINDING (deferred from M2.3b) ──
    # A check enforcing that each PRINCIPLED_REDUNDANCY_REGISTRY entry's leaf
    # domain is a subset of its declared carrier's domain was prepared during
    # M2.3b and removed under Governor ruling (Option A) for narrow-scope
    # discipline. The check exposed that:
    #
    #     CANONICALIZATION_DOMAINS["H_m"] does not include "semantic_regime_id",
    #     yet PRINCIPLED_REDUNDANCY_REGISTRY["id_Sigma"] declares H_m as carrier.
    #
    # Per REV3 §Deliverable 1, H_m's hash formula DOES include id(Sigma_0):
    #     H_m := H(DS_m ∥ id(c_m) ∥ c_m(x) ∥ id(Sigma_0) ∥ lineage)
    # So the H_m commitment materially covers the regime identity, but the
    # declared input domain omits it. Consequence: the id_Sigma → H_m registry
    # entry is currently unreachable in the runtime predicate (the subset
    # check fails first, so the registry lookup never fires).
    #
    # Resolution path: REV4 erratum or M2.3c constitutional pass —
    #   1. Add "semantic_regime_id" to CANONICALIZATION_DOMAINS["H_m"]
    #      in both invariants.py and binding_m2.py (reconcile the dual decl).
    #   2. Optionally add a domain-vs-formula consistency check that compares
    #      H_m's hash inputs against its declared input domain.
    #
    # Not in M2.3b scope. Runtime behavior is sound today; strict-mode
    # receipts still include id_Sigma as a distinct leaf and the merkle
    # tree composes correctly. The unreachable registry entry is documented
    # constitutional dead code pending resolution.

    ok = not fails
    return ok, (
        f"CHC-S-04: Commitment Minimality predicate operational; "
        f"strict-mode 7-leaf, minimal 3-leaf, and 4-leaf context-external "
        f"sets pass; unregistered redundancy rejected with explicit reason; "
        f"constitutional registry consistent with runtime mirror." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"commitment_minimality_gate: {'PASS' if ok else 'FAIL'}  {detail}")
