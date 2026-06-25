# UGK Invariant Taxonomy — generated navigation layer

**Generated from `INVARIANT_TAXONOMY.json`. Do not hand-edit.** This maps every live UGK invariant to a curated semantic family, subsystem, frame role, gate, source refs, construction provenance, and a short explanation. It is **navigation, not law**: the cited sources (invariant / ADR / gate / codex / release / file) are authority; this index is not. Stable invariant IDs are unchanged; `construction_lane` (the build lane that introduced each invariant) is provenance, not semantic standing.

Verified against: r169 · 87 invariants · 12 semantic families. For live constitutional facts use `ugk explain <id>`.

## Semantic families

- **adversarial-resistance** — 1 invariants
- **amendment-governance** — 6 invariants
- **audit-observability** — 3 invariants
- **configuration-constraint** — 10 invariants
- **content-addressed-artifact** — 19 invariants
- **effect-truthfulness** — 3 invariants
- **frame-governance** — 17 invariants
- **identity-and-vocabulary** — 3 invariants
- **jurisdiction-projection** — 4 invariants
- **namespace-authority** — 6 invariants
- **receipt-chain-integrity** — 8 invariants
- **terminal-outcome** — 7 invariants

## adversarial-resistance

### ADV-S-01 — Adversarial rug-pull detection
*subsystem:* ADV · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Four adversarial rug-pulls are each detected: (1) CHC field tamper changes semantic_hash, (2) GOVERNANCE_OPS runtime tamper raises UndeclaredOp, (3) Grundnorm file tamper breaks grundnorm_readonly_gat

- **gate:** `rugpull_gate`
- **sources (authority):** `invariant:ADV-S-01`, `file:ugk/invariants.py`, `gate:rugpull_gate`
- **provenance (build lane, not semantic standing):** `phase1`

## amendment-governance

### AMD-S-01 — Amendment record governance (AMD-S-01)
*subsystem:* AMD · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

AmendmentRecord is a first-class content-addressed artifact documenting each law_hash transition.

- **gate:** `amendment_record_gate`
- **sources (authority):** `invariant:AMD-S-01`, `file:ugk/invariants.py`, `gate:amendment_record_gate`
- **provenance (build lane, not semantic standing):** `phase9`

### AMD-S-02 — Amendment record governance (AMD-S-02)
*subsystem:* AMD · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Amendment-model-at-inception: the DeploymentManifest declares amendment_model in {higher_root, self} at the founding constitutional act, committed in manifest_hash and carried on session_open.

- **gate:** `amendment_model_gate`
- **sources (authority):** `invariant:AMD-S-02`, `file:ugk/invariants.py`, `gate:amendment_model_gate`
- **provenance (build lane, not semantic standing):** `phase17`

### AMD-S-03 — Amendment record governance (AMD-S-03)
*subsystem:* AMD · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Amendment admissibility (frame-general): a constitutional-frame transition c_n -> c_{n+1} is ADMITTED iff an AmendmentRecord satisfies, fail-closed: (1) prior frame == c_n frame triad; (2) for EVERY f

- **gate:** `amendment_admissibility_gate`
- **sources (authority):** `invariant:AMD-S-03`, `file:ugk/invariants.py`, `gate:amendment_admissibility_gate`
- **provenance (build lane, not semantic standing):** `phase17`

### CR-S-01 — Classified remainders (declared gaps) (CR-S-01)
*subsystem:* CR · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

CLASSIFIED_REMAINDERS (CR-01..CR-04) are declared in the kernel: OS layer, Python runtime, SQLite WAL, effect() internals.

- **gate:** `classified_remainders_gate`
- **sources (authority):** `invariant:CR-S-01`, `file:ugk/invariants.py`, `gate:classified_remainders_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CR-S-02 — Classified remainders (declared gaps) (CR-S-02)
*subsystem:* CR · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

CLASSIFIED_REMAINDERS are inert — no capability flows from a declared gap.

- **gate:** `canary_gate`
- **sources (authority):** `invariant:CR-S-02`, `file:ugk/invariants.py`, `gate:canary_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### SUCC-S-01 — Successor lineage proof
*subsystem:* SUCC · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

SuccessorLineage is a cryptographic succession proof.

- **gate:** `successor_lineage_gate`
- **sources (authority):** `invariant:SUCC-S-01`, `file:ugk/invariants.py`, `gate:successor_lineage_gate`
- **provenance (build lane, not semantic standing):** `phase13`

## audit-observability

### AUDIT-S-01 — Read-only audit surface (AUDIT-S-01)
*subsystem:* AUDIT · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

AuditSession is a read-only governed surface.

- **gate:** `audit_session_gate`
- **sources (authority):** `invariant:AUDIT-S-01`, `file:ugk/invariants.py`, `gate:audit_session_gate`
- **provenance (build lane, not semantic standing):** `phase8`

### AUDIT-S-02 — Read-only audit surface (AUDIT-S-02)
*subsystem:* AUDIT · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

