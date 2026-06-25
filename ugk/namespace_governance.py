"""ugk/namespace_governance.py — Namespace OWNERSHIP governance (FGA §10).

Two orthogonal namespace concerns (the r66 ontology refinement)
==============================================================
FGA's single "namespace" concept is realized in UGK along two orthogonal dimensions:

  1. MEMBERSHIP namespace — WHICH names are constitutionally valid. Already realized and
     ALREADY CONSTITUTIONAL: `invariants.NAMESPACE_PHI_0` (in law_hash), committed via
     `namespace.MOSAIC_ROOT_PHI_0`, enforced by `decision.py` (NamespaceNonMember). See
     `ugk/namespace.py`. This module does NOT touch it. Governed mutation of the membership
     set is law_hash-moving and belongs to the amendment milestone.

  2. OWNERSHIP namespace — WHO may claim / allocate / delegate / revoke / invalidate / contest
     names. THIS is the gap #2 subsystem, realized here.

CONSTITUTIONAL STATUS (current through r74)
===========================================
Realized via the kernel's transition machinery: each ownership action is an instance of the
transition form the kernel already realizes (admissibility → receipt-before-effect → refusable),
routed through GovernanceKernel.execute() as a Tier-2 APPLICATION_OP. Ownership is a DETERMINISTIC
PROJECTION over the receipt chain — there is NO ownership table (a new SQLite table would move
schema_hash).

  - Phase 2a (claim / allocation / conflict policy = REFUSE): CONSTITUTIONALIZED at r70 via
    NS-S-01 (ownership = deterministic receipt-chain projection, no table), NS-S-02 (claim and
    allocate are DISTINCT, must-not-collapse), NS-S-03 (allocation conflict = REFUSE, fail-closed).
    These are now law (in law_hash). See AD-17.
  - Phase 2b (delegation / revocation / invalidation): realized at r74 as IR, FRAME-STATIONARY
    (law_hash / legend_hash / schema_hash all unmoved, no table). Constitutionalization is DEFERRED
    to an optional later law-leg amendment (the 2a→r70 precedent). Until/unless such an amendment is
    enacted, the 2b semantics must not be silently treated as constitutional law, nor silently
    demoted.

Historical note: r66 introduced this module as a provisional constitutional candidate (AD-15),
before r70 constitutionalized Phase 2a.

Phase 2a scope: claim + allocation + ownership projection + conflict-resolution = REFUSE
(fail-closed default). Phase 2b (REALIZED, frame-stationary IR — no law/legend/schema move, no
table, not constitutionalized): delegation (owner grants SCOPED authority), revocation and
invalidation (owner removes ownership; PERMANENT — no un-revoke, WILL-S-04 pattern), all folded by
_project and gated owner-only (non-owner → REFUSE). Phase 2c (REALIZED, frame-stationary IR — no law/legend/schema move, no table, not
constitutionalized): SUPERSESSION (owner-initiated TRANSFER of ownership to a new owner, owner-only)
and ADJUDICATION (the constitutional Governor — kernel mosaic root — AWARDS a contested name,
overriding the current owner; Governor-only; cannot resurrect a revoked name). EXPIRATION is NOT a
separate primitive: per the E4 ruling it collapses onto 2b revoke/invalidate as a policy REASON for
removal — there is NO time/TTL/expires_at/clock anywhere in the projection (determinism is sacred;
owner_of stays a pure receipt-chain fold reading no wall-clock). Constitutionalization of 2b/2c is
DEFERRED to an optional later law-leg amendment (the 2a→r70 precedent).
"""
from __future__ import annotations

import unicodedata
from typing import Callable, Optional

OP_CLAIM = "namespace_claim"
OP_ALLOCATE = "namespace_allocate"
OP_DELEGATE = "namespace_delegate"        # 2b: owner grants SCOPED authority over a name
OP_REVOKE = "namespace_revoke"            # 2b: owner removes own ownership (permanent)
OP_INVALIDATE = "namespace_invalidate"    # 2b: owner strikes a name invalid (permanent)
OP_SUPERSEDE = "namespace_supersede"      # 2c: owner TRANSFERS ownership to a new owner
OP_ADJUDICATE = "namespace_adjudicate"    # 2c: constitutional Governor AWARDS a contested name


def canonicalize(name: str) -> str:
    """Deterministic canonical form for ownership-conflict detection (N1 = N2 under
    canonicalization, FGA §10). NFC-normalize, strip surrounding whitespace, casefold.
    Pure function — identical input always yields identical output (determinism is sacred).
    """
    if name is None:
        return ""
    return unicodedata.normalize("NFC", str(name)).strip().casefold()


def _params(receipt) -> dict:
    p = receipt.parameters
    if isinstance(p, str):
        import json
        try:
            p = json.loads(p or "{}")
        except Exception:
            p = {}
    return p or {}


