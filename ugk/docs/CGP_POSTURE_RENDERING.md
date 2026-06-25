# CGP Posture Rendering — Guidance for Consumers

**Audience.** Authors building dashboards, status displays, audit
panels, or any user-facing rendering of CGP governance posture from
UGK. This document specifies the canonical posture surface and shows
how to render it in different consumer idioms (CLI / TUI / GUI / JSON /
web). It does **not** prescribe a single dashboard — consumers own
their rendering realization.

**Substrate stability statement.** The `GovernancePosture` field set,
the three compute entry points, and the `verify_hash()` guarantee are
stable across UGK releases under the M2.3 line (`law_hash =
546a9e90fd780dec…`). Consumer dashboards can depend on the surface
documented here without expecting breakage in additive UGK releases.

> **CGP integration note (corrected; doc-only).** "Stable under the M2.3 line" describes the surface
> relative to the **M2.3** baseline it was authored against. **CGP as a subsystem is constitutionally
> INTEGRATED into the current r123 frame** (invariants `CGP-S-01/02/03`, `SCOPE-S-01/02`, `ESA-S-01`,
> `CTR-S-01/07`, `SRSA-S-01` + CGP-family conformance gates are part of the certified r125 frame;
> `law_hash a3992e45...`, 100 gates). The posture surface itself **renders the live frame** (it asserts no
> fixed `law_hash`), so it remains valid across the advance from the M2.3 line to r123.

For orientation on the CGP execution substrate (runner / CTR / SRSA /
how to run UGK headlessly), see
[`CGP_EXECUTION_SUBSTRATE.md`](./CGP_EXECUTION_SUBSTRATE.md). For the
CGP-ESA capability registry, see
[`CGP_CAPABILITIES.md`](./CGP_CAPABILITIES.md).

---

## §1. Ownership recap

The corrected ontology divides responsibility cleanly:

| Concern | Owner | Where it lives |
|---|---|---|
| **Posture substrate** — fields, semantics, compute logic, hash discipline | CGP / UGK | `ugk.cgp` (canonical) / `ugk.posture` (implementation) |
| **Rendering realization** — how the posture is displayed to humans | Consumer | Consumer source (Navigator GUI / AbleTools CLI / future) |
| **Refresh discipline** — when the rendering recomputes | Consumer | Consumer event loop / refresh policy |
| **Aggregation across instances** — multi-deployment dashboards | Consumer | Consumer rollup logic |

UGK does **not** ship a posture dashboard. There is no canonical TUI,
GUI, or web rendering — and there shouldn't be. Different consumers
serve different audiences (developers, auditors, operators, deploy
engineers) and benefit from different visual idioms over the same
canonical data.

A future tiny CLI posture printer may be added to UGK as a separate
phase if a common operational need surfaces. It is explicitly out of
scope for this document.

## §2. The canonical `GovernancePosture` surface

`ugk.posture.GovernancePosture` is the authoritative dataclass. The
canonical entry point is `ugk.cgp` — `compute()`, `compute_from_store()`,
and `required_attributes()` are re-exported from `ugk.cgp.posture`.

### §2.1 Fields

A `GovernancePosture` instance carries the following fields. Consumer
dashboards may display any subset; the field names are stable and
should appear verbatim (or alongside human-friendly labels) so audit
correspondence is unambiguous.

| Field | Type | Meaning |
|---|---|---|
| `posture_hash` | `str` | Content-addressed self-hash. The integrity tag of the entire posture. |
| `law_hash` | `str` | Hash of the constitutional substrate (`invariants.py`). M2.3 line: `546a9e90fd780dec…`. |
| `session_dkn` | `str` | Deployment key name for the current session. |
| `authority_model` | `str` | Declared authority model (e.g., `"undeclared"`, `"genesis_only"`, `"warrant_scoped"`). |
| `chain_intact` | `bool` | Whether the receipt chain verifies end-to-end. |
| `receipt_count` | `int` | Number of receipts in the store at compute time. |
| `phi` | `float` | The scalar governance posture metric (designed budget). |
| `disjunct_a` / `disjunct_b` / `disjunct_c` | `str` | The three disjunctive posture descriptors. |
| `require_gate` | `bool` | Whether kernel admission requires a gate decision. |
| `require_warrant` | `bool` | Whether ops require a warrant binding. |
| `require_intent` | `bool` | Whether ops require an intent declaration. |
| `require_scoped_intent` | `bool` | Whether scoped (per-jurisdiction) intent is required. |
| `matrix_cells` | `str` | Compact descriptor of the posture matrix cell. |
| `computed_at` | `str` | RFC-3339 timestamp of compute. **Part of `posture_hash`** — two otherwise identical posture computations at different times will have different `posture_hash` values. |

