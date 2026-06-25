<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Audit-Critical Workflows

Workflows where someone with standing will later ask why an action was taken and 'we have logs' is not an acceptable answer.

**UGK primitives:** receipt chain, law_hash commitment

**Integration seam:** The append-only, hash-chained receipt record makes the why a first-class artifact produced at execution time, not a later reconstruction.
**Seam primitives:** receipt chain, refusal receipt

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.
