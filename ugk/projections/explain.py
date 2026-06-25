"""ugk.projections.explain — the explain projection surface (Phase 5b).

Pure function of the corpus. Imports ONLY ugk.projections.* + stdlib; never execution. A SECOND
rendering of the one corpus, alongside docs. Explain may omit, may rephrase, may NOT invent:
  * prose lines are free-form/rephrasable (different wording from the docs surface);
  * STRUCTURED CLAIMS (cited primitive string-labels; cited pattern-ids; identity; boundary marker)
    are machine-checkable and must be traceable to the corpus — the gate verifies every cited claim
    is present in the source. Omission (citing a subset) is allowed; invention (citing anything not
    in the corpus) fails the gate.

Determinism: same metadata -> byte-identical explain output across runs/processes (the prose is
deterministic; "rephrase" is a property of this surface vs docs, not nondeterminism). Accepts
explicit corpus (defaults to packaged) so order-independence is testable.
"""
from __future__ import annotations
from dataclasses import asdict

from ugk.projections.patterns import PATTERNS
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS
from ugk.projections import hash as _hash


def _block(lines):
    return "\n".join(lines).rstrip() + "\n"


def _explain_pattern(p: dict) -> str:
    # cited primitives = the object's own primitives + its seam primitives (verbatim from corpus)
    prims = list(p["primitives"]) + [x for seam in p["seams"] for x in seam["ugk_primitives"]]
    lines = [
        "EXPLAIN pattern:" + p["id"],
        "identity: " + _hash.PROJECTION_IDENTITY,
        "",
        # rephrased didactic prose (deliberately different wording from the docs surface)
        "In plain terms: " + p["title"] + " is a governance shape. " + p["summary"],
        "",
        # structured claims (machine-checkable)
        "primitives: " + " | ".join(prims),
        "boundary: " + ("present" if p["boundaries"] else "absent"),
    ]
    return _block(lines)


def _explain_domain(d: dict) -> str:
    prims = [x for seam in d["integration_points"] for x in seam["ugk_primitives"]]
    lines = [
        "EXPLAIN domain:" + d["id"],
        "identity: " + _hash.PROJECTION_IDENTITY,
        "",
        "In plain terms: " + d["title"] + " shows how governance patterns can apply to a domain, "
        "without supplying that domain's own rules.",
        "",
        "pattern-refs: " + " | ".join(d["patterns"]),
        "primitives: " + " | ".join(prims),
        "boundary: " + ("present" if d["boundary"]["text"].strip() else "absent"),
    ]
    return _block(lines)


def explain_projections(patterns=None, domain_mappings=None) -> dict:
    """key ('pattern:<id>' / 'domain:<id>') -> explain projection text, for every corpus object.

    Top-level enumeration sorted by id (determinism); inner authored order preserved. Accepts explicit
    corpus for order-independence testing.
    """
    pats = PATTERNS if patterns is None else patterns
    doms = DOMAIN_MAPPINGS if domain_mappings is None else domain_mappings
    out = {}
    for p in sorted((asdict(x) for x in pats), key=lambda d: d["id"]):
        out["pattern:" + p["id"]] = _explain_pattern(p)
    for d in sorted((asdict(x) for x in doms), key=lambda d: d["id"]):
        out["domain:" + d["id"]] = _explain_domain(d)
    return out


# --- shared structured-claims parser (producer + gate use the SAME extractor) ---
def _field(projection_text: str, prefix: str) -> list:
    for ln in projection_text.splitlines():
        if ln.startswith(prefix):
            payload = ln[len(prefix):]
            return [t for t in payload.split(" | ") if t]
    return []


def cited_primitives(projection_text: str) -> list:
    return _field(projection_text, "primitives: ")


def cited_pattern_refs(projection_text: str) -> list:
    return _field(projection_text, "pattern-refs: ")


def boundary_marker(projection_text: str) -> str:
    v = _field(projection_text, "boundary: ")
    return v[0] if v else ""


__all__ = [
    "explain_projections", "cited_primitives", "cited_pattern_refs", "boundary_marker",
]