### §2.2 Methods

`GovernancePosture` is a frozen dataclass. The only method of interest
to dashboard authors is:

```python
posture.verify_hash() -> bool
```

Returns `True` iff `posture_hash` is the canonical content-hash of the
posture's body fields. A `False` return is an **integrity failure**, not
a cosmetic warning — see §5.

### §2.3 Compute entry points (the three modes)

The three canonical entry points are at `ugk.cgp`. Choose based on
what the consumer has access to:

```python
# Mode 1 — owner with a live kernel (most common)
from ugk.cgp import compute
posture = compute(kernel)

# Mode 2 — store-only consumer (no kernel held; CPVM bridge pattern)
from ugk.cgp import compute_from_store
posture = compute_from_store(
    store,
    session_dkn=session_dkn,
    law_hash=law_hash,
    authority_model="undeclared",
)
# (require_scoped_intent / will_store are NOT compute_from_store parameters;
#  require_scoped_intent is an OUTPUT GovernancePosture field — see the field table)

# Mode 3 — vendored-kernel consumer (AbleTools Organs pattern)
posture = kernel.organs.compute_posture()
```

All three modes return the same `GovernancePosture` shape. The
posture body fields are deterministic for equivalent inputs taken
**at the same moment**. The `computed_at` field is part of the
posture body hash, so two otherwise identical posture computations
at different times will produce different `posture_hash` values.
This is by design: the hash binds the snapshot to its capture
instant, so a posture object always identifies WHEN it was sampled
as well as what was sampled.

`ugk.cgp.required_attributes()` returns the tuple of kernel
attribute names that `compute(kernel)` reads. Useful for dashboards
that want to assert kernel shape before calling `compute()`.

## §3. The three compute modes — quick reference

| Mode | Entry point | When to use | Example consumer |
|---|---|---|---|
| 1 | `ugk.cgp.compute(kernel)` | You hold a live `GovernanceKernel` | Test harness, owner CLI |
| 2 | `ugk.cgp.compute_from_store(store, …)` | You hold a receipt store but no kernel | CPVM `AuthoritativeChain` |
| 3 | `kernel.organs.compute_posture()` | You hold a kernel that exposes an organs facade | AbleTools `Organs` |

The three modes produce equivalent posture body content for equivalent
inputs; the `posture_hash` is independent of which mode emitted it.

---

## §4. Rendering idioms

The examples below are **illustrative sketches**, not canonical
implementations. Every consumer is free to render the posture in
whatever idiom fits its audience. The only requirement is that the
rendering preserves the field names and semantics declared in §2.

### §4.1 CLI tabular output

Plain text, no dependencies. Good for `--posture` flags on consumer
CLIs, for log lines, or for `acis status`-style commands.

```python
from ugk.cgp import compute

posture = compute(kernel)

def render_cli_table(p) -> str:
    rows = [
        ("law_hash",             p.law_hash[:16] + "…"),
        ("session_dkn",          p.session_dkn or "(none)"),
        ("authority_model",      p.authority_model),
        ("chain_intact",         "yes" if p.chain_intact else "NO"),
        ("receipt_count",        str(p.receipt_count)),
        ("require_gate",         str(p.require_gate)),
        ("require_warrant",      str(p.require_warrant)),
        ("require_intent",       str(p.require_intent)),
        ("require_scoped_intent", str(p.require_scoped_intent)),
        ("phi",                  f"{p.phi:.3f}"),
        ("matrix_cells",         p.matrix_cells),
        ("posture_hash",         p.posture_hash[:16] + "…"),
        ("verify_hash()",        "OK" if p.verify_hash() else "FAIL"),
    ]
    width = max(len(k) for k, _ in rows)
    return "\n".join(f"  {k:<{width}}  {v}" for k, v in rows)

print(render_cli_table(posture))
```

