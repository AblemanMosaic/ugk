"""ugk/agent.py — Agent/MCP attestation surface (Phase 4 thin adapter, Grundnorm 444).

Exposes UGK as an agent tool surface.  Agents (LLM tool use, MCP servers,
automated pipelines) call ugk_govern() instead of calling kernel.execute()
directly.  All routing goes through BrokerClient.submit() → kernel.execute().

Functions:
  ugk_govern(intent, subject, authority, kernel) → Governed
  ugk_attest(kernel)                             → Attestation
  ugk_status(kernel)                             → dict
  ugk_session(kernel)                            → context manager

Governed — structured verdict with admitted, receipt_hash, stream_hash.
Attestation — 3+1 hash attestation proof for external verifiers.

Phase 4 constraint: NO governance logic here.  All receipt writing, gate
evaluation, and hash computation happen inside GovernanceKernel.execute()
via LocalBrokerServer.submit().  This module routes, wraps, and types.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class GoverndResult:
    """Structured verdict from ugk_govern()."""
    admitted:     bool
    op:           str
    authority:    str
    receipt_hash: str
    stream_hash:  str
    dimension_id: str
    reason:       str = ""     # populated on refusal

    @property
    def ok(self) -> bool:
        return self.admitted


@dataclass
class AttestationResult:
    """3+1 hash attestation proof for external verifiers."""
    stream_hash:         str
    hash_verified:       bool
    law_hash:            str
    csh_finality_hash:   str
    csh_quorum_achieved: bool
    mosaic_root:         str
    dimension_id:        str
    governance_status:   str

    @property
    def sound(self) -> bool:
        """True iff chain is intact and CSH quorum is achieved."""
        return self.hash_verified and self.csh_quorum_achieved


# ---------------------------------------------------------------------------
# Module-level default kernel (lazy singleton for agent usage)
# ---------------------------------------------------------------------------

_default_kernel = None
_default_broker = None


def _get_default_kernel():
    global _default_kernel, _default_broker
    if _default_kernel is None:
        from ugk.kernel import GovernanceKernel
        from ugk.transport.broker import LocalBrokerServer
        _default_kernel = GovernanceKernel(authority="agent")
        _default_kernel._ceremony()
        _default_kernel.open_session()
        _default_broker = LocalBrokerServer(_default_kernel)
    return _default_kernel, _default_broker


def _get_broker(kernel=None):
    """Return a LocalBrokerServer for the given kernel (or the default one)."""
    from ugk.transport.broker import LocalBrokerServer
    if kernel is None:
        _, broker = _get_default_kernel()
        return broker
    return LocalBrokerServer(kernel)


# ---------------------------------------------------------------------------
# ugk_govern — primary agent entry point
# ---------------------------------------------------------------------------

def ugk_govern(
    intent:    str,
    subject:   str,
    authority: str = "agent",
    op:        str = "crp_evidence",
    kernel     = None,
) -> GoverndResult:
    """Execute a governed operation via the BrokerClient.

    Routes through LocalBrokerServer.submit() → kernel.execute().
    All receipt writing and gate evaluation happen in the kernel.
    Returns a GoverndResult with the verdict.

    This is the canonical agent entry point for UGK integration.
    """
    broker = _get_broker(kernel)
    k = kernel or _get_default_kernel()[0]

    # DKN envelope
    snap = k.snapshot_fast()
    dim_id = snap.get("dimension_id", "")
    full_authority = f"{authority}@{dim_id[:16]}" if dim_id else authority

    from ugk.transport.broker import GovernedRequest
    result = broker.submit(GovernedRequest(
        op=op,
        authority=full_authority,
        parameters={"intent": intent, "subject": subject},
    ))

    stream_hash = k.store.stream_hash()
    return GoverndResult(
        admitted=result.get("admitted", False),
        op=op,
        authority=full_authority,
        receipt_hash=result.get("receipt_hash", ""),
        stream_hash=stream_hash,
        dimension_id=dim_id,
        reason=result.get("reason", ""),
    )


# ---------------------------------------------------------------------------
# ugk_attest — 3+1 hash attestation endpoint
# ---------------------------------------------------------------------------

def ugk_attest(kernel=None) -> AttestationResult:
    """Return a 3+1 hash attestation proof.

    Proves to an external verifier that this instance runs an audited kernel:
    chain is intact (verify_stream_hash=True) and CSH quorum is achieved.
    """
    k = kernel or _get_default_kernel()[0]
    snap = k.snapshot()   # O(n) — verifies chain

    return AttestationResult(
        stream_hash=snap.get("stream_hash", ""),
        hash_verified=snap.get("hash_verified", False),
        law_hash=snap.get("law_hash", ""),
        csh_finality_hash=snap.get("csh_finality_hash", ""),
        csh_quorum_achieved=snap.get("csh_quorum_achieved", False),
        mosaic_root=snap.get("mosaic_root", ""),
        dimension_id=snap.get("dimension_id", ""),
        governance_status=snap.get("governance_status", ""),
    )


# ---------------------------------------------------------------------------
# ugk_status — kernel status snapshot
# ---------------------------------------------------------------------------

def ugk_status(kernel=None) -> dict:
    """Return the kernel's fast snapshot dict for agent observability."""
    k = kernel or _get_default_kernel()[0]
    return k.snapshot_fast()


# ---------------------------------------------------------------------------
# ugk_session — context manager for scoped sessions
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def ugk_session(kernel=None, session_id: Optional[str] = None):
    """Context manager that opens a session, yields the kernel, then closes it.

    Usage:
        with ugk_session() as k:
            ugk_govern("orient", "my subject", kernel=k)
    """
    from ugk.kernel import GovernanceKernel
    k = kernel or GovernanceKernel(authority="agent")
    if not k._status == "ACTIVE":
        k._ceremony()
    sid = k.open_session(session_id=session_id)
    try:
        yield k
    finally:
        k.close_session()


__all__ = [
    "GoverndResult", "AttestationResult",
    "ugk_govern", "ugk_attest", "ugk_status", "ugk_session",
]
