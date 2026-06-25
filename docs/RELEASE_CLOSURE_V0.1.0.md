# UGK v0.1.0 — Release-Closure Record

> **HISTORICAL RECORD — not the live frame.** This closure record captures the frame *as of its authoring* (an
> early v0.1.0 release). The v0.1.0 reference line continued to evolve afterward; the **authoritative live frame for
> any checked-out archive is its top-level `RELEASE.txt`**. Older parenthetical frame pins in this historical note
> must not be read as current. The frame
> triad recorded below is preserved verbatim as history and must not be read as the current frame.

Canonical current-state record (AS OF AUTHORING) for the UGK v0.1.0 single-writer reference line. Where any other
document's framing predates the work recorded here (notably byte-identity "transitivity" language in
the GRBSA overlay notes), this record governs.

## Frame triad (the continuity anchor)

Continuity is anchored on the three-legged frame, not on byte-identity to any single baseline:

- **law leg** `law_hash` = `546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820`
  (sha256 of `ugk/invariants.py`)
- **meaning leg** `legend_hash` = `a7e2a9c9fdc2e73c403f5b191a3e84fcda06071dc2790606d8f0e2e4516552ff`
  (frozen at M2.3; `ugk/storage/binding.py:LEGEND_HASH`)
- **structure leg** `schema_hash` = `bcb3397f260b1332f80c4acd33d2dd2ac3f27133042838784868e95a7d08d394`
  (`EXPECTED_SCHEMA_HASH`, over `PRAGMA table_info` of the four governed tables)

All three are unmoved across the entire hardening + Category A/B + continuity program.

## Resolved scope

**Hardening set (complete).** B5/B5a governed `authority_model_set` + CLI enforcement; B3 keygen
creation provenance (identity claim, not a governance receipt); B4a single-writer `RLock` serializing
the whole receipt-append RMW and all seal operations; schema_hash frame-pin (observe-only); Resolution
C projection-continuity gate (constitutional ops require frozen-legend membership; deployment ops
exempt via uncompressed fallback).

**Category A (complete).**
- *B2 — governed schema migration.* `store.migrate_schema(...)` at the storage/frame layer:
  intent-required, fail-closed, single-writer-locked; a module-level receipt-safe DDL allowlist
  refuses anything that could invalidate receipting (DROP/RENAME/DROP COLUMN/DML/PRAGMA/ATTACH/
  multi-statement/NOT-NULL-without-DEFAULT), refusal-before-mutation. A permanent negative control
  proves the original atomicity-bug class is refused with zero drift. Not a kernel op; no legend term.
- *Proof Model B — intrinsic behavioral continuity.* `ContinuityB(baseline→candidate)` holds iff
  clause (S) byte-identity shortcut OR clause (B) behavioral basis: B1 frame-triad stability (computed
  tree-independently), B2 the 9 GRBSA behavioral gates, B3 conformance directly on the candidate, B4
  change confinement to the declared substrate surface. Primary continuity authority; byte-identity
  demoted to clause (S).
- *A3 — capability classification register.* Full known surface classified as
  observation / claim / governance / provenance, mechanically checked; no contradictions.

**Category B (complete).**
- *B1 — epoch seal + retention.* `seal_and_prune_epoch(seal_hash=S, intent)` at the storage/frame
  layer: intent-required, fail-closed, single-writer-locked, destructive. The seal commitment **value
  S** is the verification anchor (`verify_from_seal(S)`); `epoch_sealed`/`epoch_pruned` are provenance
  records carrying S. Provenance receipts are appended at the tail before deletion, so pruning the
  prefix cannot move the tip (`tip_after_prune == tip_before_prune`): pruning is observationally
  equivalent to retaining the prefix. No schema change; no change to receipt-hash or `stream_hash()`
  semantics.

**Continuity extension (current).** The composed claim reaches the current substrate baseline:
`ContinuityB(r17a→r46) ∧ ContinuityB(r46→r49) ∧ ContinuityB(r49→r54)`, every link HOLDS via the
behavioral basis. G6 delegates substrate continuity to the composed proof (`proof_model_b --compose`,
heavy by design). **No competing continuity model remains.**

## Capability taxonomy (A3 summary)

- **observation** — read-only state exposure (`status`, `snapshot`, `snapshot_fast`).
- **claim** — checkable assertions (`schema_hash`/`schema_frame_intact`, `verify_from_seal`,
  verifier / `ContinuityB` verdicts).
- **governance** — gated/refusable/receipted authority actions (`authority_model_set`, kernel op
  tiers, capability attenuation, the `seal_*` surfaces, and `seal_and_prune_epoch`).
- **provenance** — historical evidence artifacts that are not themselves governance acts
  (`schema_migrated`, keygen creation, `epoch_sealed`, `epoch_pruned`).

Storage-frame governed operations (`migrate_schema`, `seal_and_prune_epoch`) are deliberately **not**
kernel `execute()` ops: `schema_migrated`/`epoch_sealed`/`epoch_pruned` are confirmed absent from
`GOVERNANCE_OPS`.

## Final gate-surface verification (clean extraction, r56)

Frame triad unmoved; B1, B2, B3, B4a, B5a, schema_hash, capability-register gates all PASS; batch
78/78 ALL PASS; scale ALL PASS; AL CLEAN; G6 aggregate PASS; Proof Model B `--compose` → CONTINUITY
HOLDS (composed).

## Deferred to v0.2.0-scale (not v0.1.0 blockers)

B4b per-jurisdiction / per-epoch chain partitioning; cold-storage re-verification of pruned prefixes
(keeping pruned history re-derivable); multi-epoch seal meta-chains; distributed / high-throughput
storage architecture; cross-process writer isolation (B4a is in-process only).

## Process note

During the r56 polish, the live working tree was found to have diverged from the accepted r55
artifact. The response was to rebuild the working tree from the accepted artifact and apply the change
there, so the resulting archive is provably `accepted-baseline + the stated change`. This is the
release discipline detecting and correcting drift, recorded here as evidence the process works.

## Readiness verdict

**Publication-ready as the single-writer reference v0.1.0 line.** The substrate is frame-stable,
every governed surface is classified and gated, destructive storage operations (schema migration,
epoch prune) are fail-closed and serialized under the single writer, and substrate continuity is
proven behaviorally across the full lineage by a single authoritative model. The deferred items are
scale-architecture concerns for v0.2.0, not correctness gaps in the reference line.
