"""ugk/cgp/dispatch.py — CGP universal evidence dispatcher (additive substrate).

    dispatch_capability_evidence(*, registry, scope, runner=None,
                                 selector="full", store=None,
                                 gate_runner=None) -> CapabilityEvidenceLedger

Turns capability CLAIMS (the ESA REGISTRY) into a COMPLETE governed evidence
LEDGER. Every IN-SCOPE capability ends with EXACTLY ONE terminal verdict drawn
from the EXISTING seven-state EvidenceArtifact vocabulary
(PROVEN / FAIL / GAP / WAIVED / BY-CONSTRUCTION / NOT-RUN / ERROR, CTR-S-03);
every registry capability is either scored or VISIBLY dispositioned
(out_of_scope / waivers). Nothing is silently skipped; nothing defaults to
PROVEN.

This is EVIDENCE EXECUTION, NOT a workflow engine: it decides nothing about
WHICH capabilities a consumer should hold, in WHAT ORDER business operations
run, or WHAT TO DO about a FAIL/GAP/WAIVED. That is consumer workflow.

Ratified decisions (first implementation):
  * reuse the existing 7-verdict EvidenceArtifact vocabulary (no new enum);
  * content-addressed CapabilityEvidenceLedger WITHOUT a chain receipt
    (deterministic substrate first; no new effect-class decision);
  * no new invariant (prospective CGP-S-04 DEFERRED); no law move.

Scope of THIS increment (declared explicitly — no silent semantics):
  * gate-suite bindings whose UGK realization names a runnable ugk.conformance
    gate are EXECUTED -> PROVEN / FAIL / ERROR.
  * scenario-sweep / coverage-map / interpretive-pack bindings are RESOLVED and
    dispositioned NOT-RUN (binding exists; live execution is a later increment).
  * caps with an explicit by-construction marker -> BY-CONSTRUCTION.
  * caps with no UGK-resolvable instrument -> GAP (this is the SB-2 cap-gap
    census; closing gaps is cap-completion work).

Determinism: ledger_hash is SHA-256 over canonical_json of the DETERMINISTIC
body only; the interpretive layer and per-scenario timing are recorded (where
applicable) but EXCLUDED from the hash; capabilities are processed in canonical
sorted-key order; no wall-clock enters the hashed body.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

from ugk.cgp.runner.types import EvidenceArtifact, InterpretiveEvidencePack
from ugk.storage.binding import canonical_json

# ---------------------------------------------------------------------------
# Vocabulary (reused verbatim from EvidenceArtifact / CTR-S-03 — NOT redefined)
# ---------------------------------------------------------------------------
VERDICTS: Tuple[str, ...] = (
    "PROVEN", "FAIL", "GAP", "WAIVED", "BY-CONSTRUCTION", "NOT-RUN", "ERROR",
)

# Selector vocabulary. Every selector preserves no-silent-skip: an in-scope cap
# that a selector does not RUN is recorded NOT-RUN, never omitted.
SELECTORS: Tuple[str, ...] = ("core", "live", "full", "custom")

# evidence_class values the in-process ("live") lane is willing to attempt.
_LIVE_CLASSES = ("gate-suite", "scenario-sweep", "receipt-aggregation")
# evidence_class values resolved-but-NOT-executed in THIS increment. receipt-
# aggregation is EXPLICITLY deferred here (-> NOT-RUN), not an accidental GAP;
# implementing receipt-backed aggregation is a later increment.
_DEFERRED_CLASSES = ("scenario-sweep", "coverage-map", "interpretive-pack",
                     "receipt-aggregation")
# every evidence_class the dispatcher recognizes; anything else -> explicit GAP.
_KNOWN_CLASSES = ("gate-suite", "scenario-sweep", "coverage-map",
                  "interpretive-pack", "receipt-aggregation")
# explicit by-construction markers (declared convention; see module docstring).
_BY_CONSTRUCTION_MARKERS = ("implicit", "by construction", "by-construction",
                            "substrate level", "structural")


def verdict_vocabulary_matches_evidence_artifact() -> bool:
    """True iff VERDICTS aliases the EvidenceArtifact.verdict Literal EXACTLY.

    Proves the dispatcher did not invent or drift the governed vocabulary.
    """
    import typing
    try:
        hints = typing.get_type_hints(EvidenceArtifact)
        allowed = set(typing.get_args(hints["verdict"]))
    except Exception:
        return False
    return allowed == set(VERDICTS)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WaiverRecord:
    """An explicit waiver: a cap not run, by recorded authority + reason."""
    cap_id: str
    authority: str
    reason: str
    evidence_ref: str = ""


@dataclass(frozen=True)
class DispatchScope:
    """Consumer scope handed to the dispatcher.

    in_scope : None  -> every registry cap is in scope.
               frozenset[str] -> only these cap ids are in scope; the rest are
               recorded out_of_scope (visible, never omitted).
    waivers  : tuple[WaiverRecord] -> in-scope caps explicitly waived.
    custom_set : frozenset[str] | None -> for selector="custom", the cap ids to
               RUN; in-scope caps not in the set are recorded NOT-RUN.
    """
    scope_id: str
    in_scope: Optional[frozenset] = None
    waivers: Tuple[WaiverRecord, ...] = ()
    custom_set: Optional[frozenset] = None
    jurisdiction: str = ""


@dataclass(frozen=True)
class CapabilityEvidenceLedger:
    """Content-addressed evidence ledger. NO chain receipt (first increment)."""
    registry_version: str
    scope_id: str
    selector: str
    runner_id: str
    store_head: str
    artifacts: Tuple[EvidenceArtifact, ...]      # one per IN-SCOPE cap
    out_of_scope: Tuple[str, ...]
    waivers: Tuple[WaiverRecord, ...]
    interpretive: Tuple[InterpretiveEvidencePack, ...]  # recorded, NOT hashed
    gaps: Tuple[str, ...]
    ledger_hash: str

    def deterministic_body(self) -> dict:
        return _ledger_body(
            self.registry_version, self.scope_id, self.selector,
            self.runner_id, self.store_head, self.artifacts,
            self.out_of_scope, self.waivers, self.gaps,
        )

    def verify_hash(self) -> bool:
        return self.ledger_hash == _hash_body(self.deterministic_body())

    def verdict_counts(self) -> dict:
        out: dict = {v: 0 for v in VERDICTS}
        for a in self.artifacts:
            out[a.verdict] = out.get(a.verdict, 0) + 1
        return out


# ---------------------------------------------------------------------------
# Deterministic serialization + hashing
# ---------------------------------------------------------------------------
def _artifact_body(a: EvidenceArtifact) -> dict:
    # scenario_result and instrument timing are EXCLUDED from the hash (wall
    # clock / store-state, already pinned by store_head). The verdict + details
    # carry the deterministic outcome.
    return {
        "invariant": a.invariant,
        "verdict": a.verdict,
        "evidence_class": a.evidence_class,
        "details": a.details,
        "instrument_exit": a.instrument_exit,
    }


def _waiver_body(w: WaiverRecord) -> dict:
    return {"cap_id": w.cap_id, "authority": w.authority,
            "reason": w.reason, "evidence_ref": w.evidence_ref}


def _ledger_body(registry_version, scope_id, selector, runner_id, store_head,
                 artifacts, out_of_scope, waivers, gaps) -> dict:
    return {
        "registry_version": registry_version,
        "scope_id": scope_id,
        "selector": selector,
        "runner_id": runner_id,
        "store_head": store_head,
        "artifacts": [_artifact_body(a) for a in artifacts],
        "out_of_scope": list(out_of_scope),
        "waivers": [_waiver_body(w) for w in waivers],
        "gaps": list(gaps),
    }


def _hash_body(body: dict) -> str:
    cj = canonical_json(body)
    if isinstance(cj, str):
        cj = cj.encode("utf-8")
    return hashlib.sha256(b"CGP-LEDGER-v1" + cj).hexdigest()


# ---------------------------------------------------------------------------
# Binding resolution helpers
# ---------------------------------------------------------------------------
def _ugk_realization(cap) -> Optional[dict]:
    if not isinstance(cap, dict):
        return None
    reals = cap.get("realizations")
    if not isinstance(reals, dict):
        return None
    return reals.get("UGK")


def _primary_evidence_class(cap: dict) -> str:
    if not isinstance(cap, dict):
        return ""
    ugk = _ugk_realization(cap)
    if isinstance(ugk, dict) and ugk.get("evidence_class"):
        return ugk["evidence_class"]
    realizations = cap.get("realizations")
    if isinstance(realizations, dict):
        for key in sorted(realizations):
            r = realizations[key]
            if isinstance(r, dict) and r.get("evidence_class"):
                return r["evidence_class"]
    return ""


def _by_construction_marker(cap, ugk: Optional[dict]) -> Optional[str]:
    if not isinstance(cap, dict):
        return None
    haystacks = []
    if isinstance(ugk, dict):
        haystacks += [str(ugk.get("gate", "")), str(ugk.get("notes", ""))]
    haystacks += [str(cap.get("deterministic_layer", "")), str(cap.get("notes", ""))]
    blob = " ".join(haystacks).lower()
    for m in _BY_CONSTRUCTION_MARKERS:
        if m in blob:
            return m
    return None


_GATE_TOKEN = re.compile(r"[A-Za-z0-9_]+_gate")


def resolve_gate_name(realization: dict) -> Optional[str]:
    """Return the first ugk.conformance.*_gate module named by the realization
    that actually exists (side-effect-free existence check), else None."""
    text = " ".join(str(realization.get(k, "")) for k in ("gate", "evidence", "notes"))
    for tok in _GATE_TOKEN.findall(text):
        if importlib.util.find_spec("ugk.conformance." + tok) is not None:
            return tok
    return None


# SB-2a: posture-aware gate execution. Some conformance gates (e.g. authority_model_gate,
# application_ops_gate) require a FOUNDED governance posture and raise GovernanceNotFounded
# when invoked against an unfounded tree. An already-imported interpreter cannot adopt a
# founding, so such a gate is re-run in a FRESH interpreter under an ISOLATED, TEMPORARY
# conformance-fixture founding (the same founding verify_release / run_gates_batch establish).
# Only the gate's INVOCATION POSTURE changes: the verdict is still the gate's own (ok, detail);
# a true failing gate still returns FAIL; a missing/broken gate still raises -> ERROR; the
# temporary genesis is a throwaway dir (never the repo genesis/, via UGK_GENESIS_DIR) founded
# with the PUBLISHED dev fixture key and removed afterwards (no persistent key material).
_POSTURE_RUN_SRC = (
    "import sys, json, importlib\n"
    "from ugk._paths import genesis_dir\n"
    "g = genesis_dir(); g.mkdir(parents=True, exist_ok=True)\n"
    "from ugk.conformance._fixture import DEV_FIXTURE_PRIVKEY, fixture_pubkey\n"
    "from ugk.charter import DeploymentManifest, write_charter_artifacts\n"
    "manifest = DeploymentManifest.create(fixture_pubkey(), 'conformance-fixture', 'conformance', 'trace_only')\n"
    "write_charter_artifacts(manifest, force=False)\n"
    "(g / 'GENESIS_PRIVKEY.hex').write_text(DEV_FIXTURE_PRIVKEY + '\\n')\n"
    "m = importlib.import_module('ugk.conformance.' + sys.argv[1])\n"
    "ok, detail = m.run()\n"
    "sys.stdout.write('CGP_POSTURE_RESULT:' + json.dumps([bool(ok), str(detail)]) + '\\n')\n"
)


def _run_gate_under_temp_founding(gate_name: str) -> Tuple[bool, str]:
    """Run a posture-dependent gate in a fresh interpreter under an isolated, temporary
    conformance-fixture founding. Returns the gate's own (ok, detail); raises if the gate
    cannot be run cleanly even under founding (-> recorded as ERROR by the caller)."""
    import os, sys, json, tempfile, shutil, subprocess
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tmp = tempfile.mkdtemp(prefix="cgp-posture-")
    try:
        env = dict(os.environ)
        env["UGK_GENESIS_DIR"] = tmp
        env["PYTHONHASHSEED"] = "0"
        env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run([sys.executable, "-c", _POSTURE_RUN_SRC, gate_name],
                              capture_output=True, text=True, env=env, cwd=repo_root, timeout=300)
        for ln in proc.stdout.splitlines():
            if ln.startswith("CGP_POSTURE_RESULT:"):
                ok, detail = json.loads(ln[len("CGP_POSTURE_RESULT:"):])
                return bool(ok), str(detail)
        tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ("exit=%d" % proc.returncode)
        raise RuntimeError("posture-run:no-result:" + tail)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _default_gate_runner(gate_name: str) -> Tuple[bool, str]:
    try:
        mod = importlib.import_module("ugk.conformance." + gate_name)
        ok, detail = mod.run()
        return bool(ok), str(detail)
    except Exception as e:  # noqa: BLE001
        # SB-2a: ONLY a missing-founding posture error is retried under a temporary founding;
        # every other exception propagates so a missing/broken gate is still recorded ERROR.
        if type(e).__name__ == "GovernanceNotFounded":
            return _run_gate_under_temp_founding(gate_name)
        raise


# ---------------------------------------------------------------------------
# Planning + selection
# ---------------------------------------------------------------------------
def _selected(cap_id: str, cap: dict, selector: str, scope: DispatchScope) -> bool:
    if selector == "full":
        return True
    if selector == "custom":
        return scope.custom_set is not None and cap_id in scope.custom_set
    if selector == "core":
        ugk = _ugk_realization(cap)
        return (isinstance(cap, dict) and cap.get("class") == "I" and ugk is not None
                and bool(ugk.get("deterministic"))
                and ugk.get("evidence_class") == "gate-suite")
    if selector == "live":
        return _primary_evidence_class(cap) in _LIVE_CLASSES
    return False


def _plan(cap_id: str, cap: dict, scope: DispatchScope, selector: str,
          waiver_by_cap: dict) -> str:
    if scope.in_scope is not None and cap_id not in scope.in_scope:
        return "out_of_scope"
    if cap_id in waiver_by_cap:
        return "waived"
    if not _selected(cap_id, cap, selector, scope):
        return "not_run_selector"
    return "in_scope"


# ---------------------------------------------------------------------------
# Execution by evidence class
# ---------------------------------------------------------------------------
def _resolve_and_execute(cap_id: str, cap: dict,
                         gate_runner: Callable[[str], Tuple[bool, str]],
                         ) -> Tuple[str, str, str]:
    # Malformed entries fail closed by RULE (explicit GAP/ERROR, never a crash).
    if not isinstance(cap, dict):
        return "ERROR", "malformed:cap-not-dict", ""
    reals = cap.get("realizations")
    if reals is not None and not isinstance(reals, dict):
        return "GAP", "malformed:realizations-not-dict", ""
    ugk = _ugk_realization(cap)
    if ugk is not None and not isinstance(ugk, dict):
        return "GAP", "malformed:ugk-realization-not-dict", ""

    ev_class = _primary_evidence_class(cap)
    marker = _by_construction_marker(cap, ugk)
    gate_name = resolve_gate_name(ugk) if ugk else None

    # Strongest evidence: a runnable, named gate -> execute it.
    # details are NORMALIZED (deterministic): the gate's free-text detail is NOT
    # hashed (it may carry paths/timing/exception reprs); verdict + gate name +
    # ok-bool are the deterministic outcome.
    if gate_name is not None:
        try:
            ok, _raw = gate_runner(gate_name)
        except Exception as e:  # harness/instrument fault, NOT a capability FAIL
            return "ERROR", f"gate:{gate_name}:error:{type(e).__name__}", ev_class
        return ("PROVEN" if ok else "FAIL",
                f"gate:{gate_name}:{'ok' if ok else 'fail'}", ev_class)

    if marker is not None:
        return "BY-CONSTRUCTION", f"by-construction:{marker}", ev_class

    if ugk is None:
        return "GAP", "gap:no-ugk-realization", ev_class

    if ev_class in _DEFERRED_CLASSES:
        return "NOT-RUN", f"not-run:deferred:{ev_class}", ev_class

    if ev_class == "gate-suite":
        return "GAP", "gap:no-runnable-ugk-gate", ev_class

    if ev_class == "" or ev_class not in _KNOWN_CLASSES:
        return "GAP", f"gap:unknown-evidence-class:{ev_class or 'missing'}", ev_class

    return "GAP", f"gap:unresolved:{ev_class}", ev_class


def _mk_artifact(cap_id: str, verdict: str, detail: str, ev_class: str) -> EvidenceArtifact:
    return EvidenceArtifact(invariant=cap_id, verdict=verdict,
                            evidence_class=ev_class, details=detail)


# ---------------------------------------------------------------------------
# The dispatcher
# ---------------------------------------------------------------------------
def _realization_projection(r) -> dict:
    if not isinstance(r, dict):
        return {"_malformed": True}
    return {k: r.get(k) for k in ("evidence_class", "gate", "deterministic",
                                  "status", "notes")}


def _registry_projection(registry: dict) -> dict:
    """A deterministic projection of EVERY field the dispatcher uses for
    planning/resolution, so a changed binding (same key set) changes the
    registry_version."""
    proj: dict = {}
    for cid in sorted(registry.keys()):
        cap = registry[cid]
        if not isinstance(cap, dict):
            proj[cid] = {"_malformed": True}
            continue
        reals = cap.get("realizations")
        if isinstance(reals, dict):
            rp = {rk: _realization_projection(reals[rk]) for rk in sorted(reals)}
        else:
            rp = {"_malformed": reals is not None}
        proj[cid] = {
            "class": cap.get("class"),
            "realizations": rp,
            "primary_evidence_class": _primary_evidence_class(cap),
            "deterministic_layer": cap.get("deterministic_layer"),
            "notes": cap.get("notes"),
            "interpretive_template": cap.get("interpretive_evidence_template") is not None,
        }
    return proj


def _registry_version(registry: dict) -> str:
    proj = _registry_projection(registry)
    cj = canonical_json(proj)
    if isinstance(cj, str):
        cj = cj.encode("utf-8")
    return f"caps:{len(registry)}:{hashlib.sha256(cj).hexdigest()[:12]}"


def _store_head(store) -> str:
    if store is None:
        return "no-store"
    try:
        return store.stream_hash()
    except Exception:
        return "no-store"


def _runner_id(runner) -> str:
    if runner is None:
        return "no-runner"
    return type(runner).__name__


# ---------------------------------------------------------------------------
# D_cap capability-evidence commitment (AD-52 / Lane 4b) — PURE binding helper.
#
# Produces the capability-evidence commitment over a CapabilityEvidenceLedger for
# body-commitment (UGK-BODY-v3). It is NON-LAUNDERING and NOT decision-authoritative:
#   * fails closed on a ledger that does not self-verify (never binds a corrupt ledger);
#   * records each of the seven verdicts FAITHFULLY (no collapse, no upgrade);
#   * NEVER synthesizes PROVEN (external / Navigator-realized evidence cannot become
#     UGK PROVEN by mere existence — PROVEN appears only if the ledger artifact is PROVEN);
#   * keeps WAIVED AUTHORITY-MARKED, separate from the verdict census;
#   * keeps GAP / ERROR / NOT-RUN / BY-CONSTRUCTION distinct (closed vocabulary, CTR-S-03).
# This commitment is recorded + verified but does NOT enter conjunctive_refusal_monotone_v1
# and does NOT affect ADMIT/REFUSE (it is a committed candidate decision surface, not an
# aggregating one). Decision-authority is a later, separately-authorized enforcement increment.
# ---------------------------------------------------------------------------
CAPABILITY_EVIDENCE_MODEL_ID = "capability_evidence_model_v1"


def capability_evidence_commitment(ledger) -> dict:
    if not ledger.verify_hash():
        raise ValueError("capability-ledger-self-verify-failed")  # fail closed
    census = {v: [] for v in VERDICTS}
    for a in ledger.artifacts:
        if a.verdict not in census:
            raise ValueError("unknown-verdict:%s" % a.verdict)   # closed vocabulary
        census[a.verdict].append(a.invariant)                    # faithful, never remapped
    census = {v: sorted(ids) for v, ids in census.items()}
    waivers = sorted(({"cap_id": w.cap_id, "authority": w.authority} for w in ledger.waivers),
                     key=lambda d: (d["cap_id"], d["authority"]))  # authority-marked
    binding_body = {
        "ledger_hash": ledger.ledger_hash,
        "registry_version": ledger.registry_version,
        "scope_id": ledger.scope_id,
        "selector": ledger.selector,
        "verdict_census": census,
        "waivers": waivers,
        "gaps": sorted(ledger.gaps),
        "out_of_scope": sorted(ledger.out_of_scope),
    }
    h_cap = hashlib.sha256(b"UGK-CAP-v1" + canonical_json(binding_body)).hexdigest()
    return {
        "h_cap": h_cap,
        "capability_evidence_model_id": CAPABILITY_EVIDENCE_MODEL_ID,
        "ledger_hash": ledger.ledger_hash,
        "registry_version": ledger.registry_version,
        "scope_id": ledger.scope_id,
    }


def dispatch_capability_evidence(*, registry: dict, scope: DispatchScope,
                                 runner=None, selector: str = "full",
                                 store=None,
                                 gate_runner: Optional[Callable[[str], Tuple[bool, str]]] = None,
                                 ) -> CapabilityEvidenceLedger:
    if selector not in SELECTORS:
        raise ValueError(f"unknown selector: {selector!r} (allowed: {SELECTORS})")
    # Waivers fail closed: each needs authority+reason; no duplicate cap; the
    # cap must exist in the registry. (No silent acceptance of bad waivers.)
    seen = set()
    for w in (scope.waivers or ()):
        if not w.authority or not w.reason:
            raise ValueError(f"waiver for {w.cap_id!r} missing authority/reason")
        if w.cap_id in seen:
            raise ValueError(f"duplicate waiver for cap {w.cap_id!r}")
        seen.add(w.cap_id)
        if w.cap_id not in registry:
            raise ValueError(f"waiver for unknown cap {w.cap_id!r}")
    if gate_runner is None:
        gate_runner = _default_gate_runner

    waiver_by_cap = {w.cap_id: w for w in (scope.waivers or ())}

    artifacts = []
    out_of_scope = []
    gaps = []

    for cap_id in sorted(registry.keys()):           # canonical order
        cap = registry[cap_id]
        disposition = _plan(cap_id, cap, scope, selector, waiver_by_cap)

        if disposition == "out_of_scope":
            out_of_scope.append(cap_id)
            continue
        if disposition == "waived":
            w = waiver_by_cap[cap_id]
            artifacts.append(_mk_artifact(
                cap_id, "WAIVED",
                f"waived:{w.authority}:{w.reason}",
                _primary_evidence_class(cap)))
            continue
        if disposition == "not_run_selector":
            artifacts.append(_mk_artifact(
                cap_id, "NOT-RUN",
                f"not-run:selector:{selector}",
                _primary_evidence_class(cap)))
            continue

        # in_scope -> resolve binding + execute by evidence class
        verdict, detail, ev_class = _resolve_and_execute(cap_id, cap, gate_runner)
        artifacts.append(_mk_artifact(cap_id, verdict, detail, ev_class))
        if verdict == "GAP":
            gaps.append(cap_id)

    artifacts_t = tuple(artifacts)
    out_of_scope_t = tuple(sorted(out_of_scope))
    waivers_t = tuple(sorted(scope.waivers or (),
                             key=lambda w: (w.cap_id, w.authority, w.reason, w.evidence_ref)))
    gaps_t = tuple(sorted(gaps))

    body = _ledger_body(
        _registry_version(registry), scope.scope_id, selector,
        _runner_id(runner), _store_head(store),
        artifacts_t, out_of_scope_t, waivers_t, gaps_t)
    ledger_hash = _hash_body(body)

    return CapabilityEvidenceLedger(
        registry_version=_registry_version(registry),
        scope_id=scope.scope_id, selector=selector,
        runner_id=_runner_id(runner), store_head=_store_head(store),
        artifacts=artifacts_t, out_of_scope=out_of_scope_t,
        waivers=waivers_t, interpretive=(), gaps=gaps_t,
        ledger_hash=ledger_hash)


__all__ = [
    "VERDICTS", "SELECTORS", "WaiverRecord", "DispatchScope",
    "CapabilityEvidenceLedger", "dispatch_capability_evidence",
    "resolve_gate_name", "verdict_vocabulary_matches_evidence_artifact",
]
