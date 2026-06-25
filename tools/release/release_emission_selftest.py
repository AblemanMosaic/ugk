#!/usr/bin/env python3
"""release_emission_selftest.py — UGK release-tooling self-test for the SMH-I5 native emission path.

Proves, on the ACTUAL shipped tooling, that the native SMH emission hook is wired correctly and
fails closed on regressions. Like cert_selftest_gate.py this is release TOOLING (run directly; NOT
a kernel/conformance invariant; does not move the gate count).

Invariants proven:
  FUNCTIONAL (tools/smh/emit_release_receipt.py against a dummy sealed archive):
    F1  one real emission records EXACTLY ONE deep_export receipt to an EXTERNAL ledger
    F2  the receipt cites the FINAL archive bytes via smh_archive_ref (COLD->DEEP)
    F3  emission does NOT modify the archive bytes (read-only over the sealed artifact)
    F4  the ledger is the external SMH ledger model, not a UGK receipt store
  STATIC (tools/release/mint_release.sh as shipped):
    S1  emission (emit_release_receipt / SMH_LEDGER) appears ONLY in the mint) branch
    S2  --check and --verify-deterministic branches contain NO emission
    S3  the SMH ledger is guarded OUTSIDE the worktree (fail-closed case guard)
    S4  emission runs AFTER the archive is sealed (post mint_to "$OUT")
  ANTI-VACUITY:
    V0  the shipped script passes S1..S4
    V1  a mutated script with emission in the verify) branch is REJECTED by S1/S2 (not vacuous)

Usage:  release_emission_selftest.py            # locates the shipped tooling relative to itself
Exit 0 iff all invariants hold.
"""
import os, sys, json, tempfile, subprocess, hashlib, re

WT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MINT_SH = os.path.join(WT, "tools", "release", "mint_release.sh")
EMIT = os.path.join(WT, "tools", "smh", "emit_release_receipt.py")

results = {}
def chk(name, cond, detail=""):
    results[name] = {"pass": bool(cond), "detail": detail}


def _branch_body(src, branch):
    """Return the text of a `case` branch body: from `<branch>)` to the next `;;`."""
    m = re.search(r"\b" + re.escape(branch) + r"\)\s*\n(.*?)\n\s*;;", src, re.DOTALL)
    return m.group(1) if m else ""


def static_checks(src):
    mint_body = _branch_body(src, "mint")
    check_body = _branch_body(src, "check")
    verify_body = _branch_body(src, "verify")
    emit_tokens = ("emit_release_receipt", "SMH_LEDGER")
    s1 = all(tok in mint_body for tok in emit_tokens)
    s2 = (not any(t in check_body for t in emit_tokens)
          and not any(t in verify_body for t in emit_tokens))
    s3 = ('case "$SMH_LEDGER" in "$WT"/*)' in src) and ("SMH ledger must be OUTSIDE the worktree" in src)
    # emission must come AFTER the archive is sealed (mint_to "$OUT") within the mint branch
    s4 = ('mint_to "$OUT"' in mint_body
          and mint_body.index("emit_release_receipt") > mint_body.index('mint_to "$OUT"'))
    return s1, s2, s3, s4


def main():
    if not (os.path.exists(MINT_SH) and os.path.exists(EMIT)):
        chk("PRECONDITION_tooling_present", False, "missing %s or %s" % (MINT_SH, EMIT))
        print(json.dumps({"ALL_PASS": False, "results": results}, indent=2)); return 1

    # ---- FUNCTIONAL ----
    d = tempfile.mkdtemp()
    archive = os.path.join(d, "dummy-rXX.tar.gz")
    archive_bytes = b"\x1f\x8b dummy sealed archive bytes for emission selftest"
    open(archive, "wb").write(archive_bytes)
    pre = hashlib.sha256(open(archive, "rb").read()).hexdigest()
    ledger = os.path.join(d, "dummy-rXX.smh-ledger.json")
    rc = subprocess.call([sys.executable, EMIT, archive, ledger],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    led = json.load(open(ledger)) if os.path.exists(ledger) else {}
    recs = led.get("receipts", [])
    post = hashlib.sha256(open(archive, "rb").read()).hexdigest()

    # recompute the expected smh_archive_ref via the shipped module
    sys.path.insert(0, os.path.join(WT, "tools", "smh"))
    import smh_projection_registry as P1
    expect_digest = P1.smh_archive_hash(archive_bytes)

    f1 = (rc == 0 and len(recs) == 1 and recs[0]["receipt_body"]["movement_kind"] == "deep_export")
    sub = recs[0]["receipt_body"]["subject_refs"][0] if recs else {}
    f2 = (sub.get("ref_type") == "smh_archive_ref" and sub.get("digest") == expect_digest
          and recs and recs[0]["receipt_body"]["from_tier"] == "COLD"
          and recs[0]["receipt_body"]["to_tier"] == "DEEP")
    f3 = (pre == post)
    f4 = (led.get("model") == "smh.tier.transition.ledger.v1")
    chk("F1_one_deep_export", f1)
    chk("F2_cites_final_archive", f2)
    chk("F3_archive_unmodified", f3)
    chk("F4_external_ledger_model", f4)

    # ---- STATIC ----
    src = open(MINT_SH).read()
    s1, s2, s3, s4 = static_checks(src)
    chk("S1_emission_only_in_mint", s1)
    chk("S2_check_verify_no_emission", s2)
    chk("S3_ledger_outside_worktree_guard", s3)
    chk("S4_emission_post_seal", s4)

    # ---- ANTI-VACUITY ----
    chk("V0_shipped_passes_static", s1 and s2 and s3 and s4)
    # mutate: move an emission token into the verify branch -> S2 must reject
    mutated = src.replace(
        'mint_to "$a"; mint_to "$b"',
        'mint_to "$a"; mint_to "$b"; python3 "$WT/tools/smh/emit_release_receipt.py" "$a" "$SMH_LEDGER"')
    ms1, ms2, ms3, ms4 = static_checks(mutated)
    chk("V1_regression_caught", (mutated != src) and (ms2 is False),
        "emission injected into verify) branch is rejected by S2")

    allp = all(r["pass"] for r in results.values())
    print(json.dumps({"ALL_PASS": allp, "results": results}, indent=2, sort_keys=True))
    return 0 if allp else 1


if __name__ == "__main__":
    sys.exit(main())
