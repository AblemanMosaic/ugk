<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Irreversible Operations

Operations that cannot be undone, where the cost of an unexplained act is highest: payment capture, record deletion, production deploy, dispatch.

**UGK primitives:** receipt-before-effect (NBER-1)

**Integration seam:** Route the irreversible act through the kernel so a receipt is written before the effect; a crash leaves the receipt standing.
**Seam primitives:** receipt-before-effect (NBER-1), receipt chain

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.
