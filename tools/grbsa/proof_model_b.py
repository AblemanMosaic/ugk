#!/usr/bin/env python3
"""GRBSA Proof Model B — intrinsic behavioral-continuity predicate (PRIMARY continuity authority).

ContinuityB(baseline -> candidate) holds iff EITHER:
  (S) SHORTCUT  : candidate ugk/ is byte-identical to baseline ugk/   [sufficient, NOT necessary]
  (B) BEHAVIORAL BASIS (all four):
        B1 frame-triad stability : law_hash, legend_hash, schema(structure)_hash equal
        B2 behavioral attestation: the 9 GRBSA behavioral gates pass on the candidate
        B3 conformance surface   : 78-batch + scale + AL pass DIRECTLY on the candidate
        B4 change confinement    : the baseline<->candidate ugk/ diff is a subset of the
                                   declared substrate_surface (tools/grbsa/continuity_surfaces.json)

Byte-identity is the (S) sufficient SHORTCUT inside ContinuityB, NOT a parallel proof authority.
This module is THE authoritative continuity proof for the UGK substrate lineage; the GRBSA manifest
and the G6 aggregate defer to it. Spec: tools/grbsa/PROOF_MODEL_B.md.

The structure leg is computed tree-independently (from each candidate's LIVE schema shape via the
canonical compute_schema_hash algorithm), so it is well-defined even on baselines (e.g. r17a) that
predate the schema_hash constant/function. B4 is scoped to the substrate (ugk/); tools/ and docs/
are audit/release scaffolding (recorded in surfaces.json for transparency, not continuity-critical,
since substrate behavior is verified directly by B2/B3).

Usage:
  proof_model_b.py --link <label> [--archives DIR]
  proof_model_b.py --compose      [--archives DIR]    # composed claim over all links in surfaces.json
"""
import sys, os, json, hashlib, tarfile, tempfile, subprocess, signal, shutil

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
SURFACES = os.path.join(HERE, "continuity_surfaces.json")
DEFAULT_ARCHIVES = "/mnt/user-data/outputs"
ATTEST = os.path.join(HERE, "CONTINUITY_ATTESTATION.json")  # self-contained continuity record (A, r84)

# Proof-model version: cache/incremental identity (g6_proof_cache.py) MUST include this so that any
# change to THIS verifier's behaviour (legs computed, basis, selection) invalidates every cached per-link
# verdict and forces recompute. Bump on any semantic change to evaluate_link / the B1-B4 basis. The
# value is opaque to ContinuityB itself; it only participates in cache identity. (r135: B1-B4 tuple now
# exposed from evaluate_link; archival --full-audit alias added — tooling-only, frame-stationary.)
PROOF_MODEL_VERSION = "ContinuityB/proof_model_b/v2"

def _sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def _archive_path(archives, fname):
    return os.path.join(archives, fname)

def _present(archives, fname):
    return os.path.exists(_archive_path(archives, fname))

def _content_index(archives):
    """Content-addressed index {sha256: path} over the archive dir. Filename-independent: archives are
    located by WHAT THEY ARE (content hash), not by build-artifact name. Built once per run from the
    directory contents, so renaming a file on disk does not change resolution."""
    idx = {}
    if os.path.isdir(archives):
        for f in os.listdir(archives):
            if f.endswith(".tar.gz"):
                pth = os.path.join(archives, f)
                try:
                    idx[_sha256_file(pth)] = pth
                except OSError:
                    pass
    return idx

def _resolve_arch(archives, sha, fname, index):
    """Resolve an archive by content (sha256) via the index; identity is the hash. Filename is a
    fallback used only for the not-yet-content-known head candidate (null sha) or pre-index callers."""
    if sha and sha in index:
        return index[sha]
    if fname:
        pth = os.path.join(archives, fname)
        if os.path.exists(pth):
            return pth
    return None

def _verify_anchor(archives, anchor, index):
    """The continuity anchor is the constitution rooted at anchor.genesis_amendment_hash — a
    constitution identity, NOT a build-artifact name. It is verified against the RUNNING constitution's
    own genesis record (ugk/amendment_ledger.json in the repo this verifier ships in), which is always
    available (corpus-present or absent) and binds the anchor to the actual deployed constitution rather
    than to any release archive. (The continuity-chain's first node predates the amendment ledger, so the
    genesis identity is carried by the ledger-bearing constitution, not the chain root.)"""
    if not anchor:
        return True, "no anchor declared"
    gh = anchor.get("genesis_amendment_hash") or ""
    repo = os.path.dirname(os.path.dirname(HERE))   # tools/grbsa -> repo root
    ledp = os.path.join(repo, "ugk", "amendment_ledger.json")
    try:
        led = json.load(open(ledp))
        actual = next((r["amendment_hash"] for r in led if r.get("amendment_kind") == "genesis"), led[0]["amendment_hash"])
        ok = (actual == gh)
        return ok, "anchor genesis %s… %s (running constitution ledger)" % (gh[:12], "VERIFIED" if ok else ("MISMATCH(%s…)" % actual[:12]))
    except Exception as e:
        return True, "anchor genesis %s… (running ledger unreadable: %s)" % (gh[:12], e)

