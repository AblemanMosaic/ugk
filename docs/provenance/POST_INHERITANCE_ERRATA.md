# Post-Inheritance Errata — applied to the re-sealed canonical package
Independent run against the first ARC-COMPLETE tarball (894094bb…) found documentation/
example drift. Option A authorized: patch docs + examples, re-seal; Issue 5 scoped OUT
into its own investigation. Committed surface (ugk/ law + modules) UNCHANGED by this
reseal except where noted; law_hash 546a9e90 unchanged.

RESOLVED in this reseal (docs/examples only):
  Issue 1 — README said 77/77. FIXED → 78/78 gates + 39/39 vectors (badge, run line,
            conformance prose); README law_hash example 75a056a8 → 546a9e90.
  Issue 2 — RELEASE said codex_hash UNRECOVERABLE / CODEX.md not shipped. FIXED →
            25146018… (= SHA-256(ugk/codex/CODEX.md), recoverable & verified). CODEX.md
            IS shipped at ugk/codex/CODEX.md. Also corrected the RELEASE tree_digest line
            to the post-rho value e281f9d0 (158 files; rollback baseline 0ee3a466, 155).
  Issue 3 — examples/application_ops_example.py used GovernanceKernel(db_path=...), not a
            valid constructor (real: store=, authority=). MARKED with a stale-example
            notice naming the real API + charter path. (Not rewritten — retained as
            illustration; not part of the passing suites.)
  Issue 4 — examples/governed_session.py called _ceremony() and fails closed
            (GovernanceNotFounded) on an uncharted tree — correct fail-closed behavior,
            but unrunnable as shipped. MARKED with the same stale-example notice.

KNOWN ISSUE — scoped OUT of this reseal, OPEN for separate investigation:
  Issue 5 — `ugk charter --state-dir DIR` was observed to write genesis files under the
            package's genesis/ path in the extracted tree, not purely inside DIR. This is
            SUBSTRATE/CLI behavior (ugk/cli.py state-dir resolution), not docs. It may be
            intentional (package-relative genesis restore) or a defect. It is NOT changed
            here — changing kernel/CLI behavior under a doc-reseal would be an
            unauthorized substrate mutation. Tracked for the deployment-validation track
            (Phase 3) or a dedicated CLI-behavior investigation. No claim is made that the
            current behavior is correct or incorrect; it is recorded as observed and OPEN.

NOT AFFECTED: §6/§18 doctrine sync, RHO_SOUND_DOMAIN.md, A1/rho dormancy, execute()
(0 rho refs), law_hash, rollback baseline. The three original acceptance bars still hold.

## SUBSTRATE REVISION (deliberate; mints a new inheritance point) — Issue 5 RESOLVED
Authorized as a deliberate substrate revision (NOT a doc cleanup). `ugk charter
--state-dir DIR` now governs genesis placement as well as the SQLite stores:
  - Change: ugk/cli.py _cmd_charter now resolves --state-dir (then UGK_STATE_DIR /
    ACIS_STATE_DIR env) and passes it as write_charter_artifacts(genesis_dir=...).
    Charter help gains a --state-dir row (no silent semantics).
  - Verified end-to-end: charter --state-dir DIR writes GENESIS_KEY.pub +
    DEPLOYMENT_MANIFEST.json INTO DIR; the package genesis/ is left unchanged.
  - Precedence (deterministic): --state-dir > UGK_STATE_DIR/ACIS_STATE_DIR env >
    package-adjacent genesis/ default. Unset → byte-identical to prior behavior
    (conservative; existing suites/fixtures unaffected).
  - Committed-surface impact: cli.py changed → ugk/ tree-digest moved
    e281f9d0 → e6413f28 (158 files). law_hash UNCHANGED (546a9e90; invariants.py
    untouched). rho-rollback baseline moved 0ee3a466 → 98c5076d (155 files) because the
    pre-rho tree now includes the revised cli.py; the rollback PROPERTY (remove the 3 rho
    files → recover the pre-rho tree) still holds, against the new baseline.
  - Full validation re-run: conformance 78/78, M2 vectors 39/39, A1 conservativity 7/7.

