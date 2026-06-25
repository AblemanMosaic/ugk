"""ugk/conformance/intent_declaration_gate.py — WILL-S-01, WILL-S-04."""


def run():
    from ugk.intent import IntentDeclaration, IntentRevocation, IntentStore
    fails = []

    # WILL-S-01: content-addressed, silent edits impossible
    decl = IntentDeclaration.create(
        declared_ops=["analyze_document", "write_report"],
        authority="test_mosaic_root_" + "a" * 32,
        scope_type="session",
        scope_ref="test_session_dkn",
    )

    if not decl.verify_hash():
        fails.append("IntentDeclaration.verify_hash() failed on fresh declaration")
    if len(decl.declaration_hash) != 64:
        fails.append(f"declaration_hash length {len(decl.declaration_hash)}, expected 64")

    # Different ops → different hash (immutability by content-addressing)
    decl2 = IntentDeclaration.create(
        declared_ops=["analyze_document"],
        authority=decl.authority,
        scope_type=decl.scope_type,
        scope_ref=decl.scope_ref,
        timestamp=decl.timestamp,
    )
    if decl.declaration_hash == decl2.declaration_hash:
        fails.append("Different declared_ops produced same hash (content-addressing broken)")

    # declared_ops are sorted and deduped
    decl3 = IntentDeclaration.create(
        declared_ops=["write_report", "analyze_document", "analyze_document"],
        authority=decl.authority, scope_type=decl.scope_type,
        scope_ref=decl.scope_ref, timestamp=decl.timestamp,
    )
    if decl3.declared_ops != decl.declared_ops:
        fails.append(f"declared_ops not sorted+deduped: {decl3.declared_ops}")

    # WILL-S-04: revocation is permanent
    store = IntentStore()
    store.declare(decl)

    active = store.active_declarations(scope_ref=decl.scope_ref)
    if not any(d.declaration_hash == decl.declaration_hash for d in active):
        fails.append("Declaration not found in active_declarations after declare()")

    revocation = IntentRevocation.create(
        revoked_declaration_hash=decl.declaration_hash,
        authority=decl.authority,
    )
    store.revoke(revocation)

    if not store.is_revoked(decl.declaration_hash):
        fails.append("is_revoked() returned False after revoke()")

    active_after = store.active_declarations(scope_ref=decl.scope_ref)
    if any(d.declaration_hash == decl.declaration_hash for d in active_after):
        fails.append("Revoked declaration still appears in active_declarations")

    # Revocation itself is content-addressed
    rev2 = IntentRevocation.create(
        revoked_declaration_hash=decl.declaration_hash,
        authority=decl.authority,
        timestamp=revocation.timestamp,
    )
    if revocation.revocation_hash != rev2.revocation_hash:
        fails.append("IntentRevocation not deterministic (same inputs, different hash)")

    ok = not fails
    return ok, (
        "WILL-S-01/04: IntentDeclaration content-addressed; different ops → different "
        "hash; revocation permanent; revoked decl excluded from active_declarations." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"intent_declaration_gate: {'PASS' if ok else 'FAIL'}  {detail}")
