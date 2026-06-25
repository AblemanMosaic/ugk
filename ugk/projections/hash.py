"""ugk.projections.hash — canonical hashing for the projection jurisdiction.

Pure functions over projection metadata. Imports ONLY ugk.projections.* and stdlib; never
ugk.kernel / ugk.invariants / ugk.module_registry / ugk.storage / ugk.governance /
ugk.authority / ugk.scale / any conformance gate. Hashing the projection layer has no business
touching execution.

Per the Phase 3 design note (ratified), three conceptually-distinct notions are kept nominally
separate even where v0.1.0 derives them from related inputs:

  * PROJECTION_IDENTITY — stable logical name of this projection set. Does NOT change when the
    metadata changes or when the renderer changes.
  * content_hash()      — sha256 over the canonical JSON of the governed metadata. Changes iff the
    metadata changes. Renderer-independent. The anti-drift anchor Phase 4 fidelity compares against.
  * render_hash()       — sha256 over (RENDERER_VERSION + "\n" + rendered markdown bytes). Changes
    if either the renderer logic or the content changes. Distinct from content_hash by construction.

Canonicalization regime (design note §1-§5):
  * Top-level collections (patterns, domain_mappings) sorted ascending by `id` (code-point order).
  * Inner authored tuples (primitives, seams, a domain's pattern-id list) PRESERVED as authored —
    that order is governed content, not incidental.
  * Object fields serialized with sort_keys=True (fixed field order).
  * JSON: separators=(",", ":"), ensure_ascii=True, no indentation, no trailing newline.
  * Encoding: UTF-8, fixed.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict

from ugk.projections.patterns import PATTERNS
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS


# ---- canonicalization (the determinism foundation) ----

def canonical_payload(patterns=None, domain_mappings=None) -> dict:
    """Canonical, sorted, JSON-serializable view of the projection metadata.

    Top-level collections are sorted EXPLICITLY by id so output never depends on argument order,
    dict-insertion order, or PYTHONHASHSEED. Inner tuples are left in authored order (governed
    content). Accepts explicit metadata (defaults to the packaged sets) so order-independence is
    testable: a shuffled input must produce an identical payload.
    """
    pats = PATTERNS if patterns is None else patterns
    doms = DOMAIN_MAPPINGS if domain_mappings is None else domain_mappings
    patterns_d = sorted((asdict(p) for p in pats), key=lambda d: d["id"])
    domains_d = sorted((asdict(d) for d in doms), key=lambda d: d["id"])
    return {"patterns": patterns_d, "domain_mappings": domains_d}


def canonical_json(patterns=None, domain_mappings=None) -> str:
    """Deterministic JSON: sorted keys, fixed separators, ASCII-escaped, no whitespace drift."""
    return json.dumps(
        canonical_payload(patterns, domain_mappings),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )


# ---- three conceptually-separate notions (design note §4) ----

# Projection IDENTITY: stable logical name of this projection set. Independent of content/renderer.
PROJECTION_IDENTITY = "cgproj/patterns+domain_mappings/v1"

# Renderer version: bumping this changes the RENDER hash but not the CONTENT hash.
RENDERER_VERSION = "cgproj-render/v1"


def content_hash(patterns=None, domain_mappings=None) -> str:
    """CONTENT hash: sha256 over the canonical metadata JSON (UTF-8).

    Changes iff the governed metadata changes. Independent of the renderer — two different
    renderers over the same source share this hash. This is what Phase 4 fidelity compares against.
    """
    return hashlib.sha256(canonical_json(patterns, domain_mappings).encode("utf-8")).hexdigest()


def render_hash() -> str:
    """RENDER hash: sha256 over (RENDERER_VERSION + "\n" + rendered markdown bytes).

    Changes if EITHER the renderer logic (RENDERER_VERSION) or the content changes. Distinct from
    content_hash by construction. Late-imports render to avoid an import cycle.
    """
    from ugk.projections.render import render_all
    body = (RENDERER_VERSION + "\n").encode("utf-8") + render_all().encode("utf-8")
    return hashlib.sha256(body).hexdigest()


__all__ = [
    "canonical_payload", "canonical_json",
    "PROJECTION_IDENTITY", "RENDERER_VERSION",
    "content_hash", "render_hash",
]
