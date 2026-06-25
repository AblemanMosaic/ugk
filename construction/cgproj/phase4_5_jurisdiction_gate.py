#!/usr/bin/env python3
"""Phase 4.5 — Jurisdiction Gate (CGProj).

Proves projections are a DISTINCT jurisdiction — the full triangle, all legs held in one invocation.
Distinct from the Non-Authority Gate (7.1): that proved projections don't INFLUENCE execution; this
proves the two jurisdictions are MUTUALLY INDEPENDENT (separation, not just non-influence).

  Leg 1 — Execution survives without Projection (carried from Phase 2; re-asserted here).
  Obligation A — Metadata-sensitivity: Documentation is causally downstream of Projection.
       A1 mutation propagates to the predicted place.
       A2 distinct mutations produce outputs each CONTAINING ITS OWN mutated value (causal linkage).
       A3 content-hash tracks the mutation.
  Obligation B — Execution-independence: regeneration is causally independent of Execution.
       B1 regeneration under a PROVEN-ACTIVE execution import barrier is byte-identical to baseline.
       B2 regeneration with execution modules physically DELETED is byte-identical to baseline.

Both gates consume the SAME execution-jurisdiction definition (execution_jurisdiction.py) so the
boundary cannot drift. Run from repo root:  python phase4_5_jurisdiction_gate.py <repo_dir>
Exit 0 = PASS; nonzero = STOP (jurisdictions entangled; architecture core claim fails).
"""
import sys, os, subprocess, tempfile, shutil, dataclasses, stat

PY = sys.executable
REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import execution_jurisdiction as EJ
sys.path.insert(0, REPO)

results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    line = "  " + ("PASS" if ok else "FAIL") + "  " + name
    if detail:
        line += " — " + detail
    print(line)

from ugk.projections import generate as G
from ugk.projections import render as RND
from ugk.projections import hash as H
from ugk.projections import patterns as P


def gen_dir(repo):
    return os.path.join(repo, "ugk", "projections", "generated")


def _make_writable(path):
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _remove_file(path):
    _make_writable(path)
    os.remove(path)


def _rmtree(path):
    def _onerror(func, p, _exc):
        _make_writable(p)
        func(p)
    shutil.rmtree(path, onerror=_onerror)


# ============ Leg 1 — execution survives without projection (carried; re-run) ============
SURFACE = [
    ("78 gates", "ugk.conformance.run_gates_batch"),
    ("39 vectors", "ugk.conformance.m2_vectors_runner"),
]
def _ok(out):
    import re
    mf = re.search(r"(\d+)\s+failed", out)
    if mf and int(mf.group(1)) == 0 and re.search(r"ALL PASS|PASS \(\d+ not-established\)", out):
        return True  # posture-tolerant: 0 failed + PASS verdict (not-established warning tolerated; problem #3)
    m = re.findall(r"(\d+)/(\d+)\s+passed", out)
    return bool(m) and all(a == b for a, b in m)
tmp = tempfile.mkdtemp(); dst = os.path.join(tmp, "repo")
shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
shutil.rmtree(os.path.join(dst, "ugk", "projections"))
leg1_ok = True
for _label, mod in SURFACE:
    e = {**os.environ, "PYTHONPATH": dst, "UGK_GENESIS_DIR": tempfile.mkdtemp(),
         "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8:backslashreplace"}
    p = EJ.bounded_run([PY, "-m", mod], cwd=dst, env=e, timeout=120)  # bounded (problem #2)
    leg1_ok = leg1_ok and _ok(p.stdout + p.stderr)
check("Leg 1: execution surface passes with ugk/projections/ DELETED", leg1_ok)

# ============ Obligation A — metadata-sensitivity ============
# baseline: regeneration matches disk (Phase 4 result, re-asserted as the experiment baseline)
def read_artifact(repo, name):
    with open(os.path.join(gen_dir(repo), name), "rb") as f:
        return f.read()
