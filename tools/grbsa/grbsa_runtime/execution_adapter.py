"""grbsa_runtime.execution_adapter — ExecutionAdapter (GRBSA G5, highest-risk).

Wraps the REAL kernel `execute()` (W/G/E reactor) as a receipt-bound continuation OBSERVER. execute()
already owns NBER-1 (gate_admit -> success receipt -> effect) and all authority/founding/declaration
checks. This adapter does NOT add, bypass, duplicate, or re-implement any of that. It:
  - takes an ALREADY-FOUNDED kernel + an execute() call spec,
  - records receipt_count before,
  - calls the REAL execute(),
  - OBSERVES the single outcome receipt execute() wrote (it does NOT mint a parallel receipt),
  - maps it into ExecutionReceipt/ExecutionResultEnvelope shape.

Strict invariants (ratified):
  - no ugk/ change, no kernel.py change;
  - adapter never originates authority (no governor_sig, no authority_set, no gate_margin lowering);
  - adapter never founds the kernel;
  - adapter writes NO receipt (observes the one execute() writes);
  - gate refusal is FIRST-CLASS: a refused execution -> valid ExecutionReceipt, execution_success=False.

Equivalence is on the Receipt Sufficiency Principle (admissibility + success semantics + lineage
shape), never receipt-hash identity (chain hash binds ts).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Callable, Any

from .gate_adapter import ReceiptCore, ResultEnvelopeCore, PostureRefusal, _Trace


# ---- Execution domain extensions (4th domain) ----
@dataclass(frozen=True)
class ExecutionReceipt:
    core: ReceiptCore
    op: str
    authority_ref: str            # a REFERENCE to the authority used (not the value)
    gate_outcome: str             # 'admit' | 'refuse'
    domain: str = "execution"     # explicit category tag (Category-Separation)


@dataclass(frozen=True)
class ExecutionResultEnvelope:
    core: ResultEnvelopeCore
    effect_result_ref: str        # ref/string of the effect result (not necessarily the value)
    failed: bool
    receipts_written: int         # how many chain receipts execute() wrote (observed, not minted)
    domain: str = "execution"     # explicit category tag (Category-Separation)


# ---- success semantics: predicate over receipt+envelope (in neither core/extension) ----
def execution_success(receipt: ExecutionReceipt, envelope: ExecutionResultEnvelope) -> bool:
    """Execution succeeds iff: domain match (separation) AND the gate ADMITTED AND not failed AND a
    real chain receipt was written (>=1). Gate REFUSAL is a first-class NON-success that is still a
    valid receipt (execution_success=False, not an error)."""
    if getattr(receipt, "domain", None) != "execution" or getattr(envelope, "domain", None) != "execution":
        return False
    if receipt.gate_outcome != "admit":
        return False                       # refusal is first-class non-success
    if envelope.failed:
        return False
    if envelope.receipts_written < 1:
        return False                       # vacuous: nothing receipted
    return True


class ExecutionAdapter:
    """Observes a real execute() call on an ALREADY-FOUNDED kernel. Mints nothing.

    The caller supplies the founded kernel and the execute() arguments. The adapter NEVER founds the
    kernel and NEVER supplies authority the caller didn't pass.

    Test seams (used ONLY by the equivalence gate's negative controls):
      _attempt_authority=True  -> adapter tries to inject governor_sig it wasn't given (must be refused)
    """
    def __init__(self, kernel, *, op: str, authority: str = "adm", parameters: Optional[dict] = None,
                 gate: Optional[Callable[[], bool]] = None, effect: Optional[Callable[[], Any]] = None,
                 effect_atomicity: Optional["EffectAtomicity"] = None,
                 idempotency_key: Optional[str] = None,
                 adapter_op: str = "execution_observe",
                 _attempt_authority: bool = False):
        self.kernel = kernel
        self.op = op
        self.authority = authority
        self.parameters = parameters or {}
        self.gate = gate if gate is not None else (lambda: True)
        # r111 (AD-42): the relay no longer assigns the atomicity class on the caller's behalf.
        # `effect` defaults to the TRUE no-effect sentinel None (not a no-op lambda); a caller-supplied
        # effect REQUIRES an explicit effect_atomicity (fail-closed in run()). The adapter propagates the
        # caller's class verbatim and never defaults, downgrades, or invents it. (Caller declares; relay
        # propagates; kernel enforces -- the r107 principle, second relay joint.)
        # r118 (AD-45): the THIRD relay joint -- the caller-supplied idempotency_key is propagated verbatim
        # to execute() the same way; the adapter never invents, defaults, or pre-judges it. The kernel is
        # the SOLE enforcer (a missing key for EXTERNAL_IRREVERSIBLE fails closed in execute()'s preflight,
        # surfaced here as a ProtocolError refused envelope -- the adapter adds no key pre-check).
        self.effect = effect
        self.effect_atomicity = effect_atomicity
        self.idempotency_key = idempotency_key
        self.adapter_op = adapter_op
        self._attempt_authority = _attempt_authority

    def _admissibility(self) -> tuple:
        # authority boundary: the adapter's OWN op must not be a posture op, and it must not try to
        # originate execution authority (governor_sig) it was not given.
        from ugk.scale.oracle import POSTURE_OPS
        if self.adapter_op in POSTURE_OPS:
            raise PostureRefusal("adapter attempted posture op: " + self.adapter_op)
        if self._attempt_authority:
            raise PostureRefusal("adapter attempted to originate execution authority (governor_sig)")
        return ("c_execution.v1",)

    def run(self) -> tuple:
        from ugk.kernel import GateRefusal, GovernanceNotFounded, ProtocolError
        trace = _Trace()
        criteria = self._admissibility()             # may raise PostureRefusal (authority teeth)
        store = self.kernel._store
        before = store.receipt_count()

        # NBER-1 is owned by execute(): it writes the receipt BEFORE the effect. The adapter records
        # the receipt as observed AFTER execute() returns; the ordering guarantee is execute()'s.
        gate_outcome = "admit"
        failed = False
        result_ref = ""
        refusal_class = None
        # r111 (AD-42): fail closed BEFORE execute() when a caller-supplied effect carries no declared
        # class. The adapter has NO chain-append authority (ratified invariant), so this is a RETURNED
        # refused ExecutionReceipt envelope with NO written receipt and NO execute() call -- distinct from
        # the broker, whose missing-declaration refusal is a receipted failed=True row. Nothing is minted
        # and nothing runs, so the trace is left empty (no receipt_minted / effect_ran marks).
        if self.effect is not None and self.effect_atomicity is None:
            gate_outcome = "refuse"
            refusal_class = "UndeclaredEffect"
        else:
            try:
                trace.mark("receipt_minted")             # execute() will write the receipt before effect
                res = self.kernel.execute(op=self.op, authority=self.authority, parameters=self.parameters,
                                          gate=self.gate, effect=self.effect,
                                          effect_atomicity=self.effect_atomicity,
                                          idempotency_key=self.idempotency_key)
                trace.mark("effect_ran")
                result_ref = repr(res)[:120]
            except GateRefusal as e:
                gate_outcome = "refuse"
                refusal_class = "GateRefusal"
                trace.mark("effect_ran")                 # no effect; refusal is terminal but receipted
            except GovernanceNotFounded as e:
                gate_outcome = "refuse"
                refusal_class = "GovernanceNotFounded"
                trace.mark("effect_ran")
            except ProtocolError as e:
                # r111 (AD-42) / r118 (AD-45): execute()'s preflight refuses with ZERO mutation and NO
                # receipt when a DECLARED class cannot proceed -- now either EXTERNAL_REVERSIBLE (protocol
                # still unimplemented) OR EXTERNAL_IRREVERSIBLE submitted WITHOUT an idempotency_key
                # (missing-key fail-closed; with a key it PROCEEDS via the AD-44 two-phase path). The
                # adapter surfaces it as a first-class refused envelope (the kernel wrote no receipt). This
                # is distinct from UndeclaredEffect (no class at all -> refuse before execute()).
                gate_outcome = "refuse"
                refusal_class = "ProtocolError"
                trace.mark("effect_ran")

        after = store.receipt_count()
        written = after - before

        # observe (do NOT mint) the outcome receipt execute() wrote for this op
        observed_failed = False
        if refusal_class is None:
            outcome = [r for r in store.all_receipts() if getattr(r, "op", None) == self.op]
            if outcome:
                observed_failed = bool(getattr(outcome[-1], "failed", False))
        failed = observed_failed

        receipt = ExecutionReceipt(
            core=ReceiptCore(
                proposal={"op": self.op, "adapter_op": self.adapter_op},
                criteria=criteria,
                evaluation=("admissible",) if gate_outcome == "admit" else ("refused:" + (refusal_class or "gate"),),
                authority={"warrant": "kernel-execute", "law_ref": "law_hash"},
                outcome="admitted" if gate_outcome == "admit" else "refused",
                lineage={"prior": "0" * 64, "position": before, "produces_effects": ()},
            ),
            op=self.op,
            authority_ref="authority:" + str(self.authority),
            gate_outcome=gate_outcome,
        )
        env = ExecutionResultEnvelope(
            core=ResultEnvelopeCore(
                status="pass" if (gate_outcome == "admit" and not failed) else "fail",
                evidence_refs=(("refusal:" + refusal_class,) if refusal_class else (result_ref,)),
                timing={},
                result_hash="",   # not asserted (receipt-hash identity not claimed)
                lineage={"produced_effects": (), "delta": written},
            ),
            effect_result_ref=result_ref,
            failed=failed,
            receipts_written=written,
        )
        return receipt, env, trace
