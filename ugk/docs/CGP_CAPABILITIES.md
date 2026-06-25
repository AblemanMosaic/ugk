# CGP Capabilities — ESA Family Registry

**Audience.** Developers building on UGK who need to discover which
CGP-ESA capabilities exist, how their consumer realizes each one, and
what evidence each capability requires. This document is the
human-readable companion to `ugk.cgp.esa.REGISTRY` (the
machine-checkable counterpart at `ugk/cgp/esa/registry.py`).

**Substrate stability statement.** The CGP-ESA registry is purely
additive over the UGK substrate. The **M2.3** constitutional baseline
(`invariants.py`, `law_hash = 546a9e90fd780dec…`, the 78-gate suite,
the 39-vector suite) is unchanged. No new error codes, no new gates,
no new vectors.

> **CGP integration note (corrected; doc-only).** The "additive / unchanged" statement above describes the
> **CGP-ESA capability registry** as an additive *catalog* over the **M2.3** baseline CGP was authored
> against. **CGP as a subsystem is, however, constitutionally INTEGRATED into the current r123 frame:** the
> invariants `CGP-S-01/02/03`, `SCOPE-S-01/02`, `ESA-S-01`, `CTR-S-01/07`, `SRSA-S-01` and the CGP-family
> conformance gates (`esa_selfcheck`, `posture`, `provenance_scope`, `scope_archive`, `srsa_vector`,
> `health_surface`) are part of the certified r125 frame (`law_hash a3992e45...`, 100 gates). CGP adds **no
> UGK-substrate error codes and no receipt-schema columns**, but it is **not** "purely additive over an
> unchanged baseline" — it carries its own constitutional invariants and gates. "No new gates / no new
> constitutional declarations" held only at the M2.3 line, not at the r123 frame.

For orientation on the CGP execution substrate (HeadlessRunner / CTR /
SRSA / how to run UGK headlessly), see
[`CGP_EXECUTION_SUBSTRATE.md`](./CGP_EXECUTION_SUBSTRATE.md).

---

## §1. What CGP-ESA is

**CGP-ESA — the Constitutional Governance Platform's Evidence
Specification Architecture capability family.** ESA is one of several
construct families under CGP (alongside EVS, CTR, SRSA, AIS, COP);
this document catalogs the ESA family specifically.

**Ownership statement.** The ESA capability family is part of the
Constitutional Governance Platform (CGP). Capabilities in this family
are owned by CGP and may be realized by any CGP consumer (UGK,
AbleTools, Semantic Navigator, CPVM, future). Semantic Navigator was
the empirical test bed during the framework's formative phases; it
remains a reference realization for many ESA capabilities but is not
their owner. UGK substrate provides the kernel-native ESA subset
(`ugk.core.esa`) plus the CGP execution substrate (`ugk.cgp.runner` /
`ugk.cgp.ctr` / `ugk.cgp.srsa`) through which evidence for ESA
capabilities is produced.

## §2. Ontology recap

Three orthogonal dimensions govern every CGP-ESA entry:

| Dimension | Lives in | Owner |
|---|---|---|
| **Capability** — the abstract property being claimed | The CGP-ESA registry | CGP |
| **Realization** — concrete implementation that makes the capability true for a particular system | Consumer source | Consumer (UGK / AbleTools / Navigator / CPVM / future) |
| **Evidence** — proof that the realization satisfies the capability | The shared receipt substrate | The consumer that emits the receipts |

A GUI-specific realization does NOT imply a GUI-specific capability.
For example, `CGP-ESA-Cap-20` ("Model-Realization Fidelity") has a
current Navigator GUI realization (DisplayFidelityChecker walking the
Qt widget tree), but the capability itself is realization-agnostic — a
CLI output fidelity checker, a doc-generator fidelity checker, or an
API serializer fidelity checker would each be a valid realization of
the same capability.

## §3. Six capability classes

Every cap in the framework falls into exactly one of six classes:

- **Class I — CGP substrate-general (deterministic).** The capability
  is universal at the CGP substrate level and its evidence is purely
  deterministic (gate, hash, exact-value check). Examples: receipt
  chain integrity, semantic hash binding, governance op registry
  partition.

- **Class II — CGP receipt-backed.** The capability is CGP-general but
  its evidence is a deterministic aggregation over the receipt stream
  (latency aggregates, distribution audits, realization-fidelity
  checks). Still mechanically checkable; no human judgment required.

- **Class III — CGP interpretive.** The capability has both a
  deterministic layer (mechanical evidence) and an interpretive layer
  (requires human or LLM judgment over the deterministic output). Each
  Class III entry carries an `interpretive_evidence_template` declaring
  the reviewer question, input artifacts, output format, and review
  authority.

- **Class IV — Tool/application-specific.** No useful CGP-level
  abstraction exists; the capability is tightly bound to a specific
  realization context (e.g., Qt panel composition specifics, internal
  threading model of a particular runtime). Documented as references;
  not in the REGISTRY.

