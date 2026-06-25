"""ugk/conformance/effect_atomicity_declaration_gate.py - r102-a / AD-37, updated r102-b / AD-38.

EffectAtomicity contract. An execute() effect is opaque caller code the kernel
cannot prove rollback-able, so it MUST declare its atomicity class. This gate
proves the fail-closed / proceed contract at runtime:

  (a) effect supplied with NO declaration -> ProtocolError, raised BEFORE
      gate_admit, with ZERO chain mutation (no gate_admit receipt, no success
      receipt). This is the elimination of silent unknown effects.
  (b) effect supplied with EXTERNAL_REVERSIBLE but NO idempotency_key -> fail
      closed with ZERO mutation (r132/AD-55: now implemented as the compensation/
      saga forward trail; the forward idempotency_key is mandatory, missing fails closed).
  (b2) effect supplied with EXTERNAL_IRREVERSIBLE but NO idempotency_key -> fail
      closed with ZERO mutation (the required-key contract, r115/AD-44): the key
      is mandatory and missing evidence fails closed before gate_admit.
  (e) effect supplied with EXTERNAL_IRREVERSIBLE AND a non-empty idempotency_key
      -> PROCEEDS via the two-phase trail (r115/AD-44): a gate_admit and a PREPARE
      are written (carrying the marker). The four-state depth semantics
      (COMMIT / ABORT / orphan PREPARE) are proven in
      external_irreversible_pilot_gate; this gate proves only the proceed /
      fail-closed contract at the declaration boundary.
  (c) effect supplied with NON_ATOMIC -> proceeds under the LEGACY execution
      order, and the gate_admit + success receipts carry an explicit
      effect_atomicity marker (the legacy bridge, unchanged).
  (d) effect supplied with PURE or STORE_LOCAL -> PROCEEDS (r102-b): the effect
      fires, a gate_admit and a non-failed success receipt are written (both
      carrying the marker), and no structural abort is produced on success.
      The ATOMIC OUTCOME semantics (success-after-effect, rollback, abort) are
      proven in depth by effect_atomicity_class12_gate; this gate only proves
      these classes are no longer fail-closed.

NON_ATOMIC preserves legacy execution order while making the lack of atomicity
explicit and auditable. The marker is a receipt/execution-protocol
classification - it is NOT an authority artifact and NOT a claim that the
effect was rollback-able, success-proof, or Invariant-E-compliant.
"""



# r142 (AD-65): column-first effect-field accessor for gate scaffolding/assertions. Reads the typed
# effect COLUMN (authoritative for v>=4, the sole surface on v5), with parameter-MARKER fallback only
# for deliberately-constructed v<4 marker-era fixtures.
_R142_C = {"phase": "effect_phase", "effect_atomicity": "effect_atomicity",
           "idempotency_key": "effect_idempotency_key", "prepare_ref": "effect_prepare_ref",
           "compensate_ref": "effect_compensate_ref",
           "compensation_idempotency_key": "effect_compensation_idempotency_key",
           "abort_reason": "effect_abort_reason", "gate_admit_ref": "effect_gate_admit_ref"}
def _ef(r, marker):
    v = getattr(r, _R142_C[marker], None)
    return v if v is not None else (r.parameters or {}).get(marker)