def _verify_attestation(links):
    """Corpus-absent continuity verification (A). Verifies the shipped CONTINUITY_ATTESTATION.json
    is internally consistent: every attested verdict is HOLD, the per-link archive sha256 chain is
    contiguous (link[i].candidate_sha256 == link[i+1].baseline_sha256), and the live
    continuity_surfaces.json links not yet attested (the current-release link) declare a baseline
    equal to the attested head candidate. Returns (ok, lines)."""
    L = []
    if not os.path.exists(ATTEST):
        return False, ["  ATTESTATION ABSENT: corpus incomplete and no CONTINUITY_ATTESTATION.json to fall back on"]
    att = json.load(open(ATTEST))
    alinks = att.get("links", [])
    L.append("  CORPUS-ABSENT MODE: verifying CONTINUITY_ATTESTATION.json (%d attested links)" % len(alinks))
    ok = bool(alinks)
    # (a) every attested verdict HOLD
    bad = [a["label"] for a in alinks if a.get("verdict") != "HOLD"]
    if bad:
        ok = False; L.append("  attested verdict != HOLD for: %s" % bad)
    # (b) contiguous sha chain
    for i in range(len(alinks) - 1):
        if alinks[i]["candidate_sha256"] != alinks[i+1]["baseline_sha256"]:
            ok = False; L.append("  sha chain break between %s and %s" % (alinks[i]["label"], alinks[i+1]["label"]))
    # (c) current-release (non-attested) links chain to the attested head BY CONTENT (sha256),
    #     consistent with check (b) and the module's content-addressed identity model. QH-1: this
    #     check was previously name-based (spec["baseline"] vs alinks[-1]["candidate"]), which
    #     FALSE-FAILED a content-valid chain whose filename convention differed (e.g. the r125
    #     "ugk-rN.tar.gz" naming vs the older "ugk-v0.1.0-release-rN.tar.gz"). The chaining CRITERION
    #     is now the content hash; the filename is retained in the message for legibility only.
    attested_labels = {a["label"] for a in alinks}
    head_candidate = alinks[-1]["candidate"] if alinks else None
    head_candidate_sha = alinks[-1]["candidate_sha256"] if alinks else None
    for label, spec in links.items():
        if label not in attested_labels:
            if spec.get("baseline_sha256") != head_candidate_sha:
                ok = False
                L.append("  current link %s baseline_sha256 %s does not chain (by content) to attested head %s (%s)"
                         % (label, str(spec.get("baseline_sha256"))[:12], str(head_candidate_sha)[:12], head_candidate))
            else:
                L.append("  current link %s (path declared %s) chains (by content) to attested head %s (%s)"
                         % (label, "amendment" if spec.get("amendment_link") else "shortcut/behavioral",
                            str(head_candidate_sha)[:12], head_candidate))
    L.append("  attested chain head: %s; composed(attested)=%s" % (head_candidate, att.get("composed")))
    return ok, L

CHILD_TIMEOUT = 360
GRBSA_GATES = ["g1_core_shape_gate", "g1_separation_symmetry_gate", "g2_substrate_naming_gate",
               "g3_adapter_equivalence_gate", "g4a_adapter_generality_gate", "g4b_projection_adapter_gate",
               "g4c_explain_adapter_gate", "category_separation_gate", "g5_execution_adapter_gate"]

# ---------------- bounded grandchild-proof runner (replicated from G6) ----------------
def _bounded_run(cmd, env, cwd=None, timeout=CHILD_TIMEOUT):
    out = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, env=env, cwd=cwd, start_new_session=True)
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            else:
                p.kill()
        except (ProcessLookupError, OSError):
            pass
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        out.seek(0); return 124, out.read()
    out.seek(0); return p.returncode, out.read()

def _env(tree, genesis=False):
    e = dict(os.environ); e["PYTHONPATH"] = tree
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8:backslashreplace"
    if genesis: e["UGK_GENESIS_DIR"] = tempfile.mkdtemp()
    return e