- **Class V — Historical / stale.** Declared in earlier registry
  versions but no live owner; documented in §9 as historical record.

- **Class VI — Aspirational.** Declared with no current realization
  path; documented in §10.

**Only Classes I/II/III are in `ugk.cgp.esa.REGISTRY`.** Classes IV/V/VI
appear in this document for reference and historical record.

## §4. Naming convention

Canonical CGP-ESA IDs follow the form `CGP-ESA-Cap-<N>`, where N is
the legacy ESA numeric ID. Non-numeric handles (T0-03, NBER-1) are
prefixed: `CGP-ESA-T0-03`, `CGP-ESA-NBER-1`. Caps that split into
sub-parts use `<N>-<suffix>` form (`CGP-ESA-Cap-52-base`,
`CGP-ESA-Cap-52-modes`).

Every entry carries a `legacy_esa_id` field for compatibility with
consumers using legacy ESA cap IDs (AbleTools `evidence_scope.py`,
Semantic Navigator codex references). `ugk.cgp.esa.legacy_map()`
provides bidirectional lookup; `ugk.cgp.esa.get_cap()` accepts either
form.

No consumer is required to migrate to canonical IDs in this phase;
the legacy IDs continue to work via `legacy_map()` indefinitely.

---

## §5. Class I — Substrate-general deterministic

### CGP-ESA-Cap-1 — Causal Accountability
**Legacy ESA ID:** `Cap-1`
**Abstract.** Every governed session begins with a `session_open` receipt
at sequence #1; subsequent operations are causally chained via
`prior_receipt_hash`. The receipt stream is the audit trail.
**Realizations.** UGK (`ugk.kernel.GovernanceKernel.open_session`, DONE) ·
Navigator (`navigator.governance.kernel`, DONE) · AbleTools (`make_kernel`,
DONE) · CPVM (`cpvm.bridge.AuthoritativeChain`, PARTIAL).
**Evidence.** Gate: `session_open` receipt at sequence #1 + chain hash
verification.
**Deterministic layer.** First receipt in any session has `op='session_open'`
and `sequence == 1`; chain hash binds to genesis.
**Related invariants:** UL-S-04, NBER-1, S-04.

### CGP-ESA-Cap-2 — Refusal Record
**Legacy ESA ID:** `Cap-2`
**Abstract.** Every refusal is recorded as a structured receipt with the
refusal reason, the attempted op, and the refusing authority.
**Realizations.** UGK (`ugk.kernel.GovernanceKernel.refuse`, DONE; `admission_gate`) ·
AbleTools (`refusal_gate`, DONE).
**Evidence.** Gate: refuse-emits-receipt with structured payload.
**Deterministic layer.** Refusal receipt schema: `{op, reason, authority,
intent, jurisdiction}`; receipt persisted before refusal propagates.
**Related invariants:** UL-S-04, S-04, EH-S-01.

### CGP-ESA-Cap-4 — Integrity Proof (semantic hash)
**Legacy ESA ID:** `Cap-4`
**Abstract.** Every receipt is bound by a content-addressed semantic hash
(DM-S-03) that the chain references; tampering invalidates the hash and
breaks the chain.
**Realizations.** UGK (`ugk.binding.semantic_hash`, DONE; `chain_gate`) ·
AbleTools (`nonrepudiation_gate`, DONE) · CPVM (`cpvm._vendor.ugk.binding`,
DONE).
**Evidence.** Gate: tamper-detection over a curated receipt sequence.
**Deterministic layer.** Semantic hash is a deterministic function of
canonical receipt content; any byte change yields a different hash.
**Related invariants:** DM-S-03, CSH-S-01.

### CGP-ESA-Cap-7 — Receipt Cardinality Audit
**Legacy ESA ID:** `Cap-7`
**Abstract.** The receipt store exposes a stable count of receipts matching
the chain length and the number of persisted entries.
**Realizations.** UGK (`ugk.store.UGKReceiptStore.receipt_count`, DONE).
**Evidence.** Deterministic aggregation: `store.receipt_count() ==
len(chain.read_all())`.
**Deterministic layer.** `receipt_count()` is a pure read of persistent
state; equality with chain length is decidable.
**Related invariants:** S-04.

### CGP-ESA-Cap-12 — Causal Chain Verification
**Legacy ESA ID:** `Cap-12`
**Abstract.** The full receipt stream's hash chain can be verified end to
end; `verify_stream_hash` returns True iff every `prior_receipt_hash`
references the immediately preceding receipt.
**Realizations.** UGK (`verify_stream_hash`, DONE; `chain_gate`) ·
AbleTools (`chain_gate`, DONE) · CPVM (`cpvm.guarded_state`, DONE).
**Evidence.** Gate: chain-verification on fresh-store + on adversarial-store.
**Deterministic layer.** `verify_stream_hash()` walks the chain; returns
Boolean.
**Related invariants:** CSH-S-01, UL-S-04.

