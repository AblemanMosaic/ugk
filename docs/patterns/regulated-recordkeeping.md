<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Regulated Recordkeeping

Records that must be provably made under a specific governing regime and not silently reinterpreted when the regime changes.

**UGK primitives:** CSH, Cryptographic Phase (phase_code)

**Integration seam:** Each record commits under the active law_hash and phase; a regime change is a signed phase transition, never an implicit reinterpretation.
**Seam primitives:** CSH, phase_code

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.