## EXAMPLES (Issue 3 & 4) — RESOLVED as package maintenance
Both rewritten to the real API (GovernanceKernel(store=, authority=), DeploymentManifest
.create, write_charter_artifacts) and founded via the public conformance dev fixture into
an isolated temp dir (re-exec so the kernel adopts the founding at import). Both now RUN
end-to-end (governed op → receipts → chain intact) and write nothing into the package
tree. No stale-notice markers remain. examples/ is outside the committed ugk/ surface.

## r4 — example import ergonomics (package maintenance; no substrate change)
Independent run found: examples worked with PYTHONPATH=. from repo root, but failed as
plain scripts (python examples/foo.py → ModuleNotFoundError: No module named 'ugk').
FIX: each example now prepends its repo root to sys.path before importing ugk, so it runs
as a plain script from anywhere. Reproduced the real failure under `python -S` (no
site-packages) and confirmed both examples PASS after the fix in that clean environment.
Examples-only; committed ugk/ surface UNCHANGED (tree-digest e6413f28, law_hash 546a9e90,
rho-rollback baseline 98c5076d all unchanged from r3). Package digest changes (examples/
edited): r3 9478c1e8 → r4 075bd899.

## r5 — Issue 5 READ side end-to-end (X-b launcher shim; substrate revision)
r3 fixed the WRITE side (charter --state-dir writes genesis to DIR). r5 fixes the READ
side: `ugk --state-dir DIR govern/verify` now loads genesis identity from DIR with NO
manual UGK_GENESIS_DIR.

ROOT CAUSE (verified): governor identity binds at ugk.kernel IMPORT time; ugk/__init__.py
eagerly imports ugk.kernel at package load. Setting UGK_GENESIS_DIR inside cli.main() is
structurally too late — the package (and thus identity) is already imported before main()
runs. Authorized fix = X-b (launcher shim), NOT X-a (lazy resolution): identity stays
immutable-at-import.

CHANGE (files modified):
  - ugk/__init__.py: added _cli_state_dir_preimport_hook(), run at the TOP of package init
    BEFORE `from ugk.kernel import ...`. It pre-parses --state-dir from sys.argv and, only
    on a ugk CLI invocation (argv0 ∈ {-m, …/ugk, cli.py, ugk*}), sets UGK_GENESIS_DIR if
    unset. Never overrides an existing UGK_GENESIS_DIR (explicit env wins). Acts only when
    a --state-dir token is actually present. A plain library `import ugk` with no such
    token sets nothing.
  - ugk/cli.py: main() retains a secondary env-set (harmless; the shim is the primary
    mechanism per directive item 4).

KNOWN NARROW EDGE (documented, not over-engineered): because `python -m ugk.cli` exposes
argv0 as '-m' at package-init time, the shim treats argv0=='-m' as a CLI run. A non-ugk
`python -m othertool --state-dir X` that TRANSITIVELY imports ugk would absorb --state-dir
into UGK_GENESIS_DIR (only if UGK_GENESIS_DIR is unset). Mitigated by: the explicit-env
precedence, and that --state-dir is a ugk-specific flag. Acceptable for the CLI-isolation
requirement; revisit if a real collision is reported.

IMPACT: law_hash UNCHANGED (546a9e90; invariants.py untouched). tree-digest
e6413f28 → 0e9bf1c9 (158 files). rho-rollback baseline 98c5076d → a69395a5 (155 files;
pre-rho tree now carries the revised __init__.py + cli.py; rollback PROPERTY holds).
Full stack: conformance 78/78, M2 vectors 39/39, A1 conservativity 7/7, verify_release
PASS, both examples PASS as plain scripts, compileall PASS.
VERIFIED end-to-end: charter→govern→verify with ONLY --state-dir (no UGK_GENESIS_DIR),
separate clean processes; package genesis/ untouched.

