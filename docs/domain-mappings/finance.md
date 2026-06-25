<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Finance Mapping

> This note does not constitute a financial architecture specification and does not address regulatory requirements (SOX, MiFID II, Dodd-Frank, PCI-DSS, etc.) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** [irreversible-operations](../patterns/irreversible-operations.md), [multi-party-authorization](../patterns/multi-party-authorization.md), [delegated-authority](../patterns/delegated-authority.md), [audit-critical-workflows](../patterns/audit-critical-workflows.md)

**Integration point:** A settlement platform could map settlement authorization, execution, and reconciliation onto UGK primitives while retaining all compliance logic (limits, regulatory reporting, reconciliation) within the financial system.
**Seam primitives:** receipt-before-effect, authority chain, finality_hash
