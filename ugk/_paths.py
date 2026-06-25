"""ugk/_paths.py — deployer-configurable filesystem paths.

The genesis/ directory is resolved here so that pip-installed deployments
(where the package lives in site-packages) can specify a writable charter
location via the environment, while source-checkout / extracted-archive
deployments (where genesis/ ships alongside the ugk/ package) keep working
without configuration.

Precedence (deterministic, no silent semantics):
  1. $UGK_GENESIS_DIR  — deployer override; the only safe path for pip installs
  2. <package_root>/../genesis  — source-checkout/archive default; matches the
                                  ship layout where ugk/ and genesis/ are siblings

The fallback is byte-equivalent to the prior hardcoded resolution
(`Path(__file__).parent.parent / "genesis"` from any ugk/*.py file), so
existing tests, gate suite, and the conformance fixture's ephemeral founding
are all unaffected when the env var is unset.
"""
from __future__ import annotations
import os
from pathlib import Path


def genesis_dir() -> Path:
    """Resolve the deployment's genesis/ directory.

    Honors UGK_GENESIS_DIR if set; otherwise returns the package-adjacent
    default. Returns a Path without checking existence — callers handle
    missing/empty genesis explicitly (CHARTER-S-01 fail-closed).
    """
    env = os.environ.get("UGK_GENESIS_DIR")
    if env:
        return Path(env)
    return Path(__file__).parent.parent / "genesis"
