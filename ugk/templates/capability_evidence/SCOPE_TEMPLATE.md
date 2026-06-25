# Capability Scope — Template

**Consumer:** _<your consumer name, e.g. "AbleTools", "CPVM", "MyConsumer">_
**Registry referenced:** _<registry document + version, e.g. "ESA Capability Registry v6.25">_
**Last reviewed:** _<YYYY-MM-DD>_

This is the human-readable consumer scope document. It declares which
capabilities from the referenced registry apply to this consumer, with
explicit status per the six-term vocabulary. The machine-checkable
companion is a Python module exporting a `SCOPE` dict (see
`evidence_scope_template.py`).

The status vocabulary preserves six distinctions:

| Status         | Meaning                                                    |
|----------------|------------------------------------------------------------|
| `DONE`         | implemented + evidenced + verifying (gate runs and passes) |
| `PARTIAL`      | implemented for a declared subset; gate covers that subset |
| `FUTURE`       | planned realization; concrete next step exists, no gate yet|
| `OUT_OF_SCOPE` | explicitly waived for this consumer                         |
| `ASPIRATIONAL` | declared in registry; no realization path for this consumer |
| `UNDECLARED`   | registry mentions; this consumer has not addressed         |

The determinism flag distinguishes:
- `true`  — Class I (deterministic gate-bound, no interpretation)
- `false` — Class II (receipt-backed but interpretive judgment)
- `null`  — not applicable (Class III/IV, OUT_OF_SCOPE, ASPIRATIONAL)

## Applicable capabilities

| Cap   | Name                | Status   | Gate              | Det.  | Notes |
|-------|---------------------|----------|-------------------|-------|-------|
| Cap-A | _example name_      | DONE     | example_gate      | true  |       |
| Cap-B | _example name_      | PARTIAL  | example_gate_b    | false | _what is partial; what is interpretive_ |
| Cap-C | _example name_      | FUTURE   | —                 | —     | _stretch goal; intended approach_ |

## Out-of-scope capabilities

| Cap   | Name                | Reason                                   |
|-------|---------------------|------------------------------------------|
| Cap-X | _example name_      | _which other consumer / context owns it_ |

## Aspirational / unaddressed

Capabilities declared in the registry that this consumer does not plan to
address. Listed for transparency; honest-absent semantics.

| Cap   | Name                | Notes                                    |
|-------|---------------------|------------------------------------------|
| Cap-Y | _example name_      | _why not addressed; pointer to owner_    |
