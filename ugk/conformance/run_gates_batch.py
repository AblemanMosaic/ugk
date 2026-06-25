"""ugk/conformance/run_gates_batch.py — Single-interpreter batch conformance runner.

Runs all 78 conformance gates in a single Python interpreter.
Uses os._exit(0|1) to terminate — bypasses atexit handlers (intentional).

Usage:
    python -m ugk.conformance.run_gates_batch

Exit codes:
    0 — all gates passed
    1 — one or more gates failed
"""
import os
import sys
import time

# r163 portability: force UTF-8-safe console output so the summary glyphs (─ ✓ ✗ •) never raise
# UnicodeEncodeError on a Windows cp1252 console, independent of the caller's environment
# (PYTHONUTF8 / PYTHONIOENCODING). errors="backslashreplace" guarantees no crash on any stream.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

from ugk.conformance import NOT_ESTABLISHED


def __genesis_dir():
    from ugk._paths import genesis_dir
    return genesis_dir()

GATES = [
    # Structural / Grundnorm
    "ugk.conformance.grundnorm_readonly_gate",
    "ugk.conformance.governor_key_unset_gate",   # re-enlivened 2026-06-10 (Option K): CHARTER-S-01 fail-closed
    "ugk.conformance.record_consistency_gate",   # added 2026-06-10: records match implementation
    "ugk.conformance.zero_deps_gate",
    "ugk.conformance.liveness_gate",
    "ugk.conformance.classified_remainders_gate",
    "ugk.conformance.canary_gate",
    # Jurisdiction / enforcement
    "ugk.conformance.three_tier_jurisdiction_gate",
    "ugk.conformance.enforcement_gate",
    "ugk.conformance.bs01_gate",
    "ugk.conformance.error_codes_gate",
    "ugk.conformance.status_transition_gate",
    # Receipt / W/G/E
    "ugk.conformance.nber1_gate",
    "ugk.conformance.admission_gate",
    "ugk.conformance.effect_atomicity_declaration_gate",   # r102-a/AD-37: undeclared effect fails closed before admit; NON_ATOMIC bridge marker
    "ugk.conformance.effect_atomicity_class12_gate",        # r102-b/AD-38: PURE/STORE_LOCAL atomic outcome via the seam; structural abort + clean-path RELEASE failure
    "ugk.conformance.external_irreversible_pilot_gate",     # r115/AD-44: EXTERNAL_IRREVERSIBLE two-phase PREPARE/COMMIT/ABORT + orphan-PREPARE detector; required idempotency_key; conformance-only append-once sink
    "ugk.conformance.pure_migration_r105_gate",             # r105/AD-39: Path-A pilot - enforcement_gate callsite B NON_ATOMIC->PURE; per-callsite migration property
    "ugk.conformance.broker_propagation_gate",              # r107/AD-40: LocalBrokerServer propagates caller-declared EffectAtomicity; fail-closed cutover (missing decl -> receipted refusal; broker chooses no class)
    "ugk.conformance.pure_migration_r108_gate",             # r108/AD-41: Path-A - admission_gate admit-path callsite NON_ATOMIC->PURE; per-callsite migration property (store-reading store-pure effect)
    "ugk.conformance.refusal_gate",
    # CHC / hash / chain
    "ugk.conformance.chc_gate",
    "ugk.conformance.determinism_gate",
    "ugk.conformance.nonrepudiation_gate",
    "ugk.conformance.nonretroactivity_gate",
    "ugk.conformance.chain_gate",
    "ugk.conformance.body_integrity_gate",   # IEL/AD-23: BODY-level receipt integrity (#27)
    "ugk.conformance.mutation_atomicity_gate",   # IEL/AD-24: atomic mutation + preflight (A+E)
    "ugk.conformance.readonly_guard_gate",   # IEL/AD-25: read-only enforcement (D)
    "ugk.conformance.receipt_context_gate",   # IEL/AD-25: receipt-time context (drift)
    "ugk.conformance.migrate_schema_validation_gate",   # IEL/AD-27: migrate_schema validate-before-mutate (A)
    "ugk.conformance.receipt_commitment_integrity_gate",   # IEL/AD-28: full receipt-body integrity
    "ugk.conformance.recovery_gate",
    # Adversarial / CM
    "ugk.conformance.rugpull_gate",
    "ugk.conformance.dimension_selection_gates",
    # Observability
    "ugk.conformance.staleness_gate",
    "ugk.conformance.srsa_vector_gate",
    "ugk.conformance.esa_selfcheck_gate",
    "ugk.conformance.invariant_registry_gate",
    # Phase 2 — cryptographic identity
    "ugk.conformance.governor_signature_gate",
    "ugk.conformance.governor_enforcement_gate",
    "ugk.conformance.governor_interposition_gate",
    "ugk.conformance.dkn_gate",
    # Phase 3 — constitutional finality (CSH)
    "ugk.conformance.csh_gate",
    "ugk.conformance.csh_mcir_gate",
    # Phase 4 — multi-interface surfaces
    "ugk.conformance.ugk_surfaces_gate",
    "ugk.conformance.ugk_facade_gate",
    "ugk.conformance.choke_point_gate",
    # Phase 5 — AbleTools migration
    "ugk.conformance.migration_gate",
    # Persistence
    "ugk.conformance.persistence_gate",
    # Successor lineage
    "ugk.conformance.successor_lineage_gate",
    # Will layer wiring
    "ugk.conformance.intent_receipt_gate",
    "ugk.conformance.will_coverage_gate",
    "ugk.conformance.scope_archive_gate",
    # Will layer + Provenance scope
    "ugk.conformance.intent_declaration_gate",
    "ugk.conformance.will_checker_gate",
    "ugk.conformance.provenance_scope_gate",
    # SSA vocabulary + AbleTools migration
    "ugk.conformance.ssa_vocabulary_gate",
    "ugk.conformance.abletools_migration_gate",
    "ugk.conformance.application_ops_gate",
    # Semantic atlas
    "ugk.conformance.primitive_dependency_gate",
    "ugk.conformance.compound_capability_gate",
    "ugk.conformance.adr_gate",
    "ugk.conformance.codex_integrity_gate",
    "ugk.conformance.codex_freshness_gate",
    "ugk.conformance.readme_freshness_gate",
    "ugk.conformance.implementation_codex_freshness_gate",
    "ugk.conformance.glossary_freshness_gate",  # r166: generated GLOSSARY.md == GLOSSARY.json; refs resolve; required+core terms
    "ugk.conformance.skill_navigation_gate",   # r166: SKILL.md routes to codex+glossary+ugk-explain; targets exist
    "ugk.conformance.invariant_taxonomy_gate",   # r169: invariant taxonomy navigation layer; generated==source; registry-bound
    "ugk.conformance.docs_index_gate",           # r171: docs/index.md generated==source; links resolve; all docs represented
    "ugk.conformance.structural_error_receipt_gate",
    "ugk.conformance.namespace_governance_gate",
    "ugk.conformance.amendment_model_gate",
    "ugk.conformance.amendment_admissibility_gate",
    # Document types
    "ugk.conformance.refusal_warrant_gate",
    "ugk.conformance.amendment_record_gate",
    "ugk.conformance.session_summary_gate",
    # Audit infrastructure
    "ugk.conformance.audit_session_gate",
    "ugk.conformance.legend_archive_gate",
    "ugk.conformance.receipts_for_warrant_gate",
    # Phase 6 — Constitutional Legend + Decision Warrants
    "ugk.conformance.legend_hash_gate",
    "ugk.conformance.compression_roundtrip_gate",
    "ugk.conformance.legend_chc_gate",
    "ugk.conformance.projection_continuity_gate",
    "ugk.conformance.warrant_gate",
    "ugk.conformance.warrant_lineage_gate",
    # Phase 15 — Authority model
    "ugk.conformance.authority_model_gate",
    "ugk.conformance.model_receipt_gate",
    # Phase 16 — ALT instance configuration
    "ugk.conformance.constitutive_probe_gate",
    "ugk.conformance.alt_instance_gate",
    # Phase 17 — Pedagogical surface
    "ugk.conformance.keygen_hygiene_gate",
    "ugk.conformance.constitution_surface_gate",
    # Phase 18 — CGP + unified status
    "ugk.conformance.posture_gate",
    "ugk.conformance.health_surface_gate",
    # Phase 19 — CSIL/GTI floor
    "ugk.conformance.csil_floor_gate",
    "ugk.conformance.csil_topology_gate",
    # Phase 20 — Deployment charter + DKN ordering
    "ugk.conformance.charter_gate",
    # 2026-06-10 — R2 deployer-configurable genesis path + strict warrant materialization
    "ugk.conformance.genesis_path_gate",
    "ugk.conformance.warrant_strict_gate",
    # M2.3o — receipt-level verification (decision procedures D_s/D_c/D_m/D_j)
    "ugk.conformance.binding_verification_gate",
    # r95 / AD-30 - IEL Invariant D: read-only CLI substrate (verify/status/attest) never mutates fs/receipts
    "ugk.conformance.readonly_invariant_gate",
    # r96 / AD-31 - IEL Invariant A: execute() validate-before-mutate (no admit before refusal horizon exhausted)
    "ugk.conformance.execute_validate_before_mutate_gate",
    # r99 / AD-34 - IEL Invariant E: migrate_schema atomicity via the deferred-commit transaction seam
    "ugk.conformance.migrate_schema_atomicity_gate",
    # r101 / AD-36 - IEL Invariant E: seal_and_prune_epoch atomicity (2nd seam-backed destructive path)
    "ugk.conformance.seal_and_prune_atomicity_gate",
    "ugk.conformance.dispatcher_gate",          # CGP universal evidence dispatcher (additive substrate)
    "ugk.conformance.trace_vector_gate",         # FGA explicit committed-surface trace-vector substrate (SB-3a-core)
    "ugk.conformance.terminal_outcome_gate",      # LM-2 additive terminal-outcome classifier (read-only)
    "ugk.conformance.terminal_outcome_commit_gate",  # LM-2 Increment A (AD-51) body-v2 terminal-outcome commitment
    "ugk.conformance.capability_evidence_commit_gate",  # Lane 4b (AD-52) D_cap committed capability-evidence surface (non-aggregating)
    "ugk.conformance.external_reversible_gate",  # r132/AD-55: EXTERNAL_REVERSIBLE compensation/saga forward + separately-governed compensation arc
    "ugk.conformance.effect_trail_integrity_gate",  # r133/AD-56: EFFECT-S-01 class-relative effect-trail integrity (cross-class recompute)
    "ugk.conformance.typed_effect_surface_gate",  # r134/AD-57: UGK-BODY-v4 typed effect surface (schema-closed mirror of the parameters markers)
    "ugk.conformance.capability_sufficiency_policy_gate",  # AD-68 Lane 2a: D_cap sufficiency policy artifact
    "ugk.conformance.continuation_record_surface_gate",  # AD-71 r148: continuation-record schema surface (v7)
    "ugk.conformance.defer_lifecycle_gate",  # DEFER-S-01 r149: DEFER live + emit/resume/resolve/expire/refuse
    "ugk.conformance.bridge_surface_gate",  # CK-BRIDGE Stage 2: UGK-BODY-v8 bridge committed surface (committed-but-unbound)
    "ugk.conformance.bridge_binding_gate",  # CK-BRIDGE Stage 3: BRIDGE-BINDING law — committed v8 surface validity (resolver-parameterized, kernel-free)
    "ugk.conformance.bridge_emission_gate",  # CK-BRIDGE Stage 4: native BRIDGE kernel emission (opt-in; BRIDGE-BINDING-gated; V12/V13 native)
]

