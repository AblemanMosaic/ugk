# UGK Test Index

The conformance gates live in `ugk/conformance/` (in-place — gate import paths are
load-bearing for 83 gates, so they are NOT physically moved). This index maps the
evidence suites to what they prove and how to run them.

## Suites & what each proves
| Suite | Location | Proves | Does NOT prove |
|-------|----------|--------|----------------|
| M2 executable vectors (39) | `ugk.conformance.m2_vectors_runner` | kernel op semantics match the M2 spec vectors deterministically | performance; adversarial resistance beyond vectors |
| Conformance gates (83) | `ugk.conformance.run_gates_batch` | substrate invariants hold (genesis, warrant-strict, chain, admission, etc.) | properties outside the declared gate set |
| A1 conservativity (7) | `ugk.conformance.a1_conservativity_gate` | A1 capability is add-only & dormant; law/legend/leaf hashes unmoved | A1 behavior when explicitly enabled (separate) |
| ρ fixtures (R1-R5, A1'-A5', fail-closed, dormant) | `ugk.conformance.rho_fixtures` | hardened ρ enforces E1/E2/E3 fail-closed; dormant by default | C1/C2/C3 (declared preconditions, not ρ-enforced) |
| CLI end-to-end | `tests/cli_smoke.sh` | charter→govern→verify with --state-dir; genesis isolation | — |

## How to run
- Fast check (vectors + A1):           `python tests/run_fast.py`
- Full check (vectors + 83 gates + A1 + ρ): `python tests/run_full.py`
  (bare/un-hardened run = 77/78 + 1 not-established for `grundnorm_readonly_gate`, 0 failed —
   posture deferred, not failed; run `ugk harden` first, or use `./verify_release.sh`, the
   authoritative full-posture check, for the canonical 83/83)
- Adversarial (ρ red-team + fail-closed fixtures): `python -m ugk.conformance.rho_fixtures`
- CLI smoke:                            `bash tests/cli_smoke.sh`

All runners require `PYTHONPATH=.` from the package root and set an ephemeral
`UGK_GENESIS_DIR`. They invoke the in-place gates as a black box; no gate logic is
duplicated here.

## Logical test categories (gates are tagged by role in ugk/ARCHITECTURE.md)
unit · conformance · integration · cli · regression · adversarial · performance · fixtures
— these are *roles*, not directories; the gate files remain under `ugk/conformance/`.
