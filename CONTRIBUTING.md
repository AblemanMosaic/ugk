# Contributing to UGK

UGK is a governance substrate. Changes to it are themselves governed.

## Before you change anything

Understand the surface you're modifying:

```bash
ugk explain LEGEND-S-01      # any invariant by ID
ugk explain dkn_gate         # any gate by name
ugk explain 3003             # any CSIL integer
ugk constitution             # active law_hash, legend_hash, authority model
ugk posture                  # live φ scalar, disjunct coverage, ALT §8 matrix
```

The invariant registry (`ugk/invariants.py`) is the constitutional law.
The LEGEND (`ugk/binding.py`) is the canonical semantic vocabulary.
The gate suite is the acceptance criterion.

## The gate suite is the acceptance criterion

All patches must pass the full gate suite **at the current gate count** before
merge. Additions must also add corresponding gates — the count should not
decrease.

```bash
make test
# or directly:
python -m ugk.conformance.run_gates_batch
```

Fixes to existing functionality: gate count stays the same.
New invariants or surfaces: gate count increases by at least one per invariant.

## Constitutional changes

**New invariants** require a bound `ArchitecturalDecision` in `ugk/adr.py`:

```python
ArchitecturalDecision(
    id="ADR-13",
    context="...",
    decision="...",
    alternatives=["...", "..."],
    consequences="...",
    bound_invariants=["MY-NEW-S-01"],
)
```

- State the context clearly — what problem motivated this change?
- Name the alternatives you considered and why you rejected them
- Name the bound invariants explicitly
- A change without an ADR is a change without a rationale

**Changes to `ugk/invariants.py`** change `law_hash` — this is correct and
intentional. Update `RELEASE.txt` with the new `invariants_pin`:

```bash
sha256sum ugk/invariants.py
# paste the hash as invariants_pin in RELEASE.txt
```

**Changes to the LEGEND** (`ugk/binding.py`) change `LEGEND_HASH` — same.
Update `RELEASE.txt`. Run `python readme_gen.py` — the README footer will
show the new hash.

**Changes to `ugk/kernel.py`** (Grundnorm layer, `444` permissions) require
strong justification. The kernel is intentionally minimal and conservative.
A kernel change that does not correspond to a new invariant and gate is almost
certainly wrong.

## Regenerate the README after changes

```bash
python readme_gen.py
```

The committed `README.md` must always match:

```bash
python readme_gen.py --check
# exits 0 if current, exits 1 if stale
```

`make readme` does the same thing.

## Verify the full release

```bash
./verify_release.sh
```

This checks `invariants_pin`, `LEGEND_HASH`, and runs the full gate suite.
A release is only valid if all three pass.

## Open theory questions

The roadmap tracks open problems in the underlying theory:

- **ALT temporal-PROV** — the provenance extension to the Autonomous Legitimacy
  Theorem; formally connecting the receipt chain to the temporal-PROV model
- **SCIT/GTI full integration** — complete integration of the Semantic
  Constitutional Integrity Theory with the Governance Theory Index
- **A1 set-valued authority** — extending the authority model to support
  set-valued authority principals (multi-party authorization)

Contributions addressing open theorems are welcome with:
- A precise statement of the theorem or gap being addressed
- A corresponding ADR if the contribution changes the kernel
- Gate coverage for any new invariants introduced

## Reporting issues

**Kernel correctness issues:** describe the invariant or gate that fails or is
missing. Reference the relevant invariant ID (e.g. `CHC-S-01`) and the expected
behavior per the ADR.

**Theory questions:** reference the relevant ALT or SCIT section where
applicable. The theory is not decoration — the invariants are derived from it.

**Security issues:** see [SECURITY.md](SECURITY.md).