_LABEL_WIDTH = 36
_SEP = "─" * 60


def _run_gate(modname: str):
    import importlib
    try:
        mod = importlib.import_module(modname)
        t0 = time.perf_counter()
        ok, detail = mod.run()
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return ok, detail, elapsed_ms
    except Exception as e:
        return False, f"EXCEPTION: {type(e).__name__}: {e}", 0.0


def _ephemeral_founding_reexec():
    """Unfounded-tree handling: kernel identity loads at IMPORT time, so this
    (already-imported) interpreter cannot adopt a founding. Write the PUBLIC
    conformance fixture founding, re-exec the suite in a fresh interpreter,
    restore genesis/ in finally, and exit with the child's code.

    Founded trees: returns immediately (no-op).
    """
    from pathlib import Path
    import subprocess
    genesis = __genesis_dir()
    pub = genesis / "GENESIS_KEY.pub"
    if pub.exists():
        return
    genesis.mkdir(exist_ok=True)
    before = {p.name for p in genesis.iterdir()}
    from ugk.conformance._fixture import DEV_FIXTURE_PRIVKEY, fixture_pubkey
    from ugk.charter import DeploymentManifest, write_charter_artifacts
    manifest = DeploymentManifest.create(
        fixture_pubkey(), "conformance-fixture", "conformance", "trace_only")
    write_charter_artifacts(manifest, force=False)
    (genesis / "GENESIS_PRIVKEY.hex").write_text(DEV_FIXTURE_PRIVKEY + "\n")
    print("  [conformance fixture] tree is unfounded — re-running the suite under an")
    print("  ephemeral fixture founding (public dev key, phase 'conformance-fixture');")
    print("  genesis/ is restored to its prior state afterwards.")
    sys.stdout.flush()
    try:
        rc = subprocess.call([sys.executable, "-m", "ugk.conformance.run_gates_batch"])
    finally:
        for p in genesis.iterdir():
            if p.name not in before:
                p.unlink(missing_ok=True)
        print("  [conformance fixture] ephemeral founding removed — genesis/ restored.")
        sys.stdout.flush()
    os._exit(rc)


