"""Compatibility shim: ugk.a1_verifier moved to ugk.authority.a1_verifier (v0.1.0 path-decoupling reorg).
Legacy path `from ugk.a1_verifier import ...` preserved through v0.1.x; canonical is ugk.authority.a1_verifier."""
from ugk.authority.a1_verifier import *  # noqa: F401,F403
from ugk.authority import a1_verifier as _canonical
import sys as _sys
_sys.modules[__name__].__dict__.update({k:v for k,v in _canonical.__dict__.items() if not k.startswith('__')})
