"""ugk/kernel.py — GovernanceKernel (Grundnorm layer, 444).

The W/G/E reactor.  Any application imports GovernanceKernel to get
constitutive (CSoftA ACTIVE) governance without re-implementing it.

execute(op, gate, effect) IS the W/G/E reactor:
  W (Steward):   op + authority + parameters — intent declared
  G (Governor):  gate() — blocking admissibility check, fail-closed
  E (Executor):  effect() — fires ONLY on G-admit; receipt written BEFORE

Three-tier op jurisdiction (single class, no hierarchy):
  Tier 0 _KERNEL_OPS:      {gate_admit, gate_refuse}
    → KernelInternalOp if externally called
  Tier 1 _UNIVERSAL_OPS:   {session_open, session_close, crp_evidence, test_checkpoint}
    → available in UNINITIALIZED + ACTIVE
  Tier 2 APPLICATION_OPS:  deployer-declared (ops.py, 644)
    → GovernanceNotFounded in UNINITIALIZED

Governance status lifecycle:
  UNINITIALIZED — ships here; fail-closed (Tier 2 refused); NOT CRYSTALLIZED
  ACTIVE        — post ceremony; law_hash injected on all receipts

UNINITIALIZED is NOT CRYSTALLIZED (capable but non-constitutive).
There is no state where governance is capable but optional.

CLASSIFIED_REMAINDERS — honest gap declaration:
  CR-01: OS layer         — OS does not provide receipt infrastructure
  CR-02: Python runtime   — CPython bytecode not receipted
  CR-03: SQLite WAL layer — filesystem ops below SQLite not receipted
  CR-04: effect() internals — opaque unless it also calls kernel.execute()

Receipt-before-effect (UL-S-02 / NBER-1):
  A durable DECISION receipt precedes the effect on every path: gate_admit is written at
  depth 0 before effect() (and, on the EXTERNAL_IRREVERSIBLE two-phase path, a PREPARE
  receipt as well). This ordering is load-bearing — not advisory. The SUCCESS receipt
  precedes effect() only on the legacy NON_ATOMIC path; PURE/STORE_LOCAL write success
  AFTER effect() via the AD-38 seam, and EXTERNAL_IRREVERSIBLE writes COMMIT AFTER effect().
"""
from __future__ import annotations

import hashlib
import os
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ugk.storage.store import UGKReceiptStore
from ugk.governance.warrant import _cj as _warrant_cj  # r143/AD-66: canonical warrant-body snapshot
from ugk.schema import (
    _KERNEL_OPS, _UNIVERSAL_OPS, GOVERNANCE_OPS,
)
from ugk.storage.binding import spawn_session_identity, SessionIdentity


# ---------------------------------------------------------------------------
# Governance status constants
# ---------------------------------------------------------------------------

STATUS_UNINITIALIZED = "UNINITIALIZED"
STATUS_ACTIVE        = "ACTIVE"

# Phase 2 — Coder-generated temporary Ed25519 pubkey.
# Key status: dev_temp — bootstrap key from AbleTools C build.
# Coder has seen the secret; rotate to Governor-held key for ceremony_complete.
# Replace with Governor-held key when running the real ceremony.
def _load_governor_identity():
    """Load (pubkey_hex, phase_code) from genesis/ at import time.
    Returns (sentinel, default_phase) if genesis artifacts absent — fail-closed.
    """
    from pathlib import Path as _Path
    import json as _json
    from ugk._paths import genesis_dir as _genesis_dir
    _gdir = _genesis_dir()
    _pub  = _gdir / "GENESIS_KEY.pub"
    _mani = _gdir / "DEPLOYMENT_MANIFEST.json"
    pubkey = (_pub.read_text().strip()
              if _pub.exists() else "GOVERNOR_KEY_UNSET__RUN_UGK_CHARTER")
    phase  = "ugk-substrate"
    if _mani.exists():
        try:
            phase = _json.loads(_mani.read_text()).get("phase_code", "ugk-substrate")
        except Exception:
            pass
    return pubkey, phase

GOVERNOR_PUBKEY_HEX, _PHASE_CODE_LOADED = _load_governor_identity()
# Bootstrap key loaded from genesis/GENESIS_KEY.pub (or sentinel if absent).

# Phase code for Phase 1 builds.  Simultaneously:
#   (1) semantic namespace selector
#   (2) anti-replay nonce
#   (3) constitutional phase reference
_PHASE_CODE: str = _PHASE_CODE_LOADED  # Loaded from genesis/DEPLOYMENT_MANIFEST.json

# Honest gap declaration (surfaced via snapshot() and snapshot_fast()).
CLASSIFIED_REMAINDERS: list[str] = [
    "CR-01: OS layer — OS does not provide receipt infrastructure",
    "CR-02: Python runtime internals — CPython bytecode not receipted",
    "CR-03: SQLite WAL layer — filesystem ops below SQLite not receipted",
    "CR-04: effect() callable internals — opaque unless it also calls kernel.execute()",
]


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------

class GateRefusal(Exception):
    """Raised when gate() returns False.  A first-class constitutive outcome.

    Carries structured receipt before raising (EH-S-02 atomicity — receipt
    written to store BEFORE GateRefusal is raised).
    """
    def __init__(self, op: str, reason: str = "gate returned False"):
        self.op = op
        self.reason = reason
        super().__init__(f"GateRefusal: op={op!r} reason={reason!r}")


class KernelInternalOp(Exception):
    """Raised when a Tier-0 op (gate_admit, gate_refuse) is called externally.

    These ops are emitted only by kernel.execute() internals — they are never
    externally reachable by design (three-tier jurisdiction enforcement).
    """
    def __init__(self, op: str):
        self.op = op
        super().__init__(
            f"KernelInternalOp: op={op!r} is a Tier-0 kernel-internal op "
            f"and must not be called externally."
        )


class GovernanceNotFounded(Exception):
    """Raised when a Tier-2 APPLICATION op is called in UNINITIALIZED status.

    UNINITIALIZED is fail-closed — Tier-2 ops require the governance ceremony
    (UNINITIALIZED → ACTIVE transition) before they are admissible.
    """
    def __init__(self, op: str):
        self.op = op
        super().__init__(
            f"GovernanceNotFounded: op={op!r} requires ACTIVE governance status. "
            f"Run the genesis ceremony to found the kernel."
        )


class UndeclaredOp(Exception):
    """Raised when an op is not declared in GOVERNANCE_OPS (BS-01).

    Op declaration before execution is non-negotiable.  Silent auto-registration
    would undermine the constitutional standing of governance operations.
    """
    def __init__(self, op: str):
        self.op = op
        super().__init__(
            f"UndeclaredOp: op={op!r} is not declared in GOVERNANCE_OPS (BS-01). "
            f"Declare it in ops.py before execution."
        )


class ProtocolError(Exception):
    """Raised when execute() inputs are malformed at the protocol boundary (r96 / AD-31).

    Invariant A, "no admit before the refusal horizon is exhausted": a non-string authority,
    non-JSON-serializable parameters, or a malformed warrant_basis is a CALLER/protocol error
    caught BEFORE any receipt is written - it fails closed with ZERO chain mutation (no receipt),
    distinct from a constitutional GateRefusal (a first-class governed decision).
    """
    def __init__(self, op: str, reason: str = ""):
        self.op = op
        self.reason = reason
        super().__init__(f"ProtocolError: op={op!r} reason={reason!r}")


class ExternalEffectNotPerformed(Exception):
    """r115 / AD-44: the DESIGNATED signal an EXTERNAL_IRREVERSIBLE effect raises when, and ONLY when,
    it can PROVE the irreversible external act did NOT happen (confirmed non-performance).

    On this signal the kernel writes a clean ABORT (phase=abort, abort_reason=external_effect_not_performed)
    — a non-rollback, confirmed-non-performance terminal that asserts the act provably never occurred (it
    NEVER claims the act was undone). Any OTHER exception from an EXTERNAL_IRREVERSIBLE effect is in-doubt:
    the kernel writes NO terminal and re-raises, leaving an orphan PREPARE that the orphan detector
    surfaces. An effect must therefore raise this EXCLUSIVELY for proven non-performance; raising it
    speculatively would falsely assert 'it didn't happen'. The kernel cannot verify the claim — truthful
    use is the effect's audited contract (confess-and-audit)."""
    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(f"ExternalEffectNotPerformed: {reason!r}")


# r121 / AD-46: bounded outcome-write retry constants + signals.
MAX_OUTCOME_WRITE_ATTEMPTS = 3   # bounded; a CONSTANT, not config and NOT a registry default.


class TerminalWriteExhausted(Exception):
    """r121 / AD-46: raised when the bounded retry of an EXTERNAL_IRREVERSIBLE TERMINAL (COMMIT/ABORT)
    store write exhausts MAX_OUTCOME_WRITE_ATTEMPTS retryable failures WITHOUT persisting the terminal.

    It is an EXHAUSTION signal, NOT a receipt: no terminal was written, so the PREPARE remains an orphan
    (record-loss, in-doubt). It carries phase / prepare_ref / attempts for operator + log clarity ONLY --
    NONE of it enters the chain (Option A: the retry is invisible to receipt content). The originating
    store error is chained via `raise ... from` so the transient cause is preserved for debugging."""
    def __init__(self, phase, prepare_ref, attempts):
        self.phase = phase
        self.prepare_ref = prepare_ref
        self.attempts = attempts
        super().__init__(
            f"TerminalWriteExhausted: phase={phase!r} prepare_ref={prepare_ref!r} attempts={attempts}")


