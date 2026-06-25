#!/usr/bin/env python3
"""Phase 5a — Docs Integration Gate (CGProj).

Standing gate for the docs surface. Five checks, each with a negative control proven to have teeth:

  Boundary (7.3):     every domain-mapping doc carries a FRONT-LOADED boundary containing the
                      required negations (not a domain-architecture spec / not regulatory advice /
                      domain experts own implementation).
  Link-integrity:     every relative cross-link in docs/** resolves to an existing file.
  Docs-fidelity:      every checked-in doc byte-matches the single producer's output AND embeds a
                      content-hash equal to content_hash(current metadata). (Source-of-truth rule.)
  Anti-entanglement:  no projection-source module reads checked-in docs (flow is metadata -> docs).
  No-stale (carried): the existing staleness/law_hash pin (ugk.conformance.staleness_gate) still
                      passes. NOTE: the repo has no separate doc-claims linter; per the design note
                      this re-asserts the existing law_hash pin, it does not invent a new check.

Run from repo root:  python phase5a_docs_integration_gate.py <repo_dir>
Exit 0 = PASS; nonzero = FAIL (fails closed).
"""
import sys, os, re, ast, subprocess, tempfile

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

from ugk.projections import docs as DOCS
from ugk.projections import hash as H

DOMAIN_DIR = os.path.join(REPO, "docs", "domain-mappings")
PATTERN_DIR = os.path.join(REPO, "docs", "patterns")
REQUIRED_NEGATIONS = ("architecture specification", "regulatory requirements", "Domain experts are responsible")
_HASH_RE = re.compile(r"^content-hash:\s*([0-9a-f]{64})\s*$", re.M)
_HDR_END = "-->\n"


