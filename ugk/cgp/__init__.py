"""ugk.cgp — Constitutional Governance Platform: canonical entry surface.

CGP is the system-level capability platform exposed through UGK. This
package re-exports the canonical CGP-facing surfaces. The package
structure is::

    ugk.cgp                 (this module — posture adapter re-exports)
    ugk.cgp.posture         (the posture adapter implementation)
    ugk.cgp.runner          (HeadlessRunner / CGPRunner protocol)
    ugk.cgp.ctr             (CTR coverage discipline)
    ugk.cgp.srsa            (10-axis SRSA vector)

The implementations live in their pre-CGP-namespace locations and are
preserved as compatibility aliases (per ratified compat policy):

    ugk.cgp.posture          ← canonical
    ugk.cgp.runner.headless  ← canonical, re-exports HeadlessRunner from:
        ugk.testing.headless_runner          (compatibility alias)
    ugk.cgp.ctr              ← canonical, re-exports from:
        ugk.ctr                              (compatibility alias)
    ugk.cgp.srsa             ← canonical, re-exports from:
        ugk.core.srsa                        (compatibility alias)

Public surface preserved from the pre-package ``ugk.cgp`` single-file
module. All three call forms remain byte-for-byte equivalent at the
public API level:

    from ugk.cgp import compute
    from ugk.cgp import compute_from_store
    from ugk.cgp import required_attributes

See ``ugk/docs/CGP_EXECUTION_SUBSTRATE.md`` for consumer orientation.
"""
from ugk.cgp.posture import (
    compute,
    compute_from_store,
    required_attributes,
    GovernancePosture,
)

__all__ = [
    "compute",
    "compute_from_store",
    "required_attributes",
    "GovernancePosture",
]
