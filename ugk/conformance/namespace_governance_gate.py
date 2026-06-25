"""ugk/conformance/namespace_governance_gate.py — FGA §10 ownership lifecycle (Phase 2a). GATE_GROUP = "integration"

Proves the OWNERSHIP namespace (distinct from the constitutional MEMBERSHIP namespace
NAMESPACE_PHI_0) is governed as transitions:
  - claim and allocation are DISTINCT receipted transitions (not collapsed, FGA §10);
  - ownership is a deterministic receipt-chain projection (no table);
  - a colliding allocation is REFUSED (gate_refuse), distinct from a successful allocation;
  - canonical-name collision is the conflict criterion (N1 = N2 under canonicalization);
  - receipt conflict does NOT imply namespace conflict (distinct names both allocate).
Phase 2b/2c ownership-lifecycle authority is CONSTITUTIONAL as of r130 (AD-53): NS-S-04 (owner-only
lifecycle; delegation is scoped non-ownership authority conferring NO lifecycle authority), NS-S-05
(revoke/invalidate permanent; no wall-clock/TTL — determinism), NS-S-06 (Governor-only adjudication;
no resurrection). Membership namespace (NAMESPACE_PHI_0) is a separate constitutional concern, not
touched here.
"""


def run():
    from ugk.kernel import GovernanceKernel, GateRefusal
    from ugk import namespace_governance as NG
    fails = []

    def founded():
        k = GovernanceKernel(); k._ceremony(); k.open_session()
        return k

    # 1+2. claim then allocate — distinct receipted transitions; ownership granted
    k = founded()
    NG.claim(k, "alpha", authority="gov1")
    NG.allocate(k, "alpha", authority="gov1")
    ops = [r.op for r in k._store.all_receipts()]
    if NG.OP_CLAIM not in ops:
        fails.append("claim: no namespace_claim receipt")
    if NG.OP_ALLOCATE not in ops:
        fails.append("allocate: no namespace_allocate receipt")
    if NG.OP_CLAIM == NG.OP_ALLOCATE:
        fails.append("claim/allocate collapsed into one op")
    if NG.owner_of(k._store, "alpha") != "gov1":
        fails.append(f"ownership projection wrong: {NG.owner_of(k._store, 'alpha')!r} != gov1")

    # 3. conflict — different authority allocates the SAME canonical name -> REFUSED
    refused = False
    try:
        NG.allocate(k, "Alpha ", authority="gov2")  # canonical 'alpha' already owned
    except GateRefusal:
        refused = True
    if not refused:
        fails.append("conflict: colliding allocation was not refused")
    # ownership unchanged; a gate_refuse receipt exists; no second allocation success
    if NG.owner_of(k._store, "alpha") != "gov1":
        fails.append("conflict: ownership changed despite refusal")
    rcps = k._store.all_receipts()
    if not any(r.op == "gate_refuse" for r in rcps):
        fails.append("conflict: no gate_refuse receipt for the collision")
    alloc_success = [r for r in rcps if r.op == NG.OP_ALLOCATE and not r.failed]
    if len(alloc_success) != 1:
        fails.append(f"conflict: expected exactly 1 successful allocation, got {len(alloc_success)}")

    # 4. canonicalization is the conflict criterion
    if NG.canonicalize("Alpha ") != NG.canonicalize("alpha"):
        fails.append("canonicalization: 'Alpha ' and 'alpha' should collide")
    if NG.canonicalize("alpha") == NG.canonicalize("beta"):
        fails.append("canonicalization: distinct names must not collide")

    # 5. receipt conflict != namespace conflict — distinct names both allocate
    k2 = founded()
    NG.allocate(k2, "alpha", authority="gov1")
    NG.allocate(k2, "beta", authority="gov1")  # different name, same owner — must NOT conflict
    if NG.owner_of(k2._store, "alpha") != "gov1" or NG.owner_of(k2._store, "beta") != "gov1":
        fails.append("receipt-conflict-not-namespace-conflict: distinct names failed to allocate")

    # 6. determinism — projection is stable
    if NG.project_owners(k2._store) != NG.project_owners(k2._store):
        fails.append("projection not deterministic")

    # ---- Phase 2b: delegation / revocation / invalidation (frame-stationary IR) ----------------
    # 2b.1 delegate grants SCOPED authority; ownership unchanged
    k3 = founded()
    NG.allocate(k3, "gamma", authority="gov1")
    NG.delegate(k3, "gamma", "gov2", authority="gov1")
    if not NG.has_authority(k3._store, "gamma", "gov2"):
        fails.append("2b delegate: delegate gov2 lacks scoped authority")
    if NG.owner_of(k3._store, "gamma") != "gov1":
        fails.append("2b delegate: delegation changed ownership")
    nd_ref = False
    try:
        NG.delegate(k3, "gamma", "gov4", authority="gov3")   # non-owner delegate
    except GateRefusal:
        nd_ref = True
    if not nd_ref:
        fails.append("2b delegate: non-owner delegation not refused")

    # 2b.1c NS-S-04 clarification: delegation confers NO lifecycle authority — the delegate (gov2),
    # a non-owner, can NOT revoke / invalidate / supersede; each REFUSES and ownership stays gov1.
    for _op, _call in (("revoke", lambda: NG.revoke(k3, "gamma", authority="gov2")),
                       ("invalidate", lambda: NG.invalidate(k3, "gamma", authority="gov2")),
                       ("supersede", lambda: NG.supersede(k3, "gamma", "gov2", authority="gov2"))):
        _ref = False
        try:
            _call()
        except GateRefusal:
            _ref = True
        if not _ref:
            fails.append("2b.1c NS-S-04: delegate %s not refused (lifecycle authority leaked)" % _op)
    if NG.owner_of(k3._store, "gamma") != "gov1":
        fails.append("2b.1c NS-S-04: delegate lifecycle attempt changed ownership")

    # 2b.2 revoke removes ownership when authorized by current owner
    k4 = founded()
    NG.allocate(k4, "delta", authority="gov1")
    NG.revoke(k4, "delta", authority="gov1")
    if NG.owner_of(k4._store, "delta") is not None:
        fails.append("2b revoke: owner revoke did not remove ownership")

    # 2b.3 non-owner revoke REFUSES; ownership intact
    k5 = founded()
    NG.allocate(k5, "epsilon", authority="gov1")
    nr_ref = False
    try:
        NG.revoke(k5, "epsilon", authority="gov2")
    except GateRefusal:
        nr_ref = True
    if not nr_ref:
        fails.append("2b revoke: non-owner revoke not refused")
    if NG.owner_of(k5._store, "epsilon") != "gov1":
        fails.append("2b revoke: non-owner revoke changed ownership")

    # 2b.4 invalidate removes ownership
    k6 = founded()
    NG.allocate(k6, "zeta", authority="gov1")
    NG.invalidate(k6, "zeta", authority="gov1")
    if NG.owner_of(k6._store, "zeta") is not None:
        fails.append("2b invalidate: invalidate did not remove ownership")

    # 2b.5 revocation/invalidation are PERMANENT in the projection (no re-grant)
    perm_r = False
    try:
        NG.allocate(k4, "delta", authority="gov2")   # re-allocate a revoked name
    except GateRefusal:
        perm_r = True
    if not perm_r or NG.owner_of(k4._store, "delta") is not None:
        fails.append("2b permanence: revoked name was re-grantable")
    perm_i = False
    try:
        NG.allocate(k6, "zeta", authority="gov3")    # re-allocate an invalidated name
    except GateRefusal:
        perm_i = True
    if not perm_i or NG.owner_of(k6._store, "zeta") is not None:
        fails.append("2b permanence: invalidated name was re-grantable")

    # 2b.6 ownership remains a deterministic receipt-chain projection with 2b ops folded
    if NG.namespace_state(k4._store) != NG.namespace_state(k4._store):
        fails.append("2b determinism: namespace_state not deterministic")

    # ---- Phase 2c: supersession / adjudication (frame-stationary IR; expiration collapses onto 2b) --
    # 2c.1 supersede: owner-initiated TRANSFER
    k7 = founded()
    NG.allocate(k7, "theta", authority="gov1")
    NG.supersede(k7, "theta", "gov2", authority="gov1")
    if NG.owner_of(k7._store, "theta") != "gov2":
        fails.append("2c supersede: owner transfer did not move ownership to gov2")
    ns_ref = False
    try:
        NG.supersede(k7, "theta", "gov4", authority="gov3")   # non-owner supersede
    except GateRefusal:
        ns_ref = True
    if not ns_ref:
        fails.append("2c supersede: non-owner supersede not refused")
    # 2c.1b NS-S-03 REFUSE unaffected: a fresh ALLOCATE of a transferred (still-owned) name REFUSES
    sup_alloc_ref = False
    try:
        NG.allocate(k7, "theta", authority="gov5")
    except GateRefusal:
        sup_alloc_ref = True
    if not sup_alloc_ref:
        fails.append("2c supersede: colliding allocate after transfer not refused (NS-S-03 weakened)")

    # 2c.2 adjudicate: constitutional Governor AWARDS, overriding current owner
    k8 = founded()
    gov_root = getattr(k8, "_mosaic_root", "")
    NG.allocate(k8, "iota", authority="gov1")
    NG.adjudicate(k8, "iota", "gov2", authority=gov_root)
    if NG.owner_of(k8._store, "iota") != "gov2":
        fails.append("2c adjudicate: Governor award did not override ownership to gov2")
    na_ref = False
    try:
        NG.adjudicate(k8, "iota", "gov9", authority="gov1")   # non-Governor adjudicate
    except GateRefusal:
        na_ref = True
    if not na_ref:
        fails.append("2c adjudicate: non-Governor adjudicate not refused")

    # 2c.3 adjudication CANNOT resurrect a permanently revoked name (permanence is sacred)
    k9 = founded()
    NG.allocate(k9, "kappa", authority="gov1")
    NG.revoke(k9, "kappa", authority="gov1")
    res_ref = False
    try:
        NG.adjudicate(k9, "kappa", "gov2", authority=getattr(k9, "_mosaic_root", ""))
    except GateRefusal:
        res_ref = True
    if not res_ref or NG.owner_of(k9._store, "kappa") is not None:
        fails.append("2c adjudicate: resurrected a permanently revoked name")

    # 2c.4 determinism with 2c ops folded
    if NG.namespace_state(k8._store) != NG.namespace_state(k8._store):
        fails.append("2c determinism: namespace_state not deterministic")

    # NS-S-05 permanence across SUPERSEDE: a revoked name has no owner to authorize a transfer,
    # so supersede of the revoked name REFUSES (permanence holds across allocate AND supersede).
    sup_rev_ref = False
    try:
        NG.supersede(k9, "kappa", "gov7", authority="gov1")   # kappa revoked above
    except GateRefusal:
        sup_rev_ref = True
    if not sup_rev_ref or NG.owner_of(k9._store, "kappa") is not None:
        fails.append("NS-S-05: revoked name was supersedable (permanence breached)")

    # NS-S-05 NO-CLOCK determinism: the ownership projection admits no wall-clock / TTL — proven
    # structurally (the fold reads no clock) and on the state shape (no ttl/expiry field).
    import inspect as _inspect
    _src = _inspect.getsource(NG._project).lower()
    if any(_t in _src for _t in ("time.time", "datetime", "monotonic", "expires_at", "ttl")):
        fails.append("NS-S-05 no-clock: _project reads a wall-clock / TTL source")
    if any(_t in repr(NG.namespace_state(k9._store)).lower() for _t in ("ttl", "expires_at", "expiry")):
        fails.append("NS-S-05 no-clock: projection state carries a clock/TTL field")

    ok = not fails
    return ok, (
        "FGA §10 ownership lifecycle (2a+2b+2c): claim/allocation distinct; ownership = deterministic "
        "receipt projection (no table, no clock); canonical-collision REFUSED; 2b delegate/revoke/"
        "invalidate (owner-only; revoke/invalidate PERMANENT); 2c supersede (owner TRANSFER) + "
        "adjudicate (Governor AWARD, override; cannot resurrect revoked); non-owner/non-Governor REFUSED; "
        "NS-S-03 REFUSE unaffected by transfer; expiration collapses onto revoke/invalidate."
        if ok else "; ".join(fails)
    )


if __name__ == "__main__":
    ok, detail = run()
    print(f"namespace_governance_gate: {'PASS' if ok else 'FAIL'}  {detail}")
