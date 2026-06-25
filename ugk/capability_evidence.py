"""Compatibility shim: ugk.capability_evidence moved to ugk.authority.capability_evidence (v0.1.0 path-decoupling reorg).
Legacy path `from ugk.capability_evidence import ...` preserved through v0.1.x; canonical is ugk.authority.capability_evidence."""
from ugk.authority.capability_evidence import *  # noqa: F401,F403
from ugk.authority import capability_evidence as _canonical
import sys as _sys
_sys.modules[__name__].__dict__.update({k:v for k,v in _canonical.__dict__.items() if not k.startswith('__')})
