#!/usr/bin/env python3
"""Read-only: report what importing ugk pulls in / binds at import time."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
before = set(sys.modules)
import ugk
pulled = sorted(m for m in sys.modules if m.startswith("ugk") and m not in before)
print(f"import ugk pulls {len(pulled)} submodules at import time:")
for m in pulled: print("  ", m)
from ugk.kernel import GOVERNOR_PUBKEY_HEX
bound = not str(GOVERNOR_PUBKEY_HEX).startswith("GOVERNOR_KEY_UNSET")
print(f"governor identity bound at import: {bound} (sentinel={not bound})")
