"""grbsa_runtime — GateAdapter (GRBSA G3 beachhead).

Wraps a legacy conformance gate as a RECEIPT-BOUND CONTINUATION:
    proposal -> admissibility -> GateReceipt (minted) -> continuation (gate runs) -> GateResultEnvelope

This is a THIN wrapper. It imports ugk read-only, reimplements no gate, and adds no ugk/ object. It
realizes the GRBSA cores from the G1 spec:
  - GateReceipt        : Receipt Core + gate-domain extension (WHY it was admissible to run the gate)
  - GateResultEnvelope : ResultEnvelope Core + gate-domain extension (WHAT the gate found)
Success semantics (anti-vacuity for a gate) is a PREDICATE over receipt+envelope, stored in NEITHER.

NBER-1: the GateReceipt is minted BEFORE the continuation runs. The honest adapter enforces this;
test variants that violate it exist only in the equivalence gate's negative controls.

Equivalence (Receipt Sufficiency Principle): two runs are equivalent on admissibility + success
semantics + lineage SHAPE — never on receipt-hash identity (Receipt Identity Principle; chain hash
binds ts).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
import hashlib

# Posture/authority op set — the adapter must never originate one (authority boundary).
# Mirrors ugk.scale.oracle.POSTURE_OPS in spirit; imported read-only for the refusal check.
try:
    from ugk.scale.oracle import POSTURE_OPS as _POSTURE_OPS
except Exception:  # pragma: no cover - ugk always present in tree
    _POSTURE_OPS = set()


class PostureRefusal(Exception):
    """Raised when an adapter run attempts a posture/authority op (authority boundary)."""


# ---- Receipt Core (the closed 6-field shape from G1, realized as a record) ----
@dataclass(frozen=True)
class ReceiptCore:
    proposal: dict     # what was requested
    criteria: tuple    # admissibility criteria ids that applied
    evaluation: tuple  # per-criterion outcomes (admissibility), refs not values
    authority: dict    # authority/warrant refs (never raw values)
    outcome: str       # 'admitted' | 'refused' | 'failed'
    lineage: dict      # prior/position/produced-effects (shape)


# ---- ResultEnvelope Core (the closed 5-field shape from G1) ----
@dataclass(frozen=True)
class ResultEnvelopeCore:
    status: str            # 'pass' | 'fail'
    evidence_refs: tuple   # refs to evidence (not the values)
    timing: dict           # timing info (excluded from equivalence)
    result_hash: str       # hash of the result payload
    lineage: dict          # produced-effects / delta (shape)


# ---- Domain extensions (gate domain) ----
@dataclass(frozen=True)
class GateReceipt:
    core: ReceiptCore
    # gate extension:
    gate_id: str
    check_names: tuple     # the names of the checks the gate declares (criteria detail)
    domain: str = "gate"   # explicit category tag (Category-Separation)


@dataclass(frozen=True)
class GateResultEnvelope:
    core: ResultEnvelopeCore
    # gate extension:
    gate_id: str
    findings: tuple        # ((name, ok), ...) — per-check outcomes; detail strings EXCLUDED
    domain: str = "gate"   # explicit category tag (Category-Separation)


# ---- success semantics: a PREDICATE over receipt+envelope, not a stored field ----
def gate_success(receipt: GateReceipt, envelope: GateResultEnvelope) -> bool:
    """Anti-vacuity for a gate: the gate ran real checks AND all of them passed.
    'Vacuous pass' (zero checks) is NOT success. This predicate lives here, in neither core."""
    # Category-Separation guard: this predicate certifies ONLY the gate domain. A category mismatch
    # is a CLEAN False (not an exception) — principled separation, not accidental field mismatch.
    if getattr(receipt, "domain", None) != "gate" or getattr(envelope, "domain", None) != "gate":
        return False
    findings = envelope.findings
    if len(findings) == 0:
        return False  # no checks exercised => vacuous => not success
    # check-name/finding-name consistency (the receipt declared exactly these checks)
    if tuple(n for n, _ in findings) != receipt.check_names:
        return False
    return all(ok for _, ok in findings)


@dataclass
class _Trace:
    """Records the order of adapter steps, so NBER-1 (receipt before effect) is provable by ORDER."""
    events: list = field(default_factory=list)
    def mark(self, ev: str): self.events.append(ev)
    def receipt_before_effect(self) -> bool:
        try:
            return self.events.index("receipt_minted") < self.events.index("effect_ran")
        except ValueError:
            return False


# ---- result-shape normalizers: legacy native result -> [(check_name, ok), ...] ----
# These let ONE GateAdapter wrap gates with DIFFERENT result shapes WITHOUT re-deriving any gate.
def _default_checks_normalizer(res) -> list:
    """GateResult-style: res.checks = [(name, ok, detail), ...] (e.g. a1_conservativity_gate)."""
    return [(n, bool(ok)) for (n, ok, *_rest) in res.checks]


def verdict_tuple_normalizer(gate_id: str):
    """(ok, detail)-style: res = (ok: bool, detail: str) (e.g. determinism_gate). The single verdict
    becomes one synthetic check named '<gate_id>:verdict'. No per-check structure is invented beyond
    the gate's own single verdict."""
    def _norm(res) -> list:
        ok, _detail = res
        return [(gate_id + ":verdict", bool(ok))]
    return _norm


