"""ugk.scale.oracle — earned-independence dependency oracle (DORMANT subsystem).

Purpose (per authorization): adversarial instrument to measure SAFETY (oracle never calls
a dependent pair independent; I7/C2 no auto-promote; C3/NBER-1 not weakened) and GREEN-ZONE
WIDTH (how often genuinely-independent disjoint candidates are reorderable). NOT performance.

Integrated as INERT infrastructure: ugk/__init__.py does NOT import this module on the
default path. It is reachable only via explicit opt-in (ugk.scale.is_enabled()). It does
not touch execute(), the commit lane, or default behavior. Logic is byte-identical to the
AL-clean v1 prototype that cleared the threat model.

Governing rule encoded everywhere: declarations narrow dependence ONLY when chain-verifiable;
absent/unverifiable ⇒ UNKNOWN ⇒ DEPENDENT. There is no `independent=True` knob.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import hashlib

# ---- minimal chain model (committed receipts) -------------------------------
@dataclass(frozen=True)
class Receipt:
    pos: int
    rhash: str
    prior_hash: str
    op: str
    agent: str
    session: Optional[str]
    binding_keys: tuple          # ((effect_id, authority), ...)
    produces_effects: tuple      # effect_ids this receipt creates
    grant_class: bool            # does it establish an authority/posture/session grant?
    failed: bool = False

class Chain:
    """Append-only committed chain. The ONLY minter of canonical position (models the lane)."""
    GENESIS = "0" * 64
    def __init__(self):
        self._r: list[Receipt] = []
        self._by_hash: dict[str, Receipt] = {}
        self._effects: dict[str, int] = {}   # effect_id -> committing pos
    def tip(self) -> str:
        return self._r[-1].rhash if self._r else self.GENESIS
    def has_hash(self, h: str) -> bool:
        return h in self._by_hash
    def has_effect(self, eid: str) -> bool:
        return eid in self._effects
    def receipt(self, h: str) -> Optional[Receipt]:
        return self._by_hash.get(h)
    def all(self) -> list[Receipt]:
        return list(self._r)
    def append(self, cand: "Candidate", actual_binding_keys=None, failed=False) -> Receipt:
        """Mint canonical position. Binds prior_hash. Records ACTUAL binding (not declared)."""
        pos = len(self._r)
        prior = self.tip()
        akeys = tuple(actual_binding_keys if actual_binding_keys is not None else cand.binding_key)
        body = f"{pos}|{prior}|{cand.op}|{cand.agent}|{cand.session}|{akeys}"
        rhash = hashlib.sha256(body.encode()).hexdigest()
        r = Receipt(pos, rhash, prior, cand.op, cand.agent, cand.session,
                    akeys, tuple(cand.produces_effects), cand.grant_class, failed)
        self._r.append(r); self._by_hash[rhash] = r
        for eid in cand.produces_effects:
            self._effects[eid] = pos
        return r

# ---- candidate (proposal, NO canonical position) ----------------------------
SAFETY_OPS = {"gate_refuse", "invariant_violation", "replay_detect", "rollback", "corruption_alert"}
POSTURE_OPS = {"authority_model_set", "a1_posture_set", "rho_posture_set", "constitution_set"}

@dataclass
class Candidate:
    op: str
    agent: str
    session: Optional[str] = None
    # schema fields (all optional; absence ⇒ dependent):
    input_refs: Optional[tuple] = None          # D1: receipt hashes / effect ids consumed
    warrant_basis_refs: Optional[tuple] = None  # D2: receipt hashes (NOT values) justifying
    binding_key: tuple = ()                     # D3: declared (effect_id, authority) touched
    refusal_subject: Optional[object] = None    # D4: hash/effect/key or "ALL_PENDING"
    posture_affecting: Optional[bool] = None    # D5: must be true for POSTURE_OPS
    session_marker: Optional[str] = None        # D6: 'open'|'member'|'close'
    member_range: Optional[tuple] = None        # D7: aggregate members
    produces_effects: tuple = ()
    grant_class: bool = False
    is_aggregate: bool = False

# ---- the dependency oracle --------------------------------------------------
DEPENDENT, INDEPENDENT = "DEPENDENT", "INDEPENDENT"

class OracleRefusal(Exception):
    def __init__(self, code): super().__init__(code); self.code = code

def _posture_check(c: Candidate):
    """D5: posture-class op MUST declare posture_affecting=True; mismatch ⇒ refuse."""
    in_class = c.op in POSTURE_OPS
    if in_class and c.posture_affecting is not True:
        raise OracleRefusal("D5-POSTURE-UNDERDECLARED")
    return in_class or (c.posture_affecting is True)

def _refusal_subject_verifiable(c: Candidate, chain: Chain) -> bool:
    """D4 (v1): a narrowed refusal_subject is honored ONLY if positively chain-verifiable as
    the refusal's actual subject (resolves to a committed receipt, effect, or live binding).
    A narrowed-but-unverifiable subject is NOT evidence ⇒ caller must fall back to ALL_PENDING."""
    subj = c.refusal_subject
    if subj is None or subj == "ALL_PENDING":
        return False  # not a narrowing; it IS the global barrier
    # positive verification: the named subject must exist in the chain
    return chain.has_hash(subj) or chain.has_effect(subj)

def _is_barrier(c: Candidate, chain: Chain) -> bool:
    """Global ordering barriers: posture-affecting, or a safety op whose subject is not a
    positively-verifiable narrowing (absent, ALL_PENDING, or narrowed-but-unverifiable)."""
    if _posture_check(c):
        return True
    if c.op in SAFETY_OPS and not _refusal_subject_verifiable(c, chain):
        return True  # v1: unverifiable narrowing ⇒ global barrier (no negative narrowing)
    return False

def _verified_input_refs(c: Candidate, chain: Chain) -> Optional[set]:
    """D1 (v1 positive-declaration-only): return the verified consumed-ref set, or None if
    absent/EMPTY/unverifiable (⇒ depends on all). 'Empty' and 'negative' are not evidence:
    input_refs=() is 'inputs not positively declared', NOT 'depends on nothing'."""
    if c.input_refs is None:
        return None  # absent ⇒ depends on all
    if len(c.input_refs) == 0:
        return None  # v1: EMPTY ⇒ treated as absent ⇒ depends on all (no negative narrowing)
    verified = set()
    for ref in c.input_refs:
        if chain.has_hash(ref) or chain.has_effect(ref):
            verified.add(ref)
        else:
            return None  # unverifiable ref ⇒ treat as absent ⇒ depends on all
    return verified

def _verified_warrant(c: Candidate, chain: Chain) -> Optional[set]:
    """D2: warrant basis must be receipt-refs that resolve to grant-class receipts."""
    if c.warrant_basis_refs is None:
        return None  # absent ⇒ depends on all authority state
    verified = set()
    for ref in c.warrant_basis_refs:
        r = chain.receipt(ref)
        if r is None or not r.grant_class:
            return None  # value-only or non-grant ⇒ treat as absent
        verified.add(ref)
    return verified

def independent(x: Candidate, y: Candidate, chain: Chain) -> str:
    """Conservative under-approximation of independence. Unknown ⇒ DEPENDENT.

    Returns INDEPENDENT only when every applicable schema check is positively satisfied.
    Raises OracleRefusal for admission-time contradictions (e.g. posture underdeclaration).
    """
    # D7 aggregates depend on members; never independent of a member.
    for a, b in ((x, y), (y, x)):
        if a.is_aggregate and a.member_range and (b.op or True):
            return DEPENDENT
    # D5 / D4 barriers: if either is a global barrier, dependent.
    if _is_barrier(x, chain) or _is_barrier(y, chain):
        # a subjected safety op is only dependent on its subject (handled below); barriers here
        # are the *global* ones.
        return DEPENDENT
    # D4 subjected safety op: dependent on its subject specifically.
    for a, b in ((x, y), (y, x)):
        if a.op in SAFETY_OPS and a.refusal_subject not in (None, "ALL_PENDING"):
            subj = a.refusal_subject
            # if b is the subject (by produced effect, binding, or identity-proxy), dependent
            if subj in b.produces_effects or subj in [k for k in b.binding_key]:
                return DEPENDENT
    # D3 binding contention: shared (effect_id, authority) ⇒ dependent.
    if set(x.binding_key) & set(y.binding_key):
        return DEPENDENT
    # D3 absence ⇒ unknown target ⇒ dependent.
    if not x.binding_key or not y.binding_key:
        return DEPENDENT
    # D1 causal: verified input refs must not include the other's products/hashes.
    xin, yin = _verified_input_refs(x, chain), _verified_input_refs(y, chain)
    if xin is None or yin is None:
        return DEPENDENT  # absent/unverifiable ⇒ depends on all
    if (set(y.produces_effects) & xin) or (set(x.produces_effects) & yin):
        return DEPENDENT
    # D2 warrant: verified basis must not reference the other's products.
    xw, yw = _verified_warrant(x, chain), _verified_warrant(y, chain)
    if xw is None or yw is None:
        return DEPENDENT  # absent/value-only ⇒ depends on all authority state
    # D6 session boundary: members can't cross their own open/close (modeled by marker).
    for a, b in ((x, y), (y, x)):
        if a.session_marker in ("open", "close") and b.session == a.session:
            return DEPENDENT
    # D8 hidden: same agent+session requires the above disjointness proofs (now satisfied).
    #   If same agent+session, we required verified input_refs, warrant, disjoint binding —
    #   all checked above. Cross-agent: same checks, D8 presumed absent. Either way:
    return INDEPENDENT

# ---- minimal commit-lane simulation (I7 / C2 / C3) --------------------------
class CommitLane:
    """Single append authority. Durable queue exists but NEVER auto-commits (I7)."""
    def __init__(self, chain: Chain):
        self.chain = chain
        self.durable_queue: list[Candidate] = []   # durable candidates, NO position
        self.committed_then_effect: list[tuple] = []  # (receipt, effect_fired)
    def enqueue(self, c: Candidate):
        self.durable_queue.append(c)                # durable, but unpositioned (I7)
    def commit_and_effect(self, c: Candidate, admit_fn, effect_fn, actual_binding=None):
        """NBER-1: receipt committed BEFORE effect. Returns (receipt, effect_result)."""
        if not admit_fn(c, self.chain):             # re-validate at the lane (I7 re-entry)
            raise OracleRefusal("LANE-REFUSED-AT-COMMIT")
        # declared-vs-actual binding mismatch ⇒ refuse (H1/A3)
        if actual_binding is not None and set(actual_binding) != set(c.binding_key):
            raise OracleRefusal("BINDING-DECL-ACTUAL-MISMATCH")
        r = self.chain.append(c, actual_binding_keys=actual_binding)  # STEP: receipt durable
        self.committed_then_effect.append((r, False))
        res = effect_fn(c)                          # STEP: effect AFTER receipt (NBER-1)
        self.committed_then_effect[-1] = (r, True)
        return r, res
    def recover_after_crash(self, admit_fn):
        """C2/I7: on restart, queued candidates are NEVER auto-promoted. Re-offer to lane."""
        promoted = []
        for c in self.durable_queue:
            # MUST re-enter the lane + re-validate; may now be refused by current chain state.
            if admit_fn(c, self.chain):
                promoted.append(c)   # eligible for re-commit (not auto-committed here)
        self.durable_queue = []
        return promoted              # caller must commit_and_effect explicitly (re-entry)