### CGP-ESA-Cap-22 — Receipt Chain Completeness
**Legacy ESA ID:** `Cap-22`
**Abstract.** The receipt chain has no gaps in sequence numbers and every
receipt's chain hash matches the recomputed canonical hash.
**Realizations.** UGK (monotonic sequence + h_r in `UGKReceiptStore`, DONE;
`chain_gate`) · AbleTools (`esa_gate`, DONE).
**Evidence.** Gate: sequence-monotonicity + hash-recomputation.
**Deterministic layer.** For each receipt r at sequence n: `r.sequence ==
n`, `r.h_r == semantic_hash(canonical(r))`.
**Related invariants:** DM-S-03, S-04, CSH-S-01.

### CGP-ESA-Cap-67 — Governance Op Registry Integrity
**Legacy ESA ID:** `Cap-67`
**Abstract.** `GOVERNANCE_OPS`, `REAL_OPS`, and `PHANTOM_OPS` satisfy a
partition/disjoint/coverage invariant.
**Realizations.** UGK (`ugk.schema`, DONE; `application_ops_gate`).
**Evidence.** Module-load assertions + `application_ops_gate`.
**Deterministic layer.** `REAL_OPS ⊆ GOVERNANCE_OPS`; `REAL_OPS ∩
PHANTOM_OPS = ∅`; cardinality coverage holds.
**Related invariants:** DECOMP-T0-02.

### CGP-ESA-Cap-88 — CRP Determinism
**Legacy ESA ID:** `Cap-88`
**Abstract.** Projected output is a deterministic function of the codex
sidebar; two runs of the projector against the same codex produce
byte-identical output.
**Realizations.** Navigator (`crp_determinism_auditor`, DONE).
**Evidence.** Deterministic two-build hash equivalence.
**Deterministic layer.** `sha256(projector_output(codex, seed=s)) ==
sha256(projector_output(codex, seed=s))`.
**Related invariants:** CSH-S-01.
**Notes.** Applies to any CRP toolchain, not just Navigator's.

### CGP-ESA-Cap-89 — CRP Codex Coherence
**Legacy ESA ID:** `Cap-89`
**Abstract.** Codex narrative claims are consistent with runtime state;
narrative and source agree.
**Realizations.** Navigator (`crp_codex_coherence_auditor`, DONE).
**Evidence.** Deterministic codex-vs-runtime field comparison.
**Deterministic layer.** For each narrative claim with a runtime
counterpart, values match (or divergence is a known carry).
**Related invariants:** CX-CONV-01.

### CGP-ESA-Cap-90 — CRP Subclass Validation
**Legacy ESA ID:** `Cap-90`
**Abstract.** Source classes inheriting from codex-projected ABCs satisfy
the structural contract; violations raise CRP-γ-* at class definition time.
**Realizations.** Navigator (`crp_subclass_validation_auditor`, DONE) ·
AbleTools (`census_k4`, PARTIAL — different shape, same discipline).
**Evidence.** ABC `__init_subclass__` raises CRP-γ-* on contract miss.
**Deterministic layer.** For each declared method m: `hasattr(cls, m)`
and signature equality.
**Related invariants:** CRP-γ-CONTRACT-INCOMPLETE, CRP-γ-SIGNATURE-MISMATCH.
**Notes.** Most heavily-referenced cap in Navigator codex (136 references).

### CGP-ESA-NBER-1 — Receipt-Before-Effect Discipline
**Legacy ESA ID:** `NBER-1`
**Abstract.** No governed effect occurs without a corresponding receipt
having been persisted first; the receipt write precedes the side effect
on every code path.
**Realizations.** UGK (`GovernanceKernel.execute`, DONE; `admission_gate +
chain_gate`) · AbleTools (`esa_gate`, DONE).
**Evidence.** Gate: adversarial-effect-without-receipt is REFUSED.
**Deterministic layer.** For each side effect, there exists a preceding
receipt with matching op/authority/intent.
**Related invariants:** S-04, UL-S-04.
**Notes.** The discipline that makes the receipt stream complete.

### CGP-ESA-T0-03 — UGKReceiptStore Method Contract
**Legacy ESA ID:** `T0-03`
**Abstract.** The `UGKReceiptStore` class exposes the canonical method
surface with stable signatures; subclasses must satisfy this contract.
**Realizations.** UGK (`ugk.store.UGKReceiptStore`, DONE).
**Evidence.** Method presence + signature equality at class load.
**Deterministic layer.** `hasattr(UGKReceiptStore, m)` for each declared
method; signatures match the codex sidebar spec.
**Related invariants:** DECOMP-T0-03.
**Notes.** Decomp-level contract; mirrored in Navigator/CPVM consumers.