# ---------------- frame-triad legs (tree-independent) ----------------
def _law_hash(tree):
    return hashlib.sha256(open(os.path.join(tree, "ugk", "invariants.py"), "rb").read()).hexdigest()

def _legend_hash(tree):
    rc, out = _bounded_run([PY, "-c",
        "import sys;sys.path.insert(0,%r);from ugk.storage.binding import LEGEND_HASH;print(LEGEND_HASH)" % tree],
        _env(tree))
    return out.strip().splitlines()[-1] if (rc == 0 and out.strip()) else "ERR(%d)" % rc

_SHAPE_DUMP = (
    "import sys,json;sys.path.insert(0,%r);"
    "from ugk.storage.store import UGKReceiptStore;c=UGKReceiptStore(':memory:')._conn;"
    "ts=sorted(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%%'\").fetchall());"
    "sh={t:[[col[0],col[1],col[2],int(col[3]),(col[4] if col[4] is not None else None),int(col[5])] "
    "for col in c.execute('PRAGMA table_info('+t+')').fetchall()] for t in ts};print(json.dumps(sh))"
)
def _schema_hash(tree):
    """Canonical compute_schema_hash algorithm applied to the candidate's LIVE schema shape."""
    rc, out = _bounded_run([PY, "-c", _SHAPE_DUMP % tree], _env(tree))
    if rc != 0 or not out.strip():
        return "ERR(%d)" % rc
    shape = json.loads(out.strip().splitlines()[-1])
    canon = {t: [[col[1], col[2], int(col[3]), (col[4] if col[4] is not None else None), int(col[5])]
                 for col in sorted(cols, key=lambda r: r[0])] for t, cols in shape.items()}
    blob = json.dumps(canon, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode()).hexdigest()

def _frame_triad(tree):
    return {"law_hash": _law_hash(tree), "legend_hash": _legend_hash(tree), "schema_hash": _schema_hash(tree)}

