#!/usr/bin/env python3
"""B3 conformance gate — keygen provenance (ships in the canonical archive).

B3a Creation provenance: keygen emits a founding-independent, PUBLIC-ONLY provenance
    artifact (pubkey, fingerprint=mosaic_id(pubkey), timestamp, intent, impl/version);
    never private-key material; not a governance receipt; no founded chain required.
B3b Binding continuity: founding still captures pubkey + mosaic_root + manifest linkage;
    the creation artifact forward-links to founding via mosaic_root == pubkey_fingerprint,
    using only public material.

Run from repo root:  python3 tools/b3_conformance.py   (expects all PASS, exit 0)
"""
import os, sys, json, io, tempfile, hashlib, contextlib, subprocess
from pathlib import Path
from types import SimpleNamespace

REPO = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, REPO)
EXPECTED_LAW_HASH = "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65"

results = []
def check(n, ok, d=""):
    results.append((n, bool(ok), d))
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f"  [{d}]" if d else ""))

from ugk.storage.binding import mosaic_id
import ugk.vendor.ed25519 as ed
from ugk import cli
from ugk.charter import DeploymentManifest

# Fix the keypair so private-key absence and pubkey determinism are checkable.
REAL_PRIV, REAL_PUB = ed.generate_keypair()
ed.generate_keypair = lambda: (REAL_PRIV, REAL_PUB)

def run_keygen(**kw):
    args = SimpleNamespace(write_secure=kw.get("write_secure"),
                           show_private=kw.get("show_private", False),
                           intent=kw.get("intent"))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli._cmd_keygen(args)
    return rc, buf.getvalue()

# --- B3a-1 + B3a-4: default mode emits provenance with the required fields ---
rc, out = run_keygen(intent="founding key for deployment X")
prov = json.loads(out).get("provenance", {})
fields_ok = all(k in prov for k in ("kind", "pubkey_hex", "pubkey_fingerprint", "timestamp", "intent", "impl"))
impl_ok = all(k in prov.get("impl", {}) for k in ("ugk_version", "law_hash", "legend_hash"))
check("B3a-1 default mode emits creation-provenance artifact",
      rc == 0 and prov.get("kind") == "keygen_creation_provenance")
check("B3a-4 provenance carries required fields (pubkey, fingerprint, timestamp, intent, impl/version)",
      fields_ok and impl_ok and prov.get("intent") == "founding key for deployment X",
      f"impl={prov.get('impl')}")

# --- B3a-2: provenance never contains private-key material (default + show-private) ---
no_priv_default = REAL_PRIV not in json.dumps(prov)
rc2, out2 = run_keygen(show_private=True)
d2 = json.loads(out2); prov2 = d2.get("provenance", {})
no_priv_show = (REAL_PRIV not in json.dumps(prov2)) and (d2.get("privkey_hex") == REAL_PRIV)
check("B3a-2 provenance contains no private key (default + show-private modes)",
      no_priv_default and no_priv_show)

# --- B3a write-secure: key file holds private key; sibling provenance file does NOT ---
tmp = tempfile.mkdtemp(); kp = os.path.join(tmp, "founder.key")
rc3, out3 = run_keygen(write_secure=kp)
keyfile = open(kp).read(); provfile = open(kp + ".provenance.json").read()
check("B3a write-secure: public sibling provenance written; no private key in it",
      rc3 == 0 and os.path.exists(kp + ".provenance.json")
      and REAL_PRIV in keyfile and REAL_PRIV not in provfile
      and json.loads(provfile)["pubkey_fingerprint"] == mosaic_id(REAL_PUB))

# --- B3a-3: deterministic w.r.t. public-key material ---
fp = prov["pubkey_fingerprint"]
check("B3a-3 fingerprint == mosaic_id(pubkey) (pure function of public key)",
      fp == mosaic_id(REAL_PUB), fp[:16] + "...")
check("B3a-3 fingerprint identical across repeated emissions (same pubkey)",
      fp == prov2["pubkey_fingerprint"] == json.loads(provfile)["pubkey_fingerprint"])
# cross-process: separate interpreters, same pubkey -> same fingerprint
_scr = ("import os,sys;sys.path.insert(0,os.environ['REPO']);"
        "from ugk.cli import _keygen_provenance;"
        "print(_keygen_provenance(os.environ['PUB'])['pubkey_fingerprint'])")
_env = dict(os.environ, REPO=REPO, PUB=REAL_PUB)
o1 = subprocess.check_output([sys.executable, "-c", _scr], env=_env).decode().strip()
o2 = subprocess.check_output([sys.executable, "-c", _scr], env=_env).decode().strip()
check("B3a-3 fingerprint deterministic across separate processes",
      o1 == o2 == mosaic_id(REAL_PUB), o1[:16] + "...")

# --- B3b-1: forward-link to a later founding event WITHOUT the private key ---
mani = DeploymentManifest.create(REAL_PUB, "fwd-link-test", "session", "trace_only")
check("B3b-1 forward-link: manifest.mosaic_root == provenance fingerprint (public-only)",
      mani.mosaic_root == fp == mosaic_id(REAL_PUB),
      f"mosaic_root={mani.mosaic_root[:16]}.. == fp={fp[:16]}..")

# --- B3b-2: binding continuity — founding still captures pubkey + mosaic_root + manifest linkage ---
check("B3b-2 binding continuity: founding captures pubkey + mosaic_root + manifest_hash",
      mani.governor_pubkey == REAL_PUB and mani.mosaic_root == mosaic_id(REAL_PUB) and bool(mani.manifest_hash))

# --- keygen remains pre-founding (no kernel/execute/store dependency) ---
src = open(os.path.join(REPO, "ugk", "cli.py")).read()
import ast
f = next(n for n in ast.walk(ast.parse(src))
         if isinstance(n, ast.FunctionDef) and n.name == "_cmd_keygen")
fsrc = ast.get_source_segment(src, f)
check("B3 keygen stays founding-independent (no _make_kernel/execute/store in _cmd_keygen)",
      "_make_kernel" not in fsrc and ".execute(" not in fsrc and "UGKReceiptStore" not in fsrc)

# --- law_hash unchanged ---
lh = hashlib.sha256(open(os.path.join(REPO, "ugk", "invariants.py"), "rb").read()).hexdigest()
check("B3 law_hash unchanged (invariants.py untouched)", lh == EXPECTED_LAW_HASH, lh[:16] + "...")

ok_all = all(ok for _, ok, _ in results)
print("\nB3 CONFORMANCE GATE:", "PASS" if ok_all else "FAIL")
sys.exit(0 if ok_all else 1)
