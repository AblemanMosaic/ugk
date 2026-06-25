# GRBSA Proof Model B — Intrinsic Behavioral-Continuity Predicate

**Status:** PRIMARY continuity authority for the UGK substrate lineage.
**Gate:** `tools/grbsa/proof_model_b.py` · **Surface:** `tools/grbsa/continuity_surfaces.json`

## Purpose

Proof Model A treated **byte-identity to r17a** as the proof concept for substrate continuity.
That broke at the publication-hardening re-baseline (r17a→r46 changed 5 `ugk/` files). Proof Model B
replaces byte-identity-as-proof with an **intrinsic behavioral-continuity predicate**, in which
byte-identity survives only as a *sufficient shortcut*.

## The predicate

`ContinuityB(baseline → candidate)` holds iff **either**:

- **(S) shortcut** — the candidate's `ugk/` is byte-identical to the baseline's `ugk/`. Sufficient,
  **not** necessary. When it fires, continuity holds trivially and (B) is not evaluated.
- **(B) behavioral basis** — all four:
  - **B1 frame-triad stability** — `law_hash` (behavior), `legend_hash` (meaning), and
    `schema_hash` (structure) are equal across baseline↔candidate. The structure leg is computed
    *tree-independently* from each candidate's live schema shape via the canonical
    `compute_schema_hash` algorithm, so it is well-defined even on baselines (e.g. r17a) that predate
    the `EXPECTED_SCHEMA_HASH` constant.
  - **B2 behavioral attestation** — the 9 GRBSA behavioral gates pass on the candidate.
  - **B3 conformance surface** — the 78-gate conformance batch, scale suite, and AL conformance pass
    **directly** on the candidate (re-established, not inherited by transitivity).

B4 change confinement classifies the baseline↔candidate `ugk/` diff four ways (machine-checkable):
RUNTIME SUBSTRATE (kernel, storage, cli, ops, binding, …) must lie within the declared
`substrate_surface`; the SUBSTRATE-SHIPPED VERIFICATION SURFACE (`ugk/conformance/`) must lie
within the declared `verification_surface`; the DERIVED CODEX PROJECTION SURFACE (`ugk/codex/`)
must lie within the declared `codex_surface`. Overlay scaffolding (`tools/`, `docs/`, the
top-level `codex_gen.py`) is outside `ugk/` and not diffed. A runtime-substrate change appearing
without a `substrate_surface` declaration (or a conformance change without `verification_surface`,
or a codex change without `codex_surface`) fails B4.
  - **B4 change confinement** — the baseline↔candidate `ugk/` file diff is a subset of the declared
    `substrate_surface` for that link. Scope is the substrate (`ugk/`); `tools/` and `docs/` are
    audit/release scaffolding (declared for transparency, not continuity-critical — substrate
    behavior is verified directly by B2/B3).

## Composability

`ContinuityB` chains. The release continuity claim is the conjunction over lineage links:

```
ContinuityB(r17a → r46)  ∧  ContinuityB(r46 → r49)  ∧  ContinuityB(r49 → r54)  ∧  ContinuityB(r54 → r59)  ∧  ContinuityB(r59 → r60)  ∧  ContinuityB(r60 → r61)
```

Every link from r46 onward has real `ugk/` changes, so each is decided by the behavioral basis (B),
not the shortcut — which is the point of demoting byte-identity. The r59 → r60 link spans both
the runtime-substrate surface (ugk/cli.py) and the verification surface (ugk/conformance/*). The
r60 → r61 link is documentation-claim reconciliation only: no ugk/ file differs, so both declared
surfaces are empty and the substrate is byte-identical to r60 (B4 holds vacuously, B1–B3 hold by
identity).
change-confinement classes: `ugk/cli.py` (runtime substrate, the new `harden` establishment verb)
under `substrate_surface`, and the Grundnorm establishment-lifecycle refactor of
`ugk/conformance/{__init__,grundnorm_readonly_gate,run_gates_batch}.py` under `verification_surface`.

## Authority

Proof Model B is the single authoritative continuity proof. The GRBSA manifest and the G6 aggregate
gate **defer** to it; byte-identity is described there only as clause (S), never as a parallel
governing model. A proof model that does not actually exercise the behavioral basis is only prose —
so the gate runs B2/B3 directly on each candidate rather than asserting them.

## Usage

```
python3 tools/grbsa/proof_model_b.py --compose      # composed claim over all links
python3 tools/grbsa/proof_model_b.py --link r46->r49
```

Fail-closed: a missing archive, a moved frame leg, a failing gate, or undeclared substrate drift
yields `FAIL` for that link and `CONTINUITY FAILED` for the composed verdict.
