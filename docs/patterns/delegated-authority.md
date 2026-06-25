<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Delegated Authority

X acts on behalf of Y: a service for a user, an agent under an operator's grant, a subprocess under a parent's authority.

**UGK primitives:** authority chains, warrants

**Integration seam:** Resolve and record the delegation chain at execution time; an act whose authority chain does not resolve is refused.
**Seam primitives:** authority chain, warrant

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.