---

## §6. Class II — Receipt-backed deterministic aggregation

### CGP-ESA-Cap-3 — Authority Trace
**Legacy ESA ID:** `Cap-3`
**Abstract.** Every receipt carries an authority field; the authority trace
across a session is queryable and matches the warrant store's declared
authority bindings.
**Realizations.** UGK (DONE, `authority_model_gate`) · AbleTools (PARTIAL).
**Evidence.** Receipt-stream aggregation: distinct authorities +
warrant-store join.
**Deterministic layer.** `GROUP BY authority` over the receipt stream;
`JOIN` against `WarrantStore.list_warrants()`.
**Related invariants:** CHARTER-S-01.

### CGP-ESA-Cap-13 — Receipt Distribution Audit
**Legacy ESA ID:** `Cap-13`
**Abstract.** Distribution of receipts across ops, authorities, and
jurisdictions is queryable and matches expected proportions.
**Realizations.** UGK (PARTIAL — aggregation primitive available).
**Evidence.** Deterministic aggregation: per-op count distribution.
**Deterministic layer.** `GROUP BY op COUNT(*)` over the receipt stream.

### CGP-ESA-Cap-20 — Model-Realization Fidelity
**Legacy ESA ID:** `Cap-20`
**Abstract.** A declared model is faithfully rendered by the realization
that claims to drive it; no "phantom compliance".
**(Reclassified — previously framed GUI-specific. Under the corrected
ontology, this capability is realization-agnostic; the Navigator GUI is
one realization.)**
**Realizations.** Navigator (`DisplayFidelityChecker`, DONE).
**Evidence.** Receipt: `render_fidelity_check` with `fidelity_ok=True/False`.
**Deterministic layer.** For each declared model entry, the realization
exposes a matching surface element with identical labeling.
**Related invariants:** EVS-S-09.
**Future realizations possible:** API serializer fidelity, doc-generator
fidelity, CLI-output fidelity.

### CGP-ESA-Cap-21 — Operation Reachability
**Legacy ESA ID:** `Cap-21`
**Abstract.** Every declared op has at least one path through which the
realization invokes it.
**(Reclassified — previously framed GUI-specific.)**
**Realizations.** Navigator (`reachability_auditor + UI_PATH_REGISTRY`,
DONE).
**Evidence.** Receipt: `reachability_gap` is empty for declared ops.
**Future realizations:** CLI command paths, REST endpoint registry, MCP
tool exposure.

### CGP-ESA-Cap-52-base — Op-Pair Latency Anomaly Detection
**Legacy ESA ID:** `Cap-52`
**Abstract.** Inter-op latencies are aggregated over the receipt stream;
anomalously slow or fast pairs surface as findings.
**Realizations.** Navigator (`OpPairLatencyDetector`, DONE).
**Evidence.** Scenario-sweep anomaly score from `HR.cap52_sweep`.
**Deterministic layer.** For each `(op_a, op_b)` pair: median latency over
receipt stream; flag pairs > N stdev from baseline.
**Related invariants:** OS-S-04.
**Notes.** The 5-mode statistical-inference extension is aspirational
(`CGP-ESA-Cap-52-modes`, Class VI — see §10).

### CGP-ESA-Cap-53 — Subsystem Liveness Monitor
**Legacy ESA ID:** `Cap-53`
**Abstract.** Background subsystems emit periodic liveness receipts;
absence indicates stall.
**Realizations.** Navigator (`ESAHealthStore + ehm_workers`, DONE).
**Evidence.** Receipt: liveness heartbeat present within threshold.
**Related invariants:** OS-S-03.

### CGP-ESA-Cap-57 — Receipt Profile Convergence
**Legacy ESA ID:** `Cap-57`
**Abstract.** Two builds of the same governed system produce convergent
receipt profiles (identical convergence fingerprint).
**Realizations.** Navigator (`convergence_fingerprint`, DONE) · UGK
(`ugk.cgp.runner.ConvergenceFingerprint`, DONE).
**Evidence.** Fingerprint equality across independent build runs.
**Related invariants:** HR-T-16.

### CGP-ESA-Cap-58 — Behavior Realization Audit
**Legacy ESA ID:** `Cap-58`
**Abstract.** Every declared behavior has a realized implementation
reachable by the runtime.
**(Reclassified — previously framed GUI-specific "gesture realization".)**
**Realizations.** Navigator (`gesture_realization_auditor_runtime`, DONE).
**Evidence.** Receipt: per-behavior realization-finding (ok | gap).
**Related invariants:** EVS-S-09.
**Future realizations:** CLI action audit, API handler audit, batch-job
realization audit.

