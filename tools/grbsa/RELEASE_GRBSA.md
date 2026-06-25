# GRBSA v0.1.0 — Release Notes (Governed Receipt-Bound Scale Architecture)

**GRBSA is an additive overlay on UGK v0.1.0, not a substrate revision.** It lives entirely under
`tools/grbsa/`. The UGK substrate (`ugk/`, including `kernel.py`) is **byte-identical** to the UGK
v0.1.0 CGProj release candidate (r17a); `law_hash` is unchanged. The substrate version remains
`0.1.0`. This release is labeled **`v0.1.0-grbsa`** to denote the overlay.

> **v0.1.0 reference-line note (supersedes the byte-identity framing in this file).** Since these
> notes were first written, the UGK substrate evolved beyond r17a through authorized hardening
> (Category A/B), and **GRBSA Proof Model B** (`PROOF_MODEL_B.md`) became the primary
> substrate-continuity authority. Continuity is now proven by the composed predicate
> `ContinuityB(r17a→r46) ∧ ContinuityB(r46→r49) ∧ ContinuityB(r49→r54)`, **verified behaviorally
> per link** (frame triad + 9 gates + conformance + change confinement) — not by byte-identity
> "transitivity." Byte-identity to r17a survives only as clause (S), the sufficient shortcut inside
> `ContinuityB`; G6 delegates to the composed proof (`proof_model_b --compose`, heavy by design).
> The "green by transitivity"/"byte-identical to r17a" descriptions below describe the original
> overlay and the r34-era G6 model and are retained as historical context. Canonical current
> state: `../../docs/RELEASE_CLOSURE_V0.1.0.md`.

## What GRBSA is
GRBSA models governed work as a **receipt-bound continuation**:

```
proposal → admissibility → receipt → result-envelope → continuation
```

A **receipt** is the justificatory artifact ("why admissible"); a **result-envelope** is the
substrate-owned record ("what happened"); a domain's **success semantics** is a predicate over the
receipt+envelope pair. GRBSA wraps existing UGK/CGProj surfaces as receipt-bound continuations and
proves each wrap equivalent to its legacy runner — without changing the substrate.

## What was proven (each claim is backed by a standing gate)
Four domains, each with a **different** success predicate, all in the same continuation shape:

| Domain | Success predicate | Gate |
|---|---|---|
| Gate | anti-vacuity (≥1 check, all pass) | `g3_adapter_equivalence_gate`, `g4a_adapter_generality_gate` |
| Projection | fidelity (content_hash + per-artifact) | `g4b_projection_adapter_gate` |
| Explain | non-invention + object-level completeness | `g4c_explain_adapter_gate` |
| Execution | gate-admit + not-failed + receipted | `g5_execution_adapter_gate` |

- **Category-Separation** (`category_separation_gate`): each domain's success predicate rejects every
  other domain's receipt/envelope pair with a clean `False` via an explicit `domain` tag — proven
  across all four domains (12 cross-pair rejections + 4 native positives).
- **Core spec + separation/symmetry** (`g1_core_shape_gate`, `g1_separation_symmetry_gate`): Receipt
  Core and ResultEnvelope Core are semantic projections over existing fields; Receipt ≠ Envelope.
- **Substrate naming** (`g2_substrate_naming_gate`): the scale substrate services map to existing
  `ugk/scale` symbols; no authority expansion; NBER-1 present at the receipt-emission site.

## Equivalence basis (narrow by construction)
Equivalence is the **Receipt Sufficiency Principle**: admissibility + success semantics + lineage
*shape*. **Receipt-hash identity is NOT asserted** anywhere (the chain hash binds a timestamp; see the
Receipt Identity Principle). Each per-unit MigrationReceipt records dual-run equivalence on this basis:
`migration_receipt_{a1,determinism,projection,explain,execution}.json` (each `equivalent: true`).

## Strangler posture (nothing retired)
Legacy runners remain the **source of truth**. GRBSA wraps them read-only (and, for execution,
observes the receipt the kernel writes — it mints none). No surface is routed through an adapter in
this release; units are at most *eligible* after their gate passes from clean extraction. Execution is
not made routable even in that sense (authority is involved).

## Invariants held across the entire arc (verified)
- `ugk/` and `kernel.py` byte-identical to r17a.
- `law_hash = 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820` (unchanged).
- Existing surface green: scale 7/7, scale AL 22/22, conformance batch 78/78, CGProj component gates.
- All additions are confined to `tools/grbsa/`.

