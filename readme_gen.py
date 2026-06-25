#!/usr/bin/env python3
"""readme_gen.py — Generate README.md from live system state.

Usage:
    python readme_gen.py           # writes README.md
    python readme_gen.py --check   # exits 1 if README.md would change

Static sections (Creator's Note, What This Gives You, Architecture,
Development, Contributing) are authoritative strings in this file —
the same way ugk/invariants.py is the canonical law_hash source.
Dynamic sections pull from the live ugk package at generation time.
"""
from __future__ import annotations
import hashlib, importlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from ugk.storage.binding import LEGEND_HASH, LEGEND_ENTRY_COUNT, _LEGEND_ENTRIES
from ugk.invariants import INVARIANT_REGISTRY
from ugk.adr import ADR_REGISTRY
from ugk.kernel import GOVERNOR_PUBKEY_HEX, _PHASE_CODE
from ugk.storage.binding import mosaic_id as _mosaic_id
from ugk.conformance.run_gates_batch import GATES as _GATES

_cli = importlib.import_module("ugk.cli")
_HELP_DATA: dict = getattr(_cli, "_HELP_DATA", {})
_INV_PIN = hashlib.sha256((ROOT / "ugk" / "invariants.py").read_bytes()).hexdigest()
_MOSAIC  = _mosaic_id(GOVERNOR_PUBKEY_HEX)
_TIER_COUNTS: dict[str, int] = {}
for _e in _LEGEND_ENTRIES:
    _TIER_COUNTS[_e["tier"]] = _TIER_COUNTS.get(_e["tier"], 0) + 1

# ── Static sections ──────────────────────────────────────────────────────────

_CREATOR_NOTE = """\
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
"""

_CSOFTA = """\
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
"""

_WHAT = """\
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
"""

_QUICKSTART = """\
## Quick start

```bash
pip install .
```

**1. Charter a new deployment** — establishes the governance identity:

```bash
ugk charter --pubkey <your-ed25519-pubkey-hex> \\
            --phase-code "my-deployment-v1"    \\
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
"""

_ARCHITECTURE = """\
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
"""

_DEVELOPMENT = f"""\
## Development

```bash
make test          # full gate suite ({len(_GATES)} gates)
make readme        # regenerate this README
python verify_release.py   # AUTHORITATIVE full-posture check (cross-platform): invariants_pin + LEGEND_HASH + {len(_GATES)}/{len(_GATES)} gates
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
reports `{len(_GATES)-1}/{len(_GATES)} passed | 0 failed | 1 not-established` — the
Grundnorm read-only posture is *deferred, not failed* (exit 0). Run `ugk harden` first,
or use `python verify_release.py` (authoritative, cross-platform; `./verify_release.sh` is a
POSIX wrapper around it), for the canonical `{len(_GATES)}/{len(_GATES)}`.

`snapshot_fast()` also reports `crypto_profile`. The stdlib-only vendored Ed25519 backend
is surfaced as `reference_non_constant_time`; production deployments should bind signing to
a hardened constant-time backend or external signer.

---
"""

_CONTRIBUTING = """\
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
"""

_RESEARCH = """\
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
"""


# ── Dynamic generators ───────────────────────────────────────────────────────

def _cli_reference() -> str:
    if not _HELP_DATA:
        return "## CLI reference\n\nSee `ugk help` for all commands.\n\n---\n"
    rows = ["## CLI reference\n",
            "| Command | Description |", "|---|---|"]
    for verb in sorted(_HELP_DATA):
        rows.append(f"| `ugk {verb}` | {_HELP_DATA[verb]['summary']} |")
    rows += ["", "Use `ugk help <verb>` for parameter details.", "", "---\n"]
    return "\n".join(rows)


