# UGK Implementation Codex

Status: human-authored implementation navigation.

This file is a bounded orientation map for agents and maintainers working in the UGK source tree. It is not law, not the invariant registry, not an ADR replacement, not a generated constitutional projection, and not a schema surface. The normative/generated constitutional projection remains `ugk/codex/CODEX.md`; this file only names where implementation concepts live and how high a claim an agent may make from the cited surfaces.

Each concept entry is a JSON block so `implementation_codex_freshness_gate` can verify required fields, source references, implementation surfaces, core coverage, and release freshness.

## terminal-outcome-lattice

```json
{"concept_id":"terminal-outcome-lattice","concept_name":"Terminal Outcome Lattice","status":"live","role_in_substrate":"Closed terminal-outcome vocabulary and commitment path for governed receipts.","what_it_is_not":"Not a free-form status field and not an authority decision by itself.","instantiates":"closed outcome vocabulary for W/G/E receipts","source_refs":["invariant:TO-S-01","release:r165"],"implementation_surfaces":["ugk/fga/terminal_outcome.py","ugk/storage/store.py","ugk/conformance/terminal_outcome_gate.py","ugk/conformance/terminal_outcome_commit_gate.py"],"related":["defer-lifecycle","native-bridge","three-disjunct-receipt"],"agent_operational_rule":"Never claim a new terminal outcome unless TO-S-01 and the store/gate path establish it.","common_failure_mode":"Treating an observed string as emittable without the committed outcome path.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May identify live/reserved terminal outcomes and their committed surfaces; may not extend the lattice."}
```

## defer-lifecycle

```json
{"concept_id":"defer-lifecycle","concept_name":"DEFER Continuation Lifecycle","status":"live","role_in_substrate":"Append-only continuation lifecycle for held, resumed, resolved, expired, or refused deferred operations.","what_it_is_not":"Not a bypass around execute() and not wall-clock scheduling.","instantiates":"continuation record lifecycle under committed evidence","source_refs":["invariant:DEFER-S-01","invariant:TO-S-01","release:r165"],"implementation_surfaces":["ugk/kernel.py","ugk/storage/store.py","ugk/conformance/defer_lifecycle_gate.py","ugk/conformance/continuation_record_surface_gate.py"],"related":["terminal-outcome-lattice","three-disjunct-receipt"],"agent_operational_rule":"Treat resume as re-entry through execute(), never as replay of a stored decision.","common_failure_mode":"Reading continuation_state as mutable state instead of later receipt markers.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe the certified lifecycle and support surface; may not claim CRISIS or new expiry bases."}
```

## native-bridge

```json
{"concept_id":"native-bridge","concept_name":"Native BRIDGE Outcome","status":"live","role_in_substrate":"Opt-in native BRIDGE emission path gated by committed bridge surface verification.","what_it_is_not":"Not spontaneous bridging and not an implicit semantic conversion.","instantiates":"explicit bridge terminal path","source_refs":["invariant:TO-S-01","invariant:BRIDGE-BINDING","release:r165"],"implementation_surfaces":["ugk/kernel.py","ugk/storage/store.py","ugk/conformance/bridge_emission_gate.py","ugk/conformance/bridge_surface_gate.py"],"related":["bridge-binding","terminal-outcome-lattice","mcir-smh-resolver-boundary"],"agent_operational_rule":"Only describe BRIDGE as live through explicit kernel emit_bridge with valid BRIDGE-BINDING at emit time.","common_failure_mode":"Assuming structural divergence automatically emits BRIDGE.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May claim native BRIDGE exists under its gate; may not claim autonomous bridge synthesis."}
```

## bridge-binding

