"""ugk.projections.generate — the SINGLE producer of checked-in generated artifacts.

Pure function of projection metadata. Imports ONLY ugk.projections.* + stdlib; never execution.
This module is the ONE writer of the *.generated.md artifacts AND the function the Fidelity Gate
calls to compute "expected" bytes — so the real check and the controls share one code path (no
divergent reimplementation).

Each artifact is: a machine-parseable provenance header (HTML comment, invisible in rendered
markdown) carrying the full 64-hex content_hash, followed by the deterministic Phase 3 render
output for that collection. The flow is strictly metadata -> artifact; artifacts are never read
back as source (no reverse drift).
"""
from __future__ import annotations

from ugk.projections import render as _render
from ugk.projections import hash as _hash


# Fixed registry of the artifacts Phase 4 defines: name -> (renderer fn, label).
# Adding/removing entries is the only thing that changes which artifacts exist.
ARTIFACTS = {
    "patterns.generated.md": ("patterns", _render.render_patterns),
    "domain_mappings.generated.md": ("domain_mappings", _render.render_domain_mappings),
}


def _provenance_header() -> str:
    """Canonical provenance header. content-hash is the FULL 64-hex content hash of the metadata."""
    return (
        "<!-- CGPROJ-PROVENANCE\n"
        "projection-identity: " + _hash.PROJECTION_IDENTITY + "\n"
        "content-hash: " + _hash.content_hash() + "\n"
        "renderer-version: " + _hash.RENDERER_VERSION + "\n"
        "-->\n"
    )


def generate_artifact(name: str) -> str:
    """Produce the COMPLETE artifact text (header + body) for a named artifact.

    This is the single source of artifact bytes: used both to WRITE the checked-in file and by the
    Fidelity Gate to compute EXPECTED bytes. body = the deterministic Phase 3 render output.
    """
    if name not in ARTIFACTS:
        raise KeyError("unknown artifact: " + name)
    _label, render_fn = ARTIFACTS[name]
    body = render_fn()
    return _provenance_header() + "\n" + body


def generate_all() -> dict:
    """name -> complete artifact text, for every artifact Phase 4 defines."""
    return {name: generate_artifact(name) for name in ARTIFACTS}


__all__ = ["ARTIFACTS", "generate_artifact", "generate_all"]
