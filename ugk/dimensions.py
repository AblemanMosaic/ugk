"""ugk/dimensions.py — Configuration Manifold (Grundnorm layer, 444).

Typed Dimension registry.  Each Dimension is a frozen dataclass with:
  id:           unique CM identifier (e.g. "CM-GS-01")
  axis:         what property this dimension governs
  selection:    current Phase 1 selection for this axis
  admissible:   tuple of valid selections
  inadmissible: tuple of explicitly rejected selections

Inadmissible entries are typed predicates, not prose.  Every Dimension has a
corresponding @gate_test in conformance/dimension_selection_gates.py that asserts:
  selection in admissible AND selection not in inadmissible

Ablation discipline (§14b):
  The 444 permissions ARE the accretion boundary — adding a Dimension requires
  modifying this file, which breaks grundnorm_readonly_gate.
  The dimension_selection_gate IS the ablation test for each Dimension.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dimension:
    """Typed CM dimension — admissible/inadmissible selection sets."""
    id:           str    # e.g. "CM-GS-01"
    axis:         str    # what property this governs
    selection:    str    # current Phase 1 selection
    admissible:   tuple  # valid selections
    inadmissible: tuple  # rejected selections (typed predicates)


# ---------------------------------------------------------------------------
# Dimension registry — Phase 1
# ---------------------------------------------------------------------------

DIMENSION_REGISTRY: dict[str, Dimension] = {}


def _dim(id, axis, selection, admissible, inadmissible):
    d = Dimension(id=id, axis=axis, selection=selection,
                  admissible=admissible, inadmissible=inadmissible)
    DIMENSION_REGISTRY[id] = d
    return d


# --- Governance Status ---

CM_GS_01 = _dim(
    id="CM-GS-01",
    axis="governance_status",
    selection="UNINITIALIZED",
    admissible=("UNINITIALIZED", "ACTIVE"),
    inadmissible=("CRYSTALLIZED", "ABSENT", "UNKNOWN"),
)

# --- Op Jurisdiction ---

CM_OP_01 = _dim(
    id="CM-OP-01",
    axis="kernel_op_tier_model",
    selection="three_tier",
    admissible=("three_tier",),
    inadmissible=("flat", "single_tier", "two_tier"),
)

# --- Receipt Hash Model ---

CM_DM_01 = _dim(
    id="CM-DM-01",
    axis="receipt_hash_model",
    selection="3+1_chc",
    admissible=("3+1_chc",),
    inadmissible=("1d_hash", "no_hash", "advisory"),
)

# --- Dependency Model ---

CM_DEP_01 = _dim(
    id="CM-DEP-01",
    axis="runtime_dependency_model",
    selection="stdlib_plus_vendored",   # Phase 2: vendored Ed25519 added
    admissible=("stdlib_only", "stdlib_plus_vendored"),
    inadmissible=("external_pip", "framework_required"),
)

# --- Failure Mode ---

CM_FM_01 = _dim(
    id="CM-FM-01",
    axis="gate_failure_mode",
    selection="fail_closed",
    admissible=("fail_closed",),
    inadmissible=("fail_open", "warn_and_proceed", "log_only"),
)

# --- Receipt Storage ---

CM_ST_01 = _dim(
    id="CM-ST-01",
    axis="receipt_storage_backend",
    selection="sqlite_stdlib",
    admissible=("sqlite_stdlib", "sqlite_external"),
    inadmissible=("in_memory_list_only", "no_persistence", "external_db_required"),
)

# --- Broker Pattern ---

CM_BR_01 = _dim(
    id="CM-BR-01",
    axis="broker_pattern",
    selection="BrokerClient_abstract",
    admissible=("BrokerClient_abstract", "LocalBrokerServer_inprocess"),
    inadmissible=("ambient_io_direct", "no_broker_abstraction"),
)

# --- Snapshot Model ---

CM_SN_01 = _dim(
    id="CM-SN-01",
    axis="snapshot_model",
    selection="two_tier",
    admissible=("two_tier",),
    inadmissible=("single_tier", "no_snapshot", "always_verify"),
)

# --- Classified Remainders ---

CM_CR_01 = _dim(
    id="CM-CR-01",
    axis="classified_remainder_declaration",
    selection="declared_4",
    admissible=("declared_4",),
    inadmissible=("undeclared", "overclaimed_full_coverage"),
)

# --- Governor Key Status ---

CM_GK_01 = _dim(
    id="CM-GK-01",
    axis="governor_key_status",
    selection="dev_temp_key",           # Phase 2: real Ed25519, Coder-generated
    admissible=("unset_sentinel", "dev_temp_key", "ceremony_complete"),
    inadmissible=("no_key_mechanism",), # dev_temp_key is authorized dev state, not inadmissible
)

# --- Phase 3: Validator Set ---

CM_VS_01 = _dim(
    id="CM-VS-01",
    axis="validator_set_model",
    selection="N1_governor_sealed",   # Phase 3: N=1 dev_temp Governor
    admissible=("N1_governor_sealed", "N_quorum_bft"),
    inadmissible=("unsealed", "no_validator_set"),
)

# --- Phase 3: Inception Certificate ---

CM_IC_01 = _dim(
    id="CM-IC-01",
    axis="inception_certificate_model",
    selection="trusted_genesis_sunset",  # Phase 3: trusted-genesis, sunset declared
    admissible=("trusted_genesis_sunset", "trusted_genesis_final", "rotated"),
    inadmissible=("no_ic", "unsigned"),
)
