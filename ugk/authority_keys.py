"""Compatibility shim: ugk.authority_keys moved to ugk.authority.authority_keys (v0.1.0 path-decoupling reorg).
Legacy path `from ugk.authority_keys import ...` preserved through v0.1.x; canonical is ugk.authority.authority_keys."""
from ugk.authority.authority_keys import *  # noqa: F401,F403
from ugk.authority import authority_keys as _canonical
import sys as _sys
_sys.modules[__name__].__dict__.update({k:v for k,v in _canonical.__dict__.items() if not k.startswith('__')})