The legend_archive table in ugk.db contains every LEGEND version by legend_hash.

- **gate:** `legend_archive_gate`
- **sources (authority):** `invariant:AUDIT-S-02`, `file:ugk/invariants.py`, `gate:legend_archive_gate`
- **provenance (build lane, not semantic standing):** `phase8`

### AUDIT-S-03 — Read-only audit surface (AUDIT-S-03)
*subsystem:* AUDIT · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

AuditSession.receipts_for_warrant(warrant_hash) returns a correct, complete list of receipts whose warrant_id equals warrant_hash.

- **gate:** `receipts_for_warrant_gate`
- **sources (authority):** `invariant:AUDIT-S-03`, `file:ugk/invariants.py`, `gate:receipts_for_warrant_gate`
- **provenance (build lane, not semantic standing):** `phase8`

## configuration-constraint

### CM-DIM-01 — Governance status transitions (CM-DIM-01)
*subsystem:* CM · *classification:* ABI_CONFIG · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Every Dimension in dimensions.py has its current selection within the admissible set and outside the inadmissible set.

- **gate:** `dimension_selection_gates`
- **sources (authority):** `invariant:CM-DIM-01`, `file:ugk/invariants.py`, `gate:dimension_selection_gates`
- **provenance (build lane, not semantic standing):** `phase1`

### CM-GS-01 — Governance status transitions (CM-GS-01)
*subsystem:* CM · *classification:* ABI_CONFIG · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Governance status transitions UNINITIALIZED → ACTIVE via the founding ceremony.

- **gate:** `status_transition_gate`
- **sources (authority):** `invariant:CM-GS-01`, `file:ugk/invariants.py`, `gate:status_transition_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CM-GS-02 — Governance status transitions (CM-GS-02)
*subsystem:* CM · *classification:* ABI_CONFIG · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

The shipped kernel GOVERNOR_PUBKEY_HEX is the unset sentinel 'GOVERNOR_KEY_UNSET__RUN_GENESIS_CEREMONY'.

- **gate:** `governor_key_unset_gate`
- **sources (authority):** `invariant:CM-GS-02`, `file:ugk/invariants.py`, `gate:governor_key_unset_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CM-OP-01 — Governance status transitions (CM-OP-01)
*subsystem:* CM · *classification:* ABI_CONFIG · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Three-tier op jurisdiction is enforced by execute().

- **gate:** `three_tier_jurisdiction_gate`
- **sources (authority):** `invariant:CM-OP-01`, `file:ugk/invariants.py`, `gate:three_tier_jurisdiction_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CM-S-01 — Governance status transitions (CM-S-01)
*subsystem:* CM · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

AuthorityModel is content-addressed.

- **gate:** `authority_model_gate`
- **sources (authority):** `invariant:CM-S-01`, `file:ugk/invariants.py`, `gate:authority_model_gate`
- **provenance (build lane, not semantic standing):** `phase15`

### CM-S-02 — Governance status transitions (CM-S-02)
*subsystem:* CM · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

When require_gate=True, APPLICATION_OPs without a gate raise KernelInternalOp before tier check.

- **gate:** `authority_model_gate`
- **sources (authority):** `invariant:CM-S-02`, `file:ugk/invariants.py`, `gate:authority_model_gate`
- **provenance (build lane, not semantic standing):** `phase15`

### CM-S-03 — Governance status transitions (CM-S-03)
*subsystem:* CM · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

When require_warrant=True, execute() without warrant_basis raises KernelInternalOp.

- **gate:** `authority_model_gate`
- **sources (authority):** `invariant:CM-S-03`, `file:ugk/invariants.py`, `gate:authority_model_gate`
- **provenance (build lane, not semantic standing):** `phase15`

### CM-S-04 — Governance status transitions (CM-S-04)
*subsystem:* CM · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

AuthorityModel sealed to authority_model_archive at set_authority_model() time.

- **gate:** `model_receipt_gate`
- **sources (authority):** `invariant:CM-S-04`, `file:ugk/invariants.py`, `gate:model_receipt_gate`
- **provenance (build lane, not semantic standing):** `phase15`

### EH-S-01 — Typed exception hierarchy (EH-S-01)
*subsystem:* EH · *classification:* ABI_CONFIG · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Typed exception hierarchy: KernelInternalOp (Tier 0 external call), GovernanceNotFounded (Tier 2 in UNINITIALIZED), UndeclaredOp (BS-01 violation), GateRefusal (gate returned False).

- **gate:** `error_codes_gate`
- **sources (authority):** `invariant:EH-S-01`, `file:ugk/invariants.py`, `gate:error_codes_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### EH-S-02 — Typed exception hierarchy (EH-S-02)
*subsystem:* EH · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Chain corruption recovery: last_valid_frontier() identifies the receipt_id of the last valid receipt before corruption begins.

