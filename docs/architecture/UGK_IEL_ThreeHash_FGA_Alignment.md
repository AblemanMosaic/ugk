# UGK / IEL ↔ Three-Hash Rule + FGA — Alignment Cross-Walk

**Governed record:** ADR **AD-33** (UGK v0.1.0). **Status:** record-only, **frame-stationary**, no behavior change.
**Sources:** *The Three Hash Rule* (§17 states UGK instantiates it) and *Fractal Governance Architecture* (FGA).
**Purpose:** ground the next phase (MutationTransaction / deferred-commit) in the papers' vocabulary before any design.

This cross-walk maps the six concept-pairs the Governor named. It asserts no new law; it shows the UGK/IEL
runtime is a faithful — and in one respect stronger — realization of the two papers.

---

## M1 — ProtocolError vs REFUSE vs ADMIT

| Paper construct | Source | UGK / IEL realization |
| :-- | :-- | :-- |
| `δ = ADMIT ⟺ Adm(ρ,c,J,ε) = ⊤` | FGA §7 | `gate_admit` receipt — aggregation `F(D)=⊤` |
| `δ = REFUSE ⟺ Adm = ⊥` (fail-closed: REFUSE whenever `Adm ≠ ⊤`) | FGA §7, §15.5 | `gate_refuse` receipt + `GateRefusal` — a **constitutional** decision within a known root |
| **Protocol failure** — rejected *at the protocol layer, prior to admissibility evaluation*, distinguishable from a constitutional REFUSE | FGA §15.5 (missing jurisdiction) | **`ProtocolError`** (r96/r97) — malformed transition caught at preflight, **before** admissibility; distinguishable from `gate_refuse` by *type* |
| CRISIS — failure of **root disambiguation** (`∃ cᵢ≠cⱼ` both admitting `J`) | FGA §15.5 | **Out of scope** for single-root v0.1.0; noted frontier |

