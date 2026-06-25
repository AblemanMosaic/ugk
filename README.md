# UGK — Universal Governance Kernel

[![Gates](https://img.shields.io/badge/gates-119%2F119_(hardened)-brightgreen)](ugk/conformance/run_gates_batch.py) [![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org) [![stdlib-only](https://img.shields.io/badge/dependencies-stdlib%20only-green)](pyproject.toml) [![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

**Receipt-before-effect infrastructure for constitutional computing.**

```
intent + warrant + trace -> admissibility -> receipt -> effect or refusal
```

Governance begins where admissibility becomes a first-class computational object. UGK is a constitutional computing substrate for Python applications: governance is *constitutive* of operations — not a report written afterward. Every governed operation emits a cryptographically-chained receipt *before* executing. If the receipt cannot be written, the operation does not proceed. The chain is the governance, not documentation of it.

---

## Creator's Note

UGK began with a realization: bespoke systems governance suffered from the same
failure modes that memory management, cryptographic primitives, and networking
stacks encountered before systems engineers recognized they belonged at the
substrate level — universalized into a coherent applied theory. When a concern
recurs across enough independent systems, it stops being an application problem
and becomes an infrastructure problem.

This project started with one question: what would governance look like if it
were part of the execution loop itself, rather than a report written after the
operation had already happened?

Most systems treat governance as observation. An event occurs, a log is written,
a receipt is generated, and an auditor can later reconstruct the story. There is
value in that. But observation is not constraint. A record of an action is not
the same thing as a condition for the action.

UGK was built around a different premise: governance should be *constitutive*.
Removing it must change what the system is capable of doing. Every operation
through the kernel emits a cryptographically-chained receipt *before* executing.
If the receipt cannot be written, the operation does not proceed. Receipts are
preconditions, not observations. The chain is not documentation of governance —
it is one of the mechanisms by which governance exists.

As the project evolved, a second problem became impossible to ignore. Many
systems produce the *appearance* of governance — policies exist, logs exist,
approvals exist — while leaving the underlying authority structure ambiguous.
It remains unclear what was actually authorized, what was merely observed, and
what was simply assumed.

UGK addresses this by separating three independent questions:

> **Did this happen?** — the receipt chain  
> **Was it authorized?** — the warrant  
> **Was it intended?** — the intent declaration

These are treated as distinct claims because they are distinct realities. A
system that cannot tell the difference cannot honestly describe its own posture.

This failure mode is **authority laundering**: authority laundering occurs when
evidence of governance is mistaken for governance itself. A signature,
approval, policy label, audit event, or institutional actor becomes *authority*
simply because it appears in the record. UGK rejects that shortcut. Authority in
the kernel is not inherited from the presence of evidence. It is derived from
admissibility under declared governance rules. Evidence may support authority.
It does not become authority by assertion.

The kernel is intentionally narrow in scope. It is not a policy engine, an
access-control framework, or a compliance product. It does not decide what
should be governed, who should hold authority, or which rules matter in a
particular deployment. Those questions belong to operators, institutions, and
communities.

What UGK provides is a *constitutional computing* substrate: a composable,
self-describing minimal set of mechanisms for making authority, intent,
admissibility, and provenance structurally visible and cryptographically
falsifiable.

*If a system is governed, it should be able to prove it — both in the present
moment and after the fact.*

*If it cannot prove it is governed, it should be able to say so honestly.*

---
## Where most systems fall short

The **Constitutional Software Analysis (CSoftA)** corpus classifies governance
mechanisms across 80 production systems into three states:

| State | Meaning |
|---|---|
| **ACTIVE** | Governance is constitutive — the check failing causes the operation to fail |
| **CRYSTALLIZED** | Governance exists and is evaluated, but the operation proceeds regardless |
| **ABSENT** | No governance mechanism exists for this operation family |

Of 80 systems analyzed, 35 have at least one ACTIVE operation family. 45 are
highest-state CRYSTALLIZED: governance capable, non-operative by default.

The pattern is consistent: governance defaults to optional. Audit logging
present but not mandatory. Policy enforced in development, bypassed in
production. Approval required in the happy path, irrelevant on the error path.

UGK is designed so that CRYSTALLIZED is not a reachable state. The kernel ships
`UNINITIALIZED` — fail-closed, unusable for production until explicitly founded
via the key ceremony. Once `ACTIVE`, governance is structurally load-bearing:
the three-disjunct receipt (trace + authorization + will) is written *before*
the effect, or the effect does not execute.

`GovernancePosture.compute(kernel)` produces a content-addressed posture object
with a computable φ scalar (0.0 = fully constitutive, 1.0 = fully ceremonial)
and an ALT §8 matrix covering 13 governance dimensions. `ugk posture` surfaces
this via CLI. The governance posture is not a claim — it is a verifiable artifact.

→ CSoftA corpus: [github.com/ableman-constitutional-systems/csofta](https://github.com/ableman-constitutional-systems/csofta)

---
## What this gives you

| Surface | What it provides |
|---|---|
| **Receipt chain** | Append-only, hash-linked, tamper-evident. Receipt emitted *before* effect (NBER-1). |
| **Warrant system** | Constitutional justification (`warrant_basis`) on every admitted operation. |
| **Will layer** | Declared intent coverage — `IntentDeclaration` + `R_int` fixpoint (ALT §11 disjunct c). |
| **Authority model** | Configurable compliance posture: `alt_prevention`, `alt_trace`, `trace_only`, `custom`. |
| **Governance posture (CGP)** | Computable φ scalar, three-disjunct coverage, ALT §8 matrix — content-addressed and sealable. |
| **Deployment charter** | Runtime identity injection via `ugk charter`. Fail-closed without it. |
| **Audit surface** | Read-only access to full receipt chain, scope history, warrant archive. |
| **CSIL / GTI** | 100-entry canonical semantic vocabulary. Queryable by integer across all tiers. |
| **Provenance scope** | Explicit session scope declarations. Replay inadmissibility by scope boundary. |
| **Successor lineage** | Cryptographic key rotation with verifiable succession proof. |
| **CLI** | `ugk charter` · `ugk posture` · `ugk govern` · `ugk health` · `ugk explain` · `ugk constitution` · `ugk status` |

---
## Quick start

```bash
pip install .
```

**1. Charter a new deployment** — establishes the governance identity:

```bash
ugk charter --pubkey <your-ed25519-pubkey-hex> \
            --phase-code "my-deployment-v1"    \
            --authority-model alt_trace
```

Creates `genesis/GENESIS_KEY.pub` and `genesis/DEPLOYMENT_MANIFEST.json`.
The kernel is fail-closed until chartered.

**2. Govern an operation:**

```python
from ugk.kernel import GovernanceKernel
from ugk.schema import GOVERNANCE_OPS

GOVERNANCE_OPS["analyze_document"] = {
    "description": "Analyze a document",
    "authority":   "agent",
    "tier":        2,
}

k = GovernanceKernel()
k._ceremony()
k.open_session()

receipt = k.execute(
    op="analyze_document",
    authority="agent-001",
    parameters={"doc_id": "doc-42"},
    warrant_basis=[1027],          # LEGEND-S-01: constitutional justification
)
print(f"Receipt: {receipt.semantic_hash[:16]}…")
print(f"Chain intact: {k.store.verify_stream_hash()}")
```

**3. Check posture and verify:**

```bash
ugk posture                          # ALT §8 matrix, φ score, disjunct coverage
ugk health --run-gates structural    # fast smoke test
ugk verify                           # read-only chain integrity
```

See [`examples/basic/governed_session.py`](examples/basic/governed_session.py) for a complete walkthrough.

---
## Does this apply to my domain?

UGK ships domain mappings and reusable governance patterns:

- **Domains:** [finance](docs/domain-mappings/finance.md) · [healthcare](docs/domain-mappings/healthcare.md) · [government](docs/domain-mappings/government.md) · [infrastructure](docs/domain-mappings/infrastructure.md) · [logistics](docs/domain-mappings/logistics.md)
- **Patterns:** [audit-critical workflows](docs/patterns/audit-critical-workflows.md) · [irreversible operations](docs/patterns/irreversible-operations.md) · [multi-party authorization](docs/patterns/multi-party-authorization.md) · [delegated authority](docs/patterns/delegated-authority.md) · [distributed coordination](docs/patterns/distributed-coordination.md) · [high-consequence execution](docs/patterns/high-consequence-execution.md) · [regulated recordkeeping](docs/patterns/regulated-recordkeeping.md)

## Orientation: terminology and where to look

- **Glossary** — [`GLOSSARY.md`](GLOSSARY.md): fast term lookup (what a term is, what it is *not*, where truth lives). Generated from `GLOSSARY.json`.
- **Subsystem navigation** — [`IMPLEMENTATION_CODEX.md`](IMPLEMENTATION_CODEX.md): source-cited, claim-ceilinged map of named subsystems.
- **Invariant taxonomy** — [`INVARIANT_TAXONOMY.md`](INVARIANT_TAXONOMY.md): every invariant by semantic family, subsystem, frame role, gate, and source refs (construction lane shown only as provenance).
- **All docs** — [`docs/index.md`](docs/index.md): generated index of every UGK document, grouped and linked.
- **Self-describing CLI** — `ugk explain <invariant | gate | CSIL-integer>` resolves any constitutional term on demand.

### Terminal-outcome lattice

| outcome | status | emission condition |
|---|---|---|
| ADMIT | live | default permit, committed under receipt |
| REFUSE | live | gate refusal (fail-closed) |
| STRUCTURAL_ERROR | live | protocol / structural fault |
| DEFER | live | requires a HELD continuation record |
| BRIDGE | live | opt-in; valid BRIDGE-BINDING surface verified at emit |
| CRISIS | reserved | not emittable at this release |

### Where truth lives

| concern | source of truth |
|---|---|
| law (invariants) | `ugk/invariants.py` |
| schema | receipt schema hash · `ugk/storage/store.py` |
| legend | `ugk/storage/binding.py` |
| generated codex | `ugk/codex/CODEX.md` |
| navigation | `IMPLEMENTATION_CODEX.md` |
| glossary | `GLOSSARY.md` (generated) |
| release state | `RELEASE.txt` · publish manifest |
| continuity | `tools/grbsa/proof_model_b.py` · attestation |

### Failure semantics (distinct, do not collapse)

| signal | meaning |
|---|---|
| ProtocolError | malformed / invalid governance input (e.g. a float at the CK-CANON boundary) |
| REFUSE | a gate decided against the operation (fail-closed) |
| STRUCTURAL_ERROR | protocol / structural fault, committed as a terminal outcome |
| refuted | a verification clause failed (e.g. BRIDGE-BINDING) |
| missing | a required surface / record is absent → fail closed |
| not-established | a gate could not establish its claim (e.g. unfounded grundnorm) — *not* a failure |
| stale | a generated artifact drifted from its source (a freshness gate fails) |

### If you are changing X

| changing | inspect | expect frame move | run |
|---|---|---|---|
| an invariant | `ugk/invariants.py` + an ADR | law moves (amendment) | full suite + `certify_release.py` |
| the schema | `ugk/storage/store.py` | schema moves | `schema_hash_conformance.py` + certify |
| a conformance gate | `ugk/conformance/` | none | that gate + `run_gates_batch.py` |
| docs / glossary | the generator + cited source | none | the freshness gates |

## What governed execution looks like

Every governed operation emits a cryptographically-chained receipt *before* the effect. Illustrative receipt shape:

```json
{"op": "...", "terminal_outcome": "ADMIT", "law_hash": "1a205e27...", "h_body": "...", "prev": "..."}
```

When a gate refuses, the operation fails closed — the refusal *is* the governed outcome, and the effect does not happen:

```
ugk.kernel.GateRefusal: op='...' reason='...'
```

See it for real:

- minimal end-to-end call: `python examples/governed/a1_example.py`
- application ops: `python examples/governed/application_ops_example.py`
- fail-closed boot: run any Tier-2 op on an unfounded tree -> `GovernanceNotFounded`

## CLI reference

| Command | Description |
|---|---|
| `ugk attest` | Return 3+1 hash attestation proof |
| `ugk authority-model` | Show or set the authority model |
| `ugk charter` | Establish a governance deployment identity (founding constitutional act) |
| `ugk constitution` | Show constitutional frame (law_hash, legend_hash, authority model) |
| `ugk explain` | Explain a concept, gate, invariant, or CSIL integer |
| `ugk govern` | Execute a governed operation through the kernel |
| `ugk harden` | Establish the Grundnorm read-only protection posture (deliberate, recorded deployment act; sets protected modules to 0o444 and writes a deployment-state establishment record into genesis_dir, which UL-G-01 integrity then verifies against) |
| `ugk health` | Full system health check (chain + posture + optional gate compliance) |
| `ugk keygen` | Generate a fresh Ed25519 keypair |
| `ugk posture` | Show Constitutional Governance Posture (ALT section 11 posture vector) |
| `ugk status` | Show kernel status snapshot |
| `ugk verify` | Verify receipt chain integrity |

Use `ugk help <verb>` for parameter details.

---
## Architecture

Every governed operation produces a **three-disjunct receipt** *before* the effect executes:

| Disjunct | Carried by | Proves |
|---|---|---|
| (a) Trace | Receipt chain · `session_dkn` (NBER-1) | This happened and is attributable |
| (b) Authorization | `warrant_id` → `DecisionWarrant` | This was constitutionally admissible |
| (c) Will | `intent_ref` → `IntentDeclaration` | This was declared as intended |

**Three independent continuity problems — CHC, DKN, CSH:**

The conventional cryptographic stack answers integrity and authorship. UGK
extends it to address three independent continuity problems that conventional
approaches leave open:

| Layer | Question | Primitive |
|---|---|---|
| **CHC** — Cryptographic Homological Compilation | *What exists?* State identity, semantic binding, admissibility — independently verifiable across the same artifact | `semantic_hash` = SHA-256(state ‖ intent ‖ authority ‖ custody ‖ context …) |
| **DKN** — Distributed Knowledge Network | *Which semantic regime does it belong to?* Binds artifacts to explicit governance contexts — prevents silent drift across authority boundaries | `session_dkn` = SHA-256(mosaic_root:phase_code:session_id) |
| **CSH** — Constitutional Semantic Hash | *Did its meaning persist?* Quorum attestation over the constitutional frame — proves the governance agreement itself was continuous, not just the data | `law_hash` = SHA-256(invariants.py) · quorum over constitutional hash |

**Session identity** binds every receipt to its governance context:

```
session_dkn = SHA-256( mosaic_root : phase_code : session_id )
                       WHO                WHAT         WHICH
              (governor key)   (deployment type)  (session UUID)
```

**Constitutional frame** is content-addressed and carried on every receipt:
- `law_hash` — SHA-256 of `ugk/invariants.py`
- `legend_hash` — SHA-256 of the LEGEND vocabulary

A receipt chain is **self-verifying from artifacts alone**. No live kernel required.

**Compliance postures** (`ugk charter --authority-model`):

| Preset | `require_gate` | `require_warrant` | `require_intent` | Claim |
|---|---|---|---|---|
| `alt_prevention` | ✓ | ✓ | ✓ | ALT §11 Prevention Theorem — φ=0 target |
| `alt_trace` | ✓ | ✓ | — | Trace + causal; will vacuous |
| `trace_only` | — | — | — | Receipt chain only |
| `custom` | caller | caller | caller | Deployer-declared |

---
## Constitutional reference

### Invariants

**87 invariants** · **70 ADRs**, grouped by semantic classification. The construction lane (`introduced_in`) is retained as provenance and shown by `ugk explain <id>`; it is build history, not semantic standing.

| Classification | Count | Subsystems | Examples |
|---|---|---|---|
| `ABI_CONFIG` | 5 | CM, EH | `CM-DIM-01`, `CM-GS-01`, `CM-GS-02` +2 |
| `DOMAIN_PHYSICS` | 55 | ADV, ALT, ATLAS, AUDIT, BRIDGE, CGP, CHARTER, CHC +20 | `ADV-S-01`, `ALT-I-01`, `ALT-I-03` +52 |
| `MIXED` | 27 | ALT, AMD, ATLAS, AUDIT, CGP, CHARTER, CM, CSIL +10 | `ALT-I-02`, `ALT-I-04`, `AMD-S-01` +24 |

Invariant IDs span **36 subsystems** (the ID prefix encodes the governed area): `ADV`, `ALT`, `AMD`, `ATLAS`, `AUDIT`, `BRIDGE`, `CGP`, `CHARTER`, `CHC`, `CM`, `CR`, `CSIL`, `CTR`, `DCAP`, `DEFER`, `DKN`, `DM`, `DW`, `EFFECT`, `EH`, `ESA`, `GK`, `IEL`, `LEGEND`, `NS`, `PED`, `PERSIST`, `RECON`, `SCOPE`, `SRSA`, `SSA`, `SUCC`, `SUM`, `TO`, `UL`, `WILL`.

> Provenance note: each invariant also carries `introduced_in` — the build lane that introduced it (e.g. `phase1`, `bridge-binding-law`). That is historical evidence for continuity, not the ontology of the system; navigate by classification and subsystem above.

### LEGEND — Canonical Semantic Integer Layer

**101 entries** across 7 tiers:

| Tier | Count | Range |
|---|---|---|
| `invariant` | 32 | 1001+ |
| `dimension` | 12 | 2001+ |
| `op`        | 8 | 3001+ |
| `vocab`     | 36 | 4001+ (SSA verbs, jurisdictions, meta-governance) |
| `meta`      | 6 | 6001+ (CSIL/GTI self-description) |
| `warrant_result` | 5 | 9001+ |

### Gate suite

**119 gates**

- `structural`: 21 gates
- `unit`: 4 gates
- `integration`: 14 gates
- `conformance`: 80 gates

### Build pins

```
invariants_pin:  1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65
LEGEND_HASH:     db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7
governor_pubkey: GOVERNOR_KEY_UNSET__RUN_UGK_CHARTER
mosaic_root:     1d353b9ce31dba9a4157653ce2069b7fb626341b2e0f0e016483b81976591f83
phase_code:      ugk-substrate
```

---
## Development

```bash
make test          # full gate suite (119 gates)
make readme        # regenerate this README
python verify_release.py   # AUTHORITATIVE full-posture check (cross-platform): invariants_pin + LEGEND_HASH + 119/119 gates
./verify_release.sh        # POSIX convenience wrapper around `python verify_release.py`
```

**Understand the constitutional surface before contributing:**
```bash
ugk explain LEGEND-S-01    # invariant by ID
ugk explain 3003           # CSIL integer → op name
ugk explain dkn_gate       # gate by name
ugk constitution           # active law_hash, legend_hash, authority model
ugk posture                # live φ scalar, disjunct coverage, ALT §8 matrix
```

**Generate a keypair for a new deployment:**
```bash
ugk keygen --write-secure /path/to/key.json   # POSIX private key at 0o600; Windows fails closed
ugk charter --pubkey <hex> --phase-code "my-deployment-v1" --authority-model alt_trace
```

Note: `make test` runs `python -m ugk.conformance.run_gates_batch` from the project
root. The `-m` flag adds the current directory to `sys.path` — no separate install
required for development. A bare `make test` (or `ugk-gates`) on an un-hardened tree
reports `118/119 passed | 0 failed | 1 not-established` — the
Grundnorm read-only posture is *deferred, not failed* (exit 0). Run `ugk harden` first,
or use `python verify_release.py` (authoritative, cross-platform; `./verify_release.sh` is a
POSIX wrapper around it), for the canonical `119/119`.

`snapshot_fast()` also reports `crypto_profile`. The stdlib-only vendored Ed25519 backend
is surfaced as `reference_non_constant_time`; production deployments should bind signing to
a hardened constant-time backend or external signer.

---
## Contributing

- New invariants require a bound `ArchitecturalDecision` in `ugk/adr.py` — state context, decision, alternatives, consequences, and name the bound invariants explicitly. A change without an ADR is a change without a rationale.
- Changes to `ugk/invariants.py` change `law_hash` — intentional; update `RELEASE.txt` with the new `invariants_pin`
- Changes to the LEGEND (`ugk/binding.py`) change `LEGEND_HASH` — same
- Changes to `ugk/kernel.py` (Grundnorm layer, 444) require clear justification. The kernel is intentionally small and conservative.
- All patches must pass the full gate suite **at current count** before merge — additions must also add corresponding gates
- Run `ugk explain <id>` to understand any invariant or gate before modifying it
- Regenerate the README after any change: `python readme_gen.py` — committed README.md must match `--check`

Open questions about the underlying theory (ALT temporal-PROV, SCIT/GTI full
integration, A1 set-valued authority) are tracked in the roadmap. Contributions
addressing open theorems are welcome with a precise theorem statement and a
corresponding ADR if the contribution changes the kernel.

---
## Research

UGK is developed alongside the **Constitutional Software Analysis (CSoftA)**
corpus — 80 constitutional analyses of production systems (Vault, Kubernetes,
PostgreSQL, OPA, GitHub Actions, Kafka, and others) classifying governance
mechanisms as ACTIVE, CRYSTALLIZED, or ABSENT.

- CSoftA corpus: [github.com/ableman-constitutional-systems/csofta](https://github.com/ableman-constitutional-systems/csofta)
- *Constitutional Software Analysis: A Governance-Based Classification Method* — Mazurk 2026 — [doi:10.5281/zenodo.20472195](https://doi.org/10.5281/zenodo.20472195)
- *The Substrate Migration Principle* — Ableman 2026 *(forthcoming)*
- *Reasoning by Way of Receipts* — Ableman 2026 *(forthcoming)*

Companion papers in this repository (`docs/papers/`):

- [Constitutional Semantic Hashing](docs/papers/constitutional-semantic-hashing.md) — governed commitment framework
- [Cryptographic Admissibility and Jurisdiction](docs/papers/cryptographic-admissibility-and-jurisdiction.md)
- [Cryptographic Phase](docs/papers/cryptographic-phase.md)

Contact: ableman.research@gmail.com

---
## License

Apache 2.0 — see [LICENSE](LICENSE).

---
*Generated by `readme_gen.py` · UGK v0.1.0 · 119 gates · 87 invariants · 101 LEGEND entries*
