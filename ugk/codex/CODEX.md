# UGK v0.1.0 — Constitutional Codex (Phases 0-20)
*Derived projection (codex_gen) of invariants.py — leaf artifact, not a source.*
**LEGEND_HASH:** `db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7`  
Registry entries: 87  ADRs: 70  LEGEND: 101
Routing: S-inherited 10 · S-residue 8 (declared exclusion) · IC 2 · IR 67
---
## S — inherited / restated obligations
*Restate GK domain obligations UGK discharges. Authoritative S source is invariants.py; see the Application Codex inheritance table for the discharge mapping.*

**NAMESPACE-2BC**

- **NS-S-04** -- Namespace ownership-lifecycle operations — delegation, revocation, inv...
- **NS-S-05** -- Revocation and invalidation permanently remove a canonical name from o...
- **NS-S-06** -- Adjudication of a contested canonical name is constitutional-Governor-...

**PHASE1**

- **DM-S-01** -- Committed receipts cannot be retroactively modified.  The store is app...
- **DM-S-03** -- All receipts are stream-chained: each receipt's H_c canonicalization i...
- **EH-S-01** -- Typed exception hierarchy: KernelInternalOp (Tier 0 external call), Go...
- **GK-S-01** -- Admission is blocking and fail-closed.  gate() returning False halts e...

**PHASE20**

- **NS-S-01** -- Namespace OWNERSHIP is a deterministic receipt-chain projection: owner...
- **NS-S-02** -- namespace_claim and namespace_allocate are DISTINCT receipted transiti...
- **NS-S-03** -- Allocation conflict policy is REFUSE (fail-closed v0): a colliding all...

## S-candidate residue — declared exclusion
*Carried, NOT adjudicated as S, pending independent residue-blind re-derivation (Phase 6). The interpretive-closure / semantic-frame cluster.*

**PHASE12**

- **SSA-VOCAB-S-01** -- INTENT_TYPES in core/vocab.py contains exactly 17 governance-generic s...

**PHASE17**

- **PED-S-01** -- Every concept introduced into the UGK authority surface must have a LE...

**PHASE19**

- **CSIL-S-01** -- APPLICATION_OPs with csil_id>0 in GOVERNANCE_OPS carry op_csil in rece...
- **CSIL-S-02** -- The invariant dependency graph (depends_on fields) is the semantic top...

**PHASE6**

- **LEGEND-S-01** -- The LEGEND constant in binding.py is content-addressed and stable. LEG...
- **LEGEND-S-02** -- store.write(compress=True) stores CSIL integers for op/intent/jurisdic...
- **LEGEND-S-03** -- legend_hash appears in the dm_s03 CHC envelope on ACTIVE receipts. Alt...
- **LEGEND-S-04** -- Every compressed receipt field value has a valid LEGEND_BY_SLUG entry....

## IC — selected configuration commitments
*Selections from the GK configuration manifold (realized in code).*

**PHASE1**

