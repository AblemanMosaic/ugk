"""ugk/migration/abletools.py — GovernedContext UGK shim (Phase 5).

Drop-in migration shim for AbleTools' GovernedContext.  AbleTools tools
replace `from abletools.governed_context import GovernedContext` with
`from ugk.migration import GovernedContext`.

All ctx.* calls route through kernel.execute() via LocalBrokerServer.
Session lifecycle (open_session / close_session) is managed by the context.
No governance logic in this module — all receipts, gates, and hashes live
in GovernanceKernel.

AbleTools compatibility surface:
  ctx = GovernedContext.from_env()
  result = ctx.govern("orient", "subject")
  result = ctx.fs_read("/path/to/file", intent="orient")
  result = ctx.fs_write("/path", content, intent="transform")
  result = ctx.proc_run(["cmd", "arg"], intent="transform")
  result = ctx.net_fetch("https://...", intent="orient")
  ctx.close()

Migration notes:
  - ctx.fs_read() / fs_write() / proc_run() / net_fetch(): in UGK Phase 5,
    these record governance receipts but do NOT perform the actual I/O.
    Ring 1 confinement (actual I/O restriction) is a deployer concern declared
    via CR-01.  The shim logs the intent and returns a GovResult.
  - ctx.govern() is the primary path: full kernel.execute() routing.
  - AbleTools-specific result types (FSReadResult etc.) are replaced by
    GovResult for Phase 5.  Phase 6 completes the result-type migration.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# GovResult — Phase 5 unified result type
# ---------------------------------------------------------------------------

@dataclass
class GovResult:
    """Unified governed operation result (Phase 5 migration type).

    Replaces AbleTools' FSReadResult / FSWriteResult / etc.
    Phase 6 completes the full result-type migration with typed effects.
    """
    admitted:     bool
    op:           str
    intent:       str
    subject:      str
    receipt_hash: str
    stream_hash:  str
    h_r:           str = ""   # RT-1a (E5b Tier 1): M2 analog of receipt_hash (merkle binding root)
    m2_stream_hash: str = ""  # RT-1a (E5b Tier 1): M2 analog of stream_hash (M2 chain tip = last h_r)
    reason:       str = ""
    payload:      object = field(default=None, repr=False)

    @property
    def ok(self) -> bool:
        return self.admitted

    # AbleTools compatibility aliases
    @property
    def outcome(self) -> str:
        return "execute" if self.admitted else "refuse"


# ---------------------------------------------------------------------------
# GovernedContext
# ---------------------------------------------------------------------------

class GovernedContext:
    """UGK-backed GovernedContext.  Drop-in replacement for AbleTools GovernedContext.

    All operations route through kernel.execute() via LocalBrokerServer.
    No I/O is performed by this class; all effects are declared as governed
    intents and produce receipts.

    Phase 5 migration path:
      1. Replace `from abletools.governed_context import GovernedContext`
         with `from ugk.migration import GovernedContext`
      2. Replace `ctx.fs_read()` / `ctx.net_fetch()` etc. with `ctx.govern()`
         (Phase 6 adds typed effect routing)
      3. Verify with migration_gate
    """

    def __init__(self, kernel=None, authority: str = "governed_context"):
        from ugk.kernel import GovernanceKernel
        from ugk.transport.broker import LocalBrokerServer
        self._kernel    = kernel if kernel is not None else GovernanceKernel(authority=authority)
        self._authority = authority
        self._broker    = LocalBrokerServer(self._kernel)
        self._session_id: Optional[str] = None

        if self._kernel.status != "ACTIVE":
            self._kernel._ceremony()
        self._session_id = self._kernel.open_session()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, authority: str = "governed_context") -> "GovernedContext":
        """Construct a GovernedContext from environment configuration.

        Reads UGK_STATE_DIR (or ACIS_STATE_DIR) for the SQLite store path.
        Falls back to in-memory store when no env var is set.

        This is the standard tool entry point, mirroring AbleTools:
            ctx = GovernedContext.from_env()
        """
        from ugk.kernel import GovernanceKernel
        from ugk.storage.store import UGKReceiptStore

        state_dir = (os.environ.get("UGK_STATE_DIR")
                     or os.environ.get("ACIS_STATE_DIR"))
        db_path = ":memory:"
        if state_dir:
            db_path = str(Path(state_dir) / "ugk.db")

        store  = UGKReceiptStore(db_path=db_path)
        kernel = GovernanceKernel(store=store, authority=authority)
        return cls(kernel=kernel, authority=authority)

    # ------------------------------------------------------------------
    # Primary governed path
    # ------------------------------------------------------------------

    def govern(
        self,
        intent:  str,
        subject: str,
        op:      str = "crp_evidence",
    ) -> GovResult:
        """Execute a governed operation.

        Routes through LocalBrokerServer → kernel.execute().
        Returns GovResult with admitted/receipt_hash/stream_hash.
        """
        from ugk.transport.broker import GovernedRequest
        result = self._broker.submit(GovernedRequest(
            op=op,
            authority=self._authority,
            parameters={"intent": intent, "subject": subject},
        ))
        stream_hash = self._kernel.store.stream_hash()
        m2_stream_hash = self._kernel.store.m2_stream_hash()   # RT-1a/1c additive M2 chain tip
        return GovResult(
            admitted=result.get("admitted", False),
            op=op,
            intent=intent,
            subject=subject,
            receipt_hash=result.get("receipt_hash", ""),
            stream_hash=stream_hash,
            h_r=result.get("h_r", "") or m2_stream_hash,   # RT-1a: M2 analog (tip receipt h_r)
            m2_stream_hash=m2_stream_hash,
            reason=result.get("reason", ""),
        )

    # ------------------------------------------------------------------
    # AbleTools compatibility surface (Phase 5 shims — intent-only)
    # ------------------------------------------------------------------

    def fs_read(self, path: str, intent: str = "orient") -> GovResult:
        """Record a governed fs_read intent.  Does NOT perform I/O (CR-01)."""
        return self.govern(intent=intent, subject=f"fs_read:{path}", op="crp_evidence")

    def fs_write(self, path: str, content: bytes, intent: str = "transform") -> GovResult:
        """Record a governed fs_write intent.  Does NOT perform I/O (CR-01)."""
        return self.govern(intent=intent, subject=f"fs_write:{path}", op="crp_evidence")

    def proc_run(self, cmd: list, intent: str = "transform") -> GovResult:
        """Record a governed proc_run intent.  Does NOT execute (CR-01)."""
        cmd_str = " ".join(str(c) for c in cmd)
        return self.govern(intent=intent, subject=f"proc_run:{cmd_str}", op="crp_evidence")

    def net_fetch(self, url: str, intent: str = "orient") -> GovResult:
        """Record a governed net_fetch intent.  Does NOT fetch (CR-01)."""
        return self.govern(intent=intent, subject=f"net_fetch:{url}", op="crp_evidence")

    # ------------------------------------------------------------------
    # Session + observability
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return the kernel's fast snapshot dict."""
        return self._kernel.snapshot_fast()

    def attest(self) -> dict:
        """Return 3+1 hash attestation proof."""
        snap = self._kernel.snapshot()
        return {
            "stream_hash":         snap.get("stream_hash", ""),
            "hash_verified":       snap.get("hash_verified", False),
            "law_hash":            snap.get("law_hash", ""),
            "csh_finality_hash":   snap.get("csh_finality_hash", ""),
            "csh_quorum_achieved": snap.get("csh_quorum_achieved", False),
        }

    def close(self) -> None:
        """Close the governance session."""
        if self._session_id is not None:
            self._kernel.close_session()
            self._session_id = None

    def verify_chain(self) -> bool:
        """Verify the receipt chain integrity."""
        return self._kernel.store.verify_stream_hash()

    def __enter__(self) -> "GovernedContext":
        return self

    def __exit__(self, *args) -> None:
        self.close()


__all__ = ["GovernedContext", "GovResult"]
