"""ugk/invariants.py — Typed invariant registry (Grundnorm layer, 444).

The invariant registry IS the coverage map.  CTR iterates it directly —
no coverage_map.json binding layer.  The invariants cannot drift from the
implementation because they ARE the implementation (same file, 444 protected).

Each Invariant carries:
  id              — unique invariant identifier (e.g. "UL-S-01")
  statement       — human-readable invariant claim
  gate            — conformance gate function name that proves the invariant
  classification  — DOMAIN_PHYSICS | MIXED | ABI_CONFIG
  adjacency_target — adjacent domain that ablation of this primitive produces

Classification semantics (Ableman Razor applied to primitives):
  DOMAIN_PHYSICS  — removing this changes the fundamental physics of the domain
  MIXED           — partially domain physics, partially configuration choice
  ABI_CONFIG      — configuration choice within the admissible domain

adjacency_target discipline (§14b):
  Ablation = removing the primitive → the system drops into the named adjacent domain.
  The gate IS the ablation test: gate failure = primitive removed = adjacency achieved.
  444 permissions ARE the accretion boundary: modifying requires breaking
  grundnorm_readonly_gate, which exits the constitutionally governed space.

staleness_gate pins the SHA-256 of this file's content.  Any edit to this file
changes the pin — constitutional drift is detected, not hidden.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invariant:
    """Typed executable invariant specification primitive."""
    id:               str        # e.g. "UL-S-01"
    statement:        str        # invariant claim
    gate:             str        # conformance gate function name
    classification:   str        # DOMAIN_PHYSICS | MIXED | ABI_CONFIG
    adjacency_target: str        # what domain ablation of this primitive produces
    depends_on:       tuple = () # invariant IDs this one requires to be meaningful
    introduced_in:    str = ""   # phase that introduced this invariant


# ---------------------------------------------------------------------------
# Invariant registry — Phase 1 (all entries)
# ---------------------------------------------------------------------------

INVARIANT_REGISTRY: dict[str, Invariant] = {}


def _reg(id, statement, gate, classification, adjacency_target,
         depends_on=(), introduced_in=""):
    inv = Invariant(id=id, statement=statement, gate=gate,
                    classification=classification,
                    adjacency_target=adjacency_target,
                    depends_on=tuple(depends_on),
                    introduced_in=introduced_in)
    INVARIANT_REGISTRY[id] = inv
    return inv


# --- UL: Universal Layer invariants ---

UL_G_01 = _reg(
    id="UL-G-01",
    statement=(
        "The Grundnorm layer (kernel.py, schema.py, store.py, binding.py, "
        "broker.py, invariants.py, dimensions.py) is read-only after installation "
        "(file permissions 444).  Any modification to these files exits the "
        "constitutionally governed space."
    ),
    gate="grundnorm_readonly_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Mutable substrate — the constitutional layer can be silently edited; "
        "governance guarantees become convention rather than structure."
    ),
    depends_on=(),
    introduced_in="phase1",
)

UL_S_01 = _reg(
    id="UL-S-01",
    statement=(
        "Zero external runtime dependencies.  UGK uses only stdlib (hashlib, "
        "sqlite3, json, uuid, time, pathlib) plus vendored Ed25519 (Phase 2+).  "
        "No pip-installed package is required to run the governance substrate."
    ),
    gate="zero_deps_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Dependency-constrained substrate — not deployable in embedded, "
        "air-gapped, or locked-dependency contexts."
    ),
    depends_on=(),
    introduced_in="phase1",
)

UL_S_02 = _reg(
    id="UL-S-02",
    statement=(
        "Receipt-before-effect is kernel-enforced at the API level, not convention.  "
        "Step 6 (write success receipt) in execute() happens before Step 7 "
        "(effect() call).  A receipt is written even if effect() never returns."
    ),
    gate="nber1_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Advisory Receipt System — receipts encouraged but not structurally "
        "required; an effect can execute without a prior receipt."
    ),
    depends_on=("UL-S-03",),
    introduced_in="phase1",
)

UL_S_03 = _reg(
    id="UL-S-03",
    statement=(
        "Every op submitted to execute() must be declared in GOVERNANCE_OPS "
        "before execution (BS-01).  An undeclared op raises UndeclaredOp — "
        "never silent, never auto-registered."
    ),
    gate="bs01_gate",
    classification="MIXED",
    adjacency_target=(
        "Silent governance — undeclared operations execute without constitutional "
        "standing; governance coverage is a hope, not a verified property."
    ),
    depends_on=(),
    introduced_in="phase1",
)

UL_S_04 = _reg(
    id="UL-S-04",
    statement=(
        "The kernel provides a native ESA self-check (~5 governance-generic "
        "capabilities) and a valid 10-axis SRSA vector without any application-layer "
        "dependency.  Every UGK consumer inherits a declared governance baseline."
    ),
    gate="esa_selfcheck_gate",
    classification="MIXED",
    adjacency_target=(
        "Dark governance floor — the kernel makes no self-observability claims; "
        "consumers cannot derive a baseline SRSA score from UGK import alone."
    ),
    depends_on=("UL-S-01",),
    introduced_in="phase1",
)

# --- GK: Governance Kernel invariants ---

GK_S_01 = _reg(
    id="GK-S-01",
    statement=(
        "Admission is blocking and fail-closed.  gate() returning False halts "
        "execution unconditionally before effect() is called.  There is no "
        "'warn and proceed' mode — refusal is constitutive, not advisory."
    ),
    gate="enforcement_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Advisory gate system — gate failures produce warnings but do not "
        "block execution; governance is observable but not constitutive."
    ),
    depends_on=("UL-S-03",),
    introduced_in="phase1",
)

GK_S_02 = _reg(
    id="GK-S-02",
    statement=(
        "The W/G/E reactor fires in fixed order: gate() before effect(), "
        "gate_admit receipt before the op receipt, op receipt before effect().  "
        "No reordering is possible through the public API."
    ),
    gate="admission_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Unordered reactor — governance steps can be skipped or reordered; "
        "the W/G/E separation becomes notational rather than structural."
    ),
    depends_on=("GK-S-01", "UL-S-02"),
    introduced_in="phase1",
)

# --- CM: Configuration Manifold invariants ---

CM_GS_01 = _reg(
    id="CM-GS-01",
    statement=(
        "Governance status transitions UNINITIALIZED → ACTIVE via the founding "
        "ceremony.  UNINITIALIZED is fail-closed (Tier 2 refused).  The system "
        "NEVER occupies the CRYSTALLIZED state (capable but non-constitutive).  "
        "Ships in UNINITIALIZED with GOVERNOR_PUBKEY_HEX = sentinel."
    ),
    gate="status_transition_gate",
    classification="ABI_CONFIG",
    adjacency_target=(
        "Always-on or always-off kernel — no founding event; either governance "
        "is always ACTIVE regardless of ceremony, or Tier 2 is always refused "
        "regardless of status.  No CRYSTALLIZED→ACTIVE progression."
    ),
    depends_on=("UL-G-01",),
    introduced_in="phase1",
)

CM_GS_02 = _reg(
    id="CM-GS-02",
    statement=(
        "The shipped kernel GOVERNOR_PUBKEY_HEX is the unset sentinel "
        "'GOVERNOR_KEY_UNSET__RUN_GENESIS_CEREMONY'.  governance_status == "
        "UNINITIALIZED on the shipped artifact.  No usable key is baked in."
    ),
    gate="governor_key_unset_gate",
    classification="ABI_CONFIG",
    adjacency_target=(
        "Pre-founded artifact — a usable Governor key is baked into the shipped "
        "package; the founding ceremony is bypassed; any holder of the package "
        "implicitly holds the governance root."
    ),
    depends_on=("UL-G-01",),
    introduced_in="phase1",
)

CM_OP_01 = _reg(
    id="CM-OP-01",
    statement=(
        "Three-tier op jurisdiction is enforced by execute().  Tier 0 ops "
        "(gate_admit, gate_refuse) raise KernelInternalOp if externally called.  "
        "Tier 2 APPLICATION ops raise GovernanceNotFounded in UNINITIALIZED.  "
        "Single GovernanceKernel class — no class hierarchy."
    ),
    gate="three_tier_jurisdiction_gate",
    classification="ABI_CONFIG",
    adjacency_target=(
        "Flat dispatch surface — no jurisdiction typing; Tier 0 ops are "
        "externally reachable; Tier 2 ops execute in UNINITIALIZED; the "
        "three-tier constitutional separation becomes a comment."
    ),
    depends_on=("UL-S-03",),
    introduced_in="phase1",
)

# --- CHC: Cryptographic Homological Compilation invariants ---

CHC_S_01 = _reg(
    id="CHC-S-01",
    statement=(
        "Every receipt carries the THR-conformant binding structure: per-"
        "commitment hashes (H_s, H_c, H_m, and H_j when scope warrants), "
        "a binding root H_r = H(DS_r ∥ id(root_v1) ∥ root(leaves)) computed "
        "as a deterministic domain-separated hash tree over typed leaves, "
        "the binding mode declaration, and witness families pi_i per "
        "commitment. No receipt is admitted without H_s, H_c, H_m, and "
        "the H_r consistent with their merkle composition under the "
        "declared mode. (M2.3a: text declared constitutionally; runtime "
        "transition tracked across M2.3 subphases.)"
    ),
    gate="binding_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Flat-envelope binding — single hash collapses all commitments; "
        "selective disclosure impossible; per-leaf audit impossible; "
        "extension requires hashing everything together again."
    ),
    depends_on=(),
    introduced_in="phase1",
)

CHC_S_02 = _reg(
    id="CHC-S-02",
    statement=(
        "Each c_i canonicalization function (i ∈ {s, c, m, j}) is "
        "deterministic and byte-stable per THR §5: identical typed inputs "
        "produce byte-identical H_i. The merkle tree root(·) is deterministic: "
        "identical leaf set in canonical order produces byte-identical H_r. "
        "Reproducibility is testable without secret or external state."
    ),
    gate="determinism_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Non-deterministic binding — H_i or H_r varies between runs for "
        "identical typed inputs; reproducibility cannot be claimed; "
        "audit trails cannot be independently verified."
    ),
    depends_on=("CHC-S-01",),
    introduced_in="phase1",
)

CHC_S_03 = _reg(
    id="CHC-S-03",
    statement=(
        "Per-commitment independence and global nonrepudiation: altering "
        "the typed input to any one c_i changes that H_i without changing "
        "the others (cryptographic independence, THR §11); altering any "
        "leaf changes H_r (global nonrepudiation). The merkle structure "
        "enables per-leaf proof openings (selective disclosure) while "
        "preserving global tamper-evidence. The six decisional-independence "
        "counterexamples of §11 are exhibitable within UGK."
    ),
    gate="nonrepudiation_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Conflated binding — one or more c_i inputs share state, so altering "
        "one H_i shifts another; or the binding is repudiable because one "
        "or more typed inputs is not actually hashed."
    ),
    depends_on=("CHC-S-01",),
    introduced_in="phase1",
)


CHC_S_04 = _reg(
    id="CHC-S-04",
    statement=(
        "Commitment Minimality (THR §10.4): the leaf set under H_r contains "
        "only facts whose canonicalization input domain is not a subset of "
        "any other present leaf's input domain, except for entries explicitly "
        "registered in PRINCIPLED_REDUNDANCY_REGISTRY with a documented "
        "carrier leaf and threat-class identifier. The runtime gate enforces "
        "this predicate mechanically over receipt material and constitutional "
        "declarations alone; it does not judge threat-class novelty at runtime. "
        "Threat-class novelty for registry additions is a design-time obligation "
        "enforced by the Governor ADR protocol (threat_class field): a change "
        "to the leaf set, an expansion to c_i input domains, or a registry "
        "modification requires a documented attack scenario establishing the "
        "threat class is independent of existing coverage. Configuration "
        "parameters (binding mode) are recorded but not committed."
    ),
    gate="commitment_minimality_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Commitment-set bloat — leaves added without recoverability check; "
        "facts committed redundantly without registry justification; binding "
        "surface grows without corresponding threat-class coverage; future "
        "maintenance loses the principled rejection ground for 'just add "
        "another hash' requests."
    ),
    depends_on=("CHC-S-01",),
    introduced_in="phase1-m2",
)

# --- DM: Data Model invariants ---

DM_S_01 = _reg(
    id="DM-S-01",
    statement=(
        "Committed receipts cannot be retroactively modified.  The store is "
        "append-only.  Altering a stored semantic_hash or any stored field "
        "breaks verify_stream_hash() — retroactive modification is detected."
    ),
    gate="nonretroactivity_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Retroactively mutable ledger — stored receipts can be edited without "
        "detection; the audit trail is not tamper-evident; governance claims "
        "cannot be trusted after the fact."
    ),
    depends_on=("DM-S-03",),
    introduced_in="phase1",
)

DM_S_03 = _reg(
    id="DM-S-03",
    statement=(
        "All receipts are stream-chained: each receipt's H_c canonicalization "
        "input carries the prior receipt's H_r as `parent_H_r`. The chain is "
        "an input to the admissibility commitment, not a separate field; "
        "verify_stream_hash() recomputes the chain by recovering each receipt's "
        "parent_H_r from its H_c witness and confirming continuity from genesis "
        "to tip. The chain is unbroken iff every receipt's H_c witness opens "
        "to a parent_H_r matching its predecessor's H_r."
    ),
    gate="chain_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Unchained receipts — each receipt is independently hashed; "
        "insertion, deletion, and reordering of receipts are undetectable; "
        "the audit trail has no causal integrity."
    ),
    depends_on=("CHC-S-01",),
    introduced_in="phase1",
)

# --- CR: Classified Remainder invariants ---

CR_S_01 = _reg(
    id="CR-S-01",
    statement=(
        "CLASSIFIED_REMAINDERS (CR-01..CR-04) are declared in the kernel: "
        "OS layer, Python runtime, SQLite WAL, effect() internals.  "
        "These are honest gap declarations — not overclaimed, not hidden.  "
        "snapshot() and snapshot_fast() surface them via 'classified_remainders' key."
    ),
    gate="classified_remainders_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Undeclared governance gaps — the substrate makes no honest gap "
        "declaration; consumers cannot distinguish governed ignorance from "
        "ungoverned absence; the coverage claim is overclaimed."
    ),
    depends_on=(),
    introduced_in="phase1",
)

CR_S_02 = _reg(
    id="CR-S-02",
    statement=(
        "CLASSIFIED_REMAINDERS are inert — no capability flows from a declared "
        "gap.  CR-01..04 name boundaries; they do not enable workarounds.  "
        "A canary scenario that attempts to exploit CR-04 (effect() opaqueness) "
        "produces no additional governance capability."
    ),
    gate="canary_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Exploitable gap — a declared remainder enables a bypass; the gap "
        "declaration is a capability grant rather than an honest limitation."
    ),
    depends_on=("CR-S-01",),
    introduced_in="phase1",
)

# --- ESA: Epistemic SA invariants ---

ESA_S_01 = _reg(
    id="ESA-S-01",
    statement=(
        "GateRefusal is a first-class constitutive outcome.  A gate_refuse "
        "receipt is written to the store BEFORE GateRefusal is raised.  "
        "The refusal is observed, receipted, and causally chained — not silent."
    ),
    gate="refusal_gate",
    classification="MIXED",
    adjacency_target=(
        "Silent refusal — gate failures raise an exception without a receipt; "
        "refusals are not observable from the audit trail; coverage is "
        "unverifiable post-hoc."
    ),
    depends_on=("GK-S-01",),
    introduced_in="phase1",
)

# --- EH: Error Handling invariants ---

EH_S_01 = _reg(
    id="EH-S-01",
    statement=(
        "Typed exception hierarchy: KernelInternalOp (Tier 0 external call), "
        "GovernanceNotFounded (Tier 2 in UNINITIALIZED), UndeclaredOp "
        "(BS-01 violation), GateRefusal (gate returned False).  Each exception "
        "is distinct and catchable independently."
    ),
    gate="error_codes_gate",
    classification="ABI_CONFIG",
    adjacency_target=(
        "Undifferentiated exceptions — all governance errors raise a generic "
        "Exception or ValueError; callers cannot distinguish structural "
        "violations from gate refusals from undeclared ops."
    ),
    depends_on=("GK-S-01",),
    introduced_in="phase1",
)

EH_S_02 = _reg(
    id="EH-S-02",
    statement=(
        "Chain corruption recovery: last_valid_frontier() identifies the "
        "receipt_id of the last valid receipt before corruption begins.  "
        "Callers can pinpoint where the chain diverges and isolate valid history."
    ),
    gate="recovery_gate",
    classification="MIXED",
    adjacency_target=(
        "Opaque corruption — chain verification returns True/False with no "
        "frontier identification; corrupted chains cannot be triaged or "
        "partially recovered."
    ),
    depends_on=("DM-S-03",),
    introduced_in="phase1",
)

# --- ADV: Adversarial resistance invariants ---

ADV_S_01 = _reg(
    id="ADV-S-01",
    statement=(
        "Four adversarial rug-pulls are each detected: "
        "(1) CHC field tamper changes semantic_hash, "
        "(2) GOVERNANCE_OPS runtime tamper raises UndeclaredOp, "
        "(3) Grundnorm file tamper breaks grundnorm_readonly_gate, "
        "(4) stored chain hash tamper breaks verify_stream_hash().  "
        "All four on throwaway state — no shipped state touched."
    ),
    gate="rugpull_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Undetected rug-pull surface — one or more of the four adversarial "
        "perturbations passes silently; the governance guarantee it corresponds "
        "to is asserted but not tested."
    ),
    depends_on=("CHC-S-01", "DM-S-03", "UL-G-01"),
    introduced_in="phase1",
)

# --- CM-DIM: Dimension invariants ---

CM_DIM_01 = _reg(
    id="CM-DIM-01",
    statement=(
        "Every Dimension in dimensions.py has its current selection within "
        "the admissible set and outside the inadmissible set.  Dimensional "
        "selection tests are first-class @gate_test gates, not prose assertions."
    ),
    gate="dimension_selection_gates",
    classification="ABI_CONFIG",
    adjacency_target=(
        "Unvalidated configuration — dimension selections are not tested; "
        "an inadmissible selection could be deployed without detection; "
        "the CM provides no enforceable bounds."
    ),
    depends_on=(),
    introduced_in="phase1",
)

# --- CTR: Test Runner invariants ---

CTR_S_07 = _reg(
    id="CTR-S-07",
    statement=(
        "Staleness gate: a SHA-256 pin of invariants.py content is maintained.  "
        "If invariants.py changes without a corresponding pin update, the gate "
        "detects constitutional drift.  ACTIVE receipts carry law_hash = "
        "SHA-256(invariants.py), making every receipt self-situating."
    ),
    gate="staleness_gate",
    classification="MIXED",
    adjacency_target=(
        "Constitutional drift — invariants.py can be modified without detection; "
        "the executed spec and the declared spec diverge silently; receipts "
        "do not record which invariant set governed them."
    ),
    depends_on=("CM-GS-01",),
    introduced_in="phase1",
)

CTR_S_01 = _reg(
    id="CTR-S-01",
    statement=(
        "The invariant registry (this file) IS the coverage map.  Every "
        "Invariant has a bound gate name.  CTR iterates the registry directly "
        "and detects unbound invariants.  No JSON binding layer can drift "
        "from the implementation."
    ),
    gate="invariant_registry_gate",
    classification="MIXED",
    adjacency_target=(
        "Drifted coverage map — invariants are declared in one artifact and "
        "bound in another; the two can diverge silently; coverage claims "
        "are not derived from the live implementation."
    ),
    depends_on=(),
    introduced_in="phase1",
)

# --- SRSA: Situational Awareness invariants ---

SRSA_S_01 = _reg(
    id="SRSA-S-01",
    statement=(
        "ugk.srsa_vector() returns a valid 10-axis SRSA vector for this kernel "
        "instance.  AdSA, ASA, CSA, PSA axes are lit by UGK natively.  "
        "ESA and FSA are partially lit.  ISA and LSA are honest zeros.  "
        "The vector provides a declared baseline for any UGK consumer."
    ),
    gate="srsa_vector_gate",
    classification="MIXED",
    adjacency_target=(
        "Dark SRSA baseline — no SRSA vector is derivable from UGK import alone; "
        "consumers must instrument every axis from scratch; there is no "
        "inherited governance floor."
    ),
    depends_on=(),
    introduced_in="phase1",
)

# --- Performance / Liveness ---

UL_L_01 = _reg(
    id="UL-L-01",
    statement=(
        "All UGK modules import in a single Python process without side effects.  "
        "Import-time execution is limited to dataclass/constant definitions.  "
        "No I/O, no subprocess spawning, no global state mutation on import."
    ),
    gate="liveness_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Heavy-import substrate — importing ugk triggers I/O, network calls, "
        "or subprocess spawning; the package cannot be safely imported in "
        "constrained or sandboxed environments."
    ),
    depends_on=("UL-S-01",),
    introduced_in="phase1",
)

# --- Phase 6: Constitutional Legend invariants ---

LEGEND_S_01 = _reg(
    id="LEGEND-S-01",
    statement=(
        "The LEGEND constant in binding.py is content-addressed and stable. "
        "LEGEND_HASH = SHA-256(canonical_json(entries sorted by csil_id)). "
        "LEGEND_BY_ID and LEGEND_BY_SLUG are bidirectionally consistent. "
        "LEGEND is entirely derivable from existing Grundnorm files."
    ),
    gate="legend_hash_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Unstable or unaddressed vocabulary — compression symbols cannot be "
        "verified; legend drift is undetectable; receipts lose their "
        "projection vocabulary anchor."
    ),
    depends_on=("UL-G-01",),
    introduced_in="phase6",
)

LEGEND_S_02 = _reg(
    id="LEGEND-S-02",
    statement=(
        "store.write(compress=True) stores CSIL integers for op/intent/jurisdiction/"
        "confidence fields. all_receipts() expands them back to canonical strings. "
        "Roundtrip is lossless for all fixed vocabulary terms. "
        "Unregistered terms are rejected fail-closed, not silently stored."
    ),
    gate="compression_roundtrip_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Silent symbol corruption — unrecognized render strings are stored without "
        "error; decompressed receipts return wrong values; chain verification "
        "silently passes corrupted content."
    ),
    depends_on=("LEGEND-S-01",),
    introduced_in="phase6",
)

LEGEND_S_03 = _reg(
    id="LEGEND-S-03",
    statement=(
        "legend_hash appears in the dm_s03 CHC envelope on ACTIVE receipts. "
        "Altering any LEGEND entry changes LEGEND_HASH and therefore "
        "semantic_hash — the projection vocabulary is tamper-evident. "
        "legend_hash is present and correct in kernel.snapshot_fast() after ceremony."
    ),
    gate="legend_chc_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Unbound projection vocabulary — the legend can be changed without "
        "affecting any receipt hash; vocabulary drift is undetectable from "
        "the receipt chain; semantic participation claims are unverifiable."
    ),
    depends_on=("CHC-S-01", "LEGEND-S-01"),
    introduced_in="phase6",
)

LEGEND_S_04 = _reg(
    id="LEGEND-S-04",
    statement=(
        "Every compressed receipt field value has a valid LEGEND_BY_SLUG entry. "
        "No receipt stores unregistered CSIL integers. "
        "Projection continuity is verified at write time: any attempt to store "
        "a symbol outside the governed vocabulary raises an error."
    ),
    gate="projection_continuity_gate",
    classification="MIXED",
    adjacency_target=(
        "Ungoverned projection — receipts contain symbols with no declared "
        "constitutional participation; the admissibility of field values cannot "
        "be verified; the legend governance claim is nominal, not structural."
    ),
    depends_on=("LEGEND-S-02",),
    introduced_in="phase6",
)

# --- Phase 6: Decision Warrant invariants ---

DW_S_01 = _reg(
    id="DW-S-01",
    statement=(
        "DecisionWarrant is a first-class content-addressed artifact. "
        "warrant_hash = SHA-256(canonical_json(body fields)). "
        "constitutional_basis cites CSIL integer addresses from LEGEND. "
        "Receipts may carry warrant_id. WarrantStore is append-only and "
        "permits lineage traversal via prior_warrant_hash links."
    ),
    gate="warrant_gate",
    classification="MIXED",
    adjacency_target=(
        "Ephemeral admissibility reasoning — why an operation was admitted "
        "is lost after execution; audit queries about constitutional basis "
        "are unanswerable from the receipt store alone; warrants exist only "
        "as implicit gate return values."
    ),
    depends_on=("LEGEND-S-01", "UL-S-02"),
    introduced_in="phase6",
)

DW_S_02 = _reg(
    id="DW-S-02",
    statement=(
        "The warrant DAG is acyclic. basis_query(csil_id) returns all warrants "
        "whose constitutional_basis includes that CSIL identity. "
        "basis_query_for_law(csil_id, law_hash) filters by constitutional frame. "
        "lineage_from(warrant_hash) traverses the prior_warrant_hash chain "
        "to genesis. Results are correct, complete, and deterministic."
    ),
    gate="warrant_lineage_gate",
    classification="MIXED",
    adjacency_target=(
        "Flat warrant records — warrants are isolated; amendment queries "
        "cannot be answered; constitutional lineage is unavailable; "
        "the governed reasoning graph is a list, not a DAG."
    ),
    depends_on=("DW-S-01",),
    introduced_in="phase6",
)


# --- Phase 7: Persistence ---

PERSIST_S_01 = _reg(
    id="PERSIST-S-01",
    statement=(
        "UGKReceiptStore opened on an existing database hydrates _prior_hash "
        "from the chain tip (latest semantic_hash), not from genesis. "
        "Chain integrity is maintained across process restarts. "
        "A new receipt written in a fresh process links correctly to the prior chain."
    ),
    gate="persistence_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Single-process-only substrate — the chain breaks on every process restart; "
        "verify_stream_hash() fails after any CLI invocation that reopens the store; "
        "UGK cannot serve as a durable governance substrate."
    ),
    depends_on=("DM-S-03",),
    introduced_in="phase7",
)

# --- Phase 8: Audit infrastructure ---

AUDIT_S_01 = _reg(
    id="AUDIT-S-01",
    statement=(
        "AuditSession is a read-only governed surface. It must never call "
        "store.write(), kernel.execute(), or any method that produces receipts, "
        "warrants, or modifications to any store. All public methods are queries. "
        "Enforced behaviorally: calling all public methods leaves receipt_count() "
        "and warrant_count() unchanged."
    ),
    gate="audit_session_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Read-write audit session — audit passes can corrupt the chain being audited; "
        "the separation between operational and audit roles is lost; audit receipts "
        "pollute the causal chain with observer effects."
    ),
    depends_on=("DW-S-01", "LEGEND-S-01"),
    introduced_in="phase8",
)

AUDIT_S_02 = _reg(
    id="AUDIT-S-02",
    statement=(
        "The legend_archive table in ugk.db contains every LEGEND version by "
        "legend_hash. A legend_seal receipt is emitted at ceremony and the full "
        "entries are inserted into legend_archive. AuditSession.resolve_legend() "
        "resolves any receipt's legend_hash to the legend that governed it. "
        "LegendNotResolvable is raised for an unknown hash."
    ),
    gate="legend_archive_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Legend opacity — old receipts with a non-current legend_hash are "
        "uninterpretable; CSIL integers cannot be expanded; the audit pass "
        "cannot reconstruct the vocabulary under which those receipts were admitted."
    ),
    depends_on=("LEGEND-S-01",),
    introduced_in="phase8",
)

AUDIT_S_03 = _reg(
    id="AUDIT-S-03",
    statement=(
        "AuditSession.receipts_for_warrant(warrant_hash) returns a correct, "
        "complete list of receipts whose warrant_id equals warrant_hash. "
        "The reverse warrant->receipts linkage is navigable from a cold store."
    ),
    gate="receipts_for_warrant_gate",
    classification="MIXED",
    adjacency_target=(
        "One-way warrant linkage — receipts know their warrant, but the warrant "
        "cannot enumerate its dependent receipts; the governed reasoning graph "
        "is navigable only downward, not upward."
    ),
    depends_on=("DW-S-01",),
    introduced_in="phase8",
)

# --- Phase 9: Document type completion ---

DW_S_03 = _reg(
    id="DW-S-03",
    statement=(
        "Refusal warrants are produced when gate() returns False and warrant_basis "
        "is provided by the caller. The refusal warrant is written to WarrantStore "
        "before GateRefusal is raised (NBER-1 ordering). result=RESULT_REFUSE. "
        "Refusal warrants are first-class artifacts; the warrant taxonomy is "
        "symmetric: every governance decision in both directions is documented."
    ),
    gate="refusal_warrant_gate",
    classification="MIXED",
    adjacency_target=(
        "Admission-only warrant record — refusals are undocumented; the warrant "
        "store only explains what was admitted, never what was blocked; audit "
        "queries cannot answer which constitutional conditions caused a refusal."
    ),
    depends_on=("DW-S-01", "GK-S-01"),
    introduced_in="phase9",
)

AMD_S_01 = _reg(
    id="AMD-S-01",
    statement=(
        "AmendmentRecord is a first-class content-addressed artifact documenting "
        "each law_hash transition. amendment_hash = SHA-256(canonical_json(body)). "
        "Records are stored in genesis/AMENDMENTS.json (append-only). "
        "Each record cites prior_law_hash, successor_law_hash, invariants_added, "
        "invariants_removed, authority, Governor signature, amendment_kind "
        "(genesis|ordinary), and OPTIONAL committed prior/successor values for any "
        "additional moved frame leg (legend_hash, schema_hash) — all committed in the "
        "signed/hashed body. Uncommitted legs are OMITTED from the canonical body, so a "
        "record that moves only the law leg is byte-identical to the pre-generalization "
        "form (backward-compatible). A record MAY additionally commit prior_amendment_hash "
        "(the predecessor record's amendment_hash), forming a tamper-evident record-hash "
        "chain that is ADDITIVE to — and never replaces — the authoritative law-hash lineage. "
        "This commitment is FORWARD-ONLY: genesis and pre-existing records do not carry it "
        "(omitted from the body, hashes preserved, no retroactive rehashing), so the "
        "record-hash chain is verified only where committed while law-hash lineage remains "
        "authoritative throughout."
    ),
    gate="amendment_record_gate",
    classification="MIXED",
    adjacency_target=(
        "Implicit constitutional transitions — law_hash changes are detectable from "
        "the receipt chain but unexplained; the narrative of what changed and why is "
        "lost; constitutional lineage cannot be reconstructed without the build logs."
    ),
    depends_on=("CTR-S-07",),
    introduced_in="phase9",
)

AMD_S_02 = _reg(
    id="AMD-S-02",
    statement=(
        "Amendment-model-at-inception: the DeploymentManifest declares "
        "amendment_model in {higher_root, self} at the founding constitutional act, "
        "committed in manifest_hash and carried on session_open. UGK declares "
        "higher_root: runtime self-amendment is precluded by UL-G-01 (Grundnorm 444), "
        "so constitutional-frame transitions are performed by the higher (deploy) root "
        "and admitted under AMD-S-03. 'self' is a declarable-but-unused option preserved "
        "for substrate neutrality."
    ),
    gate="amendment_model_gate",
    classification="MIXED",
    adjacency_target=(
        "Undeclared amendment authority — the recursion boundary is implicit; a reader "
        "cannot tell whether amendment is self-governed or higher-root, and the location "
        "of amendment authority is unauditable."
    ),
    depends_on=("CHARTER-S-01", "CHARTER-S-02"),
    introduced_in="phase17",
)

AMD_S_03 = _reg(
    id="AMD-S-03",
    statement=(
        "Amendment admissibility (frame-general): a constitutional-frame transition "
        "c_n -> c_{n+1} is ADMITTED iff an AmendmentRecord satisfies, fail-closed: "
        "(1) prior frame == c_n frame triad; (2) for EVERY frame leg "
        "(law_hash, legend_hash, schema_hash): if the record COMMITS that leg "
        "(prior/successor present), its committed successor equals the actual c_{n+1} "
        "leg-value (AUTHORITATIVE) and its committed prior equals the c_n leg-value; if the "
        "record does NOT commit that leg, the leg must be UNCHANGED across the transition. "
        "Admissibility is thereby genuinely frame-general — any leg may move iff a committed "
        "record represents it. The successor-frame-leg hash is the authoritative transition "
        "proof and uniformly covers invariant additions, removals, AND modifications; "
        "invariants_added/invariants_removed are DOCUMENTARY only; "
        "(3) ERA-APPROPRIATE Governor authority: the authorizing key, identified by "
        "authority = SHA-256(signing pubkey), must be the era-appropriate key authorized by "
        "the succession lineage (SUCC-S-01) — the genesis key or a validly predecessor-signed "
        "successor — and its Ed25519 signature must verify over the canonical body under THAT "
        "key; after a Governor key rotation only the active successor key authorizes NEW "
        "amendments, while historical records remain valid under their era key (strict era); "
        "(4) append-only lineage (prior == predecessor successor or the genesis anchor; "
        "successor not already present; and where a record commits prior_amendment_hash it must "
        "equal the predecessor record amendment_hash — additive record-hash lineage, law-hash "
        "lineage authoritative); (5) amendment_kind in {genesis, ordinary} is "
        "committed in the signed body; (6) model-conformance with AMD-S-02. The genesis "
        "amendment (kind=genesis, the unique record installing AMD-S-02 and AMD-S-03) is "
        "the installation of admissibility itself and is admitted as the genesis case; "
        "every subsequent amendment is judged by the installed relation. Continuity then "
        "holds across a frame change iff the change is a validly admitted amendment "
        "(frame equality OR valid constitutional transition)."
    ),
    gate="amendment_admissibility_gate",
    classification="MIXED",
    adjacency_target=(
        "Recorded-but-not-admitted transitions — a law_hash change is documented yet "
        "never tested for admissibility, so an unauthorized or inconsistent frame change "
        "can masquerade as a legitimate amendment and continuity cannot distinguish them."
    ),
    depends_on=("AMD-S-01", "AMD-S-02", "CTR-S-07"),
    introduced_in="phase17",
)

NS_S_01 = _reg(
    id="NS-S-01",
    statement=(
        "Namespace OWNERSHIP is a deterministic receipt-chain projection: owner_of(name) is "
        "derived by folding the receipt chain (namespace_governance.project_owners); the "
        "projection is stable/deterministic; there is NO ownership table (schema_hash-invariant). "
        "Ownership is DISTINCT from MEMBERSHIP (invariants.NAMESPACE_PHI_0), which remains the "
        "constitutional set of valid name_keys; the two must not be conflated."
    ),
    gate="namespace_governance_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Ownership treated as ambient/implicit state — without a deterministic receipt-chain "
        "projection, ownership cannot be reconstructed or audited, and membership and ownership "
        "blur into one undistinguished namespace concept."
    ),
    depends_on=("CM-OP-01", "DKN-S-01"),
    introduced_in="phase20",
)

NS_S_02 = _reg(
    id="NS-S-02",
    statement=(
        "namespace_claim and namespace_allocate are DISTINCT receipted transitions and MUST NOT "
        "be collapsed into one op (FGA §10). A claim does not by itself grant ownership; "
        "allocation does. The distinctness is constitutional, not an implementation convenience."
    ),
    gate="namespace_governance_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Collapsing claim and allocation — a single combined op erases the intent/grant boundary "
        "FGA §10 requires, making contested or speculative claims indistinguishable from granted "
        "ownership."
    ),
    depends_on=("NS-S-01",),
    introduced_in="phase20",
)

NS_S_03 = _reg(
    id="NS-S-03",
    statement=(
        "Allocation conflict policy is REFUSE (fail-closed v0): a colliding allocation — the SAME "
        "canonical name (namespace_governance.canonicalize) by a DIFFERENT authority — is "
        "gate_refused (a gate_refuse receipt is emitted) and leaves ownership unchanged, with "
        "exactly one successful allocation per canonical name. Receipt conflict is NOT namespace "
        "conflict: distinct canonical names both allocate."
    ),
    gate="namespace_governance_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Silent or last-writer-wins allocation — without a fail-closed REFUSE on canonical-name "
        "collision, ownership becomes racy and a later allocation can silently override an "
        "established owner."
    ),
    depends_on=("NS-S-01", "NS-S-02"),
    introduced_in="phase20",
)

NS_S_04 = _reg(
    id="NS-S-04",
    statement=(
        "Namespace ownership-lifecycle operations — delegation, revocation, invalidation, and "
        "supersession — take effect only when the receipt authority is the current owner of the "
        "canonical name. A non-owner lifecycle operation is fail-closed, refused, and never folded, "
        "leaving ownership unchanged. Delegation grants scoped authority without transferring "
        "ownership and does not itself confer lifecycle authority. Supersession transfers ownership "
        "to a named new owner. Delegation and supersession must not be collapsed."
    ),
    gate="namespace_governance_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Delegated or non-owner lifecycle authority — if a delegate or stranger could revoke, "
        "invalidate, supersede, or adjudicate, ownership control would leak beyond the owner and "
        "delegation would silently become ownership."
    ),
    depends_on=("NS-S-01", "NS-S-03"),
    introduced_in="namespace-2bc",
)

NS_S_05 = _reg(
    id="NS-S-05",
    statement=(
        "Revocation and invalidation permanently remove a canonical name from ownership under the "
        "WILL-S-04 permanence pattern. A revoked or invalidated name is never re-granted by later "
        "allocation, supersession, or adjudication. Expiration is not a separate primitive; it is "
        "only a removal reason folded onto revocation or invalidation. The ownership projection reads "
        "no wall-clock and admits no TTL, expiry, or expires_at field."
    ),
    gate="namespace_governance_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Reversible removal or clock-based expiry — an un-revoke, resurrection, or TTL/expires_at "
        "field would let removed ownership silently return and would inject wall-clock "
        "nondeterminism into the receipt-chain projection."
    ),
    depends_on=("NS-S-01", "NS-S-04", "WILL-S-04"),
    introduced_in="namespace-2bc",
)

NS_S_06 = _reg(
    id="NS-S-06",
    statement=(
        "Adjudication of a contested canonical name is constitutional-Governor-only. A non-Governor "
        "adjudication is fail-closed, refused, and never folded. Adjudication cannot resurrect a "
        "revoked or invalidated name; NS-S-05 remains absolute."
    ),
    gate="namespace_governance_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Non-Governor adjudication or resurrection — if any authority could award a contested name, "
        "or if adjudication could revive a removed name, the constitutional-root override and the "
        "permanence guarantee would both be defeated."
    ),
    depends_on=("NS-S-04", "NS-S-05"),
    introduced_in="namespace-2bc",
)

TO_S_01 = _reg(
    id="TO-S-01",
    statement=(
        "Where a receipt commits a terminal-outcome projection under UGK-BODY version >= 2, the "
        "committed projection tuple — terminal_outcome, terminal_outcome_model_id, and "
        "terminal_outcome_reason — must correspond to the kernel's actual decision signal for that "
        "receipt, recomputed from stored fields under the declared terminal-outcome model. "
        "op==\"gate_refuse\" corresponds to REFUSE; op==\"protocol_error\" corresponds to "
        "STRUCTURAL_ERROR with the preserved protocol/error reason; otherwise the operation "
        "corresponds to ADMIT. The committed projection ratifies the kernel decision; it does not "
        "replace the kernel decision path as authority and adds no new refusal cause. A committed "
        "projection that does not correspond to the recomputed signal is a constitutional integrity "
        "violation: a corrupt, non-conformant receipt that fails closed at verification, not a "
        "re-decision of the operation. A post-admit effect abort (failed=True after admission) "
        "remains ADMIT with an admitted-effect-aborted reason; correspondence binds the admissibility "
        "decision, not effect success. A receipt commits DEFER as its terminal outcome IF AND ONLY IF it "
        "commits a valid HELD continuation record (UGK-BODY-v7): continuation_id recomputes from the captured "
        "operation payload plus anchor, continuation_state == 'HELD', continuation_model_id == "
        "'continuation_record_model_v1', and continuation_expiry_basis is committed-evidence-only "
        "({receipt_height | explicit_trigger}, never wall-clock). A DEFER receipt WITHOUT a valid HELD "
        "continuation record is a constitutional integrity violation that fails closed at verification. DEFER "
        "ratifies a DEFERRED decision -- the operation is held pending resume / resolve / expire under "
        "DEFER-S-01 -- and adds NO new refusal cause and does NOT alter the gate_refuse->REFUSE, "
        "protocol_error->STRUCTURAL_ERROR, otherwise->ADMIT correspondence above. A receipt commits BRIDGE "
        "as its terminal outcome IF AND ONLY IF it commits a valid UGK-BODY-v8 bridge surface that verifies "
        "under BRIDGE-BINDING at emit, reached ONLY via the kernel's explicit opt-in bridge path (the kernel "
        "never spontaneously bridges). A BRIDGE receipt WITHOUT a committed bridge surface that verifies under "
        "BRIDGE-BINDING is a constitutional integrity violation that fails closed at verification (an invalid "
        "bridge surface refuses/errors, never ADMITs). BRIDGE ratifies an audited regime crossing "
        "(permit-with-audit) and adds NO new refusal cause and does NOT alter the gate_refuse->REFUSE, "
        "protocol_error->STRUCTURAL_ERROR, otherwise->ADMIT, or DEFER correspondences above; BRIDGE is a "
        "DISTINCT terminal outcome (not ADMIT, REFUSE, locality-refuse, DEFER, STRUCTURAL_ERROR, or CRISIS). "
        "CRISIS remains reserved and "
        "fails closed until its support record exists. v1 receipts that do not commit terminal-outcome fields "
        "are not reinterpreted."
    ),
    gate="terminal_outcome_commit_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "A committed terminal-outcome projection that diverges from the kernel decision — a forged "
        "or corrupted outcome, model id, or reason — would let a receipt misreport the constitutional "
        "decision while still verifying, puncturing diagnostic specificity and the integrity claim."
    ),
    depends_on=("IEL-S-01", "CTR-S-01"),
    introduced_in="terminal-outcome-correspondence",
)

DEFER_S_01 = _reg(
    id="DEFER-S-01",
    statement=(
        "The DEFER continuation lifecycle. A live DEFER terminal (per TO-S-01) emits a HELD continuation "
        "record capturing the deferred operation's re-entry data (op, authority, parameters, jurisdiction) "
        "and a deterministic committed-evidence expiry basis ({receipt_height | explicit_trigger}; never "
        "wall-clock). The lifecycle is APPEND-ONLY: HELD -> {RESUMED, EXPIRED, REFUSED}, and a RESUMED "
        "continuation -> RESOLVED. Every transition is a LATER receipt that SHARES the same continuation_id; "
        "no transition mutates the creating record. RESUME re-enters governance by re-invoking the kernel's "
        "W/G/E execute() path on the captured operation with NO bypass of admission: the resumed operation "
        "runs the full gate / aggregation / admit path and its ordinary terminal outcome -- ADMIT, REFUSE, or "
        "STRUCTURAL_ERROR per TO-S-01 -- IS the RESOLVE. EXPIRE is a PURE FUNCTION of committed chain evidence "
        "(the recorded expiry basis against the committed receipt height, or an explicit committed trigger), "
        "deterministic and recomputable; it never consults ambient time. A continuation that is invalid, "
        "malformed, already terminal (RESOLVED / EXPIRED / REFUSED), or expired REFUSES cleanly rather than "
        "resuming. The DEFER lifecycle adds NO new refusal cause beyond the existing constitutional-refusal "
        "vocabulary and does NOT alter ADMIT / REFUSE / STRUCTURAL_ERROR semantics. CRISIS remains reserved "
        "and out of scope. A transition that mutates a prior record, resumes without re-entering execute(), "
        "resolves to a non-ordinary outcome, or expires by ambient time is a constitutional integrity "
        "violation that fails closed at verification."
    ),
    gate="defer_lifecycle_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "A DEFER that emitted without a valid HELD continuation, a resume that bypassed the gate/admit path, "
        "an expiry decided by wall-clock, or a transition that mutated the creating record would let a "
        "deferred decision escape governance or become non-deterministic -- a reserved outcome going live "
        "without the discipline that makes it safe."
    ),
    depends_on=("TO-S-01", "CTR-S-01"),
    introduced_in="defer-continuation-lifecycle",
)

BRIDGE_BINDING = _reg(
    id="BRIDGE-BINDING",
    statement=(
        "BRIDGE surface-validity binding (CK-BRIDGE Stage 3, law leg; UGK-BODY-v8). A receipt that "
        "carries the committed v8 bridge surface is VALID under BRIDGE-BINDING if and only if its "
        "committed BridgeRecord verifies deterministically: (a) all six bridge fields are present and "
        "well-formed; (b) source and target regime refs are DISTINCT; (c) the downgrade reason is in the "
        "closed taxonomy {jurisdiction_crossing, semantic_downgrade, regime_translation}; (d) the committed "
        "bridge_record_id equals the MCIR-derived identity of the refs; (e) source and target structurally "
        "DIVERGE under MCIR; (f) the transformation ref resolves as a valid MCIR transformation artifact; "
        "and (g) the preserved-evidence ref resolves under SMH READ-ONLY verification. Verification is "
        "KERNEL-FREE and DETERMINISTIC given receipt state plus injected read-only resolver results: UGK "
        "imports neither MCIR nor SMH; the verification context supplies the resolvers. SMH resolution is "
        "read-only ref-resolution and NEVER becomes authority; MCIR remains representation, never authority; "
        "MCIR artifact bodies remain external and unembedded (only refs/hashes are committed). A bridge "
        "surface that fails any clause is REFUTED / inadmissible at verification (fail-closed). This binds "
        "SURFACE VALIDITY and (CK-BRIDGE Stage 4 / r162) ACTIVATES the terminal-outcome correspondence: a "
        "BRIDGE terminal outcome (per TO-S-01) is committed IF AND ONLY IF its committed v8 bridge surface "
        "verifies under BRIDGE-BINDING at emit, reached ONLY via the kernel's explicit opt-in bridge path. The "
        "kernel NEVER spontaneously bridges; an invalid or unverifiable bridge surface refuses/errors "
        "fail-closed and NEVER ADMITs. Emit-time verification is the same kernel-free, deterministic, "
        "resolver-parameterized check (UGK imports neither MCIR nor SMH; resolvers are read-only; SMH is never "
        "authority; MCIR is representation, never authority; MCIR/SMH bodies are never embedded). This invariant "
        "adds NO new refusal cause and does NOT alter ADMIT / REFUSE / DEFER / STRUCTURAL_ERROR semantics."
    ),
    gate="bridge_binding_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "A committed bridge surface that verified WITHOUT BRIDGE-BINDING — a forged BridgeRecord identity, "
        "an undiverged or identical source/target, an unresolvable transformation, or a preserved-evidence "
        "ref that resolves to nothing — would let a receipt assert an audited regime crossing that never "
        "structurally occurred, hollowing out the citation guarantee while still verifying."
    ),
    depends_on=("CTR-S-01",),
    introduced_in="bridge-binding-law",
)

EFFECT_S_01 = _reg(
    id="EFFECT-S-01",
    statement=(
        "Effect-trail integrity (marker-era). SCOPE: receipts at body-schema version < 5, whose effect "
        "trail is recorded in the parameter MARKERS. (Body-schema version >= 5 retires the marker mirror "
        "under AD-65; for those receipts the typed effect columns are the sole committed structural "
        "effect surface and EFFECT-S-02 is the authoritative effect-trail-integrity surface. This "
        "invariant does NOT apply to v>=5 receipts -- it is not vacuously satisfied there, it is out of "
        "scope by construction.) Within scope: where a receipt declares an effect atomicity class or "
        "effect phase, "
        "the recorded effect trail must conform to the realized protocol for that class. This is a "
        "class-relative trail-integrity claim, NOT a claim that every effect is atomic. PURE and "
        "STORE_LOCAL effects may assert rollback-backed atomicity through the store-local seam. "
        "EXTERNAL_IRREVERSIBLE effects must follow the PREPARE / COMMIT / ABORT / in-doubt trail "
        "discipline. EXTERNAL_REVERSIBLE effects must follow the PREPARE / COMMIT / ABORT trail plus "
        "the separately governed COMPENSATE / COMPENSATED / COMPENSATION_FAILED compensation trail "
        "discipline. COMMIT, ABORT, COMPENSATED, and COMPENSATION_FAILED terminals must be anchored "
        "to their corresponding prior intent records (PREPARE for forward terminals; COMPENSATE for "
        "compensation terminals). A successful terminal must not be recorded as if an effect or "
        "compensation succeeded when it did not. Orphan PREPARE and orphan COMPENSATE states are "
        "honest in-doubt residues and are detector-reported, not auto-resolved, and are not "
        "themselves trail corruption. COMPENSATED records an offsetting action, not erasure of the "
        "original COMMIT, which remains historically true. COMPENSATION_FAILED records unresolved "
        "execution failure, not a constitutional REFUSE. NON_ATOMIC remains an explicit bridge and "
        "must not claim effect-trail compliance beyond its declared non-atomic posture. A recorded "
        "effect trail that is class-mismatched, records a terminal with no anchoring intent record, "
        "or records a false success is a constitutional integrity violation: a corrupt, non-conformant "
        "trail that fails closed at verification, not a re-decision of the operation. This invariant "
        "ratifies the realized effect-class wiring; it adds no new refusal cause and does not mutate "
        "terminal-outcome semantics (a post-admit effect abort remains ADMIT, never REFUSE)."
    ),
    gate="effect_trail_integrity_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "A recorded effect trail that misreports its class -- a false COMMIT with no PREPARE, a "
        "success terminal for an effect that did not perform, a COMPENSATED that erases the original "
        "COMMIT, or a NON_ATOMIC effect dressed as a two-phase trail -- would let a receipt claim a "
        "stronger atomicity/offset guarantee than the substrate provides while still verifying, "
        "puncturing the honest in-doubt residue and the class-relative integrity claim."
    ),
    depends_on=("IEL-S-01", "GK-S-02"),
    introduced_in="effect-trail-integrity",
)

EFFECT_S_02 = _reg(
    id="EFFECT-S-02",
    statement=(
        "Typed-column effect-trail integrity (v>=4). For receipts at body-schema version 4 or later "
        "that declare an effect atomicity class, the AUTHORITATIVE effect-trail integrity surface is "
        "the body-committed typed effect columns (effect_atomicity, effect_phase, effect_prepare_ref, "
        "effect_compensate_ref, effect_idempotency_key, effect_compensation_idempotency_key, "
        "effect_abort_reason, effect_gate_admit_ref, under effect_atomicity_model_v1), recomputed with "
        "the SAME class-relative discipline EFFECT-S-01 applies to the parameter markers: PURE and "
        "STORE_LOCAL may assert rollback-backed atomicity through the store-local seam; "
        "EXTERNAL_IRREVERSIBLE must follow the PREPARE / COMMIT / ABORT / in-doubt trail; "
        "EXTERNAL_REVERSIBLE must follow that forward trail plus the separately governed COMPENSATE / "
        "COMPENSATED / COMPENSATION_FAILED compensation trail; COMMIT, ABORT, COMPENSATED, and "
        "COMPENSATION_FAILED terminals must anchor to their prior intent columns (the typed PREPARE "
        "columns for forward terminals; the typed COMPENSATE columns for compensation terminals); a "
        "success terminal must not be recorded for an effect or compensation that did not perform; "
        "orphan PREPARE and orphan COMPENSATE remain honest in-doubt residues, detector-reported and "
        "not auto-resolved; COMPENSATED records an offsetting action, not erasure of the original "
        "COMMIT, which stays historically true; COMPENSATION_FAILED records unresolved execution "
        "failure, not a constitutional REFUSE. EFFECT-S-02 binds the TYPED COLUMNS; EFFECT-S-01 remains "
        "the marker-layer invariant and continues to govern receipts below version 4 (EFFECT-S-02 is "
        "NON-RETROACTIVE: v<4 receipts carry no typed surface and stay under EFFECT-S-01 marker "
        "semantics). For v>=4 receipts the typed columns and the parameter markers MUST agree -- the "
        "r134 marker<->column consistency bridge -- and a divergence is a corrupt receipt that fails "
        "closed. The typed columns are authoritative for the STRUCTURAL trail only; the "
        "no-physical-erasure prohibition (a COMPENSATED must not assert undone / reversed / erased / "
        "rolled_back) has NO typed column and is retained as a BOUNDED parameter-hygiene residual -- "
        "EFFECT-S-02 makes NO claim of pure column closure while that residual marker read remains. "
        "EFFECT-S-02 ADDS NO NEW REFUSAL CAUSE and does not mutate terminal-outcome semantics (TO-S-01): "
        "a post-admit effect abort remains ADMIT, never REFUSE. It ratifies the r134 v4 typed surface as "
        "the trail-integrity authority for v>=4 receipts; it moves neither schema nor legend."
    ),
    gate="effect_trail_integrity_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "If the typed effect columns could verify a trail that the parameter markers would reject (or "
        "vice versa) without the divergence failing closed, a v>=4 receipt could present a structurally "
        "false trail through whichever surface law happened to read -- a typed COMMIT with no typed "
        "PREPARE anchor, a typed COMPENSATED diverging from its marker, or a column set inconsistent "
        "with the body-committed markers -- letting a receipt claim a stronger atomicity/offset "
        "guarantee through the typed surface than the substrate provides while still verifying."
    ),
    depends_on=("IEL-S-01", "EFFECT-S-01"),
    introduced_in="typed-effect-law-leg",
)

RECON_S_01 = _reg(
    id="RECON-S-01",
    statement=(
        "Verified-grade reconciliation self-containment (opt-in). For a reconciling terminal that commits "
        "reconciliation_grade == 'verified', the receipt MUST be SELF-VERIFYING from its own committed "
        "state ALONE, with NO WarrantStore resolution: (a) reconciliation_warrant_snapshot is present and "
        "non-empty; (b) SHA-256(reconciliation_warrant_snapshot) == the committed warrant_id -- the snapshot "
        "is the verbatim canonical warrant body, so its content-address binds it to the cited warrant; (c) "
        "the snapshot's law_hash and legend_hash equal the receipt's frame (current-frame binding); (d) the "
        "snapshot's constitutional_basis is non-empty; (e) the snapshot's result == ADMIT (CSIL 9001) -- a "
        "verified reconciliation must cite a warrant that AUTHORIZED an admit, never a refuse-verdict "
        "warrant. This RATIFIES the r143 (AD-66) UGK-BODY-v6 typed verified-grade surface as the law-bound "
        "admissible-basis authority. It binds RECEIPT-LOCAL self-verification ONLY: it re-derives nothing "
        "from the WarrantStore and does NOT re-evaluate the warrant's constitutional reasoning; it proves "
        "the ADMISSIBLE BASIS is committed, hash-intact, frame-bound, non-empty, and admit-verdicted -- it "
        "does NOT and cannot prove the external-world event occurred (the kernel records, never witnesses). "
        "RECON-S-01 is OPT-IN and NON-RETROACTIVE: it governs ONLY receipts that commit reconciliation_grade "
        "== 'verified' (UGK-BODY-v6 and later); recorded-grade reconciliation (verified=False) is OUT OF "
        "SCOPE and remains the AD-47/AD-60 confess-and-audit path with reconciliation_evidence_ref a recorded "
        "string. RECON-S-01 ADDS NO NEW REFUSAL CAUSE and does NOT mandate verified-grade: a receipt whose "
        "committed verified-grade surface does not self-verify is a corrupt, non-conformant receipt that "
        "fails closed at VERIFICATION, not a re-decision of the reconciliation and not a new decision-path "
        "refusal. It moves neither schema nor legend."
    ),
    gate="external_irreversible_pilot_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "If a verified-grade reconciliation terminal could commit reconciliation_grade == 'verified' without "
        "a self-verifying snapshot -- a missing snapshot, a snapshot whose SHA-256 does not match the "
        "committed warrant_id, or a stale-frame, empty-basis, or refuse-verdict snapshot -- a receipt could "
        "present an unbacked or store-dependent verified-grade claim that still verifies, laundering an "
        "absent or free-string basis into an admissible-looking warrant-backed determination."
    ),
    depends_on=("IEL-S-01", "EFFECT-S-02"),
    introduced_in="verified-grade-law-leg",
)

DCAP_S_01 = _reg(
    id="DCAP-S-01",
    statement=(
        "D_cap enforcement -- sibling capability-sufficiency precondition (opt-in, enumerated). For an "
        "operation whose (jurisdiction, op/capability-class) is EXPLICITLY ENUMERATED in the capability "
        "sufficiency policy artifact (capability_sufficiency_policy_v1), an operation otherwise ADMITTED "
        "by aggregation MUST additionally satisfy capability sufficiency, recomputed LAW-ONLY from the "
        "capability evidence verdict census (the same census the committed h_cap binds) and the policy: "
        "the required capability-class verdict must be PROVEN (the only evidence-sufficient verdict), OR "
        "the enumerated entry must admit it as a named-proof BY-CONSTRUCTION, OR a WAIVED verdict under an "
        "entry that permits a waiver (an AUTHORITY disposition that remains DISTINCT from evidence "
        "sufficiency and never reads as PROVEN); otherwise the operation REFUSES with the explicit, "
        "attributable refusal cause `insufficient-capability`. A missing verdict in an enumerated scope, "
        "and any FAIL/GAP/ERROR/NOT-RUN/unknown verdict, and external/Navigator evidence (which can never "
        "be PROVEN), all FAIL CLOSED. ENFORCEMENT IS A SIBLING PRECONDITION OUTSIDE aggregate(): D_cap / "
        "h_cap is NOT added to conjunctive_refusal_monotone_v1 and NOT to COMMITTED_SURFACES; the four-"
        "surface aggregation model is unchanged and the precondition reads neither. SCOPE-BOUNDED + "
        "DEFAULT-DENY-WITHIN-SCOPE: ONLY explicitly enumerated entries are enforced -- there is NO ambient "
        "permit and NO global default allow; UNENUMERATED (jurisdiction, op/capability-class) operations "
        "are UNAFFECTED (existing ADMIT/REFUSE behavior unchanged), so with an empty enforced_scopes the "
        "invariant enforces nothing. The determination is LAW-ONLY: recomputable from the committed "
        "evidence census + the policy artifact, with NO committed sufficiency-determination schema surface "
        "(schema-stationary); the refusal outcome + cause are recorded in the gate_refuse receipt. "
        "DCAP-S-01 introduces exactly ONE new refusal cause (`insufficient-capability`) and changes NO "
        "other decision semantics; it moves neither schema nor legend."
    ),
    gate="capability_sufficiency_policy_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "If an operation in an enumerated capability-required scope could be ADMITTED without PROVEN "
        "capability sufficiency -- a missing, FAIL/GAP/ERROR/NOT-RUN, unbacked-BY-CONSTRUCTION, "
        "unpermitted-WAIVED, or external verdict slipping through -- the kernel would grant a governed "
        "operation whose required capability is not actually evidenced, OR conversely if D_cap leaked into "
        "aggregate()/COMMITTED_SURFACES it would silently re-weight the four-surface conjunctive decision; "
        "either way the capability precondition would stop being an honest, attributable, non-aggregating "
        "sibling gate."
    ),
    depends_on=("CGP-S-01", "CGP-S-03"),
    introduced_in="dcap-enforcement-law-leg",
)

SUM_S_01 = _reg(
    id="SUM-S-01",
    statement=(
        "SessionSummary is produced at close_session() when a WarrantStore is "
        "attached. summary_hash = SHA-256(canonical_json(body)). Fields: "
        "session_dkn, receipt_count, warrant_count, refusal_count, admitted_count, "
        "final_stream_hash, law_hash, legend_hash, phase_code, timestamp. "
        "is_consistent_with(store) verifies the summary against actual store counts."
    ),
    gate="session_summary_gate",
    classification="MIXED",
    adjacency_target=(
        "Event-level closure only — session_close receipt exists but no aggregate "
        "document; downstream consumers must read the full receipt chain to answer "
        "basic questions (how many operations? how many refusals? chain intact?)."
    ),
    depends_on=("UL-S-02",),
    introduced_in="phase9",
)

# --- Phase 10: Semantic atlas ---

ATLAS_S_01 = _reg(
    id="ATLAS-S-01",
    statement=(
        "Every Invariant in INVARIANT_REGISTRY has a valid depends_on tuple "
        "whose members are all present in the registry. The resulting dependency "
        "DAG is acyclic. introduced_in is non-empty for every invariant."
    ),
    gate="primitive_dependency_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Flat invariant list — primitive dependencies are implicit; which invariants "
        "are foundational vs derived is undocumented; DAG-shaped constitutional "
        "questions cannot be answered from the registry alone."
    ),
    depends_on=(),
    introduced_in="phase10",
)

ATLAS_S_02 = _reg(
    id="ATLAS-S-02",
    statement=(
        "compound_capabilities in adr.py maps capability names to frozensets of "
        "invariant IDs. Every member of every frozenset is present in "
        "INVARIANT_REGISTRY. compound_capabilities is non-empty. "
        "Compound capability: the system-level guarantee produced by a set of "
        "invariants working together — not expressible by any single invariant."
    ),
    gate="compound_capability_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Atomized invariants — each invariant is documented individually; "
        "their compound guarantees are unspecified; the system-level question "
        "what does this substrate guarantee end-to-end has no structured answer."
    ),
    depends_on=("ATLAS-S-01",),
    introduced_in="phase10",
)

ATLAS_S_03 = _reg(
    id="ATLAS-S-03",
    statement=(
        "ADR_REGISTRY in adr.py contains at least one ArchitecturalDecision per "
        "major design choice. Every ADR has at least one bound_invariant present "
        "in INVARIANT_REGISTRY. Every bound_invariant appears in at least one ADR."
    ),
    gate="adr_gate",
    classification="MIXED",
    adjacency_target=(
        "Decision-free invariant registry — the registry proves what must hold "
        "but not why it was chosen or what alternatives were rejected; "
        "constitutional reasoning is opaque to new contributors and auditors."
    ),
    depends_on=(),
    introduced_in="phase10",
)

ATLAS_S_04 = _reg(
    id="ATLAS-S-04",
    statement=(
        "CODEX.md is a projected representation of the semantic atlas. "
        "SHA-256(CODEX.md) is pinned. codex_integrity_gate verifies the pin. "
        "If the Codex drifts from the implementation, the gate fails. "
        "The Codex is constitutionally situated: not external documentation "
        "but part of the constitutional frame."
    ),
    gate="codex_integrity_gate",
    classification="MIXED",
    adjacency_target=(
        "Undocumented substrate — the system proves itself via gates but does not "
        "explain itself; the WHY layer (decisions, dependencies, capabilities) "
        "exists only in build session transcripts, not in a governed artifact."
    ),
    depends_on=("ATLAS-S-01", "ATLAS-S-02", "ATLAS-S-03", "LEGEND-S-01"),
    introduced_in="phase10",
)

# --- Phase 12: SSA vocabulary ---

SSA_VOCAB_S_01 = _reg(
    id="SSA-VOCAB-S-01",
    statement=(
        "INTENT_TYPES in core/vocab.py contains exactly 17 governance-generic "
        "semantic verbs (Governor-confirmed, Phase 12). All 17 verbs are present "
        "in the LEGEND compress map (_INTENT_TO_CSIL) with assigned CSIL integer "
        "addresses (4001–4017). SSA axis on the SRSA vector is lit (score=1)."
    ),
    gate="ssa_vocabulary_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Partial semantic vocabulary — INTENT_TYPES has fewer than 17 verbs; "
        "SSA axis remains 0; the semantic self-assertion surface is incomplete; "
        "intent declarations outside the 8 founding verbs have no governed vocabulary."
    ),
    depends_on=("LEGEND-S-01",),
    introduced_in="phase12",
)

# --- Phase 13A: Will layer + Provenance scope (foundation) ---

WILL_S_01 = _reg(
    id="WILL-S-01",
    statement=(
        "IntentDeclaration is content-addressed. declaration_hash = "
        "SHA-256(canonical_json(body)). Identity is its content hash — "
        "changing declared_ops or scope yields a new declaration. "
        "Silent intent edits are constitutionally impossible."
    ),
    gate="intent_declaration_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Mutable intent — declarations could be edited after covering an effect; "
        "the audit trail cannot reconstruct what was willed; label-identity "
        "laundering (ALT §16) becomes possible."
    ),
    depends_on=("LEGEND-S-01",),
    introduced_in="phase13",
)

WILL_S_02 = _reg(
    id="WILL-S-02",
    statement=(
        "R_int is the least fixpoint of declared ops under admissible "
        "production_edges. WillChecker._closure() is a deterministic monotone "
        "fixpoint that terminates on the finite APPLICATION_OPS graph. "
        "closure_depth=None is ALT §18-faithful full closure. "
        "closure_depth=0 is literal match."
    ),
    gate="will_checker_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Literal-match will — legitimately re-derivable downstream effects are "
        "refused (over-restriction); deployers must enumerate every possible op "
        "rather than declaring intent at a higher level."
    ),
    depends_on=("WILL-S-01",),
    introduced_in="phase13",
)

WILL_S_03 = _reg(
    id="WILL-S-03",
    statement=(
        "Coverage is fail-closed when require_intent=True on the kernel. "
        "No active intent → WL-005 (NO_ACTIVE_INTENT). "
        "Op outside R_int → WL-001 (EFFECT_OUTSIDE_INTENT). "
        "Applies to APPLICATION_OPS only; KERNEL_OPS and UNIVERSAL_OPS are exempt."
    ),
    gate="will_checker_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Vacuous-pass will — absent intent records admit everything; "
        "an unconfigured deployment admits all APPLICATION_OPS as vacuously willed; "
        "ALT disjunct (c) is re-opened exactly where it is most likely."
    ),
    depends_on=("WILL-S-02",),
    introduced_in="phase13",
)

WILL_S_04 = _reg(
    id="WILL-S-04",
    statement=(
        "IntentRevocation is permanent and unfalsifiable. A revoked declaration "
        "never seeds R_int again. No un-revoke, no expiry, no suspension. "
        "IntentStore marks revoked declarations and excludes them from "
        "active_declarations() output."
    ),
    gate="intent_declaration_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Reversible revocation — withdrawn intent could be silently reasserted; "
        "coverage of previously-unwilled effects could be laundered back in; "
        "the revocation audit trail becomes unreliable."
    ),
    depends_on=("WILL-S-01",),
    introduced_in="phase13",
)

SCOPE_S_01 = _reg(
    id="SCOPE-S-01",
    statement=(
        "ProvenanceScope is emitted at session_open and stored in scope_archive "
        "table in ugk.db. scope_id = SHA-256(canonical_json(scope_body)). "
        "prior_scope_id chains sessions into operational continuity lineage. "
        "AuditSession can query all scopes for a given mosaic_root."
    ),
    gate="provenance_scope_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Implicit provenance scope — session_dkn and law_hash act as implicit "
        "scope boundaries; no artifact declares admissibility constraints; "
        "the operational continuity chain (identity paper §8) is not navigable."
    ),
    depends_on=("LEGEND-S-03",),
    introduced_in="phase13",
)

# --- Phase 13B: Will layer wiring ---

WILL_S_05 = _reg(
    id="WILL-S-05",
    statement=(
        "When WillChecker.covers() returns COVERED, receipt.intent_ref records "
        "the covering IntentDeclaration hash. intent_ref is included in dm_s03 "
        "as dimension D_I — altering the covering declaration changes semantic_hash. "
        "The will is tamper-evident in the chain."
    ),
    gate="intent_receipt_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Ephemeral will trace — coverage is checked but not recorded; long-horizon "
        "audit cannot reconstruct that an effect was willed; the will leaves no "
        "durable evidence in the receipt chain."
    ),
    depends_on=("WILL-S-01", "LEGEND-S-03"),
    introduced_in="phase13",
)

WILL_S_06 = _reg(
    id="WILL-S-06",
    statement=(
        "Coverage is computed BEFORE the success receipt is written, which is "
        "BEFORE the effect executes (NBER-1 preserved). The will check is steps "
        "C1-C3 inserted before step 6 in execute(). Coverage cannot be a "
        "post-hoc annotation — it is a precondition of admission."
    ),
    gate="will_coverage_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Post-hoc coverage annotation — coverage is recorded after the effect; "
        "an unwilled effect has already executed before the will check fires; "
        "coverage becomes a description of what happened, not a gate on it."
    ),
    depends_on=("WILL-S-02", "UL-S-02"),
    introduced_in="phase13",
)

SCOPE_S_02 = _reg(
    id="SCOPE-S-02",
    statement=(
        "Replay admissibility: a receipt from a closed session is not admissible "
        "as a new-session operation. Receipts are scope-bounded by session_dkn "
        "(carried in the CHC envelope). A receipt whose session_dkn does not "
        "match the current session is from a different provenance scope — "
        "operationally inadmissible despite remaining cryptographically authentic."
    ),
    gate="scope_archive_gate",
    classification="MIXED",
    adjacency_target=(
        "Scope-blind replay — a receipted operation from a prior session could be "
        "presented as evidence of current-session activity; attribution lineage "
        "becomes malleable; operational continuity claims are unverifiable."
    ),
    depends_on=("SCOPE-S-01", "DM-S-03"),
    introduced_in="phase13",
)

# --- Phase 13C: Successor lineage ---

SUCC_S_01 = _reg(
    id="SUCC-S-01",
    statement=(
        "SuccessorLineage is a cryptographic succession proof. "
        "succession_proof = Ed25519 sig from the predecessor key over "
        "canonical_json(body_fields). Verifiable by anyone holding the "
        "predecessor pubkey — without the predecessor private key. "
        "lineage_hash = SHA-256(canonical_json(full body including succession_proof)). "
        "Stored in genesis/SUCCESSOR_LINEAGE.json."
    ),
    gate="successor_lineage_gate",
    classification="DOMAIN_PHYSICS",
    adjacency_target=(
        "Claim-only succession — a new key claims to succeed the old one "
        "without a signature from the old key; any key can claim succession; "
        "the operational continuity chain from the identity paper §8 is "
        "unverifiable without the predecessor's authorization."
    ),
    depends_on=("AUDIT-S-02",),
    introduced_in="phase13",
)

# --- Phase 15: Configuration Manifold ---
CM_S_01=_reg(id="CM-S-01",statement="AuthorityModel is content-addressed. model_hash=SHA-256(canonical_json(body)). Changing any flag yields a new hash. Silent edits constitutionally impossible.",gate="authority_model_gate",classification="DOMAIN_PHYSICS",adjacency_target="Mutable authority model — compliance posture could be changed silently; auditors cannot reconstruct posture from receipts.",depends_on=("WILL-S-01",),introduced_in="phase15")
CM_S_02=_reg(id="CM-S-02",statement="When require_gate=True, APPLICATION_OPs without a gate raise KernelInternalOp before tier check. No receipt is written for a require_gate violation.",gate="authority_model_gate",classification="DOMAIN_PHYSICS",adjacency_target="Ceremonial gate — APPLICATION_OP admitted without gate; authority is latent not effective; ALT Appendix C Builder's Trap.",depends_on=("CM-S-01",),introduced_in="phase15")
CM_S_03=_reg(id="CM-S-03",statement="When require_warrant=True, execute() without warrant_basis raises KernelInternalOp. Constitutional justification for every admitted op must be explicit.",gate="authority_model_gate",classification="DOMAIN_PHYSICS",adjacency_target="Unwarranted admission — warrant_id empty on receipt; second disjunct traced but not warranted.",depends_on=("CM-S-01",),introduced_in="phase15")
CM_S_04=_reg(id="CM-S-04",statement="AuthorityModel sealed to authority_model_archive at set_authority_model() time. model_hash in every session_open receipt parameters as authority_model_hash. Posture auditable from chain without live kernel.",gate="model_receipt_gate",classification="MIXED",adjacency_target="Unreceipted posture — authority model set but not recorded; auditors cannot determine posture from chain.",depends_on=("CM-S-01","SCOPE-S-01"),introduced_in="phase15")

# --- Phase 16: ALT Instance Configuration ---
ALT_I_01=_reg(id="ALT-I-01",statement="ConstitutiveProbeResult is content-addressed. CONSTITUTIVE: gate refused at least one tested input. CEREMONIAL: named governance gap (not an error). UNPROBED: constitutiveness unknown.",gate="constitutive_probe_gate",classification="DOMAIN_PHYSICS",adjacency_target="Uncertified gate — constitutiveness asserted rather than tested; φ scalar cannot be computed.",depends_on=("CM-S-02",),introduced_in="phase16")
ALT_I_02=_reg(id="ALT-I-02",statement="When authority_set supplied to execute(), receipt carries authority_set in parameters. A1 bridge: set-valued authority annotation alongside single warrant_id.",gate="alt_instance_gate",classification="MIXED",adjacency_target="Single-authority collapse — multi-authority effects collapsed to one warrant_id; A1 set-valued structure not expressible.",depends_on=("WILL-S-05",),introduced_in="phase16")
ALT_I_03=_reg(id="ALT-I-03",statement="When require_scoped_intent=True, only declarations with scope_ref matching session_dkn are active. Open-scope declarations (scope_ref='') excluded. Prevents stale-reuse laundering.",gate="alt_instance_gate",classification="DOMAIN_PHYSICS",adjacency_target="Stale-reuse laundering — open-scope intent declared in session 1 covers ops in session 2 under different constitutional frame.",depends_on=("WILL-S-03","SCOPE-S-02"),introduced_in="phase16")
ALT_I_04=_reg(id="ALT-I-04",statement="φ(S)=(ceremonial+unprobed APPLICATION_OPs)/(total APPLICATION_OPs). φ=0: fully constitutive. φ=1: fully ceremonial. Computable via phi_score().",gate="alt_instance_gate",classification="MIXED",adjacency_target="Hidden ceremonial authority — laundering posture unquantified; ALT posture vector cannot be computed.",depends_on=("ALT-I-01","CM-S-02"),introduced_in="phase16")

# --- Phase 17: Pedagogical surface ---
PED_S_01=_reg(id="PED-S-01",statement="Every concept introduced into the UGK authority surface must have a LEGEND entry, an invariant or ADR describing its physics, and a ugk explain resolution path. A concept that cannot be explained from ugk explain is constitutionally unnamed.",gate="constitution_surface_gate",classification="MIXED",adjacency_target="Constitutional opacity — concepts exist in code but not in vocabulary; audit cannot navigate governance decisions; documentation drifts from running system.",depends_on=("LEGEND-S-01","AUDIT-S-02"),introduced_in="phase17")

# --- Phase 18: CGP + Unified status ---
CGP_S_01=_reg(id="CGP-S-01",statement="GovernancePosture is content-addressed (posture_hash=SHA-256(canonical_json(body))). Posture is auditable from the receipt chain without running the full gate suite.",gate="posture_gate",classification="DOMAIN_PHYSICS",adjacency_target="Ephemeral posture — compliance claim exists only in kernel memory; cannot be audited from chain.",depends_on=("CM-S-04","ALT-I-04"),introduced_in="phase18")
CGP_S_02=_reg(id="CGP-S-02",statement="ugk health covers five sub-checks: chain integrity, authority model, posture vector, disjunct coverage, and gate compliance. A partial health check omitting any sub-check is constitutionally incomplete.",gate="health_surface_gate",classification="MIXED",adjacency_target="Partial health reporting — omitted sub-checks create false confidence; laundering posture goes undetected.",depends_on=("CGP-S-01","PED-S-01"),introduced_in="phase18")
CGP_S_03=_reg(id="CGP-S-03",statement="GATE_GROUP annotation on each gate file classifies it into structural|unit|integration|conformance groups. Health report accounts for every gate. ugk-gates --group structural is a fast smoke test.",gate="health_surface_gate",classification="MIXED",adjacency_target="Ungrouped gates — health report cannot distinguish fast structural failures from slow integration failures; fail-fast not achievable.",depends_on=("CGP-S-02",),introduced_in="phase18")

# --- Phase 19: CSIL/GTI floor ---
CSIL_S_01=_reg(id="CSIL-S-01",statement="APPLICATION_OPs with csil_id>0 in GOVERNANCE_OPS carry op_csil in receipt parameters. csil_id=0 is honest-absent (not an error). Collision with existing LEGEND integers raises ValueError at registration time.",gate="csil_floor_gate",classification="DOMAIN_PHYSICS",adjacency_target="Coordinate shadowing — op renamed without coordinate continuity; authority string drifts from semantic identity; cross-deployment auditing fails.",depends_on=("LEGEND-S-01","WILL-S-01"),introduced_in="phase19")
CSIL_S_02=_reg(id="CSIL-S-02",statement="The invariant dependency graph (depends_on fields) is the semantic topology over CSIL invariant tier. ugk explain <name_or_csil> navigates this topology and returns: CSIL integer, tier, statement, depends_on chain, in-degree.",gate="csil_topology_gate",classification="MIXED",adjacency_target="Governance opacity — the constitutional structure is not navigable; operators cannot trace why a decision was made through the dependency chain.",depends_on=("LEGEND-S-01","AUDIT-S-02","PED-S-01"),introduced_in="phase19")

# --- Phase 20: DKN ordering + Deployment Charter ---
DKN_S_01=_reg(id="DKN-S-01",statement="session_dkn = SHA-256(mosaic_root:phase_code:session_id). WHO×WHAT×WHICH semantic ordering: mosaic_root (key identity, most persistent) → phase_code (deployment type) → session_id (instance). dimension_id is a compound anchor for genesis/CSH — NOT an input to session_dkn.",gate="dkn_gate",classification="DOMAIN_PHYSICS",adjacency_target="Inverted identity hierarchy — phase_code before mosaic_root obscures that the governor is the primary anchor; dimension_id in session_dkn creates redundant binding.",depends_on=("LEGEND-S-03",),introduced_in="phase20")
CHARTER_S_01=_reg(id="CHARTER-S-01",statement="DeploymentManifest is content-addressed. governor_pubkey and phase_code are runtime-loaded from genesis/GENESIS_KEY.pub and genesis/DEPLOYMENT_MANIFEST.json. Kernel fails closed (sentinel pubkey → STATUS_UNINITIALIZED) without genesis/GENESIS_KEY.pub. No hardcoded governance identity in source.",gate="charter_gate",classification="DOMAIN_PHYSICS",adjacency_target="Hardcoded identity — every deployment of the same binary shares the same governance identity; no separation between development and production deployments.",depends_on=("CM-S-01",),introduced_in="phase20")
CHARTER_S_02=_reg(id="CHARTER-S-02",statement="ugk charter is the founding constitutional act. --pubkey is required minimum. manifest_hash carried on every session_open receipt parameter. ugk charter refuses to overwrite existing genesis artifacts without --force.",gate="charter_gate",classification="MIXED",adjacency_target="Uncommitted deployment identity — kernel operates without a declared governance identity; session_open receipts cannot be attributed to a specific deployment manifest.",depends_on=("CHARTER-S-01","CM-S-04"),introduced_in="phase20")
IEL_S_01=_reg(id="IEL-S-01",statement="Receipt-body integrity is runtime-verifiable and enforced over the WHOLE committed body. Each receipt carries h_body, a domain-separated commitment over EVERY committed field; store.verify_receipt_bodies() recomputes h_body (and h_s = H_s(op,parameters)) per receipt PURELY from stored values and detects tampering of ANY committed field. h_body is MANDATORY: a receipt missing it - even if h_body is stripped from every receipt wholesale - does NOT establish BODY (no downgrade to h_s-only); store.verify_chain() composes LINKAGE (stream-hash) and full BODY at required level BODY and fails closed (CorruptionKind.CORRUPT) on any committed-field tamper, a stripped or absent h_body, OR a missing checkpoint; ugk verify requires LINKAGE+BODY. Detection holds on the runtime/CLI path, not merely a fixture, proven by receipt_commitment_integrity_gate (tampers every committed field AND tests the strip-all downgrade). The IEL mutation-side (A/E), read-only (D), and context primitives are gated but not all yet wired into subsystems, so they are not yet formal invariants.",gate="receipt_commitment_integrity_gate",classification="DOMAIN_PHYSICS",adjacency_target="A verifier that checks only stream-linkage or only h_s - or that treats a missing h_body as a legacy fallback rather than a failure - reports a body-tampered or commitment-stripped chain as intact; the claim (the whole receipt body is verified) would exceed the proof. Downgrade attack: strip h_body from every receipt, then rewrite committed fields (authority, law_hash, h_c, etc.), and a fallback verifier still reports BODY.",depends_on=("CHC-S-01","CHC-S-03"),introduced_in="iel-phase1")


# ============================================================================
# M2.3a — Constitutional declarations for THR-conformant binding
# ============================================================================
#
# Per M2-DESIGN-PACK-REV3 §Deliverables 1, 3, 5. These declarations make the
# constitutional frame explicit before the M2.3b+ scaffolding-replacement
# subphases (G_c authority graph, Policy artifacts, FreshnessClaim with real
# epochs, namespace M_Phi, semantic lineage, authority key management).
#
# As of M2.3c, CANONICALIZATION_DOMAINS and PRINCIPLED_REDUNDANCY_REGISTRY
# are declared canonically here in invariants.py; ugk/binding_m2.py imports
# them from this module by object identity, eliminating the dual-registry
# arrangement from earlier subphases.

import hashlib as _hashlib
import json as _json


# ----------------------------------------------------------------------------
# Σ_0 — the canonical semantic regime shipped with UGK v0.1.0 (THR §8)
# ----------------------------------------------------------------------------
# Per REV3 §Deliverable 1. Cross-regime statements (UGK ↔ AbleTools, future
# CPVM, GMB) require V_lift; this regime is canonical for UGK's own surface.

SIGMA_0 = {
    "L":        "governed-operation-declarations",
    "T":        "intent-warrant-capability theory",
    "R":        "UGK normalization rule set",
    "v":        "0.1.0",
    "r_star":   "deterministic-reduction-v1",
    "B":        "UGK normalization bound",
    "imports":  [],
}


def _canonical_json_bytes(obj) -> bytes:
    """Local canonical-JSON encoder mirroring binding_m2._canonical_json.

    Used to compute id(Sigma_0) constitutionally without importing from
    binding_m2 (avoids circular constitutional dependency: invariants.py
    is upstream of runtime modules).
    """
    return _json.dumps(
        obj, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


ID_SIGMA_0 = _hashlib.sha256(_canonical_json_bytes(SIGMA_0)).hexdigest()


# ----------------------------------------------------------------------------
# Φ_0 — the canonical operating phase shipped with UGK v0.1.0 (THR §9)
# ----------------------------------------------------------------------------
# Per REV3 §Deliverable 1 and Roadmap §3 W-03. The phase artifact is a
# governed constitutional declaration that binds operations to a specific
# phase under regime Σ_0. id(Φ_0) replaces the placeholder string "m2.2"
# previously used as phase_code in H_j and as id_Phi leaf input. M2.3d
# introduces the single canonical phase Φ_0; multi-phase machinery and
# FreshnessClaim integration are later subphases.

PHI_0 = {
    "phase_code":  "ugk-0.1.0",
    "regime_id":   ID_SIGMA_0,
    "v":           "0.1.0",
    "description": "UGK v0.1.0 canonical operating phase",
    "imports":     [],
}


ID_PHI_0 = _hashlib.sha256(_canonical_json_bytes(PHI_0)).hexdigest()


# ----------------------------------------------------------------------------
# CANONICALIZATION_DOMAINS (constitutional declaration)
# ----------------------------------------------------------------------------
# Per REV3 §Deliverable 3. The declared input domain of each c_i and of each
# strict-mode context-pin hash. Consulted by commitment_minimality_gate.
# Runtime mirror: ugk.binding_m2.CANONICALIZATION_DOMAINS (to be reconciled
# in a later subphase).

CANONICALIZATION_DOMAINS: dict[str, frozenset[str]] = {
    "H_s":      frozenset({"op", "inputs"}),
    "H_c":      frozenset({"authority_chain", "policy_id", "capabilities",
                           "warrant_basis", "parent_H_r", "freshness"}),
    "H_m":      frozenset({"intent", "intent_ref", "legend_hash",
                           "semantic_lineage", "semantic_regime_id"}),
    "H_j":      frozenset({"phase_code", "mosaic_root", "session_id",
                           "authority_key"}),
    "id_P":     frozenset({"policy_id"}),
    "id_Sigma": frozenset({"semantic_regime_id"}),
    "id_Phi":   frozenset({"phase_code"}),
}


# ----------------------------------------------------------------------------
# PRINCIPLED_REDUNDANCY_REGISTRY (constitutional declaration)
# ----------------------------------------------------------------------------
# Per REV3 §Deliverable 3 + Appendix EV (EV-AV-001 threat vector).
# Format: leaf_name -> (carrier_leaf_name, threat_class_identifier).
# Three entries exhaust strict-mode pin admissibility for UGK v0.1.0.
# Modifying this registry is a constitutional event requiring Governor ADR
# ratification with THREAT_CLASS field populated.
# Runtime mirror: ugk.binding_m2.PRINCIPLED_REDUNDANCY_REGISTRY.

PRINCIPLED_REDUNDANCY_REGISTRY: dict[str, tuple[str, str]] = {
    "id_P":     ("H_c", "chain-link-cache-self-describing-identity"),
    "id_Sigma": ("H_m", "chain-link-cache-self-describing-identity"),
    "id_Phi":   ("H_j", "chain-link-cache-self-describing-identity"),
}


# ----------------------------------------------------------------------------
# ERROR_CODES — constitutional registry of THR error codes (REV3 §Deliverable 4)
# ----------------------------------------------------------------------------
# String error codes raised by canonicalization, freshness, binding-verification,
# and decision procedures. M2.3a adds only NotYetAdmissible; the remaining
# codes are documented constitutionally and become enforceable as their
# decision machinery lands in later subphases. Runtime values are string
# constants (compatible with current freshness_check return values).

ERROR_CODES: dict[str, str] = {
    "NonCanonical":          "input fails canonicalization (cycles, non-UTF-8, non-finite floats)",
    "PhaseMismatch":         "FreshnessClaim phase_code does not match verifier's current phase",
    "NotYetAdmissible":      "current epoch_counter < FreshnessClaim valid_from — admissibility window has not opened (M2.3a addition)",
    "ExpiredEdge":           "current epoch_counter > FreshnessClaim valid_until — admissibility window has closed",
    "CapabilityEscalation":  "capability not ⊆ predecessor in attenuation chain",
    "RevokedEdge":           "authority graph edge has been revoked",
    "NoCanonicalPath":       "no canonical admissibility path through G_c under policy P at time t",
    "NormalizationFailure":  "c_m parse_L or r* normalization fails",
    "ResourceBoundExceeded": "normalization exceeds declared bound B",
    "NamespaceNonMember":    "name_key not in M_Phi for the receipt's phase",
    "ContextMismatch":       "verifier-supplied context does not match receipt's context binding",
    "UnderRecordedCollapse": "context-external receipt omits both recovery witness and collapse witness (§4.5)",
    "SignatureInvalid":      "Ed25519 signature verification failed (FreshnessClaim window_sig, EpochIssuance, or EpochRetirement) — M2.3e addition",
    "IssuerMismatch":        "issuer_key_id on a signed artifact does not equal the expected Governor public key — M2.3e addition",
}


# ─────────────────────────────────────────────────────────────────────────────
# Capability vocabulary (M2.3i)
# ─────────────────────────────────────────────────────────────────────────────
#
# Finite enumerated set of capability identifiers that may appear in
# AuthorityEdge.capability_set values and in the H_c capabilities input.
# Any capability identifier outside this set is invalid: the Governor
# (root of G_c) is treated as holding exactly CAPABILITY_VOCABULARY, so a
# child set containing an identifier not in the vocabulary is not a
# subset of the parent's effective set → CapabilityEscalation.
#
# The vocabulary is intentionally small at M2.3i. Future subphases may
# extend it; doing so is a constitutional change that moves law_hash by
# design.
#
# Per the M2.3i directive: attenuation rule is child_set ⊆ parent_effective_set
# at every hop along the canonical G_c path. compute_effective_capabilities
# (in ugk/capabilities.py) walks the path applying this rule; failure
# emits the existing CapabilityEscalation error code (M2.3a).

CAPABILITY_VOCABULARY: frozenset[str] = frozenset({
    "attest",
    "bind",
    "evaluate",
    "read",
    "write",
})


# ─────────────────────────────────────────────────────────────────────────────
# Namespace declaration — M_Phi for phase Φ_0 (M2.3k)
# ─────────────────────────────────────────────────────────────────────────────
#
# Constitutional set of name_keys valid in phase Φ_0. Each entry is a
# namespaced identifier of the form "<kind>:<name>". The cryptographic
# commitment to this set (mosaic_root) is computed from sorted canonical
# JSON of the entries and bound into H_j via c_j canonicalization.
#
# Per the M2.3k directive: minimal namespace machinery. The set is
# intentionally small at M2.3k and covers:
#   - Op categories that appear in receipts (op:*)
#   - The root authority (authority:Governor) — runtime child authorities
#     are managed via G_c, not M_Phi (separation of concerns)
#   - The phase self-reference (phase:*)
#
# Intent refs (id://...) are NOT placed in this set — they are opaque
# identifiers at M2.3k and remain so for M2.3l. If a later subphase
# requires intent-name namespace validation, it would add an intent
# kind to this declaration.
#
# M2.3l (decision procedures) will provide the NamespaceNonMember
# enforcement that validates receipt-referenced names against this set.
# Receipts produced at M2.3k carry mosaic_root committing to this set;
# the verifier-side check arrives at M2.3l.
#
# Future extensions are constitutional changes (move law_hash, move
# mosaic_root for all subsequently-produced receipts).

NAMESPACE_PHI_0: frozenset[str] = frozenset({
    # Op categories
    "op:policy_evaluate",
    "op:audit",
    "op:attest",
    "op:bind",
    "op:evaluate",
    # Authority root
    "authority:Governor",
    # Phase self-reference
    "phase:phi_0",
})
