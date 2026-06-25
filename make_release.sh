#!/usr/bin/env bash
# =============================================================================
# RETIRED — do not use. (Tools-doc hardening lane after r128.)
# =============================================================================
# This script is RETIRED. It is kept (not deleted) so future sessions do not
# accidentally reconstruct or reuse a broken mint path. It FAILS CLOSED below.
#
# Why retired (it disagreed with the canonical mint on every axis):
#   - stale imports: `from ugk.binding import ...` (module is now
#     `ugk.storage.binding`) -> aborts under `set -e`;
#   - pre-refactor grundnorm chmod list (store.py/binding.py/... at old paths);
#   - regenerated RELEASE.txt in the OLD r-less format (no release number,
#     schema_pin, ledger, or amendment_pin) -> would CLOBBER the maintained file;
#   - NON-deterministic tar (no --sort/--owner/--group/--numeric-owner/--mtime,
#     no `gzip -n`), wrong archive name, and incomplete exclusions.
#
# CANONICAL MINT PATH (deterministic, reproducible) — run by hand:
#
#   WT=<worktree>; OUT=/path/ugk-rNNN.tar.gz
#   # 1) clean caches; confirm grundnorm files are 444 (ugk/storage/store.py,
#   #    ugk/adr.py, and the rest of the grundnorm set)
#   find "$WT" -name __pycache__ -type d -prune -exec rm -rf {} + ; \
#   find "$WT" -name '*.pyc' -delete
#   # 2) regenerate RELEASE.txt MANUALLY for the release (release number,
#   #    gate_suite N/N, invariants/ADRs/ledger, invariants_pin, LEGEND_HASH,
#   #    schema_pin, amendment_pin if any, codex_hash)
#   # 3) deterministic, reproducible archive:
#   tar --sort=name --owner=0 --group=0 --numeric-owner \
#       --mtime='2026-01-01 00:00:00' \
#       --exclude='./__pycache__' --exclude='*/__pycache__' \
#       --exclude='*.pyc' --exclude='*.pyo' --exclude='*PRIVKEY*' \
#       --exclude='./genesis' --exclude='./.git' --exclude='./dist' \
#       --exclude='./test_dispatch_focused.py' \
#       -C "$WT" -cf - . | gzip -n > "$OUT"
#   # 4) sha256sum "$OUT"   (the release identity)
#
# Certify with:  ./verify_release.sh   (ugk harden + full posture gate suite)
# See RELEASE.txt "MINT PROVENANCE" for the per-release record.
# =============================================================================
echo "make_release.sh is RETIRED. A runnable deterministic mint entry point now"  >&2
echo "exists at tools/release/mint_release.sh (same canonical recipe documented"   >&2
echo "in this header, with fail-closed grundnorm + hygiene preconditions). Use:"    >&2
echo "  tools/release/mint_release.sh <output.tar.gz>   (or --check / --verify-deterministic)" >&2
echo "Certify with ./verify_release.sh. Refusing to run this stub (fail-closed)."   >&2
exit 2
