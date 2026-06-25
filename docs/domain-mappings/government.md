<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Government Mapping

> This note does not constitute a public-sector architecture specification and does not address regulatory requirements (public-records, privacy, procurement, admin-law) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** [delegated-authority](../patterns/delegated-authority.md), [regulated-recordkeeping](../patterns/regulated-recordkeeping.md), [audit-critical-workflows](../patterns/audit-critical-workflows.md), [high-consequence-execution](../patterns/high-consequence-execution.md)

**Integration point:** A public-sector system could map decision, disbursement, and records ops onto UGK primitives, binding each act to its authority and governing phase, while retaining all statutory logic and records-law compliance.
**Seam primitives:** authority chain, CSH, phase_code