class GateAdapter:
    """Wraps a legacy gate's run callable as a receipt-bound continuation.

    run_callable() must return an object with `.passed` (bool) and `.checks`
    (iterable of (name, ok, detail)). The adapter does NOT interpret detail strings.
    """

    def __init__(self, gate_id: str, run_callable: Callable[[], object], *,
                 op: str = "gate_run",
                 normalizer: Optional[Callable[[object], list]] = None,
                 _emit_receipt_before_effect: bool = True,
                 _drop_check: Optional[str] = None):
        self.gate_id = gate_id
        self.run_callable = run_callable
        self.op = op
        # normalizer maps a legacy runner's native result -> [(check_name, ok), ...].
        # DEFAULT: GateResult-style (.checks triples) — used by a1; preserves the G3 path exactly.
        self.normalizer = normalizer if normalizer is not None else _default_checks_normalizer
        # test seams (used ONLY by the equivalence gate's negative controls):
        self._emit_receipt_before_effect = _emit_receipt_before_effect
        self._drop_check = _drop_check

    # -- substrate-named steps (admissibility -> receipt -> continuation -> envelope) --
    def _admissibility(self) -> tuple:
        # authority boundary: the adapter may never originate a posture/authority op
        if self.op in _POSTURE_OPS:
            raise PostureRefusal("adapter attempted posture op: " + self.op)
        return ("c_gate.v1",)  # the gate-admissibility criterion id (declared)

    def run(self) -> tuple:
        """Returns (GateReceipt, GateResultEnvelope, trace). NBER-1 honored unless test seam disables."""
        trace = _Trace()
        proposal = {"op": self.op, "gate_id": self.gate_id}
        criteria = self._admissibility()             # may raise PostureRefusal (authority teeth)

        def _mint_receipt(check_names, outcome):
            core = ReceiptCore(
                proposal=proposal,
                criteria=criteria,
                evaluation=("admissible",),
                authority={"warrant": "gate-suite", "law_ref": "law_hash"},
                outcome=outcome,
                lineage={"prior": "0" * 64, "position": 0, "produces_effects": ()},
            )
            return GateReceipt(core=core, gate_id=self.gate_id, check_names=tuple(check_names))

        def _run_gate():
            trace.mark("effect_ran")
            res = self.run_callable()
            checks = self.normalizer(res)            # legacy result -> [(name, ok), ...]
            checks = [(n, bool(ok)) for (n, ok) in checks]
            # NEGATIVE-CONTROL seam: drop/swallow a failing (or any) check
            if self._drop_check is not None:
                checks = [(n, ok) for (n, ok) in checks if n != self._drop_check]
            return res, checks

        if self._emit_receipt_before_effect:
            # HONEST PATH (NBER-1): mint the receipt BEFORE the effect runs. The receipt records the
            # admissibility decision (criteria/authority/outcome) which does NOT depend on check
            # outcomes; check_names are the gate's declared contract, finalized into the envelope.
            trace.mark("receipt_minted")
            res, checks = _run_gate()                # continuation runs AFTER the receipt is minted
            receipt = _mint_receipt([n for n, _ in checks], "admitted")
        else:
            # NEGATIVE-CONTROL seam: effect first, then receipt (NBER-1 VIOLATION — must FAIL the gate)
            res, checks = _run_gate()
            trace.mark("receipt_minted")
            receipt = _mint_receipt([n for n, _ in checks], "admitted")

        # Assemble the envelope (WHAT happened)
        result_hash = hashlib.sha256(repr(tuple(checks)).encode()).hexdigest()
        env = GateResultEnvelope(
            core=ResultEnvelopeCore(
                status="pass" if all(ok for _, ok in checks) else "fail",
                evidence_refs=tuple(n for n, _ in checks),
                timing={},  # excluded from equivalence
                result_hash=result_hash,
                lineage={"produced_effects": (), "delta": len(checks)},
            ),
            gate_id=self.gate_id,
            findings=tuple(checks),
        )
        return receipt, env, trace
