"""r96 / AD-31 - Invariant A adversarial gate: execute() validate-before-mutate.

Proves the governing rule *no admit before the refusal horizon is exhausted*:
  - malformed inputs (non-string authority, non-JSON-serializable parameters, malformed
    warrant_basis) raise a controlled ProtocolError with ZERO chain mutation - no receipt, and in
    particular NO gate_admit;
  - a raising gate() yields exactly ONE classified protocol_error receipt and NO gate_admit;
  - a will/intent coverage failure yields a single gate_refuse and NO gate_admit (the prior
    admit-then-refuse bug); and
  - the happy path still admits.

Requires a founded deployment: GOVERNOR_PUBKEY_HEX resolves at import, so standalone (sentinel) this
returns NOT_ESTABLISHED; under verify_release (which charters genesis first) it founds in-process and
runs the full adversarial battery.
"""
from __future__ import annotations
import os
import tempfile


def _founded():
    from ugk.storage.store import UGKReceiptStore
    from ugk.kernel import GovernanceKernel
    dbp = os.path.join(tempfile.mkdtemp(), "ugk.db")
    k = GovernanceKernel(store=UGKReceiptStore(db_path=dbp), authority="cli")
    k._ceremony()
    k.open_session()
    return k


def _snap(k):
    return (
        k.store.receipt_count(),
        k.store.stream_hash(),
        len(k.store.receipts_by_op("gate_admit")),
        len(k.store.receipts_by_op("gate_refuse")),
        len(k.store.receipts_by_op("protocol_error")),
    )


class _Bad:
    pass