class ReconciliationRefused(Exception):
    """r123 / AD-47: the DESIGNATED fail-closed refusal of reconcile_external_irreversible(). The
    reconciliation contract is strict and never guesses: it refuses (writing NO terminal, leaving the
    orphan untouched) when authority is missing, evidence_ref is missing, the determination is not one of
    {performed, not_performed} (this is also the 'cannot determine' path -- an inconclusive external check
    is a first-class refusal, never a forced terminal), or the target prepare_ref is not an OUTSTANDING
    orphan (unknown, not a PREPARE, or already carrying a terminal -- the no-duplicate-terminal guard).
    `reason` is a short stable token for operator/log clarity; it is NOT a receipt (no mutation occurs)."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"ReconciliationRefused: {reason}")


class CompensationRefused(Exception):
    """r132 / AD-55: the DESIGNATED fail-closed refusal of compensate_external_reversible(). The
    compensation arc is SEPARATELY GOVERNED and SEPARATELY IDEMPOTENT: it refuses (writing NOTHING,
    running no compensating action) when authority is missing, the compensation_idempotency_key is
    missing/empty, the compensation_idempotency_key is NOT distinct from the forward effect's
    idempotency_key (ambiguous reuse -- the Governor tightening: a compensation must not ride the
    original effect's key), or the target prepare_ref does not name a COMMITTED forward
    EXTERNAL_REVERSIBLE effect that is not already compensated (compensation applies to a PERFORMED
    forward effect, never to an aborted, in-doubt, or already-offset one). `reason` is a short stable
    token for operator/log clarity; it is NOT a receipt (no mutation occurs on refusal)."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"CompensationRefused: {reason}")


def _is_retryable_terminal_write_error(exc):
    """r121 / AD-46: the NARROW, named retryable set for a TERMINAL store write -- a transient store
    failure that may clear on an immediate re-attempt. EVERYTHING outside this set fails closed
    immediately (no retry): a logic/programming fault must surface, never be masked by retrying.
      * sqlite3.OperationalError whose message is lock/busy contention; and
      * TransactionCommitError (the AD-36 clean-path commit/RELEASE failure)."""
    import sqlite3
    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        return ("locked" in msg) or ("busy" in msg)
    try:
        from ugk.integrity import TransactionCommitError
        if isinstance(exc, TransactionCommitError):
            return True
    except Exception:
        pass
    return False


class EffectAtomicity(Enum):
    """Declared atomicity class of an execute() effect (r102-a / AD-37).

    execute()'s effect is opaque caller code the kernel cannot prove
    rollback-able. Atomicity is therefore EFFECT-CLASS-RELATIVE: a SQLite seam
    can roll back store-local state, but it cannot roll back a payment, a
    network call, a file write, or an unknown external mutation. Every effect
    must DECLARE its class; an undeclared effect fails closed before admit,
    which eliminates silent unknown effects.

    r102-b (AD-38) implements the rollback-able classes (PURE, STORE_LOCAL) onto
    the AD-34/36 seam (atomic [effect + success], success-after-effect, structural
    abort on failure); NON_ATOMIC remains the explicit legacy bridge. r115 (AD-44)
    implements EXTERNAL_IRREVERSIBLE as a two-phase prepare/commit trail; only
    EXTERNAL_REVERSIBLE remains reserved and FAILS CLOSED until its protocol lands:
      PURE / STORE_LOCAL           -> atomic via the seam        (AD-38)
      EXTERNAL_IRREVERSIBLE        -> two-phase prepare/commit    (AD-44)
      EXTERNAL_REVERSIBLE          -> compensation / saga         (AD-55)

    NON_ATOMIC preserves legacy execution order while making the lack of
    atomicity explicit and auditable. It is NOT success-proof, NOT
    rollback-proof, and NOT Invariant-E-compliant -- a transitional posture for
    callers awaiting per-class migration, not an atomicity claim.
    """
    PURE                  = "pure"
    STORE_LOCAL           = "store_local"
    EXTERNAL_REVERSIBLE   = "external_reversible"
    EXTERNAL_IRREVERSIBLE = "external_irreversible"
    NON_ATOMIC            = "non_atomic"


def _reject_floats_in_governance_input(op, value, _path="parameters"):
    """r156 / CK-CANON float ban (CK-CANON-0.1 §3, vector V9).

    Reject any float anywhere in governance-relevant input as a protocol failure.
    json.dumps would silently serialize floats through IEEE-754, which CK-CANON
    bans (`float_present`): a fractional quantity must be an integer in a declared
    unit or a [numerator, denominator] integer pair. bool is permitted (it is an
    int subclass and a CK value); only float is banned. Behavioral protocol-boundary
    guard — raised BEFORE admission (Invariant A: zero mutation), never a refusal.
    """
    if isinstance(value, bool):
        return  # bool is allowed; guard against the int-subclass check below
    if isinstance(value, float):
        raise ProtocolError(op, "float_present: non-integer number at %s is banned by "
                                "CK-CANON-0.1 (use an integer in a declared unit or a "
                                "[num,den] integer pair)" % _path)
    if isinstance(value, dict):
        for k, v in value.items():
            _reject_floats_in_governance_input(op, v, "%s.%s" % (_path, k))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _reject_floats_in_governance_input(op, v, "%s[%d]" % (_path, i))


# ---------------------------------------------------------------------------
# GovernanceKernel
# ---------------------------------------------------------------------------

class GovernanceKernel:
    """W/G/E reactor — governance closure bottom.

    Every governed operation passes through execute().  The kernel:
      - Validates ops against the three-tier jurisdiction registry
      - Enforces fail-closed in UNINITIALIZED status
      - Evaluates caller-supplied gate functions (blocking, fail-closed)
      - Writes receipt BEFORE effect (NBER-1 / UL-S-02, load-bearing)
      - Injects SessionIdentity (session_dkn) into D7 (custody) on every receipt
      - Injects law_hash (SHA-256(invariants.py)) on ACTIVE receipts

    UL-S-01: Zero external runtime dependencies (stdlib + vendored Ed25519).
    """

    def __init__(
        self,
        store:     Optional[UGKReceiptStore] = None,
        authority: str = "system",
    ):
        self._store     = store if store is not None else UGKReceiptStore()
        self._authority = authority
        self._status:   str = STATUS_UNINITIALIZED
        self._law_hash: str = ""            # empty until ACTIVE ceremony
        self._session_identity: Optional[SessionIdentity] = None
        self._session_dkn:  str = ""
        self._session_open_count: int = 0
        self._refused_by_layer: dict[str, int] = {"S": 0, "C": 0, "I": 0}
        # Phase 2: live cryptographic identity fields
        self._mosaic_root:  str = ""        # SHA-256(governor_pubkey) — set in ceremony
        self._dimension_id: str = ""        # canonical_dkn(phase_code, pubkey) — set in ceremony
        self._require_governor_sig: bool = False  # Governor interposition flag
        # Phase 6: legend projection vocabulary
        self._legend_hash:  str = ""        # LEGEND_HASH from binding.py — set in ceremony
        self._warrant_store: object = None  # WarrantStore — set via set_warrant_store()
        self._last_summary:  object = None  # SessionSummary — set in close_session()
        self._will_store:    object = None  # IntentStore — set via set_will_store()
        self._require_intent: bool = False  # fail-closed will coverage when True
        self._current_scope_id: str = ""   # ProvenanceScope.scope_id for current session
        self._authority_model   = None     # AuthorityModel set via set_authority_model()
        self._manifest_hash     = ""       # DeploymentManifest.manifest_hash (set in _ceremony())
        self._require_scoped_intent: bool = False
        self._op_csil_registry: dict = {}  # op_name → csil_id (Phase 19)
        # Phase 3: CSH finality fields
        self._launch_ic:          object = None  # InceptionCertificate — set in ceremony
        self._validator_set:      object = None  # ValidatorSet — set in ceremony
        self._csh_finality_hash:  str = ""       # MCIR finality_hash — set in ceremony
        self._csh_quorum_achieved: bool = False   # True iff N-of-M quorum met

    # ------------------------------------------------------------------
    # Governance status
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        """Current governance status: UNINITIALIZED | ACTIVE."""
        return self._status

    def _ceremony(
        self,
        genesis_seal: Optional[dict] = None,
        signature_hex: Optional[str] = None,
    ) -> None:
        """Transition UNINITIALIZED → ACTIVE.

        Phase 2: validates a signed genesis seal before activating.
        If called without arguments, loads genesis/GENESIS_SEAL.json from disk
        (when present) and validates it.  If no seal is present, proceeds
        without seal validation (Phase 1 compat / test path).

        Computes:
          law_hash      = SHA-256(invariants.py)
          mosaic_root   = SHA-256(GOVERNOR_PUBKEY_HEX bytes)
          dimension_id  = canonical_dkn(phase_code, GOVERNOR_PUBKEY_HEX)
        """
        from ugk.storage.binding import mosaic_id as _mosaic_id, canonical_dkn as _cdkn
        from ugk.governance.governor import load_genesis_seal, validate_genesis_seal

        # CHARTER-S-01 fail-closed (Option K, 2026-06-10): the unset sentinel
        # can never found governance. UNINITIALIZED → ACTIVE requires a real
        # governor identity; `ugk charter` is the founding constitutional act.
        if str(GOVERNOR_PUBKEY_HEX).startswith("GOVERNOR_KEY_UNSET"):
            raise GovernanceNotFounded("ceremony[governor-key-unset-sentinel]")

        if genesis_seal is None and signature_hex is None:
            loaded = load_genesis_seal()
            if loaded is not None:
                if not validate_genesis_seal(loaded, GOVERNOR_PUBKEY_HEX):
                    raise ValueError(
                        "ceremony: genesis seal on disk failed validation."
                    )
        elif genesis_seal is not None and signature_hex is not None:
            if not validate_genesis_seal(
                {"seal": genesis_seal, "signature": signature_hex},
                GOVERNOR_PUBKEY_HEX,
            ):
                raise ValueError(
                    "ceremony: provided genesis seal failed Ed25519 validation."
                )

        inv_path = Path(__file__).parent / "invariants.py"
        inv_content = inv_path.read_bytes() if inv_path.exists() else b"# placeholder"
        self._law_hash     = hashlib.sha256(inv_content).hexdigest()
        self._mosaic_root  = _mosaic_id(GOVERNOR_PUBKEY_HEX)
        self._dimension_id = _cdkn(_PHASE_CODE, GOVERNOR_PUBKEY_HEX)
        # Load manifest_hash from DeploymentManifest if present
        try:
            from ugk.charter import DeploymentManifest
            _m = DeploymentManifest.load()
            self._manifest_hash = _m.manifest_hash if _m else ""
        except Exception:
            self._manifest_hash = ""
        # Phase 6: legend_hash from LEGEND constant
        from ugk.storage.binding import LEGEND_HASH as _LEGEND_HASH, _LEGEND_ENTRIES as _LE
        import json as _json, time as _time
        self._legend_hash  = _LEGEND_HASH
        # Seal legend into store for cross-process audit (Phase 8 AUDIT-S-02)
        _entries_json = _json.dumps(
            sorted(_LE, key=lambda e: e["csil_id"]),
            sort_keys=True, separators=(",", ":")
        )
        self._store.seal_legend(
            legend_hash=_LEGEND_HASH,
            entries_json=_entries_json,
            phase_code=_PHASE_CODE,
            entry_count=len(_LE),
            sealed_at=_time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        )

        # Emit legend_seal receipt into chain (AUDIT-S-02)
        self._store.write(
            op="legend_seal",
            authority=self._authority,
            parameters={"legend_hash": self._legend_hash,
                        "entry_count": len(_LE),
                        "phase_code": _PHASE_CODE},
            intent="legend_seal",
            jurisdiction="kernel",
            session_dkn=self._session_dkn,
            law_hash=self._law_hash,
            legend_hash=self._legend_hash,
        )
        # Phase 3: CSH — load or create ValidatorSet, Launch IC, achieve quorum
        self._activate_csh()
        self._status = STATUS_ACTIVE

    @property
    def last_summary(self):
        """Return the SessionSummary from the most recent close_session(), or None."""
        return self._last_summary

    def set_warrant_store(self, warrant_store) -> None:
        """Attach a WarrantStore to receive DecisionWarrants from execute()."""
        self._warrant_store = warrant_store

    def register_op_csil(self, op_name: str, csil_id: int) -> None:
        """Register a CSIL coordinate for an APPLICATION_OP. CSIL-S-01.
        Raises ValueError on collision with existing LEGEND or registry entry.
        """
        from ugk.storage.binding import _LEGEND_ENTRIES
        existing = {e["csil_id"] for e in _LEGEND_ENTRIES}
        if csil_id in existing and self._op_csil_registry.get(op_name) != csil_id:
            raise ValueError(f"CSIL {csil_id} already in LEGEND — collision")
        if (op_name in self._op_csil_registry and
                self._op_csil_registry[op_name] != csil_id):
            raise ValueError(f"{op_name!r} already registered with csil_id {self._op_csil_registry[op_name]}")
        self._op_csil_registry[op_name] = csil_id

    def set_will_store(self, will_store, require_intent: bool = False,
                       require_scoped_intent: bool = False) -> None:
        """Attach an IntentStore. When require_intent=True, APPLICATION_OPS require
        coverage (fail-closed). When require_scoped_intent=True, open-scope
        declarations are excluded (ALT-I-03 temporal scope enforcement).
        """
        self._will_store            = will_store
        self._require_intent        = require_intent
        self._require_scoped_intent = require_scoped_intent

    def set_authority_model(self, model) -> None:
        """Declare the AuthorityModel. Config-layer constitutional act (CM-S-04)."""
        self._authority_model = model
        self._store.seal_authority_model(model)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def open_session(self, session_id: Optional[str] = None) -> str:
        """Spawn SessionIdentity, emit session_open receipt. Returns session_id.

        session_dkn = SHA-256(mosaic_root:phase_code:session_id)  WHO×WHAT×WHICH
        In Phase 1 the Governor key is the placeholder sentinel — session_dkn
        is still computed and injected into D7 on every receipt.
        """
        ident = spawn_session_identity(
            governor_pubkey=GOVERNOR_PUBKEY_HEX,
            phase_code=_PHASE_CODE,
            session_id=session_id,
        )
        self._session_identity   = ident
        self._session_dkn        = ident.session_dkn
        self._session_open_count = self._store.receipt_count()

        self._store.write(
            op="session_open",
            authority=self._authority,
            parameters={"session_id": ident.session_id,
                        "session_dkn": ident.session_dkn,
                        "phase_code": ident.phase_code,
                        "authority_model_hash": (self._authority_model.model_hash if self._authority_model else ""),
                        "manifest_hash": self._manifest_hash},
            intent="session_open",
            jurisdiction="kernel",
            session_dkn=self._session_dkn,
            law_hash=self._law_hash,
            legend_hash=self._legend_hash,
        )
        # Emit ProvenanceScope (SCOPE-S-01) — chained via prior_scope_id
        self._current_scope_id = ""
        try:
            from ugk.scope import ProvenanceScope
            prior_sid = self._store.latest_scope_id(self._mosaic_root)
            _scope = ProvenanceScope.create(
                authority_surface=self._mosaic_root,
                session_dkn=self._session_dkn,
                law_hash=self._law_hash,
                legend_hash=self._legend_hash,
                prior_scope_id=prior_sid,
            )
            self._store.seal_scope(_scope)
            self._current_scope_id = _scope.scope_id
        except Exception:
            pass
        return ident.session_id

    def _activate_csh(self, read_only: bool = False) -> None:
        """Phase 3: seal ValidatorSet, mint/load Launch IC, achieve CSH quorum.

        Loads artifacts from genesis/ if present; generates them from the dev
        temp key if absent (first-run path).  All new artifacts are written to
        genesis/ for subsequent runs.
        """
        import json
        from pathlib import Path as _Path
        from ugk.csh import (
            seal_validator_set, create_launch_ic, create_attestation,
            achieve_finality, declare_rotation_rule,
        )

        from ugk._paths import genesis_dir as _genesis_dir
        genesis_dir = _genesis_dir()
        genesis_dir.mkdir(exist_ok=True)

        priv_path = genesis_dir / "GENESIS_PRIVKEY.hex"
        pub_path  = genesis_dir / "GENESIS_KEY.pub"
        vs_path   = genesis_dir / "VALIDATOR_SET.json"
        ic_path   = genesis_dir / "LAUNCH_IC.json"

        if not priv_path.exists() or not pub_path.exists():
            # No key material — CSH not achievable
            self._csh_quorum_achieved = False
            return
        if read_only and not (vs_path.exists() and ic_path.exists()):
            # IEL Invariant D: read-only hydration must not CREATE CSH artifacts; fail closed on
            # incomplete founded state (quorum simply unachieved — never written into existence).
            self._csh_quorum_achieved = False
            return

        priv_hex = priv_path.read_text().strip()
        pub_hex  = pub_path.read_text().strip()
        ts       = "2026-06-09T08:30:00Z"

        # --- ValidatorSet ---
        if vs_path.exists():
            from ugk.csh import ValidatorSet
            vs_data = json.loads(vs_path.read_text())
            vs = ValidatorSet(
                validators=tuple(vs_data["validators"]),
                n_validators=vs_data["n_validators"],
                sealed_by=vs_data["sealed_by"],
                sealed_hash=vs_data["sealed_hash"],
                seal_signature=vs_data["seal_signature"],
                sealer_pubkey=vs_data["sealer_pubkey"],
            )
        else:
            vs = seal_validator_set(priv_hex, pub_hex, [self._mosaic_root])
            with open(vs_path, 'w') as f:
                import dataclasses
                json.dump(dataclasses.asdict(vs), f, indent=2, sort_keys=True)
        self._validator_set = vs

        # --- Launch IC ---
        if ic_path.exists():
            from ugk.csh import InceptionCertificate
            ic_data = json.loads(ic_path.read_text())
            ic = InceptionCertificate(**ic_data)
        else:
            ic = create_launch_ic(
                privkey_hex=priv_hex, pubkey_hex=pub_hex,
                constitutional_hash=self._law_hash,
                dimension_id=self._dimension_id,
                phase_code=_PHASE_CODE,
                validator_set_hash=vs.sealed_hash,
                timestamp=ts,
            )
            with open(ic_path, 'w') as f:
                import dataclasses
                json.dump(dataclasses.asdict(ic), f, indent=2, sort_keys=True)
        self._launch_ic = ic

        # --- CSH quorum (N=1 attestation) ---
        att = create_attestation(
            priv_hex, pub_hex, self._law_hash, _PHASE_CODE, epoch=0, timestamp=ts
        )
        mcir = achieve_finality([att], vs, self._law_hash)
        self._csh_quorum_achieved = mcir.quorum_achieved
        self._csh_finality_hash   = mcir.finality_hash

        # --- RotationRule (pre-declared, not yet exercised) ---
        self._rotation_rule = declare_rotation_rule(
            current_holder=self._mosaic_root,
            successors=[self._mosaic_root],  # placeholder: self-succession until real ceremony
            ic_hash=ic.ic_hash(),
            timestamp=ts,
        )

    def hydrate_readonly(self) -> None:
        """IEL Invariant D (AD-30): reconstruct ACTIVE kernel state from an existing founded
        deployment WITHOUT writing anything. Pure compute of the frame hashes (law/mosaic/dimension/
        manifest/legend) + LOAD-ONLY CSH from genesis artifacts. NO legend_seal, NO session_open, NO
        receipts. This is the read-only substrate the attest CLI path binds to (alongside a mode=ro
        store). Fails closed (GovernanceNotFounded) on the unset-governor sentinel; CSH quorum stays
        False if founded CSH artifacts are absent (never created)."""
        from ugk.storage.binding import mosaic_id as _mosaic_id, canonical_dkn as _cdkn
        if str(GOVERNOR_PUBKEY_HEX).startswith("GOVERNOR_KEY_UNSET"):
            raise GovernanceNotFounded("hydrate_readonly[governor-key-unset-sentinel]")
        inv_path = Path(__file__).parent / "invariants.py"
        inv_content = inv_path.read_bytes() if inv_path.exists() else b"# placeholder"
        self._law_hash     = hashlib.sha256(inv_content).hexdigest()
        self._mosaic_root  = _mosaic_id(GOVERNOR_PUBKEY_HEX)
        self._dimension_id = _cdkn(_PHASE_CODE, GOVERNOR_PUBKEY_HEX)
        try:
            from ugk.charter import DeploymentManifest
            _m = DeploymentManifest.load()
            self._manifest_hash = _m.manifest_hash if _m else ""
        except Exception:
            self._manifest_hash = ""
        from ugk.storage.binding import LEGEND_HASH as _LEGEND_HASH
        self._legend_hash = _LEGEND_HASH
        self._activate_csh(read_only=True)
        self._status = STATUS_ACTIVE

    def close_session(self) -> None:
        """Emit session_close receipt + SessionSummary (SUM-S-01)."""
        _receipt_count  = self._store.receipt_count() + 1
        _refusal_count  = self._store.refusal_count()
        _warrant_count  = self._warrant_store.warrant_count() if self._warrant_store else 0
        _admitted_count = _receipt_count - _refusal_count

        self._store.write(
            op="session_close",
            authority=self._authority,
            parameters={"session_id": (
                self._session_identity.session_id
                if self._session_identity else None
            )},
            intent="session_close",
            jurisdiction="kernel",
            session_dkn=self._session_dkn,
            law_hash=self._law_hash,
            legend_hash=self._legend_hash,
        )

        try:
            from ugk.summary import SessionSummary
            self._last_summary = SessionSummary.create(
                session_dkn=self._session_dkn,
                receipt_count=self._store.receipt_count(),
                warrant_count=_warrant_count,
                refusal_count=_refusal_count,
                admitted_count=_admitted_count,
                final_stream_hash=self._store.stream_hash(),
                law_hash=self._law_hash,
                legend_hash=self._legend_hash,
                phase_code=_PHASE_CODE,
            )
        except Exception:
            self._last_summary = None

    # ------------------------------------------------------------------
    # Primary governed path — execute()
    # ------------------------------------------------------------------

    def _emit_protocol_error(self, op: str, reason: str, authority: Optional[str] = None) -> None:
        """FGA §15.5 — write a tamper-evident protocol-error receipt for a structural/protocol
        rejection BEFORE raising the typed exception. Makes the third outcome class first-class:
        ADMIT (success) / constitutional REFUSE (gate_refuse) / PROTOCOL error (protocol_error)
        are now all receipted and distinguishable. Uncompressed op (no LEGEND entry → legend_hash
        stable), unregistered (no schema change → schema_hash stable), no new invariant (IR
        strengthening of EH-S-01 + receipt semantics → law_hash stable). Best-effort: receipt
        emission never masks or weakens the structural rejection, which always raises.
        """
        try:
            self._store.write(
                op="protocol_error",
                authority=authority or self._authority,
                parameters={"op": op, "reason": reason},
                failed=True,
                intent="protocol_error",
                jurisdiction="kernel",
                session_dkn=self._session_dkn,
                law_hash=self._law_hash,
                compress=False,
            )
        except Exception:
            pass

    def _emit_effect_abort(self, op, authority, parameters, effect_atomicity, reason,
                           jurisdiction, intent_ref, admit_ref):
        """r102-b / AD-38: durable STRUCTURAL ABORT of an admitted PURE/STORE_LOCAL effect attempt.

        Written at depth 0 AFTER the AD-34/36 seam rolled the outcome transition back (the effect's
        store writes AND the would-be success receipt persisted nothing, frontier restored). This is
        a classified failed=True receipt on the SAME op - it is the abort of an effect that WAS
        admitted (gate_admit is durable), NOT a malformed-protocol error rejected before admissibility,
        so it deliberately does NOT use protocol_error wording. Deterministic content: the op
        parameters, the effect_atomicity class, the classified abort reason (effect_failure /
        success_receipt_failure / commit_release_failure), the op/intent linkage, and the durable
        gate_admit h_r. No schema column - all fields live in the existing receipt shape."""
        abort_params = dict(parameters or {})
        abort_params["effect_aborted"] = True
        # r140 (Lane 2): typed columns are the primary write surface for the structural effect fields.
        # When effect-bearing, the store derives the abort_reason / effect_atomicity / gate_admit_ref
        # markers from this canonical descriptor (byte-identical to the legacy marker-primary write);
        # when not effect-bearing, abort_reason/gate_admit_ref remain plain markers (legacy path). The
        # receipt stays failed=True with terminal outcome ADMIT (TO-S-01 effect-abort separation intact).
        if effect_atomicity is not None:
            effect_columns = {
                "effect_atomicity": effect_atomicity.value,
                "effect_abort_reason": reason,
                "effect_gate_admit_ref": admit_ref,
            }
        else:
            effect_columns = None
            abort_params["abort_reason"] = reason
            if admit_ref:
                abort_params["gate_admit_ref"] = admit_ref
        self._store.write(
            op=op,
            authority=authority,
            parameters=abort_params,
            failed=True,
            intent=op,
            jurisdiction=jurisdiction,
            session_dkn=self._session_dkn,
            law_hash=self._law_hash,
            legend_hash=self._legend_hash,
            intent_ref=intent_ref,
            effect_columns=effect_columns,
        )

    def _emit_irreversible(self, op, authority, base_params, phase, idempotency_key,
                           jurisdiction, intent_ref, warrant_id, failed,
                           prepare_ref=None, gate_admit_ref=None, abort_reason=None):
        """r115 / AD-44: write one EXTERNAL_IRREVERSIBLE phase receipt (PREPARE / COMMIT / ABORT) at
        depth 0 in the EXISTING receipt shape — all distinguishing fields are parameters-JSON markers,
        NO schema column (mirrors the r102-a marker + _emit_effect_abort). Returns the Receipt."""
        p = dict(base_params or {})
        # r139 (Lane 1): typed columns are the PRIMARY write surface; the store derives the parameter
        # markers from this canonical descriptor (byte-identical to the legacy marker-primary write).
        effect_columns = {
            "effect_atomicity": EffectAtomicity.EXTERNAL_IRREVERSIBLE.value,
            "effect_phase": phase,
            "effect_idempotency_key": idempotency_key,
            "effect_gate_admit_ref": gate_admit_ref,
            "effect_prepare_ref": prepare_ref,
            "effect_abort_reason": abort_reason,
        }
        return self._store.write(
            op=op, authority=authority, parameters=p, failed=failed, intent=op,
            jurisdiction=jurisdiction, session_dkn=self._session_dkn,
            law_hash=self._law_hash, legend_hash=self._legend_hash,
            warrant_id=warrant_id, intent_ref=intent_ref, effect_columns=effect_columns,
        )

    def _emit_terminal_durable(self, op, authority, base_params, phase, idempotency_key,
                               jurisdiction, intent_ref, warrant_id, failed,
                               prepare_ref=None, abort_reason=None):
        """r121 / AD-46: write an EXTERNAL_IRREVERSIBLE TERMINAL receipt (phase in {commit, abort}) with a
        BOUNDED in-process retry of the STORE WRITE ONLY.

        The outcome is ALREADY known when this is called -- the effect has returned (COMMIT) or has raised
        ExternalEffectNotPerformed (ABORT). This helper re-attempts a durable RECORD of that outcome; it
        does NOT and CANNOT re-invoke the external effect (the effect lives entirely outside this helper,
        before the call site). It therefore re-attempts persistence, never the irreversible act.

        Discipline (all ratified r120 §9):
          * retries ONLY the narrow named transient-store set (_is_retryable_terminal_write_error);
            ANY other exception fails closed IMMEDIATELY (re-raise on the first attempt) -> orphan;
          * at most MAX_OUTCOME_WRITE_ATTEMPTS attempts; NO sleep / NO backoff (immediate, synchronous);
          * on exhaustion: NO terminal persists -> raise TerminalWriteExhausted (orphan, record-loss),
            chaining the last transient store error;
          * records NOTHING about the retry in the receipt (Option A): a terminal written on attempt k is
            byte-identical in PARAMETERS to one written on attempt 1 (only the inherent, already-varying
            write timestamp differs), so the chain hash carries no retry nondeterminism.

        A failed _emit_irreversible attempt persists nothing durable (store.write is all-or-nothing), so a
        subsequent successful attempt leaves exactly ONE terminal for (idempotency_key, prepare_ref)."""
        assert phase in ("commit", "abort"), "durable retry is for terminals only (commit/abort)"
        last_exc = None
        for _attempt in range(1, MAX_OUTCOME_WRITE_ATTEMPTS + 1):
            try:
                return self._emit_irreversible(
                    op, authority, base_params, phase, idempotency_key, jurisdiction, intent_ref,
                    warrant_id, failed=failed, prepare_ref=prepare_ref, abort_reason=abort_reason)
            except Exception as exc:
                if not _is_retryable_terminal_write_error(exc):
                    raise                       # fail closed immediately -> orphan, original error surfaces
                last_exc = exc                  # transient -> retry immediately (no sleep)
        raise TerminalWriteExhausted(phase, prepare_ref, MAX_OUTCOME_WRITE_ATTEMPTS) from last_exc

    def _execute_external_irreversible(self, op, authority, params, effect, idempotency_key,
                                       jurisdiction, intent_ref, admit_ref, warrant_id):
        """r115 / AD-44: the EXTERNAL_IRREVERSIBLE two-phase outcome trail (the four-state model).

        Three INDEPENDENT depth-0 receipts, NOT one atom and NOT inside store.transaction() (the act
        cannot be rolled back, so a rollback scope would be misleading):

          PREPARE (intent-to-act, BEFORE effect; NBER-1; carries idempotency_key + gate_admit_ref)
            -> effect()  [the irreversible external act]
                 returns normally          -> COMMIT (confirmed performed; written AFTER the effect)
                 ExternalEffectNotPerformed -> ABORT  (confirmed NOT performed; a non-rollback terminal)
                 any other exception        -> NO terminal written, re-raise -> orphan PREPARE (in-doubt)

        The kernel NEVER infers success or failure from an orphan PREPARE: an ambiguous effect failure
        and a hard crash between PREPARE and the terminal surface identically (both genuinely in-doubt),
        and the orphan detector surfaces them. ABORT is reserved for PROVEN non-performance and never
        claims the act was undone. No auto-retry; the required idempotency_key lets the external system
        dedup a MANUAL retry. r121/AD-46: a TRANSIENT failure of the COMMIT/ABORT store write is retried
        (bounded, store-write only -- NEVER the effect); only on EXHAUSTION (or a non-retryable error)
        does no terminal persist -> orphan (record-loss, in-doubt), surfaced and reconciled out-of-band."""
        # PREPARE — intent-to-act, committed at depth 0 BEFORE the effect.
        prepare = self._emit_irreversible(
            op, authority, params, "prepare", idempotency_key, jurisdiction, intent_ref, warrant_id,
            failed=False, gate_admit_ref=admit_ref)
        prepare_ref = getattr(prepare, "h_r", "") or ""

        # effect() — the irreversible external act. NOT inside a rollback scope.
        try:
            result = effect()
        except ExternalEffectNotPerformed:
            # CONFIRMED non-performance -> clean ABORT (NOT a rollback; the act provably never occurred).
            # r121/AD-46: the ABORT terminal write gets the SAME bounded store-retry as COMMIT. On
            # exhaustion the orphan stands and TerminalWriteExhausted propagates (chaining this signal).
            self._emit_terminal_durable(
                op, authority, params, "abort", idempotency_key, jurisdiction, intent_ref, warrant_id,
                failed=True, prepare_ref=prepare_ref, abort_reason="external_effect_not_performed")
            raise
        # NOTE (load-bearing): any OTHER exception is deliberately NOT caught. It propagates with NO
        # terminal written, leaving a PREPARE with no COMMIT/ABORT == an orphan PREPARE (in-doubt). The
        # kernel does not guess an outcome; the orphan detector reports it. This is the irreducible,
        # honest residue of irreversible external effects.

        # effect returned -> COMMIT (confirmed performed), depth 0, AFTER the effect (success-after-effect).
        # r121/AD-46: bounded store-retry of the COMMIT terminal write ONLY (the effect already returned
        # and is NEVER re-invoked). On exhaustion -> TerminalWriteExhausted, no terminal, orphan stands.
        self._emit_terminal_durable(
            op, authority, params, "commit", idempotency_key, jurisdiction, intent_ref, warrant_id,
            failed=False, prepare_ref=prepare_ref)
        return result

    def _verify_reconciliation_warrant(self, warrant_id):
        """r141 (Frontier 5, increment 1): verify the ADMISSIBLE BASIS of a verified-grade
        reconciliation. This checks the cited DecisionWarrant's content-addressed integrity, its
        resolvability in the WarrantStore, its CURRENT-FRAME binding (law/legend), and that it carries a
        non-empty constitutional basis. It is WARRANT-BACKED verified-grade -- it upgrades the basis from
        a free-string confession to an admissible, hash-verifiable, frame-bound warrant; it does NOT and
        cannot prove the external-world event occurred (the kernel still records, never witnesses). Fail
        closed: raises ReconciliationRefused (writing NOTHING) on any violation."""
        if self._warrant_store is None:
            raise ReconciliationRefused("verified-requires-warrant-store")
        if not (isinstance(warrant_id, str) and warrant_id.strip()):
            raise ReconciliationRefused("verified-requires-warrant-id")
        w = self._warrant_store.get(warrant_id)
        if w is None:
            raise ReconciliationRefused("warrant-not-found")
        if not w.verify_hash():
            raise ReconciliationRefused("warrant-hash-invalid")
        if w.law_hash != self._law_hash or w.legend_hash != self._legend_hash:
            raise ReconciliationRefused("warrant-stale-frame")
        if not w.constitutional_basis:
            raise ReconciliationRefused("warrant-basis-invalid")
        return w  # r143/AD-66: return verified warrant so the arc can commit a self-verifying snapshot

    def reconcile_external_irreversible(self, *, prepare_ref, determination, evidence_ref,
                                        authority, jurisdiction="session", intent_ref=None,
                                        warrant_id="", verified=False):
        """r123 / AD-47: the governed, out-of-band RECONCILIATION of an orphan EXTERNAL_IRREVERSIBLE
        PREPARE. It RECORDS an outcome that a governed operator determined by an EXTERNAL check; it runs
        NO effect, performs/re-performs/retries NOTHING, and NEVER infers an outcome.

        It closes an orphan ONLY by writing one provenance-marked terminal for the EXACT existing
        (idempotency_key, prepare_ref) pair, so the unchanged strict-match detector then sees it resolved.

        Strict, fail-closed contract (raises ReconciliationRefused, writing NOTHING, on any violation):
          * authority required and recorded (reconciled_by);
          * evidence_ref required and recorded (reconciliation_evidence_ref) -- recorded, NOT verified
            (confess-and-audit, as with the effect's own truthfulness);
          * determination must be exactly 'performed' or 'not_performed'. Anything else -- including a
            'cannot determine' inconclusive check -- is a first-class REFUSAL; the orphan stays in_doubt;
          * prepare_ref must be an OUTSTANDING orphan at write time: it must name a PREPARE that currently
            has NO terminal (the strict per-prepare_ref rule via detect_orphan_prepares). Unknown ref, a
            non-PREPARE ref, and an already-terminal'd ref all refuse -- guaranteeing AT MOST ONE terminal
            per (key, prepare_ref) (the r121 no-duplicate-terminal discipline, enforced here too).

        On success: determination='performed' -> a reconciling COMMIT; 'not_performed' -> a reconciling
        ABORT (abort_reason='reconciled_not_performed', DISTINCT from the in-band
        'external_effect_not_performed' so the two are never conflated). Both carry reconciled=true,
        reconciled_by, reconciliation_evidence_ref, determination -- durable, deterministic provenance so
        a reconciled terminal is NEVER mistaken for an in-band one (no laundering). The terminal write
        reuses the AD-46 durable path (bounded retry of the store write only); on exhaustion no terminal
        persists and the orphan stands. A reconciling ABORT records determined non-performance and NEVER
        claims the act was undone. The detector is unchanged; this is purely the lawful WRITER it assumed."""
        from ugk.integrity.external_irreversible import detect_orphan_prepares
        # --- strict input validation (fail closed; no mutation on any refusal) ---
        if not (isinstance(authority, str) and authority.strip()):
            raise ReconciliationRefused("authority-required")
        if not (isinstance(evidence_ref, str) and evidence_ref.strip()):
            raise ReconciliationRefused("evidence-required")
        if determination not in ("performed", "not_performed"):
            # includes None / 'cannot determine' / any other value: never force a terminal.
            raise ReconciliationRefused("determination-undetermined")
        if not (isinstance(prepare_ref, str) and prepare_ref):
            raise ReconciliationRefused("prepare_ref-required")
        # --- target must be an OUTSTANDING orphan (re-checked at write time) ---
        receipts = self._store.all_receipts()
        orphan = next((o for o in detect_orphan_prepares(receipts) if o["prepare_ref"] == prepare_ref), None)
        if orphan is None:
            # unknown ref, non-PREPARE ref, or already-terminal'd (non-orphan) ref all land here.
            raise ReconciliationRefused("not-an-outstanding-orphan")
        op = orphan["op"]
        idempotency_key = orphan["idempotency_key"]
        # r141 (Frontier 5, increment 1): OPT-IN verified-grade. When requested, the cited warrant must
        # verify (store present, resolvable, hash-intact, current-frame-bound, non-empty basis) or the
        # reconciliation fails closed. The recorded-grade path (verified=False) is UNCHANGED.
        _w = self._verify_reconciliation_warrant(warrant_id) if verified else None
        warrant_id = warrant_id or ""        # NOT NULL sentinel (recorded-grade: warrant requirement deferred, §10.3)
        intent_ref = intent_ref or ""        # NOT NULL sentinel
        # --- write the single provenance-marked terminal for THIS exact (key, prepare_ref) ---
        markers = {
            "reconciled": True,
            "reconciled_by": authority,
            "reconciliation_evidence_ref": evidence_ref,
            "determination": determination,
        }
        if verified:
            # r143/AD-66: grade + self-verifying snapshot travel via markers; write() promotes both to the
            # typed v6 columns and STRIPS them from parameters (sole committed surface). sha256(snapshot)==warrant_id.
            markers["reconciliation_grade"] = "verified"
            markers["reconciliation_warrant_snapshot"] = _warrant_cj(_w.body_dict()).decode("utf-8")
        if determination == "performed":
            return self._emit_terminal_durable(
                op, authority, markers, "commit", idempotency_key, jurisdiction, intent_ref, warrant_id,
                failed=False, prepare_ref=prepare_ref)
        return self._emit_terminal_durable(
            op, authority, markers, "abort", idempotency_key, jurisdiction, intent_ref, warrant_id,
            failed=True, prepare_ref=prepare_ref, abort_reason="reconciled_not_performed")

    # ------------------------------------------------------------------ r132 / AD-55
    #   EXTERNAL_REVERSIBLE (compensation / saga)
    # ------------------------------------------------------------------
    @staticmethod
    def compose_compensation_key(idempotency_key, phase="compensate"):
        """r132 / AD-55: a DETERMINISTIC composite compensation idempotency key derived from the
        forward effect's idempotency_key plus the compensation phase. It is GUARANTEED DISTINCT from
        the forward key (the '::' + phase suffix), so a caller that uses it cannot ambiguously reuse
        the original key. A convenience only -- a caller may instead supply its own dedicated
        compensation_idempotency_key; either way the distinctness contract is enforced in
        compensate_external_reversible (a key equal to the forward key fails closed)."""
        return "%s::%s" % (idempotency_key, phase)

    def _emit_reversible(self, op, authority, base_params, phase, idempotency_key,
                         jurisdiction, intent_ref, warrant_id, failed,
                         prepare_ref=None, gate_admit_ref=None, abort_reason=None,
                         compensate_ref=None, compensation_idempotency_key=None):
        """r132 / AD-55: write one EXTERNAL_REVERSIBLE phase receipt at depth 0 in the EXISTING receipt
        shape -- all distinguishing fields are parameters-JSON markers, NO schema column (mirrors
        _emit_irreversible). Forward-effect phases: prepare / commit / abort. Compensation-arc phases:
        compensate / compensated / compensation_failed. The compensation arc carries its OWN distinct
        compensation_idempotency_key and references the forward COMMIT via compensate_ref; it NEVER
        reuses the forward effect's idempotency_key in that slot. Returns the Receipt."""
        p = dict(base_params or {})
        # r139 (Lane 1): typed columns primary; markers derived by the store (byte-identical write).
        effect_columns = {
            "effect_atomicity": EffectAtomicity.EXTERNAL_REVERSIBLE.value,
            "effect_phase": phase,
            "effect_idempotency_key": idempotency_key,
            "effect_gate_admit_ref": gate_admit_ref,
            "effect_prepare_ref": prepare_ref,
            "effect_compensate_ref": compensate_ref,
            "effect_compensation_idempotency_key": compensation_idempotency_key,
            "effect_abort_reason": abort_reason,
        }
        return self._store.write(
            op=op, authority=authority, parameters=p, failed=failed, intent=op,
            jurisdiction=jurisdiction, session_dkn=self._session_dkn,
            law_hash=self._law_hash, legend_hash=self._legend_hash,
            warrant_id=warrant_id, intent_ref=intent_ref, effect_columns=effect_columns,
        )

    def _emit_reversible_terminal_durable(self, op, authority, base_params, phase, idempotency_key,
                                          jurisdiction, intent_ref, warrant_id, failed,
                                          prepare_ref=None, gate_admit_ref=None, abort_reason=None,
                                          compensate_ref=None, compensation_idempotency_key=None):
        """r136 / AD-59: write an EXTERNAL_REVERSIBLE TERMINAL receipt with a BOUNDED in-process
        retry of the STORE WRITE ONLY -- the exact AD-46 discipline applied to the reversible class.

        Terminals are the FORWARD trail terminals (phase in {commit, abort}, after the forward effect has
        returned / raised ExternalEffectNotPerformed) and the COMPENSATION-arc terminals (phase in
        {compensated, compensation_failed}, after the compensation action has returned / raised). In every
        case the outcome is ALREADY known when this is called: the external act / the compensating action
        lives entirely OUTSIDE this helper, BEFORE the call site, and is NEVER re-invoked here. This helper
        re-attempts only a durable RECORD of an outcome that already happened; it re-attempts persistence,
        never the external act and never the compensating action.

        Discipline (identical to _emit_terminal_durable / AD-46):
          * retries ONLY the narrow named transient-store set (_is_retryable_terminal_write_error);
            ANY other exception fails closed IMMEDIATELY (re-raise on the first attempt) -> the intent
            (PREPARE or COMPENSATE) remains an orphan, in-doubt;
          * at most MAX_OUTCOME_WRITE_ATTEMPTS attempts; NO sleep / NO backoff (immediate, synchronous);
          * on exhaustion: NO terminal persists -> raise TerminalWriteExhausted (the orphan stands,
            record-loss), chaining the last transient store error;
          * Option A -- records NOTHING about the retry in the receipt: a terminal written on attempt k is
            byte-identical in PARAMETERS to one written on attempt 1 (only the inherent, already-varying
            write timestamp differs), so the chain hash carries no retry nondeterminism.

        It does NOT auto-resolve an orphan PREPARE or orphan COMPENSATE, does NOT infer an outcome, does
        NOT convert an execution failure into REFUSE, and does NOT alter the ADMIT decision (TO-S-01) or
        the trail's class-relative conformance (EFFECT-S-01) -- it changes only the durability of a
        terminal record whose semantics are unchanged."""
        assert phase in ("commit", "abort", "compensated", "compensation_failed"), \
            "reversible durable retry is for terminals only (commit/abort/compensated/compensation_failed)"
        ref = prepare_ref or compensate_ref     # the in-doubt intent the orphan would stand on (log only)
        last_exc = None
        for _attempt in range(1, MAX_OUTCOME_WRITE_ATTEMPTS + 1):
            try:
                return self._emit_reversible(
                    op, authority, base_params, phase, idempotency_key, jurisdiction, intent_ref,
                    warrant_id, failed=failed, prepare_ref=prepare_ref, gate_admit_ref=gate_admit_ref,
                    abort_reason=abort_reason, compensate_ref=compensate_ref,
                    compensation_idempotency_key=compensation_idempotency_key)
            except Exception as exc:
                if not _is_retryable_terminal_write_error(exc):
                    raise                       # fail closed immediately -> orphan, original error surfaces
                last_exc = exc                  # transient -> retry immediately (no sleep)
        raise TerminalWriteExhausted(phase, ref, MAX_OUTCOME_WRITE_ATTEMPTS) from last_exc

    def _execute_external_reversible(self, op, authority, params, effect, idempotency_key,
                                     jurisdiction, intent_ref, admit_ref, warrant_id):
        """r132 / AD-55: the EXTERNAL_REVERSIBLE FORWARD-effect trail (compensation/saga class).

        The forward effect mirrors the EXTERNAL_IRREVERSIBLE trail EXACTLY -- three INDEPENDENT depth-0
        receipts, NOT inside store.transaction() (an external effect is not store-rollback-able):

          PREPARE (intent-to-act, BEFORE effect; NBER-1; carries idempotency_key + gate_admit_ref)
            -> effect()  [the forward external act]
                 returns normally          -> COMMIT (confirmed performed; written AFTER the effect)
                 ExternalEffectNotPerformed -> ABORT  (confirmed NOT performed)
                 any other exception        -> NO terminal written, re-raise -> orphan PREPARE (in-doubt)

        Identically to EXTERNAL_IRREVERSIBLE, the kernel NEVER infers an outcome from an orphan PREPARE
        (an ambiguous failure and a crash between PREPARE and terminal are both genuinely in-doubt and
        the detector surfaces them), and the gate_admit decision stays ADMIT throughout (an in-doubt
        forward failure is execution status, NEVER a REFUSE). The DIFFERENCE from EXTERNAL_IRREVERSIBLE
        is purely downstream and OUT OF BAND: a committed forward effect MAY later be OFFSET by a
        COMPENSATING forward action via compensate_external_reversible -- a SEPARATE governed call with
        its OWN COMPENSATE intent receipt written BEFORE the compensating action and its OWN distinct
        compensation idempotency scope. Compensation is NOT a hidden side effect of COMMIT and never
        runs automatically here. A COMMITTED forward effect stays HISTORICALLY TRUE even after it is
        compensated; COMPENSATED records an OFFSET, never an erasure, and the kernel NEVER claims the
        forward act was physically undone."""
        # PREPARE -- intent-to-act, committed at depth 0 BEFORE the effect (receipt-before-effect).
        prepare = self._emit_reversible(
            op, authority, params, "prepare", idempotency_key, jurisdiction, intent_ref, warrant_id,
            failed=False, gate_admit_ref=admit_ref)
        prepare_ref = getattr(prepare, "h_r", "") or ""
        # effect() -- the forward external act. NOT inside a rollback scope.
        try:
            result = effect()
        except ExternalEffectNotPerformed:
            # CONFIRMED non-performance -> clean ABORT (the act provably never occurred; never undone).
            self._emit_reversible_terminal_durable(
                op, authority, params, "abort", idempotency_key, jurisdiction, intent_ref, warrant_id,
                failed=True, prepare_ref=prepare_ref, abort_reason="external_effect_not_performed")
            raise
        # NOTE (load-bearing): any OTHER exception is deliberately NOT caught. It propagates with NO
        # terminal written, leaving a PREPARE with no COMMIT/ABORT == an orphan PREPARE (in-doubt). The
        # kernel does not guess; the orphan detector reports it; the admission decision stays ADMIT.
        self._emit_reversible_terminal_durable(
            op, authority, params, "commit", idempotency_key, jurisdiction, intent_ref, warrant_id,
            failed=False, prepare_ref=prepare_ref)
        return result

    def compensate_external_reversible(self, *, prepare_ref, compensation_effect,
                                       compensation_idempotency_key, authority,
                                       jurisdiction="session", intent_ref=None, warrant_id=""):
        """r132 / AD-55: the SEPARATELY GOVERNED, SEPARATELY IDEMPOTENT compensation arc for a
        COMMITTED EXTERNAL_REVERSIBLE forward effect.

        Compensation is a NEW FORWARD offsetting action (e.g., a refund offsets a charge), NOT a
        physical undo and NOT a store rollback. The Governor tightening, enforced here: it is NOT a
        hidden side effect of COMMIT -- it runs ONLY when a governed caller explicitly invokes it, it
        writes its OWN COMPENSATE intent receipt at depth 0 BEFORE the compensating action
        (receipt-before-effect all the way down), and it carries its OWN distinct compensation
        idempotency scope, NEVER reusing the forward effect's idempotency_key.

        Fail-closed contract (raises CompensationRefused, writing NOTHING, running no action, on any
        violation):
          * authority required;
          * compensation_idempotency_key required (non-empty str) -- a missing key fails closed;
          * compensation_idempotency_key MUST be DISTINCT from the forward effect's idempotency_key --
            ambiguous reuse fails closed (use a dedicated key or compose_compensation_key());
          * prepare_ref must name a forward EXTERNAL_REVERSIBLE effect that is currently COMMITTED and
            NOT already compensated/compensating -- otherwise fail closed (compensation applies to a
            PERFORMED forward effect, never to an aborted, in-doubt, or already-offset one).

        Phases:
          COMPENSATE (intent-to-offset, depth 0, BEFORE the compensating action; references the
            forward COMMIT via prepare_ref/compensate_ref; carries the distinct compensation key)
            -> compensation_effect()  [the forward offsetting action]
                 returns normally  -> COMPENSATED (offset confirmed; the forward COMMIT STILL STANDS --
                                      an offset, never an erasure)
                 raises            -> COMPENSATION_FAILED (failed=True; UNRESOLVED execution status --
                                      the forward effect happened and the offset did not; NEVER a
                                      REFUSE, NEVER a false success)

        An orphan COMPENSATE (intent written, no terminal -- e.g., a crash) is in-doubt and surfaced by
        the detector; the kernel never infers the offset's outcome and never auto-resolves."""
        from ugk.integrity.external_reversible import find_committed_forward
        # --- strict input validation (fail closed; NO mutation, NO action on any refusal) ---
        if not (isinstance(authority, str) and authority.strip()):
            raise CompensationRefused("authority-required")
        if not (isinstance(compensation_idempotency_key, str) and compensation_idempotency_key.strip()):
            raise CompensationRefused("compensation-key-required")
        if not (isinstance(prepare_ref, str) and prepare_ref):
            raise CompensationRefused("prepare_ref-required")
        if not callable(compensation_effect):
            raise CompensationRefused("compensation-effect-required")
        # --- target must be a COMMITTED, not-yet-compensated forward effect (re-checked here) ---
        receipts = self._store.all_receipts()
        fwd = find_committed_forward(receipts, prepare_ref)
        if fwd is None:
            # unknown ref, non-committed (aborted/in-doubt) ref, or already-compensated ref land here.
            raise CompensationRefused("not-a-compensable-committed-forward-effect")
        fwd_op = fwd["op"]
        fwd_key = fwd["idempotency_key"]
        # --- distinctness: a compensation must NOT ambiguously reuse the forward effect's key ---
        if compensation_idempotency_key == fwd_key:
            raise CompensationRefused("ambiguous-compensation-key-reuses-forward-key")
        intent_ref = intent_ref or ""
        warrant_id = warrant_id or ""
        markers = {"compensates_prepare_ref": prepare_ref}
        # COMPENSATE -- intent-to-offset, depth 0, BEFORE the compensating action (receipt-before-effect).
        self._emit_reversible(
            fwd_op, authority, markers, "compensate", fwd_key, jurisdiction, intent_ref, warrant_id,
            failed=False, compensate_ref=prepare_ref,
            compensation_idempotency_key=compensation_idempotency_key)
        # compensation_effect() -- the forward offsetting action. NOT inside a rollback scope.
        try:
            result = compensation_effect()
        except Exception:
            # the offset FAILED -> COMPENSATION_FAILED: unresolved execution status (the forward effect
            # happened and the offset did not). failed=True, NEVER a REFUSE, NEVER a false success.
            self._emit_reversible_terminal_durable(
                fwd_op, authority, markers, "compensation_failed", fwd_key, jurisdiction, intent_ref,
                warrant_id, failed=True, compensate_ref=prepare_ref,
                compensation_idempotency_key=compensation_idempotency_key,
                abort_reason="compensation_effect_failed")
            raise
        # the offset succeeded -> COMPENSATED (confirmed offset; the forward COMMIT STILL STANDS).
        self._emit_reversible_terminal_durable(
            fwd_op, authority, markers, "compensated", fwd_key, jurisdiction, intent_ref, warrant_id,
            failed=False, compensate_ref=prepare_ref,
            compensation_idempotency_key=compensation_idempotency_key)
        return result

    # ------------------------------------------------------------------ r137 / AD-60
    #   EXTERNAL_REVERSIBLE governed reconciliation (the AD-47 analogue for the reversible class):
    #   the out-of-band RESOLUTION of honest in-doubt residue that survives bounded retry exhaustion.
    #   Two arcs: an orphan FORWARD PREPARE, and an orphan COMPENSATE. Each RECORDS an outcome a
    #   governed operator determined by an EXTERNAL check; neither runs the external effect nor the
    #   compensating action, neither infers an outcome, neither auto-resolves. Closure is by writing ONE
    #   provenance-marked terminal for the EXACT orphan key/ref, so the UNCHANGED reversible detector
    #   then sees it resolved (detector = reader, this = the lawful writer it always assumed).
    # ------------------------------------------------------------------
    def reconcile_external_reversible_forward(self, *, prepare_ref, determination, evidence_ref,
                                              authority, jurisdiction="session", intent_ref=None,
                                              warrant_id="", verified=False):
        """r137 / AD-60: governed reconciliation of an orphan EXTERNAL_REVERSIBLE FORWARD PREPARE -- the
        reversible-class analogue of reconcile_external_irreversible (AD-47), forward arc. It RECORDS an
        externally-determined outcome; runs NO effect, retries/performs/infers NOTHING.

        Strict, fail-closed contract (raises ReconciliationRefused, writing NOTHING, on any violation):
          * authority required and recorded (reconciled_by);
          * evidence_ref required and recorded (reconciliation_evidence_ref) -- recorded, NOT verified
            (confess-and-audit);
          * determination must be exactly 'performed' or 'not_performed'; anything else (incl. None /
            'cannot determine') is a first-class REFUSAL; the orphan stays in_doubt;
          * prepare_ref must be an OUTSTANDING orphan at write time (via the REVERSIBLE
            detect_orphan_prepares) -- unknown / non-PREPARE / already-terminal'd all refuse, so AT MOST
            ONE terminal exists per (key, prepare_ref).

        On success: 'performed' -> a reconciling COMMIT; 'not_performed' -> a reconciling ABORT
        (abort_reason='reconciled_not_performed', DISTINCT from the in-band 'external_effect_not_performed'
        so the two are never conflated). Both carry reconciled=true + provenance markers so a reconciled
        terminal is NEVER mistaken for an in-band one. The terminal write reuses the AD-59 reversible
        durable path (bounded retry of the store write only); on exhaustion no terminal persists and the
        orphan stands. A reconciling ABORT records determined non-performance and NEVER claims undo."""
        from ugk.integrity.external_reversible import detect_orphan_prepares
        if not (isinstance(authority, str) and authority.strip()):
            raise ReconciliationRefused("authority-required")
        if not (isinstance(evidence_ref, str) and evidence_ref.strip()):
            raise ReconciliationRefused("evidence-required")
        if determination not in ("performed", "not_performed"):
            raise ReconciliationRefused("determination-undetermined")
        if not (isinstance(prepare_ref, str) and prepare_ref):
            raise ReconciliationRefused("prepare_ref-required")
        receipts = self._store.all_receipts()
        orphan = next((o for o in detect_orphan_prepares(receipts) if o["prepare_ref"] == prepare_ref), None)
        if orphan is None:
            raise ReconciliationRefused("not-an-outstanding-orphan")
        op = orphan["op"]
        idempotency_key = orphan["idempotency_key"]
        # r141 (Frontier 5, increment 1): OPT-IN verified-grade (see reconcile_external_irreversible).
        _w = self._verify_reconciliation_warrant(warrant_id) if verified else None
        warrant_id = warrant_id or ""
        intent_ref = intent_ref or ""
        markers = {
            "reconciled": True,
            "reconciled_by": authority,
            "reconciliation_evidence_ref": evidence_ref,
            "determination": determination,
            "arc": "forward",
        }
        if verified:
            # r143/AD-66: grade + self-verifying snapshot travel via markers; write() promotes both to the
            # typed v6 columns and STRIPS them from parameters (sole committed surface). sha256(snapshot)==warrant_id.
            markers["reconciliation_grade"] = "verified"
            markers["reconciliation_warrant_snapshot"] = _warrant_cj(_w.body_dict()).decode("utf-8")
        if determination == "performed":
            return self._emit_reversible_terminal_durable(
                op, authority, markers, "commit", idempotency_key, jurisdiction, intent_ref, warrant_id,
                failed=False, prepare_ref=prepare_ref)
        return self._emit_reversible_terminal_durable(
            op, authority, markers, "abort", idempotency_key, jurisdiction, intent_ref, warrant_id,
            failed=True, prepare_ref=prepare_ref, abort_reason="reconciled_not_performed")

    def reconcile_external_reversible_compensation(self, *, compensate_ref, determination, evidence_ref,
                                                   authority, jurisdiction="session", intent_ref=None,
                                                   warrant_id="", verified=False):
        """r137 / AD-60: governed reconciliation of an orphan EXTERNAL_REVERSIBLE COMPENSATE -- the
        compensation arc. It RECORDS whether a governed operator determined, by an EXTERNAL check, that
        the compensating OFFSET was performed; it runs NO compensation action, retries/performs/infers
        NOTHING, and NEVER claims the forward effect was physically undone.

        Strict, fail-closed contract (raises ReconciliationRefused, writing NOTHING, on any violation):
          * authority required and recorded (reconciled_by);
          * evidence_ref required and recorded (reconciliation_evidence_ref) -- recorded, NOT verified;
          * determination must be exactly 'performed' or 'not_performed'; anything else is a first-class
            REFUSAL; the orphan stays in_doubt;
          * compensate_ref must name an OUTSTANDING orphan COMPENSATE at write time (via the REVERSIBLE
            detect_orphan_compensates) -- unknown / non-COMPENSATE / already-terminal'd all refuse, so AT
            MOST ONE compensation terminal exists per (compensate_ref, compensation_idempotency_key).

        On success: 'performed' -> a reconciling COMPENSATED (the offset is determined to have run; an
        OFFSET, NOT an undo -- the forward COMMIT stays historically true; NO erasure marker is ever set);
        'not_performed' -> a reconciling COMPENSATION_FAILED (the offset is determined NOT to have run;
        unresolved business state, the forward effect stands), abort_reason='reconciled_compensation_not_performed'
        -- DISTINCT from the in-band 'compensation_effect_failed' so the two are never conflated. Both
        carry reconciled=true + provenance markers (no laundering). Either compensation terminal CLEARS
        the orphan via the unchanged detector. The terminal write reuses the AD-59 reversible durable
        path; on exhaustion no terminal persists and the orphan stands. A reconciling COMPENSATION_FAILED
        is an execution-status failure (failed=True), NEVER a REFUSE."""
        from ugk.integrity.external_reversible import detect_orphan_compensates
        if not (isinstance(authority, str) and authority.strip()):
            raise ReconciliationRefused("authority-required")
        if not (isinstance(evidence_ref, str) and evidence_ref.strip()):
            raise ReconciliationRefused("evidence-required")
        if determination not in ("performed", "not_performed"):
            raise ReconciliationRefused("determination-undetermined")
        if not (isinstance(compensate_ref, str) and compensate_ref):
            raise ReconciliationRefused("compensate_ref-required")
        receipts = self._store.all_receipts()
        orphan = next((o for o in detect_orphan_compensates(receipts)
                       if o["compensate_ref"] == compensate_ref), None)
        if orphan is None:
            raise ReconciliationRefused("not-an-outstanding-orphan")
        op = orphan["op"]
        compensation_idempotency_key = orphan["compensation_idempotency_key"]
        # recover the forward effect's key from the COMPENSATE intent receipt, so the reconciled
        # compensation terminal carries the SAME idempotency_key slot the in-band terminal would (the
        # detector + EFFECT-S-02 anchor on (compensate_ref, compensation_idempotency_key); this is for
        # trail-linkage fidelity only). Falls back to the compensation key if the intent is unreadable.
        # r142 (AD-65): read the typed effect COLUMNS (authoritative for v>=4 / v5), with parameter-marker
        # fallback for v<4 marker-era receipts.
        def _ef(r, col, marker):
            v = getattr(r, col, None)
            return v if v is not None else (r.parameters or {}).get(marker)
        comp_rec = next((r for r in receipts
                         if _ef(r, "effect_phase", "phase") == "compensate"
                         and _ef(r, "effect_compensate_ref", "compensate_ref") == compensate_ref
                         and _ef(r, "effect_compensation_idempotency_key", "compensation_idempotency_key")
                             == compensation_idempotency_key), None)
        fwd_key = (_ef(comp_rec, "effect_idempotency_key", "idempotency_key")
                   if comp_rec is not None else compensation_idempotency_key)
        # r141 (Frontier 5, increment 1): OPT-IN verified-grade (see reconcile_external_irreversible).
        _w = self._verify_reconciliation_warrant(warrant_id) if verified else None
        warrant_id = warrant_id or ""
        intent_ref = intent_ref or ""
        markers = {
            "reconciled": True,
            "reconciled_by": authority,
            "reconciliation_evidence_ref": evidence_ref,
            "determination": determination,
            "arc": "compensation",
        }
        if verified:
            # r143/AD-66: grade + self-verifying snapshot travel via markers; write() promotes both to the
            # typed v6 columns and STRIPS them from parameters (sole committed surface). sha256(snapshot)==warrant_id.
            markers["reconciliation_grade"] = "verified"
            markers["reconciliation_warrant_snapshot"] = _warrant_cj(_w.body_dict()).decode("utf-8")
        if determination == "performed":
            return self._emit_reversible_terminal_durable(
                op, authority, markers, "compensated", fwd_key, jurisdiction, intent_ref, warrant_id,
                failed=False, compensate_ref=compensate_ref,
                compensation_idempotency_key=compensation_idempotency_key)
        return self._emit_reversible_terminal_durable(
            op, authority, markers, "compensation_failed", fwd_key, jurisdiction, intent_ref, warrant_id,
            failed=True, compensate_ref=compensate_ref,
            compensation_idempotency_key=compensation_idempotency_key,
            abort_reason="reconciled_compensation_not_performed")

    def execute(
        self,
        op:           str,
        authority:    Optional[str] = None,
        parameters:   Optional[dict] = None,
        gate:         Optional[Callable[[], bool]] = None,
        effect:       Optional[Callable[[], Any]] = None,
        effect_atomicity: Optional[EffectAtomicity] = None,
        idempotency_key: Optional[str] = None,
        gate_margin:  Optional[float] = None,
        layer:        str = "I",
        jurisdiction: str = "session",
        governor_sig:   Optional[str] = None,
        warrant_basis:  Optional[list] = None,
        intent_ref:     Optional[str] = None,
        authority_set:  Optional[list] = None,
        capability_verdicts: Optional[dict] = None,
        required_locality: Optional[str] = None,
    ) -> Any:
        """W/G/E reactor.

        Order of operations (NBER-1 / UL-S-02). Steps 1-5 are common to every path; step 5
        (gate_admit, depth 0) is the durable decision-before-effect receipt and ALWAYS precedes
        effect(). What follows gate_admit depends on the declared effect class:
          1. op ∈ _KERNEL_OPS?                → KernelInternalOp
          2. op ∉ _UNIVERSAL_OPS ∧ UNINIT?    → GovernanceNotFounded
          3. op ∉ GOVERNANCE_OPS?             → UndeclaredOp (BS-01)
          4. gate() → False?                  → GateRefusal + gate_refuse receipt
          5. emit gate_admit receipt (depth 0; precedes effect() on every path)
          6. then, by effect class:
             - NON_ATOMIC / no-effect : write success (depth 0) BEFORE effect(), then call effect()
                                        (the legacy order; success-before-effect)
             - PURE / STORE_LOCAL     : [effect() + success] run in the AD-38 seam — success written
                                        AFTER effect() returns, committing/rolling-back together; a
                                        failed effect leaves a durable structural abort, no false success
             - EXTERNAL_IRREVERSIBLE  : PREPARE (depth 0, before effect) → effect() → COMMIT after a
                                        confirmed-performed return | ABORT on ExternalEffectNotPerformed
                                        (confirmed non-performance) | no terminal + re-raise on any other
                                        exception (orphan PREPARE, in-doubt) — AD-44
             - EXTERNAL_REVERSIBLE    : forward PREPARE → effect() → COMMIT | ABORT | orphan (mirrors
                                        EXTERNAL_IRREVERSIBLE) plus a SEPARATELY-GOVERNED compensation arc
                                        (compensate_external_reversible: COMPENSATE → COMPENSATED |
                                        COMPENSATION_FAILED), requires a forward idempotency_key — AD-55

        gate_admit (step 5) precedes effect() ALWAYS — that ordering is load-bearing. The SUCCESS
        receipt precedes effect() only on the NON_ATOMIC/legacy path; the seam and the two-phase path
        write their success/COMMIT AFTER effect().
        """
        # r97 / AD-32 PREFLIGHT - validate the protocol boundary BEFORE any normalization or write.
        # r96 proved parameters were JSON-serializable but did NOT enforce dict-ness, so a non-dict
        # JSON value (parameters="bad" / 1) passed preflight and crashed AFTER gate_admit, and a falsy
        # non-None value (parameters=[]) was silently normalized to {} by `or {}`. The contract is
        # validated FIRST: authority is None|non-empty-str; parameters is None|dict; warrant_basis is
        # sortable; authority_set is a JSON-serializable list. Malformed -> controlled ProtocolError
        # with ZERO mutation (Invariant A: no admit before the refusal horizon is exhausted).
        if authority is None:
            authority = self._authority
        elif not isinstance(authority, str) or authority == "":
            raise ProtocolError(op, "authority must be a non-empty string, got %r" % (authority,))
        if parameters is None:
            parameters = {}
        elif not isinstance(parameters, dict):
            raise ProtocolError(op, "parameters must be a dict or None, got %s" % type(parameters).__name__)
        from ugk.storage.store import _params_json as _pj_preflight
        try:
            _pj_preflight(parameters)   # dict contents must be JSON-serializable (store's own serializer)
        except (TypeError, ValueError) as _perr:
            raise ProtocolError(op, "parameters not JSON-serializable: %s" % _perr)
        # r156 / CK-CANON float ban (V9): a float anywhere in governance-relevant
        # parameters fails closed as a protocol failure BEFORE admission. json.dumps
        # would silently serialize floats (IEEE-754); CK-CANON-0.1 §3 bans them.
        _reject_floats_in_governance_input(op, parameters)
        if warrant_basis is not None:
            # contract: warrant_basis is a sortable list of CSIL addresses (the system computes
            # sorted(warrant_basis)); "bad" = a non-list or an unsortable list (what would crash sorted()).
            if not isinstance(warrant_basis, (list, tuple)):
                raise ProtocolError(op, "warrant_basis must be a list, got %s" % type(warrant_basis).__name__)
            try:
                sorted(warrant_basis)
            except TypeError as _werr:
                raise ProtocolError(op, "warrant_basis is not sortable: %s" % _werr)
        if authority_set is not None:
            # authority_set is folded into the success-receipt parameters AFTER admit; validate it here
            # so a non-list or non-JSON authority_set fails closed before any write.
            if not isinstance(authority_set, (list, tuple)):
                raise ProtocolError(op, "authority_set must be a list, got %s" % type(authority_set).__name__)
            try:
                _pj_preflight({"authority_set": list(authority_set)})
            except (TypeError, ValueError) as _aerr:
                raise ProtocolError(op, "authority_set not JSON-serializable: %s" % _aerr)

        # r102-a / AD-37 - EffectAtomicity contract. effect() is a side effect on the world the
        # kernel cannot prove rollback-able; it MUST declare its atomicity class. An undeclared
        # effect, or a declared-but-unimplemented atomic class, fails closed HERE - before gate
        # eval, gate_admit, the success receipt, or effect itself - with ZERO mutation (no receipt),
        # exactly like the protocol-boundary checks above. r102-a implements ONLY the NON_ATOMIC
        # legacy bridge: it preserves legacy execution order while making the lack of atomicity
        # explicit and auditable. NON_ATOMIC is NOT success-proof, rollback-proof, or Invariant-E-safe.
        if effect is not None:
            if effect_atomicity is None:
                raise ProtocolError(
                    op, "effect supplied without an EffectAtomicity declaration; undeclared "
                        "effects fail closed (r102-a / AD-37)")
            if effect_atomicity == EffectAtomicity.EXTERNAL_REVERSIBLE:
                # r132 / AD-55: EXTERNAL_REVERSIBLE now PROCEEDS via the compensation/saga trail. The
                # FORWARD effect runs a two-phase PREPARE/COMMIT/ABORT trail mirroring
                # EXTERNAL_IRREVERSIBLE and likewise REQUIRES a caller-supplied, non-empty
                # idempotency_key; a missing/empty key -> controlled ProtocolError with ZERO mutation,
                # BEFORE gate_admit (the AD-37 posture). The COMPENSATION arc is NOT run here -- it is a
                # SEPARATE governed call (compensate_external_reversible) that carries its OWN distinct
                # compensation idempotency scope, enforced there, never on this forward path.
                if not isinstance(idempotency_key, str) or idempotency_key == "":
                    raise ProtocolError(
                        op, "EXTERNAL_REVERSIBLE requires a non-empty idempotency_key for the forward "
                            "effect (r132/AD-55; a missing key fails closed before gate_admit)")
            if effect_atomicity == EffectAtomicity.EXTERNAL_IRREVERSIBLE:
                # r115 / AD-44: EXTERNAL_IRREVERSIBLE now PROCEEDS via the two-phase PREPARE/COMMIT/ABORT
                # trail (below), but REQUIRES a caller-supplied, deterministic, non-empty idempotency_key
                # (locked decision Q1: REQUIRE, no auto-retry). A missing/empty key -> controlled
                # ProtocolError with ZERO mutation, BEFORE gate_admit - exactly the undeclared-effect
                # posture (AD-37). The kernel checks non-empty string only; DETERMINISM of the key is the
                # caller's audited contract (it is what makes a MANUAL retry externally dedup-safe), not
                # something the kernel can verify.
                if not isinstance(idempotency_key, str) or idempotency_key == "":
                    raise ProtocolError(
                        op, "EXTERNAL_IRREVERSIBLE requires a non-empty idempotency_key "
                            "(r115/AD-44; no auto-retry; a missing key fails closed before gate_admit)")

        # Step 1 — Tier 0 check (externally unreachable ops)
        if op in _KERNEL_OPS:
            self._emit_protocol_error(op, "kernel_internal", authority)
            raise KernelInternalOp(op)

        # Step 2 — UNINITIALIZED fail-close for Tier 2 ops
        if op not in _UNIVERSAL_OPS and self._status == STATUS_UNINITIALIZED:
            self._emit_protocol_error(op, "not_founded", authority)
            raise GovernanceNotFounded(op)

        # Step 2b — Governor interposition (Tier 2 ops in ACTIVE with flag set)
        if (self._require_governor_sig
                and op not in _UNIVERSAL_OPS
                and self._status == STATUS_ACTIVE):
            from ugk.governance.governor import verify_governor, GovernorSignatureRequired
            from ugk.storage.binding import canonical_json as _cj
            if governor_sig is None:
                self._emit_protocol_error(op, "governor_sig", authority)
                raise GovernorSignatureRequired(op, "no signature provided")
            msg = _cj({"op": op, "parameters": parameters or {}})
            if not verify_governor(GOVERNOR_PUBKEY_HEX, msg, governor_sig):
                self._emit_protocol_error(op, "governor_sig", authority)
                raise GovernorSignatureRequired(op, "signature verification failed")

        # Step 3 — BS-01 declaration check
        if op not in GOVERNANCE_OPS:
            self._emit_protocol_error(op, "undeclared", authority)
            raise UndeclaredOp(op)

        # CM-S-02/03: AuthorityModel enforcement
        _am = None  # r96: defined unconditionally so the post-admit warrant handler never UnboundLocalErrors
        if self._authority_model is not None and op not in _KERNEL_OPS and op not in _UNIVERSAL_OPS:
            _am=self._authority_model
            if _am.require_gate and gate is None:
                self._emit_protocol_error(op, "require_gate", authority)
                raise KernelInternalOp(f"require_gate=True: {op!r} needs a gate [{_am.model_id}]")
            if _am.require_warrant and not warrant_basis:
                self._emit_protocol_error(op, "require_warrant", authority)
                raise KernelInternalOp(f"require_warrant=True: {op!r} needs warrant_basis [{_am.model_id}]")

        # Step 4 — Gate evaluation (r96: GUARDED - a raising gate is a controlled protocol error
        # emitting a classified protocol_error receipt, not a propagated raw exception)
        if gate is not None:
            try:
                admitted = gate()
            except Exception as _gerr:
                self._emit_protocol_error(op, "gate_exception", authority)
                raise ProtocolError(op, "gate callable raised %s: %s" % (type(_gerr).__name__, _gerr))
            if not admitted:
                self._store.write(
                    op="gate_refuse",
                    authority=authority,
                    parameters={"op": op, "parameters": parameters},
                    failed=True,
                    intent="gate_refuse",
                    jurisdiction="kernel",
                    session_dkn=self._session_dkn,
                    law_hash=self._law_hash,
                )
                if layer in self._refused_by_layer:
                    self._refused_by_layer[layer] += 1
                # Produce refusal warrant if caller declared warrant_basis (DW-S-03)
                if warrant_basis is not None and self._warrant_store is not None:
                    try:
                        from ugk.governance.warrant import create_refusal_warrant
                        rw = create_refusal_warrant(
                            constitutional_basis=sorted(warrant_basis),
                            law_hash=self._law_hash,
                            legend_hash=self._legend_hash,
                        )
                        self._warrant_store.write(rw)
                    except Exception:
                        pass
                raise GateRefusal(op=op)

        # Step 4a (r146 / AD-69 -- DCAP-S-01): D_cap ENFORCEMENT, a SIBLING precondition OUTSIDE
        # aggregate(). For an ENUMERATED (jurisdiction, op/capability-class) policy entry ONLY, an op
        # that passed aggregation additionally REQUIRES PROVEN capability sufficiency (law-only recompute
        # from the supplied capability verdict census -- the same census the committed h_cap binds -- and
        # the policy artifact), else it REFUSES with the attributable cause `insufficient-capability`.
        # UNENUMERATED scopes: NO-OP (behavior unchanged). h_cap is NOT in conjunctive_refusal_monotone_v1
        # and NOT in COMMITTED_SURFACES; this precondition consults NEITHER -- it is non-aggregating.
        # Guard: exempt only _KERNEL_OPS (externally unreachable); the EXPLICIT enumeration is the scope
        # control (default-empty enforced_scopes => no-op for every op, including universal ones).
        if op not in _KERNEL_OPS:
            from ugk.cgp import capability_sufficiency as _dcap
            _pol = getattr(self, "_dcap_policy", None) or _dcap.CAPABILITY_SUFFICIENCY_POLICY
            _entry = _dcap.find_enforced_entry(_pol, jurisdiction, op)
            if _entry is not None:
                _verd = (capability_verdicts or {}).get(_entry.get("capability_class"))
                _refuse, _cause = _dcap.enforce_decision(jurisdiction=jurisdiction, op=op, verdict=_verd, policy=_pol)
                if _refuse:
                    self._store.write(
                        op="gate_refuse", authority=authority,
                        parameters={"op": op, "parameters": parameters, "refusal_cause": _cause,
                                    "capability_class": _entry.get("capability_class"),
                                    "enforced_jurisdiction": jurisdiction,
                                    "refusal_axis": "authority", "refusal_reason": "authority_missing"},
                        failed=True, intent="gate_refuse", jurisdiction="kernel",
                        session_dkn=self._session_dkn, law_hash=self._law_hash)
                    if layer in self._refused_by_layer:
                        self._refused_by_layer[layer] += 1
                    raise GateRefusal(op=op, reason="authority_missing")

        # Step 4c (r157 — NEW bounded LOCALITY precondition) — explicit, opt-in, per-transition
        # locality/jurisdiction requirement. Fires ONLY when the caller declares required_locality
        # (no global ambient requirement; calls that do not opt in are unaffected, so existing traffic
        # is unchanged). In an ACTIVE/declared op path, if the supplied jurisdiction does NOT satisfy
        # the declared required_locality, emit a constitutional gate_refuse on the LOCALITY axis (no
        # admit; replayable). This is a real decision-path check — NOT a reinterpretation of
        # GovernanceNotFounded / UndeclaredOp (those remain posture/declaration/protocol failures),
        # NOT a conversion of require_gate/require_warrant protocol errors, and NOT a mapping of the
        # opaque generic gate-false. Bounded to opt-in locality-required calls only.
        if required_locality is not None and op not in _KERNEL_OPS:
            if jurisdiction != required_locality:
                self._store.write(
                    op="gate_refuse", authority=authority,
                    parameters={"op": op, "parameters": parameters,
                                "required_locality": required_locality,
                                "supplied_jurisdiction": jurisdiction,
                                "refusal_axis": "locality", "refusal_reason": "locality_required"},
                    failed=True, intent="gate_refuse", jurisdiction="kernel",
                    session_dkn=self._session_dkn, law_hash=self._law_hash)
                if layer in self._refused_by_layer:
                    self._refused_by_layer[layer] += 1
                raise GateRefusal(op=op, reason="locality_required")

        # Step 4b (r96 / AD-31 — MOVED above gate_admit) — Will coverage check (WILL-S-06):
        # exhaust the INTENT-refusal horizon BEFORE the admit. A coverage failure now writes a
        # single gate_refuse and raises GateRefusal with NO preceding gate_admit (was: admit then refuse).
        _intent_ref = intent_ref or ""
        if self._will_store is not None:
            if op not in _KERNEL_OPS and op not in _UNIVERSAL_OPS:
                # C1: resolve active declarations (ALT-I-03: scoped_intent filter)
                if self._require_scoped_intent:
                    active_decls = [
                        d for d in self._will_store.active_declarations(
                            scope_ref=self._session_dkn)
                        if d.scope_ref != ""
                    ]
                else:
                    active_decls = self._will_store.active_declarations(
                        scope_ref=self._session_dkn
                    )
                # C2: check coverage
                if intent_ref:
                    # Caller-declared intent_ref: verify it resolves
                    resolved = self._will_store.get(intent_ref)
                    if resolved and resolved.covers_op(op):
                        _intent_ref = intent_ref
                    elif self._require_intent:
                        self._store.write(
                            op="gate_refuse", authority=self._authority,
                            parameters={"op": op, "reason": "WL-002 intent_ref unresolvable",
                                        "refusal_axis": "intent", "refusal_reason": "intent_required_missing"},
                            failed=True, intent="conform", jurisdiction="kernel",
                            session_dkn=self._session_dkn,
                            law_hash=self._law_hash, legend_hash=self._legend_hash,
                        )
                        raise GateRefusal(op=op, reason="intent_required_missing")
                elif self._require_intent:
                    # No intent_ref + require_intent=True: check coverage
                    from ugk.will import WillChecker
                    outcome = WillChecker().covers(op, active_decls)
                    if outcome.status == "COVERED":
                        _intent_ref = outcome.intent_ref or ""
                    else:
                        self._store.write(
                            op="gate_refuse", authority=self._authority,
                            parameters={"op": op, "reason": outcome.refusal_code,
                                        "refusal_axis": "intent", "refusal_reason": "intent_required_missing"},
                            failed=True, intent="conform", jurisdiction="kernel",
                            session_dkn=self._session_dkn,
                            law_hash=self._law_hash, legend_hash=self._legend_hash,
                        )
                        raise GateRefusal(op=op, reason="intent_required_missing")
                else:
                    # conservative_fallback: auto-resolve from active declarations
                    from ugk.will import WillChecker
                    outcome = WillChecker().covers(op, active_decls)
                    if outcome.status == "COVERED":
                        _intent_ref = outcome.intent_ref or ""
        # Step 5 — gate_admit receipt (reached ONLY after the full refusal horizon is exhausted:
        # preflight + gate + intent coverage all passed). Written directly to store.
        admit_params: dict = {"op": op, "parameters": parameters}
        if gate_margin is not None:
            admit_params["gate_margin"] = gate_margin
        # r102-a / AD-37: make the declared effect atomicity class visible in the admit. r139 (Lane 1):
        # the class is committed via the canonical typed column; the parameters marker is store-derived.
        _admit_effect_columns = ({"effect_atomicity": effect_atomicity.value}
                                 if (effect is not None and effect_atomicity is not None) else None)
        _admit_receipt = self._store.write(
            op="gate_admit",
            authority=authority,
            parameters=admit_params,
            failed=False,
            intent="gate_admit",
            jurisdiction="kernel",
            session_dkn=self._session_dkn,
            law_hash=self._law_hash,
            legend_hash=self._legend_hash,
            effect_columns=_admit_effect_columns,
        )
        # r102-b: capture the gate_admit h_r - the durable decision-before-effect reference the
        # structural abort receipt links to if a PURE/STORE_LOCAL outcome transition rolls back.
        _admit_ref = getattr(_admit_receipt, "h_r", "") or ""

        # Produce DecisionWarrant if caller declared warrant_basis
        _warrant_id = ""
        if warrant_basis is not None:
            try:
                from ugk.governance.warrant import DecisionWarrant
                warrant = DecisionWarrant.create(
                    constitutional_basis=sorted(warrant_basis),
                    law_hash=self._law_hash,
                    legend_hash=self._legend_hash,
                )
                if self._warrant_store is None:
                    if _am is not None and _am.require_warrant:
                        raise RuntimeError("no WarrantStore attached")
                else:
                    written_id = self._warrant_store.write(warrant)
                    stored = self._warrant_store.get(warrant.warrant_hash)
                    if written_id != warrant.warrant_hash or stored is None:
                        raise RuntimeError("warrant write not durably readable")
                    _warrant_id = warrant.warrant_hash
            except Exception as _werr:
                # CM-S-03 strengthening: under require_warrant=True, warrant
                # materialization is load-bearing. An op with warrant_basis
                # declared but no durable warrant is the crack auditors and
                # attackers both look for — refuse instead of swallow.
                if _am is not None and _am.require_warrant:
                    raise KernelInternalOp(
                        f"warrant materialization failed under require_warrant=True "
                        f"for op={op!r} [{_am.model_id}]: {type(_werr).__name__}: {_werr}"
                    )
                # Permissive postures (trace_only): swallow as before so an
                # auxiliary warrant-production failure doesn't block the op.
                _warrant_id = ""

        # A1 bridge: authority_set in parameters when supplied
        _params=dict(parameters or {})
        if authority_set: _params["authority_set"]=list(authority_set)
        _op_csil=self._op_csil_registry.get(op,0)
        if _op_csil: _params["op_csil"]=_op_csil
        # r140 (Lane 2): the declared effect-atomicity CLASS is carried via the canonical typed column,
        # not a parameters marker. The store derives the marker mirror from this descriptor at write
        # (byte-identical to the legacy _params["effect_atomicity"] marker). The EXTERNAL_* helpers below
        # build their own descriptor, so _params no longer needs to carry the class tag for them.
        _effect_columns = ({"effect_atomicity": effect_atomicity.value}
                           if (effect is not None and effect_atomicity is not None) else None)
        # r115 / AD-44 — EXTERNAL_IRREVERSIBLE two-phase trail. Deliberately NOT inside
        # store.transaction(): wrapping an unrollback-able external act in a rollback scope would be
        # misleading. PREPARE (depth 0, BEFORE effect; NBER-1) -> effect() -> COMMIT (confirmed
        # performed) | ABORT (confirmed NOT performed) | no-terminal+re-raise (in-doubt -> orphan
        # PREPARE). gate_admit above is the generic admission; PREPARE is the EXTERNAL_IRREVERSIBLE
        # intent-to-act anchor that outcomes link back to via prepare_ref.
        # r132 / AD-55 — EXTERNAL_REVERSIBLE (compensation/saga) FORWARD-effect trail. The forward
        # effect mirrors the EXTERNAL_IRREVERSIBLE two-phase trail (PREPARE -> effect -> COMMIT |
        # ABORT | orphan), also NOT inside store.transaction() (an external effect is not store-
        # rollback-able). The DIFFERENCE is downstream and OUT OF BAND: a committed forward effect MAY
        # later be OFFSET by compensate_external_reversible -- a SEPARATE governed call with its own
        # COMPENSATE intent receipt (receipt-before-effect all the way down) and its own DISTINCT
        # compensation idempotency scope. Compensation is NEVER a hidden side effect of COMMIT.
        if effect is not None and effect_atomicity == EffectAtomicity.EXTERNAL_REVERSIBLE:
            return self._execute_external_reversible(
                op, authority, _params, effect, idempotency_key,
                jurisdiction, _intent_ref, _admit_ref, _warrant_id)
        if effect is not None and effect_atomicity == EffectAtomicity.EXTERNAL_IRREVERSIBLE:
            return self._execute_external_irreversible(
                op, authority, _params, effect, idempotency_key,
                jurisdiction, _intent_ref, _admit_ref, _warrant_id)
        # r102-b / AD-38 — rollback-able effect classes (PURE / STORE_LOCAL) get the ATOMIC OUTCOME
        # transition: [effect + success receipt] run inside the AD-34/36 seam so they commit-or-roll-
        # back together, and the success receipt is written AFTER effect() returns (no success-before-
        # effect). gate_admit above is the durable decision-before-effect receipt (committed at depth
        # 0); a failed effect leaves gate_admit + a durable STRUCTURAL ABORT, never a false success.
        # NON_ATOMIC and no-effect ops keep the legacy order; external classes already failed closed in
        # the preflight. (confess-and-audit: STORE_LOCAL asserts its durable mutations are store-local
        # and flow only through audited store surfaces; the seam guarantees rollback only for those.)
        if effect is not None and effect_atomicity in (EffectAtomicity.PURE, EffectAtomicity.STORE_LOCAL):
            from ugk.integrity import TransactionCommitError
            _result = None
            _phase = "effect"   # distinguishes effect_failure from success_receipt_failure
            try:
                with self._store.transaction(name="effect:%s" % op):
                    _result = effect()        # depth>0; STORE_LOCAL store writes defer to the RELEASE
                    _phase = "success_receipt"
                    self._store.write(
                        op=op,
                        authority=authority,
                        parameters=_params,
                        failed=False,
                        intent=op,
                        jurisdiction=jurisdiction,
                        session_dkn=self._session_dkn,
                        law_hash=self._law_hash,
                        legend_hash=self._legend_hash,
                        warrant_id=_warrant_id,
                        intent_ref=_intent_ref,
                        effect_columns=_effect_columns,
                    )
                # clean RELEASE committed [effect store writes + success receipt] together
                return _result
            except TransactionCommitError:
                # clean-path RELEASE (commit) failure: the seam restored the frontier and persisted
                # nothing; record a durable structural ABORT (commit_release_failure) and fail closed.
                self._emit_effect_abort(op, authority, parameters, effect_atomicity,
                                        "commit_release_failure", jurisdiction, _intent_ref, _admit_ref)
                raise
            except BaseException:
                # effect() or the success-receipt write raised -> the seam rolled the whole outcome
                # transition back: the effect's store writes AND the would-be success receipt persisted
                # nothing (frontier restored). Record a durable structural ABORT, classified by phase.
                _reason = "effect_failure" if _phase == "effect" else "success_receipt_failure"
                self._emit_effect_abort(op, authority, parameters, effect_atomicity,
                                        _reason, jurisdiction, _intent_ref, _admit_ref)
                raise

        # Legacy order — NON_ATOMIC and no-effect ops: success receipt at depth 0, then effect.
        self._store.write(
            op=op,
            authority=authority,
            parameters=_params,
            failed=False,
            intent=op,
            jurisdiction=jurisdiction,
            session_dkn=self._session_dkn,
            law_hash=self._law_hash,
            legend_hash=self._legend_hash,
            warrant_id=_warrant_id,
            intent_ref=_intent_ref,
            effect_columns=_effect_columns,
        )

        # Steps 7 + 8 — effect + failure receipt (legacy NON_ATOMIC path)
        if effect is not None:
            try:
                return effect()
            except Exception:
                self._store.write(
                    op=op,
                    authority=authority,
                    parameters=parameters,
                    failed=True,
                    intent=op,
                    jurisdiction=jurisdiction,
                    session_dkn=self._session_dkn,
                    law_hash=self._law_hash,
                )
                raise

        return None

    # ------------------------------------------------------------------
    # Snapshot tier 1: O(1), never verify_stream_hash (UL-S-05)
    # ------------------------------------------------------------------

    # ---- DEFER-S-01 continuation lifecycle (r149) ------------------------------------------------
    def defer_operation(self, op, authority=None, parameters=None, *, jurisdiction="session",
                        expiry_basis=None, anchor=None):
        """DEFER-S-01 EMIT: record a DEFER terminal with a HELD continuation record capturing the
        operation's re-entry data for a later resume. DEFER is emittable ONLY with a valid HELD
        continuation (TO-S-01); the store fails closed otherwise. Returns the deterministic continuation_id."""
        from ugk.storage.store import compute_continuation_id
        authority = authority or self._authority
        parameters = dict(parameters or {})
        anchor = anchor if anchor is not None else self._store.stream_hash()
        cid = compute_continuation_id(op=op, authority=authority, parameters=parameters,
                                      jurisdiction=jurisdiction, anchor=anchor)
        if expiry_basis is None:
            # default: a far committed-height horizon (deterministic; never wall-clock)
            expiry_basis = {"kind": "receipt_height", "value": self._store.committed_height() + 1_000_000}
        cont = dict(id=cid, op=op, authority=authority, parameters=parameters, jurisdiction=jurisdiction,
                    anchor=anchor, expiry_basis=expiry_basis, state="HELD",
                    model_id="continuation_record_model_v1")
        self._store.write(op=op, authority=authority, parameters=parameters, jurisdiction=jurisdiction,
                          session_dkn=self._session_dkn, law_hash=self._law_hash,
                          legend_hash=self._legend_hash, commit_terminal_outcome=True,
                          terminal_outcome_override="DEFER", continuation=cont)
        return cid

    def emit_bridge(self, op, authority=None, parameters=None, *, bridge, bridge_verifier,
                    jurisdiction="session", failed=False, intent=""):
        """CK-BRIDGE Stage 4 native BRIDGE emission — EXPLICIT OPT-IN ONLY.

        Emits a BRIDGE terminal receipt for an audited regime crossing (permit-with-audit). The caller
        MUST supply the committed v8 `bridge` surface AND a read-only `bridge_verifier` (the Stage-3
        verify_bridge_binding bound with the caller's injected MCIR/SMH read-only resolvers — UGK imports
        neither). The store fails CLOSED: BRIDGE is emittable ONLY when the surface verifies under
        BRIDGE-BINDING at emit (TO-S-01 / BRIDGE-BINDING); a missing/malformed/refuting surface raises
        ReservedOutcomeError (refuse/error, NEVER admit). The kernel NEVER reaches this path on its own —
        there is no policy that auto-bridges; bridging requires this explicit call. Receipt-before-effect
        is preserved: the BRIDGE receipt is written here, before any downstream crossing effect. Returns
        the Receipt.
        """
        authority = authority or self._authority
        parameters = dict(parameters or {})
        return self._store.write(op=op, authority=authority, parameters=parameters,
                                 jurisdiction=jurisdiction, failed=bool(failed), intent=intent,
                                 session_dkn=self._session_dkn, law_hash=self._law_hash,
                                 legend_hash=self._legend_hash, commit_terminal_outcome=True,
                                 terminal_outcome_override="BRIDGE", bridge=bridge,
                                 bridge_verifier=bridge_verifier)

    def _continuation_marker(self, continuation_id, src, state, *, refuse, reason):
        """Append-only DEFER-S-01 transition receipt: shares continuation_id, NEVER mutates `src`.
        refuse=True records a clean constitutional REFUSE (expire/refuse); refuse=False records the
        resolved bookkeeping marker."""
        import json as _json
        cont = dict(id=continuation_id, op=src.continuation_op, authority=src.continuation_authority,
                    parameters=_json.loads(src.continuation_parameters) if src.continuation_parameters else {},
                    jurisdiction=src.continuation_jurisdiction,
                    expiry_basis=_json.loads(src.continuation_expiry_basis) if src.continuation_expiry_basis else None,
                    state=state, model_id="continuation_record_model_v1")  # no anchor -> carried id linkage
        marker_op = "gate_refuse" if refuse else "continuation_resolved"
        self._store.write(op=marker_op, authority=src.continuation_authority or self._authority,
                          parameters={"continuation_id": continuation_id, "reason": reason},
                          failed=False, intent=reason, jurisdiction=src.continuation_jurisdiction or "session",
                          session_dkn=self._session_dkn, law_hash=self._law_hash,
                          legend_hash=self._legend_hash, commit_terminal_outcome=True, continuation=cont)

    def resume_continuation(self, continuation_id, *, gate=None, effect=None, effect_atomicity=None):
        """DEFER-S-01 RESUME: re-enter the FULL W/G/E execute() path on the captured operation with NO
        bypass of admission. Refuses cleanly (recording an EXPIRED / REFUSED transition) if the
        continuation is missing, already terminal, or expired. Expiry is deterministic from committed
        evidence (committed_height), never wall-clock. The resumed operation's ordinary terminal
        (ADMIT / REFUSE / STRUCTURAL_ERROR) IS the resolve."""
        import json as _json
        from ugk.storage.store import continuation_expired
        rec = self._store.find_continuation(continuation_id)
        if rec is None or rec.continuation_state != "HELD":
            # missing / already-terminal -> clean governed refusal (no resume, no bypass)
            if rec is not None:
                self._continuation_marker(continuation_id, rec, "REFUSED", refuse=True,
                                          reason="continuation-not-resumable")
            raise GateRefusal(op="resume_continuation", reason="continuation-not-resumable")
        if continuation_expired(rec.continuation_expiry_basis, self._store.committed_height()):
            self._continuation_marker(continuation_id, rec, "EXPIRED", refuse=True,
                                      reason="continuation-expired")
            raise GateRefusal(op="resume_continuation", reason="continuation-expired")
        params = _json.loads(rec.continuation_parameters) if rec.continuation_parameters else {}
        # RE-ENTER GOVERNANCE: the captured op runs the full gate/aggregation/admit path. No bypass.
        result = self.execute(op=rec.continuation_op, authority=rec.continuation_authority,
                              parameters=params, gate=gate, effect=effect,
                              effect_atomicity=effect_atomicity,
                              jurisdiction=rec.continuation_jurisdiction, intent_ref=continuation_id)
        # record the RESOLVED transition (append-only; the execute() receipt above carries the ordinary
        # terminal outcome which IS the resolution).
        self._continuation_marker(continuation_id, rec, "RESOLVED", refuse=False, reason="continuation-resolved")
        return result

    def snapshot_fast(self) -> dict:
        """O(1) snapshot for continuous monitoring.

        NEVER calls verify_stream_hash().  hash_verified = None.
        Fields: session_id, receipt_count, refusal_count, admitted,
                stream_hash, hash_verified, refusal_rate_by_op,
                session_delta, refused_by_layer, classified_remainders.
        """
        receipt_count = self._store.receipt_count()
        refusal_count = self._store.refusal_count()
        admitted      = len(self._store.receipts_by_op("gate_admit"))
        sh            = self._store.stream_hash()
        session_delta = receipt_count - self._session_open_count

        return {
            "session_id":        (self._session_identity.session_id
                                  if self._session_identity else None),
            "session_dkn":       self._session_dkn,
            "governance_status": self._status,
            "law_hash":          self._law_hash,
            # Frame triad — structure leg (B-schema_hash): observe-only frame binding.
            "schema_hash":         self._store.schema_hash(),
            "schema_frame_intact": self._store.schema_frame_intact(),
            "receipt_count":     receipt_count,
            "refusal_count":     refusal_count,
            "admitted":          admitted,
            "stream_hash":       sh,
            "hash_verified":          None,          # UL-S-05: never verify in fast path
            "refusal_rate_by_op":     self._store.refusal_rate_by_op(),
            "session_delta":          session_delta,
            "refused_by_layer":       dict(self._refused_by_layer),
            "classified_remainders":  list(CLASSIFIED_REMAINDERS),
            # Phase 2: live cryptographic identity
            "mosaic_root":            self._mosaic_root,
            "dimension_id":           self._dimension_id,
            "require_governor_sig":   self._require_governor_sig,
            "crypto_profile":         "reference_non_constant_time",
            # Phase 6: legend vocabulary
            "legend_hash":            self._legend_hash,
            # Phase 3: CSH finality
            "csh_finality_hash":      self._csh_finality_hash,
            "csh_quorum_achieved":    self._csh_quorum_achieved,
            "launch_ic_hash":         (
                self._launch_ic.ic_hash() if self._launch_ic else ""
            ),
        }

    # ------------------------------------------------------------------
    # Snapshot tier 2: O(n), cryptographic ground truth (UL-S-05)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """O(n) snapshot for session boundaries / integrity assertions.

        CALLS verify_stream_hash() — may block on large stores.
        hash_verified: True|False (never None — distinguishes from snapshot_fast).
        Additional fields vs snapshot_fast: observation_surfaces, epistemic_version.
        """
        fast = self.snapshot_fast()
        hash_verified = self._store.verify_stream_hash()
        return {
            **fast,
            "hash_verified":      hash_verified,
            "observation_surfaces": ["Cap-1", "Cap-2", "Cap-4"],
            "epistemic_version":  "ESA-1.0",
        }

    # ------------------------------------------------------------------
    # Store access (for HeadlessRunner and test infrastructure)
    # ------------------------------------------------------------------

    @property
    def store(self) -> UGKReceiptStore:
        """Direct store access for HeadlessRunner evidence capture."""
        return self._store
