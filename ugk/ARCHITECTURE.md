# UGK v0.1.0 — Module Architecture

The `ugk/` package groups modules by role. Cohesive role-clusters live in subpackages;
genuinely-core and singleton modules remain flat at the package root. Constitutional identity
is decoupled from physical paths via `ugk/module_registry.py`, so conformance gates resolve
protected modules by logical identity rather than filename — the layout can evolve without
perturbing `law_hash` or breaking gates.

## Layout (role-packages + flat core)

### Role / capability subpackages
- `storage/` — append-only substrate: `store.py` (UGKReceiptStore), `audit.py`,
  `binding.py`, `binding_m2.py` (effect↔authority binding, CHC/PSA).
- `transport/` — surfaces/adapters: `broker.py`, `rpc.py`, `agent.py`.
- `governance/` — policy & authorization: `policy.py`, `posture.py`, `governor.py`,
  `warrant.py` (WarrantStore).
- `authority/` — A1 capability cluster (DORMANT, opt-in): `a1_verifier.py`,
  `authority_graph.py`, `authority_keys.py`, `authority_model.py`, `capabilities.py`,
  `capability_evidence.py`.
- `scale/` — scale-lane capability (DORMANT, opt-in): `oracle.py`, `scheduler.py`,
  `conformance.py`, `al_conformance.py`. Posture-gated (`ScalePosture`); never on the
  default execution path.

### Flat core (at `ugk/` root)
The kernel reactor and its law, plus modules whose real boundary is *within* the core (a
`core/` wrapper would relabel without clarifying) and singletons:
- `kernel.py` — GovernanceKernel; execute() reactor; identity bind at import.
- `invariants.py` — the law (source of `law_hash`); **do not modify without authorization**.
- `ops.py`, `schema.py` — declared op registry (GOVERNANCE_OPS / BS-01).
- `decision.py`, `will.py`, `intent.py` — decision/intent surface.
- `amendment.py`, `successor.py` — amendment & succession records.
- `csh.py` — constitutional semantic hashing.
- `namespace.py`, `dimensions.py`, `scope.py`, `lineage.py`, `freshness.py`, `summary.py`,
  `witness.py`, `charter.py`, `adr.py`, `gate_probe.py`, `_paths.py` — core substrate.
- `rho_hardened.py` — temporal/ρ capability (DORMANT, opt-in; NOT wired into execute()).
- `cli.py` — CLI surface.
- `module_registry.py` — logical identity of constitutionally-significant modules
  (Grundnorm / law / facade / record), resolved to paths at runtime. The decoupling layer.

### Existing subpackages
- `cgp/` — Constitutional Governance Protocol (receipt-generation reasoning layer; core).
- `conformance/` — gates, vectors, fixtures (the test substrate).
- `core/` — SRSA and core vector primitives. `ctr/`, `codex/`, `migration/`, `templates/`,
  `docs/`, `testing/`, `vendor/` — supporting material.

## Public API
`from ugk import ...` is the canonical public surface (`ugk.__all__`, 17 symbols incl.
GovernanceKernel, UGKReceiptStore, WarrantStore, DeploymentManifest, BrokerClient, ...).
Opt-in dormant capabilities (A1, ρ, scale) are reached via their explicit modules/subpackages
and are never on the default execution path.

## Path-decoupling note
Conformance gates and the protected-module set resolve through `ugk.module_registry` by
logical dotted identity, not root-relative filenames. This is why the storage/transport/
governance/authority clusters could be physically reorganized while keeping `law_hash`
byte-identical and the full conformance-gate suite passing. `invariants.py` carries two
`# Runtime mirror:` comments that still name pre-reorg module paths; they are documentation
only (the law module never moves) and are left unedited to preserve `law_hash`.
