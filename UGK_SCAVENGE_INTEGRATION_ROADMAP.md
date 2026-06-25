# UGK Scavenge Integration Roadmap

Status: design roadmap, non-canonical until minted
Base repo: UGK v0.1.0 r164 working tree
Date: 2026-06-23
Purpose: record high-value improvements scavenged from Jnana, MCIR, HLIR, AOK, AI-HLIR, and legacy CARA handoffs for later canonicalization.

## Claim Boundary

This roadmap does not change UGK law, schema, legend, codex, gates, or runtime semantics.

It records candidate work for a future canonicalization lane. Each item below remains design-only until implemented, certified, and minted through the normal UGK release process.

The source window begins with `jnana_mcir_handoff_v1` and includes the later secondary Jnana/GCR/EAR handoff, HLIR feedback, AOK identity handoff, AI-HLIR handoff, and legacy CARA handoff.

## CGProj Baseline Correction

CGProj should protect continuity of accepted governed meaning, not every historical implementation detail.

Therefore a future CGProj drift-detection pass should define its normative baseline from the actual accepted UGK v0.1.0 canonical lineage/head, not from the old r9 archive by default. The r9 archive may remain historical evidence or a prior projection sample, but it should not become the protected baseline unless a specific invariant from r9 is explicitly adopted.

Rule:

```text
CGProj protects accepted governed meaning.
It does not freeze obsolete historical shape.
```

## Integration Principles

1. Keep UGK core small.
2. Add most scavenged material as profiles, conformance vectors, tools, or roadmaps.
3. Keep MCIR stable and low-level.
4. Let HLIR carry domain meaning.
5. Treat identity policy as constitutional, not formatting.
6. Preserve refusal origin across layers.
7. Never let user or engine context supply trusted governance state.
8. Do not import legacy runtimes wholesale.

## Phase 0 - Canonical Intake Discipline

Goal: turn this roadmap into a controlled canonicalization lane.

Deliverables:

- Mint this roadmap as an explicit roadmap artifact.
- Decide whether it is a standalone roadmap or folded into the existing global audit roadmap.
- Create an issue/lane map for each profile family below.
- Mark all items as design-only until implemented.

Acceptance:

- No runtime claim is made from this roadmap alone.
- Every future implementation item has a target profile/tool/gate and proof expectation.

## Phase 1 - Compiled Profile Architecture

Source insight: Jnana HLIR stack and HLIR feedback.

Doctrine:

```text
Humans author HLIR.
Systems ratify MCIR.
HLIR carries domain meaning.
MCIR carries canonical identity.
```

Deliverables:

- `UGK-HLIR-PROFILE-AUTHORING-v0`: doctrine and minimum profile language contract.
- A profile lowering contract: parser, validator, refusal codes, deterministic lowering, canonical MCIR output, reference graph, conformance vectors.
- CK profile packaging model using the SCI-like triad:
  - specification: what exists
  - configuration: what it requires
  - implementation: what realizes it

Candidate conformance vectors:

- malformed profile source refuses before lowering
- semantic validation failure refuses before MCIR admission
- same profile source lowers to identical MCIR on repeated runs
- equivalent prose-only change does not silently change canonical identity
- unknown profile declaration type refuses

## Phase 2 - CK / MCIR / GMB Identity Hardening

Source insight: AOK identity handoff.

Goal: make canonical identity explicit across bytes, encoding, serialization, hashing, host behavior, receipt paths, and implementation authority.

Deliverables:

- `UGK-UNICODE-IDENTITY-POLICY-v0`
- `UGK-BEHAVIORAL-FINGERPRINT-v0`
- `UGK-IDENTITY-SURFACE-INVENTORY-v0`
- `UGK-CANON-FALSIFICATION-v0`
- `UGK-RECEIPT-PATH-IDENTITY-v0`
- optional `UGK-CROSS-HOST-REPLAY-v0`
- optional `UGK-NATIVE-PARITY-VECTORS-v0`

Negative vector families:

- duplicate key acceptance
- NaN or infinity number acceptance
- leading-zero number acceptance
- Unicode normalization ambiguity
- locale-dependent ordering
- wrong key order acceptance
- non-UTF-8 bytes
- path separator ambiguity
- timestamp, hostname, or temp-path entropy in identity

Acceptance:

- Canonicalization proves what it refuses, not only what it accepts.
- Receipt identity excludes ambient host/path entropy.
- Existing behavior is fingerprinted before any convergence change.

## Phase 3 - MCIR / SMH / EAR / JD Profile Deepening

Source insight: Jnana MCIR, secondary Jnana/GCR/EAR handoff, CRE/MCIR review.

Goal: strengthen MCIR/SMH as bounded, inspectable, non-authoritative profile references unless explicitly integrated as authority.

Deliverables:

- `UGK-MCIR-SMH-BOUNDED-REFERENCE-v0`
- `UGK-EAR-PROFILE-v0`
- `UGK-JD-PROFILE-v0`
- `UGK-PHASE-EVIDENCE-PROTOCOL-v0`
- scope-isolation guidance for local synthesis vs downstream deployment.

Key rules:

- EAR means observable, contractable external interaction.
- JD means opaque external execution or truth custody.
- EAR and JD are distinct and may coexist at operation-phase granularity.
- Evidence readiness enables a request; it does not self-authorize schema or law changes.
- Sparse MCIRs should defer rather than fabricate TO/TH/JD fields.