- **CM-DIM-01** -- Every Dimension in dimensions.py has its current selection within the ...
- **UL-S-01** -- Zero external runtime dependencies.  UGK uses only stdlib (hashlib, sq...

## IR — realized mechanisms and checks
*Realizations registered in the invariant registry; they discharge inherited GK obligations but are not themselves novel domain physics.*

**BRIDGE-BINDING-LAW**

- **BRIDGE-BINDING** -- BRIDGE surface-validity binding (CK-BRIDGE Stage 3, law leg; UGK-BODY-...

**DCAP-ENFORCEMENT-LAW-LEG**

- **DCAP-S-01** -- D_cap enforcement -- sibling capability-sufficiency precondition (opt-...

**DEFER-CONTINUATION-LIFECYCLE**

- **DEFER-S-01** -- The DEFER continuation lifecycle. A live DEFER terminal (per TO-S-01) ...

**EFFECT-TRAIL-INTEGRITY**

- **EFFECT-S-01** -- Effect-trail integrity (marker-era). SCOPE: receipts at body-schema ve...

**IEL-PHASE1**

- **IEL-S-01** -- Receipt-body integrity is runtime-verifiable and enforced over the WHO...

**PHASE1**

- **ADV-S-01** -- Four adversarial rug-pulls are each detected: (1) CHC field tamper cha...
- **CHC-S-01** -- Every receipt carries the THR-conformant binding structure: per-commit...
- **CHC-S-02** -- Each c_i canonicalization function (i ∈ {s, c, m, j}) is deterministic...
- **CHC-S-03** -- Per-commitment independence and global nonrepudiation: altering the ty...
- **CM-GS-01** -- Governance status transitions UNINITIALIZED → ACTIVE via the founding ...
- **CM-GS-02** -- The shipped kernel GOVERNOR_PUBKEY_HEX is the unset sentinel 'GOVERNOR...
- **CM-OP-01** -- Three-tier op jurisdiction is enforced by execute().  Tier 0 ops (gate...
- **CR-S-01** -- CLASSIFIED_REMAINDERS (CR-01..CR-04) are declared in the kernel: OS la...
- **CR-S-02** -- CLASSIFIED_REMAINDERS are inert — no capability flows from a declared ...
- **CTR-S-01** -- The invariant registry (this file) IS the coverage map.  Every Invaria...
- **CTR-S-07** -- Staleness gate: a SHA-256 pin of invariants.py content is maintained. ...
- **EH-S-02** -- Chain corruption recovery: last_valid_frontier() identifies the receip...
- **ESA-S-01** -- GateRefusal is a first-class constitutive outcome.  A gate_refuse rece...
- **GK-S-02** -- The W/G/E reactor fires in fixed order: gate() before effect(), gate_a...
- **SRSA-S-01** -- ugk.srsa_vector() returns a valid 10-axis SRSA vector for this kernel ...
- **UL-G-01** -- The Grundnorm layer (kernel.py, schema.py, store.py, binding.py, broke...
- **UL-L-01** -- All UGK modules import in a single Python process without side effects...
- **UL-S-02** -- Receipt-before-effect is kernel-enforced at the API level, not convent...
- **UL-S-03** -- Every op submitted to execute() must be declared in GOVERNANCE_OPS bef...
- **UL-S-04** -- The kernel provides a native ESA self-check (~5 governance-generic cap...

**PHASE1-M2**

- **CHC-S-04** -- Commitment Minimality (THR §10.4): the leaf set under H_r contains onl...

**PHASE10**

- **ATLAS-S-01** -- Every Invariant in INVARIANT_REGISTRY has a valid depends_on tuple who...
- **ATLAS-S-02** -- compound_capabilities in adr.py maps capability names to frozensets of...
- **ATLAS-S-03** -- ADR_REGISTRY in adr.py contains at least one ArchitecturalDecision per...
- **ATLAS-S-04** -- CODEX.md is a projected representation of the semantic atlas. SHA-256(...

**PHASE13**

- **SCOPE-S-01** -- ProvenanceScope is emitted at session_open and stored in scope_archive...
- **SCOPE-S-02** -- Replay admissibility: a receipt from a closed session is not admissibl...
- **SUCC-S-01** -- SuccessorLineage is a cryptographic succession proof. succession_proof...
- **WILL-S-01** -- IntentDeclaration is content-addressed. declaration_hash = SHA-256(can...
- **WILL-S-02** -- R_int is the least fixpoint of declared ops under admissible productio...
- **WILL-S-03** -- Coverage is fail-closed when require_intent=True on the kernel. No act...
- **WILL-S-04** -- IntentRevocation is permanent and unfalsifiable. A revoked declaration...
- **WILL-S-05** -- When WillChecker.covers() returns COVERED, receipt.intent_ref records ...
- **WILL-S-06** -- Coverage is computed BEFORE the success receipt is written, which is B...

**PHASE15**

- **CM-S-01** -- AuthorityModel is content-addressed. model_hash=SHA-256(canonical_json...
- **CM-S-02** -- When require_gate=True, APPLICATION_OPs without a gate raise KernelInt...
- **CM-S-03** -- When require_warrant=True, execute() without warrant_basis raises Kern...
- **CM-S-04** -- AuthorityModel sealed to authority_model_archive at set_authority_mode...

**PHASE16**

- **ALT-I-01** -- ConstitutiveProbeResult is content-addressed. CONSTITUTIVE: gate refus...
- **ALT-I-02** -- When authority_set supplied to execute(), receipt carries authority_se...
- **ALT-I-03** -- When require_scoped_intent=True, only declarations with scope_ref matc...
- **ALT-I-04** -- φ(S)=(ceremonial+unprobed APPLICATION_OPs)/(total APPLICATION_OPs). φ=...

**PHASE17**

- **AMD-S-02** -- Amendment-model-at-inception: the DeploymentManifest declares amendmen...
- **AMD-S-03** -- Amendment admissibility (frame-general): a constitutional-frame transi...

**PHASE18**

- **CGP-S-01** -- GovernancePosture is content-addressed (posture_hash=SHA-256(canonical...
- **CGP-S-02** -- ugk health covers five sub-checks: chain integrity, authority model, p...
- **CGP-S-03** -- GATE_GROUP annotation on each gate file classifies it into structural|...

**PHASE20**

- **CHARTER-S-01** -- DeploymentManifest is content-addressed. governor_pubkey and phase_cod...
- **CHARTER-S-02** -- ugk charter is the founding constitutional act. --pubkey is required m...
- **DKN-S-01** -- session_dkn = SHA-256(mosaic_root:phase_code:session_id). WHO×WHAT×WHI...

**PHASE6**

- **DW-S-01** -- DecisionWarrant is a first-class content-addressed artifact. warrant_h...
- **DW-S-02** -- The warrant DAG is acyclic. basis_query(csil_id) returns all warrants ...

**PHASE7**

- **PERSIST-S-01** -- UGKReceiptStore opened on an existing database hydrates _prior_hash fr...

**PHASE8**

- **AUDIT-S-01** -- AuditSession is a read-only governed surface. It must never call store...
- **AUDIT-S-02** -- The legend_archive table in ugk.db contains every LEGEND version by le...
- **AUDIT-S-03** -- AuditSession.receipts_for_warrant(warrant_hash) returns a correct, com...

**PHASE9**

- **AMD-S-01** -- AmendmentRecord is a first-class content-addressed artifact documentin...
- **DW-S-03** -- Refusal warrants are produced when gate() returns False and warrant_ba...
- **SUM-S-01** -- SessionSummary is produced at close_session() when a WarrantStore is a...

**TERMINAL-OUTCOME-CORRESPONDENCE**

- **TO-S-01** -- Where a receipt commits a terminal-outcome projection under UGK-BODY v...

**TYPED-EFFECT-LAW-LEG**

- **EFFECT-S-02** -- Typed-column effect-trail integrity (v>=4). For receipts at body-schem...

**VERIFIED-GRADE-LAW-LEG**

- **RECON-S-01** -- Verified-grade reconciliation self-containment (opt-in). For a reconci...

## ADRs


### AD-01
**Bound:** CM-OP-01, EH-S-01, GK-S-01, UL-S-03

### AD-02
**Bound:** UL-S-02

### AD-03
**Bound:** CHC-S-01, CHC-S-02, CHC-S-03

### AD-04
**Bound:** CTR-S-01, CTR-S-07

### AD-05
**Bound:** UL-G-01, ADV-S-01

### AD-06
**Bound:** LEGEND-S-02, LEGEND-S-04

### AD-07
**Bound:** AUDIT-S-01

### AD-10
**Bound:** CM-S-01, CM-S-02, CM-S-03, CM-S-04

### AD-11
**Bound:** ALT-I-01, ALT-I-02, ALT-I-03, ALT-I-04

### AD-12
**Bound:** CGP-S-01, CGP-S-02, CGP-S-03

### AD-13
**Bound:** CSIL-S-01, CSIL-S-02

### AD-14
**Bound:** DKN-S-01, CHARTER-S-01

### AD-15
**Bound:** GK-S-01, CM-OP-01, EH-S-01, DM-S-01, DKN-S-01

### AD-16
**Bound:** AMD-S-01, AMD-S-03, CTR-S-07

### AD-17
**Bound:** NS-S-01, NS-S-02, NS-S-03, AMD-S-03

### AD-18
**Bound:** AMD-S-03, SUCC-S-01, AMD-S-01

### AD-19
**Bound:** AMD-S-01, AMD-S-03

### AD-20
**Bound:** AMD-S-01, AMD-S-03, NS-S-01

### AD-21
**Bound:** AMD-S-01, AMD-S-03, PERSIST-S-01, DM-S-01

### AD-22
**Bound:** AMD-S-01, AMD-S-03, LEGEND-S-01

### AD-23
**Bound:** CHC-S-01, CHC-S-03, DM-S-01, DM-S-03

### AD-24
**Bound:** GK-S-02, UL-S-02, PERSIST-S-01, DM-S-01

### AD-25
**Bound:** AUDIT-S-01, DM-S-03, DM-S-01

### AD-26
**Bound:** IEL-S-01, CHC-S-03, AMD-S-01, AMD-S-03

### AD-27
**Bound:** PERSIST-S-01, DM-S-01, GK-S-02

### AD-28
**Bound:** IEL-S-01, CHC-S-03, AMD-S-01, AMD-S-03

### AD-29
**Bound:** IEL-S-01, CHC-S-03, AMD-S-01, AMD-S-03

### AD-30
**Bound:** IEL-S-01, DM-S-01, DM-S-03

### AD-31
**Bound:** EH-S-02, CM-S-03, WILL-S-06

### AD-32
**Bound:** EH-S-02, CM-S-03, WILL-S-06

### AD-33
**Bound:** EH-S-02, IEL-S-01, CM-S-03

### AD-34
**Bound:** PERSIST-S-01, EH-S-02, DM-S-01

### AD-35
**Bound:** PERSIST-S-01, DM-S-01, GK-S-02

### AD-36
**Bound:** PERSIST-S-01, EH-S-02, DM-S-01

### AD-37
**Bound:** GK-S-02, EH-S-02, DM-S-01

### AD-38
**Bound:** PERSIST-S-01, EH-S-02, DM-S-01

### AD-39
**Bound:** GK-S-01, PERSIST-S-01, EH-S-02

### AD-40
**Bound:** EH-S-02, PERSIST-S-01, GK-S-02

### AD-41
**Bound:** GK-S-02, PERSIST-S-01, EH-S-02

### AD-42
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-43
**Bound:** DM-S-03, PERSIST-S-01, IEL-S-01

### AD-44
**Bound:** PERSIST-S-01, DM-S-03, EH-S-02

### AD-45
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-46
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-47
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-48
**Bound:** CGP-S-01, CGP-S-02, CTR-S-01

### AD-49
**Bound:** IEL-S-01, CTR-S-01

### AD-50
**Bound:** IEL-S-01, CTR-S-01

### AD-51
**Bound:** IEL-S-01, CTR-S-01

### AD-52
**Bound:** IEL-S-01, CTR-S-01

### AD-53
**Bound:** NS-S-04, NS-S-05, NS-S-06

### AD-54
**Bound:** TO-S-01

### AD-55
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-56
**Bound:** EFFECT-S-01

### AD-57
**Bound:** IEL-S-01, EFFECT-S-01

### AD-58
**Bound:** IEL-S-01, AUDIT-S-01

### AD-59
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-60
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-61
**Bound:** EFFECT-S-02, EFFECT-S-01, IEL-S-01

### AD-62
**Bound:** EFFECT-S-01, EFFECT-S-02, IEL-S-01

### AD-63
**Bound:** EFFECT-S-01, EFFECT-S-02, IEL-S-01

### AD-64
**Bound:** GK-S-02, EH-S-02, PERSIST-S-01

### AD-65
**Bound:** EFFECT-S-01, EFFECT-S-02, IEL-S-01

### AD-66
**Bound:** IEL-S-01, EFFECT-S-02

### AD-67
**Bound:** RECON-S-01, IEL-S-01, EFFECT-S-02

### AD-68
**Bound:** CGP-S-01, CGP-S-02, CGP-S-03

### AD-69
**Bound:** DCAP-S-01, CGP-S-01, CGP-S-03

### AD-70
**Bound:** DCAP-S-01, CGP-S-01, CGP-S-03

### AD-71
**Bound:** TO-S-01

### AD-72
**Bound:** TO-S-01, DEFER-S-01
