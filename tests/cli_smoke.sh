#!/usr/bin/env bash
# CLI end-to-end smoke: charter -> govern -> verify, isolated --state-dir only.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
SD="$(mktemp -d)"; PK="$(PYTHONPATH=. python -c 'from ugk.conformance._fixture import fixture_pubkey;print(fixture_pubkey())')"
unset UGK_GENESIS_DIR
PYTHONPATH=. python -m ugk.cli --state-dir "$SD" charter --pubkey "$PK" --force >/dev/null
PYTHONPATH=. python -m ugk.cli --state-dir "$SD" govern --intent verify --subject smoke | grep -q '"admitted": true'
PYTHONPATH=. python -m ugk.cli --state-dir "$SD" verify >/dev/null
echo "cli smoke: PASS"