- **gate:** `recovery_gate`
- **sources (authority):** `invariant:EH-S-02`, `file:ugk/invariants.py`, `gate:recovery_gate`
- **provenance (build lane, not semantic standing):** `phase1`

## content-addressed-artifact

### ALT-I-01 — Constitutive probe result (ALT-I-01)
*subsystem:* ALT · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

ConstitutiveProbeResult is content-addressed.

- **gate:** `constitutive_probe_gate`
- **sources (authority):** `invariant:ALT-I-01`, `file:ugk/invariants.py`, `gate:constitutive_probe_gate`
- **provenance (build lane, not semantic standing):** `phase16`

### ALT-I-02 — Constitutive probe result (ALT-I-02)
*subsystem:* ALT · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

When authority_set supplied to execute(), receipt carries authority_set in parameters.

- **gate:** `alt_instance_gate`
- **sources (authority):** `invariant:ALT-I-02`, `file:ugk/invariants.py`, `gate:alt_instance_gate`
- **provenance (build lane, not semantic standing):** `phase16`

### ALT-I-03 — Constitutive probe result (ALT-I-03)
*subsystem:* ALT · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

When require_scoped_intent=True, only declarations with scope_ref matching session_dkn are active.

- **gate:** `alt_instance_gate`
- **sources (authority):** `invariant:ALT-I-03`, `file:ugk/invariants.py`, `gate:alt_instance_gate`
- **provenance (build lane, not semantic standing):** `phase16`

### ALT-I-04 — Constitutive probe result (ALT-I-04)
*subsystem:* ALT · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

φ(S)=(ceremonial+unprobed APPLICATION_OPs)/(total APPLICATION_OPs).

- **gate:** `alt_instance_gate`
- **sources (authority):** `invariant:ALT-I-04`, `file:ugk/invariants.py`, `gate:alt_instance_gate`
- **provenance (build lane, not semantic standing):** `phase16`

### CGP-S-01 — Governance posture (content-addressed) (CGP-S-01)
*subsystem:* CGP · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

GovernancePosture is content-addressed (posture_hash=SHA-256(canonical_json(body))).

- **gate:** `posture_gate`
- **sources (authority):** `invariant:CGP-S-01`, `file:ugk/invariants.py`, `gate:posture_gate`
- **provenance (build lane, not semantic standing):** `phase18`

### CGP-S-02 — Governance posture (content-addressed) (CGP-S-02)
*subsystem:* CGP · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

ugk health covers five sub-checks: chain integrity, authority model, posture vector, disjunct coverage, and gate compliance.

- **gate:** `health_surface_gate`
- **sources (authority):** `invariant:CGP-S-02`, `file:ugk/invariants.py`, `gate:health_surface_gate`
- **provenance (build lane, not semantic standing):** `phase18`

### CGP-S-03 — Governance posture (content-addressed) (CGP-S-03)
*subsystem:* CGP · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

GATE_GROUP annotation on each gate file classifies it into structural|unit|integration|conformance groups.

- **gate:** `health_surface_gate`
- **sources (authority):** `invariant:CGP-S-03`, `file:ugk/invariants.py`, `gate:health_surface_gate`
- **provenance (build lane, not semantic standing):** `phase18`

### CHARTER-S-01 — Deployment manifest / charter (CHARTER-S-01)
*subsystem:* CHARTER · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

DeploymentManifest is content-addressed.

- **gate:** `charter_gate`
- **sources (authority):** `invariant:CHARTER-S-01`, `file:ugk/invariants.py`, `gate:charter_gate`
- **provenance (build lane, not semantic standing):** `phase20`

### CHARTER-S-02 — Deployment manifest / charter (CHARTER-S-02)
*subsystem:* CHARTER · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

ugk charter is the founding constitutional act.

- **gate:** `charter_gate`
- **sources (authority):** `invariant:CHARTER-S-02`, `file:ugk/invariants.py`, `gate:charter_gate`
- **provenance (build lane, not semantic standing):** `phase20`

### DW-S-01 — Decision warrant (content-addressed) (DW-S-01)
*subsystem:* DW · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

DecisionWarrant is a first-class content-addressed artifact.

- **gate:** `warrant_gate`
- **sources (authority):** `invariant:DW-S-01`, `file:ugk/invariants.py`, `gate:warrant_gate`
- **provenance (build lane, not semantic standing):** `phase6`

### DW-S-02 — Decision warrant (content-addressed) (DW-S-02)
*subsystem:* DW · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

The warrant DAG is acyclic.

- **gate:** `warrant_lineage_gate`
- **sources (authority):** `invariant:DW-S-02`, `file:ugk/invariants.py`, `gate:warrant_lineage_gate`
- **provenance (build lane, not semantic standing):** `phase6`

### DW-S-03 — Decision warrant (content-addressed) (DW-S-03)
*subsystem:* DW · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Refusal warrants are produced when gate() returns False and warrant_basis is provided by the caller.

