"""Compatibility shim: ugk.authority_model moved to ugk.authority.authority_model (v0.1.0 path-decoupling reorg).
Legacy path `from ugk.authority_model import ...` preserved through v0.1.x; canonical is ugk.authority.authority_model."""
from ugk.authority.authority_model import *  # noqa: F401,F403
from ugk.authority import authority_model as _canonical
import sys as _sys
_sys.modules[__name__].__dict__.update({k:v for k,v in _canonical.__dict__.items() if not k.startswith('__')})
