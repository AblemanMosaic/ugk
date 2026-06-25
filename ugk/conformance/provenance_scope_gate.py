"""ugk/conformance/provenance_scope_gate.py — SCOPE-S-01: ProvenanceScope emitted and stored."""


def run():
    from ugk.scope import ProvenanceScope, ScopeArchive
    from ugk.storage.binding import LEGEND_HASH
    fails = []

    mosaic = "mosaic_" + "a" * 40
    dkn1   = "dkn_session_1_" + "a" * 20
    dkn2   = "dkn_session_2_" + "b" * 20
    law    = "l" * 64

    # scope_id is content-addressed
    s1 = ProvenanceScope.create(
        authority_surface=mosaic, session_dkn=dkn1,
        law_hash=law, legend_hash=LEGEND_HASH, prior_scope_id="",
    )
    if not s1.verify_id():
        fails.append("ProvenanceScope.verify_id() failed on fresh scope")

    # prior_scope_id chains sessions
    s2 = ProvenanceScope.create(
        authority_surface=mosaic, session_dkn=dkn2,
        law_hash=law, legend_hash=LEGEND_HASH, prior_scope_id=s1.scope_id,
    )
    if s2.prior_scope_id != s1.scope_id:
        fails.append("prior_scope_id not chained correctly")
    if s2.scope_id == s1.scope_id:
        fails.append("Different sessions produced same scope_id")

    # ScopeArchive stores and retrieves
    arch = ScopeArchive()
    arch.seal(s1)
    arch.seal(s2)

    # Query by authority
    scopes = arch.scopes_for_authority(mosaic)
    if len(scopes) != 2:
        fails.append(f"Expected 2 scopes for authority, got {len(scopes)}")

    # latest_scope_id
    latest = arch.latest_scope_id(mosaic)
    if latest not in (s1.scope_id, s2.scope_id):
        fails.append(f"latest_scope_id returned unknown id: {latest[:16]!r}…")

    # session_is_in_scope
    if not arch.session_is_in_scope(dkn1, s1.scope_id):
        fails.append("session_is_in_scope returned False for dkn1 in s1")
    if arch.session_is_in_scope(dkn1, s2.scope_id):
        fails.append("session_is_in_scope returned True for dkn1 in s2 (wrong scope)")

    # Idempotent seal
    arch.seal(s1)
    if len(arch.scopes_for_authority(mosaic)) != 2:
        fails.append("Duplicate seal added extra row (not idempotent)")

    ok = not fails
    return ok, (
        f"SCOPE-S-01: ProvenanceScope content-addressed (verify_id passes); "
        f"prior_scope_id chains sessions; ScopeArchive stores/queries correctly; "
        f"session_is_in_scope correct; idempotent seal." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"provenance_scope_gate: {'PASS' if ok else 'FAIL'}  {detail}")
