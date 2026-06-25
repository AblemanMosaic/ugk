#!/usr/bin/env python3
"""GRBSA - ExecutionAdapter Atomicity-Propagation Gate (r111 / AD-42).

Proves the second relay joint: the GRBSA ExecutionAdapter PROPAGATES the caller-declared EffectAtomicity
verbatim to kernel.execute() (caller declares; relay propagates; kernel enforces) and FAILS CLOSED --
it never defaults, downgrades, or invents a class. A k.execute spy captures exactly what the adapter
passed to the kernel; the store delta and the returned envelope confirm the outcome semantics.

Six properties:
  (a) no-effect exempt          -- effect=None succeeds, no declaration required, no class invented;
  (b) explicit NON_ATOMIC bridge-- legacy class propagated verbatim, succeeds;
  (c) explicit PURE -> r103      -- a failing PURE effect yields the classified atomic abort (no false success);
  (d) missing declaration        -- caller-supplied effect with no class -> RETURNED refused envelope,
                                    NO written receipt, execute() NOT called (no chain-append authority);
  (e) external/unimplemented     -- declared external class fails closed through kernel preflight
                                    (ProtocolError, zero mutation), surfaced as a refused envelope;
  (f) never substitutes          -- across all classes: verbatim propagation or refusal, never a silent class.

This is NOT a member of the G6 fixed aggregate set (the adapter is GRBSA tooling, not ugk/conformance);
it is run directly by the release certification.

Run:  python adapter_atomicity_propagation_gate.py <repo_dir>
Exit 0 iff all properties hold; exit 1 otherwise.
"""
import sys, os

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools", "grbsa"))

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" - " + detail if detail else ""))

from ugk.kernel import GovernanceKernel, EffectAtomicity, ProtocolError
from grbsa_runtime import ExecutionAdapter, execution_success

# r142 (AD-65): column-first effect-field accessor (v>=4/v5 authoritative; marker fallback for v<4 fixtures).
_R142C={"phase":"effect_phase","effect_atomicity":"effect_atomicity","idempotency_key":"effect_idempotency_key",
        "prepare_ref":"effect_prepare_ref","abort_reason":"effect_abort_reason","gate_admit_ref":"effect_gate_admit_ref"}
def _ef(r,mk):
    v=getattr(r,_R142C[mk],None)
    return v if v is not None else (r.parameters or {}).get(mk)

OP = "crp_evidence"          # universal op: works on a freshly constructed kernel, no founding invented
def boom(): raise RuntimeError("boom")


def fresh_with_spy():
    """A fresh kernel whose execute() is wrapped to CAPTURE the effect_atomicity it actually receives
    (the append happens before delegating, so a preflight raise still records what was passed)."""
    k = GovernanceKernel()
    captured = []
    orig = k.execute
    def spy(*a, **kw):
        captured.append(kw.get("effect_atomicity"))
        return orig(*a, **kw)
    k.execute = spy
    return k, k._store, captured


def fresh_with_spy2():
    """Like fresh_with_spy but ALSO captures the idempotency_key execute() receives (r118 / AD-45),
    so the third relay joint (verbatim key propagation) is provable from the capture alone."""
    k = GovernanceKernel()
    cap_class, cap_key = [], []
    orig = k.execute
    def spy(*a, **kw):
        cap_class.append(kw.get("effect_atomicity"))
        cap_key.append(kw.get("idempotency_key"))
        return orig(*a, **kw)
    k.execute = spy
    return k, k._store, cap_class, cap_key


# (a) no-effect exempt: effect=None -> succeeds, no declaration needed, no class invented.
k, s, cap_a = fresh_with_spy()
ra, ea, ta = ExecutionAdapter(k, op=OP).run()
check("(a) no-effect exempt: effect=None succeeds, no refusal, >=1 receipt written",
      execution_success(ra, ea) is True and ra.gate_outcome == "admit" and ea.receipts_written >= 1,
      "written=" + str(ea.receipts_written))
check("(a) no-effect: adapter invents NO class (execute() received effect_atomicity=None)",
      cap_a == [None], "captured=" + str(cap_a))

# (b) explicit NON_ATOMIC bridge -> succeeds; class propagated verbatim.
k, s, cap_b = fresh_with_spy()
rb, eb, tb = ExecutionAdapter(k, op=OP, effect=lambda: {"ok": True},
                              effect_atomicity=EffectAtomicity.NON_ATOMIC).run()
check("(b) explicit NON_ATOMIC bridge: succeeds and NON_ATOMIC propagated verbatim",
      execution_success(rb, eb) is True and cap_b == [EffectAtomicity.NON_ATOMIC],
      "success=" + str(execution_success(rb, eb)) + " captured=" + str(cap_b))