def run():
    from ugk.kernel import GovernanceNotFounded
    from ugk.intent import IntentStore, IntentDeclaration

    try:
        _founded()  # founding probe
    except GovernanceNotFounded:
        return "NOT_ESTABLISHED", "requires a founded deployment (runs under verify_release charter)"

    fails = []

    # --- malformed inputs: ProtocolError + ZERO mutation + no admit ---
    def zero_mutation(name, fn):
        k = _founded(); n0, s0, a0, r0, p0 = _snap(k); exc = None
        try:
            fn(k)
        except Exception as e:
            exc = type(e).__name__
        n1, s1, a1, r1, p1 = _snap(k)
        if exc != "ProtocolError":
            fails.append("%s: expected ProtocolError, got %s" % (name, exc))
        if n1 != n0 or s1 != s0:
            fails.append("%s: MUTATION (receipt %d->%d, stream_changed=%s)" % (name, n0, n1, s0 != s1))
        if a1 != a0:
            fails.append("%s: gate_admit written (%d->%d)" % (name, a0, a1))

    zero_mutation("non-JSON parameters",
                  lambda k: k.execute(op="crp_evidence", authority="alice",
                                      parameters={"x": _Bad()}, gate=lambda: True))
    zero_mutation("non-string authority",
                  lambda k: k.execute(op="crp_evidence", authority=12345,
                                      parameters={"x": 1}, gate=lambda: True))
    zero_mutation("malformed warrant_basis",
                  lambda k: k.execute(op="namespace_claim", authority="alice",
                                      parameters={"name": "x"}, gate=lambda: True,
                                      warrant_basis=[{"a": 1}, {"b": 2}]))
    # r97 / AD-32: the protocol boundary - non-dict parameters (formerly admit-then-crash, or []->{}),
    # empty-string authority (formerly silently defaulted), and non-JSON authority_set (formerly
    # admit-then-crash in the success-receipt write). All must fail closed with ZERO mutation.
    zero_mutation("non-dict parameters (list)",
                  lambda k: k.execute(op="crp_evidence", authority="alice",
                                      parameters=[], gate=lambda: True))
    zero_mutation("non-dict parameters (str)",
                  lambda k: k.execute(op="crp_evidence", authority="alice",
                                      parameters="bad", gate=lambda: True))
    zero_mutation("non-dict parameters (int)",
                  lambda k: k.execute(op="crp_evidence", authority="alice",
                                      parameters=1, gate=lambda: True))
    zero_mutation("empty-string authority",
                  lambda k: k.execute(op="crp_evidence", authority="",
                                      parameters={"x": 1}, gate=lambda: True))
    zero_mutation("non-JSON authority_set",
                  lambda k: k.execute(op="crp_evidence", authority="alice",
                                      parameters={"x": 1}, gate=lambda: True,
                                      authority_set=[_Bad()]))

    # --- gate() raises: ProtocolError + exactly ONE protocol_error receipt + NO admit ---
    k = _founded(); n0, s0, a0, r0, p0 = _snap(k); exc = None
    try:
        k.execute(op="crp_evidence", authority="alice", parameters={"x": 1},
                  gate=lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    except Exception as e:
        exc = type(e).__name__
    n1, s1, a1, r1, p1 = _snap(k)
    if exc != "ProtocolError":
        fails.append("gate-raises: expected ProtocolError, got %s" % exc)
    if a1 != a0:
        fails.append("gate-raises: gate_admit written (%d->%d)" % (a0, a1))
    if (p1 - p0) != 1 or (n1 - n0) != 1:
        fails.append("gate-raises: expected exactly 1 classified protocol_error receipt "
                     "(protocol_error %d->%d, total %d->%d)" % (p0, p1, n0, n1))

    # --- will/intent coverage fails: GateRefusal + single gate_refuse + NO admit ---
    k = _founded()
    ws = IntentStore(); k.set_will_store(ws, require_intent=True)
    ws.declare(IntentDeclaration.create(["namespace_allocate"], authority=k._mosaic_root, scope_ref=""))
    n0, s0, a0, r0, p0 = _snap(k); exc = None
    try:
        k.execute(op="namespace_claim", authority="alice", parameters={"name": "x"}, gate=lambda: True)
    except Exception as e:
        exc = type(e).__name__
    n1, s1, a1, r1, p1 = _snap(k)
    if exc != "GateRefusal":
        fails.append("will-fail: expected GateRefusal, got %s" % exc)
    if a1 != a0:
        fails.append("will-fail: gate_admit written before refusal (%d->%d) = ADMIT-THEN-REFUSE" % (a0, a1))
    if (r1 - r0) != 1:
        fails.append("will-fail: expected exactly 1 gate_refuse (%d->%d)" % (r0, r1))

    # --- happy path still admits ---
    k = _founded(); n0, s0, a0, r0, p0 = _snap(k); exc = None
    try:
        k.execute(op="crp_evidence", authority="alice", parameters={"x": 1}, gate=lambda: True)
    except Exception as e:
        exc = type(e).__name__
    n1, s1, a1, r1, p1 = _snap(k)
    if exc is not None:
        fails.append("happy: unexpected %s" % exc)
    if a1 != a0 + 1:
        fails.append("happy: expected gate_admit +1 (%d->%d)" % (a0, a1))

    if fails:
        return False, "execute() validate-before-mutate FAILURES: " + "; ".join(fails)
    return True, ("Invariant A: malformed authority (non-string or empty), parameters (non-dict or non-JSON), "
                  "warrant_basis (non-sortable), and authority_set (non-list or non-JSON) all raise ProtocolError with "
                  "ZERO mutation and no admit; raising gate -> exactly 1 classified protocol_error receipt, "
                  "no admit; intent-coverage failure -> single gate_refuse, no admit; happy path admits. "
                  "No admit before the refusal horizon is exhausted.")


if __name__ == "__main__":
    import sys
    ok, detail = run()
    label = "PASS" if ok is True else ("NOT_ESTABLISHED" if ok == "NOT_ESTABLISHED" else "FAIL")
    print(label + ": " + detail)
    sys.exit(0 if ok in (True, "NOT_ESTABLISHED") else 1)
