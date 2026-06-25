<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Multi-Party Authorization

Acts that must not proceed on one party's say-so: large transfers, privileged changes, releases requiring sign-off.

**UGK primitives:** quorum finality (finality_hash), RotationRule

**Integration seam:** Finalize the act under a declared quorum regime; v0.1.0 ships N=1 and rotates to N>=1 via a pre-declared RotationRule.
**Seam primitives:** finality_hash, CSH

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.