- **gate:** `refusal_warrant_gate`
- **sources (authority):** `invariant:DW-S-03`, `file:ugk/invariants.py`, `gate:refusal_warrant_gate`
- **provenance (build lane, not semantic standing):** `phase9`

### SUM-S-01 — Session summary
*subsystem:* SUM · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

SessionSummary is produced at close_session() when a WarrantStore is attached.

- **gate:** `session_summary_gate`
- **sources (authority):** `invariant:SUM-S-01`, `file:ugk/invariants.py`, `gate:session_summary_gate`
- **provenance (build lane, not semantic standing):** `phase9`

### WILL-S-01 — Intent declaration (content-addressed) (WILL-S-01)
*subsystem:* WILL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

IntentDeclaration is content-addressed.

- **gate:** `intent_declaration_gate`
- **sources (authority):** `invariant:WILL-S-01`, `file:ugk/invariants.py`, `gate:intent_declaration_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### WILL-S-02 — Intent declaration (content-addressed) (WILL-S-02)
*subsystem:* WILL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

R_int is the least fixpoint of declared ops under admissible production_edges.

- **gate:** `will_checker_gate`
- **sources (authority):** `invariant:WILL-S-02`, `file:ugk/invariants.py`, `gate:will_checker_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### WILL-S-03 — Intent declaration (content-addressed) (WILL-S-03)
*subsystem:* WILL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Coverage is fail-closed when require_intent=True on the kernel.

- **gate:** `will_checker_gate`
- **sources (authority):** `invariant:WILL-S-03`, `file:ugk/invariants.py`, `gate:will_checker_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### WILL-S-04 — Intent declaration (content-addressed) (WILL-S-04)
*subsystem:* WILL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

IntentRevocation is permanent and unfalsifiable.

- **gate:** `intent_declaration_gate`
- **sources (authority):** `invariant:WILL-S-04`, `file:ugk/invariants.py`, `gate:intent_declaration_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### WILL-S-05 — Intent declaration (content-addressed) (WILL-S-05)
*subsystem:* WILL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

When WillChecker.covers() returns COVERED, receipt.intent_ref records the covering IntentDeclaration hash.

- **gate:** `intent_receipt_gate`
- **sources (authority):** `invariant:WILL-S-05`, `file:ugk/invariants.py`, `gate:intent_receipt_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### WILL-S-06 — Intent declaration (content-addressed) (WILL-S-06)
*subsystem:* WILL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Coverage is computed BEFORE the success receipt is written, which is BEFORE the effect executes (NBER-1 preserved).

- **gate:** `will_coverage_gate`
- **sources (authority):** `invariant:WILL-S-06`, `file:ugk/invariants.py`, `gate:will_coverage_gate`
- **provenance (build lane, not semantic standing):** `phase13`

## effect-truthfulness

### DCAP-S-01 — Capability-sufficiency precondition
*subsystem:* DCAP · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* admissibility-precondition  
*continuity:* stable · *last verified:* r169  

D_cap enforcement -- sibling capability-sufficiency precondition (opt-in, enumerated).

- **gate:** `capability_sufficiency_policy_gate`
- **sources (authority):** `invariant:DCAP-S-01`, `file:ugk/invariants.py`, `gate:capability_sufficiency_policy_gate`
- **provenance (build lane, not semantic standing):** `dcap-enforcement-law-leg`

### EFFECT-S-01 — Effect-trail integrity (EFFECT-S-01)
*subsystem:* EFFECT · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*effect-class scope:* PURE, STORE_LOCAL, EXTERNAL_REVERSIBLE, EXTERNAL_IRREVERSIBLE, NON_ATOMIC  
*continuity:* stable · *last verified:* r169  

Effect-trail integrity (marker-era).

- **gate:** `effect_trail_integrity_gate`
- **sources (authority):** `invariant:EFFECT-S-01`, `file:ugk/invariants.py`, `gate:effect_trail_integrity_gate`
- **provenance (build lane, not semantic standing):** `effect-trail-integrity`

### EFFECT-S-02 — Effect-trail integrity (EFFECT-S-02)
*subsystem:* EFFECT · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*effect-class scope:* PURE, STORE_LOCAL, EXTERNAL_REVERSIBLE, EXTERNAL_IRREVERSIBLE, NON_ATOMIC  
*continuity:* stable · *last verified:* r169  

Typed-column effect-trail integrity (v>=4).

- **gate:** `effect_trail_integrity_gate`
- **sources (authority):** `invariant:EFFECT-S-02`, `file:ugk/invariants.py`, `gate:effect_trail_integrity_gate`
- **provenance (build lane, not semantic standing):** `typed-effect-law-leg`

## frame-governance

### ATLAS-S-01 — Invariant dependency-graph integrity (ATLAS-S-01)
*subsystem:* ATLAS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Every Invariant in INVARIANT_REGISTRY has a valid depends_on tuple whose members are all present in the registry.

- **gate:** `primitive_dependency_gate`
- **sources (authority):** `invariant:ATLAS-S-01`, `file:ugk/invariants.py`, `gate:primitive_dependency_gate`
- **provenance (build lane, not semantic standing):** `phase10`

### ATLAS-S-02 — Invariant dependency-graph integrity (ATLAS-S-02)
*subsystem:* ATLAS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

compound_capabilities in adr.py maps capability names to frozensets of invariant IDs.

- **gate:** `compound_capability_gate`
- **sources (authority):** `invariant:ATLAS-S-02`, `file:ugk/invariants.py`, `gate:compound_capability_gate`
- **provenance (build lane, not semantic standing):** `phase10`

### ATLAS-S-03 — Invariant dependency-graph integrity (ATLAS-S-03)
*subsystem:* ATLAS · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

ADR_REGISTRY in adr.py contains at least one ArchitecturalDecision per major design choice.

- **gate:** `adr_gate`
- **sources (authority):** `invariant:ATLAS-S-03`, `file:ugk/invariants.py`, `gate:adr_gate`
- **provenance (build lane, not semantic standing):** `phase10`

### ATLAS-S-04 — Invariant dependency-graph integrity (ATLAS-S-04)
*subsystem:* ATLAS · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

CODEX.md is a projected representation of the semantic atlas.

- **gate:** `codex_integrity_gate`
- **sources (authority):** `invariant:ATLAS-S-04`, `file:ugk/invariants.py`, `gate:codex_integrity_gate`
- **provenance (build lane, not semantic standing):** `phase10`

### CTR-S-01 — Invariant staleness pin (CTR-S-01)
*subsystem:* CTR · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

The invariant registry (this file) IS the coverage map.

- **gate:** `invariant_registry_gate`
- **sources (authority):** `invariant:CTR-S-01`, `file:ugk/invariants.py`, `gate:invariant_registry_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CTR-S-07 — Invariant staleness pin (CTR-S-07)
*subsystem:* CTR · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Staleness gate: a SHA-256 pin of invariants.py content is maintained.

