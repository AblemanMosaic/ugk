<!-- CGPROJ-PROVENANCE
projection-identity: cgproj/patterns+domain_mappings/v1
content-hash: 09a63ebefe96dddaa88d454c2767ec200f98d6ef393ccdc89c75547a8a3b623b
renderer-version: cgproj-render/v1
-->

# Governance Patterns

## Audit-Critical Workflows

Workflows where someone with standing will later ask why an action was taken and 'we have logs' is not an acceptable answer.

**UGK primitives:** receipt chain, law_hash commitment

**Integration seam:** The append-only, hash-chained receipt record makes the why a first-class artifact produced at execution time, not a later reconstruction.
**Seam primitives:** receipt chain, refusal receipt

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.

## Delegated Authority

X acts on behalf of Y: a service for a user, an agent under an operator's grant, a subprocess under a parent's authority.

**UGK primitives:** authority chains, warrants

**Integration seam:** Resolve and record the delegation chain at execution time; an act whose authority chain does not resolve is refused.
**Seam primitives:** authority chain, warrant

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.

## Distributed Coordination

Many actors producing consequential operations concurrently, where throughput matters but governance must not be laundered by the scheduler.

**UGK primitives:** scale lane (opt-in), dependency oracle, I5 self-governance

**Integration seam:** The opt-in scale lane reorders only within oracle-proven earned-independent sets; dependent work serializes; every scheduling decision is receipted.
**Seam primitives:** ScalePosture, dependency oracle, I5 receipts

> The scale lane is dormant by default and deployment-gated; use ugk.scale.lab to measure whether a workload qualifies before enabling anything.

## High-Consequence Execution

Execution where the right refusal matters as much as the right action: a tool-using agent that must not exceed its grant.

**UGK primitives:** admissibility evaluation, refusal as first-class outcome

**Integration seam:** Every op is an explicit capability exercise with declared intent and authority chain; an inadmissible op yields a refusal receipt, not a silent proceed.
**Seam primitives:** admissibility evaluation, refusal receipt

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.

## Irreversible Operations

Operations that cannot be undone, where the cost of an unexplained act is highest: payment capture, record deletion, production deploy, dispatch.

**UGK primitives:** receipt-before-effect (NBER-1)

**Integration seam:** Route the irreversible act through the kernel so a receipt is written before the effect; a crash leaves the receipt standing.
**Seam primitives:** receipt-before-effect (NBER-1), receipt chain

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.

## Multi-Party Authorization

Acts that must not proceed on one party's say-so: large transfers, privileged changes, releases requiring sign-off.

**UGK primitives:** quorum finality (finality_hash), RotationRule

**Integration seam:** Finalize the act under a declared quorum regime; v0.1.0 ships N=1 and rotates to N>=1 via a pre-declared RotationRule.
**Seam primitives:** finality_hash, CSH

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.

## Regulated Recordkeeping

Records that must be provably made under a specific governing regime and not silently reinterpreted when the regime changes.

**UGK primitives:** CSH, Cryptographic Phase (phase_code)

**Integration seam:** Each record commits under the active law_hash and phase; a regime change is a signed phase transition, never an implicit reinterpretation.
**Seam primitives:** CSH, phase_code

> UGK supplies the governance shape, not the domain rules; the domain system retains its own logic, standards, and compliance.
