"""ugk.projections.render — deterministic renderer for the projection jurisdiction.

PURE FUNCTION of projection metadata. Imports ONLY ugk.projections.* and stdlib; never
ugk.kernel / ugk.invariants / ugk.module_registry / ugk.storage / ugk.governance /
ugk.authority / ugk.scale / any conformance gate. Rendering is the Source → Documentation arrow;
it never reads generated docs back (no reverse drift), and it writes no files in Phase 3.

Determinism contract (Phase 3 design note, ratified):
  * same metadata → byte-identical markdown across repeated runs AND across processes;
  * top-level collections ordered EXPLICITLY by id (never dict-insertion / hash-seed dependent);
  * inner authored tuples preserved in authored order (governed content);
  * no timestamps, no hostnames, no absolute paths, no locale dependence, no runtime discovery;
  * line endings LF only; one blank line between blocks; rstrip() + single terminal newline.

This is the SMALLEST renderer that satisfies the Determinism Gate. No templating engine, no
multiple output formats, no configuration surface (all out of Phase 3 scope).
"""
from __future__ import annotations
from dataclasses import asdict

from ugk.projections.patterns import PATTERNS
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS


def _block(lines: list) -> str:
    """Join lines with LF, strip trailing whitespace, exactly one terminal newline."""
    return "\n".join(lines).rstrip() + "\n"


def _render_pattern(p: dict) -> str:
    lines = ["## " + p["title"], "", p["summary"], ""]
    if p["primitives"]:
        # authored tuple order preserved
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


def _render_domain(d: dict) -> str:
    lines = ["## " + d["title"], ""]
    # boundary is front-loaded (per Phase 1 object model)
    lines.append("> " + d["boundary"]["text"])
    lines.append("")
    if d["patterns"]:
        # authored pattern-id order preserved
        lines.append("**Instantiates patterns:** " + ", ".join(d["patterns"]))
        lines.append("")
    for seam in d["integration_points"]:
        lines.append("**Integration point:** " + seam["summary"])
        if seam["ugk_primitives"]:
            lines.append("**Seam primitives:** " + ", ".join(seam["ugk_primitives"]))
        lines.append("")
    return _block(lines)


def render_patterns(patterns=None) -> str:
    pats = PATTERNS if patterns is None else patterns
    ordered = sorted((asdict(p) for p in pats), key=lambda d: d["id"])
    parts = ["# Governance Patterns", ""]
    for p in ordered:
        parts.append(_render_pattern(p).rstrip())
        parts.append("")
    return _block(parts)


def render_domain_mappings(domain_mappings=None) -> str:
    doms = DOMAIN_MAPPINGS if domain_mappings is None else domain_mappings
    ordered = sorted((asdict(d) for d in doms), key=lambda d: d["id"])
    parts = ["# Domain Mappings", ""]
    for d in ordered:
        parts.append(_render_domain(d).rstrip())
        parts.append("")
    return _block(parts)


def render_all(patterns=None, domain_mappings=None) -> str:
    """The full deterministic projection: patterns then domain mappings, as one markdown string."""
    parts = [
        render_patterns(patterns).rstrip(),
        "",
        render_domain_mappings(domain_mappings).rstrip(),
    ]
    return _block(parts)


__all__ = ["render_patterns", "render_domain_mappings", "render_all"]
