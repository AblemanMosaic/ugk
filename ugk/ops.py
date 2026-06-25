"""ugk/ops.py — Application operations registry (644 — deployer surface).

THIS IS THE ONLY FILE IN THE UGK PACKAGE WITH WRITE PERMISSION (644).
Every other UGK file is read-only (444 — Grundnorm layer).

Deployers declare application-layer ops here.  UGK ships with an empty
APPLICATION_OPS dict.  Add ops before passing them to kernel.execute():

    APPLICATION_OPS["write_config"] = {
        "description": "Write application configuration file",
        "authority":   "admin",
        "tier":        2,
    }

Rules:
  - All ops declared here are Tier 2 (ACTIVE only).
  - Op names must not collide with _KERNEL_OPS or _UNIVERSAL_OPS (checked at
    kernel construction time by the schema import).
  - Removing an op from APPLICATION_OPS breaks any caller that passes it to
    execute() — UndeclaredOp will be raised (BS-01 enforced).

Do NOT add ops that belong to the Grundnorm layer (gate_admit, gate_refuse,
session_open, session_close, crp_evidence, test_checkpoint).  Those are
declared in schema.py (444) and are not deployer-configurable.
"""

# Deployer-declared application-layer ops.
# B5 (GOVLOG-6 track): authority_model_set makes governance-posture mutation a governed,
# receipted, refusable op. The ungoverned direct charter rewrite in `authority-model --set`
# is removed; the posture change is now routed through kernel.execute().
APPLICATION_OPS: dict[str, dict] = {
    "authority_model_set": {
        "description": "Govern a change to the deployment authority model (charter posture). "
                       "Routed through execute() so it is gated per the current model, "
                       "receipted before effect (NBER-1), and refusable.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_claim": {
        "description": "Namespace OWNERSHIP governance (FGA §10): propose to acquire an "
                       "application-level name. A claim is a proposal receipt and does NOT grant "
                       "ownership. Distinct from allocation (must not be collapsed). "
                       "Ownership-lifecycle layer over application names — NOT the constitutional "
                       "membership namespace (NAMESPACE_PHI_0). See ugk/namespace_governance.py.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_allocate": {
        "description": "Namespace OWNERSHIP governance (FGA §10): admit a claim into ownership. "
                       "Gated by the conflict policy (REFUSE on canonical-name collision). On "
                       "admission the allocation receipt is the ownership grant (ownership is a "
                       "receipt-chain projection; no table). Distinct from claim.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_delegate": {
        "description": "Namespace OWNERSHIP governance (FGA §10, Phase 2b): the current owner grants "
                       "SCOPED authority over a name to another authority. Owner-only (non-owner "
                       "REFUSED); does not transfer ownership. Folded by project/_project; no table.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_revoke": {
        "description": "Namespace OWNERSHIP governance (FGA §10/§14, Phase 2b): the current owner "
                       "removes ownership of a name. Owner-only (non-owner REFUSED). PERMANENT — a "
                       "revoked name is never re-granted (no un-revoke; WILL-S-04 pattern). No table.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_invalidate": {
        "description": "Namespace OWNERSHIP governance (FGA §10/§14, Phase 2b): the current owner "
                       "strikes a name permanently invalid (removes ownership; never re-grantable). "
                       "Owner-only (non-owner REFUSED). Collapses onto the revocation pattern. No table.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_supersede": {
        "description": "Namespace OWNERSHIP governance (FGA §10, Phase 2c): the current owner TRANSFERS "
                       "ownership of a name to a new owner (owner-initiated supersession via append-only "
                       "receipt). Owner-only (non-owner REFUSED). Distinct from allocation REFUSE (NS-S-03) "
                       "— a transfer of existing ownership, not a colliding allocation. No table.",
        "authority": "governor",
        "tier":      2,
    },
    "namespace_adjudicate": {
        "description": "Namespace OWNERSHIP governance (FGA §10, Phase 2c): the constitutional Governor "
                       "(authority == kernel mosaic root) AWARDS a contested name to an owner, overriding "
                       "the current owner. Governor-only (non-Governor REFUSED). Cannot resurrect a "
                       "permanently revoked/invalidated name. Reuses authority-by-admissibility. No table.",
        "authority": "governor",
        "tier":      2,
    },
}
