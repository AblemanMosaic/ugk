"""SMH-I4 — Integration / Emission Hooks (SMH Track B, increment 4).

Wires SMH tier-transition receipt emission to REAL movement points, recording to the EXTERNAL
SMH ledger (SMH-I2) — without embedding anything in the UGK receipt chain and without moving the
UGK frame. The clean, coarse movement point is a release MINT, which is a COLD->DEEP export
(SMH-0 §8 / SMH-P2 §3): the hook reads the minted archive bytes (read-only), cites the archive by
`smh_archive_ref`, and records a `deep_export` receipt in the external ledger.

Discipline (SMH-I4 scope / halt conditions):
  * The SMH ledger stays EXTERNAL; receipts are NEVER embedded in the UGK constitutional chain.
  * Emit only for coarse, deliberate strata movements (deep_export / restore / hydration). Ordinary
    HOT frontier movement stays RECEIPT-FREE (anti-spam preserved via SMH-I2 classification).
  * Hooks READ archive bytes only — they do not modify any UGK file, do not move law/schema/legend,
    and do not found/run a kernel.
  * CK-CANON identity is reused (via SMH-I2 / ck_canon), not forked.
  * Read-only archive verification (SMH-I3) remains available and kernel-free.
  * No "UGK implements SMH" claim — this is an external integration layer alongside UGK tooling.

Imports only os/sys/hashlib + smh_tier_ledger (I2) + smh_projection_registry (I1). No ugk.*.
"""
import os, sys, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smh_tier_ledger as P2
import smh_projection_registry as P1


class SMHHookError(Exception):
    pass


def _read_bytes(path: str) -> bytes:
    """Read an artifact's bytes READ-ONLY (open 'rb', no write mode, no extraction)."""
    if not os.path.exists(path):
        raise SMHHookError("artifact not present: %s" % path)
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------- real-movement hooks
def on_release_minted(archive_path: str, ledger: P2.TierTransitionLedger) -> dict:
    """Hook for the release MINT movement point (COLD -> DEEP export). Reads the minted archive
    bytes read-only, cites it via smh_archive_ref, and records a `deep_export` receipt in the
    EXTERNAL ledger. This is a coarse, deliberate strata movement -> RECEIPT-REQUIRED."""
    subject = P1.smh_archive_ref(_read_bytes(archive_path))
    return ledger.record_movement("deep_export", from_tier="COLD", to_tier="DEEP",
                                  subject_refs=[subject])


def on_archive_restored(archive_path: str, ledger: P2.TierTransitionLedger) -> dict:
    """Hook for a restore movement (DEEP -> COLD). RECEIPT-REQUIRED."""
    subject = P1.smh_archive_ref(_read_bytes(archive_path))
    return ledger.record_movement("restore", from_tier="DEEP", to_tier="COLD",
                                  subject_refs=[subject])


def on_archive_hydrated(archive_path: str, ledger: P2.TierTransitionLedger,
                        to_tier: str = "WARM") -> dict:
    """Hook for hydration (COLD/DEEP -> WARM/HOT materialization). RECEIPT-REQUIRED."""
    subject = P1.smh_archive_ref(_read_bytes(archive_path))
    return ledger.record_movement("hydration", from_tier="COLD", to_tier=to_tier,
                                  subject_refs=[subject])


def on_hot_frontier_tick(ledger: P2.TierTransitionLedger, subject_refs=None) -> dict:
    """Hook for ordinary HOT frontier movement. ANTI-SPAM: classifies NO_RECEIPT -> emits nothing.
    Present so the integration explicitly routes frontier ticks through the receipt-free path."""
    return ledger.record_movement("hot_frontier_update", from_tier="HOT", to_tier="HOT",
                                  subject_refs=subject_refs or [])


# ---------------------------------------------------------------- clean mint composition
def mint_and_record(mint_fn, archive_path: str, ledger: P2.TierTransitionLedger):
    """Compose an EXISTING mint with the external SMH record at the real movement point, WITHOUT
    modifying the mint tool. `mint_fn()` performs the (unmodified) UGK mint and returns when the
    archive exists at `archive_path`; the hook then records the deep_export externally. The mint
    artifact is not modified by the hook (it is read read-only after mint)."""
    mint_result = mint_fn()
    receipt = on_release_minted(archive_path, ledger)
    return {"mint_result": mint_result, "smh_receipt": receipt}