### CGP-ESA-Cap-59 — Receipt Volume Health
**Legacy ESA ID:** `Cap-59`
**Abstract.** Receipt emission rate stays within declared bounds.
**Realizations.** Navigator (`esa_health` volume thresholds, DONE).
**Deterministic layer.** `len(receipts in window W) in [lo, hi]`.
**Related invariants:** OS-S-03.

### CGP-ESA-Cap-41 — Receipt Stream Lineage
**Legacy ESA ID:** `Cap-41`
**Abstract.** The lineage of each receipt (causal chain from session
open to current point) is queryable and stable; replay produces
identical lineage for identical inputs.
**Realizations.** UGK (`UGKReceiptStore.read_all + verify_stream_hash`,
DONE; `chain_gate`) · Navigator (`HR.run_batch` HR-S-05 batched
execution with checkpoint receipts, DONE).
**Evidence.** Deterministic lineage walk: each receipt's
`prior_receipt_hash` references the previous in sequence.
**Deterministic layer.** For each receipt r at sequence n > 1:
`r.prior_receipt_hash == h_r(receipt at sequence n-1)`. Walking the
chain from genesis to any receipt produces a deterministic lineage.
**Related invariants:** CSH-S-01, UL-S-04, HR-S-05.
**Notes.** Promoted from pattern family in Track 3. Closely related to
Cap-12 (Causal Chain Verification, Class I): Cap-12 verifies lineage
integrity; Cap-41 is the broader "lineage as queryable artifact"
abstract.

---

## §7. Class III — CGP interpretive

Class III caps have both a deterministic layer (mechanical) and an
interpretive layer (requires human or LLM judgment over the
deterministic output). Each entry includes an
`interpretive_evidence_template` declaring the reviewer question,
input artifacts, output format, and review authority. These are
TEMPLATES; concrete signed `InterpretiveEvidencePack` instances are
emitted at review time by the consumer.

### CGP-ESA-Cap-31 — Structural Completeness Audit
**Legacy ESA ID:** `Cap-31`
**Abstract.** The implementation is structurally complete with respect to
the declared invariant surface.
**Realizations.** Navigator (`structural_auditor (R3 census)`, DONE,
deterministic=False) · AbleTools (`census_k4`, PARTIAL, deterministic=True).
**Deterministic layer.** For each invariant i: `count(artifacts bound to
i)` is computable; gaps listed.
**Interpretive layer.** Given the census, is the implementation
"complete"? Some gaps are intentional (waivers, future work).
**Interpretive evidence template.**
- Reviewer question: Given R3 census output, is the implementation
  structurally complete for the declared surface? List unjustified gaps
  and recommend disposition.
- Input artifacts: census output + declared invariant list + waiver
  registry.
- Output format: verdict ∈ {complete, partial-acceptable,
  partial-with-gaps, absent} + per-gap classification + cited rationale.
- Review authority: `designated_auditor`.

**Pattern family note:** `Cap-34`, `Cap-35`, `Cap-36` were originally
pattern entries under Cap-31; in Track 3 they were promoted to full
anchor entries below. Additional pattern variations under Cap-31's
shape (different counting predicates) may be promoted to anchors in
future maturation phases as realization evidence accumulates.

### CGP-ESA-Cap-32 — Hardcoded-Value Scan
**Legacy ESA ID:** `Cap-32`
**Abstract.** Source modules are scanned for hardcoded values that should
be config-driven.
**Realizations.** Navigator (`ConfigAuditor` KNOWN_HARDCODED scan, DONE).
**Interpretive layer.** For each match: intentional / config-leak / fixture?
**Interpretive evidence template.**
- Reviewer question: Classify each hardcoded-value match as intentional /
  config-leak / fixture; recommend extraction where appropriate.
- Review authority: `designated_auditor`.

### CGP-ESA-Cap-33 — Error Path Completeness
**Legacy ESA ID:** `Cap-33`
**Abstract.** Every declared error code has a path that emits it; every
failure path has a declared code.
**Realizations.** Navigator (PARTIAL, deterministic=False) · AbleTools
(`error_codes_gate`, DONE, deterministic=True — declaration-only).
**Interpretive layer.** Are there undeclared failure modes?
**Interpretive evidence template.**
- Reviewer question: Given the declared-vs-raised error code mapping,
  are there failure modes lacking a declared error code?
- Review authority: `designated_auditor`.
**Related invariants:** EH-S-01, EVS-S-08.

### CGP-ESA-Cap-56 — CTR Parsed Invariant Count
**Legacy ESA ID:** `Cap-56`
**Abstract.** Parser-extracted invariant count matches independent count.
**Realizations.** Navigator (`ctr.analyzer` + narrative count, DONE).
**Interpretive layer.** Is the parser correctly scoped?
**Interpretive evidence template.**
- Reviewer question: If counts differ, is the parser scope correct or
  is the codex narrative stale?
- Review authority: `Governor`.
**Related invariants:** CTR-S-02.