## Scope boundary (deliberate)
The ratified CGProj Phase-6 gate validates the **CGProj** release surface and is left **unmodified**.
On the combined GRBSA tree it fails **by design** because `tools/grbsa/` is out of CGProj scope — a
scope statement, not a regression. The **GRBSA G6 aggregate gate** is the authority for the combined
surface, with its own reconciliation against r17a (admitting only `tools/grbsa/`).

## How to verify (single command)
From the extracted repo root, with a writable genesis dir:

```
python tools/grbsa/g6_aggregate_validation_gate.py . --r17a <ugk-v0.1.0-cgproj-rc-r17a.tar.gz>
```

It transitively exercises all 9 other GRBSA gates, verifies all 5 MigrationReceipts
(`equivalent: true`), confirms the **existing surface is green by transitivity** (the surface modules
`ugk/scale`, `ugk/conformance` and the CGProj gates `tools/cgproj/` are byte-identical to the ratified
r17a CGProj RC, which passed scale 7/7, AL 22/22, batch 78/78 — so no re-execution is needed),
confirms `law_hash` unmoved, reconciles the GRBSA surface vs r17a (only `tools/grbsa/` added, `ugk/`
byte-identical, `kernel.py` unchanged), runs a current-state drift guard, and carries an anti-vacuity
control. By default G6 spawns no heavy/grandchild subprocess — its only children are the 9 GRBSA leaf
gates and 2 anti-vacuity stubs — so the default command is bounded and reliable in a hostile session.

For an exhaustive run that ADDITIONALLY re-executes the substrate surface (scale 7/7, AL 22/22, batch
78/78) via the grandchild-proof runner, pass `--full`:

```
python tools/grbsa/g6_aggregate_validation_gate.py . --r17a <ugk-v0.1.0-cgproj-rc-r17a.tar.gz> --full
```

## Lineage (per-phase canonical archives)
```
r17a CGProj RC          4d080a4bcd4abfae0862fb5b2e7de5bcc3c03557419567ecbd3c6bb93b56d487
r18  G1 core spec       eb16c6d16f6786383feea8979e76a8f1e017983088d79204f848e61a41672148
r19  G2 substrate name  5c38a84c9979bb437942e454fac0d3f4d8f37654016384b0749c3797e2bf3483
r20  G3 GateAdapter     37c552390dd4b70a529a4415f53472b4d76aa80dd3e0f11debc0374b527723ce
r21  G4a generality     43b0c80240a6814b8f5dd5abd6c5aeed87a9fdc0d417cdcba4d8d94eb6eb32fe
r22  G4b ProjectionAd.  9345fd87206abe814c81fc3625fd7e8d49388e47eb74006015fefbd5a8d30c32
r23  G4c ExplainAdapter a43014b74af612c3bdb079b72ab95ea79aa4512c9bd75c9ab80887a10cffab7f
r24  Category-Sep       655db9e4f64e374426be3f2f54f5bb8f6ab71a44a3c20e881d92f9ed150a7dda
r25  G5 ExecutionAd.    f669ac702e49a71b47e226ad0289027f760890466fe6643e6f24030a651cfa70
r26  G6 aggregate       ad6dfd0fb80c8a376100a47b4728b874c9f06157d955bfefedfac7129143f9b0
r27  release hygiene    (r26 + GRBSA hygiene docs)
r28  remediation        (de-tangled adapter runtime paths; verify_release.sh fix)
r29  validation hygiene  (G4b/G4c validation paths de-entangled from CGProj gate scripts)
r30  G6 batch-once        (G6 runs the 78-gate batch exactly once; dead gate-loaders removed)
r31  anti-vacuity sweep   (gate vacuity guards + G6 bounded/fail-closed subprocess)
r32  docs/provenance      (stale-language cleanup; no .py changes)
r33  runner + guard       (grandchild-proof subprocess runner; consistency drift guard)
r34  G6 type-closure      (default proves surface green by transitivity; --full re-runs scale/AL/batch)
r35  docs polish          (release-notes wording aligned to r34 behavior; no code changes)
r36  presentation polish   (manifest scope truth; inherited-substrate boundary; CLI docs)
r37  genesis/key hygiene   (superseded — reconciliation-exclude approach)
r38  genesis/key ROOT-FIX  (this archive — reconciliation REFUSES genesis; batch invocations isolate+pre-found genesis; verify_release/--full no longer contaminate or hang)
```

