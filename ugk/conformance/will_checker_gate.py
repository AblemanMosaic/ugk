"""ugk/conformance/will_checker_gate.py — WILL-S-02, WILL-S-03."""


def run():
    from ugk.intent import IntentDeclaration, WL_001, WL_005
    from ugk.will import WillChecker, COVERED, OUTSIDE
    fails = []
    checker = WillChecker()

    auth = "mosaic_" + "a" * 40

    def make_decl(ops, scope_ref=""):
        return IntentDeclaration.create(declared_ops=ops, authority=auth,
                                        scope_ref=scope_ref)

    # WILL-S-02: R_int is the fixpoint
    decl = make_decl(["analyze_document"])
    edges = {"analyze_document": {"write_report"}}

    # Direct cover (depth=0)
    out = checker.covers("analyze_document", [decl])
    if out.status != COVERED:
        fails.append(f"Direct cover missed: analyze_document not covered by its own declaration")

    # Closure-derived cover
    out2 = checker.covers("write_report", [decl], production_edges=edges)
    if out2.status != COVERED:
        fails.append("Closure cover missed: write_report not reachable from analyze_document")
    if out2.intent_ref != decl.declaration_hash:
        fails.append(f"intent_ref wrong: {out2.intent_ref[:8]!r}… != {decl.declaration_hash[:8]!r}…")

    # Literal match (depth=0) refuses re-derivable effect
    out3 = checker.covers("write_report", [decl], production_edges=edges, depth=0)
    if out3.status != OUTSIDE:
        fails.append("depth=0 should refuse closure-derived effect write_report")

    # WILL-S-03: fail-closed
    # Empty active_declarations → WL-005
    out_empty = checker.covers("analyze_document", [])
    if out_empty.status != OUTSIDE or out_empty.refusal_code != WL_005:
        fails.append(f"Empty intents: expected WL-005, got {out_empty.refusal_code}")

    # Op outside R_int → WL-001
    out_outside = checker.covers("unplanned_op", [decl])
    if out_outside.status != OUTSIDE or out_outside.refusal_code != WL_001:
        fails.append(f"Outside op: expected WL-001, got {out_outside.refusal_code}")

    # Multi-declaration: union of declared_ops
    decl_a = make_decl(["A"])
    decl_b = make_decl(["B"])
    out_both = checker.covers("B", [decl_a, decl_b])
    if out_both.status != COVERED:
        fails.append("Multi-decl: B should be covered when declared_b includes B")

    # Transitive closure terminates (no infinite loop)
    circular_edges = {"X": {"Y"}, "Y": {"X"}}
    decl_x = make_decl(["X"])
    out_circ = checker.covers("Y", [decl_x], production_edges=circular_edges)
    if out_circ.status != COVERED:
        fails.append("Circular edges: Y should be reachable from X via closure")

    ok = not fails
    return ok, (
        "WILL-S-02/03: R_int fixpoint correct (direct + closure); "
        "depth=0 literal match; empty intents → WL-005; "
        "outside op → WL-001; multi-decl union; circular edges terminate." if ok
        else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"will_checker_gate: {'PASS' if ok else 'FAIL'}  {detail}")
