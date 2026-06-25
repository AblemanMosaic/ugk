# UGK v0.1.0 — Batching / Performance Analysis (analysis only — nothing implemented)

**Authorization:** analysis only. Implement nothing unless a clearly-safe **class-A**
candidate preserves receipt order, prior_hash, deterministic replay, NBER-1, fail-closed,
and rollback. **Result: no class-A candidate found. Nothing implemented.**

## Governing constraint (from the substrate, measured)

Each receipt's `semantic_hash` is `dm_s03(state, parent=prior_receipt_hash, intent, …)`
— it **binds the prior receipt's hash**. Receipts therefore form a strict hash chain in
which **order is identity**: reordering or coalescing receipts changes every downstream
`semantic_hash` and the `stream_hash` tip. NBER-1 writes the success receipt *before* the
effect (`kernel.py` step 6 before step 7). Any batching that defers, reorders, or merges
receipt emission breaks chain identity and/or record-before-effect. This single fact
disqualifies most candidates.

Baseline timings (already fast): construct+ceremony+open 18.6 ms · govern 8.5 ms ·
verify_stream_hash 2.2 ms · warrant write 0.11 ms.

## Classification (A=safe structural · B=atomic-tx only · C=unsafe, obscures receipts · D=not worth it)

| Candidate | Class | 10-question verdict (order / prior_hash / fail-closed / replay / NBER-1 / one-receipt-per-item+envelope / rollback) |
|---|---|---|
| **Receipt writes** | **C** | Order *is* identity; coalescing breaks prior_hash chain & replay; NBER-1 requires per-effect timing. Unsafe — obscures receipts. |
| **Warrant writes** | D | Already 0.11 ms. No meaningful gain; batching adds a partial-failure surface. |
| **Conformance gate execution** | D | Dev-time only; 78 gates run in ~3 s. Parallelism risks shared-genesis races; not worth it. Not a production path. |
| **Verification passes** | D | `verify_stream_hash` is O(n) by design (UL-S-05), already 2.2 ms; `from_checkpoint` O(Δ) path already exists. |
| **CLI batch operations** | C | A "batch govern" would emit one receipt per op (correct) but tempt a single merged receipt (incorrect). No safe structural batch. |
| **Archive digest computation** | D | One-shot at release; 158 files hash in <1 s. No runtime path. |
| **Repeated kernel construction** | D | 18.6 ms dominated by ceremony+open (genesis read, identity); not batchable without changing identity-binding semantics (out of scope). |
| **Ceremony/open-session** | C | Each opens a session boundary receipt; coalescing would drop session-boundary granularity (audit loss). |
| **ρ fixture execution** | D | Dev-time; dormant capability; no production batching value. |
| **A1 verification** | D | Per-effect, dormant; batching would obscure the per-effect admissibility decision. |
| **Tree digest calculation** | D | Release-time one-shot. |

## Why no class-A exists

A class-A (safe structural) batch would have to emit **one receipt per item AND preserve
their individual order and prior_hash links** — i.e. it would not actually coalesce the
chain, only wrap it. The recommended envelope pattern (per-item receipts + one batch
envelope receipt that does *not* replace them) is admissible in principle, but:
- it adds machinery and a partial-validity fail-closed path to a system already sub-20 ms;
- the only candidate where an envelope adds insight (CLI batch govern) has no current
  multi-op CLI workload to justify it.

So the honest verdict is **D/C across the board for v0.1.0**: the system is already fast,
and the receipt chain's order-is-identity property makes receipt/session batching unsafe
(class C) rather than merely unhelpful. **No implementation is warranted or authorized.**

## If batching is ever revisited (recommended pattern, not implemented)
Keep per-operation receipts; add an *optional* batch-envelope receipt that references —
never replaces — the individual receipts; require atomic effects and fail-closed on
partial invalidity; record deterministic batch order. Re-validate full stack and mint
separately, as a substrate change.
