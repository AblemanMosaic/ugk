<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Distributed Coordination

Many actors producing consequential operations concurrently, where throughput matters but governance must not be laundered by the scheduler.

**UGK primitives:** scale lane (opt-in), dependency oracle, I5 self-governance

**Integration seam:** The opt-in scale lane reorders only within oracle-proven earned-independent sets; dependent work serializes; every scheduling decision is receipted.
**Seam primitives:** ScalePosture, dependency oracle, I5 receipts

> The scale lane is dormant by default and deployment-gated; use ugk.scale.lab to measure whether a workload qualifies before enabling anything.
