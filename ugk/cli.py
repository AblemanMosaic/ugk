"""ugk/cli.py — CLI surface (Phase 4 thin adapter, Grundnorm 444).

All governance logic lives in GovernanceKernel.  The CLI parses arguments,
delegates to the kernel via kernel.execute() or kernel.snapshot(), and exits
with a structured verdict.

Commands:
  ugk govern   --intent X --subject Y [--authority Z] [--op OP]
  ugk status   [--json]
  ugk keygen
  ugk verify

Verdict exit codes:
  0 — admitted
  1 — gate refused (GateRefusal)
  2 — governance not founded (GovernanceNotFounded)
  3 — undeclared op (UndeclaredOp)
  4 — internal / Tier 0 op (KernelInternalOp)
  5 — error (unexpected exception)

DKN dimension_id is included in the authority envelope on every govern call.
Phase 4 constraint: NO governance logic here.  This module must contain zero
receipt-writing, hash-computing, or gate-evaluating code.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Kernel factory — shared across CLI commands
# ---------------------------------------------------------------------------

def _make_kernel(state_dir: Optional[str] = None):
    """Construct a GovernanceKernel from env or defaults."""
    import os
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore

    db_path = ":memory:"
    env_dir = state_dir or os.environ.get("UGK_STATE_DIR") or os.environ.get("ACIS_STATE_DIR")
    if env_dir:
        db_path = str(Path(env_dir) / "ugk.db")

    store = UGKReceiptStore(db_path=db_path)
    k = GovernanceKernel(store=store, authority="cli")
    k._ceremony()
    # B5a: activate the declared authority model at the CLI execution boundary. Before B5a the
    # CLI kernel never attached the charter's authority model, so require_gate/require_warrant
    # enforcement (CM-S-02/03) was DORMANT for every CLI-governed (Tier-2) op. Load the active
    # model from the charter and attach it BEFORE open_session, so CM-S-04 model_hash rides the
    # session_open receipt. The preset model's timestamp is bound to the manifest timestamp so
    # model_hash is DETERMINISTIC (no wall-clock in the content hash). Universal ops
    # (session_open/crp_evidence/...) remain constitutively exempt; only Tier-2 ops are enforced.
    try:
        from ugk.charter import DeploymentManifest
        from ugk.authority.authority_model import AuthorityModel
        _m = DeploymentManifest.load()
    except Exception:
        _m, AuthorityModel = None, None
    if _m is not None and getattr(_m, "authority_model", None) in ("alt_prevention", "alt_trace", "trace_only"):
        _proto = getattr(AuthorityModel, _m.authority_model)(k._law_hash, "cli")
        _model = AuthorityModel.create(
            _proto.model_id, _proto.require_gate, _proto.require_warrant, _proto.require_intent,
            _proto.description, _proto.rationale, k._law_hash, "cli", timestamp=_m.timestamp,
        )
        k.set_authority_model(_model)
    k.open_session()
    return k


# ---------------------------------------------------------------------------
# Govern command
# ---------------------------------------------------------------------------

def _cmd_govern(args) -> int:
    """Execute a governed op and print a JSON verdict.  Returns exit code."""
    from ugk.kernel import (
        GovernanceKernel, GateRefusal, GovernanceNotFounded,
        UndeclaredOp, KernelInternalOp,
    )

    k = _make_kernel(getattr(args, "state_dir", None))
    snap_before = k.snapshot_fast()

    # Carry dimension_id as authority envelope (DKN identity namespace)
    authority = getattr(args, "authority", "cli")
    if snap_before.get("dimension_id"):
        authority = f"{authority}@{snap_before['dimension_id'][:16]}"

    op = getattr(args, "op", "crp_evidence") or "crp_evidence"
    parameters = {
        "intent":    args.intent,
        "subject":   args.subject,
        "authority": authority,
    }

    try:
        k.execute(op=op, authority=authority, parameters=parameters)
        snap_after = k.snapshot_fast()
        verdict = {
            "admitted":      True,
            "op":            op,
            "authority":     authority,
            "stream_hash":   snap_after["stream_hash"],
            "receipt_count": snap_after["receipt_count"],
            "dimension_id":  snap_after.get("dimension_id", ""),
            "governance_status": snap_after["governance_status"],
        }
        print(json.dumps(verdict, indent=2))
        return 0

    except GateRefusal as e:
        _print_refused(op, str(e))
        return 1
    except GovernanceNotFounded as e:
        _print_error("governance_not_founded", op, str(e))
        return 2
    except UndeclaredOp as e:
        _print_error("undeclared_op", op, str(e))
        return 3
    except KernelInternalOp as e:
        _print_error("kernel_internal_op", op, str(e))
        return 4
    except Exception as e:
        _print_error("error", op, str(e))
        return 5


def _print_refused(op: str, reason: str) -> None:
    print(json.dumps({"admitted": False, "op": op, "reason": reason}, indent=2))


def _print_error(kind: str, op: str, detail: str) -> None:
    print(json.dumps({"admitted": False, "op": op, "error": kind,
                      "detail": detail}, indent=2))


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def _cmd_status(args) -> int:
    """Print kernel status snapshot. Read-only — does not open a session."""
    import os, hashlib
    from ugk.storage.store import UGKReceiptStore
    from ugk.storage.binding import LEGEND_HASH
    from ugk.kernel import GOVERNOR_PUBKEY_HEX, _PHASE_CODE
    from ugk.storage.binding import mosaic_id as _mosaic_id
    from ugk.integrity.readonly import ReadOnlyGuard, ReadOnlyViolation
    state_dir = getattr(args, "state_dir", None)
    env_dir = state_dir or os.environ.get("UGK_STATE_DIR") or os.environ.get("ACIS_STATE_DIR")
    db_path = str(Path(env_dir) / "ugk.db") if env_dir else ":memory:"
    law_hash = hashlib.sha256(
        open(Path(__file__).parent / "invariants.py", "rb").read()
    ).hexdigest()
    # IEL Invariant D (AD-30): read-only mode=ro store; missing state fails closed (no creation).
    try:
        with ReadOnlyGuard(db_path, name="status"):
            store = UGKReceiptStore(db_path=db_path, read_only=True)
            snap = {
                "status":          "read-only snapshot",
                "chain_intact":    store.verify_stream_hash(),
                "receipt_count":   store.receipt_count(),
                "governor_pubkey": GOVERNOR_PUBKEY_HEX[:16]+"...",
                "mosaic_root":     _mosaic_id(GOVERNOR_PUBKEY_HEX)[:16]+"...",
                "phase_code":      _PHASE_CODE,
                "law_hash":        law_hash[:16]+"...",
                "legend_hash":     LEGEND_HASH[:16]+"...",
                "schema_hash":     store.schema_hash()[:16]+"...",
                "schema_frame_intact": store.schema_frame_intact(),
                "mode":            "read-only",
            }
    except ReadOnlyViolation as e:
        print(json.dumps({"status": "read-only snapshot", "chain_intact": False,
                          "mode": "read-only", "error": "state_absent_or_unreadable",
                          "detail": str(e)}, indent=2))
        return 2
    print(json.dumps(snap, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Keygen command
# ---------------------------------------------------------------------------

def _keygen_provenance(pub_hex, intent=None):
    """B3a creation provenance: a founding-independent, PUBLIC-ONLY artifact that makes
    key origin answerable. pubkey_fingerprint = mosaic_id(pubkey) = SHA-256(pubkey) — the
    same identity root that founding stores as manifest.mosaic_root, so this artifact
    forward-links to a later `charter` using only public material. It asserts identity
    (WHO), never authority (which requires the Ed25519 secret, bound at founding). It
    contains NO private-key material. This is a provenance artifact, not a governance
    receipt: it does not route through execute() and requires no founded chain."""
    import time, hashlib
    from pathlib import Path as _P
    from ugk.storage.binding import mosaic_id as _mosaic_id, LEGEND_HASH
    import ugk as _ugk
    law_hash = hashlib.sha256((_P(__file__).parent / "invariants.py").read_bytes()).hexdigest()
    return {
        "kind":               "keygen_creation_provenance",
        "pubkey_hex":         pub_hex,
        "pubkey_fingerprint": _mosaic_id(pub_hex),
        "timestamp":          time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "intent":             intent,
        "impl": {"ugk_version": getattr(_ugk, "__version__", None),
                 "law_hash": law_hash, "legend_hash": LEGEND_HASH},
        "note": ("Public provenance only — asserts identity (WHO), not authority. "
                 "Forward-links to founding via manifest.mosaic_root == pubkey_fingerprint. "
                 "Contains no private-key material."),
    }


def _cmd_keygen(args) -> int:
    """Generate a fresh Ed25519 keypair.
    Default: pubkey only. --show-private: full keypair + loud warning.
    --write-secure PATH: write full keypair to PATH at 0o600 on POSIX (must not pre-exist); fails closed on Windows (cannot enforce user-only ACLs in this stdlib-only build).
    """
    import os as _os
    import stat as _stat
    from ugk.vendor.ed25519 import generate_keypair
    priv_hex, pub_hex = generate_keypair()
    intent = getattr(args, "intent", None)
    provenance = _keygen_provenance(pub_hex, intent)   # B3a: PUBLIC-only creation provenance
    write_path = getattr(args, "write_secure", None)
    show_priv  = getattr(args, "show_private",  False)
    if write_path:
        if _os.name == "nt":
            print("ERROR: --write-secure cannot enforce user-only ACLs on Windows in this stdlib-only build.", file=sys.stderr)
            print("Use --show-private only in a protected terminal, then store the key in a location protected by Windows ACLs.", file=sys.stderr)
            return 1
        if _os.path.exists(write_path):
            print(f"ERROR: {write_path!r} already exists.", file=sys.stderr); return 1
        payload = json.dumps({"pubkey_hex":pub_hex,"privkey_hex":priv_hex,
                               "note":"Private key material. Store securely."}, indent=2)+"\n"
        fd = _os.open(write_path, _os.O_WRONLY|_os.O_CREAT|_os.O_EXCL, 0o600)
        try:
            with _os.fdopen(fd,"w") as fh: fh.write(payload)
        except Exception:
            _os.unlink(write_path); raise
        mode = _stat.S_IMODE(_os.stat(write_path).st_mode)
        if mode != 0o600:
            _os.unlink(write_path)
            print(f"ERROR: secure key write failed: mode {oct(mode)} != 0o600", file=sys.stderr)
            return 1
        # B3a: write a sibling PUBLIC provenance artifact (no private key) beside the key file.
        prov_path = write_path + ".provenance.json"
        try:
            with open(prov_path, "w") as pf: pf.write(json.dumps(provenance, indent=2) + "\n")
        except Exception:
            print(f"WARNING: key written but provenance artifact failed: {prov_path!r}", file=sys.stderr)
            prov_path = None
        print(json.dumps({"pubkey_hex":pub_hex,"written_to":write_path,
                          "provenance_written_to":prov_path,"provenance":provenance},indent=2))
        print(f"*** Private key written to {write_path!r} (mode 0600). Keep off-artifact. ***",file=sys.stderr)
        return 0
    if show_priv:
        print("*** PRIVATE KEY — SENSITIVE — NOT FOR LOGS OR PIPELINES ***",file=sys.stderr)
        print("*** Store off-artifact. Never commit. Rotate after ceremony. ***",file=sys.stderr)
        print(json.dumps({"pubkey_hex":pub_hex,"privkey_hex":priv_hex,"provenance":provenance},indent=2)); return 0
    print(json.dumps({"pubkey_hex":pub_hex,"provenance":provenance,
                      "note":"Use --show-private or --write-secure PATH for private key."},indent=2))
    return 0


# ---------------------------------------------------------------------------
# Verify command
# ---------------------------------------------------------------------------

def _cmd_verify(args) -> int:
    """Verify the receipt chain integrity. Read-only — does not open a session."""
    import os
    from ugk.storage.store import UGKReceiptStore
    from ugk.integrity.readonly import ReadOnlyGuard, ReadOnlyViolation
    state_dir = getattr(args, "state_dir", None)
    env_dir = state_dir or os.environ.get("UGK_STATE_DIR") or os.environ.get("ACIS_STATE_DIR")
    db_path = str(Path(env_dir) / "ugk.db") if env_dir else ":memory:"
    # IEL Invariant D (AD-30): a true read-only path. The mode=ro store cannot create the DB; the
    # ReadOnlyGuard both pre-checks existence and DETECTS any creation. Missing state fails closed.
    try:
        with ReadOnlyGuard(db_path, name="verify"):
            store = UGKReceiptStore(db_path=db_path, read_only=True)
            # IEL / AD-28: require LINKAGE + full BODY, not linkage alone. Fails closed on tamper.
            res = store.verify_chain()
            result = {
                "chain_intact":       res.ok,
                "verification_level": res.achieved.name,
                "required_level":     res.required.name,
                "corruption":         res.corruption.value if res.corruption else None,
                "detail":             res.detail,
                "receipt_count":      store.receipt_count(),
                "stream_hash":        store.stream_hash(),
                "mode":               "read-only",
            }
    except ReadOnlyViolation as e:
        print(json.dumps({"chain_intact": False, "mode": "read-only",
                          "error": "state_absent_or_unreadable", "detail": str(e)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if res.ok else 1


# ---------------------------------------------------------------------------
# Attest command — 3+1 hash pins + stream hash proof
# ---------------------------------------------------------------------------



def _cmd_constitution(args) -> int:
    """Print the constitutional frame and authority model."""
    import os, hashlib
    from ugk.storage.binding import LEGEND_HASH, LEGEND_ENTRY_COUNT
    from ugk.kernel import GOVERNOR_PUBKEY_HEX
    from ugk.storage.binding import mosaic_id as _mosaic_id
    from ugk.invariants import INVARIANT_REGISTRY
    law_hash = hashlib.sha256(
        open(os.path.join(os.path.dirname(__file__), "invariants.py"), "rb").read()
    ).hexdigest()
    mosaic_root = _mosaic_id(GOVERNOR_PUBKEY_HEX)
    state_dir = getattr(args, "state_dir", None)
    model_id = "not declared"
    model_hash = ""
    if state_dir:
        try:
            from ugk.storage.store import UGKReceiptStore
            store = UGKReceiptStore(state_dir=state_dir)
            am = store._conn.execute(
                "SELECT model_id, model_hash FROM authority_model_archive ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if am: model_id, model_hash = am
        except Exception: pass
    frame = {
        "governor_pubkey":  GOVERNOR_PUBKEY_HEX[:16]+"...",
        "mosaic_root":      mosaic_root[:16]+"...",
        "law_hash":         law_hash[:16]+"...",
        "legend_hash":      LEGEND_HASH[:16]+"...",
        "legend_entries":   LEGEND_ENTRY_COUNT,
        "invariant_count":  len(INVARIANT_REGISTRY),
        "authority_model":  model_id,
    }
    if model_hash: frame["model_hash"] = model_hash[:16]+"..."
    fmt = getattr(args, "format", "text")
    if fmt == "json":
        print(json.dumps(frame, indent=2))
    else:
        for k, v in frame.items():
            print(f"  {k:<22} {v}")
    return 0


def _cmd_explain(args) -> int:
    """Explain a gate, invariant, or LEGEND entry by name or CSIL integer."""
    from ugk.invariants import INVARIANT_REGISTRY
    from ugk.storage.binding import _LEGEND_ENTRIES
    name = args.name
    # Try implementation concept ID. These entries are navigation, not law.
    try:
        from ugk.implementation_codex import load_entries
        concepts = load_entries()
    except Exception:
        concepts = {}
    if name in concepts:
        c = concepts[name]
        print(f"Concept: {c['concept_id']}")
        print(f"  Name:        {c['concept_name']}")
        print(f"  Status:      {c['status']}")
        print(f"  Role:        {c['role_in_substrate']}")
        print(f"  Not:         {c['what_it_is_not']}")
        print(f"  Instantiates: {c['instantiates']}")
        print(f"  Sources:     {', '.join(c['source_refs'])}")
        print(f"  Surfaces:    {', '.join(c['implementation_surfaces'])}")
        print(f"  Related:     {', '.join(c['related']) or 'none'}")
        print(f"  Rule:        {c['agent_operational_rule']}")
        print(f"  Failure:     {c['common_failure_mode']}")
        print(f"  Verified:    {c['last_verified_release']}")
        print(f"  Ceiling:     {c['claim_ceiling']}")
        print("  Boundary:    navigation only; not law; generated CODEX remains ugk/codex/CODEX.md")
        return 0
    # Try CSIL integer
    try:
        csil = int(name)
        matches = [e for e in _LEGEND_ENTRIES if e["csil_id"] == csil]
        if matches:
            e = matches[0]
            print(f"CSIL {e['csil_id']} [{e['tier']}]")
            print(f"  slug:   {e['slug']}")
            print(f"  render: {e['render']!r}")
            inv_refs = [i for i in INVARIANT_REGISTRY.values() if e["render"] in i.statement]
            if inv_refs:
                print(f"  referenced by: {', '.join(r.id for r in inv_refs[:5])}")
            return 0
        print(f"No LEGEND entry found for CSIL {csil}"); return 1
    except ValueError: pass
    # Try invariant ID
    if name in INVARIANT_REGISTRY:
        inv = INVARIANT_REGISTRY[name]
        dep_chain = []
        seen = set()
        queue = list(inv.depends_on)
        while queue:
            d = queue.pop(0)
            if d in seen: continue
            seen.add(d); dep_chain.append(d)
            if d in INVARIANT_REGISTRY:
                queue.extend(INVARIANT_REGISTRY[d].depends_on)
        print(f"Invariant: {name}")
        print(f"  Statement:   {inv.statement[:160]}...")
        print(f"  Class:       {inv.classification}")
        print(f"  Subsystem:   {inv.id.split('-')[0]}")
        print(f"  Gate:        {inv.gate}")
        print(f"  Ablation:    {inv.adjacency_target[:100]}...")
        print(f"  Depends-on:  {', '.join(inv.depends_on) or 'none'}")
        print(f"  Introduced:  {inv.introduced_in} (build lane - provenance, not semantic standing)")
        if dep_chain:
            print(f"  Full chain:  {' -> '.join(dep_chain)}")
        # In-degree: how many invariants depend on this one
        in_deg = sum(1 for i in INVARIANT_REGISTRY.values() if name in i.depends_on)
        print(f"  In-degree:   {in_deg}")
        return 0
    # Try gate name  
    import os, importlib
    gate_mod = f"ugk.conformance.{name}" if not name.startswith("ugk.") else name
    try:
        mod = importlib.import_module(gate_mod)
        print(f"Gate: {name}")
        print(f"  Module: {gate_mod}")
        invs = [i for i in INVARIANT_REGISTRY.values() if i.gate == name]
        if invs:
            print(f"  Covers: {', '.join(i.id for i in invs)}")
        if mod.__doc__:
            print(f"  Doc: {mod.__doc__.strip()[:120]}")
        return 0
    except ImportError: pass
    print(f"Not found: {name!r}. Try a concept ID (e.g. terminal-outcome-lattice), invariant ID (e.g. LEGEND-S-01), CSIL integer (e.g. 3003), or gate name.")
    return 1


def _cmd_posture(args) -> int:
    """Compute and display the Constitutional Governance Posture."""
    from ugk.kernel import GovernanceKernel
    from ugk.governance.posture import GovernancePosture
    state_dir=getattr(args,"state_dir",None)
    fmt=getattr(args,"format","text")
    k=GovernanceKernel(state_dir=state_dir) if state_dir else GovernanceKernel()
    try: k._ceremony()
    except Exception: pass
    posture=GovernancePosture.compute(k)
    if fmt=="json": print(posture.report("json"))
    else: print(posture.report("text"))
    return 0


def _cmd_health(args) -> int:
    """Full system health check: chain, posture, and optionally gate compliance."""
    from ugk.kernel import GovernanceKernel
    from ugk.governance.posture import GovernancePosture
    import importlib,time
    state_dir=getattr(args,"state_dir",None)
    run_gates_group=getattr(args,"run_gates",None)
    fmt=getattr(args,"format","text")
    k=GovernanceKernel(state_dir=state_dir) if state_dir else GovernanceKernel()
    try: k._ceremony()
    except Exception: pass
    posture=GovernancePosture.compute(k)
    # Gate compliance
    gate_results={}
    if run_gates_group:
        from ugk.conformance.run_gates_batch import GATES,_run_gate
        GATE_GROUPS={"structural":[],"unit":[],"integration":[],"conformance":[]}
        # Classify gates by GATE_GROUP annotation in their module docstring
        for modname in GATES:
            try:
                mod=importlib.import_module(modname)
                doc=mod.__doc__ or ""
                for grp in GATE_GROUPS:
                    if grp.upper() in doc.upper() or f'GATE_GROUP = "{grp}"' in doc:
                        GATE_GROUPS[grp].append(modname); break
                else:
                    GATE_GROUPS["integration"].append(modname)
            except Exception:
                GATE_GROUPS["integration"].append(modname)
        if run_gates_group=="all":
            selected=[m for g in ["structural","unit","integration","conformance"] for m in GATE_GROUPS[g]]
        else:
            selected=GATE_GROUPS.get(run_gates_group,GATES)
        passed=0; failed_names=[]
        import io, contextlib
        for modname in selected:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ok,detail,ms=_run_gate(modname)
            if ok: passed+=1
            else: failed_names.append(modname.rsplit(".",1)[-1])
        gate_results={"passed":passed,"total":len(selected),"failed":failed_names}
    sections=["chain","authority_model","posture","disjuncts","gate_compliance"]
    if fmt=="json":
        out={"sections":sections,"chain_intact":posture.chain_intact,
             "receipt_count":posture.receipt_count,"authority_model":posture.authority_model,
             "phi":posture.phi,"disjuncts":{"a":posture.disjunct_a,"b":posture.disjunct_b,"c":posture.disjunct_c},
             "posture_hash":posture.posture_hash}
        if gate_results: out["gate_compliance"]=gate_results
        print(json.dumps(out,indent=2))
    else:
        print("UGK Health Report"); print("="*40)
        print(f"chain:          {'intact' if posture.chain_intact else 'BROKEN'}  ({posture.receipt_count} receipts)")
        print(f"authority_model: {posture.authority_model}")
        print(f"posture:        {posture.disjunct_a}/{posture.disjunct_b}/{posture.disjunct_c} disjuncts, phi={posture.phi:.2f}")
        if gate_results:
            p,t=gate_results["passed"],gate_results["total"]
            status="ALL PASS" if p==t else f"{t-p} FAILED"
            print(f"gates:          {p}/{t} {status}")
            if gate_results["failed"]: print(f"  failed: {', '.join(gate_results['failed'])}")
        else:
            print("gates:          (run with --run-gates all|structural|unit|integration|conformance)")
        print(f"posture_hash:   {posture.posture_hash[:16]}...")
    return 0 if posture.chain_intact else 1


def _cmd_charter(args) -> int:
    """ugk charter — founding constitutional act. Establishes deployment governance identity."""
    import os
    from ugk.charter import DeploymentManifest, write_charter_artifacts
    from ugk.vendor.ed25519 import generate_keypair
    pubkey = args.pubkey.strip()
    if len(pubkey) != 64:
        print(f"ERROR: --pubkey must be 64 hex chars, got {len(pubkey)}", file=sys.stderr); return 1
    try: bytes.fromhex(pubkey)
    except ValueError: print("ERROR: --pubkey is not valid hex", file=sys.stderr); return 1
    phase    = getattr(args, "phase_code",      "ugk-substrate")
    juris    = getattr(args, "jurisdiction",    "kernel")
    am       = getattr(args, "authority_model", "trace_only")
    force    = getattr(args, "force",           False)
    # State isolation (deliberate substrate revision): --state-dir governs genesis
    # placement too, not only the SQLite stores. Precedence matches other commands:
    # explicit --state-dir, else UGK_STATE_DIR/ACIS_STATE_DIR env, else package default.
    state_dir = getattr(args, "state_dir", None) \
        or os.environ.get("UGK_STATE_DIR") or os.environ.get("ACIS_STATE_DIR")
    manifest = DeploymentManifest.create(pubkey, phase, juris, am)
    try:
        pub_p, mani_p = write_charter_artifacts(manifest, genesis_dir=state_dir, force=force)
    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr); return 1
    print(json.dumps({
        "manifest_hash":   manifest.manifest_hash,
        "mosaic_root":     manifest.mosaic_root,
        "dimension_id":    manifest.dimension_id,
        "governor_pubkey": manifest.governor_pubkey[:16]+"...",
        "phase_code":      manifest.phase_code,
        "jurisdiction":    manifest.jurisdiction,
        "authority_model": manifest.authority_model,
        "genesis_key_pub": str(pub_p),
        "manifest_path":   str(mani_p),
    }, indent=2))
    print(f"Charter established. Kernel will load identity on next import.", file=sys.stderr)
    return 0


_HELP_DATA = {
    "charter": {
        "summary": "Establish a governance deployment identity (founding constitutional act)",
        "doc": """
  This is the founding constitutional act. It makes an anonymous UGK binary into
  a specific governed deployment by providing the Governor's public key and declaring
  the deployment's type and compliance posture.

  After charter, every session_dkn encodes:
    mosaic_root (WHO)  = SHA-256(--pubkey)
    phase_code  (WHAT) = --phase-code
    session_id  (WHICH)= UUID4 per session
