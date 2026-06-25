"""ugk.projections.patterns — the governance patterns as frozen descriptive metadata.

PRIMARY objects in the pattern-primary hierarchy. Universal governance shapes; domains are
examples that reference these by id. Descriptive only — no execution authority. Content mirrors
docs/patterns/ (which, in a later phase, would be rendered FROM these objects).
"""
from __future__ import annotations
from ugk.projections.types import GovernancePattern, IntegrationSeam, BoundaryStatement

_NOT_DOMAIN_RULES = BoundaryStatement(
    text="UGK supplies the governance shape, not the domain rules; the domain system retains "
         "its own logic, standards, and compliance.")

PATTERNS: tuple[GovernancePattern, ...] = (
    GovernancePattern(
        id="irreversible-operations",
        title="Irreversible Operations",
        summary="Operations that cannot be undone, where the cost of an unexplained act is "
                "highest: payment capture, record deletion, production deploy, dispatch.",
        primitives=("receipt-before-effect (NBER-1)",),
        seams=(IntegrationSeam(
            summary="Route the irreversible act through the kernel so a receipt is written "
                    "before the effect; a crash leaves the receipt standing.",
            ugk_primitives=("receipt-before-effect (NBER-1)", "receipt chain")),),
        boundaries=(_NOT_DOMAIN_RULES,),
    ),
    GovernancePattern(
        id="multi-party-authorization",
        title="Multi-Party Authorization",
        summary="Acts that must not proceed on one party's say-so: large transfers, privileged "
                "changes, releases requiring sign-off.",
        primitives=("quorum finality (finality_hash)", "RotationRule"),
        seams=(IntegrationSeam(
            summary="Finalize the act under a declared quorum regime; v0.1.0 ships N=1 and "
                    "rotates to N>=1 via a pre-declared RotationRule.",
            ugk_primitives=("finality_hash", "CSH")),),
        boundaries=(_NOT_DOMAIN_RULES,),
    ),
    GovernancePattern(
        id="delegated-authority",
        title="Delegated Authority",
        summary="X acts on behalf of Y: a service for a user, an agent under an operator's "
                "grant, a subprocess under a parent's authority.",
        primitives=("authority chains", "warrants"),
        seams=(IntegrationSeam(
            summary="Resolve and record the delegation chain at execution time; an act whose "
                    "authority chain does not resolve is refused.",
            ugk_primitives=("authority chain", "warrant")),),
        boundaries=(_NOT_DOMAIN_RULES,),
    ),
    GovernancePattern(
        id="audit-critical-workflows",
        title="Audit-Critical Workflows",
        summary="Workflows where someone with standing will later ask why an action was taken "
                "and 'we have logs' is not an acceptable answer.",
        primitives=("receipt chain", "law_hash commitment"),
        seams=(IntegrationSeam(
            summary="The append-only, hash-chained receipt record makes the why a first-class "
                    "artifact produced at execution time, not a later reconstruction.",
            ugk_primitives=("receipt chain", "refusal receipt")),),
        boundaries=(_NOT_DOMAIN_RULES,),
    ),
    GovernancePattern(
        id="regulated-recordkeeping",
        title="Regulated Recordkeeping",
        summary="Records that must be provably made under a specific governing regime and not "
                "silently reinterpreted when the regime changes.",
        primitives=("CSH", "Cryptographic Phase (phase_code)"),
        seams=(IntegrationSeam(
            summary="Each record commits under the active law_hash and phase; a regime change is "
                    "a signed phase transition, never an implicit reinterpretation.",
            ugk_primitives=("CSH", "phase_code")),),
        boundaries=(_NOT_DOMAIN_RULES,),
    ),
    GovernancePattern(
        id="high-consequence-execution",
        title="High-Consequence Execution",
        summary="Execution where the right refusal matters as much as the right action: a "
                "tool-using agent that must not exceed its grant.",
        primitives=("admissibility evaluation", "refusal as first-class outcome"),
        seams=(IntegrationSeam(
            summary="Every op is an explicit capability exercise with declared intent and "
                    "authority chain; an inadmissible op yields a refusal receipt, not a silent "
                    "proceed.",
            ugk_primitives=("admissibility evaluation", "refusal receipt")),),
        boundaries=(_NOT_DOMAIN_RULES,),
    ),
    GovernancePattern(
        id="distributed-coordination",
        title="Distributed Coordination",
        summary="Many actors producing consequential operations concurrently, where throughput "
                "matters but governance must not be laundered by the scheduler.",
        primitives=("scale lane (opt-in)", "dependency oracle", "I5 self-governance"),
        seams=(IntegrationSeam(
            summary="The opt-in scale lane reorders only within oracle-proven earned-independent "
                    "sets; dependent work serializes; every scheduling decision is receipted.",
            ugk_primitives=("ScalePosture", "dependency oracle", "I5 receipts")),),
        boundaries=(BoundaryStatement(
            text="The scale lane is dormant by default and deployment-gated; use ugk.scale.lab "
                 "to measure whether a workload qualifies before enabling anything."),),
    ),
)

# pattern id -> object, for upward reference resolution by domain mappings.
PATTERNS_BY_ID = {p.id: p for p in PATTERNS}

__all__ = ["PATTERNS", "PATTERNS_BY_ID"]
