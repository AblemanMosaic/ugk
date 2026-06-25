# Invariant Taxonomy — guide

## Purpose
`INVARIANT_TAXONOMY.json` (and its generated projection `INVARIANT_TAXONOMY.md`) is a structured
**navigation layer** over UGK's invariants. It maps every live invariant to a curated semantic family,
subsystem, frame role, authority role, gate, source references, construction provenance, and a short
explanation — so an agent or reviewer can navigate the constitution by **meaning** rather than by build
history.

## It is navigation, not law
The taxonomy does not define, constrain, or replace anything. The authoritative sources are the cited
invariant, ADR, gate, codex, release, and file. If the taxonomy and a cited source ever disagree, the
**source wins** and the taxonomy is stale (the freshness gate will fail). The taxonomy never carries
authority by itself.

## `introduced_in` is provenance
Each record carries `construction_lane`, mapped directly from the invariant's real `introduced_in` field
(e.g. `phase1`, `bridge-binding-law`). That is the build lane that introduced the invariant — historical
evidence for continuity, **not** semantic standing. Navigate by `semantic_family` and `subsystem`; read
`construction_lane` only as provenance.

## `semantic_family` is curated
`semantic_family` is a human-curated, source-bounded label seeded from the invariant's `classification`,
its ID-prefix subsystem, and (where applicable) an already-semantic construction lane. It is not inferred
from construction history alone, and it is not law. Current families: adversarial-resistance,
amendment-governance, audit-observability, configuration-constraint, content-addressed-artifact,
effect-truthfulness, frame-governance, identity-and-vocabulary, jurisdiction-projection,
namespace-authority, receipt-chain-integrity, terminal-outcome.

## Source refs are authority
`source_refs` use only resolvable schemes: `invariant:`, `adr:`, `gate:`, `codex:`, `release:`, `file:`.
Every ref must resolve against the live tree (the gate enforces this). No `profile:` refs until a profile
registry exists.

## How agents should use it
- To understand what an invariant is *about*, read its record's `semantic_family`, `subsystem`,
  `explanation_summary`, and `frame_role`/`authority_role`.
- To get the *authoritative* statement, follow `source_refs` (the invariant in `ugk/invariants.py`, its
  gate, the codex) — or run `ugk explain <id>` for the live statement.
- Never quote the taxonomy as if it were the invariant text or as law. It is an index.

## How to update it
1. Edit `INVARIANT_TAXONOMY.json` (the structured source). Never hand-edit `INVARIANT_TAXONOMY.md`.
2. Regenerate: `python invariant_taxonomy_gen.py`.
3. Keep `classification`, `gate`, and `construction_lane` equal to the live registry (the gate checks this).
4. Keep `last_verified_release` within two releases of head — re-stamp when it drifts (the gate enforces
   the same staleness discipline as the implementation codex).
5. Run `ugk/conformance/invariant_taxonomy_gate.py` (it is in the release batch). It fails closed on stale
   docs, unknown/missing IDs, dangling refs, registry mismatch, or any record claiming authority.

## What this layer must never do
- Rename or redefine invariant IDs (it only references them).
- Move law, schema, or legend.
- Import non-UGK IDs as UGK invariants (e.g. there is no `IEL-A..E`; the UGK IEL invariant is `IEL-S-01`).
- Mark live, gated invariants as design-only (e.g. `DKN-S-01` and `CHARTER-S-01` are live law-backed).
- Act as law rather than navigation.
