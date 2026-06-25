"""ugk/schema.py — Governance operations registry (Grundnorm layer, 444).

Three-tier op jurisdiction enforced by GovernanceKernel.execute():

  Tier 0 — _KERNEL_OPS:        {"gate_admit", "gate_refuse"}
    Never externally callable.  Emitted only by kernel.execute() internals.
    Calling directly raises KernelInternalOp.

  Tier 1 — _UNIVERSAL_OPS:     {"session_open", "session_close",
                                 "crp_evidence", "test_checkpoint"}
    Available in UNINITIALIZED + ACTIVE.  The ceremony itself uses these.

  Tier 2 — APPLICATION_OPS:    {}  (deployer populates via ops.py — 644)
    ACTIVE only.  Refused in UNINITIALIZED with GovernanceNotFounded.

GOVERNANCE_OPS = _UNIVERSAL_OPS ∪ APPLICATION_OPS.
_KERNEL_OPS is deliberately excluded from GOVERNANCE_OPS — the distinction
is constitutive: passing a Tier-0 op to execute() must raise KernelInternalOp
before any BS-01 check.

BS-01: an op not in GOVERNANCE_OPS raises UndeclaredOp at execute() time —
not silent, not auto-registered.
"""

# ---------------------------------------------------------------------------
# Tier 0 — kernel-internal ops (never externally callable)
# ---------------------------------------------------------------------------

_KERNEL_OPS: frozenset[str] = frozenset({
    "gate_admit",
    "gate_refuse",
})

# ---------------------------------------------------------------------------
# Tier 1 — universal governance primitives (UNINITIALIZED + ACTIVE)
# ---------------------------------------------------------------------------

_UNIVERSAL_OPS: dict[str, dict] = {
    "session_open": {
        "description": "Governance session opened; SessionIdentity spawned",
        "authority":   "system",
        "tier":        1,
    },
    "session_close": {
        "description": "Governance session closed; chain anchored",
        "authority":   "system",
        "tier":        1,
    },
    "crp_evidence": {
        "description": "CRP structural test evidence receipt",
        "authority":   "system",
        "tier":        1,
    },
    "test_checkpoint": {
        "description": "Causal boundary between scenarios in governed batch execution",
        "authority":   "system",
        "tier":        1,
    },
    "legend_seal": {
        "description": "Constitutional legend vocabulary sealed into the receipt store at ceremony",
        "authority":   "system",
        "tier":        1,
    },
    "session_summary": {
        "description": "Aggregate closure document for a governed session",
        "authority":   "system",
        "tier":        1,
    },
}

# ---------------------------------------------------------------------------
# APPLICATION_OPS imported from ops.py (644 — deployer surface).
# schema.py itself never declares application ops.
# ---------------------------------------------------------------------------

try:
    from ugk.ops import APPLICATION_OPS as _APPLICATION_OPS
except ImportError:  # ops.py absent during wheel build or standalone import
    _APPLICATION_OPS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# GOVERNANCE_OPS — single lookup surface for GovernanceKernel.execute()
# _KERNEL_OPS deliberately excluded.
# ---------------------------------------------------------------------------

GOVERNANCE_OPS: dict[str, dict] = {**_UNIVERSAL_OPS, **_APPLICATION_OPS}

__all__ = [
    "_KERNEL_OPS",
    "_UNIVERSAL_OPS",
    "_APPLICATION_OPS",
    "GOVERNANCE_OPS",
]