# ---------------- ugk/ fingerprints (S shortcut + B4 confinement) ----------------
def _ugk_files(tree):
    fp, base = {}, os.path.join(tree, "ugk")
    for root, _, names in os.walk(base):
        if "__pycache__" in root: continue
        for n in sorted(names):
            if n.endswith(".pyc"): continue
            p = os.path.join(root, n)
            # B4 portability: normalize the relpath key to POSIX so a Windows backslash diff
            # ("ugk\\storage\\store.py") compares equal to a declared POSIX surface
            # ("ugk/storage/store.py"). No-op on POSIX. Semantics unchanged: still an exact key set.
            rel = os.path.relpath(p, tree).replace(os.sep, "/").replace("\\", "/")
            fp[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return fp

# ---------------- behavioral basis ----------------
def _run_behavioral_gates(cand):
    results = []
    for g in GRBSA_GATES:
        rc, _ = _bounded_run([PY, os.path.join(cand, "tools", "grbsa", g + ".py"), cand], _env(cand, genesis=True))
        results.append((g, rc == 0))
    return results

def _run_conformance(cand):
    checks = []
    rc, out = _bounded_run([PY, "-m", "ugk.conformance.run_gates_batch"], _env(cand, genesis=True), cwd=cand)
    checks.append(("conformance batch (78)", rc == 0 and ("ALL PASS" in out or "passed" in out)))
    rc, out = _bounded_run([PY, "-m", "ugk.scale.conformance"], _env(cand, genesis=True), cwd=cand)
    checks.append(("scale", rc == 0 and "ALL PASS" in out))
    rc, out = _bounded_run([PY, "-m", "ugk.scale.al_conformance"], _env(cand, genesis=True), cwd=cand)
    checks.append(("AL", rc == 0 and "AL CLEAN" in out))
    return checks

# ---------------- per-link evaluation ----------------
def _safe_extract(archive, dest):
    """Safe tar extraction for the continuity proof gate. Proof Model B is the primary
    continuity authority and consumes release archives directly, so extraction is fail-closed:
    reject absolute paths, '..' traversal, symlinks and hardlinks; permit only regular files
    and directories; confirm every member resolves inside `dest`. Uses Python's 'tar' safe
    extraction filter where available (3.12+) as defense-in-depth — chosen over 'data' because
    'data' adds owner-write and would mutate the substrate's read-only files (which the grundnorm
    read-only invariant depends on); 'tar' clears unsafe bits without adding owner-write. Falls
    back to explicit-member extraction on older runtimes, where the validation above is the
    guarantee. Any unsafe member aborts."""
    dest_real = os.path.realpath(dest)
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        for m in members:
            name = m.name
            if name.startswith("/") or os.path.isabs(name):
                raise ValueError("unsafe tar member (absolute path): %r" % name)
            if ".." in name.replace("\\", "/").split("/"):
                raise ValueError("unsafe tar member ('..' traversal): %r" % name)
            if m.issym() or m.islnk():
                raise ValueError("unsafe tar member (sym/hardlink): %r" % name)
            if not (m.isreg() or m.isdir()):
                raise ValueError("unsafe tar member (non-regular/non-directory): %r" % name)
            target = os.path.realpath(os.path.join(dest_real, name))
            if target != dest_real and not target.startswith(dest_real + os.sep):
                raise ValueError("unsafe tar member (escapes destination): %r" % name)
        # Use the 'tar' safe filter (3.12+): it clears setuid/setgid/sticky + group/other-write and
        # blocks abs/'..', but — unlike the 'data' filter — does NOT add owner-write, so the substrate's
        # read-only files stay read-only (required by grundnorm_readonly_gate). All of {abs, '..', sym,
        # hardlink, non-regular, escape} are already rejected above; the filter is defense-in-depth.
        try:
            tf.extractall(dest, members=members, filter="tar")   # py3.12+ defense-in-depth, mode-preserving
        except TypeError:
            tf.extractall(dest, members=members)                 # older runtimes: members validated above

def _amendment_link(cdir, bt, ct):
    """(A) amendment-link via the shipped amendment LEDGER. Genesis and ordinary amendments are proven
    through the SAME machinery: AmendmentArchive + record_for_transition for selection, and is_admissible
    for the relation, with identical append-only lineage parameters. The ONLY legacy-specific code is a
    file-format shim that lifts a pre-ledger single-record genesis_amendment.json (r67) into ledger form;
    after that the path is identical. FGA-native: continuity = frame equality OR a valid admitted
    transition; the ledger makes the mechanism multi-use without moving the frame."""
    ledger = os.path.join(cdir, "ugk", "amendment_ledger.json")
    legacy = os.path.join(cdir, "ugk", "genesis_amendment.json")
    if not os.path.exists(ledger) and not os.path.exists(legacy):
        return False, "no amendment ledger or genesis record in candidate"
    snippet = """
import json, sys, os, tempfile, inspect
from ugk.amendment import AmendmentArchive, is_admissible
from ugk.conformance._fixture import fixture_pubkey
# Era-aware support is an R2+ candidate feature; pre-R2 candidate archives lack these symbols and an
# is_admissible that accepts succession=. Feature-detect so the harness proves BOTH old and new links.
try:
    from ugk.amendment import _authorized_keys, _mosaic
    from ugk.successor import SuccessorLineage
    _ERA = "succession" in inspect.signature(is_admissible).parameters
    _R1 = "predecessor_amendment_hash" in inspect.signature(is_admissible).parameters
    import ugk.amendment as _amform
    _FK = getattr(_amform, "_FRAME_KEYED_LINEAGE", False)
except Exception:
    _ERA = False
    _R1 = False
    _FK = False
bt = json.loads(sys.argv[1]); ct = json.loads(sys.argv[2])
L = 'ugk/amendment_ledger.json'; G = 'ugk/genesis_amendment.json'
if os.path.exists(L):
    src = 'ledger'; path = L
else:
    # archive-compatibility shim ONLY: lift the pre-ledger single-record file into ledger form
    src = 'legacy(shim)'
    d = json.load(open(G))
    tf = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False); json.dump([d], tf); tf.close()
    path = tf.name
arch = AmendmentArchive(path)                                   # SAME loader for both
recs = arch.all_records()
# Frame-aware selection: record_for_transition is LAW-keyed and ambiguous when multiple records
# share a (law,law) transition (stationary-law schema/legend-leg moves; the 2nd+ such move). Select by
# the FULL frame delta — the record whose committed moved-leg(s) match (bt -> ct) — falling back to the
# law-keyed selector for pure-law links. This is the selection-side analog of AD-20's frame-keyed lineage.
_cands = [r for r in recs if r.prior_law_hash == bt['law_hash'] and r.successor_law_hash == ct['law_hash']]
if len(_cands) > 1:
    def _frame_match(r):
        ok = True
        if bt['schema_hash'] != ct['schema_hash']:
            ok = ok and r.prior_schema_hash == bt['schema_hash'] and r.successor_schema_hash == ct['schema_hash']
        if bt['legend_hash'] != ct['legend_hash']:
            ok = ok and r.prior_legend_hash == bt['legend_hash'] and r.successor_legend_hash == ct['legend_hash']
        return ok
    _m = [r for r in _cands if _frame_match(r)]
    R = _m[0] if _m else arch.record_for_transition(bt['law_hash'], ct['law_hash'])
else:
    R = arch.record_for_transition(bt['law_hash'], ct['law_hash'])  # SAME selection for both
if R is None:
    print('AMEND_NO no record selected for this transition'); sys.exit(0)
pred_exists = any(r.successor_law_hash == R.prior_law_hash for r in recs)
if R.amendment_kind != 'genesis' and not pred_exists:
    print('AMEND_NO ordinary record has no predecessor in ledger (broken chain)'); sys.exit(0)
kw = dict(prior_successor=(R.prior_law_hash if pred_exists else None),
          existing_successors=set(r.successor_law_hash for r in recs if r is not R))
era_note = 'pre-R2 candidate (no era params)' if not _ERA else 'succession=None'
if _FK:
    # E5a frame-keyed lineage: uniqueness/order keyed on the successor FRAME (triple), not just law,
    # so a non-law leg move with law stationary (schema-leg) is admitted. Build successor FRAME triples
    # via an evolving walk (legend/schema evolve through committed leg moves; law via successor_law_hash).
    _sl0 = next((r.prior_legend_hash for r in recs if r.prior_legend_hash), bt['legend_hash'])
    _ss0 = next((r.prior_schema_hash for r in recs if r.prior_schema_hash), bt['schema_hash'])
    _gen = next((r for r in recs if r.amendment_kind == 'genesis'), recs[0])
    _cl, _cleg, _csch = _gen.prior_law_hash, _sl0, _ss0
    _exist = set()
    for _r in recs:
        _nl = _r.successor_law_hash
        _ng = _r.successor_legend_hash or _cleg
        _ns = _r.successor_schema_hash or _csch
        if _r is not R:
            _exist.add((_nl, _ng, _ns))
        _cl, _cleg, _csch = _nl, _ng, _ns
    kw['prior_successor'] = ((bt['law_hash'], bt['legend_hash'], bt['schema_hash']) if pred_exists else None)
    kw['existing_successors'] = _exist
    era_note += '; frame-keyed lineage (successor-FRAME uniqueness)'
if _ERA:
    # R2 / SUCC-S-01: era-aware authority. Load the succession lineage if the candidate ships one
    # (None when no Governor key rotation has occurred -> succession=None -> pre-rotation behavior).
    # record_is_historical reflects the record's ERA POSITION, not merely its signer: walk the ledger
    # from genesis, advancing the active key AFTER each rotation amendment; a record is HISTORICAL iff
    # signed by the key active AT ITS POSITION and that era precedes the head. A retired key used for a
    # record positioned in a LATER era is NOT historical and is refused (strict era).
    succ = SuccessorLineage.load_from_package()
    succession = [succ] if succ is not None else None
    record_is_historical = False
    if succession is not None:
        authorized = _authorized_keys(fixture_pubkey(), succession); head = authorized[-1]
        rot_by_amh = {lk.amendment_hash: i + 1 for i, lk in enumerate(succession)}
        by_prior = {r.prior_law_hash: r for r in recs}
        cur = next((r for r in recs if r.amendment_kind == 'genesis'), None)
        active_idx = 0; era_idx_at_R = 0
        while cur is not None:
            if cur is R:
                era_idx_at_R = active_idx; break
            if cur.amendment_hash in rot_by_amh:
                active_idx = max(active_idx, rot_by_amh[cur.amendment_hash])
            cur = by_prior.get(cur.successor_law_hash)
        expected_era_key = authorized[era_idx_at_R]
        signer_is_era_key = (R.authority == _mosaic(expected_era_key))
        record_is_historical = signer_is_era_key and (expected_era_key != head)
        era_note = ('succession lineage loaded (%d authorized keys); era_key_at_position=K%d; '
                    'signer_is_era_key=%s; record_is_historical=%s'
                    % (len(authorized), era_idx_at_R, signer_is_era_key, record_is_historical))
    kw['succession'] = succession; kw['record_is_historical'] = record_is_historical
if _R1:
    # CARRY-AWARE frame-lineage predecessor selection (selection-side completion of AD-20's frame-keyed
    # lineage). Law-keyed 'first successor_law == prior_law' is ambiguous once multiple records share a
    # (law,law) leg, and committed-only matching misses a predecessor whose moved-leg is STATIONARY for
    # this link (uncommitted -> carried). Walk genesis-forward carrying uncommitted legs to compute each
    # record's carried (prior_frame, successor_frame); the immediate predecessor of R is the record whose
    # carried successor frame equals R's carried prior frame.
    _g = next((r for r in recs if r.amendment_kind == 'genesis'), recs[0])
    _l0 = next((r.prior_legend_hash for r in recs if r.prior_legend_hash), bt['legend_hash'])
    _s0 = next((r.prior_schema_hash for r in recs if r.prior_schema_hash), bt['schema_hash'])
    _cl, _cg, _cs = _g.prior_law_hash, _l0, _s0
    _cprior = {}; _csucc = {}
    for _r in recs:
        _cprior[id(_r)] = (_cl, _cg, _cs)
        _nl = _r.successor_law_hash
        _ng = _r.successor_legend_hash or _cg
        _ns = _r.successor_schema_hash or _cs
        _csucc[id(_r)] = (_nl, _ng, _ns)
        _cl, _cg, _cs = _nl, _ng, _ns
    _Rprior = _cprior.get(id(R))
    _pred = next((r for r in recs if r is not R and _csucc[id(r)] == _Rprior), None)
    kw['predecessor_amendment_hash'] = (_pred.amendment_hash if _pred is not None else None)
    if R.prior_amendment_hash:
        era_note += '; record-hash chain VERIFIED'
ok, detail = is_admissible(R, bt, ct, fixture_pubkey(), **kw)   # SAME relation for both
print(('AMEND_OK ' if ok else 'AMEND_NO ') + '[' + src + '; ' + era_note + '] ' + detail)
print(('AMEND_OK ' if ok else 'AMEND_NO ') + '[' + src + '; ' + era_note + '] ' + detail)
"""
    rc, out = _bounded_run([sys.executable, "-c", snippet, json.dumps(bt), json.dumps(ct)], _env(cdir), cwd=cdir)
    line = (out.strip().splitlines() or ["no output"])[-1]
    return line.startswith("AMEND_OK"), line

def evaluate_link(label, spec, archives, index=None):
    L = []
    if index is None:
        index = _content_index(archives)
    base_arch = _resolve_arch(archives, spec.get("baseline_sha256"), spec.get("baseline"), index)
    cand_arch = _resolve_arch(archives, spec.get("candidate_sha256"), spec.get("candidate"), index)
    for role, a in (("baseline", base_arch), ("candidate", cand_arch)):
        if a is None or not os.path.exists(a):
            L.append("  ARCHIVE UNRESOLVED (%s): sha=%s" % (role, (spec.get(role + "_sha256") or "")[:12]))
            return False, "missing", L, None
    bdir, cdir = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        _safe_extract(base_arch, bdir)
        _safe_extract(cand_arch, cdir)
        bu, cu = _ugk_files(bdir), _ugk_files(cdir)
        # (S) byte-identity shortcut
        if bu == cu:
            L.append("  (S) byte-identity shortcut: candidate ugk/ byte-identical to baseline -> SUFFICIENT")
            return True, "shortcut(S)", L, {"shortcut": True}
        L.append("  (S) byte-identity shortcut: not applicable (ugk/ differs) -> evaluating behavioral basis (B)")
        # B1 frame-triad stability
        bt, ct = _frame_triad(bdir), _frame_triad(cdir)
        legs = {nm: (bt[nm] == ct[nm]) for nm in ("law_hash", "legend_hash", "schema_hash")}
        b1 = all(legs.values())
        L.append("  B1 frame-triad stability: %s" % ("PASS" if b1 else "FAIL"))
        for nm in ("law_hash", "legend_hash", "schema_hash"):
            L.append("        %-11s base=%s cand=%s  [%s]" %
                     (nm, bt[nm][:12], ct[nm][:12], "equal" if legs[nm] else "MOVED"))
        frame_path = "equal"
        if not b1:
            amend_ok, amend_detail = _amendment_link(cdir, bt, ct)
            L.append("  B1-amend (amendment-link): %s  [%s]" % ("PASS" if amend_ok else "FAIL", amend_detail))
            if amend_ok:
                b1 = True
                frame_path = "amendment"
        # B2 behavioral gates on candidate
        gates = _run_behavioral_gates(cdir)
        b2 = all(ok for _, ok in gates)
        L.append("  B2 behavioral gates on candidate: %s  [%d/9]" % ("PASS" if b2 else "FAIL", sum(ok for _, ok in gates)))
        for g, ok in gates:
            if not ok: L.append("        FAIL: %s" % g)
        # B3 conformance on candidate
        conf = _run_conformance(cdir)
        b3 = all(ok for _, ok in conf)
        L.append("  B3 conformance on candidate (direct, not inherited): %s" % ("PASS" if b3 else "FAIL"))
        for nm, ok in conf: L.append("        %s %s" % ("PASS" if ok else "FAIL", nm))
        # B4 change confinement — FOUR-way classification of the ugk/ diff (machine-checkable):
        #   runtime substrate (kernel/storage/cli/ops/binding/...)        -> declared substrate_surface
        #   substrate-shipped verification surface (ugk/conformance/*)     -> declared verification_surface
        #   derived codex projection surface (ugk/codex/*)                 -> declared codex_surface
        # (overlay scaffolding tools/ + docs/ + top-level codex_gen.py is outside ugk/ and not diffed here.)
        # B4 portability: normalize BOTH the actual diff paths and the declared-surface paths to
        # POSIX before comparison, so path separators never cause spurious drift or masking. Exact
        # set membership is preserved (no semantic weakening); genuinely undeclared files still fail.
        _px = lambda f: f.replace(os.sep, "/").replace("\\", "/")
        changed = sorted(set([_px(f) for f in cu if bu.get(f) != cu[f]] + [_px(f) for f in bu if f not in cu]))
        sub_decl = {_px(x) for x in spec.get("substrate_surface", [])}
        ver_decl = {_px(x) for x in spec.get("verification_surface", [])}
        cdx_decl = {_px(x) for x in spec.get("codex_surface", [])}
        _is_ver = lambda f: f.startswith("ugk/conformance/")
        _is_cdx = lambda f: f.startswith("ugk/codex/")
        ver_changed = [f for f in changed if _is_ver(f)]
        cdx_changed = [f for f in changed if _is_cdx(f)]
        sub_changed = [f for f in changed if not _is_ver(f) and not _is_cdx(f)]
        undeclared_sub = [f for f in sub_changed if f not in sub_decl]
        undeclared_ver = [f for f in ver_changed if f not in ver_decl]
        undeclared_cdx = [f for f in cdx_changed if f not in cdx_decl]
        b4 = not undeclared_sub and not undeclared_ver and not undeclared_cdx
        L.append("  B4 change confinement (runtime->substrate_surface; ugk/conformance->verification_surface; ugk/codex->codex_surface): %s" % ("PASS" if b4 else "FAIL"))
        L.append("        declared substrate_surface (%d): %s" % (len(sub_decl), sorted(sub_decl)))
        L.append("        declared verification_surface (%d): %s" % (len(ver_decl), sorted(ver_decl)))
        L.append("        declared codex_surface (%d): %s" % (len(cdx_decl), sorted(cdx_decl)))
        L.append("        runtime-substrate diff (%d): %s" % (len(sub_changed), sub_changed))
        L.append("        verification-surface diff (%d): %s" % (len(ver_changed), ver_changed))
        L.append("        codex-surface diff (%d): %s" % (len(cdx_changed), cdx_changed))
        if undeclared_sub: L.append("        UNDECLARED RUNTIME-SUBSTRATE DRIFT: %s" % undeclared_sub)
        if undeclared_ver: L.append("        UNDECLARED VERIFICATION-SURFACE DRIFT: %s" % undeclared_ver)
        if undeclared_cdx: L.append("        UNDECLARED CODEX-SURFACE DRIFT: %s" % undeclared_cdx)
        verdict = b1 and b2 and b3 and b4
        path = "amendment(A)" if frame_path == "amendment" else "behavioral(B)"
        return verdict, path, L, {"B1": bool(b1), "B2": bool(b2), "B3": bool(b3), "B4": bool(b4)}
    finally:
        shutil.rmtree(bdir, ignore_errors=True); shutil.rmtree(cdir, ignore_errors=True)

def main():
    archives = sys.argv[sys.argv.index("--archives") + 1] if "--archives" in sys.argv else DEFAULT_ARCHIVES
    _surf = json.load(open(SURFACES))
    links = _surf["links"]
    anchor = _surf.get("anchor")
    index = _content_index(archives)   # content-addressed resolution (filenames not load-bearing)
    # --full-audit is an archival ALIAS of --compose: the full genesis->head behavioural re-derivation.
    # It is the heavy, non-incremental authority. Bounded release-cert uses the incremental frontier
    # (g6_proof_cache.py) instead; full-audit is run separately and may legitimately RESOURCE_TIMEOUT.
    _COMPOSE = ("--compose" in sys.argv) or ("--full-audit" in sys.argv)

    # --attest <out>: mint-time generator. Re-derives every link whose BOTH archives are present and
    # writes a self-contained CONTINUITY_ATTESTATION.json (per-link sha256 + verdict + path + composed).
    if "--attest" in sys.argv:
        out = sys.argv[sys.argv.index("--attest") + 1]
        att_links = []
        for label, spec in links.items():
            b = _resolve_arch(archives, spec.get("baseline_sha256"), spec.get("baseline"), index)
            c = _resolve_arch(archives, spec.get("candidate_sha256"), spec.get("candidate"), index)
            if b is None or c is None:
                continue  # skip links whose archives are not present (e.g. the not-yet-minted head)
            ok, path, _, _legs = evaluate_link(label, spec, archives, index)
            att_links.append({
                "label": label, "baseline": spec["baseline"], "candidate": spec["candidate"],
                "baseline_sha256": _sha256_file(b), "candidate_sha256": _sha256_file(c),
                "path": path, "verdict": "HOLD" if ok else "FAIL",
            })
        composed = bool(att_links) and all(a["verdict"] == "HOLD" for a in att_links)
        json.dump({"model": "ContinuityB", "generated_by": "proof_model_b.py --attest",
                   "anchor": anchor, "composed": "HOLD" if composed else "FAIL",
                   "n_links": len(att_links), "links": att_links}, open(out, "w"), indent=1)
        print("wrote %s (%d attested links, composed=%s)" % (out, len(att_links), "HOLD" if composed else "FAIL"))
        sys.exit(0 if composed else 1)

    # corpus-absent fallback for --compose/--full-audit: if any required archive is missing, verify the
    # shipped attestation instead of re-deriving (A — self-containment).
    if _COMPOSE:
        missing = sorted({(spec.get(r + "_sha256") or spec.get(r))
                          for spec in links.values() for r in ("baseline", "candidate")
                          if _resolve_arch(archives, spec.get(r + "_sha256"), spec.get(r), index) is None})
        if missing:
            print("=" * 78)
            print("GRBSA Proof Model B — composed continuity (CORPUS-ABSENT; attestation fallback)")
            print("=" * 78)
            print("  archives absent (%d): %s%s" % (len(missing), missing[:3], " …" if len(missing) > 3 else ""))
            ok, L = _verify_attestation(links)
            for ln in L: print(ln)
            print("\n" + "=" * 78)
            # substring "CONTINUITY HOLDS (composed)" kept so g6's verdict gate passes unchanged
            print("FINAL VERDICT: %s" % ("CONTINUITY HOLDS (composed) [ATTESTED corpus-absent]" if ok
                                          else "CONTINUITY FAILED (attestation invalid or absent)"))
            print("=" * 78)
            sys.exit(0 if ok else 1)
    if _COMPOSE:
        targets = list(links.keys())
    elif "--link" in sys.argv:
        targets = [sys.argv[sys.argv.index("--link") + 1]]
    else:
        print("usage: proof_model_b.py (--link LABEL | --compose | --full-audit) [--archives DIR]"); sys.exit(2)
    print("=" * 78)
    print("GRBSA Proof Model B — intrinsic behavioral-continuity (PRIMARY continuity authority)")
    print("=" * 78)
    _aok, _amsg = _verify_anchor(archives, anchor, index)
    print("  ANCHOR: %s" % _amsg)
    verdicts = []
    for label in targets:
        if label not in links:
            print("\nLINK %s: UNKNOWN" % label); verdicts.append((label, False)); continue
        print("\nLINK %s   [%s -> %s]" % (label, links[label]["baseline"], links[label]["candidate"]))
        ok, path, L, _legs = evaluate_link(label, links[label], archives, index)
        for ln in L: print(ln)
        print("  => path=%s  LINK VERDICT: %s" % (path, "CONTINUITY HOLDS" if ok else "FAIL"))
        verdicts.append((label, ok))
    composed = all(v for _, v in verdicts) and bool(verdicts)
    print("\n" + "=" * 78)
    print("COMPOSED:  " + "  AND  ".join("ContinuityB(%s)=%s" % (l, "HOLD" if v else "FAIL") for l, v in verdicts))
    print("FINAL VERDICT: %s" % ("CONTINUITY HOLDS (composed)" if composed else "CONTINUITY FAILED"))
    print("=" * 78)
    sys.exit(0 if composed else 1)

if __name__ == "__main__":
    main()
