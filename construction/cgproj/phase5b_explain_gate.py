#!/usr/bin/env python3
"""Phase 5b — Explain Surface Gate (CGProj).

Proves explain can be added without a new authority surface or a new semantic-drift surface.
E1 determinism+purity | E2 non-invention | E3 explain/doc agreement | E4 bidirectional independence
| E5 corpus completeness. Each with a negative control that fails through the real gate path.

Narrow claim: explain is a deterministic, non-inventing projection of the corpus, mutually
independent of execution, and the corpus is complete across docs+explain.

Run from repo root:  python phase5b_explain_gate.py <repo_dir>
Exit 0 = PASS; nonzero = FAIL (fails closed).
"""
import sys, os, subprocess, tempfile, shutil, random, json

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

from ugk.projections import explain as EX
from ugk.projections import docs as DOCS
from ugk.projections import patterns as P
from ugk.projections import domain_mappings as DM

# corpus truth sets (for non-invention)
def _pattern_prims(p):
    return set(p.primitives) | {x for s in p.seams for x in s.ugk_primitives}
def _domain_prims(d):
    return {x for s in d.integration_points for x in s.ugk_primitives}
CORPUS_PAT = {p.id: _pattern_prims(p) for p in P.PATTERNS}
CORPUS_PAT_REFS = {d.id: set(d.patterns) for d in DM.DOMAIN_MAPPINGS}
CORPUS_DOM = {d.id: _domain_prims(d) for d in DM.DOMAIN_MAPPINGS}

# ---------- E1: determinism + purity ----------
runs = [EX.explain_projections() for _ in range(5)]
e1_repeat = all(r == runs[0] for r in runs)
# cross-process under varied PYTHONHASHSEED
probe = ("import sys,json; sys.path.insert(0,%r);"
         "from ugk.projections import explain as EX;"
         "print(json.dumps(EX.explain_projections(), sort_keys=True))" % REPO)