base_match = all(
    read_artifact(REPO, n) == G.generate_artifact(n).encode("utf-8") for n in G.ARTIFACTS
)
check("A baseline: unmutated regeneration matches on-disk artifacts", base_match)

# A1 — mutate one pattern's title; regeneration must change IN THE PREDICTED PLACE.
orig = P.PATTERNS
MARK1 = "ZZMARKER_ONE_7f3a"
mutated1 = list(orig); mutated1[0] = dataclasses.replace(mutated1[0], title=mutated1[0].title + " " + MARK1)
patt_name = next(n for n, (label, _) in G.ARTIFACTS.items() if label == "patterns")
base_body = RND.render_patterns()
mut1_body = RND.render_patterns(patterns=tuple(mutated1))
a1_changed = (mut1_body != base_body)
a1_marker_in_mut = (MARK1 in mut1_body)
a1_marker_not_in_base = (MARK1 not in base_body)
check("A1: metadata mutation propagates to predicted place (marker present only after mutation)",
      a1_changed and a1_marker_in_mut and a1_marker_not_in_base,
      "changed=" + str(a1_changed) + " marker_in_mutated=" + str(a1_marker_in_mut)
      + " marker_absent_in_base=" + str(a1_marker_not_in_base))

# A2 — distinct mutations -> outputs EACH CONTAINING ITS OWN mutated value (causal linkage formal).
MARK_A = "ZZMARK_ALPHA_11aa"; MARK_B = "ZZMARK_BETA_22bb"
mutA = list(orig); mutA[0] = dataclasses.replace(mutA[0], title=mutA[0].title + " " + MARK_A)
mutB = list(orig); mutB[0] = dataclasses.replace(mutB[0], title=mutB[0].title + " " + MARK_B)
outA = RND.render_patterns(patterns=tuple(mutA))
outB = RND.render_patterns(patterns=tuple(mutB))
a2_distinct = (outA != outB)
a2_A_has_A = (MARK_A in outA) and (MARK_B not in outA)
a2_B_has_B = (MARK_B in outB) and (MARK_A not in outB)
check("A2: distinct mutations yield outputs EACH containing its own mutated value (causal linkage)",
      a2_distinct and a2_A_has_A and a2_B_has_B,
      "distinct=" + str(a2_distinct) + " A_contains_only_A=" + str(a2_A_has_A)
      + " B_contains_only_B=" + str(a2_B_has_B))

# A3 — content-hash tracks the mutation.
ch_base = H.content_hash()
ch_mut = H.content_hash(patterns=tuple(mutated1))
check("A3: content_hash tracks metadata mutation (base != mutated)",
      ch_base != ch_mut, "base=" + ch_base[:12] + "… mutated=" + ch_mut[:12] + "…")

# ============ Obligation B — execution-independence ============
# B1 — regenerate under a PROVEN-ACTIVE execution import barrier; byte-identical to baseline.
# Same-process barrier (no sitecustomize ordering dependence): prelude installs the meta_path barrier
# and writes the sentinel BEFORE regeneration runs in that same process.
sentinel = os.path.join(tempfile.mkdtemp(), "BAR_LOADED")
regen_code = (
    "from ugk.projections import generate as G\n"
    "import json\n"
    "print(json.dumps({n: G.generate_artifact(n) for n in G.ARTIFACTS}))\n"
)
pr = EJ.run_code_under_barrier(PY, regen_code, EJ.EXECUTION_MODULE_PREFIXES, sentinel, REPO,
                               env={**os.environ}, cwd=REPO)
sentinel_written = os.path.exists(sentinel)
# positive control: importing an execution module under the SAME barrier prelude RAISES
pos = EJ.run_code_under_barrier(PY, "import ugk.kernel\n", EJ.EXECUTION_MODULE_PREFIXES,
                                os.path.join(tempfile.mkdtemp(), "S"), REPO, env={**os.environ}, cwd=REPO)
