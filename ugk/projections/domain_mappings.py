"""ugk.projections.domain_mappings — domain mappings as frozen descriptive metadata.

A domain mapping is an EXAMPLE of one or more patterns. It references patterns by id (upward
only; patterns never reference domains). Each carries a front-loaded BoundaryStatement. These
are seam descriptions, NOT domain architecture specs and NOT claims of domain expertise.
"""
from __future__ import annotations
from ugk.projections.types import DomainMapping, IntegrationSeam, BoundaryStatement


def _boundary(domain: str, regs: str) -> BoundaryStatement:
    return BoundaryStatement(
        text=f"This note does not constitute a {domain} architecture specification and does not "
             f"address regulatory requirements ({regs}) specific to any jurisdiction. It "
             f"identifies potential integration points only. Domain experts are responsible for "
             f"implementation, compliance, and validation. UGK provides governed execution, "
             f"receipts, authority chains, warrants, and admissibility controls; the domain "
             f"system retains all domain-specific rules, standards, and compliance logic.")


DOMAIN_MAPPINGS: tuple[DomainMapping, ...] = (
    DomainMapping(
        id="finance",
        title="Finance Mapping",
        patterns=("irreversible-operations", "multi-party-authorization",
                  "delegated-authority", "audit-critical-workflows"),
        integration_points=(IntegrationSeam(
            summary="A settlement platform could map settlement authorization, execution, and "
                    "reconciliation onto UGK primitives while retaining all compliance logic "
                    "(limits, regulatory reporting, reconciliation) within the financial system.",
            ugk_primitives=("receipt-before-effect", "authority chain", "finality_hash")),),
        boundary=_boundary("financial", "SOX, MiFID II, Dodd-Frank, PCI-DSS, etc."),
    ),
    DomainMapping(
        id="healthcare",
        title="Healthcare Mapping",
        patterns=("delegated-authority", "irreversible-operations",
                  "audit-critical-workflows", "high-consequence-execution"),
        integration_points=(IntegrationSeam(
            summary="A health system could map order-entry, administration, and disclosure onto "
                    "UGK primitives, recording the authority chain and warrant per act, while "
                    "retaining all clinical logic, consent rules, and compliance.",
            ugk_primitives=("authority chain", "receipt-before-effect", "refusal receipt")),),
        boundary=_boundary("clinical or health-IT", "HIPAA, GDPR health data, HL7/FHIR"),
    ),
    DomainMapping(
        id="logistics",
        title="Logistics Mapping",
        patterns=("irreversible-operations", "delegated-authority",
                  "distributed-coordination", "audit-critical-workflows"),
        integration_points=(IntegrationSeam(
            summary="A logistics platform could map dispatch, custody-handoff, and declaration "
                    "onto UGK primitives, recording authority and a receipt at each custody "
                    "boundary, while retaining all routing, customs, and carrier logic.",
            ugk_primitives=("receipt-before-effect", "authority chain", "scale lane (opt-in)")),),
        boundary=_boundary("logistics or supply-chain", "customs, trade-compliance, carrier regs"),
    ),
    DomainMapping(
        id="government",
        title="Government Mapping",
        patterns=("delegated-authority", "regulated-recordkeeping",
                  "audit-critical-workflows", "high-consequence-execution"),
        integration_points=(IntegrationSeam(
            summary="A public-sector system could map decision, disbursement, and records ops "
                    "onto UGK primitives, binding each act to its authority and governing phase, "
                    "while retaining all statutory logic and records-law compliance.",
            ugk_primitives=("authority chain", "CSH", "phase_code")),),
        boundary=_boundary("public-sector", "public-records, privacy, procurement, admin-law"),
    ),
    DomainMapping(
        id="infrastructure",
        title="Infrastructure Mapping",
        patterns=("irreversible-operations", "high-consequence-execution",
                  "delegated-authority", "audit-critical-workflows"),
        integration_points=(IntegrationSeam(
            summary="A platform could map deploy, config-change, and rotation onto UGK "
                    "primitives, making each an explicit capability exercise with declared "
                    "intent, producing a refusal receipt when an actor exceeds its grant, while "
                    "retaining all orchestration and IAM policy.",
            ugk_primitives=("receipt-before-effect", "admissibility evaluation", "refusal receipt")),),
        boundary=_boundary("infrastructure or SRE", "change-management, IAM, SOC 2 / ISO 27001"),
    ),
)

DOMAIN_MAPPINGS_BY_ID = {d.id: d for d in DOMAIN_MAPPINGS}

__all__ = ["DOMAIN_MAPPINGS", "DOMAIN_MAPPINGS_BY_ID"]
