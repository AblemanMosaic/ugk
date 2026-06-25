# B2 — Governed Schema Migration (storage-frame; Option 3)

**Status:** implemented and gated (`tools/b2_conformance.py`).

## Why

`schema_hash` is the **structure** leg of the frame triad. Pinning structure while leaving live
structure mutation ungoverned is incoherent. B2 makes post-construction structure mutation a
**governed, intent-bearing, receipted** act — without advancing the frozen M2.3 legend and
without forcing `schema_migrated` into the kernel-op vocabulary.

## The boundary (Governor ruling — Option 3)

Schema migration is **constitutional in consequence** (it mutates a frame leg) but is governed at
the **storage/frame layer**, not through the frozen kernel-op vocabulary:

- no new legend term; no `APPLICATION_OP`; no M2.4 legend advance; no kernel-op vocabulary change;
- explicit `intent` required (fail-closed refusal otherwise);
- a **schema-frame migration receipt** (storage-frame provenance, `op='schema_migrated'`) is
  emitted into the tamper-evident chain, recording `schema_hash` before/after, intent, the
  release anchor, and the drift flag;
- raw silent live `ALTER` outside this path is forbidden.

It is a **storage-frame provenance receipt, not a governance receipt in the `execute()` sense** —
there is no kernel gate/refuse; governance is the controlled single path + intent + receipt.

## Bootstrap vs live migration

- **Bootstrap** (`__init__` `CREATE` + `_migrate_m2_schema`): construction-time normalization of a
  DB *to* the release's pinned shape. Single-threaded, pre-sharing. A declared genesis/bootstrap
  remainder — not a live migration, not governed.
- **Live migration** (`migrate_schema`): the sole post-construction structure-mutation path.
  Runs under the single-writer lock (B4a), records before/after, emits the migration receipt.

## `schema_hash` anchor policy

`EXPECTED_SCHEMA_HASH` remains the **release** anchor; a migration does **not** move it. A migrated
deployment's live `schema_hash` diverges from the anchor, so `schema_frame_intact()` reports
**drift** (observe-only — never refuses), and the migration receipt **explains** the drift
(before/after + intent). Re-pinning the anchor is a deliberate later-release act.

## Invariants (do not regress)

1. The only hardcoded `ALTER` literal site is bootstrap (`_migrate_m2_schema`); the only dynamic-SQL
   execution sites are bootstrap-construction (`__init__`) and the governed `migrate_schema`.
2. `migrate_schema` requires intent and always emits a before/after migration receipt.
3. Startup fingerprint stays observe-and-report only; drift never refuses.
4. `law_hash` and `legend_hash` unchanged; `EXPECTED_SCHEMA_HASH` unchanged unless a release re-pins it.

## Out of scope (deferred)

Versioned migration tooling, rollback orchestration, multi-step migration planning, and automatic
anchor re-pinning remain future work. B2 provides the governed primitive (one receipted, intent-bearing
migration step), not a migration framework.