```json
{"concept_id":"bridge-binding","concept_name":"BRIDGE-BINDING Verification Boundary","status":"live","role_in_substrate":"Resolver-parameterized validity rule for committed v8 BridgeRecord surfaces.","what_it_is_not":"Not embedded MCIR/SMH authority and not kernel-owned semantic resolution.","instantiates":"bridge surface integrity rule","source_refs":["invariant:BRIDGE-BINDING","release:r165"],"implementation_surfaces":["ugk/storage/bridge_binding.py","ugk/conformance/bridge_binding_gate.py","ugk/conformance/bridge_surface_gate.py"],"related":["native-bridge","mcir-smh-resolver-boundary"],"agent_operational_rule":"Keep MCIR representation and SMH resolution read-only evidence, never authority.","common_failure_mode":"Importing external artifact bodies or treating resolver success as governance authority.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May claim committed bridge-surface validation; may not claim embedded external semantics."}
```

## effect-atomicity

```json
{"concept_id":"effect-atomicity","concept_name":"Effect Atomicity","status":"live","role_in_substrate":"Class-relative discipline for effect-bearing operations and receipt trails.","what_it_is_not":"Not a blanket guarantee that all external effects are reversible.","instantiates":"IEL effect discipline","source_refs":["invariant:EFFECT-S-01","release:r165"],"implementation_surfaces":["ugk/integrity/external_irreversible.py","ugk/integrity/external_reversible.py","ugk/conformance/effect_atomicity_declaration_gate.py","ugk/conformance/effect_trail_integrity_gate.py"],"related":["wge-reactor","three-disjunct-receipt"],"agent_operational_rule":"Require declared effect class and class-appropriate trail before asserting integrity.","common_failure_mode":"Collapsing PURE, STORE_LOCAL, EXTERNAL_REVERSIBLE, and EXTERNAL_IRREVERSIBLE into one safety story.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe certified class-relative behavior; may not certify arbitrary integrations."}
```

## amendment-ledger

```json
{"concept_id":"amendment-ledger","concept_name":"Amendment Ledger","status":"live","role_in_substrate":"Append-only record of frame-moving constitutional amendments and successor hashes.","what_it_is_not":"Not a mutable changelog and not a substitute for release certification.","instantiates":"constitutional frame succession evidence","source_refs":["invariant:AMD-S-03","release:r165"],"implementation_surfaces":["ugk/amendment.py","ugk/amendment_ledger.json","ugk/conformance/amendment_model_gate.py","ugk/conformance/amendment_admissibility_gate.py"],"related":["proof-model-b","release-certification-stack"],"agent_operational_rule":"Treat law/schema/legend moves as amendment-governed unless explicitly proven frame-stationary.","common_failure_mode":"Calling a release docs-only while quietly moving a frame leg.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May cite ledger-backed frame succession; may not infer unrecorded amendments."}
```

## proof-model-b

```json
{"concept_id":"proof-model-b","concept_name":"Proof Model B","status":"live","role_in_substrate":"Continuity proof model for release-to-release declared surface and frame transition checks.","what_it_is_not":"Not runtime law and not a replacement for conformance gates.","instantiates":"GRBSA continuity proof discipline","source_refs":["doc:ROADMAP_G6.md","release:r165"],"implementation_surfaces":["tools/grbsa/proof_model_b.py","tools/grbsa/verifier.py","tools/grbsa/g6_aggregate_validation_gate.py"],"related":["amendment-ledger","release-certification-stack"],"agent_operational_rule":"Use it to bound continuity claims, especially B4 declared-surface drift.","common_failure_mode":"Treating a passed runtime suite as release continuity proof.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May speak to certified archive continuity; may not certify live runtime behavior alone."}
```

## verifier-boundary

```json
{"concept_id":"verifier-boundary","concept_name":"Verifier Boundary","status":"live","role_in_substrate":"Defines what verification tools may prove and what remains outside verifier authority.","what_it_is_not":"Not a grant of runtime authority to verifier tooling.","instantiates":"bounded verification posture","source_refs":["doc:VERIFIER_BOUNDARY.md","release:r165"],"implementation_surfaces":["VERIFIER_BOUNDARY.md","tools/grbsa/verifier.py","tools/release/certify_release.py"],"related":["release-certification-stack","proof-model-b"],"agent_operational_rule":"Phrase verifier results as bounded proofs, not global correctness.","common_failure_mode":"Overclaiming from a passing verifier into production readiness.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May summarize verifier scope; may not assert untested operational guarantees."}
```