""",
        "params": [
            ("--pubkey <hex>",          "REQUIRED", "",             "Governor Ed25519 public key (64 hex chars). Establishes mosaic_root and dimension_id."),
            ("--phase-code <string>",   "optional", "ugk-substrate","Deployment type identifier. Scopes the governance namespace."),
            ("--jurisdiction <string>", "optional", "kernel",       "Governance domain. Carried on every receipt."),
            ("--authority-model",       "optional", "trace_only",   "Compliance posture: alt_prevention | alt_trace | trace_only | custom"),
            ("--force",                 "optional", "False",        "Overwrite existing genesis artifacts."),
            ("--state-dir <dir>",       "optional", "package genesis/", "Deployment state dir. Governs BOTH the SQLite stores AND genesis artifact placement (GENESIS_KEY.pub, DEPLOYMENT_MANIFEST.json). Without it, genesis writes to the package-adjacent genesis/."),
        ],
        "example": "ugk charter --pubkey ceb70ad0... --phase-code email-governance-v1 --authority-model alt_trace",
    },
    "posture": {"summary": "Show Constitutional Governance Posture (ALT section 11 posture vector)", "params": [], "example": "ugk posture --format json"},
    "health":  {"summary": "Full system health check (chain + posture + optional gate compliance)", "params": [], "example": "ugk health --run-gates structural"},
    "constitution": {"summary": "Show constitutional frame (law_hash, legend_hash, authority model)", "params": [], "example": "ugk constitution --format json"},
    "explain": {"summary": "Explain a concept, gate, invariant, or CSIL integer", "params": [], "example": "ugk explain terminal-outcome-lattice  |  ugk explain LEGEND-S-01  |  ugk explain 3003  |  ugk explain dkn_gate"},
    "keygen":  {"summary": "Generate a fresh Ed25519 keypair", "params": [], "example": "ugk keygen --write-secure /safe/path/key.json"},
    "govern":  {"summary": "Execute a governed operation through the kernel", "params": [], "example": "ugk govern --op crp_evidence --authority system"},
    "status":  {"summary": "Show kernel status snapshot", "params": [], "example": "ugk status"},
    "verify":  {"summary": "Verify receipt chain integrity", "params": [], "example": "ugk verify"},
    "attest":  {"summary": "Return 3+1 hash attestation proof", "params": [], "example": "ugk attest"},
    "authority-model": {"summary": "Show or set the authority model", "params": [], "example": "ugk authority-model"},
    "harden": {"summary": "Establish the Grundnorm read-only protection posture (deliberate, recorded deployment act; sets protected modules to 0o444 and writes a deployment-state establishment record into genesis_dir, which UL-G-01 integrity then verifies against)", "params": [], "example": "ugk harden   |   ugk --state-dir /deploy/state harden"},
}


def _cmd_help(args) -> int:
    """Show help for all verbs or a specific verb."""
    verb = getattr(args, "verb", None)
    if verb and verb in _HELP_DATA:
        h = _HELP_DATA[verb]
        print(f"\nugk {verb} — {h['summary']}")
        if h.get("doc"): print(h["doc"])
        if h.get("params"):
            print("Parameters:")
            for flag, req, default, desc in h["params"]:
                req_str = req if req=="REQUIRED" else f"optional  default: {default!r}"
                print(f"  {flag:<28} {req_str}")
                print(f"  {'':28} {desc}")
        if h.get("example"): print(f"\nExample:\n  {h['example']}\n")
        return 0
    # List all verbs
    print("\nUGK — Universal Governance Kernel\n")
    for v, h in sorted(_HELP_DATA.items()):
        print(f"  ugk {v:<20} {h['summary']}")
    print("\nUse 'ugk help <verb>' for detailed parameter descriptions.\n")
    return 0


def _cmd_authority_model(args) -> int:
    """Show the current authority model or set a new one."""
    from ugk.charter import DeploymentManifest
    fmt = getattr(args, "format", "text")
    set_model = getattr(args, "set_model", None)

    if set_model:
        # B5: governance-posture mutation is a GOVERNED op. It is routed through
        # kernel.execute() so it is gated (per the current authority model), receipted
        # BEFORE the charter-write effect (NBER-1), refusable, and failed-effect-receipted.
        # The previous ungoverned direct write_charter_artifacts(force=True) call is removed.
        intent = getattr(args, "intent", None)
        if not intent or not intent.strip():
            print("ERROR: --intent is required to change the authority model "
                  "(governed mutation; no silent posture change).", file=sys.stderr)
            return 1
        m = DeploymentManifest.load()
        if m is None:
            print("ERROR: No genesis/DEPLOYMENT_MANIFEST.json — run ugk charter first.", file=sys.stderr)
            return 1
        from ugk.charter import write_charter_artifacts
        from ugk.kernel import (
            GateRefusal, GovernanceNotFounded, UndeclaredOp, KernelInternalOp,
            EffectAtomicity,
        )
        import os as _os
        state_dir = getattr(args, "state_dir", None) or _os.environ.get("UGK_STATE_DIR") \
            or _os.environ.get("ACIS_STATE_DIR")
        new_m = DeploymentManifest.create(
            m.governor_pubkey, m.phase_code, m.jurisdiction, set_model
        )
        k = _make_kernel(state_dir)
        try:
            k.execute(
                op="authority_model_set",
                authority=getattr(args, "authority", "cli"),
                parameters={"intent": intent, "old_model": m.authority_model,
                            "new_model": set_model, "new_manifest_hash": new_m.manifest_hash},
                # minimal predicate (B5): explicit intent required; the current authority
                # model determines any additional enforcement (warrant/governor-sig) inside execute().
                gate=(lambda: bool(intent and intent.strip())),
                intent_ref=intent,
                effect=(lambda: write_charter_artifacts(new_m, force=True)), effect_atomicity=EffectAtomicity.NON_ATOMIC,
            )
        except GateRefusal:
            print(json.dumps({"admitted": False, "op": "authority_model_set",
                              "reason": "gate refused (intent required); charter NOT changed"}, indent=2))
            return 1
        except GovernanceNotFounded as e:
            _print_error("governance_not_founded", "authority_model_set", str(e)); return 2
        except UndeclaredOp as e:
            _print_error("undeclared_op", "authority_model_set", str(e)); return 3
        except KernelInternalOp as e:
            _print_error("kernel_internal_op", "authority_model_set", str(e)); return 4
        except Exception as e:
            _print_error("error", "authority_model_set", str(e)); return 5
        print(f"Authority model updated to: {set_model}")
        print(f"New manifest_hash: {new_m.manifest_hash}")
        return 0

    # Show current authority model
    m = DeploymentManifest.load()
    model_id = m.authority_model if m else "undeclared"
    rg = rw = ri = False
    try:
        from ugk.authority.authority_model import AuthorityModel
        presets = {
            "alt_prevention": (True,  True,  True),
            "alt_trace":      (True,  True,  False),
            "trace_only":     (False, False, False),
        }
        if model_id in presets:
            rg, rw, ri = presets[model_id]
    except Exception:
        pass

    if fmt == "json":
        print(json.dumps({
            "model_id":        model_id,
            "require_gate":    rg,
            "require_warrant": rw,
            "require_intent":  ri,
            "source":          "genesis/DEPLOYMENT_MANIFEST.json" if m else "none",
        }, indent=2))
    else:
        print(f"  authority_model:   {model_id}")
        print(f"  require_gate:      {rg}")
        print(f"  require_warrant:   {rw}")
        print(f"  require_intent:    {ri}")
        print(f"  source:            {'genesis/DEPLOYMENT_MANIFEST.json' if m else 'none (run ugk charter)'}")
    return 0

def _cmd_attest(args) -> int:
    """Return a CSH attestation proof (3+1 hash pins + stream hash). Read-only (IEL Invariant D /
    AD-30): binds a mode=ro store + a hydrate-only kernel, so it NEVER creates ugk.db, opens a
    session, or emits receipts. Missing state fails closed with a structured result."""
    import os
    from pathlib import Path as _P
    from ugk.kernel import GovernanceKernel
    from ugk.storage.store import UGKReceiptStore
    from ugk.integrity.readonly import ReadOnlyGuard, ReadOnlyViolation
    state_dir = getattr(args, "state_dir", None)
    env_dir = state_dir or os.environ.get("UGK_STATE_DIR") or os.environ.get("ACIS_STATE_DIR")
    db_path = str(_P(env_dir) / "ugk.db") if env_dir else ":memory:"
    try:
        with ReadOnlyGuard(db_path, name="attest"):
            store = UGKReceiptStore(db_path=db_path, read_only=True)
            k = GovernanceKernel(store=store, authority="cli")
            k.hydrate_readonly()          # pure compute + load-only CSH; NO writes, NO session
            snap = k.snapshot()
            attestation = {
                "stream_hash":         snap["stream_hash"],
                "hash_verified":       snap["hash_verified"],
                "law_hash":            snap.get("law_hash", ""),
                "csh_finality_hash":   snap.get("csh_finality_hash", ""),
                "csh_quorum_achieved": snap.get("csh_quorum_achieved", False),
                "mosaic_root":         snap.get("mosaic_root", ""),
                "dimension_id":        snap.get("dimension_id", ""),
                "governance_status":   snap.get("governance_status", ""),
                "mode":                "read-only",
            }
    except ReadOnlyViolation as e:
        print(json.dumps({"hash_verified": False, "mode": "read-only",
                          "error": "state_absent_or_unreadable", "detail": str(e)}, indent=2))
        return 2
    print(json.dumps(attestation, indent=2))
    return 0 if snap["hash_verified"] else 1


def _cmd_harden(args) -> int:
    """ugk harden — ESTABLISH the Grundnorm read-only protection posture.

    Establishment is a deliberate, recorded deployment act, distinct from integrity
    (which UL-G-01 verifies). It does two things:
      1. set every registry-resolved Grundnorm module to read-only (0o444);
      2. write a deployment-state establishment record (GRUNDNORM_POSTURE.json) into
         genesis_dir() — NOT into the package. pip strips file modes (0o444 -> 0o644)
         but copies package data, so a packaged marker would collapse establishment
         back into integrity and re-create false-FAILs on vanilla installs.

    After this, "posture established" is a first-class, observable proposition that the
    conformance establishment check and UL-G-01 (integrity) read from genesis_dir().
    Genesis resolution honors --state-dir / UGK_GENESIS_DIR, so harden and the gates
    agree on one deployment-state location.
    """
    import os
    import stat
    import time
    from ugk.module_registry import grundnorm_paths, GRUNDNORM_MODULES
    from ugk._paths import genesis_dir

    paths = grundnorm_paths()
    for p in paths:
        mode = os.stat(p).st_mode
        os.chmod(p, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

    gdir = genesis_dir()
    gdir.mkdir(parents=True, exist_ok=True)
    record = {
        "posture": "grundnorm_readonly",
        "established": True,
        "expected_mode": "0o444",
        "modules": list(GRUNDNORM_MODULES),
        "module_paths": [str(p) for p in paths],
        # Observability only; never hashed into any frame/continuity artifact and never
        # consulted by the establishment check (which keys on posture + established).
        "established_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    rec_path = gdir / "GRUNDNORM_POSTURE.json"
    rec_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    print(json.dumps({
        "established": True,
        "posture": "grundnorm_readonly",
        "modules_protected": len(paths),
        "expected_mode": "0o444",
        "record": str(rec_path),
    }, indent=2))
    print(f"Grundnorm read-only posture established: {len(paths)} modules set to 0o444; "
          f"establishment record written to {rec_path}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ugk",
        description="Universal Governance Kernel CLI",
    )
    p.add_argument("--state-dir", dest="state_dir", default=None,
                   help="UGK state directory (overrides UGK_STATE_DIR env var)")
    sub = p.add_subparsers(dest="command", required=True)

    # govern
    gov = sub.add_parser("govern", help="Execute a governed operation")
    gov.add_argument("--intent",    required=True, help="Governance intent (e.g. orient, verify)")
    gov.add_argument("--subject",   required=True, help="Subject of the governance action")
    gov.add_argument("--authority", default="cli",        help="Caller authority")
    gov.add_argument("--op",        default="crp_evidence", help="Governance op name")

    # status
    sub.add_parser("status", help="Show kernel status snapshot")

    # keygen
    keygen_p=sub.add_parser("keygen", help="Generate a fresh Ed25519 keypair")
    keygen_p.add_argument("--show-private",action="store_true",help="Print full keypair (warning on stderr)")
    keygen_p.add_argument("--write-secure",metavar="PATH",help="Write keypair JSON to PATH at 0o600 on POSIX (must not exist); fails closed on Windows (no user-only ACLs in this stdlib-only build)")
    keygen_p.add_argument("--intent",metavar="REASON",help="Optional creation intent recorded in the provenance artifact")

    # verify
    sub.add_parser("verify", help="Verify the receipt chain integrity")
    am_p = sub.add_parser("authority-model", help="Show or update the authority model")
    am_p.add_argument("--set", dest="set_model", metavar="MODEL_ID",
                      choices=["alt_prevention","alt_trace","trace_only","custom"],
                      help="Update authority model in deployment manifest (requires --intent)")
    am_p.add_argument("--intent", dest="intent", metavar="TEXT",
                      help="Explicit intent for a posture change (required with --set)")
    am_p.add_argument("--format", choices=["text","json"], default="text")
    chr_p = sub.add_parser("charter", help="Establish governance deployment identity")
    chr_p.add_argument("--pubkey",         required=True,  metavar="HEX")
    chr_p.add_argument("--phase-code",     default="ugk-substrate", metavar="STR")
    chr_p.add_argument("--jurisdiction",   default="kernel",        metavar="STR")
    chr_p.add_argument("--authority-model",default="trace_only",    metavar="PRESET",
                       choices=["alt_prevention","alt_trace","trace_only","custom"])
    chr_p.add_argument("--force", action="store_true")
    hlp_p = sub.add_parser("help", help="Show help for all verbs or a specific verb")
    hlp_p.add_argument("verb", nargs="?", default=None, metavar="VERB")
    pos_p=sub.add_parser("posture",help="Show Constitutional Governance Posture")
    pos_p.add_argument("--state-dir",metavar="PATH")
    pos_p.add_argument("--format",choices=["text","json"],default="text")
    hlth_p=sub.add_parser("health",help="Full system health check")
    hlth_p.add_argument("--state-dir",metavar="PATH")
    hlth_p.add_argument("--run-gates",metavar="GROUP",
                        help="Run gate group: all|structural|unit|integration|conformance")
    hlth_p.add_argument("--format",choices=["text","json"],default="text")
    const_p=sub.add_parser("constitution", help="Show constitutional frame")
    const_p.add_argument("--state-dir",metavar="PATH",help="State directory")
    const_p.add_argument("--format",choices=["text","json"],default="text")
    expl_p=sub.add_parser("explain", help="Explain a concept, gate, invariant, or CSIL integer")
    expl_p.add_argument("name",help="Concept ID, invariant ID, gate name, or CSIL integer")

    # attest
    sub.add_parser("attest", help="Return 3+1 hash attestation proof")
    sub.add_parser("harden", help="Establish the Grundnorm read-only protection posture")
    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    """CLI entry point.  Returns exit code; does NOT call sys.exit()."""
    import os
    parser = _build_parser()
    args = parser.parse_args(argv)

    # State isolation (Option X): make --state-dir end-to-end. Governor identity loads at
    # ugk.kernel IMPORT time from genesis_dir(), which honors UGK_GENESIS_DIR. cli.py
    # imports the kernel lazily INSIDE command handlers, so setting the env here — after
    # parse_args, before dispatch — is seen by that import. This makes a later
    # `ugk --state-dir DIR govern/verify` load genesis from DIR (the read side), matching
    # `charter --state-dir DIR` (the write side). Precedence preserved: an already-set
    # UGK_GENESIS_DIR wins (explicit env beats the flag); identity stays immutable-at-import
    # (no reload — we set the resolution source before the one and only import).
    _sd = getattr(args, "state_dir", None) or os.environ.get("UGK_STATE_DIR") \
        or os.environ.get("ACIS_STATE_DIR")
    if _sd and not os.environ.get("UGK_GENESIS_DIR"):
        os.environ["UGK_GENESIS_DIR"] = _sd

    dispatch = {
        "govern": _cmd_govern,
        "status": _cmd_status,
        "keygen": _cmd_keygen,
        "verify": _cmd_verify,
        "attest": _cmd_attest,
        "charter": _cmd_charter,
        "authority-model": _cmd_authority_model,
        "help": _cmd_help,
        "posture": _cmd_posture,
        "health": _cmd_health,
        "constitution": _cmd_constitution,
        "explain": _cmd_explain,
        "harden": _cmd_harden,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