### CGP-ESA-Cap-73 — Test Suite Representativeness
**Legacy ESA ID:** `Cap-73`
**Abstract.** Test suite adequately samples the governed surface.
**(Reclassified — previously GUI gesture coverage; under corrected
ontology, applies to any governed-surface coverage.)**
**Realizations.** Navigator (`test_representativeness_auditor`, DONE,
deterministic=False).
**Deterministic layer.** `ratio = covered / total >= advisory_floor`.
**Interpretive layer.** Is the covered subset biased toward easy cases?
**Interpretive evidence template.**
- Reviewer question: Given coverage ratio and surface coverage, is the
  test suite representative or biased?
- Review authority: `designated_auditor`.
**Related invariants:** CTR-S-05, EVS-S-01.

### CGP-ESA-Cap-83 — Cross-Session Persistence
**Legacy ESA ID:** `Cap-83`
**Abstract.** State that should persist across sessions does; state that
should not, doesn't.
**Realizations.** Navigator (PARTIAL; carry).
**Interpretive layer.** Per-element intentionality.
**Interpretive evidence template.**
- Reviewer question: For each state element that changed (or did not)
  across session boundary, is the behavior intentional per the declared
  persistence model?
- Review authority: `designated_auditor`.

### CGP-ESA-Cap-34 — Structural Completeness: Class Names
**Legacy ESA ID:** `Cap-34`
**Abstract.** For each declared class in the codex, a class of the
same name exists in source; for each class in source, a corresponding
codex declaration exists. Drift surfaces as findings classified by
interpretive review.
**Realizations.** Navigator (`structural_auditor` declared-vs-source
class enumeration, DONE, deterministic=False).
**Deterministic layer.** `declared_classes(codex) ⊕
source_classes(modules)` is computable: `(in_both, codex_only,
source_only)` triple.
**Interpretive layer.** For each `codex_only` entry: speculative codex
addition or pending source impl? For each `source_only` entry:
legitimate helper or undeclared drift?
**Interpretive evidence template.**
- Reviewer question: Classify each codex-only / source-only class as:
  speculative-codex-entry / pending-source-impl /
  legitimate-source-helper / drift-to-fix.
- Input artifacts: structural_auditor symmetric diff output.
- Output format: per-entry classification + recommended action.
- Review authority: `designated_auditor`.
**Related invariants:** ST-S-01, DECOMP-T0-03.
**Notes.** Promoted from Cap-31 pattern family in Track 3. Narrows
the Cap-31 completeness audit to class-name population specifically.

### CGP-ESA-Cap-35 — Structural Completeness: Method Signatures
**Legacy ESA ID:** `Cap-35`
**Abstract.** For each declared class, the methods declared in the
codex match the methods in source by name AND signature; signature
drift is detected and surfaced for interpretive review.
**Realizations.** Navigator (`crp_subclass_validation_auditor`,
PARTIAL — name+signature check is deterministic for ABC sidebars via
Phase γ; helper-classification of undeclared methods is interpretive).
**Deterministic layer.** For each declared method m: `hasattr(cls,
m)` AND `inspect.signature(cls.m) == declared signature`. Undeclared
method set is enumerable.
**Interpretive layer.** For undeclared source methods: accepted
private helper, candidate for codex promotion, or accidental
addition?
**Interpretive evidence template.**
- Reviewer question: For each undeclared method in source, classify
  as: accepted-private-helper / consider-promoting /
  accidental-addition.
- Input artifacts: method-name diff + signature comparison output.
- Output format: per-method classification + recommended action.
- Review authority: `designated_auditor`.
**Related invariants:** ST-S-02, DECOMP-T0-03,
CRP-γ-CONTRACT-INCOMPLETE, CRP-γ-SIGNATURE-MISMATCH.
**Notes.** Promoted in Track 3. **Coexists with Cap-90.** Cap-90
(Class I) is the narrow deterministic ABC-subclass validation; Cap-35
(Class III) is the broader method-set abstract that includes
interpretive classification of undeclared methods. Both are valid;
they answer different questions about the same source.

### CGP-ESA-Cap-36 — Structural Completeness: Module Boundaries
**Legacy ESA ID:** `Cap-36`
**Abstract.** The module boundaries declared in the codex (which
classes live in which module) match source layout; cross-module
references are declared in `cross_module_invariants` blocks.
**Realizations.** Navigator (`structural_auditor` declared-vs-actual
module paths + cross-module import audit, PARTIAL).
**Deterministic layer.** For each codex-declared class c with
declared_module m: `actual_module(c) == m`. For each cross-module
import in source: presence in declared `cross_module_invariants` is
decidable.
**Interpretive layer.** Undeclared cross-module imports may be
standard-library, accepted utility, drift to declare, or
architectural violation.
**Interpretive evidence template.**
- Reviewer question: For each undeclared cross-module import,
  classify as: standard-library / accepted-utility /
  declare-as-invariant / architectural-violation.