## r6 — stale docstring count (package maintenance)
ugk/__init__.py docstring said "run_gates_batch — 27-gate Phase 1 suite". Stale: the
runner and docs report 78/78 (+ 39 M2 vectors), and the suite passes 78/78. FIXED →
"78-gate conformance suite (+ 39 M2 vectors)". Docstring-only; no behavior change. Swept
package-wide — single occurrence, no siblings.
IMPACT: law_hash UNCHANGED (546a9e90). tree-digest 0e9bf1c9 → ead5ffec (158 files;
committed-surface change → re-minted, not patched-in-place). rho-rollback baseline
a69395a5 → 4620e6c2 (155). Full stack re-run: import OK, conformance 78/78, M2 39/39,
A1 conservativity 7/7.

## r7 — remaining stale gate-count comments (package maintenance)
A THOROUGH package-wide sweep (broadened beyond the "27-gate"/"77/77" patterns used in
r6) found FIVE stale references, not the two first reported:
  - ugk/conformance/__init__.py — "Phase 1 conformance gates (27 total)"
  - ugk/conformance/run_gates_batch.py — "Runs all 27 Phase 1 gates ..."
  - ugk/policy.py — "preserves the 77-gate suite's hash stability"
  - ugk/freshness.py (x2) — "In-process tests / 77-gate suite", "so that the 77-gate"
ALL FIVE corrected to 78 (the policy/freshness ones 77→78-gate). Comments/docstrings only;
no behavior change. Re-swept: zero 27/77 gate references remain package-wide.
IMPACT: law_hash UNCHANGED (546a9e90). tree-digest ead5ffec → faf43ecd (158 files).
rho-rollback baseline 4620e6c2 → 33c235a9 (155). Full stack: import OK, conformance
78/78, M2 39/39, A1 conservativity 7/7, compile PASS. (The policy/freshness edits are
comments only — the hash-stability they describe is proven intact by the green suites.)
LESSON: the r6 sweep was too narrow (literal "27-gate"); r7 used a broad numeric+keyword
sweep and verified zero residuals.

## r8 — governed refactor (low-risk batches; logical-map; analysis-only batching)
Executed the authorized low-risk refactor (move/add-only; NO physical ugk/ reorg).
BATCHES:
  1. tests/ index + thin runners (run_fast.py, run_full.py, cli_smoke.sh) invoking the
     in-place gates as a black box — gates NOT moved (63 import paths preserved).
  2. docs/ reorganized: doctrine/ (alt, RECEIPTED_REUSE_BOUNDARY), papers/, and
     provenance/ (this errata trail + ARC_COMPLETION_RECORD, marked as history not public
     surface). Empty canonical/ removed.
  3. examples/ → basic/ (governed_session), governed/ (application_ops, NEW a1_example),
     temporal/ (NEW rho_example). All 4 run as plain scripts; _REPO_ROOT depth fixed.
  4. ugk/ARCHITECTURE.md added — logical role-grouping of the flat modules WITHOUT moving
     them (physical reorg rejected: 292 import edits / 63 gate-path changes). CGP/SRSA
     dedupe clarification: cgp/srsa.py confirmed an INTENTIONAL pure re-export shim of
     core.srsa; cgp/esa is a distinct CGP registry, not a duplicate. No code dedupe needed.
  5. tools/ read-only observability: hygiene_check, import_side_effects, dep_graph,
     refusal_taxonomy. Add-only, outside ugk/.
  6. tools/BATCHING_ANALYSIS.md — analysis only. No class-A candidate (receipt chain's
     order-is-identity + NBER-1 make receipt/session batching class C). NOTHING implemented.
IMPACT: law_hash UNCHANGED (546a9e90). Only committed-surface change = ugk/ARCHITECTURE.md
(a doc). tree-digest faf43ecd → e93c32de (158 → 159 files). rho-rollback baseline
33c235a9 → 02c2100a (156 files). default behavior unchanged; execute() does not call ρ;
A1/ρ dormant; Tier-A unimplemented; CNH/PHCG/PHCG-Spine hypotheses.
ROLLBACK: remove ugk/ARCHITECTURE.md → recover faf43ecd (r7). tests/, docs/ reorg,
examples/, tools/ are all outside ugk/ and do not affect the substrate digest.
VALIDATION: 39/39, 78/78, A1 7/7, ρ ALL PASS, 4 examples PASS, CLI smoke PASS, hygiene CLEAN.
