<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Domain Mappings

## Finance Mapping

> This note does not constitute a financial architecture specification and does not address regulatory requirements (SOX, MiFID II, Dodd-Frank, PCI-DSS, etc.) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** irreversible-operations, multi-party-authorization, delegated-authority, audit-critical-workflows

**Integration point:** A settlement platform could map settlement authorization, execution, and reconciliation onto UGK primitives while retaining all compliance logic (limits, regulatory reporting, reconciliation) within the financial system.
**Seam primitives:** receipt-before-effect, authority chain, finality_hash

## Government Mapping

> This note does not constitute a public-sector architecture specification and does not address regulatory requirements (public-records, privacy, procurement, admin-law) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** delegated-authority, regulated-recordkeeping, audit-critical-workflows, high-consequence-execution

**Integration point:** A public-sector system could map decision, disbursement, and records ops onto UGK primitives, binding each act to its authority and governing phase, while retaining all statutory logic and records-law compliance.
**Seam primitives:** authority chain, CSH, phase_code

## Healthcare Mapping

> This note does not constitute a clinical or health-IT architecture specification and does not address regulatory requirements (HIPAA, GDPR health data, HL7/FHIR) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** delegated-authority, irreversible-operations, audit-critical-workflows, high-consequence-execution

**Integration point:** A health system could map order-entry, administration, and disclosure onto UGK primitives, recording the authority chain and warrant per act, while retaining all clinical logic, consent rules, and compliance.
**Seam primitives:** authority chain, receipt-before-effect, refusal receipt

## Infrastructure Mapping

> This note does not constitute a infrastructure or SRE architecture specification and does not address regulatory requirements (change-management, IAM, SOC 2 / ISO 27001) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** irreversible-operations, high-consequence-execution, delegated-authority, audit-critical-workflows

**Integration point:** A platform could map deploy, config-change, and rotation onto UGK primitives, making each an explicit capability exercise with declared intent, producing a refusal receipt when an actor exceeds its grant, while retaining all orchestration and IAM policy.
**Seam primitives:** receipt-before-effect, admissibility evaluation, refusal receipt

## Logistics Mapping

> This note does not constitute a logistics or supply-chain architecture specification and does not address regulatory requirements (customs, trade-compliance, carrier regs) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** irreversible-operations, delegated-authority, distributed-coordination, audit-critical-workflows

**Integration point:** A logistics platform could map dispatch, custody-handoff, and declaration onto UGK primitives, recording authority and a receipt at each custody boundary, while retaining all routing, customs, and carrier logic.
**Seam primitives:** receipt-before-effect, authority chain, scale lane (opt-in)