# (c) explicit PURE reaches the r103 atomic-outcome path: a failing PURE effect yields a durable
#     classified structural abort (failed=True, abort_reason=effect_failure, effect_atomicity=pure),
#     written=2 (gate_admit + abort, NO false success -- contrast NON_ATOMIC's 3). The kernel re-raises
#     after the abort; the adapter propagates that (it is a thin observer of effect failures, not a
#     swallower).
k, s, cap_c = fresh_with_spy(); b = s.receipt_count()
raised_c = None
try:
    ExecutionAdapter(k, op=OP, effect=boom, effect_atomicity=EffectAtomicity.PURE).run()
except RuntimeError:
    raised_c = True
rcs = [x for x in s.all_receipts() if getattr(x, "op", None) == OP]
abort = rcs[-1] if rcs else None
pure_reached = (cap_c == [EffectAtomicity.PURE]                            # PURE propagated verbatim
                and raised_c is True                                      # kernel re-raised post-abort
                and abort is not None and abort.failed is True
                and _ef(abort, "abort_reason") == "effect_failure"
                and _ef(abort, "effect_atomicity") == "pure"    # the r103 atomic-seam marker
                and (s.receipt_count() - b) == 2)                         # gate_admit + abort, no false success
check("(c) explicit PURE reaches the r103 atomic-outcome path (classified abort, no false success)",
      pure_reached, "captured=" + str(cap_c) + " written=" + str(s.receipt_count() - b) +
      " abort=" + str({kk: _ef(abort, kk) for kk in ("abort_reason", "effect_atomicity")} if abort else None))

# (d) missing declaration fails closed as a RETURNED refused envelope with NO written receipt and NO
#     execute() call. The adapter has no chain-append authority (distinct from the broker's receipted
#     refusal). Crucially, execute() is NEVER called -- the class is not silently defaulted to NON_ATOMIC.
k, s, cap_d = fresh_with_spy(); b = s.receipt_count()
rd, ed, td = ExecutionAdapter(k, op=OP, effect=lambda: {"ok": True}).run()   # effect supplied, NO class
missing_closed = (rd.gate_outcome == "refuse"
                  and "UndeclaredEffect" in str(rd.core.evaluation)
                  and execution_success(rd, ed) is False
                  and ed.receipts_written == 0
                  and (s.receipt_count() - b) == 0                        # NO receipt written
                  and cap_d == []                                         # execute() NOT called (not defaulted)
                  and td.events == [])                                    # nothing minted, nothing ran
check("(d) missing declaration: returned refused envelope, NO written receipt, execute() NOT called",
      missing_closed, "refusal=" + str(rd.core.evaluation) + " written=" + str(ed.receipts_written) +
      " store_delta=" + str(s.receipt_count() - b) + " captured=" + str(cap_d) + " trace=" + str(td.events))

# (e) EXTERNAL_IRREVERSIBLE WITHOUT an idempotency_key fails closed THROUGH the kernel preflight: the
#     adapter DOES call execute() (it has a declaration), the kernel's missing-key preflight raises
#     ProtocolError with ZERO mutation and NO receipt, and the adapter surfaces it as a refused envelope.
#     The class is propagated verbatim and NO key is invented. (r118/AD-45: the missing-key fail-closed
#     case; EXTERNAL_REVERSIBLE without a key is now the SAME missing-key fail-closed case, r132/AD-55.)
k, s, cap_e, cap_e_key = fresh_with_spy2(); b = s.receipt_count()
re_, ee, te = ExecutionAdapter(k, op=OP, effect=lambda: {"ok": True},
                               effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE).run()  # NO key
external_closed = (re_.gate_outcome == "refuse"
                   and "ProtocolError" in str(re_.core.evaluation)
                   and execution_success(re_, ee) is False
                   and ee.receipts_written == 0
                   and (s.receipt_count() - b) == 0                       # zero mutation
                   and cap_e == [EffectAtomicity.EXTERNAL_IRREVERSIBLE]   # class propagated verbatim
                   and cap_e_key == [None])                               # NO key invented
check("(e) EXTERNAL_IRREVERSIBLE without a key fails closed through kernel preflight (refused, zero mutation, no key invented)",
      external_closed, "refusal=" + str(re_.core.evaluation) + " store_delta=" + str(s.receipt_count() - b) +
      " captured=" + str(cap_e) + " key=" + str(cap_e_key))

# (e2) EXTERNAL_IRREVERSIBLE WITH an idempotency_key PROCEEDS through the kernel's AD-44 two-phase path:
#      the adapter propagates the key VERBATIM, execute() runs PREPARE -> effect -> COMMIT, the run
#      succeeds, and exactly one COMMIT terminal carrying the key is written. (r118/AD-45: the third relay
#      joint -- the key reaches the kernel unaltered, enabling the two-phase trail the kernel alone enforces.)
k2, s2, cap_e2, cap_e2_key = fresh_with_spy2(); SINK_E2 = []
re2, ee2, te2 = ExecutionAdapter(k2, op=OP, effect=lambda: SINK_E2.append(1),
                                 effect_atomicity=EffectAtomicity.EXTERNAL_IRREVERSIBLE,
                                 idempotency_key="K-e2").run()
