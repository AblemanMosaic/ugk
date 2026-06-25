"""ugk/cgp.py — Constitutional Governance Platform: adapter surface.

The canonical entry point for enabling CGP from any UGK-consuming context.
GovernancePosture.compute() (ugk.posture) is already kernel-duck-typed: it
reads only six structural attributes from its argument
(.store, ._session_dkn, ._law_hash, ._authority_model,
 ._require_scoped_intent, ._will_store). This module exposes that
structural target through three integration paths so consumers do not
need to know GovernanceKernel internals.

Three integration modes:

  Mode 1 — direct GovernanceKernel posture computation
    >>> from ugk.cgp import compute
    >>> posture = compute(kernel)        # kernel = ugk.kernel.GovernanceKernel

  Mode 2 — store-only consumers (e.g. CPVM AuthoritativeChain)
    >>> from ugk.cgp import compute_from_store
    >>> posture = compute_from_store(store, session_dkn=..., law_hash=...)
    Organs the consumer does not manage (authority_model, will_store)
    default to honest-absent. The posture's matrix cells reflect this
    faithfully per CGP-S-02 (ugk health honest-absent semantics).

  Mode 3 — vendored-kernel consumers (e.g. AbleTools UGKVendoredKernel)
    Consumer-side facades (e.g. AbleTools Organs) call compute() on the
    underlying kernel they wrap. See abletools.governance.abletools_organs
    Organs.compute_posture() for the canonical example.

Discoverability:
    required_attributes() returns the structural attribute tuple, useful
    when writing a new consumer-side adapter.

This module is additive: no constitutional change, no law_hash movement,
no new error codes. The posture machinery (ugk.posture) is unchanged;
this is purely an ergonomic entry surface.
"""
from __future__ import annotations
from ugk.governance.posture import GovernancePosture


# Structural attributes consulted by GovernancePosture.compute(). Order
# matches the read order in ugk/posture.py compute() body — required
# first, then optional. Useful for new-integrator orientation.
_REQUIRED_ATTRS: tuple[str, ...] = (
    "store",                       # required: receipt store with verify_stream_hash / receipt_count
    "_session_dkn",                # required: session identifier (truthy implies founded)
    "_law_hash",                   # required: law_hash string
    "_authority_model",            # optional: AuthorityModel | None — None → "undeclared"
    "_require_scoped_intent",      # optional: bool — getattr-defaulted to False
    "_will_store",                 # optional: will store | None — getattr-defaulted to None
)


def required_attributes() -> tuple[str, ...]:
    """Return the tuple of structural attributes GovernancePosture.compute()
    reads from its argument. Provided for integrator guidance: any
    kernel-shaped object exposing these attributes will compute a valid
    posture, with honest-absent semantics filling unmanaged dimensions.
    """
    return _REQUIRED_ATTRS


class _StoreShim:
    """Kernel-duck-typed facade over a receipt-only consumer.

    Exposes exactly the structural attributes GovernancePosture.compute()
    reads. Optional attributes default to honest-absent values
    (authority_model=None → 'undeclared'; will_store=None;
    require_scoped_intent=False).
    """
    __slots__ = ("store", "_session_dkn", "_law_hash",
                 "_authority_model", "_require_scoped_intent", "_will_store")

    def __init__(self, store, *, session_dkn: str = "", law_hash: str = "",
                 authority_model=None, require_scoped_intent: bool = False,
                 will_store=None):
        self.store                  = store
        self._session_dkn           = session_dkn
        self._law_hash              = law_hash
        self._authority_model       = authority_model
        self._require_scoped_intent = require_scoped_intent
        self._will_store            = will_store


def compute(kernel) -> GovernancePosture:
    """Mode 1: compute the CGP posture from a GovernanceKernel-shaped
    object. One obvious call for direct-kernel consumers.

    Equivalent to ``GovernancePosture.compute(kernel)``; re-exported here
    so the verb "compute the CGP posture" lives under the canonical
    ``ugk.cgp`` surface.
    """
    return GovernancePosture.compute(kernel)


def compute_from_store(store, *, session_dkn: str = "", law_hash: str = "",
                       authority_model=None) -> GovernancePosture:
    """Mode 2: compute the CGP posture from a UGKReceiptStore-only
    consumer state. One obvious call for store-only consumers (e.g.
    CPVM's AuthoritativeChain).

    Wraps the store in a kernel-duck-typed shim and delegates to
    GovernancePosture.compute(). Organs the consumer does not manage
    yield honest-absent matrix cells in the resulting posture.

    Required keyword arguments:
        store         — the UGKReceiptStore instance (or any object
                        exposing verify_stream_hash() and receipt_count())
        session_dkn   — the session identifier (truthy → founded session)
        law_hash      — the consumer's law_hash string

    Optional:
        authority_model — an AuthorityModel instance, or None
                          (None → posture.authority_model == "undeclared")
    """
    shim = _StoreShim(store, session_dkn=session_dkn, law_hash=law_hash,
                      authority_model=authority_model)
    return GovernancePosture.compute(shim)
