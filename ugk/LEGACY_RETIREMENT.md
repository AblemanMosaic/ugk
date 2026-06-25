# Legacy Retirement Backlog

> Status as of M2.3p (end of M2.3 series).
> See ugk/store.py constants for the in-code classification:
> `M2_PRIMARY_RECEIPT_FIELDS`, `LEGACY_COMPAT_RECEIPT_FIELDS`, `LEGACY_ONLY_GATES`.

## Context

The M2.3 series completed the construction-side proxy-replacement program,
the verifier-side decision-procedure surface, and witness-based selective
disclosure. M2.3n executed the **Option B partial schema clean-break** —
classification plus safe-reader migration, not destructive removal.

Full retirement of the legacy CHC envelope and legacy `semantic_hash` chain
remains **deferred**. This document catalogs the work that would be required,
grouped by dependency tier. None of these items is authorized today; each
requires explicit Governor authorization and forms part of a coherent
retirement sequence.

## Tier 1 — Production-API migrations (gated by audit/API stability policy)

These touch surfaces that external consumers may depend on. Each is a
production-visible breaking change.

**(a) `GovResult.receipt_hash`**
- Current: `agent.GovResult.receipt_hash: str` populated from `stream_hash()`.
- Migration: add `h_r: str` field to `GovResult`; populate alongside `receipt_hash`.
- Cascading edits: `ugk/agent.py`, `ugk/broker.py`.
- Constraint: callers consuming `GovResult.receipt_hash` (in `migration_gate.py` and
  any external code) keep working until the field is removed.

**(b) `audit.py` log format**
- Current: emits `"semantic_hash": receipt.semantic_hash` in JSON audit log records.
- Migration: add `"h_r": receipt.h_r` alongside (additive, non-breaking).
  Later, after consumers migrate, remove the `semantic_hash` field.
- Production-visible: log consumers (SIEM, analytics) must update.

**(c) `store.stream_hash()` semantics**
- Current: returns the legacy chain tip (= last receipt's `semantic_hash`).
- Migration: add `store.m2_stream_hash()` returning the last receipt's `h_r`.
  Existing `stream_hash()` continues until deprecation milestone.
- Cascading: `agent.py`, `broker.py`, `migration/abletools.py`, anywhere
  external code calls it.

## Tier 2 — CHC-envelope migrations (gated by retirement of legacy CHC layer)

These re-anchor or retire gates whose semantic purpose is the legacy
CHC envelope or DM-S-03 tamper-evidence. Each gate would need either
a clean M2 analog or explicit retirement authorization.

**(d) `chc_gate.py` (CHC-S-01..03)**
- Current: validates CHC envelope structure on every receipt
  (`state_hash`, `prior_receipt_hash`, `semantic_hash` length and presence).
- Options:
  - Re-anchor: validate THR binding structure instead (overlap with
    `binding_gate`; might make `chc_gate` redundant).
  - Retire: remove from suite once CHC envelope is no longer populated.

**(e) `chain_gate.py`**
- Current: validates chain linkage via `semantic_hash` chaining:
  `receipts[i-1].semantic_hash == receipts[i].prior_receipt_hash`.
- Options:
  - Re-anchor: validate `receipts[i-1].h_r == receipts[i].parent_h_r`.
    The M2 chain is structurally analogous.
  - Retire: remove if `binding_gate`'s H_r round-trip covers the
    equivalent invariant.

**(f) `rugpull_gate.py`**
- Current: DM-S-03 envelope-field tamper-evidence
  (`dm_s03(state_hash=..., parent=..., ...)`).
- Options:
  - Re-anchor: M2-leaf tamper-evidence — alter each c_i input and
    confirm H_s/H_c/H_m/H_j changes.
  - Retire: superseded by EV-W-02 (witness tamper detection).

**(g) `nonrepudiation_gate.py`**
- Current: same DM-S-03 envelope-field tamper-evidence pattern.
- Same options as (f).

**(h) `testing/headless_runner.snapshot_at`**
- Current: `r.semantic_hash == checkpoint_hash` lookup.
- Migration: re-anchor to `r.h_r == checkpoint_hash` lookup.
- Coupled to: `store.stream_hash()` output format (Tier 1 item c).
  Must migrate together.

## Tier 3 — Schema field + property removal (gated by Tiers 1 + 2 complete)

These actually delete fields, requiring all readers above to have been
migrated first.

**(i) SQL columns**
- Drop columns: `state_hash`, `prior_receipt_hash`, `semantic_hash`.
- Migration: ALTER TABLE on existing receipt databases; existing
  databases would need offline migration.

**(j) Receipt dataclass fields**
- Drop fields: `state_hash`, `prior_receipt_hash`, `semantic_hash`.
- `LEGACY_COMPAT_RECEIPT_FIELDS` in store.py becomes empty (or removed).

**(k) `Receipt.receipt_hash` property**
- Drop the property (returns `semantic_hash`, which no longer exists).
- Callers (migration_gate.py via GovResult) must already use `h_r`
  per Tier 1 (a).

**(l) Legacy chain machinery in store.py**
- Remove `_prior_hash` tracking, `_state_hash` import, `dm_s03` import,
  `canonical_json as _cj` import — all from `ugk/binding.py` (forbidden
  file, but its imports become safe-to-delete from store.py side).
- Genesis seed `GENESIS = "0" * 64` reference may also be re-anchored.

**(m) `LEGACY_ONLY_GATES` in store.py**
- Once chc_gate / chain_gate / rugpull_gate / nonrepudiation_gate have
  been re-anchored or retired (Tier 2), this set becomes empty or
  removed.

## Dependency graph

```
Tier 1 (Production APIs)
  (a) GovResult.receipt_hash ────┐
  (b) audit.py log format        │
  (c) stream_hash() variants ────┤
                                  │
Tier 2 (CHC-envelope gates)       │
  (d) chc_gate retire/re-anchor   │
  (e) chain_gate retire/re-anchor │
  (f) rugpull_gate retire         │
  (g) nonrepudiation_gate retire  │
  (h) headless_runner.snapshot_at─┘
                                  │
                                  ▼
Tier 3 (Schema removal)
  (i) SQL columns
  (j) Receipt fields
  (k) receipt_hash property
  (l) Legacy chain machinery
  (m) LEGACY_ONLY_GATES classification removal
```

## Authorization requirements

Each tier requires a separate Governor decision:

- **Tier 1** authorization: "production API stability policy permits
  additive then breaking changes to GovResult, audit logs, and
  stream_hash."

- **Tier 2** authorization (independent for each gate): "legacy CHC
  envelope / DM-S-03 tamper-evidence / legacy chain integrity is no
  longer a required conformance witness." Each ratified gate-retirement
  reduces the conformance-gate suite by one.

- **Tier 3** authorization: "Tier 1 and Tier 2 migrations have all
  ratified; full schema clean-break is now safe."

## Per-tier expected `law_hash` movement

- Tier 1: no `law_hash` movement (production API changes are runtime).
- Tier 2: no `law_hash` movement (gate retirements are roster changes).
- Tier 3: no `law_hash` movement (Receipt schema is runtime, not
  constitutional). `law_hash` is set by `invariants.py` content; the
  schema fields live in `store.py`.

## Out of scope of this catalog

- Phase M2.4 work (AbleTools integration).
- Phase M2.5 work (CPVM adoption).
- New constitutional declarations (would move `law_hash` and require
  separate authorization).
- Field additions (additive changes to Receipt; not retirement).

---

End of catalog. Updates to this document should be made as part of any
future subphase that addresses one of the above items, with a brief
note indicating which item was completed and on what date.
