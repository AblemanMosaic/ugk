#!/usr/bin/env bash
# verify_deep.sh — DEEP verification surface (maintained, beyond verify_release.sh).
#
# Runs, with bounded per-leg timeouts and a final table:
#   - the release verifier (verify_release.sh: 83-gate suite + pins)
#   - all CGProj construction phase gates (P1..P6) under construction/cgproj/
#   - GRBSA 9 leaf gates (direct) + the G6 verifier self-test (mechanics)
#   - the standalone overlay probes (b1/b2/b4a/capability_register_check)
#
# Each leg is bounded (no hang can stall the run); each prints its own verdict and is timed.
# Exit 0 iff every established leg passed. Corpus-dependent / not-established postures are reported
# but do not fail the run (matches verify_release semantics).
#
# This is a DEEP surface for archival/construction confidence. RELEASE ACCEPTANCE remains
# verify_release.sh; verify_deep additionally exercises the maintained construction gates.

set -u
REPO="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$REPO"
PY="${PYTHON:-python3}"
LEG_TIMEOUT="${LEG_TIMEOUT:-300}"  # G6 corpus-present re-derivation ~200s

NAMES=""; CODES=""
run_leg() {
  # run_leg "<label>" <cmd...>
  label="$1"; shift
  printf '———— %s ————\n' "$label"
  t0=$(date +%s)
  timeout "$LEG_TIMEOUT" "$@" > "/tmp/vd_$$.log" 2>&1
  rc=$?
  t1=$(date +%s)
  tail -1 "/tmp/vd_$$.log"
  if [ "$rc" -eq 124 ]; then
    printf '  -> %s TIMED OUT after %ss\n\n' "$label" "$LEG_TIMEOUT"
  else
    printf '  -> %s exit=%d (%ss)\n\n' "$label" "$rc" "$((t1 - t0))"
  fi
  NAMES="$NAMES|$label"
  CODES="$CODES|$rc"
}

echo "================================================================"
echo " UGK verify_deep — deep verification surface"
echo "================================================================"

run_leg "release verifier (83-gate suite)" bash "$REPO/verify_release.sh"

for g in phase1_structural_validity_gate phase2_execution_removability_gate \
         phase3_determinism_gate phase4_fidelity_gate phase4_5_jurisdiction_gate \
         phase5a_docs_integration_gate phase5b_explain_gate phase6_full_validation_gate; do
  run_leg "cgproj:$g" "$PY" "$REPO/construction/cgproj/$g.py" "$REPO"
done

# r135: G6 is no longer a standalone aggregate orchestrator (it is now a bundle consumer, exercised
# by certify_release.py --phase bundle). The deep surface preserves GRBSA coverage by running the 9
# leaf gates DIRECTLY, and proves the G6 verifier mechanics via its focused self-test gate.
for g in g1_core_shape_gate g1_separation_symmetry_gate g2_substrate_naming_gate \
         g3_adapter_equivalence_gate g4a_adapter_generality_gate g4b_projection_adapter_gate \
         g4c_explain_adapter_gate category_separation_gate g5_execution_adapter_gate; do
  run_leg "grbsa:$g" "$PY" "$REPO/tools/grbsa/$g.py" "$REPO"
done
run_leg "G6 verifier self-test" "$PY" "$REPO/tools/grbsa/g6_incremental_gate.py"

for t in b1_conformance b2_conformance b4a_conformance capability_register_check; do
  run_leg "probe:$t" "$PY" "$REPO/tools/$t.py"
done

# ---- final table ----
echo "================================================================"
echo " DEEP VERIFICATION SUMMARY"
echo "================================================================"
overall=0
OLDIFS="$IFS"; IFS='|'
set -- $NAMES; shift 0
# rebuild arrays by splitting on '|'
i=0
echo "$NAMES" | tr '|' '\n' | sed '/^$/d' > "/tmp/vd_names_$$"
echo "$CODES" | tr '|' '\n' | sed '/^$/d' > "/tmp/vd_codes_$$"
IFS="$OLDIFS"
paste -d'|' "/tmp/vd_names_$$" "/tmp/vd_codes_$$" | while IFS='|' read -r nm cd; do
  if [ "$cd" -eq 0 ]; then st="PASS"; elif [ "$cd" -eq 124 ]; then st="TIMEOUT"; else st="FAIL"; fi
  printf '  %-7s  %s\n' "$st" "$nm"
done
# overall verdict (recompute; while-subshell can't set parent vars in sh)
if grep -vq '^0$' "/tmp/vd_codes_$$"; then overall=1; else overall=0; fi
echo "----------------------------------------------------------------"
if [ "$overall" -eq 0 ]; then
  echo " VERIFY_DEEP: ALL LEGS PASS"
else
  echo " VERIFY_DEEP: one or more legs did not pass (see table)"
fi
echo "================================================================"
rm -f "/tmp/vd_$$.log" "/tmp/vd_names_$$" "/tmp/vd_codes_$$"
exit "$overall"
