# GRBSA — Governed Receipt-Bound Scale Architecture (`tools/grbsa/`)

An additive overlay on **UGK v0.1.0**. GRBSA wraps existing UGK/CGProj surfaces as **receipt-bound
continuations** and proves each wrap equivalent to its legacy runner, without modifying the substrate
(`ugk/` and `kernel.py` are byte-identical to UGK v0.1.0; `law_hash` unchanged).

Release notes: **`RELEASE_GRBSA.md`**. Manifest + lineage: **`GRBSA_MANIFEST.md`**.

## Verify everything (one command)
```
python tools/grbsa/g6_aggregate_validation_gate.py . --r17a <ugk-v0.1.0-cgproj-rc-r17a.tar.gz>
```

## Surface map

### Standing gates (`tools/grbsa/*.py`)
- `g1_core_shape_gate` — Receipt/ResultEnvelope cores are projections over existing fields.
- `g1_separation_symmetry_gate` — Receipt ≠ Envelope; symmetric separation.
- `g2_substrate_naming_gate` — scale services map to existing `ugk/scale` symbols; no authority expansion.
- `g3_adapter_equivalence_gate` — GateAdapter beachhead (wraps `a1_conservativity_gate`).
- `g4a_adapter_generality_gate` — GateAdapter generality (wraps `determinism_gate`, different shape).
- `g4b_projection_adapter_gate` — ProjectionAdapter (fidelity; reuses CGProj `fidelity_compare`).
- `g4c_explain_adapter_gate` — ExplainAdapter (non-invention + completeness; reuses CGProj 5b checks).
- `category_separation_gate` — domain predicates reject foreign receipt/envelope pairs (clean False).
- `g5_execution_adapter_gate` — ExecutionAdapter (founded `execute()`, observed, non-invasive).
- `g6_aggregate_validation_gate` — full matrix + reconciliation vs r17a + anti-vacuity control.

### Runtime (`tools/grbsa/grbsa_runtime/`)
- `gate_adapter.py` — GateAdapter, GateReceipt/Envelope, `gate_success`, result-shape normalizers.
- `projection_adapter.py` — ProjectionAdapter, ProjectionReceipt/Envelope, `projection_success`.
- `explain_adapter.py` — ExplainAdapter, ExplainReceipt/Envelope, `explain_success`.
- `execution_adapter.py` — ExecutionAdapter, ExecutionReceipt/Envelope, `execution_success`.
- `migration_receipt_*.json` — per-unit dual-run equivalence records (a1, determinism, projection,
  explain, execution); each `equivalent: true`.

### Specs & provenance
- `RECEIPT_CORE_SPEC.md`, `core_mapping.json` — G1 core semantic spec + machine-readable manifest.
- `SUBSTRATE_INTERFACE.md`, `service_map.json` — G2 substrate naming.
- `G{1,2,3,4A,4B,4C}_PROVENANCE.md`, `CATEGORY_SEPARATION_PROVENANCE.md`, `G5_PROVENANCE.md`,
  `G6_PROVENANCE.md` — per-phase canonical provenance.

## Principles
- **Receipt Sufficiency** is the equivalence basis (admissibility + success semantics + lineage shape);
  **receipt-hash identity is not asserted**.
- **Strangler posture**: legacy runners remain source of truth; nothing retired; no live routing.
- **Category separation** is explicit (a `domain` tag), not accidental.

## Scope & inherited substrate (read before reviewing the full tree)
This release is an **additive GRBSA overlay** on the **UGK v0.1.0 substrate**. The two are different
in authority and polish:

- **GRBSA overlay (authoritative, this release):** everything under `tools/grbsa/`, plus two disclosed
  inherited-substrate fixes (`verify_release.sh` import fix; `tests/README.md` gate-count correction).
  These docs are the authoritative description of GRBSA.
- **Inherited UGK substrate (byte-identical to the ratified r17a CGProj RC):** `ugk/`, `kernel.py`,
  root `README.md`, `RELEASE.txt`, `docs/`, and the rest of the base tree. GRBSA does **not** re-author
  or re-validate the substrate's own documentation; it is shipped exactly as inherited so that the
  byte-identity guarantee (`ugk/` + `kernel.py` unchanged, `law_hash` unchanged) holds.

**Known pre-existing substrate-documentation issues (inherited from r17a, byte-identical, NOT GRBSA
claims).** Disclosed so reviewers aren't misled:
- Root `README.md` contains broken links to `docs/mechanism.md` and `docs/applications/` (those paths
  are not present in this distribution), and `readme_gen.py --check` reports the generated root README
  as out of sync. These are substrate-base matters; fixing them would require creating the missing docs
  or editing the substrate generator, which would break the byte-identity guarantee, so they are left
  as-inherited and disclosed here instead.
- The authoritative GRBSA documentation (this file, `RELEASE_GRBSA.md`, `GRBSA_MANIFEST.md`) does not
  depend on the substrate README/docs.

## CLI surface (clarification)
The substrate ships a `ugk` CLI (entry point `ugk.cli:main`). Two clarifications for reviewers:

- **`ugk explain <name>` is the SUBSTRATE explain surface** — it explains an *invariant ID, gate name,
  or CSIL integer*. It is **distinct** from the **CGProj *projection* explain surface**, which is a
  *library* surface (`ugk.projections.explain`) wrapped by GRBSA's ExplainAdapter (G4c). They share the
  word "explain" but are different things: the CLI explains kernel invariants/gates/CSIL; the GRBSA
  ExplainAdapter governs the projection-explanation library output (non-invention + completeness).
- **`ugk attest` and `ugk govern` require a *founded* kernel** (run the genesis ceremony / establish a
  charter first, e.g. `ugk charter`). On an unfounded tree, `ugk attest` raises
  `GovernanceNotFounded` ("requires ACTIVE governance status. Run the genesis ceremony to found the
  kernel.") — the message is correct and structured, but it surfaces as a Python traceback rather than
  a one-line CLI error. `ugk govern` likewise requires `--intent`/`--subject` (a clean argparse error).
  Cleaning the attest traceback into a one-line error would require modifying `ugk/cli.py` — a
  substrate change that would break the byte-identity guarantee — so this release **documents** the
  precondition rather than altering the substrate CLI. Found the kernel first and these commands work. **Important — founding writes local runtime state:** running the genesis ceremony / `ugk charter` writes founded artifacts into `<repo>/genesis/` — `DEPLOYMENT_MANIFEST.json`, `GENESIS_KEY.pub`, `LAUNCH_IC.json`, `VALIDATOR_SET.json`, and a `GENESIS_PRIVKEY.hex`. The shipped `GENESIS_PRIVKEY.hex` in a founded tree is the PUBLIC dev fixture key (`DEV_FIXTURE_PRIVKEY`), not a real secret, but per `genesis/README.md` no `PRIVKEY`/`.hex` material may ever be committed. These are RUNTIME state, not release content: the shipped archive contains only `genesis/README.md`, the G6 reconciliation REFUSES genesis founding artifacts (a founded tree FAILS, with a message telling you to re-extract — it does NOT silently admit them), and a G6 SECURITY check FAILS on any *.hex/GENESIS_PRIVKEY anywhere. verify_release.sh and G6 `--full` isolate and pre-found genesis in a throwaway dir, so they never found `<repo>/genesis` and never hang. Found the kernel in a throwaway/isolated working copy, and never commit a founded `genesis/`.
