"""ugk/conformance/scope_archive_gate.py — SCOPE-S-01/02: ProvenanceScope stored, replay bounded."""


def run():
    from ugk.kernel import GovernanceKernel
    from ugk.scope import ProvenanceScope
    from ugk.storage.binding import LEGEND_HASH
    fails = []

    # --- SCOPE-S-01: ProvenanceScope emitted at session_open ---
    k = GovernanceKernel()
    k._ceremony()
    k.open_session()

    if not k._current_scope_id:
        fails.append("kernel._current_scope_id is empty after open_session()")

    scopes = k.store.scopes_for_authority(k._mosaic_root)
    if not scopes:
        fails.append("No ProvenanceScope in scope_archive after open_session()")
    else:
        s = scopes[-1]
        if s.session_dkn != k._session_dkn:
            fails.append(f"ProvenanceScope.session_dkn mismatch")
        if s.law_hash != k._law_hash:
            fails.append(f"ProvenanceScope.law_hash mismatch")
        if s.legend_hash != k._legend_hash:
            fails.append(f"ProvenanceScope.legend_hash mismatch")
        if not s.verify_id():
            fails.append("ProvenanceScope.verify_id() failed")
        if s.scope_id != k._current_scope_id:
            fails.append("scope_archive scope_id != kernel._current_scope_id")

    # --- prior_scope_id chains sessions ---
    session1_scope_id = k._current_scope_id
    k.close_session()

    k.open_session()
    scopes2 = k.store.scopes_for_authority(k._mosaic_root)
    if len(scopes2) < 2:
        fails.append(f"Expected ≥2 scopes after 2 sessions, got {len(scopes2)}")
    else:
        s2 = scopes2[-1]
        if s2.prior_scope_id != session1_scope_id:
            fails.append(
                f"Second session prior_scope_id {s2.prior_scope_id[:8]!r}… "
                f"!= first session scope_id {session1_scope_id[:8]!r}…"
            )

    # --- SCOPE-S-02: replay admissibility — session_dkn is scope-bound ---
    # Direct test: two different session_dkns → two different scope_ids
    all_scopes = k.store.scopes_for_authority(k._mosaic_root)
    dkns = {s.session_dkn for s in all_scopes}
    if len(dkns) < 2:
        # Only pass check: we have at least two scopes with different session_dkns
        scope_ids = {s.scope_id for s in all_scopes}
        if len(scope_ids) < 2:
            fails.append("Two sessions produced same scope_id (scope not session-unique)")
    else:
        # Different dkns must map to different scope_ids
        dkn_to_scope = {s.session_dkn: s.scope_id for s in all_scopes}
        if len(set(dkn_to_scope.values())) != len(dkn_to_scope):
            fails.append("Multiple session_dkns share a scope_id (scope not unique per session)")

    ok = not fails
    return ok, (
        "SCOPE-S-01/02: ProvenanceScope emitted at session_open; verify_id passes; "
        "scope archived in ugk.db; prior_scope_id chains sessions; "
        "two sessions produce two distinct scope_ids (replay boundary)." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"scope_archive_gate: {'PASS' if ok else 'FAIL'}  {detail}")