- Input artifacts: module-path diff + cross-module import report.
- Output format: per-import classification + action.
- Review authority: `designated_auditor`.
**Related invariants:** ST-S-03, DECOMP-T0-03.
**Notes.** Promoted from Cap-31 pattern family in Track 3.

### CGP-ESA-Cap-42 — Op-Coverage Audit
**Legacy ESA ID:** `Cap-42`
**Abstract.** The set of ops actually exercised over a representative
workload covers the declared `REAL_OPS` surface to an adequate
threshold; under-exercised ops surface as findings for interpretive
classification.
**Realizations.** Navigator (HR sweeps per-op count distribution,
PARTIAL — coverage ratio deterministic; "representative workload?"
interpretive).
**Deterministic layer.** `coverage_ratio = |distinct ops in receipt
stream| / |REAL_OPS|`. `under-exercised_set = REAL_OPS \ {ops in
stream}`.
**Interpretive layer.** For each under-exercised op: adequately-
exercised (false positive), rare-by-design (acceptable, e.g.
emergency refusal), or under-tested (add coverage)?
**Interpretive evidence template.**
- Reviewer question: For each under-exercised op, classify as:
  adequately-exercised / rare-by-design / under-tested.
- Input artifacts: coverage ratio + per-op count distribution +
  REAL_OPS reference.
- Output format: per-op classification + recommended additions.
- Review authority: `designated_auditor`.
**Related invariants:** CTR-S-05, EVS-S-01.
**Notes.** Promoted in Track 3. Distinct from Cap-73 (Test Suite
Representativeness): Cap-73 asks about test/governed-surface match;
Cap-42 asks specifically about op-set coverage.

### CGP-ESA-Cap-48 — Test-Path Reachability
**Legacy ESA ID:** `Cap-48`
**Abstract.** Every declared test path (gate, scenario, sweep) is
reachable from the canonical entry point; orphaned tests (declared
but unreachable) and extras (discovered but undeclared) surface for
interpretive classification.
**Realizations.** Navigator (`collect_gate_tests` + `TEST_REGISTRY`
cross-check, HR-S-06, DONE) · AbleTools (`governed_runner` reading
`coverage_map.json`, PARTIAL — coverage-dispatch shape; same
discipline).
**Deterministic layer.** `discovered_tests(module) ⊕
declared_tests(registry)` is a symmetric diff. `orphan_set =
declared \ discovered`. `extra_set = discovered \ declared`.
**Interpretive layer.** Orphan classification: registry-stale, test
renamed, or pending-impl? Extra classification: ad-hoc-to-declare,
ephemeral-debugging, or accepted-helper?
**Interpretive evidence template.**
- Reviewer question: For each orphan/extra test, classify as:
  registry-stale / pending-impl / ad-hoc / ephemeral /
  declare-formally.
- Input artifacts: discovered-tests vs declared-tests diff.
- Output format: per-test classification + recommended action.
- Review authority: `designated_auditor`.
**Related invariants:** CTR-S-06, HR-S-06.
**Notes.** Promoted in Track 3.

---

## §8. Class IV — Truly realization-bound (reference)

The following capability families are realization-specific in a way
that no useful CGP-level abstraction exists yet. They are documented
here for reference but NOT in `ugk.cgp.esa.REGISTRY`.

- **Cap-77..87 — Qt panel composition / button signal-connectivity /
  widget population variants.** The abstract concerns (component
  composition, signal handling, surface population) are realizable in
  non-GUI contexts, but the SPECIFICITY of these caps (Qt panel
  objects, signal handlers, widget population semantics) ties them
  tightly to Qt widget trees. The broader "component-composition
  realization" concern is covered by `CGP-ESA-Cap-58`.

- **Cap-40..46 — Navigator runtime/simulation specifics.** Threading
  model, event loop, worker scheduling — runtime concerns specific to
  the Navigator's GUI architecture. The CGP-level abstraction (work
  scheduling discipline) is too thin to host as a separate cap.

If a future non-GUI realization emerges, the abstract gets promoted
to Class I/II/III at that point.

## §9. Class V — Historical / stale

Caps declared in earlier ESA registry versions whose implementations
have been retired, renamed, or never written. The Navigator codex
v6.1 cites a `~75-cap drift surfaced by Build 4 inspection — codex
narrative claims 90 caps, source has 15` and later reconciles to
`Cap-1..76 with Cap-1..57 + Cap-58/59/73 active`. The drift gap
(`Cap-60..72`, `Cap-74/75/76`) is the Class V population.

These are NOT in `ugk.cgp.esa.REGISTRY`. Consumers should not declare
scope entries for them. If reconciliation work produces live
realizations in the future, the relevant caps get promoted to
Class I/II/III in the registry at that point.

## §10. Class VI — Aspirational