ph = []
for seed in ("0", "1", "12345", "98765"):
    p = subprocess.run([PY, "-c", probe], capture_output=True, text=True,
                       env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": REPO}, cwd=REPO)
    ph.append(p.stdout.strip())
e1_xproc = len(set(ph)) == 1
# shuffle order-independence + unsorted neg-control
sp = list(P.PATTERNS); random.Random(7).shuffle(sp)
sd = list(DM.DOMAIN_MAPPINGS); random.Random(8).shuffle(sd)
e1_shuf = EX.explain_projections(patterns=tuple(sp), domain_mappings=tuple(sd)) == EX.explain_projections()
shuffle_changed = [p.id for p in sp] != [p.id for p in P.PATTERNS]
# purity: importing explain loads no execution module
pr = subprocess.run([PY, "-c",
    "import sys; sys.path.insert(0,%r); import ugk.projections.explain;" % REPO +
    "ex=%r;" % (EJ.EXECUTION_MODULE_PREFIXES,) +
    "print([m for m in sys.modules if any(m==e or m.startswith(e+'.') for e in ex)])"],
    capture_output=True, text=True, env={**os.environ, "PYTHONPATH": REPO}, cwd=REPO)
e1_pure = pr.stdout.strip() == "[]"
check("E1 determinism + purity (repeat, cross-process, shuffle-independent, no-execution-import)",
      e1_repeat and e1_xproc and e1_shuf and shuffle_changed and e1_pure,
      "repeat=%s xproc=%s shuffle_indep=%s pure=%s" % (e1_repeat, e1_xproc, e1_shuf, e1_pure))

# ---------- E2: non-invention (shared checker; the load-bearing burden) ----------
def invention_violations(projections):
    """Return list of (key, claim) where explain cites something NOT in the corpus."""
    bad = []
    for key, text in projections.items():
        kind, oid = key.split(":", 1)
        prims = set(EX.cited_primitives(text))
        if kind == "pattern":
            allowed = CORPUS_PAT.get(oid, set())
            bad += [(key, "prim:" + x) for x in prims - allowed]
        else:
            allowed = CORPUS_DOM.get(oid, set())
            bad += [(key, "prim:" + x) for x in prims - allowed]
            refs = set(EX.cited_pattern_refs(text))
            bad += [(key, "ref:" + x) for x in refs - CORPUS_PAT_REFS.get(oid, set())]
    return bad

e2_real = invention_violations(EX.explain_projections())
check("E2 non-invention: every cited claim traceable to corpus (omit ok, rephrase ok)",
      not e2_real, "violations=" + str(e2_real) if e2_real else "all cited claims in corpus")
# neg control (invention): inject an explain entry citing a primitive not in corpus -> MUST flag
inj = dict(EX.explain_projections())
k0 = next(k for k in inj if k.startswith("pattern:"))
inj[k0] = inj[k0].replace("primitives: ", "primitives: INVENTED-PRIMITIVE-zzz | ", 1)
e2_teeth = len(invention_violations(inj)) > 0
check("  (neg-control) injected invented primitive IS flagged (E2 has teeth)", e2_teeth,
      "flagged=" + str(e2_teeth))
# neg control (omission allowed): drop a primitive -> must NOT flag (omit is legal)
omit = dict(EX.explain_projections())
k1 = next(k for k in omit if k.startswith("pattern:"))
prims1 = EX.cited_primitives(omit[k1])
if len(prims1) > 1:
    omit[k1] = omit[k1].replace("primitives: " + " | ".join(prims1),
                                "primitives: " + " | ".join(prims1[1:]), 1)
e2_omit_ok = len(invention_violations(omit)) == 0
check("  (control) omission (citing a subset) is allowed (does NOT flag)", e2_omit_ok)

# ---------- E3: explain/doc agreement (identity, boundary, primitive consistency) ----------
doc_arts = DOCS.doc_artifacts()
def doc_for(kind, oid):
    rel = ("docs/patterns/" if kind == "pattern" else "docs/domain-mappings/") + oid + ".md"
    return doc_arts.get(rel, "")
def agreement_violations(projections):
    bad = []
    for key, text in projections.items():
        kind, oid = key.split(":", 1)
        doc = doc_for(kind, oid)
        # identity: explain references PROJECTION_IDENTITY; doc embeds same in its header
        if EX.boundary_marker(text) not in ("present", "absent"):
            bad.append((key, "no-boundary-marker"))
        # boundary agreement: doc has a front-loaded '>' boundary <=> explain says present
        doc_has_boundary = "\n> " in doc
        exp_says = EX.boundary_marker(text) == "present"
        if doc_has_boundary != exp_says:
            bad.append((key, "boundary-contradiction exp=%s doc=%s" % (exp_says, doc_has_boundary)))
        # primitive consistency: every primitive explain cites must appear in the doc text
        for prim in EX.cited_primitives(text):
            if prim not in doc:
                bad.append((key, "prim-not-in-doc:" + prim))
    return bad
e3_real = agreement_violations(EX.explain_projections())
check("E3 explain/doc agreement (identity, boundary, primitive consistency; no contradiction)",
      not e3_real, "violations=" + str(e3_real[:3]) if e3_real else "explain and docs agree")
# neg control (desync): explain asserts boundary absent where doc has one -> contradiction
desync = dict(EX.explain_projections())
kd = next(k for k in desync if k.startswith("domain:"))
desync[kd] = desync[kd].replace("boundary: present", "boundary: absent", 1)
e3_teeth = len(agreement_violations(desync)) > 0
check("  (neg-control) desynchronized explain (boundary contradiction) IS flagged (E3 has teeth)",
      e3_teeth)

# ---------- E4: bidirectional independence ----------
# E4a static: no execution module imports explain; explain imports no execution
exec_imports_explain = []
for path in EJ.static_scan_files(REPO):
    src = open(path, encoding="utf-8").read()
    if "ugk.projections.explain" in src or "projections import explain" in src:
        exec_imports_explain.append(os.path.relpath(path, REPO))
import ast
explain_imports_exec = []
for n in ast.walk(ast.parse(open(os.path.join(REPO, "ugk", "projections", "explain.py"), encoding="utf-8").read())):
    ms = [a.name for a in n.names] if isinstance(n, ast.Import) else ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
    for m in ms:
        if m.startswith("ugk") and not m.startswith("ugk.projections"):
            explain_imports_exec.append(m)
check("E4a static: execution imports no explain; explain imports no execution",
      not exec_imports_explain and not explain_imports_exec,
      "exec->explain=%s explain->exec=%s" % (exec_imports_explain, explain_imports_exec))

# E4b explain independent of execution: render under execution barrier (byte-identical) + removed
# Same-process barrier (no sitecustomize ordering dependence): the prelude installs the meta_path
# barrier and writes the sentinel BEFORE the explain render runs in the same process.
sentinel = os.path.join(tempfile.mkdtemp(), "S")
render_code = ("import json\n"
               "from ugk.projections import explain as EX\n"
               "print(json.dumps(EX.explain_projections(), sort_keys=True))\n")
pr2 = EJ.run_code_under_barrier(PY, render_code, EJ.EXECUTION_MODULE_PREFIXES, sentinel, REPO,
                                env={**os.environ}, cwd=REPO)
sent_ok = os.path.exists(sentinel)
# positive control: importing an execution module under the SAME barrier prelude raises
pos = EJ.run_code_under_barrier(PY, "import ugk.kernel\n", EJ.EXECUTION_MODULE_PREFIXES,
                                os.path.join(tempfile.mkdtemp(), "S2"), REPO, env={**os.environ}, cwd=REPO)
bar_raises = pos.returncode != 0 and "barred jurisdiction module" in (pos.stderr + pos.stdout)
# negative control: WITHOUT the barrier, importing execution succeeds
neg = subprocess.run([PY, "-c", "import sys; sys.path.insert(0, %r); import ugk.kernel; print('ok')" % REPO],
                     capture_output=True, text=True, env={**os.environ}, cwd=REPO)
bar_is_cause = "ok" in neg.stdout
e4b_identical = pr2.returncode == 0 and pr2.stdout.strip() == json.dumps(EX.explain_projections(), sort_keys=True)
check("E4b explain independent of execution (renders byte-identical under proven-active exec barrier)",
      sent_ok and bar_raises and bar_is_cause and e4b_identical,
      "sentinel=%s bar_raises=%s bar_is_cause=%s identical=%s" % (sent_ok, bar_raises, bar_is_cause, e4b_identical))

# E4c execution independent of explain: delete explain.py, run execution surface -> passes
tmp = tempfile.mkdtemp(); dst = os.path.join(tmp, "repo")
shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
os.remove(os.path.join(dst, "ugk", "projections", "explain.py"))
e = {**os.environ, "PYTHONPATH": dst, "UGK_GENESIS_DIR": tempfile.mkdtemp()}
gp = EJ.bounded_run([PY, "-m", "ugk.conformance.run_gates_batch"], cwd=dst, env=e, timeout=120)
import re as _re
gm = _re.search(r"(\d+)/(\d+) passed", gp.stdout)
_mf = _re.search(r"(\d+)\s+failed", gp.stdout)
e4c_exec_ok = (bool(_mf) and int(_mf.group(1)) == 0 and bool(_re.search(r"ALL PASS|PASS \(\d+ not-established\)", gp.stdout))) \
              or (bool(gm) and gm.group(1) == gm.group(2))
check("E4c execution independent of explain (execution passes with explain.py DELETED)",
      e4c_exec_ok, gm.group(0) if gm else "no summary")
# neg control: inject execution import into explain -> E4b barred render breaks
dst2 = os.path.join(tempfile.mkdtemp(), "repo")
shutil.copytree(REPO, dst2, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))
ex_path = os.path.join(dst2, "ugk", "projections", "explain.py")
s = open(ex_path, encoding="utf-8").read().replace("from ugk.projections import hash as _hash",
                                  "import ugk.kernel  # INJECTED\nfrom ugk.projections import hash as _hash", 1)
