"""ugk.projections — CGProj projection jurisdiction (descriptive metadata only).

Non-authoritative by construction. Nothing in the execution jurisdiction imports this package;
the Execution Removability / Non-Authority Gate proves the platform runs fully with this package
deleted. A projection may teach the system, but it may not govern the system.
"""
from ugk.projections.types import (
    BoundaryStatement, IntegrationSeam, GovernancePattern, DomainMapping,
)
from ugk.projections.patterns import PATTERNS, PATTERNS_BY_ID
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS, DOMAIN_MAPPINGS_BY_ID

__all__ = [
    "BoundaryStatement", "IntegrationSeam", "GovernancePattern", "DomainMapping",
    "PATTERNS", "PATTERNS_BY_ID", "DOMAIN_MAPPINGS", "DOMAIN_MAPPINGS_BY_ID",
]
