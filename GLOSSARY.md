# UGK Glossary — generated term index

**Generated from `GLOSSARY.json`. Do not hand-edit.** This is a navigation/lookup artifact, not law: each term names where it lives, what it is, what it is not, and which source owns truth. The cited sources are authority; this index is not.

Verified against release: r165 · 36 terms · 13 categories. Authoritative projections: `ugk/codex/CODEX.md` (generated law projection), `IMPLEMENTATION_CODEX.md` (human navigation). For live unknowns: `ugk explain <id>`.

## Terms

- [ADMIT](#admit) — Operation admitted; effect permitted under receipt.
- [amendment-ledger](#amendment-ledger) — Append-only Ed25519-signed record of frame-moving amendments.
- [B1/B2/B3/B4](#b1b2b3b4) — The four behavioral-continuity legs (shape, identity, attestation, declared-surface confinement).
- [BRIDGE](#bridge) — Native opt-in permit-with-audit for an attested regime crossing.
- [BRIDGE-BINDING](#bridge-binding) — Resolver-parameterized validity rule for committed v8 BridgeRecord surfaces.
- [BridgeRecord](#bridgerecord) — Committed v8 bridge surface (source/target/transform/evidence refs) validated by BRIDGE-BINDING.
- [CK profile](#ck-profile) — Portable CK profile packaging (spec/schemas/vectors/verifier).
- [CK-CANON](#ck-canon) — Canonicalization discipline for governance input (e.g. float ban at the protocol boundary).
- [classified-remainders](#classified-remainders) — Explicitly declared governance gaps surfaced as constitutional posture.
- [ContinuationRecord](#continuationrecord) — Append-only record carrying DEFER lifecycle state.
- [CRISIS](#crisis) — Reserved terminal outcome; not emittable at this release.
- [DEFER](#defer) — Deferred outcome backed by a HELD continuation record.
- [EffectAtomicity](#effectatomicity) — Class-relative discipline for effect-bearing operations and trails.
- [EXTERNAL_IRREVERSIBLE](#external-irreversible) — Effect class: irreversible external effect via prepare/commit trail.
- [EXTERNAL_REVERSIBLE](#external-reversible) — Effect class: external effect with compensation/saga reversal.
- [generated CODEX](#generated-codex) — Deterministic constitutional projection of invariants.py; machine-owned leaf.
- [GRBSA](#grbsa) — Gate/Refusal Behavioral Substrate Adapter forest backing continuity proofs.
- [Implementation Codex](#implementation-codex) — Human-authored, source-cited, claim-ceilinged navigation map of named subsystems.
- [integrity-basis](#integrity-basis) — Trust basis is cryptographic, not file mode; packaging strips modes.
- [MCIR](#mcir) — Machine-canonical intermediate representation; bounded read-only reference, never authority.
- [MCIR structural identity](#mcir-structural-identity) — MCIR's canonical structural identity used by bridge resolvers.
- [NON_ATOMIC](#non-atomic) — Effect class: explicit transitional posture, not an atomicity claim.
- [Proof Model B](#proof-model-b) — Behavioral continuity proof model for release-to-release transitions.
- [PURE](#pure) — Effect class: no external or persistent effect.
- [REFUSE](#refuse) — Operation refused at a gate; fail-closed.
- [resolver-parameterized verification](#resolver-parameterized-verification) — Verification pattern injecting read-only resolvers (kernel-free, deterministic).
- [rho-integration-posture](#rho-integration-posture) — Temporal-PROV layer integrated add-only, dormant/opt-in, with no kernel wiring.
- [SKILL.md](#skill.md) — Short procedural agent boot/operating guide; routes to deeper docs.
- [SMH](#smh) — Evidence layer resolved read-only and non-authoritatively for bridge verification.
- [SMH archive identity](#smh-archive-identity) — Archive-level SMH identity distinct from a projection.
- [SMH projection](#smh-projection) — A projected SMH view consumed read-only by resolvers.
- [STORE_LOCAL](#store-local) — Effect class: local persistent receipt store write only.
- [STRUCTURAL_ERROR](#structural-error) — Protocol/structural fault committed as a typed terminal outcome.
- [terminal-outcome-lattice](#terminal-outcome-lattice) — Closed terminal-outcome vocabulary committed on governed receipts.
- [ugk explain](#ugk-explain) — Self-describing CLI resolving invariants, gates, and CSIL integers on demand.
- [verifier-boundary](#verifier-boundary) — Boundary defining what verification may prove vs what stays out of verifier authority.

## Category: CK concept

### CK profile
*status:* design-only · *introduced:* r165 · *last verified:* r165  

Portable CK profile packaging (spec/schemas/vectors/verifier).

- **is not:** Not an implemented package; not law.
- **agent rule:** Treat as design-only roadmap; not implemented in-tree at this release.
- **authoritative sources:** `release:r165`, `doc:UGK_SCAVENGE_INTEGRATION_ROADMAP.md`
- **surfaces:** `UGK_SCAVENGE_INTEGRATION_ROADMAP.md`
- **related:** CK-CANON, MCIR

### CK-CANON
*aliases:* CK canon  
*status:* live · *introduced:* r156 · *last verified:* r165  

Canonicalization discipline for governance input (e.g. float ban at the protocol boundary).

- **is not:** Not a serialization convenience; not optional.
- **agent rule:** Pass ints/strings/decimals, not floats; floats refuse with ProtocolError.
- **authoritative sources:** `codex:ck-canon-float-ban`, `release:r156`
- **surfaces:** `ugk/storage/store.py`
- **related:** CK profile, ck-canon-float-ban

## Category: MCIR concept

### MCIR
*status:* bounded-external · *introduced:* r161 · *last verified:* r165  

Machine-canonical intermediate representation; bounded read-only reference, never authority.

- **is not:** Not embedded runtime authority; UGK imports neither MCIR nor SMH.
- **agent rule:** Treat MCIR as representation/reference, never embedded authority.
- **authoritative sources:** `codex:mcir-smh-resolver-boundary`, `invariant:BRIDGE-BINDING`
- **surfaces:** `ugk/storage/bridge_binding.py`
- **invariants:** BRIDGE-BINDING
- **related:** SMH, BRIDGE-BINDING, resolver-parameterized verification

### MCIR structural identity
*status:* bounded-external · *introduced:* r161 · *last verified:* r165  

MCIR's canonical structural identity used by bridge resolvers.

- **is not:** Not UGK law; not embedded.
- **agent rule:** Use only via injected read-only resolver; never as authority.
- **authoritative sources:** `codex:mcir-smh-resolver-boundary`, `invariant:BRIDGE-BINDING`
- **surfaces:** `ugk/storage/bridge_binding.py`
- **invariants:** BRIDGE-BINDING
- **related:** MCIR, BRIDGE-BINDING

## Category: SMH concept

### SMH
*status:* bounded-external · *introduced:* r161 · *last verified:* r165  

Evidence layer resolved read-only and non-authoritatively for bridge verification.

- **is not:** Not embedded authority; not a UGK import.
- **agent rule:** Treat SMH evidence as read-only; never authority.
- **authoritative sources:** `codex:mcir-smh-resolver-boundary`, `invariant:BRIDGE-BINDING`
- **surfaces:** `ugk/storage/bridge_binding.py`
- **invariants:** BRIDGE-BINDING
- **related:** MCIR, BRIDGE-BINDING, SMH projection, SMH archive identity

### SMH archive identity
*status:* bounded-external · *introduced:* r161 · *last verified:* r165  

Archive-level SMH identity distinct from a projection.

- **is not:** Not a projection; not authority.
- **agent rule:** Distinguish archive identity from projection; both read-only.
- **authoritative sources:** `codex:mcir-smh-resolver-boundary`
- **surfaces:** `ugk/storage/bridge_binding.py`
- **invariants:** BRIDGE-BINDING
- **related:** SMH, SMH projection

### SMH projection
*status:* bounded-external · *introduced:* r161 · *last verified:* r165  

A projected SMH view consumed read-only by resolvers.

- **is not:** Not authoritative; not archive identity.
- **agent rule:** Treat as read-only projected evidence.
- **authoritative sources:** `codex:mcir-smh-resolver-boundary`
- **surfaces:** `ugk/storage/bridge_binding.py`
- **invariants:** BRIDGE-BINDING
- **related:** SMH, SMH archive identity

## Category: bridge concept

### BRIDGE-BINDING
*status:* live · *introduced:* r161 · *last verified:* r165  

Resolver-parameterized validity rule for committed v8 BridgeRecord surfaces.

- **is not:** Not embedded MCIR/SMH authority; not kernel-owned resolution.
- **agent rule:** Keep MCIR representation and SMH evidence read-only; resolver success is not authority.
- **authoritative sources:** `invariant:BRIDGE-BINDING`, `codex:bridge-binding`, `gate:bridge_binding_gate`
- **surfaces:** `ugk/storage/bridge_binding.py`, `ugk/conformance/bridge_binding_gate.py`
- **invariants:** BRIDGE-BINDING
- **related:** BRIDGE, BridgeRecord, resolver-parameterized verification, MCIR, SMH

### BridgeRecord
*status:* live · *introduced:* r160 · *last verified:* r165  

Committed v8 bridge surface (source/target/transform/evidence refs) validated by BRIDGE-BINDING.

- **is not:** Not embedded MCIR/SMH bodies; references only.
- **agent rule:** Require a complete, verifying surface before BRIDGE; missing fields fail closed.
- **authoritative sources:** `invariant:BRIDGE-BINDING`, `codex:native-bridge`, `gate:bridge_surface_gate`
- **surfaces:** `ugk/storage/store.py`, `ugk/storage/bridge_binding.py`, `ugk/conformance/bridge_surface_gate.py`
- **invariants:** BRIDGE-BINDING
- **related:** BRIDGE, BRIDGE-BINDING, MCIR, SMH

### resolver-parameterized verification
*status:* live · *introduced:* r161 · *last verified:* r165  

Verification pattern injecting read-only resolvers (kernel-free, deterministic).

- **is not:** Not embedded authority; not kernel-owned semantics.
- **agent rule:** Inject resolvers read-only; resolver exceptions fail closed to False.
- **authoritative sources:** `invariant:BRIDGE-BINDING`, `codex:bridge-binding`
- **surfaces:** `ugk/storage/bridge_binding.py`
- **invariants:** BRIDGE-BINDING
- **related:** BRIDGE-BINDING, MCIR, SMH

## Category: defer/continuation concept

### ContinuationRecord
*status:* live · *introduced:* r149 · *last verified:* r165  

Append-only record carrying DEFER lifecycle state.

- **is not:** Not mutable scheduling state.
- **agent rule:** Read continuation_state as later receipt markers, not mutable state.
- **authoritative sources:** `invariant:DEFER-S-01`, `codex:defer-lifecycle`, `gate:continuation_record_surface_gate`
- **surfaces:** `ugk/storage/store.py`, `ugk/conformance/continuation_record_surface_gate.py`
- **invariants:** DEFER-S-01
- **related:** DEFER, terminal-outcome-lattice

## Category: effect concept

### EffectAtomicity
*status:* live · *introduced:* r17a · *last verified:* r165  

Class-relative discipline for effect-bearing operations and trails.

- **is not:** Not a blanket reversibility guarantee.
- **agent rule:** Require a declared effect class and class-appropriate trail before asserting integrity.
- **authoritative sources:** `invariant:EFFECT-S-01`, `codex:effect-atomicity`
- **surfaces:** `ugk/kernel.py`, `ugk/integrity/external_irreversible.py`, `ugk/integrity/external_reversible.py`
- **invariants:** EFFECT-S-01
- **related:** PURE, STORE_LOCAL, EXTERNAL_REVERSIBLE, EXTERNAL_IRREVERSIBLE, NON_ATOMIC

### EXTERNAL_IRREVERSIBLE
*status:* live · *introduced:* r17a · *last verified:* r165  

Effect class: irreversible external effect via prepare/commit trail.

- **is not:** Not reversible; no rollback claim.
- **agent rule:** Track by truthful prepare/commit trail; orphan PREPARE and TerminalWriteExhausted signal exhaustion, not receipt.
- **authoritative sources:** `invariant:EFFECT-S-01`, `codex:effect-atomicity`
- **surfaces:** `ugk/integrity/external_irreversible.py`
- **invariants:** EFFECT-S-01
- **related:** EffectAtomicity, EXTERNAL_REVERSIBLE

### EXTERNAL_REVERSIBLE
*status:* live · *introduced:* r17a · *last verified:* r165  

Effect class: external effect with compensation/saga reversal.

- **is not:** Not EXTERNAL_IRREVERSIBLE.
- **agent rule:** Provide forward+compensation; reversal is by compensation, not rollback claim.
- **authoritative sources:** `invariant:EFFECT-S-01`, `codex:effect-atomicity`, `gate:external_reversible_gate`
- **surfaces:** `ugk/integrity/external_reversible.py`, `ugk/conformance/external_reversible_gate.py`
- **invariants:** EFFECT-S-01
- **related:** EffectAtomicity, EXTERNAL_IRREVERSIBLE

### NON_ATOMIC
*status:* posture · *introduced:* r17a · *last verified:* r165  

Effect class: explicit transitional posture, not an atomicity claim.

- **is not:** Not an atomicity guarantee.
- **agent rule:** Read NON_ATOMIC as an honest gap declaration, not a guarantee.
- **authoritative sources:** `invariant:EFFECT-S-01`, `codex:effect-atomicity`
- **surfaces:** `ugk/kernel.py`
- **invariants:** EFFECT-S-01
- **related:** EffectAtomicity, classified-remainders

### PURE
*status:* live · *introduced:* r17a · *last verified:* r165  

Effect class: no external or persistent effect.

- **is not:** Not STORE_LOCAL; not external.
- **agent rule:** Use PURE only when nothing is persisted or externalized.
- **authoritative sources:** `invariant:EFFECT-S-01`, `codex:effect-atomicity`
- **surfaces:** `ugk/kernel.py`
- **invariants:** EFFECT-S-01
- **related:** EffectAtomicity

### STORE_LOCAL
*status:* live · *introduced:* r17a · *last verified:* r165  

Effect class: local persistent receipt store write only.

- **is not:** Not an external effect.
- **agent rule:** Use for local-store writes with no external effect.
- **authoritative sources:** `invariant:EFFECT-S-01`, `codex:effect-atomicity`
- **surfaces:** `ugk/storage/store.py`
- **invariants:** EFFECT-S-01
- **related:** EffectAtomicity

## Category: generated artifact

### generated CODEX
*aliases:* CODEX.md  
*status:* generated · *introduced:* r17a · *last verified:* r165  

Deterministic constitutional projection of invariants.py; machine-owned leaf.

- **is not:** Not narrative doctrine; not the human navigation map.
- **agent rule:** Never hand-edit; it is generated and gate-pinned (and truncates statements).
- **authoritative sources:** `file:ugk/codex/CODEX.md`, `codex:generated-codex-boundary`, `gate:codex_freshness_gate`
- **surfaces:** `ugk/codex/CODEX.md`, `codex_gen.py`, `ugk/conformance/codex_freshness_gate.py`
- **related:** Implementation Codex, integrity-basis

## Category: human-authored navigation artifact

### Implementation Codex
*aliases:* IMPLEMENTATION_CODEX.md  
*status:* live · *introduced:* r165 · *last verified:* r165  

Human-authored, source-cited, claim-ceilinged navigation map of named subsystems.

- **is not:** Not law; not the generated CODEX; not a second source of truth.
- **agent rule:** Use concept entries to navigate; obey each entry's claim_ceiling.
- **authoritative sources:** `file:IMPLEMENTATION_CODEX.md`, `gate:implementation_codex_freshness_gate`
- **surfaces:** `IMPLEMENTATION_CODEX.md`, `ugk/implementation_codex.py`, `ugk/conformance/implementation_codex_freshness_gate.py`
- **related:** generated CODEX, SKILL.md, GLOSSARY.md

### SKILL.md
*status:* live · *introduced:* r17a · *last verified:* r165  

Short procedural agent boot/operating guide; routes to deeper docs.

- **is not:** Not a theory document; not a complete substrate map.
- **agent rule:** Use for boot + routing; follow its pointers for depth.
- **authoritative sources:** `file:SKILL.md`
- **surfaces:** `SKILL.md`
- **related:** Implementation Codex, GLOSSARY.md, ugk explain

## Category: integrity concept

### classified-remainders
*status:* posture · *introduced:* r17a · *last verified:* r165  

Explicitly declared governance gaps surfaced as constitutional posture.

- **is not:** Not a defect list to silently ignore; not a guarantee of completeness.
- **agent rule:** Treat as honest gap declarations that bound scope claims.
- **authoritative sources:** `codex:classified-remainders`, `file:ugk/__init__.py`
- **surfaces:** `ugk/__init__.py`, `ugk/conformance/classified_remainders_gate.py`
- **related:** NON_ATOMIC, verifier-boundary

### integrity-basis
*status:* live · *introduced:* r17a · *last verified:* r165  

Trust basis is cryptographic, not file mode; packaging strips modes.

- **is not:** File mode is not the trust basis.
- **agent rule:** Verify by hash + verify_release.py, not on-disk permissions.
- **authoritative sources:** `doc:INTEGRITY_BASIS.md`, `codex:integrity-basis`
- **surfaces:** `INTEGRITY_BASIS.md`
- **related:** grundnorm-layer, release-certification-stack

## Category: release/continuity concept

### amendment-ledger
*status:* live · *introduced:* r17a · *last verified:* r165  

Append-only Ed25519-signed record of frame-moving amendments.

- **is not:** Constitutional history, not constitutional law; not a mutable changelog.
- **agent rule:** Treat law/schema/legend moves as amendment-governed unless proven frame-stationary.
- **authoritative sources:** `invariant:AMD-S-03`, `codex:amendment-ledger`, `gate:amendment_admissibility_gate`
- **surfaces:** `ugk/amendment.py`, `ugk/amendment_ledger.json`, `ugk/conformance/amendment_admissibility_gate.py`
- **invariants:** AMD-S-01, AMD-S-02, AMD-S-03
- **related:** Proof Model B, release-certification-stack

### B1/B2/B3/B4
*status:* live · *introduced:* r135 · *last verified:* r165  

The four behavioral-continuity legs (shape, identity, attestation, declared-surface confinement).

- **is not:** Not byte-identity (that is a demoted shortcut clause).
- **agent rule:** B4 confines the declared surface; a real undeclared diff must fail B4.
- **authoritative sources:** `doc:ROADMAP_G6.md`, `codex:proof-model-b`
- **surfaces:** `tools/grbsa/proof_model_b.py`
- **related:** Proof Model B, GRBSA

### Proof Model B
*aliases:* ContinuityB, behavioral continuity  
*status:* live · *introduced:* r135 · *last verified:* r165  

Behavioral continuity proof model for release-to-release transitions.

- **is not:** Not runtime law; not a substitute for conformance gates.
- **agent rule:** Use it to bound continuity claims, especially B4 declared-surface drift.
- **authoritative sources:** `doc:ROADMAP_G6.md`, `codex:proof-model-b`
- **surfaces:** `tools/grbsa/proof_model_b.py`, `tools/grbsa/g6_aggregate_validation_gate.py`
- **related:** B1/B2/B3/B4, GRBSA, amendment-ledger

## Category: rho concept

### rho-integration-posture
*aliases:* rho  
*status:* dormant · *introduced:* r17a · *last verified:* r165  

Temporal-PROV layer integrated add-only, dormant/opt-in, with no kernel wiring.

- **is not:** Not active; not kernel-wired; not authority.
- **agent rule:** Treat rho as present but dormant; do not assume it is wired into the kernel.
- **authoritative sources:** `codex:rho-integration-posture`, `file:ugk/rho_hardened.py`
- **surfaces:** `ugk/rho_hardened.py`, `ugk/conformance/rho_fixtures.py`
- **related:** classified-remainders, integrity-basis

## Category: terminal outcome

### ADMIT
*status:* live · *introduced:* r17a · *last verified:* r165  

Operation admitted; effect permitted under receipt.

- **is not:** Not an unconditional success flag.
- **agent rule:** Read ADMIT as permit-with-receipt, not silent success.
- **authoritative sources:** `invariant:TO-S-01`, `codex:terminal-outcome-lattice`
- **surfaces:** `ugk/fga/terminal_outcome.py`
- **invariants:** TO-S-01
- **related:** terminal-outcome-lattice, REFUSE

### BRIDGE
*status:* live · *introduced:* r162 · *last verified:* r165  

Native opt-in permit-with-audit for an attested regime crossing.

- **is not:** Not spontaneous; the kernel never auto-bridges.
- **agent rule:** Claim BRIDGE only via explicit emit_bridge with valid BRIDGE-BINDING at emit.
- **authoritative sources:** `invariant:TO-S-01`, `invariant:BRIDGE-BINDING`, `codex:native-bridge`, `gate:bridge_emission_gate`
- **surfaces:** `ugk/kernel.py`, `ugk/storage/store.py`, `ugk/conformance/bridge_emission_gate.py`
- **invariants:** TO-S-01, BRIDGE-BINDING
- **related:** BRIDGE-BINDING, BridgeRecord, terminal-outcome-lattice

### CRISIS
*status:* reserved · *introduced:* r17a · *last verified:* r165  

Reserved terminal outcome; not emittable at this release.

- **is not:** Not a live outcome; not emittable.
- **agent rule:** Treat CRISIS as reserved/non-emittable; do not claim it is live.
- **authoritative sources:** `invariant:TO-S-01`, `codex:terminal-outcome-lattice`
- **surfaces:** `ugk/fga/terminal_outcome.py`
- **invariants:** TO-S-01
- **related:** terminal-outcome-lattice

### DEFER
*aliases:* deferral  
*status:* live · *introduced:* r149 · *last verified:* r165  

Deferred outcome backed by a HELD continuation record.

- **is not:** Not scheduling and not a stored-decision replay.
- **agent rule:** Emit DEFER only with a valid HELD continuation; resume re-enters execute().
- **authoritative sources:** `invariant:DEFER-S-01`, `invariant:TO-S-01`, `codex:defer-lifecycle`
- **surfaces:** `ugk/kernel.py`, `ugk/storage/store.py`, `ugk/conformance/defer_lifecycle_gate.py`
- **invariants:** DEFER-S-01, TO-S-01
- **related:** DEFER, ContinuationRecord, terminal-outcome-lattice

### REFUSE
*status:* live · *introduced:* r17a · *last verified:* r165  

Operation refused at a gate; fail-closed.

- **is not:** Not an exception/crash; not locality-refuse by itself.
- **agent rule:** Treat REFUSE as a governed outcome with a reason, not an error to retry blindly.
- **authoritative sources:** `invariant:TO-S-01`, `gate:refusal_gate`
- **surfaces:** `ugk/fga/terminal_outcome.py`, `ugk/conformance/refusal_gate.py`
- **invariants:** TO-S-01
- **related:** terminal-outcome-lattice, STRUCTURAL_ERROR

### STRUCTURAL_ERROR
*status:* live · *introduced:* r17a · *last verified:* r165  

Protocol/structural fault committed as a typed terminal outcome.

- **is not:** Not a refusal and not a normal exception.
- **agent rule:** Distinguish STRUCTURAL_ERROR (protocol fault) from REFUSE (gate decision).
- **authoritative sources:** `invariant:TO-S-01`, `gate:structural_error_receipt_gate`
- **surfaces:** `ugk/fga/terminal_outcome.py`, `ugk/conformance/structural_error_receipt_gate.py`
- **invariants:** TO-S-01
- **related:** terminal-outcome-lattice, REFUSE

### terminal-outcome-lattice
*status:* live · *introduced:* r149 · *last verified:* r165  

Closed terminal-outcome vocabulary committed on governed receipts.

- **is not:** Not a free-form status string.
- **agent rule:** Treat the outcome set as closed; never invent an outcome.
- **authoritative sources:** `invariant:TO-S-01`, `codex:terminal-outcome-lattice`
- **surfaces:** `ugk/fga/terminal_outcome.py`, `ugk/storage/store.py`
- **invariants:** TO-S-01
- **related:** ADMIT, REFUSE, STRUCTURAL_ERROR, DEFER, BRIDGE, CRISIS

## Category: verifier concept

### GRBSA
*status:* live · *introduced:* r135 · *last verified:* r165  

Gate/Refusal Behavioral Substrate Adapter forest backing continuity proofs.

- **is not:** Not the runtime kernel; not authority.
- **agent rule:** Read GRBSA gate output as bounded behavioral proof, not global correctness.
- **authoritative sources:** `doc:ROADMAP_G6.md`, `gate:g6_aggregate_validation_gate`
- **surfaces:** `tools/grbsa/`
- **related:** Proof Model B, verifier-boundary

### ugk explain
*status:* live · *introduced:* r17a · *last verified:* r165  

Self-describing CLI resolving invariants, gates, and CSIL integers on demand.

- **is not:** Not a doc generator; not authority — it reports from source.
- **agent rule:** For any unknown invariant/gate/CSIL integer, run `ugk explain <id>`.
- **authoritative sources:** `file:ugk/cli.py`
- **surfaces:** `ugk/cli.py`
- **related:** SKILL.md, Implementation Codex, GLOSSARY.md

### verifier-boundary
*status:* live · *introduced:* r135 · *last verified:* r165  

Boundary defining what verification may prove vs what stays out of verifier authority.

- **is not:** Not a grant of runtime authority to tooling.
- **agent rule:** Phrase verifier results as bounded proofs, not production readiness.
- **authoritative sources:** `doc:VERIFIER_BOUNDARY.md`, `codex:verifier-boundary`
- **surfaces:** `VERIFIER_BOUNDARY.md`, `tools/grbsa/verifier.py`, `tools/release/certify_release.py`
- **related:** GRBSA, release-certification-stack