def _project(store) -> dict:
    """Single deterministic fold of the receipt chain (chain order) into namespace state:
      - owners:    {canonical_name: {"owner", "name", "index"}}  (allocation grants)
      - revoked:   set of canonical names PERMANENTLY removed (revoke / invalidate). A revoked
                   name is never re-granted by a later allocation (WILL-S-04 permanence pattern:
                   no un-revoke). This is enforced in-fold and by make_allocation_gate.
      - delegates: {canonical_name: [authority, ...]}  scoped grants made by the current owner.
    Authority rule (reused from NS-S-03 / authority-by-admissibility): delegate / revoke /
    invalidate take effect ONLY when the receipt authority is the current owner of the name;
    otherwise they are folded with no ownership effect (and are refused at emit time by the gate).
    Pure/deterministic: identical receipt chain → identical state.
    """
    owners: dict = {}
    revoked: set = set()
    delegates: dict = {}
    for i, r in enumerate(store.all_receipts()):
        if r.failed:
            continue
        p = _params(r)
        canon = p.get("canonical") or canonicalize(p.get("name", ""))
        if not canon:
            continue
        if r.op == OP_ALLOCATE:
            if canon not in owners and canon not in revoked:   # permanent revocation blocks re-grant
                owners[canon] = {"owner": r.authority, "name": p.get("name", ""), "index": i}
        elif r.op == OP_DELEGATE:
            cur = owners.get(canon)
            da = p.get("delegate_authority")
            if cur is not None and r.authority == cur["owner"] and da:   # only the owner may delegate
                d = delegates.setdefault(canon, [])
                if da not in d:
                    d.append(da)
        elif r.op in (OP_REVOKE, OP_INVALIDATE):
            cur = owners.get(canon)
            if cur is not None and r.authority == cur["owner"]:          # only the owner may remove
                del owners[canon]
                revoked.add(canon)                                       # PERMANENT
                delegates.pop(canon, None)
        elif r.op == OP_SUPERSEDE:
            cur = owners.get(canon)
            new = p.get("new_owner")
            if cur is not None and r.authority == cur["owner"] and new:  # owner-initiated TRANSFER
                owners[canon] = {"owner": new, "name": p.get("name", ""), "index": i}
                delegates.pop(canon, None)   # delegations are not carried across a transfer (v0)
        elif r.op == OP_ADJUDICATE:
            # Governor-imposed AWARD. Admissibility (authority == constitutional Governor mosaic root)
            # is enforced at the emit gate; a non-Governor adjudicate is refused (failed) and never
            # folded. Permanence is sacred: adjudication CANNOT resurrect a revoked/invalidated name.
            award = p.get("awarded_owner")
            if award and canon not in revoked:
                owners[canon] = {"owner": award, "name": p.get("name", ""), "index": i}
                delegates.pop(canon, None)
    return {"owners": owners, "revoked": revoked, "delegates": delegates}


def project_owners(store) -> dict:
    """Current ownership projection {canonical_name: {"owner", "name", "index"}}. Backward-compatible
    Phase-2a return shape. 2b removals (revoke / invalidate) are now folded — revoked names are absent
    and permanently un-re-grantable; delegations are exposed via delegates_of / has_authority.
    """
    return _project(store)["owners"]


def namespace_state(store) -> dict:
    """Full 2b namespace state: {"owners", "revoked", "delegates"}."""
    return _project(store)


def owner_of(store, name: str) -> Optional[str]:
    """Current owner authority of `name` (by canonical form), or None if unowned/revoked."""
    rec = project_owners(store).get(canonicalize(name))
    return rec["owner"] if rec else None


def delegates_of(store, name: str) -> list:
    """Authorities the current owner has granted SCOPED authority over `name` (delegation)."""
    return list(_project(store)["delegates"].get(canonicalize(name), []))


def has_authority(store, name: str, authority: str) -> bool:
    """True if `authority` is the current owner OR a current delegate of `name` (scoped authority)."""
    st = _project(store)
    canon = canonicalize(name)
    rec = st["owners"].get(canon)
    if rec is not None and authority == rec["owner"]:
        return True
    return authority in st["delegates"].get(canon, [])


def make_allocation_gate(store, name: str) -> Callable[[], bool]:
    """Admissibility gate for namespace_allocate. Conflict policy = REFUSE (fail-closed v0):
    returns False (→ gate_refuse) if the canonical name is already owned OR has been permanently
    revoked/invalidated, else True. Receipt conflict does NOT imply namespace conflict (FGA §10).
    """
    canon = canonicalize(name)

    def _gate() -> bool:
        if not canon:
            return False  # malformed name — refuse
        st = _project(store)
        return canon not in st["owners"] and canon not in st["revoked"]   # 2b: revoked is permanent

    return _gate


