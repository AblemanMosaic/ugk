# GRBSA Receipt + ResultEnvelope Core — Semantic Specification (G1)

**Semantic specification ONLY.** These two cores are *projections over existing UGK machinery*. G1
introduces **no second receipt/envelope implementation and no new runtime object**. The shared source
of truth for prose and gates is `core_mapping.json` (same directory); this document explains it.

## Receipt Core (closed, 6 fields) — "Why was the continuation admissible?"
Minted at admissibility time, before effect (NBER-1). Projection over `ugk.storage.store.Receipt`
(the constitutional receipt) and `ugk.scale.oracle.Receipt` (the scale lane receipt).

| Core field | Projects from (existing) |
|---|---|
| proposal   | Receipt.op, Receipt.parameters; scale.Receipt.op/agent/session |
| criteria   | Receipt.id_c_s, id_c_c, id_c_m, id_c_j (commitment-criteria ids) |
| evaluation | Receipt.h_s, h_c, h_m, h_j, h_r (per-commitment evaluation hashes) |
| authority  | Receipt.authority, warrant_id, law_hash |
| outcome    | Receipt.failed, mode |
| lineage    | Receipt.prior_receipt_hash, parent_h_r, semantic_hash; scale.Receipt.pos/prior_hash/produces_effects |

The core is **closed**: domains attach a keyed **Receipt Extension** (ExecutionReceipt, GateReceipt,
ProjectionReceipt, ExplainReceipt, AuditReceipt, BenchmarkReceipt, MigrationReceipt). No domain field
enters the core.

## ResultEnvelope Core (closed, 5 fields) — "What happened?" (symmetric, substrate-owned)
Produced by the continuation. Projection over the existing result shapes
(`ugk.testing.headless_runner.ScenarioResult` / `BatchResult`).

| Core field | Projects from (existing) |
|---|---|
| status        | ScenarioResult.passed; Receipt.failed |
| evidence_refs | ScenarioResult.checkpoint_hash; BatchResult.checkpoint_hashes |
| timing        | ScenarioResult.timing_ms |
| result_hash   | ScenarioResult.stream_hash; BatchResult.final_stream_hash |
| lineage       | ScenarioResult.receipt_delta; BatchResult.total_receipt_delta |

Structurally symmetric with the Receipt: closed core + keyed **Envelope Extension**
(GateResultEnvelope, ProjectionResultEnvelope, …). The envelope answers *what happened*; the receipt
answers *why admissible*. Result/outcome data lives ONLY in the envelope, never the receipt.

## Success semantics — in NEITHER core NOR either extension
Success is a **domain predicate applied over receipt+envelope**, not a stored field: Gate→anti-vacuity,
Projection→fidelity, Explain→non-invention, Execution→effect-under-authority. This is the structural
reason category collapse cannot occur (and why the same collapse cannot migrate into envelopes).

## Constitutional principles invoked (from the GRBSA roadmap)
- **NBER-1 (receipt-before-effect):** Proposal → Admissibility → Receipt → ResultEnvelope → Continuation.
- **Receipt Identity Principle:** behavioral equivalence is never inferred from / required to equal
  receipt-hash identity (the chain hash binds `ts`).
- **Receipt Sufficiency Principle:** equivalent admissibility + equivalent success semantics +
  equivalent lineage shape ⇒ constitutionally equivalent, regardless of implementation.

## Scope (G1)
Spec + manifest + two read-only gates. No runtime object, no behavior change, `law_hash` unchanged.