r26 is the code-complete predecessor; r27 = r26 + these additive `tools/grbsa/` hygiene docs, re-verified
by the G6 aggregate gate with `ugk/` byte-identical and `law_hash` unchanged.

## r28 — remediation (post-review)
An independent verification pass on r27 found two release-integrity defects, both fixed in r28:
1. **Import-time entanglement (root cause):** the Projection/Explain adapters previously obtained
   reusable check logic by *executing* a CGProj gate script (`phase4`/`phase5b`). `phase5b`'s top
   level spawns the full 78-gate conformance batch, so constructing an ExplainAdapter re-ran the
   batch (blocking G4c/Category-Separation/G6). **Fix:** both adapters now source from import-clean
   `ugk.projections` library surfaces and reconstruct the fidelity / non-invention+completeness
   predicates in-lane — **no gate-script execution on the adapter path**. Each reconstruction is
   verified **once** against the original CGProj checker (G4b/G4c fidelity safeguards); if a
   reconstruction disagreed on the honest corpus, the gate would fail.
2. **`verify_release.sh`** imported `ugk.binding`; corrected to `ugk.storage.binding` (the only
   substrate-script delta; `ugk/` and `law_hash` untouched).
CGProj gates (`phase4`/`phase5b`) remain **unmodified**; `ugk/` byte-identical; `law_hash` unchanged.
Adapter path no longer spawns the conformance batch (G4c ~5s; was over ceiling). Packaging: GRBSA
remains a source-tree overlay (not pip-installed) for v0.1.0.

## r30 — dead-code removal + G6 batch-once (post external review)
External testing of r29 found the primary command (G6) still ran the 78-gate conformance batch ~3×:
once directly, and once each inside the standalone CGProj gates `phase5b` and `phase4_5`, which spawn
their own nested batch. Also flagged: dead gate-loader functions remained. r30 fixes both:
- **G6 (Option A):** keeps ONE canonical direct conformance batch run + scale + AL; the standalone
  CGProj component step now runs only LIGHT, non-batch-spawning gates (`phase2`, `phase4`, `phase5a`)
  — `phase5b` and `phase4_5` are excluded. **Invariant: G6 runs the 78-gate batch exactly once.**
  Their substrate coverage is the single batch run; their GRBSA-relevant logic is validated
  import-clean in G4c/G4b. Measured: G6 end-to-end ~6s from clean extraction (was 14s+/not completing).
- **Dead code removed:** `explain_adapter.load_5b()` and `projection_adapter.load_fidelity_compare()`
  deleted, stale docstrings scrubbed. Re-entanglement is now impossible by construction — neither
  adapter module can load a gate script.
CGProj gates UNMODIFIED; ugk/ + kernel.py byte-identical; law_hash unchanged. verify_release.sh left
as-is (substrate script; legitimately runs the conformance suite once — allow adequate time).

## r31 — proactive anti-vacuity / robustness sweep
A proactive sweep for the same defect classes surfaced by external review (vacuity / silent-pass /
unbounded-completion) found and fixed three same-class issues in the GRBSA gates (no adapter, ugk/,
kernel.py, law_hash, or CGProj changes):
- **g2 zero-service vacuity:** `check(..., not missing)` would pass with zero services/symbols. Now
  requires >=1 service AND >=1 symbol actually resolved (degenerate manifest → FAIL). Verified the
  guard fires on empty input.
- **Universal final-verdict vacuity:** every gate ended `ok = all(r[1] for r in results)`, and
  `all([])` is True — a gate that ran zero checks would report PASS. Hardened to
  `ok = bool(results) and all(...)` across all 10 gates (zero checks → FAIL). Verified the guard fires.
- **G6 unbounded subprocess:** `run_py`/`run_mod` had no `timeout=`; a hung child would hang G6
  indefinitely. Now bounded (180s/child, ~16x the batch) and fail-closed (TimeoutExpired → returncode
  124 → component FAIL) rather than hanging.
Sweep also confirmed clean: no residual gate-script execution, no receipt-hash-identity assertions, no
brittle hardcoded-count assertions (counts are dynamically derived), G6 reconciliation fails closed
when no baseline is supplied.