- **gate:** `staleness_gate`
- **sources (authority):** `invariant:CTR-S-07`, `file:ugk/invariants.py`, `gate:staleness_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### LEGEND-S-01 — LEGEND constant integrity (LEGEND-S-01)
*subsystem:* LEGEND · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

The LEGEND constant in binding.py is content-addressed and stable.

- **gate:** `legend_hash_gate`
- **sources (authority):** `invariant:LEGEND-S-01`, `file:ugk/invariants.py`, `gate:legend_hash_gate`
- **provenance (build lane, not semantic standing):** `phase6`

### LEGEND-S-02 — LEGEND constant integrity (LEGEND-S-02)
*subsystem:* LEGEND · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

store.write(compress=True) stores CSIL integers for op/intent/jurisdiction/confidence fields.

- **gate:** `compression_roundtrip_gate`
- **sources (authority):** `invariant:LEGEND-S-02`, `file:ugk/invariants.py`, `gate:compression_roundtrip_gate`
- **provenance (build lane, not semantic standing):** `phase6`

### LEGEND-S-03 — LEGEND constant integrity (LEGEND-S-03)
*subsystem:* LEGEND · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

legend_hash appears in the dm_s03 CHC envelope on ACTIVE receipts.

- **gate:** `legend_chc_gate`
- **sources (authority):** `invariant:LEGEND-S-03`, `file:ugk/invariants.py`, `gate:legend_chc_gate`
- **provenance (build lane, not semantic standing):** `phase6`

### LEGEND-S-04 — LEGEND constant integrity (LEGEND-S-04)
*subsystem:* LEGEND · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Every compressed receipt field value has a valid LEGEND_BY_SLUG entry.

- **gate:** `projection_continuity_gate`
- **sources (authority):** `invariant:LEGEND-S-04`, `file:ugk/invariants.py`, `gate:projection_continuity_gate`
- **provenance (build lane, not semantic standing):** `phase6`

### PED-S-01 — Concept-introduction discipline
*subsystem:* PED · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Every concept introduced into the UGK authority surface must have a LEGEND entry, an invariant or ADR describing its physics, and a ugk explain resolution path.

- **gate:** `constitution_surface_gate`
- **sources (authority):** `invariant:PED-S-01`, `file:ugk/invariants.py`, `gate:constitution_surface_gate`
- **provenance (build lane, not semantic standing):** `phase17`

### UL-G-01 — Grundnorm layer integrity (UL-G-01)
*subsystem:* UL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

The Grundnorm layer (kernel.py, schema.py, store.py, binding.py, broker.py, invariants.py, dimensions.py) is read-only after installation (file permissions 444).

- **gate:** `grundnorm_readonly_gate`
- **sources (authority):** `invariant:UL-G-01`, `file:ugk/invariants.py`, `gate:grundnorm_readonly_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### UL-L-01 — Grundnorm layer integrity (UL-L-01)
*subsystem:* UL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

