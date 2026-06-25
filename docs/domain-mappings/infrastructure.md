<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Infrastructure Mapping

> This note does not constitute a infrastructure or SRE architecture specification and does not address regulatory requirements (change-management, IAM, SOC 2 / ISO 27001) specific to any jurisdiction. It identifies potential integration points only. Domain experts are responsible for implementation, compliance, and validation. UGK provides governed execution, receipts, authority chains, warrants, and admissibility controls; the domain system retains all domain-specific rules, standards, and compliance logic.

**Instantiates patterns:** [irreversible-operations](../patterns/irreversible-operations.md), [high-consequence-execution](../patterns/high-consequence-execution.md), [delegated-authority](../patterns/delegated-authority.md), [audit-critical-workflows](../patterns/audit-critical-workflows.md)

**Integration point:** A platform could map deploy, config-change, and rotation onto UGK primitives, making each an explicit capability exercise with declared intent, producing a refusal receipt when an actor exceeds its grant, while retaining all orchestration and IAM policy.
**Seam primitives:** receipt-before-effect, admissibility evaluation, refusal receipt