## r33 — eliminate the recurring TYPES (subprocess fragility + stale-doc drift)
External review correctly identified that prior passes fixed instances, not the generating types. r33
eliminates both classes:
- **Runtime (subprocess-orchestration fragility):** G6 validated by orchestrating a subprocess tree;
  its only grandchild-spawning child is the conformance batch (run_gates_batch re-execs under a fresh
  genesis). Under `subprocess.run(capture_output=True, timeout=...)`, a timed-out child's grandchildren
  keep the captured pipe open → hang, not fail-closed (timing-dependent: passed in-house, hung in the
  hostile session). Fixed by a single grandchild-proof runner used for EVERY child: own process group
  (start_new_session), output to a temp FILE (never an OS pipe), and kill the WHOLE process group on
  timeout → genuinely fail-closed and bounded regardless of grandchildren. Proven against a synthetic
  grandchild-holds-pipe hang (returns rc=124 in ~timeout, no hang).
- **Docs (stale-claim drift):** provenance/receipts written at phase creation, invalidated by later
  remediation. Swept the whole class: receipts' reuse language → import-clean fixture; G6_PROVENANCE
  present-tense "r26 final release" → rev-agnostic (history preserved); G4B/G4C provenance → SUPERSEDED
  banner + corrected present-tense lines. Added a CONSISTENCY GUARD in G6 that FAILS if retired-
  mechanism language ("read-only module load", "verified once against phase", "load_5b", etc.) reappears
  in current-state artifacts — so this class is caught by the harness, not by external review. Guard
  proven to fire on injection.
ugk/ + kernel.py byte-identical; CGProj gates + adapters unchanged; law_hash unchanged.

## r34 — close the recurring TYPE: G6 no longer re-runs the substrate conformance
Root of every recurring G6 hang: G6 re-ran the substrate's heavy conformance (scale/AL/batch) as a
child process under a FRESH/unfounded genesis, forcing run_gates_batch's _ephemeral_founding_reexec
(a grandchild spawn). The r33 grandchild-proof runner only made a TIMED-OUT child fail-closed at 180s —
far beyond a hostile-session ceiling — so a slow re-exec still read as a hang. r34 removes the cause:
- **G6 no longer re-executes the substrate surface.** The surface modules (ugk/scale, ugk/conformance)
  and CGProj gates (tools/cgproj/) are part of the ratified r17a CGProj RC (which passed scale 7/7,
  AL 22/22, batch 78/78). G6 proves them GREEN BY TRANSITIVITY via byte-identity to r17a (the
  reconciliation it already performs), with an anti-vacuity floor (>=1 surface file present). G6's only
  child processes are now the 9 GRBSA LEAF gates + 2 anti-vacuity stubs — none spawn grandchildren.
  G6 default is bounded and reliable (no heavy/grandchild subprocess on the default path; observed a
  few seconds at clean extraction, but exact timing is environment-dependent and not promised). Pass
  `--full` to additionally re-run scale/AL/batch (grandchild-proof
  runner) for exhaustive verification.
- Consistency guard broadened to catch "once against phase"/"asserted once"; fixed a stale
  explain_adapter docstring; inline-qualified all remaining historical "read-only module load" mentions
  in G4B/G4C provenance as superseded.
ugk/ + kernel.py byte-identical; CGProj gates + adapters unchanged; law_hash unchanged.

## r36 — presentation-surface truth/polish (docs-only + one substrate-doc correction)
Type-level cleanup of the public-facing surface (no code, no gate, no ugk/ change):
- **GRBSA-doc truth (Type A):** GRBSA_MANIFEST.md corrected — it claimed "No substrate file modified",
  but verify_release.sh (r28 import fix) and tests/README.md (r36 gate-count) are modified inherited
  files; the manifest now discloses both precisely. ugk/ + kernel.py remain byte-identical; law_hash
  unchanged.
- **Inherited-substrate docs (Type B):** added a "Scope & inherited substrate" section (this overlay vs
  the byte-identical UGK base) that discloses known pre-existing substrate-doc issues (root README
  broken docs/ links; readme_gen --check stale) as inherited, not GRBSA claims. Corrected the one
  self-contradictory inherited count (tests/README 63 -> 78; the file already said 78 elsewhere).
- **CLI surface (Type C):** documented that `ugk explain` is the substrate invariant/gate/CSIL explainer
  (distinct from the CGProj projection-explain library surface), and that `ugk attest`/`ugk govern`
  require a founded kernel/charter first (else GovernanceNotFounded). Cleaning the traceback would
  require a ugk/cli.py change (breaking byte-identity), so it is documented, not altered.