All UGK modules import in a single Python process without side effects.

- **gate:** `liveness_gate`
- **sources (authority):** `invariant:UL-L-01`, `file:ugk/invariants.py`, `gate:liveness_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### UL-S-01 — Grundnorm layer integrity (UL-S-01)
*subsystem:* UL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Zero external runtime dependencies.

- **gate:** `zero_deps_gate`
- **sources (authority):** `invariant:UL-S-01`, `file:ugk/invariants.py`, `gate:zero_deps_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### UL-S-02 — Grundnorm layer integrity (UL-S-02)
*subsystem:* UL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Receipt-before-effect is kernel-enforced at the API level, not convention.

- **gate:** `nber1_gate`
- **sources (authority):** `invariant:UL-S-02`, `file:ugk/invariants.py`, `gate:nber1_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### UL-S-03 — Grundnorm layer integrity (UL-S-03)
*subsystem:* UL · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

Every op submitted to execute() must be declared in GOVERNANCE_OPS before execution (BS-01).

- **gate:** `bs01_gate`
- **sources (authority):** `invariant:UL-S-03`, `file:ugk/invariants.py`, `gate:bs01_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### UL-S-04 — Grundnorm layer integrity (UL-S-04)
*subsystem:* UL · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

The kernel provides a native ESA self-check (~5 governance-generic capabilities) and a valid 10-axis SRSA vector without any application-layer dependency.

- **gate:** `esa_selfcheck_gate`
- **sources (authority):** `invariant:UL-S-04`, `file:ugk/invariants.py`, `gate:esa_selfcheck_gate`
- **provenance (build lane, not semantic standing):** `phase1`

## identity-and-vocabulary

### CSIL-S-01 — Canonical semantic-integer layer (CSIL-S-01)
*subsystem:* CSIL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

APPLICATION_OPs with csil_id>0 in GOVERNANCE_OPS carry op_csil in receipt parameters.

- **gate:** `csil_floor_gate`
- **sources (authority):** `invariant:CSIL-S-01`, `file:ugk/invariants.py`, `gate:csil_floor_gate`
- **provenance (build lane, not semantic standing):** `phase19`

### CSIL-S-02 — Canonical semantic-integer layer (CSIL-S-02)
*subsystem:* CSIL · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

The invariant dependency graph (depends_on fields) is the semantic topology over CSIL invariant tier.

- **gate:** `csil_topology_gate`
- **sources (authority):** `invariant:CSIL-S-02`, `file:ugk/invariants.py`, `gate:csil_topology_gate`
- **provenance (build lane, not semantic standing):** `phase19`

### DKN-S-01 — Session DKN identity
*subsystem:* DKN · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

session_dkn = SHA-256(mosaic_root:phase_code:session_id).

- **gate:** `dkn_gate`
- **sources (authority):** `invariant:DKN-S-01`, `file:ugk/invariants.py`, `gate:dkn_gate`
- **provenance (build lane, not semantic standing):** `phase20`

## jurisdiction-projection

### SCOPE-S-01 — Provenance scope (SCOPE-S-01)
*subsystem:* SCOPE · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

ProvenanceScope is emitted at session_open and stored in scope_archive table in ugk.db.

- **gate:** `provenance_scope_gate`
- **sources (authority):** `invariant:SCOPE-S-01`, `file:ugk/invariants.py`, `gate:provenance_scope_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### SCOPE-S-02 — Provenance scope (SCOPE-S-02)
*subsystem:* SCOPE · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Replay admissibility: a receipt from a closed session is not admissible as a new-session operation.

- **gate:** `scope_archive_gate`
- **sources (authority):** `invariant:SCOPE-S-02`, `file:ugk/invariants.py`, `gate:scope_archive_gate`
- **provenance (build lane, not semantic standing):** `phase13`

### SRSA-S-01 — SRSA jurisdiction vector
*subsystem:* SRSA · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

ugk.srsa_vector() returns a valid 10-axis SRSA vector for this kernel instance.

- **gate:** `srsa_vector_gate`
- **sources (authority):** `invariant:SRSA-S-01`, `file:ugk/invariants.py`, `gate:srsa_vector_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### SSA-VOCAB-S-01 — Governance-generic verb vocabulary
*subsystem:* SSA · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* frame-constraint  
*continuity:* stable · *last verified:* r169  

INTENT_TYPES in core/vocab.py contains exactly 17 governance-generic semantic verbs (Governor-confirmed, Phase 12).

- **gate:** `ssa_vocabulary_gate`
- **sources (authority):** `invariant:SSA-VOCAB-S-01`, `file:ugk/invariants.py`, `gate:ssa_vocabulary_gate`
- **provenance (build lane, not semantic standing):** `phase12`

## namespace-authority

### NS-S-01 — Namespace ownership projection (NS-S-01)
*subsystem:* NS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Namespace OWNERSHIP is a deterministic receipt-chain projection: owner_of(name) is derived by folding the receipt chain (namespace_governance.project_owners); the projection is stable/deterministic; t