Candidate vectors:

- EAR present but uncontracted is recorded, not silently treated as internal
- JD boundary cannot be downgraded to EAR by observability of result alone
- phase-level EAR+JD system preserves both classifications
- regime-only MCIR refuses normalization without evidence
- local synthesis scope does not inherit downstream cloud execution JD as primary scope

## Phase 4 - Execution Legibility And Receipt Surfaces

Source insight: Jnana FLOW-1/FLOW-2, Receipts Manager, executable graph work.

Goal: make complex governed execution paths easier to inspect without changing core semantics.

Deliverables:

- `UGK-EXECUTION-PATH-LEGIBILITY-v0`
- `UGK-RECEIPT-LINEAGE-v0`
- `ugk inspect/history` design sketch or profile tooling equivalent.

Vocabulary:

- taken
- denied
- not_reached
- not_applicable
- deferred
- blocked_by_prior_refusal

Receipt layer split:

- decision receipt: what did the gate decide?
- operation receipt: what happened as a result?
- persistence receipt: where/how was evidence stored?
- lineage binding: what capability, authority, EAR, admissibility, or profile object produced it?

Candidate vectors:

- denial at gate B preserves gate A receipt and marks later gates not_reached
- bridge/defer/refusal path renders node sequence and receipt-to-node correspondence
- receipt lineage is descriptive, not authority-bearing
- audit after closure remains readable

## Phase 5 - AI-HLIR / AOK / CARA Profile Family

Source insight: AI-HLIR handoff.

Goal: separate AI governance into knowledge, reasoning, model invocation, and developer/API surfaces.

Profile candidates:

- `UGK-WMH-v0`: governed world/knowledge artifacts
- `UGK-GEP-v0`: governed epistemic reasoning artifacts
- `UGK-MGH-v0`: governed model invocation artifacts
- `UGK-AI-API-v0`: governed developer/session surface

Rules:

- knowledge != reasoning != model invocation != developer API
- lower-layer refusal identity must be preserved through API projection
- ungrounded output may be a governed outcome
- fabricated grounding must refuse
- conflict can be an artifact, not automatic failure
- model invocation requires receipt-before-model-effect
- model/artifact type IDs require profile-local namespace or registry mapping

Candidate vectors:

- evidence missing -> refusal
- invalid predicate -> refusal
- conflict -> conflict artifact, not overwrite
- confidence exceeds evidence -> refusal
- circular inference -> refusal
- revoked model -> refusal
- prohibited use -> refusal
- receipt before model effect
- cross-session artifact reference -> refusal
- closed-session write -> refusal

## Phase 6 - CARA Anti-Laundering Harness

Source insight: legacy CARA handoff.

Goal: prevent agents, engines, or user context from smuggling governance state into trusted authority surfaces.

Profile candidates:

- `UGK-CARA-ROUTER-CONTEXT-v0`
- `UGK-CARA-CONTEXT-SANITIZATION-v0`
- `UGK-CARA-ADMISSION-EVENT-v0`
- `UGK-CARA-AUTHORITY-ANTI-LAUNDERING-v0`
- `UGK-CARA-ESCALATION-TRUST-ORIGIN-v0`
- `UGK-CARA-BUFFERED-KB-WRITE-v0`

Rules:

- router context is trusted
- user context is untrusted
- engine output is untrusted proposal
- validators decide
- promotion is an admitted event, not a gradient
- KB promotion detection comes from governed state diff, not engine-declared metadata
- pending escalation blocks commit

Candidate vectors:

- user supplies evidence/promotions/authority_refs/report_mode -> stripped and logged
- validator reads router context only
- missing required validator fails boot
- unknown authority source fails closed
- engine-declared promotion ignored
- promotion without AdmissionEvent refuses
- KB-diff promotion detected
- engine escalation not automatically trusted
- pending escalation blocks commit
- every early refusal produces trace

## Phase 7 - Tooling And Certification Support

Goal: add proof and review tools without bloating UGK core.

Deliverables:

- profile maturity tiers
- implementation authority roles
- cross-host replay harness
- native parity harness
- identity-surface inventory tool
- canonicalization falsification suite
- receipt history/lineage inspector
- CGProj baseline correction design

Maturity tiers:

- design-only
- schema-present
- conformance vectors present
- executable verifier present
- cross-host replay verified
- native parity verified
- canonical release certified

Certification discipline:

- quick lane for exploration
- canonical lane for accepted artifacts
- no profile is accepted without clear proof boundary

## Explicit Non-Imports

Do not import wholesale:

- Jnana native VM/platform stack
- legacy CARA runtime
- in-memory KB model
- AI-HLIR artifact type numbers
- r9 cgproj archive as normative baseline
- old source-tree packaging assumptions

Use them as evidence, pattern archives, or prior art only.

## Recommended First Mint Lane

Best first canonicalization package:

1. Mint this roadmap.
2. Add the CGProj baseline correction as a roadmap note, not a semantic runtime change.
3. Define `UGK-HLIR-PROFILE-AUTHORING-v0` and `UGK-CANON-FALSIFICATION-v0` as design profiles.
4. Add conformance-vector stubs for identity falsification and CARA context poisoning.
5. Defer AI-HLIR implementation until the profile namespace/MCIR type registry question is decided.

This ordering gives high leverage while keeping core stationary.