## r37 — (SUPERSEDED BY r38) first attempt at the genesis/key contamination type
> NOTE: r37 made reconciliation EXCLUDE genesis founding state (so a founded tree passed). r38 reverses
> that — it REFUSES genesis artifacts (does-not-admit) and instead fixes the SOURCE so verification never
> founds <repo>/genesis. Read this section as historical.
Root cause of the reported "added=41 (bad=5)" + "private key shipped": the committed archive is CLEAN
(genesis/README.md only), but FOUNDING the extracted tree (genesis ceremony / `ugk charter` — which the
r36 CLI docs instructed reviewers to run to test attest/govern) writes runtime artifacts into
`<repo>/genesis/`, including `GENESIS_PRIVKEY.hex` (the PUBLIC dev fixture key). G6's reconciliation
then refused the founded tree because it did not exclude genesis founding state. Same class as the
earlier hang: verification/founding contaminating the tree under inspection. Closed structurally:
- **Reconciliation excludes genesis founding state** (GENESIS_PRIVKEY.hex, GENESIS_KEY.pub,
  DEPLOYMENT_MANIFEST.json, LAUNCH_IC.json, VALIDATOR_SET.json, any *.hex under genesis/) exactly like
  __pycache__/*.pyc. A founded tree now reconciles clean (added=36, bad=0). Verified on both a clean and
  a freshly-founded tree.
- **G6 SECURITY check**: private-key material in RELEASE content (*.hex / GENESIS_PRIVKEY outside the
  excluded genesis-runtime location) is a hard FAIL; a founded tree passes with a note that the local
  runtime key is excluded and must never be committed. Proven to fire on a planted key.
- **Inherited-change allowlist**: reconciliation admits exactly {verify_release.sh, tests/README.md} and
  fails on any other non-tools/grbsa change. Proven to fire on a planted README change.
- **Packaging guard** (build): the archive is refused if it contains any *.hex / GENESIS_PRIVKEY /
  founded genesis artifact; genesis/ is scrubbed to README.md and packaged from a never-founded tree.
- **CLI docs** now warn that founding writes a local dev key + genesis artifacts (runtime, never commit).
No code change to ugk/ or kernel.py; law_hash unchanged. Only tools/grbsa/g6 + GRBSA docs changed.

## r38 — ROOT-CAUSE fix for the genesis/private-key contamination (answers "why does this keep happening")
The committed archive was ALWAYS clean (genesis/README.md only; sha-verified). The reported "private
key shipped" + "added=41 (bad=5)" came from the WORKING TREE being founded after extraction: a
conformance batch (run by verify_release.sh / --full) founds <repo>/genesis and, when it HANGS on its
ephemeral-founding grandchild and is killed, its restore never runs — leaving GENESIS_PRIVKEY.hex (the
public dev fixture key) behind. Same class as every prior cycle: verification contaminating the tree it
inspects. Fixed at the SOURCE, three ways:
- **Batch invocations isolate + pre-found genesis.** verify_release.sh and G6 `--full` now point
  UGK_GENESIS_DIR at a throwaway dir AND pre-found it, so (a) founding never touches <repo>/genesis even
  if killed, and (b) the batch runs in-process instead of taking the ephemeral re-exec grandchild path —
  so it neither contaminates nor hangs. Verified: --full ~4s, verify_release completes, <repo>/genesis
  stays README.md-only throughout.
- **G6 reconciliation REFUSES genesis founding artifacts** (does NOT admit them) and FAILS the SECURITY
  check on any *.hex/GENESIS_PRIVKEY anywhere, with a message distinguishing "this tree was founded —
  re-extract" from "the archive is dirty." Proven to FAIL on a founded tree and on planted key material.
- **Required vs exhaustive checks clarified.** G6 default (`--r17a`) is the REQUIRED, reliable
  presentation check (no batch). `--full` and `verify_release.sh` are EXHAUSTIVE checks that re-run the
  substrate conformance batch; r38 makes them reliable, but G6 default remains the gate of record.
- Packaging guard refuses any archive containing *.hex / GENESIS_PRIVKEY / founded genesis / pyc.
ugk/ + kernel.py byte-identical; law_hash unchanged. Changed outside tools/grbsa/: verify_release.sh
(import fix r28 + genesis isolation r38) and tests/README.md (gate count r36) — both declared & admitted.