def main():
    print(f"\n{'UGK v0.1.0 — Constitutional Conformance Suite':^60}")
    print(_SEP)
    _ephemeral_founding_reexec()
    print(f"  {'Gate':<{_LABEL_WIDTH}} {'Result':<8} {'ms':>6}")
    print(_SEP)

    results = []
    for modname in GATES:
        gate_name = modname.rsplit(".", 1)[-1]
        ok, detail, ms = _run_gate(modname)
        if ok == NOT_ESTABLISHED:
            label = "N/EST"
        elif ok is True:
            label = "PASS"
        else:
            label = "FAIL"
        print(f"  {gate_name:<{_LABEL_WIDTH}} {label:<8} {ms:>5.1f}")
        if label != "PASS":
            print(f"    {'↳':} {detail}")
        results.append((gate_name, ok, detail, ms))

    print(_SEP)
    total = len(results)
    # "passed" uses `is True` so the NOT_ESTABLISHED sentinel can never be mis-tallied.
    passed = sum(1 for _, ok, _, _ in results if ok is True)
    not_est = sum(1 for _, ok, _, _ in results if ok == NOT_ESTABLISHED)
    failed = total - passed - not_est
    total_ms = sum(ms for _, _, _, ms in results)

    # Three first-class buckets. "not-established" is neither pass nor fail and is never
    # folded into either. The run fails (exit 1) iff there is at least one FAIL.
    if failed:
        status = f"{failed} FAILED"
    elif not_est:
        status = f"PASS ({not_est} not-established)"
    else:
        status = "ALL PASS"
    print(f"\n  {passed}/{total} passed  |  {failed} failed  |  {not_est} not-established"
          f"  |  {status}  |  {total_ms:.1f} ms total\n")

    if failed:
        print("  Failed gates:")
        for name, ok, detail, _ in results:
            if ok is not True and ok != NOT_ESTABLISHED:
                print(f"    ✗ {name}: {detail}")
        print()
    if not_est:
        print("  Not-established (run `ugk harden` to establish the posture):")
        for name, ok, detail, _ in results:
            if ok == NOT_ESTABLISHED:
                print(f"    • {name}: {detail}")
        print()

    # os._exit bypasses atexit — intentional for batch finisher.
    # Flush buffers first so output is not lost on non-tty (CI/pipe).
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
