"""ugk.cgp.esa — CGP-ESA capability family registry.

The CGP-ESA registry is the CGP-owned catalog of ESA-family capabilities.
ESA capabilities are owned by CGP (the Constitutional Governance
Platform), realized by consumers (UGK, AbleTools, Semantic Navigator,
CPVM, future), and evidenced through the shared receipt substrate via
the CGP execution substrate (ugk.cgp.runner / ugk.cgp.ctr).

This module is DISTINCT from ``ugk.core.esa``:
  - ``ugk.core.esa``   — the kernel-native ESA cap evaluator
                         (~5 caps; runs against a GovernanceKernel
                          and returns ESAKernelReport)
  - ``ugk.cgp.esa``    — the CGP-ESA capability family registry
                         (REGISTRY dict + helpers)

Both coexist by ratified design. The kernel-native evaluator is one
realization of a small subset of caps that the full CGP-ESA registry
declares.

Public surface:
    REGISTRY                          dict[cap_id, dict]
    registry_cap_ids()                tuple[str, ...]
    legacy_map()                      dict[legacy_id, canonical_id]
    get_cap(cap_id)                   dict
    cap_class(cap_id)                 "I" | "II" | "III"
    by_class(class_)                  tuple[str, ...]

The cap_id argument to get_cap / cap_class accepts either the
canonical CGP-ESA form (``"CGP-ESA-Cap-1"``) or the legacy ESA form
(``"Cap-1"``).

See ``ugk/docs/CGP_CAPABILITIES.md`` for the human-readable registry.
"""
from __future__ import annotations
from typing import Optional

from ugk.cgp.esa.registry import REGISTRY


__all__ = [
    "REGISTRY",
    "registry_cap_ids",
    "legacy_map",
    "get_cap",
    "cap_class",
    "by_class",
]


def registry_cap_ids() -> tuple[str, ...]:
    """Return the sorted tuple of canonical CGP-ESA capability IDs.

    Suitable for passing as the ``registry_caps`` argument to
    ``ugk.authority.capability_evidence.diff_against_registry``.
    """
    return tuple(sorted(REGISTRY.keys()))


def legacy_map() -> dict[str, str]:
    """Return a dict mapping legacy ESA cap IDs → canonical CGP-ESA IDs.

    Example:
        >>> from ugk.cgp.esa import legacy_map
        >>> legacy_map()["Cap-22"]
        'CGP-ESA-Cap-22'

    Useful when diff-ing a consumer scope that uses legacy IDs against
    the canonical registry. The legacy_map is injective (each legacy ID
    maps to exactly one canonical ID and vice versa); this is enforced
    at module load by registry._validate_registry.
    """
    return {entry["legacy_esa_id"]: cap_id
            for cap_id, entry in REGISTRY.items()}


def get_cap(cap_id: str) -> dict:
    """Return the registry entry for ``cap_id``.

    Accepts both canonical and legacy forms:
        >>> get_cap("CGP-ESA-Cap-1")  # canonical
        >>> get_cap("Cap-1")           # legacy — resolves to the same entry

    Raises KeyError if ``cap_id`` is not in the registry under either form.
    """
    if cap_id in REGISTRY:
        return REGISTRY[cap_id]
    lm = legacy_map()
    if cap_id in lm:
        return REGISTRY[lm[cap_id]]
    raise KeyError(
        f"cap_id {cap_id!r} not in CGP-ESA registry (neither as "
        f"canonical nor as legacy_esa_id)"
    )


def cap_class(cap_id: str) -> str:
    """Return the class ('I' | 'II' | 'III') of ``cap_id``.

    Accepts both canonical and legacy forms (see ``get_cap``).
    """
    return get_cap(cap_id)["class"]


def by_class(class_: str) -> tuple[str, ...]:
    """Return the sorted tuple of canonical cap IDs with the given class.

    Example:
        >>> by_class("I")[:3]
        ('CGP-ESA-Cap-1', 'CGP-ESA-Cap-12', 'CGP-ESA-Cap-2')

    Raises ValueError if class_ is not one of {'I', 'II', 'III'}.
    """
    if class_ not in ("I", "II", "III"):
        raise ValueError(
            f"class_ must be one of 'I', 'II', 'III'; got {class_!r}"
        )
    return tuple(sorted(
        cap_id for cap_id, entry in REGISTRY.items()
        if entry["class"] == class_
    ))
