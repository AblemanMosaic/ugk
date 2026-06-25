#!/usr/bin/env python3
"""Phase 3 — Determinism Gate (CGProj).

Proves the projection renderer + hash are a DETERMINISTIC metadata -> bytes function, so Phase 4
fidelity can later be meaningful. Checks (design note), each with teeth:

  1. Repeat-run identity: render_all() / content_hash() identical across N in-process calls.
  2. Cross-process identity: identical across separate interpreters with DIFFERENT PYTHONHASHSEED.
  3. Order-independence (TEETH): a SHUFFLED copy of patterns/domain_mappings yields byte-identical
     output and identical content_hash.
       - Negative control: an intentionally-UNSORTED renderer DOES differ under shuffle, proving
         the shuffle test is not vacuous (it can detect order-dependence).
  4. Hash separation: content_hash != render_hash; bumping RENDERER_VERSION changes render_hash but
     NOT content_hash.
  5. Purity / no-execution: importing render+hash loads no execution-jurisdiction module.

Run from repo root:  python phase3_determinism_gate.py <repo_dir>
Exit 0 = PASS; nonzero = STOP (a nondeterministic projection cannot be hash-verified).
"""
import sys, os, subprocess, random

PY = sys.executable
REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    line = "  " + ("PASS" if ok else "FAIL") + "  " + name
    if detail:
        line += " — " + detail
    print(line)

from ugk.projections import render as R
from ugk.projections import hash as H
from ugk.projections.patterns import PATTERNS
from ugk.projections.domain_mappings import DOMAIN_MAPPINGS

# 1. Repeat-run identity
outs = {R.render_all() for _ in range(5)}
chs = {H.content_hash() for _ in range(5)}
check("1 repeat-run identity (render + content_hash stable across 5 calls)",
      len(outs) == 1 and len(chs) == 1,
      "render variants=" + str(len(outs)) + " content_hash variants=" + str(len(chs)))

# 2. Cross-process identity under varied PYTHONHASHSEED
probe = ("import sys; sys.path.insert(0, %r);"
         "from ugk.projections import render as R, hash as H;"
         "print(H.content_hash()); print(__import__('hashlib').sha256(R.render_all().encode()).hexdigest())"
         % REPO)
proc_hashes = []
for seed in ("0", "1", "12345", "98765"):
    e = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": REPO}
    p = subprocess.run([PY, "-c", probe], capture_output=True, text=True, env=e, cwd=REPO)
    proc_hashes.append(p.stdout.strip())
check("2 cross-process identity (4 procs, varied PYTHONHASHSEED)",
      len(set(proc_hashes)) == 1,
      "distinct outputs across procs=" + str(len(set(proc_hashes))))

# 3. Order-independence with shuffle (TEETH)
def shuffled(seq):
    lst = list(seq)
    random.Random(20260614).shuffle(lst)
    return tuple(lst)
sp = shuffled(PATTERNS)
sd = shuffled(DOMAIN_MAPPINGS)
# guard: shuffle actually changed input order (else the test would be vacuous)
shuffle_changed = (tuple(p.id for p in sp) != tuple(p.id for p in PATTERNS)
                   or tuple(d.id for d in sd) != tuple(d.id for d in DOMAIN_MAPPINGS))
base_out = R.render_all()
shuf_out = R.render_all(patterns=sp, domain_mappings=sd)
base_ch = H.content_hash()
shuf_ch = H.content_hash(patterns=sp, domain_mappings=sd)
check("3 order-independence (shuffled input -> identical output + content_hash)",
      shuffle_changed and base_out == shuf_out and base_ch == shuf_ch,
      "shuffle_changed_input=" + str(shuffle_changed)
      + " output_identical=" + str(base_out == shuf_out)
      + " hash_identical=" + str(base_ch == shuf_ch))

# 3-neg. Negative control: an intentionally UNSORTED renderer MUST differ under shuffle.
#        Proves the shuffle test in (3) can actually detect order-dependence (not vacuous).
def render_unsorted(patterns):
    # deliberately DO NOT sort — emit in argument order
    from dataclasses import asdict
    return "\n".join("## " + asdict(p)["title"] for p in patterns)
neg_base = render_unsorted(PATTERNS)
neg_shuf = render_unsorted(sp)
check("3-neg (teeth) unsorted renderer DIFFERS under shuffle (shuffle test is not vacuous)",
      shuffle_changed and neg_base != neg_shuf,
      "unsorted_base==unsorted_shuf? " + str(neg_base == neg_shuf) + " (must be False)")

# 4. Hash separation
ch = H.content_hash()
rh = H.render_hash()
sep = (ch != rh)
# bumping renderer version changes render_hash but not content_hash
orig_ver = H.RENDERER_VERSION
try:
    H.RENDERER_VERSION = orig_ver + "-bumped"
    rh2 = H.render_hash()
    ch2 = H.content_hash()
finally:
    H.RENDERER_VERSION = orig_ver
render_moved = (rh2 != rh)
content_stable = (ch2 == ch)
check("4 hash separation (content != render; version bump moves render hash only)",
      sep and render_moved and content_stable,
      "content!=render=" + str(sep) + " render_moved_on_version_bump=" + str(render_moved)
      + " content_stable=" + str(content_stable))

# 5. Purity / no-execution: importing render+hash loads no execution-jurisdiction module
probe2 = ("import sys; sys.path.insert(0, %r);"
          "import ugk.projections.render, ugk.projections.hash;"
          "ex=('ugk.kernel','ugk.invariants','ugk.module_registry','ugk.storage','ugk.governance','ugk.authority','ugk.scale');"
          "print([m for m in sys.modules if any(m==e or m.startswith(e+'.') for e in ex)])"
          % REPO)
p = subprocess.run([PY, "-c", probe2], capture_output=True, text=True,
                   env={**os.environ, "PYTHONPATH": REPO}, cwd=REPO)
leaked = p.stdout.strip()
check("5 purity (importing render+hash loads no execution module)",
      leaked == "[]", "execution modules loaded: " + leaked)

ok = all(r[1] for r in results)
print("\n  content_hash = " + ch)
print("  render_hash  = " + rh)
print("  PROJECTION_IDENTITY = " + H.PROJECTION_IDENTITY)
print("\n  PHASE 3 DETERMINISM GATE: " + ("PASS" if ok else "FAIL — STOP"))
sys.exit(0 if ok else 1)