def _constitutional_reference() -> str:
    # Group invariants by SEMANTIC classification, not construction lane (introduced_in).
    by_class: dict[str, list] = {}
    for inv in INVARIANT_REGISTRY.values():
        by_class.setdefault(inv.classification, []).append(inv)
    subsystems = sorted({inv.id.split("-")[0] for inv in INVARIANT_REGISTRY.values()})

    groups: dict[str, int] = {}
    for modname in _GATES:
        try:
            doc = (importlib.import_module(modname).__doc__ or "").lower()
            for g in ("structural", "unit", "integration", "conformance"):
                if g in doc:
                    groups[g] = groups.get(g, 0) + 1; break
            else:
                groups["integration"] = groups.get("integration", 0) + 1
        except Exception:
            groups["integration"] = groups.get("integration", 0) + 1

    lines = [
        "## Constitutional reference\n",
        "### Invariants\n",
        f"**{len(INVARIANT_REGISTRY)} invariants** · **{len(ADR_REGISTRY)} ADRs**, grouped by semantic "
        "classification. The construction lane (`introduced_in`) is retained as provenance and shown by "
        "`ugk explain <id>`; it is build history, not semantic standing.\n",
        "| Classification | Count | Subsystems | Examples |", "|---|---|---|---|",
    ]
    for cls in sorted(by_class):
        invs = by_class[cls]
        subs = sorted({i.id.split("-")[0] for i in invs})
        ids = sorted(i.id for i in invs)
        ex = ", ".join(f"`{i}`" for i in ids[:3]) + (f" +{len(ids)-3}" if len(ids) > 3 else "")
        subdisp = ", ".join(subs[:8]) + (f" +{len(subs)-8}" if len(subs) > 8 else "")
        lines.append(f"| `{cls}` | {len(invs)} | {subdisp} | {ex} |")
    lines += [
        "",
        f"Invariant IDs span **{len(subsystems)} subsystems** (the ID prefix encodes the governed area): "
        + ", ".join(f"`{s}`" for s in subsystems) + ".",
        "",
        "> Provenance note: each invariant also carries `introduced_in` — the build lane that introduced it "
        "(e.g. `phase1`, `bridge-binding-law`). That is historical evidence for continuity, not the ontology "
        "of the system; navigate by classification and subsystem above.",
    ]

    lines += [
        "",
        "### LEGEND — Canonical Semantic Integer Layer\n",
        f"**{LEGEND_ENTRY_COUNT} entries** across {len(_TIER_COUNTS)} tiers:\n",
        "| Tier | Count | Range |", "|---|---|---|",
        f"| `invariant` | {_TIER_COUNTS.get('invariant',0)} | 1001+ |",
        f"| `dimension` | {_TIER_COUNTS.get('dimension',0)} | 2001+ |",
        f"| `op`        | {_TIER_COUNTS.get('op',0)} | 3001+ |",
        f"| `vocab`     | {_TIER_COUNTS.get('vocab',0)} | 4001+ (SSA verbs, jurisdictions, meta-governance) |",
        f"| `meta`      | {_TIER_COUNTS.get('meta',0)} | 6001+ (CSIL/GTI self-description) |",
        f"| `warrant_result` | {_TIER_COUNTS.get('warrant_result',0)} | 9001+ |",
        "",
        "### Gate suite\n",
        f"**{len(_GATES)} gates**",
        "",
    ]
    if groups:
        for g in ("structural", "unit", "integration", "conformance"):
            if g in groups:
                lines.append(f"- `{g}`: {groups[g]} gates")
    lines += [
        "",
        "### Build pins\n",
        "```",
        f"invariants_pin:  {_INV_PIN}",
        f"LEGEND_HASH:     {LEGEND_HASH}",
        f"governor_pubkey: {GOVERNOR_PUBKEY_HEX}",
        f"mosaic_root:     {_MOSAIC}",
        f"phase_code:      {_PHASE_CODE}",
        "```",
        "",
        "---\n",
    ]
    return "\n".join(lines)


# ── Entry point ──────────────────────────────────────────────────────────────

_ORIENTATION = """## Does this apply to my domain?

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

"""

def generate() -> str:
    header = (
        "# UGK — Universal Governance Kernel\n\n"
        f"[![Gates](https://img.shields.io/badge/gates-{len(_GATES)}%2F{len(_GATES)}_(hardened)-brightgreen)]"
        "(ugk/conformance/run_gates_batch.py) "
        "[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org) "
        "[![stdlib-only](https://img.shields.io/badge/dependencies-stdlib%20only-green)](pyproject.toml) "
        "[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)\n\n"
        "**Receipt-before-effect infrastructure for constitutional computing.**\n\n"
        "```\n"
        "intent + warrant + trace -> admissibility -> receipt -> effect or refusal\n"
        "```\n\n"
        "Governance begins where admissibility becomes a first-class computational object. "
        "UGK is a constitutional computing substrate for Python applications: governance is "
        "*constitutive* of operations — not a report written afterward. "
        "Every governed operation emits a cryptographically-chained receipt *before* executing. "
        "If the receipt cannot be written, the operation does not proceed. "
        "The chain is the governance, not documentation of it.\n\n---\n\n"
    )
    return (
        header + _CREATOR_NOTE + _CSOFTA + _WHAT + _QUICKSTART + _ORIENTATION +
        _cli_reference() + _ARCHITECTURE +
        _constitutional_reference() +
        _DEVELOPMENT + _CONTRIBUTING + _RESEARCH +
        "## License\n\nApache 2.0 — see [LICENSE](LICENSE).\n\n"
        f"---\n*Generated by `readme_gen.py` · "
        f"UGK v0.1.0 · {len(_GATES)} gates · "
        f"{len(INVARIANT_REGISTRY)} invariants · {LEGEND_ENTRY_COUNT} LEGEND entries*\n"
    )


def main() -> None:
    check   = "--check" in sys.argv
    content = generate()
    readme  = ROOT / "README.md"
    if check:
        current = readme.read_text(encoding="utf-8") if readme.exists() else ""
        if current == content:
            print("README.md is current."); sys.exit(0)
        print("README.md is stale — run: python readme_gen.py"); sys.exit(1)
    readme.write_text(content, encoding="utf-8")
    print(f"README.md written  ({content.count(chr(10))} lines, {len(content):,} chars)")


if __name__ == "__main__":
    main()