## classified-remainders

```json
{"concept_id":"classified-remainders","concept_name":"Classified Remainders","status":"live","role_in_substrate":"Tracks explicitly classified non-realized or deferred residue so gaps are named.","what_it_is_not":"Not completion and not a permission to ignore deferred work.","instantiates":"gap classification discipline","source_refs":["invariant:AUDIT-S-02","release:r165"],"implementation_surfaces":["ugk/conformance/classified_remainders_gate.py","ugk/invariants.py","ugk/codex/CODEX.md"],"related":["generated-codex-boundary","release-certification-stack"],"agent_operational_rule":"When work is deferred, name the class and proof boundary instead of implying closure.","common_failure_mode":"Letting design residue masquerade as implemented substrate.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May identify classified residues; may not clear them without implementation proof."}
```

## compliance-posture-scalar

```json
{"concept_id":"compliance-posture-scalar","concept_name":"Compliance Posture Scalar","status":"live","role_in_substrate":"Computable posture surfaces for governance/enabler orientation claims.","what_it_is_not":"Not a moral score and not ambient authority.","instantiates":"audit-visible posture measurement","source_refs":["invariant:ALT-I-04","invariant:CGP-S-01","release:r165"],"implementation_surfaces":["ugk/cgp/posture.py","ugk/governance/posture.py","ugk/conformance/alt_instance_gate.py","ugk/conformance/posture_gate.py"],"related":["classified-remainders","release-certification-stack"],"agent_operational_rule":"Report posture as a computable claim over declared surfaces, not as broad compliance certification.","common_failure_mode":"Converting a posture metric into a universal pass/fail claim.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe phi/posture computation; may not certify real-world legal compliance."}
```

## epoch-seal-semantics

```json
{"concept_id":"epoch-seal-semantics","concept_name":"Epoch Seal Semantics","status":"live","role_in_substrate":"Atomic seal/prune behavior for epoch lifecycle integrity.","what_it_is_not":"Not arbitrary compaction and not lossy history deletion.","instantiates":"IEL atomic destructive-path discipline","source_refs":["invariant:IEL-S-01","release:r165"],"implementation_surfaces":["ugk/kernel.py","ugk/conformance/seal_and_prune_atomicity_gate.py","ugk/integrity/transaction.py"],"related":["effect-atomicity","integrity-basis"],"agent_operational_rule":"Treat seal/prune as an atomic governed transition with receipt discipline.","common_failure_mode":"Describing pruning as a storage cleanup independent of governance.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May cite the certified atomicity gate; may not claim every archive policy is validated."}
```

## rho-integration-posture

```json
{"concept_id":"rho-integration-posture","concept_name":"Rho Integration Posture","status":"dormant","role_in_substrate":"Hardening posture fixtures and boundary language for rho-adjacent integration.","what_it_is_not":"Not a live authority substrate and not a completed external integration.","instantiates":"bounded integration posture","source_refs":["doc:INTEGRITY_BASIS.md","release:r165"],"implementation_surfaces":["ugk/rho_hardened.py","ugk/conformance/rho_fixtures.py","INTEGRITY_BASIS.md"],"related":["integrity-basis","verifier-boundary"],"agent_operational_rule":"Describe rho as bounded posture/support unless an integration path is separately certified.","common_failure_mode":"Promoting a hardening fixture into a production dependency claim.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May identify rho hardening surfaces; may not claim full rho runtime integration."}
```

## mcir-smh-resolver-boundary

