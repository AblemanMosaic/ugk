# UGK — Universal Governance Kernel: Agent Skill

Governs any agent session operating inside a UGK v0.1.x tree. UGK is the
governance closure bottom: dispatch + admissibility + NBER-1 receipts over a
deployment identity. Applications import it; they do not reimplement it.

## Orientation & navigation (read before operating)
Four layers, four jobs:
- `SKILL.md` (this file) — procedural boot + operating guide; routing only, not a theory document.
- `IMPLEMENTATION_CODEX.md` — human-authored subsystem navigation: per `concept_id`, the source refs,
  implementation surfaces, operational rule, common failure mode, and claim ceiling.
- `GLOSSARY.md` — generated term index for fast lookup (what a term is, what it is **not**, where truth lives).
  Generated from `GLOSSARY.json`; do not hand-edit.
- `INVARIANT_TAXONOMY.md` — generated navigation layer mapping every invariant to a semantic family,
  subsystem, frame role, gate, and source refs (construction lane shown only as provenance). Generated from
  `INVARIANT_TAXONOMY.json`; do not hand-edit.
- `ugk/codex/CODEX.md` — generated constitutional codex projection; machine-owned, do not edit.

For any unknown invariant, gate, or CSIL integer at runtime, run `ugk explain <id>` — the substrate is
self-describing; never restate constitutional facts from memory. For a minimal end-to-end call, see
`examples/governed/a1_example.py` (more direct than `examples/basic/governed_session.py`, which re-execs to
found into a tempdir). Before calling `execute()`, consult these entries: `effect-atomicity` (declare an effect
class; undeclared effects fail closed), `ck-canon-float-ban` (governance input refuses floats with a
ProtocolError — pass ints/strings), and `rho-integration-posture` (rho is dormant/opt-in, not kernel-wired).
Trust basis is cryptographic, not file mode — see `INTEGRITY_BASIS.md`.

## Boot sequence (always, in order)
1. `./verify_release.sh` — pins + full conformance suite. Expect ALL PASS.
   (Never restate the gate count from memory; the runner prints it.)
2. `python -m ugk.cli status` — read-only posture snapshot. Note
   `governor_pubkey`, `phase_code`, `chain_intact`, `mode`.
3. Determine founding posture before any work:
   - `governor_pubkey` starts with `GOVERNOR_KEY_UNSET` → **unfounded**.
   - Otherwise → founded under that identity. Confirm with the Governor that
     you are operating in the intended deployment.

## Fail-closed semantics (CHARTER-S-01 — never work around)
- The sentinel can never found governance. On an unfounded tree, `_ceremony()`
  and every Tier-2 APPLICATION op refuse with `GovernanceNotFounded`.
- That refusal is a SUCCESS state, not an error to suppress. Do not
  monkeypatch identity, hand-write genesis files, or copy another
  deployment's genesis/ to "get past" it.
- Founding is one act: `ugk charter --pubkey <ed25519-hex>` (the Governor's
  decision, never the agent's). `--force` is required to overwrite an
  existing charter — treat any `--force` as Governor-authorization-required.
- Tier-1 UNIVERSAL ops (e.g. `session_open`, read surfaces) are lawfully
  available under any identity, including the sentinel.

## Receipt discipline (NBER-1)
- Receipts are written BEFORE effects. Never reorder, batch around, or
  "reconcile later".
- Every receipt must satisfy the three-disjunct: trace, or warrant_id, or
  intent_ref. If none applies, the op should not run.
- Mutations happen only through `kernel.execute()` — no direct store writes.

## Observability is read-only
`ugk verify`, `ugk status`, `ugk posture`, `ugk health` never mutate session
state. If an "observation" would write anything outside a declared fixture
scope, stop — that is a defect, not a convenience.

## Conformance fixture (know it, don't fear it)
The dev fixture keypair in `ugk/conformance/_fixture.py` is deliberately
public and attests nothing. On unfounded trees the gate runner founds an
ephemeral fixture deployment (declared in output) and restores `genesis/`
afterwards. If a run leaves anything in `genesis/` you did not charter,
report it as a defect.

## Grundnorm discipline
Core files ship chmod 444 (`make_release.sh` holds the list). Editing one is
a constitutional act: explicit Governor authorization, chmod ceremony,
re-run the full suite, note the edit in the change report. `ops.py` (644) is
the deployer surface — new APPLICATION ops are declared there, never patched
into the kernel.

## What not to do
- Never ship, commit, or copy `genesis/*PRIVKEY*` or `*.hex` material.
- Never edit `invariants.py` or anything that moves `invariants_pin`,
  `LEGEND_HASH`, or `codex_hash` without an explicit constitutional ruling.
- Never claim gate counts, invariant counts, or identity values from memory —
  run the command and read the output.
- Never treat a refusal path as a bug to route around. Refusal is governance
  working.