commits_e2 = sum(1 for r in s2.all_receipts() if _ef(r, "phase") == "commit")
key_in_commit = any(_ef(r, "idempotency_key") == "K-e2"
                    for r in s2.all_receipts() if _ef(r, "phase") == "commit")
external_with_key = (execution_success(re2, ee2) is True
                     and re2.gate_outcome == "admit"
                     and commits_e2 == 1
                     and key_in_commit
                     and cap_e2 == [EffectAtomicity.EXTERNAL_IRREVERSIBLE]
                     and cap_e2_key == ["K-e2"])                          # key propagated VERBATIM
check("(e2) EXTERNAL_IRREVERSIBLE with a key proceeds via two-phase (success, 1 COMMIT carrying the key, key propagated verbatim)",
      external_with_key, "success=" + str(execution_success(re2, ee2)) + " commits=" + str(commits_e2) +
      " key_capture=" + str(cap_e2_key) + " key_in_commit=" + str(key_in_commit))

# (e3) r132/AD-55: EXTERNAL_REVERSIBLE WITH an idempotency_key PROCEEDS through the kernel's AD-55 forward
#      trail: the adapter propagates the class + key VERBATIM, execute() runs PREPARE -> effect -> COMMIT,
#      the run succeeds, and exactly one reversible COMMIT carrying the key is written. Proves the adapter
#      no longer fails closed on the reversible class and invents/defaults no key for it.
k3, s3, cap_e3, cap_e3_key = fresh_with_spy2(); SINK_E3 = []
re3, ee3, te3 = ExecutionAdapter(k3, op=OP, effect=lambda: SINK_E3.append(1),
                                 effect_atomicity=EffectAtomicity.EXTERNAL_REVERSIBLE,
                                 idempotency_key="K-e3").run()
commits_e3 = sum(1 for r in s3.all_receipts()
                 if _ef(r, "phase") == "commit"
                 and _ef(r, "effect_atomicity") == "external_reversible")
key_in_commit3 = any(_ef(r, "idempotency_key") == "K-e3"
                     for r in s3.all_receipts() if _ef(r, "phase") == "commit")
reversible_with_key = (execution_success(re3, ee3) is True
                       and re3.gate_outcome == "admit"
                       and commits_e3 == 1
                       and key_in_commit3
                       and cap_e3 == [EffectAtomicity.EXTERNAL_REVERSIBLE]
                       and cap_e3_key == ["K-e3"])
check("(e3) EXTERNAL_REVERSIBLE with a key proceeds via the AD-55 forward trail (success, 1 reversible COMMIT carrying the key, key propagated verbatim)",
      reversible_with_key, "success=" + str(execution_success(re3, ee3)) + " commits=" + str(commits_e3) +
      " key_capture=" + str(cap_e3_key) + " key_in_commit=" + str(key_in_commit3))

# (f) adapter never defaults, downgrades, or invents the CLASS. Synthesized DIRECTLY from the captures:
#     each declared class reached execute() verbatim; no-effect invented nothing (None); a missing
#     declaration produced NO execute() call at all (not a silent NON_ATOMIC). This is the negation of
#     the broker's pre-r107 defect, now proven for the second relay joint.
never_substitutes = (cap_a == [None]
                     and cap_b == [EffectAtomicity.NON_ATOMIC]
                     and cap_c == [EffectAtomicity.PURE]
                     and cap_d == []
                     and cap_e == [EffectAtomicity.EXTERNAL_IRREVERSIBLE]
                     and cap_e2 == [EffectAtomicity.EXTERNAL_IRREVERSIBLE])
check("(f) adapter never defaults/downgrades/invents the class (verbatim propagation or refusal)",
      never_substitutes,
      "caps=" + str([cap_a, cap_b, cap_c, cap_d, cap_e, cap_e2]))

# (g) adapter never invents, defaults, or alters the KEY (r118/AD-45, the third relay joint): the key
#     reaches execute() exactly as supplied -- None when absent (e), verbatim "K-e2" when present (e2).
never_invents_key = (cap_e_key == [None] and cap_e2_key == ["K-e2"])
check("(g) adapter never defaults/invents/alters the idempotency_key (verbatim or None)",
      never_invents_key, "key_caps=" + str([cap_e_key, cap_e2_key]))

ok = bool(results) and all(r[1] for r in results)   # anti-vacuity: zero checks is not a pass
print("\n  ADAPTER ATOMICITY-PROPAGATION GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