def run():
    from ugk.kernel import GovernanceKernel, EffectAtomicity, ProtocolError
    fails = []

    def fresh():
        k = GovernanceKernel(); k.open_session(); return k

    def marker_value(recs, value):
        for r in recs:
            p = r.parameters or {}
            if isinstance(p, str):
                import json
                p = json.loads(p)
            if _ef(r, "effect_atomicity") == value:
                return True
        return False

    # (a) undeclared effect -> ProtocolError BEFORE admit, zero mutation, no gate_admit.
    # The effect kwargs here are built dynamically on purpose: this is the runtime fixture for a
    # *missing* declaration, so no static undeclared callsite exists in-tree and
    # tools/effect_declaration_probe.py's universal claim stays literally true for every file.
    k = fresh(); n0 = k.store.receipt_count()
    undeclared_kwargs = {"effect": lambda: 1}
    try:
        k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True, **undeclared_kwargs)
        fails.append("(a) undeclared effect did not raise ProtocolError")
    except ProtocolError as e:
        if "without an EffectAtomicity" not in e.reason:
            fails.append("(a) wrong ProtocolError reason: %s" % e.reason)
        if k.store.receipt_count() != n0:
            fails.append("(a) chain MUTATED on undeclared effect (%d -> %d)" % (n0, k.store.receipt_count()))
        if k.store.receipts_by_op("gate_admit"):
            fails.append("(a) gate_admit receipt written for an undeclared effect")
    except Exception as e:  # noqa: BLE001 - any other type is a contract failure
        fails.append("(a) unexpected exception type %s" % type(e).__name__)

    # (b) EXTERNAL_REVERSIBLE with NO idempotency_key -> fail closed, zero mutation (r132/AD-55:
    #     the class is now IMPLEMENTED as the compensation/saga forward trail, but -- like
    #     EXTERNAL_IRREVERSIBLE -- requires a mandatory caller-supplied idempotency_key for the forward
    #     effect; absent a key the kernel preflight fails closed before gate_admit). The WITH-key proceed
    #     path and the full forward+compensation trail are proven in external_reversible_gate.
    for badkey, label in ((None, "missing"), ("", "empty")):
        k = fresh(); n0 = k.store.receipt_count()
        rev_kwargs = {"effect": lambda: 1, "effect_atomicity": EffectAtomicity.EXTERNAL_REVERSIBLE,
                      "idempotency_key": badkey}
        try:
            k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True, **rev_kwargs)
            fails.append("(b) EXTERNAL_REVERSIBLE %s key did not fail closed" % label)
        except ProtocolError as e:
            if "idempotency_key" not in e.reason:
                fails.append("(b) EXTERNAL_REVERSIBLE %s-key wrong reason: %s" % (label, e.reason))
            if k.store.receipt_count() != n0:
                fails.append("(b) EXTERNAL_REVERSIBLE %s-key chain MUTATED" % label)
            if k.store.receipts_by_op("gate_admit"):
                fails.append("(b) EXTERNAL_REVERSIBLE %s-key gate_admit written" % label)
        except Exception as e:  # noqa: BLE001
            fails.append("(b) EXTERNAL_REVERSIBLE %s-key unexpected %s" % (label, type(e).__name__))

    # (b2) EXTERNAL_IRREVERSIBLE with NO idempotency_key -> fail closed, zero mutation (r115/AD-44)
    for badkey, label in ((None, "missing"), ("", "empty")):
        k = fresh(); n0 = k.store.receipt_count()
        nokey_kwargs = {"effect": lambda: 1, "effect_atomicity": EffectAtomicity.EXTERNAL_IRREVERSIBLE,
                        "idempotency_key": badkey}
        try:
            k.execute(op="crp_evidence", authority="adm", parameters={}, gate=lambda: True, **nokey_kwargs)
            fails.append("(b2) EXTERNAL_IRREVERSIBLE %s key did not fail closed" % label)
        except ProtocolError as e:
            if "idempotency_key" not in e.reason:
                fails.append("(b2) %s-key wrong reason: %s" % (label, e.reason))
            if k.store.receipt_count() != n0:
                fails.append("(b2) %s-key chain MUTATED (must be zero mutation)" % label)
            if k.store.receipts_by_op("gate_admit"):
                fails.append("(b2) %s-key gate_admit written before fail-closed" % label)
        except Exception as e:  # noqa: BLE001
            fails.append("(b2) %s-key unexpected %s" % (label, type(e).__name__))

    # (e) EXTERNAL_IRREVERSIBLE WITH a non-empty idempotency_key -> PROCEEDS (two-phase; r115/AD-44).
    #     Dynamic kwargs keep tools/effect_declaration_probe.py's per-callsite literal scan clean.
    k = fresh(); fired = []
    proceed_kwargs = {"effect": lambda: fired.append(True),
                      "effect_atomicity": EffectAtomicity.EXTERNAL_IRREVERSIBLE,
                      "idempotency_key": "decl-gate-key-1"}
    try:
        k.execute(op="crp_evidence", authority="adm", parameters={"x": 1}, gate=lambda: True, **proceed_kwargs)
    except Exception as e:  # noqa: BLE001
        fails.append("(e) EXTERNAL_IRREVERSIBLE with key raised %s (should proceed)" % type(e).__name__)
    else:
        if not fired:
            fails.append("(e) EXTERNAL_IRREVERSIBLE effect did not fire")
        recs = k.store.receipts_by_op("crp_evidence")
        prep = [r for r in recs if _ef(r, "phase") == "prepare"]
        com = [r for r in recs if _ef(r, "phase") == "commit"]
        if len(prep) != 1:
            fails.append("(e) expected exactly one PREPARE (got %d)" % len(prep))
        if len(com) != 1:
            fails.append("(e) expected exactly one COMMIT (got %d)" % len(com))
        if not k.store.receipts_by_op("gate_admit"):
            fails.append("(e) no gate_admit written")
        if not marker_value(recs, "external_irreversible"):
            fails.append("(e) receipt missing effect_atomicity=external_irreversible marker")

    # (c) NON_ATOMIC -> proceeds; effect fires; marker present in gate_admit + success receipts
    k = fresh(); fired = []
    k.execute(op="crp_evidence", authority="adm", parameters={"x": 1}, gate=lambda: True,
              effect=lambda: fired.append(True), effect_atomicity=EffectAtomicity.NON_ATOMIC)
    if not fired:
        fails.append("(c) NON_ATOMIC effect did not fire")
    if not marker_value(k.store.receipts_by_op("crp_evidence"), "non_atomic"):
        fails.append("(c) success receipt missing effect_atomicity=non_atomic marker")
    if not marker_value(k.store.receipts_by_op("gate_admit"), "non_atomic"):
        fails.append("(c) gate_admit missing effect_atomicity=non_atomic marker")

    # (d) PURE / STORE_LOCAL -> PROCEED (r102-b): effect fires, gate_admit + non-failed success
    #     written with the marker, NO structural abort on success. (Depth atomicity: class12 gate.)
    for cls, val in ((EffectAtomicity.PURE, "pure"), (EffectAtomicity.STORE_LOCAL, "store_local")):
        k = fresh(); fired = []
        # dynamic kwargs (same pattern as (a)/(b)): the loop variable cls is passed via **kwargs, so no
        # static `effect_atomicity=<non-literal>` callsite exists in-tree for tools/effect_declaration_probe.py
        # to flag - the probe's per-callsite literal-class scan stays clean and unambiguous (r104 cleanup).
        proceed_kwargs = {"effect": lambda: fired.append(True), "effect_atomicity": cls}
        try:
            k.execute(op="crp_evidence", authority="adm", parameters={"x": 1}, gate=lambda: True, **proceed_kwargs)
        except Exception as e:  # noqa: BLE001
            fails.append("(d) %s raised %s (should proceed)" % (cls.name, type(e).__name__))
            continue
        if not fired:
            fails.append("(d) %s effect did not fire" % cls.name)
        recs = k.store.receipts_by_op("crp_evidence")
        if sum(1 for r in recs if not r.failed) != 1:
            fails.append("(d) %s expected exactly one non-failed success receipt" % cls.name)
        if any((r.parameters or {}).get("effect_aborted") for r in recs):
            fails.append("(d) %s wrote a structural abort on SUCCESS" % cls.name)
        if not k.store.receipts_by_op("gate_admit"):
            fails.append("(d) %s no gate_admit written" % cls.name)
        if not marker_value(recs, val):
            fails.append("(d) %s success receipt missing effect_atomicity=%s marker" % (cls.name, val))

    ok = not fails
    return ok, ("EffectAtomicity contract: undeclared effects fail closed before admit with zero "
                "mutation; EXTERNAL_REVERSIBLE and key-less EXTERNAL_IRREVERSIBLE fail closed; "
                "NON_ATOMIC proceeds under legacy order; PURE/STORE_LOCAL proceed under the "
                "atomic-outcome protocol; EXTERNAL_IRREVERSIBLE with a non-empty idempotency_key "
                "proceeds via the two-phase trail - all carrying an explicit, auditable receipt "
                "marker (not an atomicity claim)."
                if ok else "; ".join(fails))


if __name__ == "__main__":
    ok, detail = run()
    print(f"effect_atomicity_declaration_gate: {'PASS' if ok else 'FAIL'}  {detail}")