```json
{"concept_id":"mcir-smh-resolver-boundary","concept_name":"MCIR/SMH Resolver Boundary","status":"bounded-external","role_in_substrate":"Keeps MCIR representation and SMH resolution as read-only evidence around bridge checks.","what_it_is_not":"Not authority, not embedded artifact storage, and not a UGK-owned semantic universe.","instantiates":"external representation/resolution boundary","source_refs":["invariant:BRIDGE-BINDING","doc:UGK_SCAVENGE_INTEGRATION_ROADMAP.md","release:r165"],"implementation_surfaces":["tools/smh/ck_canon.py","tools/smh/smh_projection_registry.py","ugk/conformance/csh_mcir_gate.py","ugk/storage/bridge_binding.py"],"related":["bridge-binding","native-bridge","ck-canon-float-ban"],"agent_operational_rule":"Keep refs and hashes committed; keep bodies external; keep authority in UGK.","common_failure_mode":"Letting semantic resolution become an admissibility authority without a law lane.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe current boundary and roadmap adjacency; may not claim MCIR/SMH profile completion."}
```

## generated-codex-boundary

```json
{"concept_id":"generated-codex-boundary","concept_name":"Generated CODEX Boundary","status":"live","role_in_substrate":"Separates generated constitutional projection from human navigation docs.","what_it_is_not":"Not this file and not a hand-edited orientation map.","instantiates":"generated projection freshness discipline","source_refs":["doc:ugk/codex/CODEX.md","release:r165"],"implementation_surfaces":["ugk/codex/CODEX.md","ugk/codex/CODEX_HASH.txt","codex_gen.py","ugk/conformance/codex_freshness_gate.py"],"related":["classified-remainders","ck-canon-float-ban"],"agent_operational_rule":"Never hand-edit generated CODEX claims through IMPLEMENTATION_CODEX.md.","common_failure_mode":"Using a human map to overwrite generated law projection.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May explain boundary; may not restate generated CODEX as source law."}
```

## release-certification-stack

```json
{"concept_id":"release-certification-stack","concept_name":"Release Certification Stack","status":"live","role_in_substrate":"Coordinates verify, conformance, archive certification, GRBSA, and continuity checks.","what_it_is_not":"Not a single command guarantee and not a production deployment audit.","instantiates":"release proof bundle discipline","source_refs":["doc:RELEASE.txt","release:r165"],"implementation_surfaces":["verify_release.py","verify_release.sh","tools/release/certify_release.py","ugk/conformance/run_gates_batch.py"],"related":["proof-model-b","verifier-boundary","amendment-ledger"],"agent_operational_rule":"Report which layer passed: verify_release, gates, quick cert, bundle cert, or G6.","common_failure_mode":"Saying 'certified' without naming the phase and archive boundary.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May summarize local certification surfaces; may not claim unrun phases passed."}
```

## grundnorm-layer

```json
{"concept_id":"grundnorm-layer","concept_name":"Grundnorm Layer","status":"live","role_in_substrate":"Read-only constitutional root posture and founding constraints.","what_it_is_not":"Not mutable configuration and not deployer convenience state.","instantiates":"constitutional root read-only discipline","source_refs":["invariant:GK-S-01","release:r165"],"implementation_surfaces":["ugk/conformance/grundnorm_readonly_gate.py","ugk/conformance/governor_key_unset_gate.py","ugk/invariants.py"],"related":["integrity-basis","amendment-ledger"],"agent_operational_rule":"Treat founding-root changes as constitutional events, not local setup tweaks.","common_failure_mode":"Mutating root posture to satisfy a test or convenience path.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May cite read-only root gates; may not authorize root mutation."}
```

## integrity-basis

```json
{"concept_id":"integrity-basis","concept_name":"Integrity Basis","status":"live","role_in_substrate":"Shared integrity and transaction primitives behind IEL safety claims.","what_it_is_not":"Not a claim that every external system is integrity-preserving.","instantiates":"IEL substrate support","source_refs":["doc:INTEGRITY_BASIS.md","invariant:IEL-S-01","release:r165"],"implementation_surfaces":["INTEGRITY_BASIS.md","ugk/integrity/validation.py","ugk/integrity/transaction.py","ugk/conformance/receipt_commitment_integrity_gate.py"],"related":["effect-atomicity","epoch-seal-semantics","rho-integration-posture"],"agent_operational_rule":"Anchor integrity claims to a specific transaction, receipt, or validation surface.","common_failure_mode":"Using 'integrity' as a broad unstated guarantee.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe certified integrity primitives; may not extend them to uncertified adapters."}
```

