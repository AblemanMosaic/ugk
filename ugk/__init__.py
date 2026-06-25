"""ugk — Universal Governance Kernel v0.1.0.

Phase 1 standalone Python package.  Zero external dependencies (stdlib only).

Primary API:
    GovernanceKernel    — W/G/E reactor with three-tier op jurisdiction
    GOVERNANCE_OPS      — declared op registry (BS-01)
    srsa_vector         — 10-axis SRSA baseline vector
    LocalBrokerServer   — in-process broker (dev/test)
    BrokerClient        — abstract broker interface

Conformance:
    ugk.conformance.run_gates_batch — 78-gate conformance suite (+ 39 M2 vectors)
"""

# --- X-b launcher shim (state isolation) ---------------------------------------
# Governor identity binds at kernel IMPORT time (see ugk.kernel) from genesis_dir(),
# which honors UGK_GENESIS_DIR. The CLI's --state-dir must therefore be reflected into
# UGK_GENESIS_DIR BEFORE the kernel import below — i.e. before main()/argparse run.
# This CLI-scoped pre-parse does exactly that, and nothing else:
#   * Only acts when this process is a ugk CLI invocation (argv[0] is the ugk console
#     script or `python -m ugk[.cli]`), so a plain library `import ugk` never absorbs an
#     unrelated --state-dir from argv.
#   * Precedence preserved: an already-set UGK_GENESIS_DIR is NEVER overridden.
#   * Identity stays immutable-at-import: we only set the resolution SOURCE before the one
#     and only bind; we do not reload or mutate identity (NOT lazy resolution / X-a).
def _cli_state_dir_preimport_hook():
    import os, sys
    if os.environ.get("UGK_GENESIS_DIR"):
        return  # explicit env wins; never override
    argv = sys.argv
    arg0 = (argv[0] or "") if argv else ""
    # Entry paths where this IS the ugk CLI:
    #   * console script           → argv[0] ends with 'ugk' (…/bin/ugk)
    #   * python path/to/cli.py    → argv[0] ends with 'cli.py'
    #   * python -m ugk.cli        → argv[0] is '-m' (runpy sets it before fixing argv)
    # A plain library `import ugk` has none of these, so --state-dir is never absorbed.
    base = os.path.basename(arg0)
    is_cli = (arg0 == "-m"
              or base in ("ugk", "ugk.cli", "cli.py")
              or base.startswith("ugk"))
    if not is_cli:
        return
    sd = None
    for i, tok in enumerate(argv[1:], start=1):
        if tok == "--state-dir" and i + 1 < len(argv):
            sd = argv[i + 1]; break
        if tok.startswith("--state-dir="):
            sd = tok.split("=", 1)[1]; break
    sd = sd or os.environ.get("UGK_STATE_DIR") or os.environ.get("ACIS_STATE_DIR")
    if sd:
        os.environ["UGK_GENESIS_DIR"] = sd

_cli_state_dir_preimport_hook()
# -------------------------------------------------------------------------------

# Lazy public-API exports (PEP 562). Importing `ugk` must NOT eagerly load the
# execution jurisdiction (kernel, governance, storage, authority, transport,
# schema, core). Each public name is resolved on first access via __getattr__,
# imported from its module at that point, and cached into module globals.
#
# Why: a non-execution surface (e.g. ugk.projections — the CGProj projection
# jurisdiction) must be importable without dragging in execution. With eager
# imports here, `import ugk.projections` would import the parent `ugk` package
# first and pull the whole kernel in. Lazy resolution severs that: `import ugk`
# (and `import ugk.projections`) load zero execution modules until a public
# execution symbol is actually requested.
#
# Public contract preserved EXACTLY:
#   * `from ugk import GovernanceKernel`  → triggers __getattr__, works as before
#   * `import ugk; ugk.GovernanceKernel`  → same
#   * `from ugk import *`                 → uses __all__ (each name resolved lazily)
#   * accessing a bogus attribute         → AttributeError (standard semantics)
# No symbol is added or removed; only the import *timing* changes.

# name -> module path it is imported from
_LAZY_EXPORTS = {
    # ugk.kernel
    "GovernanceKernel": "ugk.kernel",
    "STATUS_UNINITIALIZED": "ugk.kernel",
    "STATUS_ACTIVE": "ugk.kernel",
    "GOVERNOR_PUBKEY_HEX": "ugk.kernel",
    "CLASSIFIED_REMAINDERS": "ugk.kernel",
    "GateRefusal": "ugk.kernel",
    "KernelInternalOp": "ugk.kernel",
    "GovernanceNotFounded": "ugk.kernel",
    "UndeclaredOp": "ugk.kernel",
    # ugk.schema
    "GOVERNANCE_OPS": "ugk.schema",
    # ugk.transport.broker
    "BrokerClient": "ugk.transport.broker",
    "LocalBrokerServer": "ugk.transport.broker",
    # ugk.governance.governor
    "GovernorSignatureRequired": "ugk.governance.governor",
    "verify_governor": "ugk.governance.governor",
    "governor_key_status": "ugk.governance.governor",
    # ugk.core.srsa
    "srsa_vector": "ugk.core.srsa",
    # public types used by canonical examples
    "UGKReceiptStore": "ugk.storage.store",
    "WarrantStore": "ugk.governance.warrant",
    "DeploymentManifest": "ugk.charter",
    "write_charter_artifacts": "ugk.charter",
}


def __getattr__(name):
    """PEP 562 lazy attribute resolution for public API exports."""
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    module = importlib.import_module(module_path)
    value = getattr(module, name)
    globals()[name] = value   # cache so subsequent access skips __getattr__
    return value


def __dir__():
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))


__version__ = "0.1.0"
__all__ = [
    "GovernanceKernel",
    "STATUS_UNINITIALIZED", "STATUS_ACTIVE",
    "GOVERNOR_PUBKEY_HEX", "CLASSIFIED_REMAINDERS",
    "GateRefusal", "KernelInternalOp", "GovernanceNotFounded", "UndeclaredOp",
    "GOVERNANCE_OPS",
    "BrokerClient", "LocalBrokerServer",
    "srsa_vector",
    "UGKReceiptStore", "WarrantStore",
    "DeploymentManifest", "write_charter_artifacts",
]
