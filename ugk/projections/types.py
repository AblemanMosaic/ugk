"""ugk.projections.types — descriptive metadata types for the projection jurisdiction.

CGProj (Constitutionally Governed Projections). These are FROZEN, DESCRIPTIVE objects. They
are governed source content, NOT constitutional law and NOT executable policy. Authority never
flows from these objects into execution; the Execution Removability / Non-Authority Gate proves
it (the execution jurisdiction runs fully with this package deleted).

Design rules that keep this layer inert and non-authoritative:
  - stdlib only; imports NOTHING from ugk.kernel, ugk.invariants, ugk.module_registry,
    ugk.storage, ugk.governance, ugk.authority, ugk.scale, or any conformance gate.
  - primitives are referenced by STRING LABEL, never by importing primitive code — this severs
    the dependency that could otherwise couple the projection jurisdiction to the substrate.
  - frozen dataclasses; no methods that touch execution, I/O, or mutable state.

A projection may teach the system, but it may not govern the system.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BoundaryStatement:
    """A front-loaded statement of what a mapping is NOT. Purely descriptive text."""
    text: str


@dataclass(frozen=True)
class IntegrationSeam:
    """Where a domain attaches to UGK primitives. Primitives are NAMED, not imported."""
    summary: str
    ugk_primitives: tuple[str, ...] = ()   # string labels only, e.g. "receipt-before-effect"


@dataclass(frozen=True)
class GovernancePattern:
    """PRIMARY object. A universal governance shape. Patterns never reference domains."""
    id: str
    title: str
    summary: str
    primitives: tuple[str, ...] = ()        # string labels only
    seams: tuple[IntegrationSeam, ...] = ()
    boundaries: tuple[BoundaryStatement, ...] = ()


@dataclass(frozen=True)
class DomainMapping:
    """A domain is an EXAMPLE of patterns. References patterns by id (upward only)."""
    id: str
    title: str
    patterns: tuple[str, ...] = ()          # pattern IDs this domain instantiates
    integration_points: tuple[IntegrationSeam, ...] = ()
    boundary: BoundaryStatement = field(
        default_factory=lambda: BoundaryStatement(text=""))


__all__ = ["BoundaryStatement", "IntegrationSeam", "GovernancePattern", "DomainMapping"]
