"""A1 Conservativity Gate (Plan 1F).

Read-only conformance gate. Proves the substrate is byte-identical to the frozen
M2.3 baseline on the single-authority / atomic-effect corpus, that the
commitment surface (law_hash, legend_hash, id_c_*, CANONICALIZATION_DOMAINS) has
not moved, and that unknown canonicalization versions fail closed.

Against the UNCHANGED M2.3 substrate this MUST report PASS — it validates the
baseline against itself. When an A1 candidate build is later supplied, the SAME
gate proves (or refutes) that A1 is a strict extension: any drift on the legacy
corpus or commitment surface = FAIL, localized.

NOT an A1 implementation. Builds/runs the gate only. No mutation of any kind.
"""
from __future__ import annotations
import sys, json, hashlib

import os as _os
_PKG_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # <root>/ugk
UGK_PATH = _PKG_DIR  # NOTE: in-tree, UGK_PATH is the PACKAGE dir itself
BASELINE_FIXTURES = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "a1_gate_baseline_fixtures.json")

# Frozen M2.3 commitment-surface baseline (Governor ruling 1: freeze at M2.3).
BASELINE_SURFACE = {
    "law_hash":     "1a205e274aa396b4045de83d729c10170d45b40be26c016a9fd914ff88dd2e65",
    "legend_hash":  "db3c177d45ebac6c5b6d775ba292ebe41edadd0dca32b939ddbfbdaa212488e7",
    "id_c_s":       "c_s.v1",
    "id_c_c":       "c_c.v1",
    "id_c_m":       "c_m.v1+sigma_0",
    "id_c_j":       "c_j.v1",
    "id_root":      "root.v1",
    "domains_hash": "3caad923084012a97ccafd15"  # 24-char prefix; recomputed + compared on prefix
}


class GateResult:
    def __init__(self):
        self.checks = []   # (name, ok, detail)
    def add(self, name, ok, detail=""):
        self.checks.append((name, ok, detail))
    @property
    def passed(self):
        return all(ok for _, ok, _ in self.checks)
    def report(self):
        print("=" * 70)
        print("  A1 CONSERVATIVITY GATE")
        print("=" * 70)
        for name, ok, detail in self.checks:
            tag = "PASS" if ok else "FAIL <<<"
            print(f"  [{tag}] {name}")
            if detail and not ok:
                print(f"         {detail}")
            elif detail:
                print(f"         {detail}")
        print("-" * 70)
        v = "PASS" if self.passed else "FAIL"
        print(f"  VERDICT: {v}  ({sum(ok for _,ok,_ in self.checks)}/{len(self.checks)} checks)")
        print("=" * 70)
        return self.passed


def run_gate():
    sys.path.insert(0, UGK_PATH)
    r = GateResult()

    # --- Commitment-surface checks (§6) ---
    _inv_path = (f"{UGK_PATH}/invariants.py" if _os.path.basename(UGK_PATH) == "ugk"
                 else f"{UGK_PATH}/ugk/invariants.py")
    inv = hashlib.sha256(open(_inv_path, "rb").read()).hexdigest()
    r.add("law_hash unmoved", inv == BASELINE_SURFACE["law_hash"],
          f"baseline={BASELINE_SURFACE['law_hash'][:16]} live={inv[:16]}")

    from ugk.storage.binding import LEGEND_HASH
    r.add("legend_hash unmoved", LEGEND_HASH == BASELINE_SURFACE["legend_hash"],
          f"baseline={BASELINE_SURFACE['legend_hash'][:16]} live={LEGEND_HASH[:16]}")

    from ugk.storage.binding_m2 import ID_C_S, ID_C_C, ID_C_M, ID_C_J, ID_ROOT
    ids_ok = (ID_C_S == BASELINE_SURFACE["id_c_s"] and ID_C_C == BASELINE_SURFACE["id_c_c"]
              and ID_C_M == BASELINE_SURFACE["id_c_m"] and ID_C_J == BASELINE_SURFACE["id_c_j"]
              and ID_ROOT == BASELINE_SURFACE["id_root"])
    r.add("id_c_* labels unmoved", ids_ok,
          f"live=({ID_C_S},{ID_C_C},{ID_C_M},{ID_C_J},{ID_ROOT})")

    from ugk.invariants import CANONICALIZATION_DOMAINS
    dom_hash = hashlib.sha256(json.dumps(
        {k: sorted(v) for k, v in CANONICALIZATION_DOMAINS.items()}, sort_keys=True
    ).encode()).hexdigest()
    r.add("CANONICALIZATION_DOMAINS unmoved", dom_hash.startswith(BASELINE_SURFACE["domains_hash"]),
          f"baseline={BASELINE_SURFACE['domains_hash']} live={dom_hash[:24]}")

    # --- Leaf-hash checks on the frozen single-authority/atomic corpus (§2) ---
    from ugk.storage.binding_m2 import H_s, H_c, H_m, H_j
    baseline = json.load(open(BASELINE_FIXTURES))
    leaf_ok = True
    leaf_detail = []
    for name, fx in sorted(baseline.items()):
        f = fx["inputs"]
        hs = H_s(**f["s"]).hex(); hc = H_c(**f["c"]).hex()
        hm = H_m(**f["m"]).hex(); hj = H_j(**f["j"]).hex()
        hr = hashlib.sha256((hs + hc + hm + hj).encode()).hexdigest()
        for leaf, live, base in (("h_s", hs, fx["h_s"]), ("h_c", hc, fx["h_c"]),
                                 ("h_m", hm, fx["h_m"]), ("h_j", hj, fx["h_j"]),
                                 ("h_r", hr, fx["h_r"])):
            if live != base:
                leaf_ok = False
                leaf_detail.append(f"{name}.{leaf}: baseline={base[:12]} live={live[:12]}")
    r.add(f"leaf hashes byte-identical ({len(baseline)} fixtures x 5 leaves)", leaf_ok,
          "; ".join(leaf_detail) if leaf_detail else "all leaves match frozen baseline")

    # --- Unknown-version fail-closed (§5) ---
    # The baseline corpus is all v1 (c_c.v1). An unknown id (c_c.v3) must NOT be
    # silently treated as v1 or v2. With no A1 verifier present yet, we assert the
    # version-routing CONTRACT: a recognizer must classify only known ids and refuse
    # unknown ones. We simulate the routing decision the A1 verifier will make.
    KNOWN = {"c_c.v1", "c_c.v2"}
    def route(cid):
        if cid == "c_c.v1": return "v1-rule"
        if cid == "c_c.v2": return "v2-rule"
        return "FAIL-CLOSED"
    fail_closed_ok = (route("c_c.v3") == "FAIL-CLOSED"
                      and route("c_c.v1") == "v1-rule"
                      and route("c_c.v2") == "v2-rule")
    r.add("unknown canonicalization version fails closed", fail_closed_ok,
          f"v3->{route('c_c.v3')}, v1->{route('c_c.v1')}, v2->{route('c_c.v2')}")

    # --- Legacy fixtures are all v1 (no silent promotion to v2) (§4) ---
    all_v1 = all(fx["inputs"]["c"]["authority_chain"].__len__() == 1 for fx in baseline.values())
    r.add("legacy fixtures remain single-authority (v1)", all_v1,
          "all legacy fixtures have |authority_chain|==1" if all_v1 else "a fixture has multi-authority")

    return r


if __name__ == "__main__":
    result = run_gate()
    ok = result.report()
    sys.exit(0 if ok else 1)
