"""ugk.projections.docs — the docs surface producer (Phase 5a).

Pure function of the corpus. Imports ONLY ugk.projections.* + stdlib; never execution; never reads
checked-in docs back (anti-entanglement: flow is strictly metadata -> docs). Produces per-object
documentation artifacts:
    docs/patterns/<id>.md          (one per GovernancePattern)
    docs/domain-mappings/<id>.md   (one per DomainMapping; boundary front-loaded; links to patterns)

Each artifact embeds the corpus content_hash in a provenance header (the Phase 4 anti-drift anchor),
so the docs Fidelity check catches any metadata/doc drift. Domain docs cross-link to the pattern docs
they instantiate (relative links), which makes the link-integrity gate meaningful.

This is the docs SURFACE rendering. It is distinct from ugk.projections.render.render_all (the
Phase 3 determinism surface); content_hash is renderer-independent by design, so the docs surface
does not change content_hash.
"""
from __future__ import annotations
from dataclasses import asdict

from ugk.projections.patterns import PATTERNS
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS
from ugk.projections import hash as _hash


def _block(lines):
    return "\n".join(lines).rstrip() + "\n"


def _provenance_header() -> str:
    return (
        "<!-- CGPROJ-PROVENANCE\n"
        "projection-identity: " + _hash.PROJECTION_IDENTITY + "\n"
        "content-hash: " + _hash.content_hash() + "\n"
        "renderer-version: " + _hash.RENDERER_VERSION + "\n"
        "-->\n"
    )


def _render_pattern_doc(p: dict) -> str:
    lines = ["# " + p["title"], "", p["summary"], ""]
    if p["primitives"]:
        lines.append("**UGK primitives:** " + ", ".join(p["primitives"]))
        lines.append("")
    for seam in p["seams"]:
        lines.append("**Integration seam:** " + seam["summary"])
        if seam["ugk_primitives"]:
            lines.append("**Seam primitives:** " + ", ".join(seam["ugk_primitives"]))
        lines.append("")
    for b in p["boundaries"]:
        lines.append("> " + b["text"])
        lines.append("")
    return _block(lines)


def _render_domain_doc(d: dict) -> str:
    lines = ["# " + d["title"], ""]
    # boundary FRONT-LOADED (before any substantive content) — required by the Boundary Gate
    lines.append("> " + d["boundary"]["text"])
    lines.append("")
    if d["patterns"]:
        # cross-link to the pattern docs this domain instantiates (relative link, authored order)
        links = ["[" + pid + "](../patterns/" + pid + ".md)" for pid in d["patterns"]]
        lines.append("**Instantiates patterns:** " + ", ".join(links))
        lines.append("")
    for seam in d["integration_points"]:
        lines.append("**Integration point:** " + seam["summary"])
        if seam["ugk_primitives"]:
            lines.append("**Seam primitives:** " + ", ".join(seam["ugk_primitives"]))
        lines.append("")
    return _block(lines)


def doc_artifacts() -> dict:
    """relpath (under repo root) -> complete artifact text (header + body), for every corpus object.

    Single producer: used both to WRITE the docs and by the gates to compute EXPECTED bytes.
    Top-level enumeration sorted by id (determinism); inner authored order preserved.
    """
    out = {}
    hdr = _provenance_header()
    for p in sorted((asdict(x) for x in PATTERNS), key=lambda d: d["id"]):
        out["docs/patterns/" + p["id"] + ".md"] = hdr + "\n" + _render_pattern_doc(p)
    for d in sorted((asdict(x) for x in DOMAIN_MAPPINGS), key=lambda d: d["id"]):
        out["docs/domain-mappings/" + d["id"] + ".md"] = hdr + "\n" + _render_domain_doc(d)
    return out


__all__ = ["doc_artifacts"]