### §4.2 CLI JSON output

For piping into `jq`, structured logs, CI assertions, or downstream
tools. The field names mirror §2 verbatim — no renaming.

```python
import json, dataclasses
from ugk.cgp import compute

posture = compute(kernel)
print(json.dumps(dataclasses.asdict(posture), indent=2, sort_keys=True))
```

Adding `verify_hash()` to the payload is recommended for downstream
consumers that don't import UGK:

```python
payload = dataclasses.asdict(posture) | {"_verify_hash": posture.verify_hash()}
print(json.dumps(payload, indent=2, sort_keys=True))
```

The leading underscore signals this is a derived check, not a
substrate field.

### §4.3 TUI panel sketch (library-agnostic)

Pseudocode for a terminal UI panel. The structure — header / body /
status line — translates directly to most TUI toolkits (curses,
prompt_toolkit, textual, rich, blessed).

```python
# ── CGP Governance Posture ─────────────────────────────────────
# law_hash      546a9e90fd780dec…
# session       deploy-prod-2026
# authority     warrant_scoped
# chain         ✓ intact            receipts: 1,283
# requires      gate ✓  warrant ✓  intent ✓  scoped ✓
# phi           0.871                matrix: [a|b|c]
#
# integrity     OK    (posture_hash 3f7c…)
# ───────────────────────────────────────────────────────────────
```

Refresh policy: recompute on each panel paint, or every N seconds via
a background task. Do not cache the posture across the panel's
lifecycle; see §5.

### §4.4 GUI panel sketch (widget-toolkit-agnostic)

For Qt / GTK / Cocoa / Tk / web GUI panels. The structure is the same
information arranged as labeled widgets, often in a two-column
key/value grid with a colored status indicator for `chain_intact` and
`verify_hash()`.

Recommended widget layout:

