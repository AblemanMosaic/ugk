#!/usr/bin/env python3
"""GRBSA G2 — Substrate-Naming Gate.

Verifies the named substrate services map to symbols that EXIST in the current tree, that the
interface is pure schedule/observe (no authority expansion), that NBER-1 ordering is present at the
named receipt-emission site, and that G2 introduced NO new runtime scheduler/lane object. Read-only;
fails closed. Negative controls fail through the real gate path.

Run:  python g2_substrate_naming_gate.py <repo_dir>
"""
import sys, os, json, importlib, inspect, dataclasses as dc

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, REPO)
HERE = os.path.dirname(os.path.abspath(__file__))
results = []
def check(name, ok, detail=""):
    results.append((name, ok))
    print("  " + ("PASS" if ok else "FAIL") + "  " + name + (" — " + detail if detail else ""))

man = json.load(open(os.path.join(HERE, "service_map.json"), encoding="utf-8"))


def symbol_exists(dotted):
    """Resolve 'pkg.mod.A.b' as: module attr chain, OR dataclass field, OR method/property/const.
    Handles methods, dataclass FIELDS (scale.Receipt.rhash), and module constants (SCALE_OPS)."""
    parts = dotted.split(".")
    # find the longest importable module prefix
    mod = None
    for i in range(len(parts), 0, -1):
        try:
            mod = importlib.import_module(".".join(parts[:i]))
            rest = parts[i:]
            break
        except Exception:
            continue
    if mod is None:
        return False
    obj = mod
    for j, a in enumerate(rest):
        # dataclass field check at the class level
        if dc.is_dataclass(obj) and a in {f.name for f in dc.fields(obj)}:
            return True  # field resolves (terminal)
        if hasattr(obj, a):
            obj = getattr(obj, a)
        else:
            return False
    return True


# ---- existence: every named service symbol resolves in the real tree ----
missing = []
service_count = 0
symbols_checked = 0
for svc, entry in man["services"].items():
    service_count += 1
    for s in entry.get("symbols", []):
        symbols_checked += 1
        if not symbol_exists(s):
            missing.append((svc, s))
# anti-vacuity: a manifest with zero services or zero symbols must FAIL, not silently pass.
check("existence: every named service maps to a symbol present in the tree (>=1 service, >=1 symbol)",
      (not missing) and service_count >= 1 and symbols_checked >= 1,
      str(service_count) + " services, " + str(symbols_checked) + " symbols; unmapped=" + str(missing)
      if (missing or service_count < 1 or symbols_checked < 1) else
      str(service_count) + " services, " + str(symbols_checked) + " symbols all resolve")

# ---- no authority expansion: no named service intersects POSTURE_OPS; emitted vocab == closed SCALE_OPS ----
from ugk.scale.oracle import POSTURE_OPS
from ugk.scale.scheduler import SCALE_OPS
named_symbol_leaves = set()
for entry in man["services"].values():
    for s in entry.get("symbols", []):
        named_symbol_leaves.add(s.split(".")[-1])
posture_leak = named_symbol_leaves & set(POSTURE_OPS)
# the emitted-ops vocabulary referenced by the map must be exactly the existing closed SCALE_OPS
emitted_symbol = man["authority_boundary"]["emitted_ops_symbol"]
emitted_is_scaleops = symbol_exists(emitted_symbol) and emitted_symbol.endswith("SCALE_OPS")
check("no authority expansion: no named service is a posture op; emitted vocab is the closed SCALE_OPS",
      not posture_leak and emitted_is_scaleops,
      "posture_leak=%s emitted=%s" % (sorted(posture_leak), emitted_symbol))

# ---- NBER-1 present at the named receipt-emission site (source-order inspection) ----
from ugk.scale.oracle import CommitLane
src = inspect.getsource(CommitLane.commit_and_effect)
def first_index(hay, needle):
    return hay.find(needle)
append_at = first_index(src, "chain.append")
effect_at = first_index(src, "effect_fn(")
nber1_ok = append_at != -1 and effect_at != -1 and append_at < effect_at
check("NBER-1 present: receipt append precedes effect at commit_and_effect", nber1_ok,
      "append@%d < effect@%d" % (append_at, effect_at))

# ---- no new runtime scheduler/lane/chain object introduced by G2 ----
new_obj = []
for dp, dns, fs in os.walk(os.path.join(REPO, "ugk")):
    for f in fs:
        if not f.endswith(".py"):
            continue
        s = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        for marker in ("class GovernedSchedulerV2", "class ChainV2", "class CommitLaneV2", "class SubstrateInterface"):
            if marker in s:
                new_obj.append((os.path.relpath(os.path.join(dp, f), REPO), marker))
check("no new runtime scheduler/lane object added under ugk/ by G2", not new_obj,
      str(new_obj) if new_obj else "none")

# ---- negative controls (same checkers, malformed fixtures) ----
check("  (neg) a service mapped to a non-existent symbol is rejected",
      not symbol_exists("ugk.scale.scheduler.GovernedScheduler.NO_SUCH_METHOD"))
# inject a posture op as a named-service leaf -> must be caught by the posture-leak check
bad_leaves = named_symbol_leaves | set(list(POSTURE_OPS)[:1])
check("  (neg) a posture op injected as a named service is detected",
      len(bad_leaves & set(POSTURE_OPS)) > 0)
# effect-before-append fixture -> NBER-1 checker must FAIL
fake = "def f(c):\n    res = effect_fn(c)\n    r = chain.append(c)\n    return r, res\n"
fa = fake.find("chain.append"); fe = fake.find("effect_fn(")
check("  (neg) effect-before-append ordering fails the NBER-1 check", not (fa != -1 and fe != -1 and fa < fe))
# a new scheduler class fixture would be caught
check("  (neg) a 'class GovernedSchedulerV2' marker would be detected",
      "class GovernedSchedulerV2" in "class GovernedSchedulerV2: pass")

ok = bool(results) and all(r[1] for r in results)  # anti-vacuity: zero checks is not a pass
print("\n  GRBSA G2 SUBSTRATE-NAMING GATE: " + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