- **`CGP-ESA-Cap-52-modes`** — The five-mode statistical-inference
  extension of `Cap-52`. The base form (op-pair latency anomaly) is
  Class II and is realized (`CGP-ESA-Cap-52-base`). The five-mode
  extension is declared in Navigator codex but lacks an active
  realization path. Aspirational pending implementation evidence.

Class VI caps are NOT in `ugk.cgp.esa.REGISTRY` but appear here for
discoverability. Promotion to Class I/II/III requires a concrete
realization.

---

## §11. Cross-references

### Consumer scope authoring
Consumers declare which CGP-ESA caps apply to them via an
`evidence_scope.py` module of the shape documented in
`ugk.capability_evidence`. The module exports a `SCOPE` dict; the
helper `ugk.capability_evidence.load_scope(module)` parses it; the
helper `ugk.capability_evidence.verify_evidence_map(claims, gates_dir)`
asserts each `DONE`/`PARTIAL` claim has a resolvable gate file.

Diff against this CGP-ESA registry:
```python
from ugk.cgp.esa import registry_cap_ids, legacy_map
from ugk.capability_evidence import diff_against_registry, load_scope
from <consumer>.governance.codex import evidence_scope

claims = load_scope(evidence_scope)

# Diff against legacy IDs (preserves consumer's current convention)
legacy_ids = set(legacy_map().keys())
diff = diff_against_registry(claims, legacy_ids)

# OR diff against canonical CGP-ESA IDs (forward-consistent)
canonical_ids = set(registry_cap_ids())
diff = diff_against_registry(claims, canonical_ids)
```

### CGP execution substrate
Evidence for CGP-ESA caps is produced through the CGP execution
substrate. See [`CGP_EXECUTION_SUBSTRATE.md`](./CGP_EXECUTION_SUBSTRATE.md)
for the runner contract, HeadlessRunner / CTR / SRSA surfaces, and
the pipeline from scope → claim → gate → CGPRunner → EvidenceArtifact
→ CTR analysis → CoverageReport.

### Distinct from ugk.core.esa
`ugk.core.esa` is the kernel-native ESA capability evaluator
(~5 caps; runs against a `GovernanceKernel` and returns
`ESAKernelReport`). `ugk.cgp.esa` is the CGP-ESA capability family
registry (this document's subject). Both coexist; the kernel-native
evaluator is one realization of a small subset of caps the registry
declares.

## §12. Substrate stability statement

The UGK constitutional substrate is UNCHANGED by the CGP-ESA registry:

- `ugk/invariants.py` **was** byte-identical to the M2.3 canonical at the M2.3 line CGP was authored against; the **current r123 frame** is `law_hash a3992e45...`
  (`law_hash 546a9e90fd780dec…`).
- As of the M2.3 line, the conformance suite was **78 gates** and the M2 vector suite **39 vectors**, and CGP adds none over that baseline. **Current frame (as of release r125): 100 conformance gates, 46 ADRs, `law_hash a3992e45...`.** Whether the CGP additivity statement re-validates over the advanced frame is a separate grounding question, not asserted here.
- No new error codes are declared.
- No new constitutional declarations exist.
- The Receipt schema, `GOVERNANCE_OPS`, `REAL_OPS`, `PHANTOM_OPS` are
  unchanged.
- `ugk.core.esa` (the kernel-cap evaluator) is unchanged and remains
  separate from `ugk.cgp.esa` (the registry).
- `ugk.capability_evidence` is unchanged; the registry is one possible
  argument to its `diff_against_registry()` helper, not a modification
  of the helper itself.
- All Tier 1 compatibility aliases preserved per CGP-SUBSTRATE policy.

CGP-ESA infrastructure is purely additive. Consumers who do not
reference the registry continue to work identically. Consumers who
reference the registry (via `ugk.cgp.esa.REGISTRY` or
`registry_cap_ids()` / `legacy_map()`) gain forward-consistent
capability discovery without sacrificing compatibility with legacy
ESA cap IDs.

---

**Registry version:** Track 3 expansion (anchor enumeration grown
from 27 to 33 caps; `CGP-ESA-Cap-NN` namespace preserved).
**Population:** 33 anchor caps across Classes I (12) / II (10) / III (11).
**Track 3 promotions:** Cap-41 (Class II); Cap-34, Cap-35, Cap-36,
Cap-42, Cap-48 (Class III). All 27 pre-existing entries preserved
byte-identical; legacy_esa_id mappings unchanged.
**Pattern families remaining (not in REGISTRY):** Cap-31 sub-family
variations beyond Cap-34/35/36 (additional counting-predicate
variants); Class IV / V / VI populations summarized in §8/§9/§10.
**Future expansion:** additional anchor caps promoted as realization
evidence accumulates; consumer-side adoption of `CGP-ESA-Cap-NN`
naming is voluntary and deferred to separate phases.
