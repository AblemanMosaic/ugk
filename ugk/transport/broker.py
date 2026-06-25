"""ugk/broker.py — BrokerClient interface + LocalBrokerServer stub (Grundnorm layer, 444).

BrokerClient defines the Ring 2 boundary: the interface between a tool process
(which holds request-rights only) and the broker (which holds effect-rights AND
receipt-chain append authority).

Ring 2 architectural property:
  Tool processes call BrokerClient.execute() — they can only make requests.
  The broker implementation performs effects and writes receipts.
  A tool that constructs its own BrokerClient still only makes requests;
  only the concrete broker implementation performs ambient I/O.

LocalBrokerServer: in-process reference implementation (dev/test).
  - No OS isolation (no seccomp/container/WASI).
  - is_isolated() returns False.
  - NOT the only module permitted to make ambient I/O calls — UGK substrate
    does not restrict ambient I/O at the Python process level (CR-01 declared).
    Ring 1 enforcement is an application-layer concern (AbleTools Phase 5).

Phase 2+ deployments: provide a concrete BrokerClient subclass that connects
to an isolated broker process (IPC / WASI / seccomp worker).

Classified Remainder: Ring 2 confinement is deployer-provided.
  CR-01 applies: OS-level isolation is outside UGK's reach.
  UGK ships BrokerClient to make the interface contract explicit; the
  isolation guarantee is the deployer's responsibility.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


# ---------------------------------------------------------------------------
# GovernedRequest — structured carrier (r107 / AD-40)
# ---------------------------------------------------------------------------

@dataclass
class GovernedRequest:
    """A governed request submitted through a BrokerClient (r107 / AD-40).

    The caller-declared `effect_atomicity` travels WITH the request — the broker
    does NOT choose a class on the caller's behalf. The broker propagates the
    declaration to kernel.execute(); the kernel enforces. Minimal carrier: the
    isolated / named-op registry model is design-reserved, not built here.

    The caller-supplied `idempotency_key` likewise travels WITH the request
    (r118 / AD-45 — the third relay joint, after effect r107 and class r111). The
    broker propagates it VERBATIM to kernel.execute() and never invents, defaults,
    or pre-judges it. The kernel remains the SOLE enforcer: a missing key for an
    EXTERNAL_IRREVERSIBLE effect fails closed at the kernel preflight (ProtocolError,
    zero mutation), surfaced by the broker as admitted=False — the broker does NOT
    add a key pre-check (that would duplicate the kernel's contract).

    Contract: if `effect` is not None, `effect_atomicity` MUST be a declared
    EffectAtomicity — an effect with no declaration fails closed at the broker
    (receipted refusal). A no-effect request needs no declaration. The key is
    enforced by the kernel, not the broker.
    """
    op:               str
    authority:        str
    parameters:       dict
    intent:           Optional[str] = None
    jurisdiction:     str = "session"
    gate:             Optional[Any] = None
    effect:           Optional[Any] = None
    effect_atomicity: Optional[Any] = None   # EffectAtomicity; caller-declared (None = undeclared)
    idempotency_key:  Optional[str] = None   # r118/AD-45: caller-supplied; propagated verbatim, kernel-enforced


# ---------------------------------------------------------------------------
# BrokerClient — abstract interface (Ring 2 boundary)
# ---------------------------------------------------------------------------

class BrokerClient(ABC):
    """Abstract broker interface.

    All concrete broker implementations subclass this.  GovernedContext
    (in a UGK consumer application) holds a BrokerClient reference — it never
    references LocalBrokerServer or any concrete broker directly.
    """

    @abstractmethod
    def submit(self, request: GovernedRequest) -> dict:
        """Submit a governed request to the broker (r107 / AD-40 carrier shape).

        `request` carries the caller-declared `effect_atomicity`. The broker
        propagates the declaration to the kernel; it MUST NOT choose a class on
        the caller's behalf.

        Returns a result dict with at minimum:
          {"admitted": bool, "receipt_hash": str, "payload": Any}

        Must never raise — errors are returned as admitted=False with a reason.
        Per NBER-1, refusal is first-class and receipted, not silent: an effect
        present with NO declaration fails closed with a receipted refusal.
        """
        ...

    @abstractmethod
    def broker_posture(self) -> str:
        """One-line posture string for observability.

        Examples:
          'LocalBrokerServer (dev/test — no OS isolation)'
          'IpcBrokerClient (connected to unix:/tmp/ugk-broker.sock)'
          'WasiBrokerClient (WASI worker — structurally confined)'
        """
        ...

    @abstractmethod
    def is_isolated(self) -> bool:
        """True if the broker runs in a structurally confined environment.

        LocalBrokerServer returns False (in-process, no OS isolation).
        A production IPC broker with seccomp/container isolation returns True.
        Used by governance status checks to flag non-isolated deployments.
        """
        ...


# ---------------------------------------------------------------------------
# LocalBrokerServer — in-process reference implementation (dev/test)
# ---------------------------------------------------------------------------

class LocalBrokerServer(BrokerClient):
    """In-process broker reference (dev/test posture).

    Implements BrokerClient.  Routes submissions through a GovernanceKernel
    execute() call.  No OS isolation — is_isolated() returns False.

    Posture:
      - Dev/test only.  Production deployments should substitute an
        IpcBrokerClient with seccomp/container isolation.
      - Broker authority property satisfied at the in-process level:
        callers submit requests via submit(); only this broker calls
        kernel.execute() on their behalf.
    """

    POSTURE = "LocalBrokerServer (dev/test — in-process, no OS isolation)"

    def __init__(self, kernel: Any):
        """kernel: GovernanceKernel instance to route requests through."""
        self._kernel = kernel

    def broker_posture(self) -> str:
        return self.POSTURE

    def is_isolated(self) -> bool:
        return False  # in-process: no seccomp/container/WASI isolation

    def submit(self, request: GovernedRequest) -> dict:
        """Route a governed request through the kernel's W/G/E execute() (r107 / AD-40; r118 / AD-45).

        The caller-declared `request.effect_atomicity` and `request.idempotency_key`
        are propagated verbatim to kernel.execute(); the broker does NOT default,
        downgrade, or pre-judge either. A missing key for an EXTERNAL_IRREVERSIBLE
        effect fails closed at the KERNEL preflight (ProtocolError), surfaced here as
        admitted=False with no receipt. Returns {"admitted": True/False,
        "receipt_hash": str, "payload": Any}; never raises.
        """
        from ugk.kernel import (GateRefusal, KernelInternalOp, GovernanceNotFounded,
                                 UndeclaredOp, ProtocolError)
        # FAIL-CLOSED CUTOVER (r107/AD-40): an effect with NO caller declaration is refused
        # at the broker with a RECEIPTED refusal (NBER-1) — the broker never substitutes a
        # default class (the old line-141 NON_ATOMIC hardcode is gone). The kernel preflight
        # is zero-mutation for an undeclared effect, so the broker records the refusal via its
        # chain-append authority before returning admitted=False. (No-effect needs no class.)
        if request.effect is not None and request.effect_atomicity is None:
            rec = self._kernel.store.write(
                op=request.op,
                authority=request.authority,
                parameters={**request.parameters,
                            "broker_refused": True,
                            "refuse_reason": "missing_effect_atomicity_declaration"},
                failed=True,
                jurisdiction=request.jurisdiction,
            )
            return {"admitted": False, "receipt_hash": getattr(rec, "h_r", "") or "",
                    "reason": "missing effect_atomicity declaration (effect present, no class)",
                    "payload": None}
        try:
            result = self._kernel.execute(
                op=request.op,
                authority=request.authority,
                parameters=request.parameters,
                gate=request.gate,
                effect=request.effect,
                jurisdiction=request.jurisdiction,
                effect_atomicity=request.effect_atomicity,   # caller-declared; None only when no effect
                idempotency_key=request.idempotency_key,      # r118/AD-45: verbatim; kernel is sole enforcer
            )
            tip = self._kernel.store.stream_hash()
            return {"admitted": True, "receipt_hash": tip, "payload": result}
        except GateRefusal as e:
            tip = self._kernel.store.stream_hash()
            return {"admitted": False, "receipt_hash": tip,
                    "reason": f"GateRefusal: {e.reason}", "payload": None}
        except (KernelInternalOp, GovernanceNotFounded, UndeclaredOp, ProtocolError) as e:
            # protocol-boundary rejections, incl. unknown / unimplemented effect classes:
            # the kernel preflight is zero-mutation; surface admitted=False with no receipt.
            return {"admitted": False, "receipt_hash": "",
                    "reason": str(e), "payload": None}
        except Exception as e:
            tip = self._kernel.store.stream_hash()
            return {"admitted": False, "receipt_hash": tip,
                    "reason": f"{type(e).__name__}: {e}", "payload": None}


__all__ = ["BrokerClient", "LocalBrokerServer", "GovernedRequest"]