FGA's three-way split (ADMIT / REFUSE / protocol-failure) is exactly the distinction r96/r97 built. The kernel is a
**full FGA realization**: it emits receipts on *both* ADMIT and REFUSE (§7's preferred form, above the admit-only floor).

---

## M2 — Evaluator context ε

| Paper claim | Source | UGK / IEL realization |
| :-- | :-- | :-- |
| `Adm : P × C × J × E → {⊤,⊥}`; ε is the constitutionally qualified evaluator | FGA §4 | ε ↔ `authority` + `gate`/`AuthorityModel` + `governor_sig` |
| ε **implements** the decision procedure; its identity is a **provenance** fact in the witness family `π`, not a semantic input (deterministic constitution) | Three-Hash §7 "Evaluator as Implementation"; FGA Property 6 | UGK is a **deterministic constitution**: gate outcome is **evaluator-invariant**; ε is recorded as the receipt `authority` field |
| Even when outcome-invariant, ε stays load-bearing for issuance authority, attestation, auditability, accountability | FGA §6, Property 6 | ε carried on every receipt for exactly those four functions; determinism-sacred = the evaluator-invariance commitment |
| **Future evaluator context (frontier)** | — | ε currently binds to `authority` + `gate`/`AuthorityModel` + governor signature; **full** ε should eventually include kernel/build identity, the law/schema/legend frame, jurisdiction, phase/epoch, the policy/authority frame, verification level, and the decision-surface set |

---

## M3 — Decision surfaces D_i

| Paper construct | Source | UGK / IEL realization |
| :-- | :-- | :-- |
| `D = {D₁..Dₙ}`, `Dᵢ:(x,c,J,ε) → Rᵢ` — one surface per admissibility dimension | FGA §5.1 | Per-axis kernel checks: `D_s` (state/`H_s`), `D_c` (admissibility — gate + AuthorityModel + authority graph), `D_m` (meaning/`H_m`), `D_j` (locality/`H_j`), will/intent coverage (`WILL-S-06`) |
| `Adm = F(D)`, `F` the aggregation operator | FGA §5.1 | **Conjunctive** `F` (all surfaces must pass to admit) |
| Conjunctive ⇒ adding a surface can only **refuse** (monotone toward refusal) | FGA Property 3 | Holds — UGK's amendment discipline relies on conjunctive aggregation |
| Three-layer factorization: transition structure / decomposed evaluation / aggregation | FGA §5.1 | schema (receipt + committed fields) / per-axis surfaces / conjunctive admit |

The r96/r97 **preflight** checks are **protocol surfaces** (well-formedness), evaluated *before* the constitutional
surfaces — the structural correlate of M1's protocol-vs-constitutional split.

---

## M4 — Receipt commitments H_s / H_c / H_m / H_j / H_r / h_body

| Commitment | Question | Source | UGK / IEL realization |
| :-- | :-- | :-- | :-- |
| `H_s` | state | Three-Hash §6 | object identity/integrity commitment |
| `H_c` | admissibility | Three-Hash §7 | authority-graph + policy commitment |
| `H_m` | meaning | Three-Hash §8 | canonical-sense commitment (jurisdiction-stable) |
| `H_j` | locality | Three-Hash §9 | namespace/jurisdiction commitment (when phase-bound) |
| `H_r` | receipt **identity** | Three-Hash §4 | merkle root over `(H_s,H_c,H_m,H_j[+context])` |
| **`h_body`** | **whole-body integrity** | **UGK AD-28 / IEL-S-01** | **STRONGER than the paper's `H_r`** — domain-separated hash over **every** committed field, computed purely from stored values |

By **FGA Property 5** the receipt commits the trace vector componentwise (`R ~ Commit(D)`), so `H_s/H_c/H_m/H_j` are
the **cryptographic dual** of the decision-surface vector. `h_body` is UGK going *beyond* the papers: it operationalizes
the binding-verification / recoverability concern (Three-Hash §4.5) and FGA's "tamper-evidence is structural" (§6)
**at the field level**, detecting tampering of any field — not only the four-axis root. It is already law (IEL-S-01).

---

## M5 — Trace-vector evidence

| Paper construct | Source | UGK / IEL realization |
| :-- | :-- | :-- |
| Constitutional trace vector `D = (D₁..Dₙ)` — first-class, the commitment target, basis for differential evaluation | FGA §5.1 | per-axis verify outcome vector, committed in the receipt |
| `verify(R,C) → [(Domain, Result, ErrorCode)]` with codes from the error taxonomy | Three-Hash App. B/D | `D_s/D_c/D_m/D_j` outcomes + reason codes (ExpiredEdge, NamespaceNonMember, …) |
| Differential evaluation = comparing two trace vectors = which surfaces changed | FGA §5.1, Property 5 | **across releases:** a release-lineage *analogue* of trace-vector differential evaluation (an analogy, **not** an identity) — realized by the continuity-surface diff (B4 substrate/verification/codex change-confinement) |

---

## M6 — Transaction atomicity as preservation of a whole governed transition  *(bridge to the next phase)*

| Paper construct | Source | UGK / IEL realization & target |
| :-- | :-- | :-- |
| Governed transition `T = (ρ, J, E, v, δ, R, α)` — the **unit** of governance | FGA §3 | proposal → jurisdiction → evaluator → eval result → decision → receipt → amendment-eligibility |
| Constitutions may **separate** decision from execution; the admit is itself a transition whose receipt records the consequent state change | FGA §8.1 | UGK separates `gate_admit` (decision) from `effect()` (execution); admit + effect + success-receipt realize `T` |
| Atomicity = the **whole** `T` is preserved | FGA §3, §8.1 | a partial `T` (admit-without-effect, effect-without-success-receipt, admit-then-crash) is a **broken** transition that must not persist |

**Where r96/r97 left it, and what B must do:**

- r96/r97 sealed the **pre-admit (refusal) horizon** — no `δ` (admit) is written until the refusal horizon (protocol
  surfaces + the surfaces' refusal aggregation) is exhausted. *No admit before the refusal horizon is exhausted.*
- **MutationTransaction (phase B)** must seal the **post-admit horizon**: once `δ = ADMIT`, the admit + effect +
  success-receipt are **atomic** — if the effect or the success-receipt fails, the whole `T` rolls back, leaving the
  pre-transition state plus a **structural abort record**. The unit of atomicity becomes the **governed transition `T`**,
  not the individual `store.write()`.

This reframing is the design constraint the MutationTransaction work inherits: *the transition is the atom.*

**Realized — r99 / AD-34 (pilot).** The deferred-commit seam (`store.transaction()` + a depth guard in `store.write()`) is wired onto `migrate_schema()`: the schema ALTER, the migration receipt, and the terminal status commit together or roll back together, with the in-memory frontier restored on rollback and **no outer commit** persisting any side effect of a failed block. For this path, *the governed transition T is the atom.* Scope-bounded: pilot only — **not** global atomicity, and Invariant E is **not** yet formalized as law (it becomes law when the wiring covers the claim).

---

## Frame determination

**Frame-stationary — no law/schema move.** UGK already instantiates the papers (Three-Hash §17); the UGK receipt frame
is a **superset** of the paper's receipt (it adds `h_body` and the committed fields); `H_r` and the four axes match;
ADMIT/REFUSE match `gate_admit`/`gate_refuse`. No discrepancy in the alignment requires moving the committed frame.

- `law a3992e45` / `schema a49e520e` / `legend db3c177d` — **unmoved**; no amendment; ledger 11; registry 77; gates 91.

  > **Frame snapshot (point-in-time).** The pins above are the frame *as of this alignment analysis* (gates 91). The
  > authoritative live frame is `RELEASE.txt`. Since this analysis, the schema leg moved `a49e520e -> 20c78e18` at r128
  > (AD-51), carried by a law-stationary schema-leg amendment; law `a3992e45` and legend `db3c177d` remain unmoved. This
  > note does not change the analysis, which was frame-stationary at the time it was made.

## Recorded divergence (not a frame change, not acted on here)

The paper's §15.5 has a *protocol failure* emit a **structural-error receipt** (distinguishable from REFUSE). UGK emits
`protocol_error` receipts for most protocol violations (`kernel_internal`, `not_founded`, `undeclared`, `require_gate`,
`gate_exception`) — **but** the malformed-**input** subclass (non-dict `parameters`, non-string/empty `authority`,
bad `warrant_basis`/`authority_set`) uses **zero mutation** (Governor ruling a), because a non-string authority cannot be
safely written into a receipt. **Distinguishability — the architectural requirement — is satisfied.** The visibility gap
(malformed-input protocol errors leave only the raised exception, no durable receipt) is recorded as an **alignment
observation and a future option**, explicitly **not** a committed-frame change and **not** a behavior change in this ADR.
