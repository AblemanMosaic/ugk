"""ugk.scale.scheduler — opt-in governed scale lane + I5 self-governance (DORMANT subsystem).

Scope: microservice profile only. Purpose is NOT speed; it answers:
  1. Can I5 be made reconstructable? (every scheduler op receipted; "why ordered/delayed/
     prioritized/refused/paused/resumed/backpressured" answerable from receipts alone)
  2. Can the scheduler remain downstream of the oracle? (never reorders dependent candidates)
  3. Can priority operate without laundering authority? (orders only WITHIN independent sets)
  4. Can the microservice green zone be scheduled while non-target profiles safely serialize?
  5. Are one-receipt-per-operation (I2) and no-position-without-the-lane (I7) preserved?

No execute() wiring, no substrate mutation, r8 canonical. Disposable.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import itertools
from ugk.scale.oracle import (
    Chain, Candidate, independent, INDEPENDENT, DEPENDENT, OracleRefusal, CommitLane,
)

# ---- I5 receipt log: scheduler operations are themselves governed/receipted -------------
SCALE_OPS = {
    "scheduler_policy_set", "independence_set_computed", "priority_class_assigned",
    "backpressure_engaged", "backpressure_released", "queue_overflow_refused",
    "batch_envelope_created", "worker_pool_scaled", "lane_paused", "lane_resumed",
}

@dataclass
class I5Receipt:
    seq: int
    op: str
    detail: dict
    prior_hash: str
    def rhash(self) -> str:
        import hashlib
        return hashlib.sha256(f"{self.seq}|{self.prior_hash}|{self.op}|{sorted(self.detail.items())}".encode()).hexdigest()

class I5Log:
    """Append-only log of scheduler control operations. The scheduler's decisions live HERE,
    not behind the chain. Reconstruction = answer 'why' from this log alone."""
    GENESIS = "0"*64
    def __init__(self):
        self._log: list[I5Receipt] = []
    def emit(self, op: str, **detail) -> I5Receipt:
        assert op in SCALE_OPS, f"undeclared scale op: {op}"
        prior = self._log[-1].rhash() if self._log else self.GENESIS
        r = I5Receipt(len(self._log), op, detail, prior)
        self._log.append(r)
        return r
    def all(self): return list(self._log)
    def why(self, candidate_id) -> list:
        """Reconstruct the decision trail for a candidate from receipts alone."""
        return [(r.op, r.detail) for r in self._log if r.detail.get("cand") == candidate_id]

# ---- priority classes (order only WITHIN an independent set; never across dep edges) ----
PRIORITY = {  # lower = higher priority
    "gate_refuse": 0, "invariant_violation": 0, "replay_detect": 0,        # P0 safety
    "authority_model_set": 1, "a1_posture_set": 1, "session_open": 1,      # P1 governance
    "app_write": 2,                                                         # P2 ordinary
    "bulk": 3,                                                              # P3 bulk
}
def prio(c: Candidate) -> int:
    return PRIORITY.get(c.op, 2)

# ---- the scheduler: downstream of the oracle, fully receipted ---------------------------
class GovernedScheduler:
    def __init__(self, chain: Chain, capacity: int = 1000):
        self.chain = chain
        self.lane = CommitLane(chain)
        self.i5 = I5Log()
        self.capacity = capacity
        self.i5.emit("scheduler_policy_set",
                     policy="independence-set + priority-within-set + aging",
                     capacity=capacity, profile="microservice-only")

    def independence_set(self, cands: list[Candidate], cand_ids: list) -> list[int]:
        """Return indices that are MUTUALLY independent (oracle-proven). Conservative: a
        candidate joins the set only if independent of EVERY already-admitted member."""
        members: list[int] = []
        for i, c in enumerate(cands):
            ok = True
            for m in members:
                try:
                    if independent(c, cands[m], self.chain) != INDEPENDENT:
                        ok = False; break
                except OracleRefusal:
                    ok = False; break
            if ok:
                members.append(i)
        # I5: record WHICH set was ruled independent and the evidence basis
        self.i5.emit("independence_set_computed",
                     members=[cand_ids[i] for i in members],
                     basis="positive input_refs + grant warrant + disjoint binding + cross-agent")
        return members

    def _safe_priority_order(self, cands: list[Candidate], indep_idx: set) -> list[int]:
        """Return a commit order that applies priority ONLY across mutually-independent
        candidates and NEVER reorders a dependency.

        Method: start from submission order (the floor) and perform stable adjacent swaps,
        promoting a higher-priority candidate ahead of an adjacent lower-priority one ONLY
        when the two are oracle-independent. A swap is permitted iff independent(a,b)==
        INDEPENDENT; a dependent pair is never swapped, so no candidate can overtake one it
        depends on. This is a dependency-respecting (topological-stable) priority sort:
        priority orders within independent sets, submission order holds across dependency edges.
        """
        order = list(range(len(cands)))
        n = len(order)
        # bubble passes: only swap adjacent (i, i+1) when later has strictly higher priority
        # (lower number) AND the pair is independent. Dependent adjacent pairs are immovable.
        changed = True
        passes = 0
        while changed and passes < n:
            changed = False
            passes += 1
            for k in range(n - 1):
                a, b = order[k], order[k + 1]
                if prio(cands[b]) < prio(cands[a]):  # b wants to move ahead of a
                    try:
                        indep = independent(cands[a], cands[b], self.chain) == INDEPENDENT
                    except OracleRefusal:
                        indep = False
                    if indep:  # safe: a and b are independent ⇒ priority may reorder them
                        order[k], order[k + 1] = order[k + 1], order[k]
                        changed = True
                    # else: dependent ⇒ DO NOT swap (submission order is the floor)
        return order

    def schedule(self, cands: list[Candidate], cand_ids: list, admit_fn, effect_fn):
        """Schedule a batch: compute independent set, order by priority WITHIN the set,
        commit each as ONE receipt via the single lane (serial head). Everything receipted."""
        # capacity / backpressure (fail-closed, receipted — never silent)
        if len(cands) > self.capacity:
            self.i5.emit("backpressure_engaged", pending=len(cands), capacity=self.capacity)
            refused = cand_ids[self.capacity:]
            for rid in refused:
                self.i5.emit("queue_overflow_refused", cand=rid, reason="capacity-exceeded")
            cands, cand_ids = cands[:self.capacity], cand_ids[:self.capacity]
            self.i5.emit("backpressure_released", admitted=len(cands))

        indep_idx = set(self.independence_set(cands, cand_ids))
        # Priority orders ONLY within the oracle-proven independent set; dependent candidates
        # preserve submission order. A candidate may move EARLIER only if it is independent of
        # EVERY candidate it would jump ahead of — otherwise priority could reorder a
        # dependency (a high-priority dependent op overtaking what it depends on). Submission
        # order is the floor; priority is a tie-break that may never cross a dependency edge.
        order = self._safe_priority_order(cands, indep_idx)
        committed = []
        for i in order:
            cid = cand_ids[i]
            in_set = i in indep_idx
            self.i5.emit("priority_class_assigned", cand=cid, prio=prio(cands[i]),
                         in_independent_set=in_set,
                         note="ordered within independent set" if in_set else "serialized (dependent)")
            # commit via the single lane: ONE receipt per op (I2), receipt-before-effect (I3),
            # re-validated at lane (I7 re-entry). Dependent candidates still commit — they just
            # were NOT reordered; they keep submission order relative to their dependencies.
            try:
                r, _ = self.lane.commit_and_effect(cands[i], admit_fn, effect_fn,
                                                   actual_binding=cands[i].binding_key)
                committed.append((cid, r.rhash))
            except OracleRefusal as e:
                self.i5.emit("queue_overflow_refused", cand=cid, reason=f"lane-refused:{e.code}")
        return committed

    def reconstruct_why(self, cand_id) -> list:
        """Q1: can I5 answer 'why' for a candidate from receipts alone?"""
        return self.i5.why(cand_id)