## ck-canon-float-ban

```json
{"concept_id":"ck-canon-float-ban","concept_name":"CK Canon Float Ban","status":"design-only","role_in_substrate":"Roadmapped rule that CK canonicalization should avoid floating-point ambiguity.","what_it_is_not":"Not current runtime law and not a completed CK profile packaging claim.","instantiates":"future CK profile canonicalization guardrail","source_refs":["doc:UGK_SCAVENGE_INTEGRATION_ROADMAP.md","release:r165"],"implementation_surfaces":["tools/smh/ck_canon.py","UGK_SCAVENGE_INTEGRATION_ROADMAP.md"],"related":["mcir-smh-resolver-boundary","generated-codex-boundary"],"agent_operational_rule":"Treat as roadmap guidance until a CK profile lane mints tests and profile artifacts.","common_failure_mode":"Claiming CK canonicalization is fully packaged from a design note.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May identify a design guardrail; may not claim implementation completeness."}
```

## wge-reactor

```json
{"concept_id":"wge-reactor","concept_name":"W/G/E Reactor","status":"live","role_in_substrate":"Kernel transition path across warrant, governance, and effect receipt formation.","what_it_is_not":"Not a generic task runner and not bypassable by lifecycle helpers.","instantiates":"governed transition execution path","source_refs":["invariant:CTR-S-01","release:r165"],"implementation_surfaces":["ugk/kernel.py","ugk/storage/store.py","ugk/conformance/admission_gate.py","ugk/conformance/choke_point_gate.py"],"related":["effect-atomicity","three-disjunct-receipt","defer-lifecycle"],"agent_operational_rule":"Route execution claims through execute() and its receipts unless a method is explicitly proved as a governed wrapper.","common_failure_mode":"Calling helper methods governance-equivalent without receipt proof.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe the certified execution path; may not certify arbitrary caller workflows."}
```

## three-tier-jurisdiction

```json
{"concept_id":"three-tier-jurisdiction","concept_name":"Three-Tier Jurisdiction","status":"live","role_in_substrate":"Jurisdiction tiering and fail-closed routing discipline for governed operations.","what_it_is_not":"Not an ambient namespace and not an external legal jurisdiction model.","instantiates":"jurisdiction routing boundary","source_refs":["invariant:CM-OP-01","release:r165"],"implementation_surfaces":["ugk/conformance/three_tier_jurisdiction_gate.py","ugk/decision.py","docs/papers/cryptographic-admissibility-and-jurisdiction.md"],"related":["wge-reactor","bridge-binding","compliance-posture-scalar"],"agent_operational_rule":"State the UGK jurisdiction tier involved before claiming an operation is in scope.","common_failure_mode":"Conflating UGK jurisdiction labels with real-world legal authority.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe UGK internal jurisdiction behavior; may not claim external legal effect."}
```

## three-disjunct-receipt

```json
{"concept_id":"three-disjunct-receipt","concept_name":"Three-Disjunct Receipt","status":"live","role_in_substrate":"Receipt outcome discipline separating admit, refuse, and structural-error paths.","what_it_is_not":"Not a four-way freeform result and not a silent exception policy.","instantiates":"closed receipt/refusal/error disjunction","source_refs":["invariant:TO-S-01","release:r165"],"implementation_surfaces":["ugk/storage/store.py","ugk/conformance/refusal_gate.py","ugk/conformance/structural_error_receipt_gate.py","ugk/conformance/body_integrity_gate.py"],"related":["terminal-outcome-lattice","wge-reactor","effect-atomicity"],"agent_operational_rule":"Name which receipt disjunct was produced and cite its committed body surface.","common_failure_mode":"Treating protocol errors, refusals, and admitted outcomes as equivalent failures.","freshness_owner":"release-lane author","last_verified_release":"r171","claim_ceiling":"May describe current receipt disjuncts and body commitments; may not invent extra result classes."}
```