def claim(kernel, name: str, authority: Optional[str] = None):
    """Record an ownership CLAIM (proposal to acquire). Distinct from allocation — a claim does
    not grant ownership. Gated only on basic validity (non-empty canonical form).
    """
    canon = canonicalize(name)
    return kernel.execute(
        op=OP_CLAIM,
        authority=authority,
        parameters={"name": name, "canonical": canon},
        gate=(lambda: bool(canon)),
        effect=None,
        jurisdiction="namespace",
    )


def allocate(kernel, name: str, authority: Optional[str] = None):
    """ADMIT a claim into OWNERSHIP. Gated by the conflict policy (REFUSE on collision). On
    admission the allocation receipt IS the ownership grant (ownership is projected from it).
    Raises GateRefusal on conflict (constitutional REFUSE), distinct from a protocol error.
    """
    canon = canonicalize(name)
    return kernel.execute(
        op=OP_ALLOCATE,
        authority=authority,
        parameters={"name": name, "canonical": canon},
        gate=make_allocation_gate(kernel._store, name),
        effect=None,
        jurisdiction="namespace",
    )


def delegate(kernel, name: str, delegate_authority: str, authority: Optional[str] = None):
    """Grant SCOPED authority over `name` to `delegate_authority`. Admissible only if `authority`
    is the current owner (else REFUSE → gate_refuse). Does not transfer ownership; the owner stays
    the owner and the delegate gains scoped authority (has_authority True)."""
    canon = canonicalize(name)

    def _gate() -> bool:
        return bool(canon) and bool(delegate_authority) and owner_of(kernel._store, name) == authority

    return kernel.execute(
        op=OP_DELEGATE,
        authority=authority,
        parameters={"name": name, "canonical": canon, "delegate_authority": delegate_authority},
        gate=_gate,
        effect=None,
        jurisdiction="namespace",
    )


def revoke(kernel, name: str, authority: Optional[str] = None):
    """REVOKE ownership of `name`. Admissible only if `authority` is the current owner (non-owner →
    REFUSE). Permanent: a revoked name is never re-granted (WILL-S-04 pattern — no un-revoke)."""
    canon = canonicalize(name)

    def _gate() -> bool:
        return bool(canon) and owner_of(kernel._store, name) == authority

    return kernel.execute(
        op=OP_REVOKE,
        authority=authority,
        parameters={"name": name, "canonical": canon},
        gate=_gate,
        effect=None,
        jurisdiction="namespace",
    )


def invalidate(kernel, name: str, authority: Optional[str] = None):
    """INVALIDATE `name` (strike it permanently invalid). Admissible only if `authority` is the
    current owner (non-owner → REFUSE). Permanent: the name is never re-granted thereafter."""
    canon = canonicalize(name)

    def _gate() -> bool:
        return bool(canon) and owner_of(kernel._store, name) == authority

    return kernel.execute(
        op=OP_INVALIDATE,
        authority=authority,
        parameters={"name": name, "canonical": canon},
        gate=_gate,
        effect=None,
        jurisdiction="namespace",
    )


def supersede(kernel, name: str, new_owner: str, authority: Optional[str] = None):
    """SUPERSEDE (transfer) ownership of `name` from the current owner to `new_owner`. Owner-initiated:
    admissible only if `authority` is the current owner (non-owner → REFUSE). Distinct from allocation
    REFUSE (NS-S-03): this transfers EXISTING ownership rather than allocating a colliding name."""
    canon = canonicalize(name)

    def _gate() -> bool:
        return bool(canon) and bool(new_owner) and owner_of(kernel._store, name) == authority

    return kernel.execute(
        op=OP_SUPERSEDE,
        authority=authority,
        parameters={"name": name, "canonical": canon, "new_owner": new_owner},
        gate=_gate,
        effect=None,
        jurisdiction="namespace",
    )


def adjudicate(kernel, name: str, awarded_owner: str, authority: Optional[str] = None):
    """ADJUDICATE: the constitutional Governor AWARDS a contested name to `awarded_owner`, overriding the
    current owner. Admissible ONLY if `authority` is the constitutional Governor (kernel mosaic root);
    any other authority → REFUSE. Cannot resurrect a permanently revoked/invalidated name (permanence
    is sacred). Reuses the constitutional Governor identity established at the founding ceremony."""
    canon = canonicalize(name)
    gov = getattr(kernel, "_mosaic_root", "") or ""

    def _gate() -> bool:
        if not (canon and awarded_owner):
            return False
        if not gov or authority != gov:        # Governor-only (constitutional root authority)
            return False
        return canon not in _project(kernel._store)["revoked"]   # permanence: no resurrection

    return kernel.execute(
        op=OP_ADJUDICATE,
        authority=authority,
        parameters={"name": name, "canonical": canon, "awarded_owner": awarded_owner},
        gate=_gate,
        effect=None,
        jurisdiction="namespace",
    )
