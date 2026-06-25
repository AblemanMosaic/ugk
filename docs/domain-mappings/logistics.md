<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Logistics Mapping

> This note does not constitute a logistics or supply-chain architecture specification and does not address regulatory requirements (customs, trade-compliance, carrier regs) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** [irreversible-operations](../patterns/irreversible-operations.md), [delegated-authority](../patterns/delegated-authority.md), [distributed-coordination](../patterns/distributed-coordination.md), [audit-critical-workflows](../patterns/audit-critical-workflows.md)

**Integration point:** A logistics platform could map dispatch, custody-handoff, and declaration onto UGK primitives, recording authority and a receipt at each custody boundary, while retaining all routing, customs, and carrier logic.
**Seam primitives:** receipt-before-effect, authority chain, scale lane (opt-in)
