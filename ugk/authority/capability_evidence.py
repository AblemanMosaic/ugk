"""ugk/capability_evidence.py — consumer-side scope + evidence-map helper.

Registry-agnostic helper that lets a CONSUMER of UGK declare:
  - which capabilities (from some external registry) apply to it
  - how each applicable capability is evidenced (cap → named gate)
  - the determinism / interpretation character of that evidence

The helper VERIFIES claimed bindings resolve (gates exist), reports
DRIFT against a registry's declared cap list, and SUMMARIZES by status
class. It deliberately:

  - does NOT host any registry (ESA or otherwise) inside UGK
  - does NOT know about ESA / AIS / EVS / COP / CTR / SRSA specifically
  - does NOT execute the gates (UGK's existing gate machinery does that)
  - does NOT assert that any consumer SHOULD address any cap
  - does NOT pretend every capability can become deterministic

Status vocabulary (six terms covering the declared/evidenced/implemented/
interpreted/out-of-scope/aspirational distinctions):

  DONE          implemented + evidenced + verifying
  PARTIAL       implemented for declared subset; gate present
  FUTURE        planned realization; no gate yet
  OUT_OF_SCOPE  explicitly waived for this consumer
  ASPIRATIONAL  declared in registry; no realization path
  UNDECLARED    registry mentions; consumer hasn't addressed

For Class I (deterministic gate-bound) capabilities, set
deterministic=True. For Class II (receipt-backed interpretive), set
deterministic=False and use scope_notes to document the interpretive
boundary. For Class III/IV, leave deterministic=None.

Public surface:
    CapabilityClaim       dataclass for a single cap claim
    STATUS_VOCAB          canonical six-term tuple
    load_scope(module)    parse a consumer SCOPE dict into claims
    verify_evidence_map(claims, gates_dir)
                          assert DONE/PARTIAL claims have a gate file present
    diff_against_registry(claims, registry_caps)
                          report drift between consumer scope and registry
    summarize(claims)     count claims by status and determinism
    status_vocabulary()   introspection helper (returns STATUS_VOCAB)

Companion templates under ugk/templates/capability_evidence/ show the
expected SCOPE dict shape and a Markdown scope-doc skeleton.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


STATUS_VOCAB: tuple[str, ...] = (
    "DONE",          # implemented + evidenced + verifying
    "PARTIAL",       # implemented for declared subset; gate present
    "FUTURE",        # planned realization; no gate yet
    "OUT_OF_SCOPE",  # explicitly waived for this consumer
    "ASPIRATIONAL",  # declared in registry; no realization path
    "UNDECLARED",    # registry mentions; consumer hasn't addressed
)

# Statuses that REQUIRE a resolvable gate binding for verify_evidence_map.
# Other statuses are intentionally not asserted (honest-absent for
# FUTURE/OUT_OF_SCOPE/ASPIRATIONAL/UNDECLARED).
_GATE_REQUIRED_STATUSES = frozenset({"DONE", "PARTIAL"})


@dataclass(frozen=True)
class CapabilityClaim:
    """A consumer's claim about a single capability.

    Fields:
      cap_id         registry identifier (str — e.g. "Cap-22", "T0-03")
      name           human-readable name (matches registry)
      status         one of STATUS_VOCAB
      gate           named gate module identifier, or None for
                     FUTURE / OUT_OF_SCOPE / ASPIRATIONAL / UNDECLARED
      deterministic  True for Class I (pure gate evidence);
                     False for Class II (receipt-backed interpretive);
                     None for Class III/IV / OUT_OF_SCOPE / ASPIRATIONAL
      scope_notes    optional free-text describing partial scope,
                     interpretation boundary, or waiver rationale
    """
    cap_id: str
    name: str
    status: str
    gate: Optional[str] = None
    deterministic: Optional[bool] = None
    scope_notes: str = ""


def status_vocabulary() -> tuple[str, ...]:
    """Return the canonical STATUS_VOCAB tuple. Introspection helper for
    consumers writing new scope documents — parallels
    ugk.cgp.required_attributes()."""
    return STATUS_VOCAB


def load_scope(scope_module) -> tuple[CapabilityClaim, ...]:
    """Load consumer scope from a Python module exporting a SCOPE dict.

    Accepts either:
      - a module object (with .SCOPE attribute)
      - a dotted module path (str) to be imported

    Each SCOPE entry must have at least 'name' and 'status'. Other
    fields default to the CapabilityClaim defaults.

    Raises:
      ValueError if any entry has an unknown status, missing required
        field, or a malformed type. Drift between consumer scope and a
        registry is NOT checked here — use diff_against_registry().
    """
    if isinstance(scope_module, str):
        import importlib
        scope_module = importlib.import_module(scope_module)
    if not hasattr(scope_module, "SCOPE"):
        raise ValueError(
            f"capability_evidence.load_scope: {scope_module!r} has no "
            f"SCOPE attribute (expected dict[cap_id, entry])"
        )
    raw = scope_module.SCOPE
    if not isinstance(raw, dict):
        raise ValueError(
            f"capability_evidence.load_scope: SCOPE must be a dict, "
            f"got {type(raw).__name__}"
        )

    claims = []
    for cap_id, entry in raw.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"SCOPE[{cap_id!r}] must be a dict, got "
                f"{type(entry).__name__}"
            )
        for required in ("name", "status"):
            if required not in entry:
                raise ValueError(
                    f"SCOPE[{cap_id!r}] missing required field {required!r}"
                )
        status = entry["status"]
        if status not in STATUS_VOCAB:
            raise ValueError(
                f"SCOPE[{cap_id!r}] has unknown status {status!r}; "
                f"must be one of {STATUS_VOCAB}"
            )
        det = entry.get("deterministic")
        if det is not None and not isinstance(det, bool):
            raise ValueError(
                f"SCOPE[{cap_id!r}].deterministic must be bool or None, "
                f"got {type(det).__name__}"
            )
        claims.append(CapabilityClaim(
            cap_id=str(cap_id),
            name=str(entry["name"]),
            status=status,
            gate=entry.get("gate"),
            deterministic=det,
            scope_notes=str(entry.get("scope_notes", "")),
        ))
    return tuple(claims)


def verify_evidence_map(claims, gates_dir) -> tuple[bool, str]:
    """For every claim with status in {DONE, PARTIAL}, assert the named
    gate module file (gate + ".py") exists under gates_dir.

    Returns (ok, detail) — same shape as existing UGK conformance gates.
    Honest-absent: FUTURE / OUT_OF_SCOPE / ASPIRATIONAL / UNDECLARED
    claims are NOT asserted. A DONE/PARTIAL claim with gate=None is a
    failure (consumer must name a gate to claim evidence).
    """
    gates_dir = Path(gates_dir)
    missing = []
    no_gate = []
    for c in claims:
        if c.status not in _GATE_REQUIRED_STATUSES:
            continue
        if c.gate is None:
            no_gate.append(f"{c.cap_id}({c.status},no-gate-named)")
            continue
        if not (gates_dir / f"{c.gate}.py").exists():
            missing.append(f"{c.cap_id}->{c.gate}.py(absent)")
    asserted = sum(1 for c in claims if c.status in _GATE_REQUIRED_STATUSES)
    done = sum(1 for c in claims if c.status == "DONE")
    partial = sum(1 for c in claims if c.status == "PARTIAL")
    ok = not (missing or no_gate)
    if ok:
        detail = (f"claims={len(claims)} asserted={asserted} "
                  f"(DONE {done}, PARTIAL {partial}); all gates present")
    else:
        problems = missing + no_gate
        detail = f"problems ({len(problems)}): " + "; ".join(problems)
    return ok, detail


def diff_against_registry(claims, registry_caps) -> dict:
    """Report drift between consumer scope and a registry's declared
    cap-list.

    Args:
      claims          tuple of CapabilityClaim
      registry_caps   iterable of cap_id strings parsed from the
                      registry document (consumer supplies; helper
                      does not parse Markdown)

    Returns a structured diff (reporting only — no judgment):
      {
        "in_registry_not_in_scope": list[str],
        "in_scope_not_in_registry": list[str],
        "in_both":                  list[str],
      }
    Consumer decides what to do with the diff (some caps in registry
    are legitimately not in scope; consumer may want to flag this
    EXPLICITLY by adding an UNDECLARED or OUT_OF_SCOPE entry).
    """
    scope_ids = {c.cap_id for c in claims}
    registry_ids = set(registry_caps)
    return {
        "in_registry_not_in_scope": sorted(registry_ids - scope_ids),
        "in_scope_not_in_registry": sorted(scope_ids - registry_ids),
        "in_both":                  sorted(scope_ids & registry_ids),
    }


def summarize(claims) -> dict:
    """Aggregate counts by status and by deterministic flag.

    Returns:
      {
        "total":           int,
        "by_status":       dict[status -> count],
        "by_deterministic":dict["true"|"false"|"none" -> count],
        "evidenced":       int  (DONE + PARTIAL with gate populated),
        "unevidenced":     int  (everything else),
      }
    """
    by_status = {s: 0 for s in STATUS_VOCAB}
    by_det = {"true": 0, "false": 0, "none": 0}
    evidenced = 0
    for c in claims:
        by_status[c.status] = by_status.get(c.status, 0) + 1
        if c.deterministic is True:
            by_det["true"] += 1
        elif c.deterministic is False:
            by_det["false"] += 1
        else:
            by_det["none"] += 1
        if c.status in _GATE_REQUIRED_STATUSES and c.gate is not None:
            evidenced += 1
    return {
        "total":           len(claims),
        "by_status":       by_status,
        "by_deterministic": by_det,
        "evidenced":       evidenced,
        "unevidenced":     len(claims) - evidenced,
    }