bar_raises = pos.returncode != 0 and "barred jurisdiction module" in (pos.stderr + pos.stdout)
# negative control: WITHOUT the barrier, importing it SUCCEEDS
neg = subprocess.run([PY, "-c", "import sys; sys.path.insert(0, %r); import ugk.kernel; print('ok')" % REPO],
                     cwd=REPO, capture_output=True, text=True, env={**os.environ})
bar_is_cause = "ok" in neg.stdout
barred = sentinel_written and bar_raises and bar_is_cause
# compare barred-regen output to baseline regen
import json as _json
b1_identical = False
regen_nonempty = False
if pr.returncode == 0:
    try:
        regen = _json.loads(pr.stdout)
        baseline = {n: G.generate_artifact(n) for n in G.ARTIFACTS}
        b1_identical = (regen == baseline)
        regen_nonempty = all(len(v) > 0 for v in regen.values()) and len(regen) == len(G.ARTIFACTS)
    except Exception:
        pass
check("B1: regeneration under PROVEN-ACTIVE execution barrier is byte-identical to baseline",
      barred and b1_identical and regen_nonempty,
      "barrier_active=" + str(barred) + " identical=" + str(b1_identical)
      + " nonempty=" + str(regen_nonempty)
      + " (sentinel=" + str(sentinel_written) + " bar_raises=" + str(bar_raises)
      + " bar_is_cause=" + str(bar_is_cause) + ")")

# B2 — regenerate with execution modules physically DELETED; byte-identical to baseline.
tmp2 = tempfile.mkdtemp(); dst2 = os.path.join(tmp2, "repo")
shutil.copytree(REPO, dst2, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
# delete execution-jurisdiction files (named set) + conformance dir + heavy execution dirs
removed = []
for rel in EJ.EXECUTION_MODULE_FILES:
    pth = os.path.join(dst2, rel)
    if os.path.exists(pth):
        _remove_file(pth); removed.append(rel)
for d in ("ugk/conformance", "ugk/scale"):
    pth = os.path.join(dst2, d)
    if os.path.isdir(pth):
        _rmtree(pth); removed.append(d + "/")
regen_code_b2 = ("import sys; sys.path.insert(0, " + repr(dst2) + ")\n"
                 "from ugk.projections import generate as G\n"
                 "import json\n"
                 "print(json.dumps({n: G.generate_artifact(n) for n in G.ARTIFACTS}))\n")
pr2 = subprocess.run([PY, "-c", regen_code_b2], cwd=dst2, capture_output=True,
                     text=True, env={**os.environ})
b2_identical = False
if pr2.returncode == 0:
    try:
        regen2 = _json.loads(pr2.stdout)
        baseline = {n: G.generate_artifact(n) for n in G.ARTIFACTS}
        b2_identical = (regen2 == baseline)
    except Exception:
        pass
check("B2: regeneration with execution modules DELETED is byte-identical to baseline",
      b2_identical and len(removed) > 0,
      "removed=" + str(len(removed)) + " execution paths; identical=" + str(b2_identical))

# ============ static corroboration (not the proof) ============
import ast
purity_bad = []
for fn in ("render.py", "hash.py", "generate.py"):
    src = open(os.path.join(REPO, "ugk", "projections", fn), encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        ms = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        for m in ms:
            if m.startswith("ugk") and not m.startswith("ugk.projections"):
                purity_bad.append((fn, m))
check("static corroboration: render/hash/generate import only ugk.projections.* + stdlib",
      not purity_bad, str(purity_bad) if purity_bad else "clean")

ok = all(r[1] for r in results)
print("\n  content_hash = " + H.content_hash())
print("  shared execution-jurisdiction prefixes = " + str(EJ.EXECUTION_MODULE_PREFIXES))
print("\n  PHASE 4.5 JURISDICTION GATE: " + ("PASS" if ok else "FAIL — STOP, jurisdictions entangled"))
sys.exit(0 if ok else 1)
