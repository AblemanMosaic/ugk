#!/usr/bin/env bash
# =============================================================================
# mint_release.sh — runnable deterministic mint entry point (PACKAGING ONLY).
# =============================================================================
# This is the runnable counterpart to the canonical deterministic mint recipe
# documented in make_release.sh (RETIRED stub) and in RELEASE.txt
# (MINT PROVENANCE). It reproduces that recipe EXACTLY and adds fail-closed
# preconditions. It is packaging machinery, NOT an authority source:
#
#   * it READS the worktree as-is and emits ONE gzip tarball;
#   * it NEVER regenerates RELEASE.txt, recomputes pins, mints amendments,
#     touches the codex, or alters ANY canonical frame artifact;
#   * it fails closed (nonzero exit, no archive) if a precondition is unmet.
#
# The authority for law/schema/legend/registry/ledger/codex remains the in-tree
# artifacts and verify_release.sh. This tool only packages what is already there.
#
# Usage:
#   tools/release/mint_release.sh <output.tar.gz> [worktree]
#   tools/release/mint_release.sh --check [worktree]            # preflight only, no mint
#   tools/release/mint_release.sh --verify-deterministic [worktree]  # double-mint + compare
#
# Certify the result with:  ./verify_release.sh
# =============================================================================
set -euo pipefail

MODE="mint"
case "${1:-}" in
  --check)               MODE="check";  shift ;;
  --verify-deterministic) MODE="verify"; shift ;;
  "" ) echo "usage: mint_release.sh <output.tar.gz> [worktree] | --check [wt] | --verify-deterministic [wt]" >&2; exit 2 ;;
esac

if [ "$MODE" = "mint" ]; then
  OUT="${1:?usage: mint_release.sh <output.tar.gz> [worktree]}"
  WT="$(cd "${2:-$(dirname "$0")/../..}" && pwd)"
else
  WT="$(cd "${1:-$(dirname "$0")/../..}" && pwd)"
fi

fail() { echo "mint_release: FAIL-CLOSED: $*" >&2; exit 3; }

# --- preflight 1: grundnorm files present and read-only-locked (444) ----------
GRUNDNORM=(
  ugk/invariants.py
  ugk/adr.py
  ugk/amendment_ledger.json
  ugk/storage/store.py
  RELEASE.txt
  ugk/codex/CODEX.md
  ugk/codex/CODEX_HASH.txt
  ugk/codex/sci_typing.json
  ugk/kernel.py
  tools/grbsa/CONTINUITY_ATTESTATION.json
)
for f in "${GRUNDNORM[@]}"; do
  [ -f "$WT/$f" ] || fail "grundnorm file missing: $f"
  perm="$(stat -c '%a' "$WT/$f")"
  [ "$perm" = "444" ] || fail "grundnorm file not locked 444 (is $perm): $f"
done

# --- preflight 2: hygiene — no caches/scratch/secrets/test-junk in the tree ----
# (the tar recipe also EXCLUDES these; this assertion fails closed BEFORE minting
#  so a dirty tree is never silently packaged.)
hyg() {
  # $1 = human label, $2.. = find predicate
  local label="$1"; shift
  local hits
  hits="$(find "$WT" -path "$WT/.git" -prune -o \( "$@" \) -print 2>/dev/null | head -5 || true)"
  [ -z "$hits" ] || fail "hygiene: found $label in worktree (clean first):"$'\n'"$hits"
}
hyg "__pycache__ dirs"      -name __pycache__ -type d
hyg "*.pyc"                 -name '*.pyc' -type f
hyg "*.pyo"                 -name '*.pyo' -type f
hyg "genesis/ dir"          -path "$WT/genesis" -type d
hyg "PRIVKEY material"      -iname '*PRIVKEY*' -type f
hyg "G6 proof cache"        -name 'g6_proof_cache.json' -type f
hyg "scratch backups"       \( -name '*~' -o -name '*.bak' -o -name '*.orig' -o -name '*.swp' -o -name '*.rej' \) -type f
# r136 carried mint-tooling hygiene erratum (declared separately from the bounded reversible
# terminal-write retry payload): a release must NEVER ship the continuity-archive staging dir or any
# nested release tarball. Stage continuity archives OUTSIDE the worktree (certify_release --archives-dir).
hyg "_archives/ staging dir"        -path "$WT/_archives" -type d
hyg "nested release archive(s)"     -name 'ugk-r*.tar.gz' -type f

# --- the CANONICAL deterministic recipe (byte-for-byte as make_release.sh header) ---
mint_to() {
  tar --sort=name --owner=0 --group=0 --numeric-owner \
      --mtime='2026-01-01 00:00:00' \
      --exclude='./__pycache__' --exclude='*/__pycache__' \
      --exclude='*.pyc' --exclude='*.pyo' --exclude='*PRIVKEY*' \
      --exclude='./genesis' --exclude='./.git' --exclude='./dist' \
      --exclude='*g6_proof_cache.json' \
      --exclude='./_archives' --exclude='./ugk-r*.tar.gz' \
      --exclude='./test_dispatch_focused.py' \
      -C "$WT" -cf - . | gzip -n > "$1"
}

case "$MODE" in
  check)
    echo "mint_release: PREFLIGHT OK (grundnorm 444 x${#GRUNDNORM[@]}; hygiene clean). No archive written (--check)."
    ;;
  verify)
    a="$(mktemp -t mint_a.XXXXXX.tar.gz)"; b="$(mktemp -t mint_b.XXXXXX.tar.gz)"
    mint_to "$a"; mint_to "$b"
    sa="$(sha256sum "$a" | cut -d' ' -f1)"; sb="$(sha256sum "$b" | cut -d' ' -f1)"
    rm -f "$a" "$b"
    [ "$sa" = "$sb" ] || fail "non-deterministic: two mints differ ($sa != $sb)"
    echo "mint_release: DETERMINISTIC OK (two mints identical): $sa"
    ;;
  mint)
    case "$OUT" in "$WT"/*) fail "output must be OUTSIDE the worktree (would self-include): $OUT";; esac
    mint_to "$OUT"
    echo "mint_release: minted $OUT"
    sha256sum "$OUT"
    # SMH-I5 (native release hook): AFTER the archive is sealed, record ONE external deep_export
    # tier-transition receipt for the minted archive (COLD->DEEP). The archive is NOT modified
    # (emission reads its final bytes read-only); the SMH ledger is EXTERNAL to the worktree and
    # to the UGK constitutional chain. Only the real mint emits (not --check / --verify-deterministic),
    # so deterministic minting is unaffected. Disable with SMH_EMIT=0.
    if [ "${SMH_EMIT:-1}" = "1" ] && command -v python3 >/dev/null 2>&1 && [ -f "$WT/tools/smh/emit_release_receipt.py" ]; then
      SMH_LEDGER="${SMH_LEDGER_PATH:-${OUT%.tar.gz}.smh-ledger.json}"
      case "$SMH_LEDGER" in "$WT"/*) fail "SMH ledger must be OUTSIDE the worktree: $SMH_LEDGER";; esac
      if python3 "$WT/tools/smh/emit_release_receipt.py" "$OUT" "$SMH_LEDGER"; then
        echo "mint_release: SMH deep_export receipt recorded (external ledger: $SMH_LEDGER)"
      else
        echo "mint_release: WARNING SMH emission did not record (archive unaffected)" >&2
      fi
    fi
    ;;
esac
