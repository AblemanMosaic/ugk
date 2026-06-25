# UGK Capability Classification Register (A3)

Classifies the **full known capability surface** of the UGK v0.1.0 substrate so that no known
site is ambiguous. Classification only — no behavior is changed by this document. The machine
checker `tools/capability_register_check.py` verifies every row against the code; run it to
reproduce the consistency verdict.

## Taxonomy (Governor-confirmed)

- **observation** — read-only exposure of current state; no asserted conclusion beyond reporting;
  no receipt; never refuses.
- **claim** — a checkable assertion *derived from* observations (e.g. a hash, an intactness
  boolean, a verifier/continuity verdict, a key-fingerprint identity).
- **governance** — a gated / refusable / receipted authority action through `kernel.execute()`.
- **provenance** — a historical evidence artifact / receipt explaining how something came to be,
  without necessarily being a governance act.
- **declared remainder** — a boundary where governance does not reach, *declared* (CR-01..04) and
  surfaced; named, not exploitable.

## Register

| # | Site | Kind | Status | Evidence path | Receipt / provenance behavior | Closing / deferred |
|---|------|------|--------|---------------|------------------------------|--------------------|
| 1 | CR-01 OS layer | declared remainder | declared+surfaced | `ugk/kernel.py` `CLASSIFIED_REMAINDERS`; `classified_remainders_gate.py` | none (OS gives no receipt infra) | OS-level isolation out of scope (B4a cross-process) |
| 2 | CR-02 Python runtime internals | declared remainder | declared+surfaced | `ugk/kernel.py`; `classified_remainders_gate.py` | none (bytecode not receipted) | — |
| 3 | CR-03 SQLite/WAL layer | declared remainder | declared+surfaced | `ugk/kernel.py`; `classified_remainders_gate.py` | none (fs ops below SQLite not receipted) | — |
| 4 | CR-04 `effect()` internals | declared remainder | declared+surfaced+canary | `ugk/kernel.py`; `ugk/conformance/canary_gate.py` | opaque unless effect re-enters `kernel.execute()`; canary proves no capability leaks | — |
| 5 | `kernel.status()` | observation | active | `ugk/kernel.py:215` | read-only; no receipt; no refuse | — |
| 6 | `kernel.snapshot()` | observation | active | `ugk/kernel.py:803` | read-only; no receipt | — |
| 7 | `kernel.snapshot_fast()` | observation | active | `ugk/kernel.py:753` | read-only; no receipt | — |
| 8 | CLI `status` | observation | active | `ugk/cli.py` (status); surfaces frame triad | read-only | — |
| 9 | `store.schema_hash()` | claim | active | `ugk/storage/store.py:373` | observation-derived structural fingerprint; no receipt; observe-only | — |
| 10 | `store.schema_frame_intact()` | claim | active | `ugk/storage/store.py:377` | boolean structural-intactness claim vs `EXPECTED_SCHEMA_HASH`; observe-only, never refuses | — |
| 11 | Key fingerprint identity `mosaic_id(pubkey)` | claim | active | B3 keygen; `manifest.mosaic_root` forward-link | identity assertion; **not** a governance receipt | — |
| 12 | Keygen creation provenance (B3) | provenance | active | `docs/B3_KEY_PROVENANCE.md`; `tools/b3_conformance.py` | public-only creation artifact; founding-independent; not a governance receipt | — |
| 13 | GRBSA verifier verdict | claim | active | `tools/grbsa/verifier.py`, `verifier_gate.py` | checkable conclusion derived from gate observations | — |
| 14 | Proof Model B `ContinuityB` verdict | claim | active (primary) | `tools/grbsa/proof_model_b.py`; `PROOF_MODEL_B.md` | continuity conclusion derived from frame-triad + gates + conformance + confinement; byte-identity only clause S | — |
| 15 | `migrate_schema` / `schema_migrated` (B2) | provenance | active | `ugk/storage/store.py:382`; `docs/B2_SCHEMA_MIGRATION.md`; `tools/b2_conformance.py` | storage-frame migration receipt (before/after `schema_hash` + intent); **not** a governance receipt; refuse-before-mutation on unsafe DDL | full transactional atomicity (DDL+receipt single txn) deferred; mitigated by receipt-safe allowlist |
| 16 | `authority_model_set` (B5/B5a) | governance | active | `ugk/ops.py` (`_APPLICATION_OPS`); `tools/b5a_conformance.py` | execute()-routed governed op; deterministic `model_hash` bound to manifest; CLI enforcement | — |
| 17 | Capability attenuation chain | governance | active | `ugk/authority/capabilities.py` (`attenuates`, `compute_effective_capabilities`) | enforces `child ⊆ parent`; fails `CapabilityEscalation` | — |
| 18 | `_KERNEL_OPS` {gate_admit, gate_refuse} | governance | frozen | `ugk/schema.py` | the gate verbs; refusal is first-class | — |
| 19 | `_UNIVERSAL_OPS` {crp_evidence, legend_seal, session_open/close/summary, test_checkpoint} | governance | frozen (M2.3 legend) | `ugk/schema.py:38` | execute()-routed governed ops; legend-member (frozen) | — |
| 20 | `_APPLICATION_OPS` {authority_model_set} | governance | active (deployment-declarable) | `ugk/schema.py:79`; `ugk/ops.py` | execute()-routed; exempt from frozen legend (Resolution C); uncompressed fallback | — |
| 21 | `store.seal_legend` | governance (frame sealing) | frozen (M2.3) | `ugk/storage/store.py:832` | persists the frozen legend seal under the writer lock; idempotent; provenance character | — |
| 22 | `store.seal_scope` | governance (frame sealing) | active | `ugk/storage/store.py:873` | persists scope seal under the writer lock | — |
| 23 | `store.seal_authority_model` | governance (frame sealing) | active | `ugk/storage/store.py:909` | persists the B5/B5a authority model under the writer lock | — |
| 24 | `verify_from_seal(S)` (B1) | claim | active | `ugk/storage/store.py`; `tools/b1_conformance.py` | checkable assertion that the retained chain verifies from the seal commitment S; read-only | — |
| 25 | `epoch_sealed` receipt (B1) | provenance | active | `ugk/storage/store.py`; `docs/B1_EPOCH_SEAL.md` | records the seal commitment S + epoch metadata; not a governance receipt; tail-appended | — |
| 26 | `epoch_pruned` receipt (B1) | provenance | active | `ugk/storage/store.py`; `docs/B1_EPOCH_SEAL.md` | records the prune event (range + S); the *record* is provenance | — |
| 27 | `seal_and_prune_epoch` op (B1) | governance | active | `ugk/storage/store.py`; `tools/b1_conformance.py` | destructive, fail-closed, intent-required, single-writer-locked storage-frame governed act; refuse-before-mutation; tip preserved across prune | full multi-epoch seal meta-chains + cold-storage of pruned prefix deferred (B4b territory) |

## Notes on boundary calls

- **observation vs claim.** `status`/`snapshot` merely expose state (observation). `schema_hash`,
  `schema_frame_intact`, the verifier verdict, the `ContinuityB` verdict, and the key fingerprint are
  *derived assertions* over observations (claim). None of them refuse or emit receipts.
- **governance vs provenance.** `authority_model_set` is execute()-routed and refusable → governance.
  `schema_migrated` and keygen creation are receipts/artifacts recording how state came to be, with no
  gate/refuse → provenance. This is the boundary fixed by the B2 and B3 rulings.
- **seal surfaces** are the persistence half of governed sealing (constitutional frame state under the
  single-writer lock). Classified as governance (frame sealing) with provenance character; they do not
  independently gate/refuse but only execute as the effect of a governed/sealing flow.

## Consistency

`tools/capability_register_check.py` mechanically verifies the load-bearing classifications against the
code (op-tier membership; `schema_migrated` is **not** a governance op; migration is provenance with
refuse-before-mutation; inspection/claim sites are read-only; CR-01..04 declared; seal/authority surfaces
present). A contradiction would be any site whose implementation does not match its declared kind.