```
┌─ Governance Posture ────────────────────────────────────────┐
│                                                              │
│  ●  Chain intact            ●  Integrity OK                  │
│                                                              │
│  Law hash:        546a9e90fd780dec…                          │
│  Session:         deploy-prod-2026                           │
│  Authority:       warrant_scoped                             │
│  Receipts:        1,283                                      │
│  Phi:             0.871                                      │
│  Matrix cells:    [a|b|c]                                    │
│                                                              │
│  Requires:  [Gate] [Warrant] [Intent] [Scoped Intent]        │
│                                                              │
│  Computed at:     2026-06-12T22:14:03Z                       │
│  Posture hash:    3f7c…  [Copy]                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

The two indicator lights (`chain_intact`, `verify_hash()`) are the
most important visual elements — they should be the first things a
viewer's eye lands on. Red/green is appropriate; if the integrity
indicator is red, the rendering should make this prominent (modal
warning, banner, or refusal to display the rest of the posture as if
it were valid).

Navigator's `GovernanceDashboard` (`navigator/gui/dialogs/
governance_dashboard.py`) is one realization of this pattern; consumers
are free to copy its structure or diverge.

### §4.5 Web dashboard payload (JSON over HTTP)

For consumers exposing posture to a web frontend or to remote
monitoring tools. The recommended payload shape is the §4.2 JSON form
plus a small envelope for transport metadata:

```json
{
  "envelope": {
    "consumer":      "abletools",
    "consumer_version": "0.1.0",
    "fetched_at":    "2026-06-12T22:14:03Z"
  },
  "posture": {
    "authority_model": "warrant_scoped",
    "chain_intact":    true,
    "computed_at":     "2026-06-12T22:14:03Z",
    "disjunct_a":      "…",
    "disjunct_b":      "…",
    "disjunct_c":      "…",
    "law_hash":        "546a9e90fd780dec…",
    "matrix_cells":    "[a|b|c]",
    "phi":             0.871,
    "posture_hash":    "3f7c…",
    "receipt_count":   1283,
    "require_gate":    true,
    "require_intent":  true,
    "require_scoped_intent": true,
    "require_warrant": true,
    "session_dkn":     "deploy-prod-2026",
    "_verify_hash":    true
  }
}
```

Note: the `envelope` is consumer-defined; the `posture` subtree is the
canonical surface and SHOULD preserve field names verbatim.

### §4.6 Coverage-aggregation dashboards (multi-posture roll-up)

Dashboards that show posture across multiple deployments, multiple
sessions, or a time series should display:

- One posture summary per row (the §4.4 layout in compact form, or a
  single colored status indicator).
- The `posture_hash` as the row's identity — two rows with the same
  `posture_hash` are identical posture states.
- The `law_hash` highlighted prominently — rows with differing
  `law_hash` values are NOT in the same constitutional regime and
  should be visually grouped or warned about.
- The `chain_intact` and `verify_hash()` indicators as the row's
  health signal.

Aggregation rule: a multi-posture dashboard is HEALTHY iff every row
has `chain_intact == True` AND `verify_hash() == True` AND a uniform
`law_hash` across rows. Any deviation is an integrity finding to
surface to the operator.

## §5. Discipline guidance — what NOT to do

The rendering layer is a thin presentation over the canonical
substrate. The following pitfalls compromise that discipline:

### Don't reach past the public API into private fields

The `GovernancePosture` dataclass is frozen and its fields are
documented. Don't introspect `__dict__`, don't depend on
implementation details of the kernel that `compute()` reads. If a
field you need isn't in §2, propose its addition through the Governor
protocol rather than reading kernel internals directly.

### Don't reimplement `compute()`

There are exactly three entry points (`compute`, `compute_from_store`,
`organs.compute_posture`). Recomputing posture by reading the kernel's
private fields and assembling a dict bypasses the integrity hash and
breaks audit correspondence. Always call a canonical entry point.

### Don't reinterpret field semantics

`chain_intact == False` means the receipt chain failed verification.
The dashboard does not get to re-interpret this as "warning" or
"degraded" or "recoverable" — it is a hard integrity failure and
should be surfaced as such.

Similarly, `authority_model` strings are declarative; if the value is
`"undeclared"`, the dashboard SHOULD display `"undeclared"` rather
than guessing what the authority model is.

### Don't silently treat `verify_hash() == False` as cosmetic

If `verify_hash()` returns `False`, the posture object's content does
not match its declared hash — possible tampering, possible bug.
Surface this prominently. Do not render the rest of the posture as if
it were trustworthy.

A reasonable response to `verify_hash() == False`:

```python
if not posture.verify_hash():
    render_integrity_warning(posture)
    return  # do not show the rest of the posture as authoritative
