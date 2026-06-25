# B1 — Epoch Seal / Retention (storage-frame; governed, fail-closed)

**Status:** implemented and gated (`tools/b1_conformance.py`). Governed at the storage/frame layer
(consistent with B2): no kernel-op, no legend term, no `APPLICATION_OP`, **no schema change**, and
no change to receipt-hash or `stream_hash()` semantics.

## Why

The receipt chain grows unboundedly. B1 lets a sealed historical **prefix** be pruned while the
chain's tamper-evidence is preserved — because the chain already makes any receipt's `semantic_hash`
a **cumulative commitment** to its entire prefix.

## Concepts (commitment vs event)

- **Seal commitment `S`** (cryptographic): `S = B.semantic_hash` for the boundary receipt `B` (the
  last receipt of the sealed prefix). Via the chain (`semantic_hash = dm_s03(parent=prior, …)`), `S`
  already commits to every receipt from genesis through `B`. **`S` is the verification anchor.**
- **Seal event** `epoch_sealed(S)` (provenance) and **prune event** `epoch_pruned(S)`
  (provenance record of a governed destructive act): these *describe* the operation. They are
  **not** the anchor — the anchor is the value `S`.

## Operation: `seal_and_prune_epoch(seal_hash=S, intent)`

Storage-frame governed, destructive, fail-closed, under the single-writer lock (B4a):

1. **Refuse-before-mutation:** missing `intent`, unknown `S`, or a frontier that does not chain from
   `S` → refuse, delete nothing.
2. Append `epoch_sealed(S)` then `epoch_pruned(S)` provenance receipts **at the tail**.
3. Record `tip_before_prune = stream_hash()`.
4. **Prune:** `DELETE FROM receipts WHERE receipt_id <= boundary` (the prefix only). The tail epoch
   receipts (`receipt_id > boundary`) are untouched.
5. Record `tip_after_prune` and assert the post-conditions (fail-closed): `tip_after_prune ==
   tip_before_prune` **and** `verify_from_seal(S)`.

## Verification across the seal: `verify_from_seal(S)`

Anchors on the commitment **value** `S` (the boundary receipt is gone) and verifies the retained
chain forward: the first retained receipt's `prior_receipt_hash` must equal `S`. A sealed/pruned
store is, by design, **not** expected to pass genesis-anchored `verify_stream_hash()` — its anchor is
the seal, not genesis.

## Invariants (proved by `tools/b1_conformance.py`)

1. **Tip preserved across the prune:** `tip_after_prune == tip_before_prune`. Pruning is
   **observationally equivalent to retaining the prefix** — deleting the prefix cannot move the tip,
   because the tip is the tail epoch receipt, which the deletion never touches. *This is the real
   retention invariant: not merely "the frontier verifies," but "the externally visible commitment is
   unchanged by pruning."*
2. **Retained chain verifies from the seal:** `verify_from_seal(S)` holds after pruning.
3. **Anchor is the value `S`, not a receipt:** the boundary receipt is pruned, yet verification holds.
4. **Prefix actually pruned** (receipt count drops by the sealed count).
5. **Fail-closed:** empty intent / unknown `S` refused with zero mutation.
6. **Frame triad + legend unmoved; `schema_hash` unchanged** (no schema change).

## Proof of no chain-integrity loss (sketch)

- *Frontier tamper-evidence preserved:* the retained suffix verifies link-by-link from anchor `S`.
- *Prefix committed:* `S` is a SHA-256 cumulative commitment to the pruned prefix; under collision
  resistance, no different history reproduces `S`.
- *Anchor authenticity:* `S` is recorded in the retained `epoch_sealed`/`epoch_pruned` receipts,
  themselves in the verified frontier.
The explicit, bounded tradeoff: pruning trades the ability to *re-derive* the prefix for a
*cryptographic commitment* to it. Nothing in the frontier loses tamper-evidence.

## Classification (A3 register, rows 24–27)

`verify_from_seal` = claim; `epoch_sealed`/`epoch_pruned` = provenance; `seal_and_prune_epoch` =
governance (destructive authorized act).

## Deferred (B4b territory — not in B1)

Multi-epoch seal meta-chains, per-jurisdiction/per-epoch chains, and cold-storage retention of the
pruned prefix (so it stays re-derivable) remain deferred. B1 provides the single governed
seal+prune+verify primitive on the existing `receipts` table.