open(ex_path, "w").write(s)
prn = EJ.run_code_under_barrier(PY, render_code, EJ.EXECUTION_MODULE_PREFIXES,
                                os.path.join(tempfile.mkdtemp(), "S3"), dst2, env={**os.environ}, cwd=dst2)
e4_teeth = prn.returncode != 0  # barred kernel import makes explain fail to load
check("  (neg-control) hidden execution import in explain breaks barred render (E4 has teeth)",
      e4_teeth)

# ---------- E5: corpus completeness (docs + explain; no orphans) ----------
corpus_keys = {"pattern:" + p.id for p in P.PATTERNS} | {"domain:" + d.id for d in DM.DOMAIN_MAPPINGS}
explain_keys = set(EX.explain_projections().keys())
doc_keys = set()
for rel in DOCS.doc_artifacts():
    if rel.startswith("docs/patterns/"):
        doc_keys.add("pattern:" + rel[len("docs/patterns/"):-3])
    elif rel.startswith("docs/domain-mappings/"):
        doc_keys.add("domain:" + rel[len("docs/domain-mappings/"):-3])
e5_explain_complete = corpus_keys == explain_keys
e5_doc_complete = corpus_keys == doc_keys
check("E5 corpus completeness: every object projects into docs AND explain; no orphans",
      e5_explain_complete and e5_doc_complete and len(corpus_keys) == 12,
      "corpus=%d explain=%d docs=%d" % (len(corpus_keys), len(explain_keys), len(doc_keys)))
# neg control: drop one explain projection -> incomplete
short = dict(EX.explain_projections()); short.pop(next(iter(short)))
check("  (neg-control) removing one explain projection breaks completeness (E5 has teeth)",
      corpus_keys != set(short.keys()))

ok = all(r[1] for r in results)
print("\n  explain projections: " + str(len(EX.explain_projections())) + " (corpus objects: 12)")
print("  PHASE 5b EXPLAIN GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