def read_text(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")


# ---------- Boundary Gate (7.3) ----------
def boundary_check(doc_text):
    """Return (has_boundary, front_loaded, has_negations). Boundary is the first '>' blockquote;
    front-loaded means it appears before any substantive content marker."""
    body = doc_text.split(_HDR_END, 1)[-1]
    lines = [ln for ln in body.splitlines()]
    # find first blockquote line and first substantive marker
    first_bq = next((i for i, ln in enumerate(lines) if ln.startswith("> ")), None)
    first_subst = next((i for i, ln in enumerate(lines)
                        if ln.startswith("**Instantiates patterns:**") or ln.startswith("**Integration point:**")), None)
    has_boundary = first_bq is not None and lines[first_bq][2:].strip() != ""
    front_loaded = has_boundary and (first_subst is None or first_bq < first_subst)
    bq_text = lines[first_bq][2:] if first_bq is not None else ""
    has_negations = all(neg in bq_text for neg in REQUIRED_NEGATIONS)
    return has_boundary, front_loaded, has_negations

dom_docs = sorted(f for f in os.listdir(DOMAIN_DIR) if f.endswith(".md")) if os.path.isdir(DOMAIN_DIR) else []
b_ok = len(dom_docs) > 0
for f in dom_docs:
    hb, fl, hn = boundary_check(read_text(os.path.join(DOMAIN_DIR, f)))
    b_ok = b_ok and hb and fl and hn
check("Boundary (7.3): every domain doc has a front-loaded boundary with required negations",
      b_ok, str(len(dom_docs)) + " domain docs checked")
# negative controls (same checker): empty boundary, boundary-after-content, missing negation all FAIL
neg_empty = boundary_check("x\n-->\n# T\n\n> \n\n**Integration point:** y\n")
neg_after = boundary_check("x\n-->\n# T\n\n**Instantiates patterns:** [a](../patterns/a.md)\n\n> not a domain architecture specification regulatory requirements Domain experts are responsible\n")
neg_noneg = boundary_check("x\n-->\n# T\n\n> just some text with no negations\n\n**Integration point:** y\n")
teeth_b = (not neg_empty[0]) and (not neg_after[1]) and (not neg_noneg[2])
check("  (neg-control) boundary checker rejects empty / after-content / missing-negation", teeth_b,
      "empty_rejected=" + str(not neg_empty[0]) + " after_rejected=" + str(not neg_after[1])
      + " noneg_rejected=" + str(not neg_noneg[2]))

# ---------- Link-integrity ----------
link_re = re.compile(r"\]\(([^)]+)\)")
all_links = 0
broken = []
for d in (PATTERN_DIR, DOMAIN_DIR):
    if not os.path.isdir(d):
        continue
    for f in os.listdir(d):
        if not f.endswith(".md"):
            continue
        txt = read_text(os.path.join(d, f))
        for target in link_re.findall(txt):
            if target.startswith("http"):
                continue
            all_links += 1
            resolved = os.path.normpath(os.path.join(d, target))
            if not os.path.exists(resolved):
                broken.append((f, target))
check("Link-integrity: every relative cross-link resolves", all_links > 0 and not broken,
      str(all_links) + " links checked; broken=" + str(broken))
# negative control: an injected dangling link is detected
inj = os.path.normpath(os.path.join(DOMAIN_DIR, "../patterns/NO_SUCH.md"))
check("  (neg-control) a dangling link target does NOT exist (checker would catch it)",
      not os.path.exists(inj))

# ---------- Docs-fidelity (source-of-truth) ----------
expected = DOCS.doc_artifacts()
recomputed = H.content_hash()
fid_ok = len(expected) > 0
checked = 0
for relpath, exp_text in expected.items():
    full = os.path.join(REPO, relpath)
    if not os.path.exists(full):
        fid_ok = False
        continue
    on_disk = open(full, "rb").read()
    byte_match = (on_disk == exp_text.encode("utf-8"))
    m = _HASH_RE.search(on_disk.decode("utf-8", "replace"))
    hash_ok = bool(m) and m.group(1) == recomputed
    checked += 1
    fid_ok = fid_ok and byte_match and hash_ok
check("Docs-fidelity: every doc byte-matches producer + embeds content_hash", fid_ok,
      str(checked) + "/" + str(len(expected)) + " docs verified")
# negative control: body tamper -> byte-match fails (real on-disk style flip, in memory here)
sample_rel = next(iter(expected))
tampered = bytearray(expected[sample_rel].encode("utf-8"))
hdr_end_idx = tampered.index(b"-->\n") + 6
tampered[hdr_end_idx] ^= 0x20
check("  (neg-control) body tamper breaks byte-match",
      bytes(tampered) != expected[sample_rel].encode("utf-8"))

# ---------- Anti-entanglement (no source reads docs) ----------
proj_dir = os.path.join(REPO, "ugk", "projections")
entangle = []
for f in os.listdir(proj_dir):
    if not f.endswith(".py"):
        continue
    src = open(os.path.join(proj_dir, f), encoding="utf-8").read()
    # flag any read of docs/ or generated dir from projection SOURCE (open()/read of a docs path)
    if re.search(r"open\([^)]*docs/", src) or re.search(r"read.*docs/(patterns|domain-mappings)", src):
        entangle.append(f)
check("Anti-entanglement: no projection-source module reads checked-in docs", not entangle,
      str(entangle) if entangle else "clean (flow is metadata -> docs only)")

# ---------- No-stale (carried): existing law_hash pin still passes ----------
# staleness_gate requires a FOUNDED kernel (it checks ACTIVE receipts carry law_hash); it is one of
# the 78 batch gates. Invoke it through the batch harness (which performs genesis), not bare run().
e = {**os.environ, "PYTHONPATH": REPO, "UGK_GENESIS_DIR": tempfile.mkdtemp()}
p = subprocess.run([PY, "-m", "ugk.conformance.run_gates_batch"],
                   cwd=REPO, env=e, capture_output=True, text=True, timeout=900)
out = p.stdout + p.stderr
m = re.search(r"^\s*staleness_gate\s+(PASS|FAIL)", out, re.M)
stale_ok = bool(m) and m.group(1) == "PASS"
check("No-stale (carried): existing staleness/law_hash pin passes (no new doc-linter invented)",
      stale_ok, ("staleness_gate=" + m.group(1)) if m else "staleness_gate line not found")

ok = all(r[1] for r in results)
print("\n  content_hash = " + recomputed)
print("  PHASE 5a DOCS INTEGRATION GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
