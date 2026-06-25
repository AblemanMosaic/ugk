"""ugk.cgp.srsa — canonical CGP-facing SRSA surface.

Sovereign Reliance Spectrum Architecture: 10-axis vector computation
over a GovernanceKernel instance. This module is the canonical
CGP-facing import path; the implementation lives at ``ugk.core.srsa``
and remains valid as a compatibility alias.

The 10 SRSA axes (per ugk.core.srsa source, current status against
the UGK substrate):

    AdSA  Admit-class                    UGK native (three-tier execute)
    ASA   Authority/intent/jurisdiction  UGK native (per-op fields)
    CSA   Causal chain                   UGK native (prior_receipt_hash)
    PSA   Provenance / CHC               UGK native (binding.py)
    ESA   Evidence self-check            UGK partial (~5 kernel caps;
                                           full CGP-ESA registry pending)
    FSA   Freshness / staleness          UGK partial (CTR staleness +
                                           determinism gate)
    RSA   Reachability                   Application-layer
                                           (not in UGK core)
    SSA   Semantic surface               UGK partial (17 verbs declared)
    ISA   Identity / individuation       Honest zero — designed budget
                                           only; emergent geometry unmapped
    LSA   Legitimacy                     Honest zero — no declared
                                           legitimacy basis

The honest-zero entries for ISA and LSA are intentional; they reflect
the corrected ontology in which UGK declares only what it actually
implements and leaves application-layer or doctrinally-undefined
axes explicitly absent rather than silently zeroed.

Public surface:
    srsa_vector(kernel) -> dict[str, dict]
        Returns the 10-axis SRSA score vector for a GovernanceKernel.

Canonical import:
    from ugk.cgp.srsa import srsa_vector

Compatibility alias (preserved, no deprecation):
    from ugk.core.srsa import srsa_vector

See ``ugk/docs/CGP_EXECUTION_SUBSTRATE.md`` for orientation.
"""
from ugk.core.srsa import srsa_vector

__all__ = ["srsa_vector"]
