<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Healthcare Mapping

> This note does not constitute a clinical or health-IT architecture specification and does not address regulatory requirements (HIPAA, GDPR health data, HL7/FHIR) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** [delegated-authority](../patterns/delegated-authority.md), [irreversible-operations](../patterns/irreversible-operations.md), [audit-critical-workflows](../patterns/audit-critical-workflows.md), [high-consequence-execution](../patterns/high-consequence-execution.md)

**Integration point:** A health system could map order-entry, administration, and disclosure onto UGK primitives, recording the authority chain and warrant per act, while retaining all clinical logic, consent rules, and compliance.
**Seam primitives:** authority chain, receipt-before-effect, refusal receipt
