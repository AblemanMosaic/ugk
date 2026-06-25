"""evidence_scope_template.py — consumer SCOPE dict skeleton.

This is the MACHINE-CHECKABLE companion to a human-readable
SCOPE_TEMPLATE.md scope document. Each consumer copies this file
into their own tree (e.g. `<consumer>/governance/codex/
evidence_scope.py`) and fills in the entries for the registry they
reference.

The file exports a single `SCOPE` dict mapping cap_id strings to entry
dicts. Each entry MUST have `name` and `status`. Other fields are
optional with the indicated defaults.

The helper `ugk.authority.capability_evidence.load_scope(module)` parses this
module into a tuple of `CapabilityClaim`. Use
`verify_evidence_map(claims, gates_dir)` to assert that every DONE /
PARTIAL claim has its named gate file present.

Status vocabulary (one per entry):
  DONE          — implemented + evidenced + verifying
  PARTIAL       — implemented for declared subset; gate present
  FUTURE        — planned realization; no gate yet
  OUT_OF_SCOPE  — explicitly waived for this consumer
  ASPIRATIONAL  — declared in registry; no realization path
  UNDECLARED    — registry mentions; consumer hasn't addressed

The deterministic flag (per entry, optional):
  True   — Class I deterministic gate-bound
  False  — Class II receipt-backed interpretive
  None   — not applicable (Class III/IV / OUT_OF_SCOPE / ASPIRATIONAL)
"""

SCOPE = {
    # Class I — deterministic gate-bound (DONE)
    "Cap-A": {
        "name": "Example Capability A",
        "status": "DONE",
        "gate": "example_gate",
        "deterministic": True,
        "scope_notes": "",
    },

    # Class II — receipt-backed interpretive (PARTIAL)
    "Cap-B": {
        "name": "Example Capability B",
        "status": "PARTIAL",
        "gate": "example_gate_b",
        "deterministic": False,
        "scope_notes": "What is partial; what is interpretive.",
    },

    # FUTURE / stretch — declared, no gate yet
    "Cap-C": {
        "name": "Example Capability C",
        "status": "FUTURE",
        "gate": None,
        "deterministic": None,
        "scope_notes": "Stretch goal; intended approach.",
    },

    # OUT_OF_SCOPE — waived for this consumer
    "Cap-X": {
        "name": "Example Capability X",
        "status": "OUT_OF_SCOPE",
        "gate": None,
        "deterministic": None,
        "scope_notes": "Which other consumer / context owns this.",
    },

    # ASPIRATIONAL — registry mentions, no path for this consumer
    "Cap-Y": {
        "name": "Example Capability Y",
        "status": "ASPIRATIONAL",
        "gate": None,
        "deterministic": None,
        "scope_notes": "No realization path; flagged for transparency.",
    },
}
