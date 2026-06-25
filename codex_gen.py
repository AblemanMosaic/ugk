#!/usr/bin/env python3
"""codex_gen.py — Phase-4 derived projection of CODEX.md from the authoritative registry.

CODEX.md is a LEAF projection, never a source (Application Codex v0.1, Projection DAG).
Authority direction (ratified 0B): `ugk/invariants.py` is the authoritative registry;
`law_hash = sha256(invariants.py)`. This generator derives the shipped CODEX.md from the
registry (+ ADRs + LEGEND), deterministically and idempotently. The SCI routing table is an
EXTERNAL first-class data artifact (ugk/codex/sci_typing.json), consumed here and validated as a
fail-closed exactly-once routing gate before emitting. The table is classification metadata over
the registry; it is not invariants.py and does not affect law_hash.

When run with an output dir argument it writes CODEX.md + CODEX_HASH.txt there (pass ugk/codex to
re-pin in place); the live re-pin of ugk/codex/ is a governed, explicitly-approved mutation step.
"""
import hashlib, sys, os, json
from pathlib import Path
import ugk
from ugk.invariants import INVARIANT_REGISTRY
from ugk.adr import ADR_REGISTRY
from ugk.storage.binding import LEGEND_HASH, LEGEND_ENTRY_COUNT

TRUNC = 70  # empirical: matches the shipped CODEX.md projection (hard cut, then "...").

# ---- SCI typing (the routing table) — loaded from the external authoritative artifact. ----
# ugk/codex/sci_typing.json is classification metadata over INVARIANT_REGISTRY (not invariants.py,
# so not part of law_hash). A registry entry absent from it MUST fail the exactly-once gate below.
_TYPING_PATH = Path(ugk.__file__).parent / "codex" / "sci_typing.json"

def _load_typing():
    data = json.loads(_TYPING_PATH.read_text())
    t = data["types"]
    return set(t["S-INH"]), set(t["S-RES"]), set(t["IC"]), set(t["IR"])

try:
    S_INH, S_RES, IC, IR = _load_typing()
    _LOAD_ERR = None
except Exception as e:  # missing / malformed / wrong shape -> fail closed in consistency_check
    S_INH = S_RES = IC = IR = set()
    _LOAD_ERR = f"{type(e).__name__}: {e}"
_SETS = {'S-INH': S_INH, 'S-RES': S_RES, 'IC': IC, 'IR': IR}


def consistency_check():
    """Fail-closed routing gate: the typing artifact loaded, every registry entry is typed
    exactly once, every typing refers to a real registry entry, and the four sets are disjoint."""
    if _LOAD_ERR is not None:
        return False, [f'cannot load {_TYPING_PATH}: {_LOAD_ERR}']
    reg = set(INVARIANT_REGISTRY)
    errors = []
    # exactly-once: union covers registry, disjoint sets
    seen = {}
    for tname, s in _SETS.items():
        for i in s:
            if i in seen:
                errors.append(f'DOUBLE-ROUTED: {i} in {seen[i]} and {tname}')
            seen[i] = tname
    for i in sorted(reg - set(seen)):
        errors.append(f'UNTYPED registry entry: {i} (add to sci_typing.json)')
    for i in sorted(set(seen) - reg):
        errors.append(f'TYPING refers to non-registry id: {i}')
    return (not errors), errors


def _trunc(s: str) -> str:
    return (s[:TRUNC] + '...') if len(s) > TRUNC else s


def _render_layer(ids) -> list:
    """Render a set of registry ids, grouped by phase (preserved inside the layer)."""
    R = INVARIANT_REGISTRY
    ids = set(ids)
    out = []
    for p in sorted({R[i].introduced_in for i in ids}):
        members = sorted(i for i in ids if R[i].introduced_in == p)
        out.append('')
        out.append(f'**{p.upper()}**')
        out.append('')
        for i in members:
            out.append(f'- **{i}** -- {_trunc(R[i].statement)}')
    return out


def generate() -> str:
    R = INVARIANT_REGISTRY
    A = ADR_REGISTRY
    nums = [int(''.join(c for c in R[i].introduced_in if c.isdigit()) or 0) for i in R]
    lo, hi = min(nums), max(nums)
    out = []
    out.append(f'# UGK v0.1.0 — Constitutional Codex (Phases {lo}-{hi})')
    out.append('*Derived projection (codex_gen) of invariants.py — leaf artifact, not a source.*')
    out.append(f'**LEGEND_HASH:** `{LEGEND_HASH}`  ')
    out.append(f'Registry entries: {len(R)}  ADRs: {len(A)}  LEGEND: {LEGEND_ENTRY_COUNT}')
    out.append(f'Routing: S-inherited {len(S_INH)} · S-residue {len(S_RES)} (declared exclusion) · '
               f'IC {len(IC)} · IR {len(IR)}')
    out.append('---')
    out.append('## S — inherited / restated obligations')
    out.append('*Restate GK domain obligations UGK discharges. Authoritative S source is '
               'invariants.py; see the Application Codex inheritance table for the discharge mapping.*')
    out += _render_layer(S_INH)
    out.append('')
    out.append('## S-candidate residue — declared exclusion')
    out.append('*Carried, NOT adjudicated as S, pending independent residue-blind re-derivation '
               '(Phase 6). The interpretive-closure / semantic-frame cluster.*')
    out += _render_layer(S_RES)
    out.append('')
    out.append('## IC — selected configuration commitments')
    out.append('*Selections from the GK configuration manifold (realized in code).*')
    out += _render_layer(IC)
    out.append('')
    out.append('## IR — realized mechanisms and checks')
    out.append('*Realizations registered in the invariant registry; they discharge inherited GK '
               'obligations but are not themselves novel domain physics.*')
    out += _render_layer(IR)
    out.append('')
    out.append('## ADRs')
    out.append('')
    for aid in sorted(A):
        out.append('')
        out.append(f'### {aid}')
        out.append(f'**Bound:** {", ".join(A[aid].bound_invariants)}')
    return '\n'.join(out) + '\n'


def main(argv):
    out_dir = argv[1] if len(argv) > 1 else '/tmp/codex_candidate'
    ok, errors = consistency_check()
    print('SCI routing gate:', 'PASS' if ok else 'FAIL')
    for e in errors:
        print('  -', e)
    if not ok:
        print('Refusing to emit: routing gate failed (fail-closed).')
        return 2
    text = generate()
    h = hashlib.sha256(text.encode()).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'CODEX.md'), 'w') as f:
        f.write(text)
    with open(os.path.join(out_dir, 'CODEX_HASH.txt'), 'w') as f:
        f.write(h + '\n')
    print(f'Wrote {out_dir}/CODEX.md ({len(text)} bytes) and CODEX_HASH.txt')
    print(f'CODEX_HASH = {h}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