```

### Don't cache posture across sessions

`posture_hash` is content-addressed for the moment of compute, and
`computed_at` is part of the hashed body — so the hash identifies a
specific snapshot taken at a specific instant. Caching a posture
object beyond its useful lifetime risks displaying stale state under
a hash that no longer represents current state. Recompute on each
rendering refresh; rely on the kernel's state, not on the dashboard's
memory.

The `computed_at` field can be displayed to surface posture age
(e.g., "computed 4 minutes ago"); this is informational and is not
a substitute for recomputing. A live dashboard showing a posture
whose `computed_at` is several minutes old is showing the past.

### Don't rename canonical field names in display

Use the canonical field names from §2 either verbatim or alongside
human-friendly labels (e.g., `"Chain intact (chain_intact)"`). Pure
human-friendly names are an anti-pattern because they break audit
correspondence — a viewer who sees "Receipt chain status: healthy"
cannot cross-reference that to the canonical `chain_intact` field
without searching.

### Don't conflate posture with capability evidence

Posture is a single-instant snapshot of governance state. The CGP-ESA
capability registry, the CTR coverage report, and per-runner sweep
results are SEPARATE evidence streams. A complete dashboard should
display all of them (see §6), but should not blend them into one
score — each answers a different question.

## §6. What evidence the dashboard should ALSO show

A complete CGP-aware dashboard surfaces multiple evidence streams,
not just posture. Recommended companions:

- **Consumer scope summary.** Call
  `ugk.capability_evidence.summarize(claims)` on the consumer's
  parsed `evidence_scope.py`. Display claim counts by status
  (`DONE`, `PARTIAL`, `FUTURE`, `OUT_OF_SCOPE`, `ASPIRATIONAL`,
  `UNDECLARED`). See
  [`CGP_EXECUTION_SUBSTRATE.md §6`](./CGP_EXECUTION_SUBSTRATE.md) for
  the scope-to-evidence pipeline.

- **Registry alignment.** Call
  `ugk.capability_evidence.diff_against_registry(claims,
  ugk.cgp.esa.registry_cap_ids())` (or against
  `ugk.cgp.esa.legacy_map().keys()` if the consumer uses legacy IDs).
  Display `in_both` / `in_scope_not_in_registry` /
  `in_registry_not_in_scope` counts. See
  [`CGP_CAPABILITIES.md §11`](./CGP_CAPABILITIES.md) for the diff
  pattern.

- **Most recent CTR coverage report.** If the consumer runs CTR
  (via `ugk.cgp.ctr.CTR.analyse(...)`), the most recent
  `CoverageReport.coverage_ratio` and `invariants_missing` are
  high-signal dashboard items.

- **Most recent runner sweep.** If the consumer runs HR (via
  `ugk.cgp.runner.HeadlessRunner`), the most recent `SweepResult`'s
  `ok` flag, `receipts_emitted` delta, and `anomaly_score` complete
  the live-evidence picture.

A dashboard that shows only the posture (and not the surrounding
capability and runner evidence) is showing a snapshot in isolation;
the snapshot is meaningful only in the context of what evidence has
been emitted to produce it.

## §7. Reference realizations

Existing consumer realizations of the posture surface, for reference
(NOT canonical — consumers should imitate or diverge freely):

- **Semantic Navigator GUI.** `navigator/gui/dialogs/
  governance_dashboard.py` — Qt widget panel; full posture rendering
  in a tabbed dialog alongside other Navigator-specific governance
  views. Substrate-coupled to NavigatorKernel; not directly portable
  but architecturally instructive.

- **AbleTools CLI.** `abletools/tests/governed_runner.py` produces
  per-invariant CTR verdict tables via `acis test`; posture surfacing
  is handled separately via `Organs.compute_posture()` from inside
  AbleTools-aware tooling. CLI-tabular pattern aligned with §4.1.

- **CPVM tooling.** `cpvm.bridge.AuthoritativeChain.compute_posture()`
  is the Mode 2 entry point. CPVM's `cpvm.conformance` module emits
  gate-pass summaries which complement the posture snapshot. No
  dedicated CPVM dashboard at the time of writing.

If you build a new consumer dashboard worth referencing here, propose
its inclusion through the Governor protocol.

## §8. Substrate stability statement

The UGK constitutional substrate is UNCHANGED by this rendering guide:

- `ugk/invariants.py` **was** byte-identical to the M2.3 canonical at the M2.3 line this surface was authored against; the **current r123 frame** is `law_hash a3992e45...`
  (`law_hash 546a9e90fd780dec…`).
- As of the M2.3 line, the conformance suite was **78 gates** and the M2 vector suite **39 vectors**, and this rendering guide adds none over that baseline. **Current frame (as of release r125): 100 conformance gates, 46 ADRs, `law_hash a3992e45...`.** The `law_hash 546a9e90...` values in the example renders above are illustrative **M2.3-line sample** values, not the current frame. Whether this additivity statement re-validates over the advanced frame is a separate grounding question, not asserted here.
- No new error codes, no new gates, no new vectors, no new code
  modules.
- The `GovernancePosture` field set documented in §2 is the
  authoritative surface for the M2.3 line. Future UGK releases that
  add fields will do so additively; consumer dashboards depending on
  the §2 fields will continue to render correctly.
- The three compute entry points (`compute`, `compute_from_store`,
  `organs.compute_posture`) and the `verify_hash()` contract are
  stable.

Consumer dashboards are SAFE to build against this surface and depend
on it across the M2.3 line.

---

**Document version:** 1.0 (CGP-POSTURE-RENDERING phase)
**Authoritative surfaces:** `ugk.cgp` (entry points),
`ugk.posture.GovernancePosture` (dataclass).
**Future tiny phase (separately authorized):** a small
`ugk.cgp.posture_show` CLI printer for operational convenience.
That phase is explicitly NOT folded into this documentation phase.
