#!/usr/bin/env bash
# POSIX convenience wrapper. The authoritative, cross-platform release check is verify_release.py;
# this just execs it so existing `bash verify_release.sh` callers keep working unchanged.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/verify_release.py"