- **gate:** `namespace_governance_gate`
- **sources (authority):** `invariant:NS-S-01`, `file:ugk/invariants.py`, `gate:namespace_governance_gate`
- **provenance (build lane, not semantic standing):** `phase20`

### NS-S-02 — Namespace ownership projection (NS-S-02)
*subsystem:* NS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

namespace_claim and namespace_allocate are DISTINCT receipted transitions and MUST NOT be collapsed into one op (FGA §10).

- **gate:** `namespace_governance_gate`
- **sources (authority):** `invariant:NS-S-02`, `file:ugk/invariants.py`, `gate:namespace_governance_gate`
- **provenance (build lane, not semantic standing):** `phase20`

### NS-S-03 — Namespace ownership projection (NS-S-03)
*subsystem:* NS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Allocation conflict policy is REFUSE (fail-closed v0): a colliding allocation — the SAME canonical name (namespace_governance.canonicalize) by a DIFFERENT authority — is gate_refused (a gate_refuse re

- **gate:** `namespace_governance_gate`
- **sources (authority):** `invariant:NS-S-03`, `file:ugk/invariants.py`, `gate:namespace_governance_gate`
- **provenance (build lane, not semantic standing):** `phase20`

### NS-S-04 — Namespace ownership projection (NS-S-04)
*subsystem:* NS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Namespace ownership-lifecycle operations — delegation, revocation, invalidation, and supersession — take effect only when the receipt authority is the current owner of the canonical name.

- **gate:** `namespace_governance_gate`
- **sources (authority):** `invariant:NS-S-04`, `file:ugk/invariants.py`, `gate:namespace_governance_gate`
- **provenance (build lane, not semantic standing):** `namespace-2bc`

### NS-S-05 — Namespace ownership projection (NS-S-05)
*subsystem:* NS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Revocation and invalidation permanently remove a canonical name from ownership under the WILL-S-04 permanence pattern.

- **gate:** `namespace_governance_gate`
- **sources (authority):** `invariant:NS-S-05`, `file:ugk/invariants.py`, `gate:namespace_governance_gate`
- **provenance (build lane, not semantic standing):** `namespace-2bc`

### NS-S-06 — Namespace ownership projection (NS-S-06)
*subsystem:* NS · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* receipt-evidence  
*continuity:* stable · *last verified:* r169  

Adjudication of a contested canonical name is constitutional-Governor-only.

- **gate:** `namespace_governance_gate`
- **sources (authority):** `invariant:NS-S-06`, `file:ugk/invariants.py`, `gate:namespace_governance_gate`
- **provenance (build lane, not semantic standing):** `namespace-2bc`

## receipt-chain-integrity

### CHC-S-01 — Receipt commitment-hash binding (CHC-S-01)
*subsystem:* CHC · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Every receipt carries the THR-conformant binding structure: per-commitment hashes (H_s, H_c, H_m, and H_j when scope warrants), a binding root H_r = H(DS_r ∥ id(root_v1) ∥ root(leaves)) computed as a

- **gate:** `binding_gate`
- **sources (authority):** `invariant:CHC-S-01`, `file:ugk/invariants.py`, `gate:binding_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CHC-S-02 — Receipt commitment-hash binding (CHC-S-02)
*subsystem:* CHC · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Each c_i canonicalization function (i ∈ {s, c, m, j}) is deterministic and byte-stable per THR §5: identical typed inputs produce byte-identical H_i.

- **gate:** `determinism_gate`
- **sources (authority):** `invariant:CHC-S-02`, `file:ugk/invariants.py`, `gate:determinism_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CHC-S-03 — Receipt commitment-hash binding (CHC-S-03)
*subsystem:* CHC · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Per-commitment independence and global nonrepudiation: altering the typed input to any one c_i changes that H_i without changing the others (cryptographic independence, THR §11); altering any leaf cha

- **gate:** `nonrepudiation_gate`
- **sources (authority):** `invariant:CHC-S-03`, `file:ugk/invariants.py`, `gate:nonrepudiation_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### CHC-S-04 — Receipt commitment-hash binding (CHC-S-04)
*subsystem:* CHC · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Commitment Minimality (THR §10.4): the leaf set under H_r contains only facts whose canonicalization input domain is not a subset of any other present leaf's input domain, except for entries explicitl

- **gate:** `commitment_minimality_gate`
- **sources (authority):** `invariant:CHC-S-04`, `file:ugk/invariants.py`, `gate:commitment_minimality_gate`
- **provenance (build lane, not semantic standing):** `phase1-m2`

### DM-S-01 — Append-only receipt immutability (DM-S-01)
*subsystem:* DM · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Committed receipts cannot be retroactively modified.

- **gate:** `nonretroactivity_gate`
- **sources (authority):** `invariant:DM-S-01`, `file:ugk/invariants.py`, `gate:nonretroactivity_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### DM-S-03 — Append-only receipt immutability (DM-S-03)
*subsystem:* DM · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

All receipts are stream-chained: each receipt's H_c canonicalization input carries the prior receipt's H_r as `parent_H_r`.

- **gate:** `chain_gate`
- **sources (authority):** `invariant:DM-S-03`, `file:ugk/invariants.py`, `gate:chain_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### IEL-S-01 — Whole-body receipt integrity
*subsystem:* IEL · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

Receipt-body integrity is runtime-verifiable and enforced over the WHOLE committed body.

- **gate:** `receipt_commitment_integrity_gate`
- **sources (authority):** `invariant:IEL-S-01`, `file:ugk/invariants.py`, `gate:receipt_commitment_integrity_gate`
- **provenance (build lane, not semantic standing):** `iel-phase1`

### PERSIST-S-01 — Receipt-store chain hydration
*subsystem:* PERSIST · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* verification-claim  
*continuity:* stable · *last verified:* r169  

UGKReceiptStore opened on an existing database hydrates _prior_hash from the chain tip (latest semantic_hash), not from genesis.

- **gate:** `persistence_gate`
- **sources (authority):** `invariant:PERSIST-S-01`, `file:ugk/invariants.py`, `gate:persistence_gate`
- **provenance (build lane, not semantic standing):** `phase7`

## terminal-outcome

### BRIDGE-BINDING — BRIDGE surface-validity binding
*subsystem:* BRIDGE · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* admissibility-precondition  
*continuity:* stable · *last verified:* r169  

BRIDGE surface-validity binding (CK-BRIDGE Stage 3, law leg; UGK-BODY-v8).

- **gate:** `bridge_binding_gate`
- **sources (authority):** `invariant:BRIDGE-BINDING`, `file:ugk/invariants.py`, `gate:bridge_binding_gate`
- **provenance (build lane, not semantic standing):** `bridge-binding-law`

### DEFER-S-01 — DEFER continuation lifecycle
*subsystem:* DEFER · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* outcome-correspondence  
*continuity:* stable · *last verified:* r169  

The DEFER continuation lifecycle.

- **gate:** `defer_lifecycle_gate`
- **sources (authority):** `invariant:DEFER-S-01`, `file:ugk/invariants.py`, `gate:defer_lifecycle_gate`
- **provenance (build lane, not semantic standing):** `defer-continuation-lifecycle`

### ESA-S-01 — Gate-refusal constitutive outcome
*subsystem:* ESA · *classification:* MIXED · *frame role:* law-backed-invariant · *authority role:* outcome-correspondence  
*continuity:* stable · *last verified:* r169  

GateRefusal is a first-class constitutive outcome.

- **gate:** `refusal_gate`
- **sources (authority):** `invariant:ESA-S-01`, `file:ugk/invariants.py`, `gate:refusal_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### GK-S-01 — Fail-closed admission gating (GK-S-01)
*subsystem:* GK · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* admissibility-precondition  
*continuity:* stable · *last verified:* r169  

Admission is blocking and fail-closed.

- **gate:** `enforcement_gate`
- **sources (authority):** `invariant:GK-S-01`, `file:ugk/invariants.py`, `gate:enforcement_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### GK-S-02 — Fail-closed admission gating (GK-S-02)
*subsystem:* GK · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* admissibility-precondition  
*continuity:* stable · *last verified:* r169  

The W/G/E reactor fires in fixed order: gate() before effect(), gate_admit receipt before the op receipt, op receipt before effect().

- **gate:** `admission_gate`
- **sources (authority):** `invariant:GK-S-02`, `file:ugk/invariants.py`, `gate:admission_gate`
- **provenance (build lane, not semantic standing):** `phase1`

### RECON-S-01 — Verified-grade reconciliation
*subsystem:* RECON · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* outcome-correspondence  
*continuity:* stable · *last verified:* r169  

Verified-grade reconciliation self-containment (opt-in).

- **gate:** `external_irreversible_pilot_gate`
- **sources (authority):** `invariant:RECON-S-01`, `file:ugk/invariants.py`, `gate:external_irreversible_pilot_gate`
- **provenance (build lane, not semantic standing):** `verified-grade-law-leg`

### TO-S-01 — Terminal-outcome correspondence
*subsystem:* TO · *classification:* DOMAIN_PHYSICS · *frame role:* law-backed-invariant · *authority role:* outcome-correspondence  
*continuity:* stable · *last verified:* r169  

Where a receipt commits a terminal-outcome projection under UGK-BODY version >= 2, the committed projection tuple — terminal_outcome, terminal_outcome_model_id, and terminal_outcome_reason — must corr

- **gate:** `terminal_outcome_commit_gate`
- **sources (authority):** `invariant:TO-S-01`, `file:ugk/invariants.py`, `gate:terminal_outcome_commit_gate`
- **provenance (build lane, not semantic standing):** `terminal-outcome-correspondence`

