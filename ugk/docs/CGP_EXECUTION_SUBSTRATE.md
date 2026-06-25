# CGP Execution Substrate

**Audience.** Developers building on UGK who want to understand what
CGP capabilities are available, how to run UGK headlessly, and how to
inherit the CGP execution-evidence contract. This document is the
canonical orientation for the CGP execution-substrate layer; a
separate `CGP_CAPABILITIES.md` (future) will catalog the full CGP-ESA
capability registry once it is authored.

**Substrate stability statement.** Everything described below is
*additive* over the UGK M2.3 constitutional substrate. The UGK
substrate (`invariants.py`, `law_hash = 546a9e90fd780dec…`,
the 78-gate suite, the 39-vector suite, the Receipt schema,
`GOVERNANCE_OPS`, the kernel/store discipline) is unchanged. CGP
infrastructure can be ignored entirely by consumers who don't need it,
and adopted incrementally by consumers who do.

> **CGP integration note (corrected; doc-only).** The "additive over the M2.3 substrate / unchanged"
> statement above describes CGP relative to the **M2.3** baseline it was authored against. **CGP as a
> subsystem is constitutionally INTEGRATED into the current r123 frame:** the invariants `CGP-S-01/02/03`,
> `SCOPE-S-01/02`, `ESA-S-01`, `CTR-S-01/07`, `SRSA-S-01` and the CGP-family conformance gates
> (`esa_selfcheck`, `posture`, `provenance_scope`, `scope_archive`, `srsa_vector`, `health_surface`) are
> part of the certified r125 frame (`law_hash a3992e45...`, 100 gates). CGP adds **no UGK-substrate error
> codes and no receipt-schema columns**, but it is **not** "purely additive over an unchanged baseline."

---

## §1. What CGP is

**CGP — Constitutional Governance Platform.** The system-level
capability platform exposed through UGK. CGP is the layer at which
*capabilities* (declared properties of governed systems) are owned,
*realizations* (concrete implementations of capabilities) live in
consumers, and *evidence* (proofs that realizations satisfy
capabilities) flows through the shared UGK receipt substrate.

Three ownership rules govern CGP:

1. **Capability ownership = CGP.** A capability (e.g., "the receipt
   chain is verifiable end-to-end", "every declared op has a
   reachable handler") is owned by the CGP platform regardless of
   which consumer realizes it.
2. **Realization ownership = consumer.** The concrete code that
   makes a capability true for a particular system (e.g., a GUI
   display-fidelity checker, a CLI command reachability auditor,
   a service-API call audit) lives in the consumer that runs it.
3. **Evidence ownership = realization.** Whoever implements the
   realization is responsible for emitting governed evidence — receipts,
   gate outcomes, structured results — through the shared UGK receipt
   substrate.

The CGP execution substrate (this document's subject) provides the
*runtime machinery* through which realizations produce that evidence.

## §2. CGP construct families

CGP organizes governance concerns into construct families. Each family
has its own Domain Codex (the authoritative source); UGK ships either
a runtime module, a re-export surface, or both for each.

| Family | Concerns | Where in UGK | Compat alias | Status |
|---|---|---|---|---|
| **ESA** | Evidence Specification Architecture — capability inventory and self-check | `ugk.core.esa` (kernel-cap evaluator, ~5 caps); future `ugk.cgp.esa` registry | `ugk.core.esa` (impl) | UGK ships kernel subset; full registry deferred |
| **EVS** | Evidence Verification Surface — tests-as-proof, evidence-class stratification, structured error codes | DSS:OS:EVS Domain Codex (external); no dedicated UGK runtime module yet | — | construct doc only |
| **CTR** | Constitutional Test Runner — test-invariant binding, governance coverage reporting, harness independence | `ugk.cgp.ctr` (canonical) | `ugk.ctr` (impl) | substrate-ready; runner-agnostic discipline |
| **SRSA** | Sovereign Reliance Spectrum Architecture — 10-axis governance reliance vector | `ugk.cgp.srsa` (canonical) | `ugk.core.srsa` (impl) | substrate-ready; 10 axes declared with honest-zero entries |
| **AIS** | Admissibility Invariant Surface — choke point structural enforcement | AIS Domain Codex (external); no runtime module yet | — | construct doc only |
| **COP** | Constitutional Observability Platform — receipt observability infrastructure | external; no runtime module yet | — | construct doc only |
| **HeadlessRunner** | Governed scenario execution + checkpoint receipts | `ugk.cgp.runner` (canonical) | `ugk.testing.headless_runner` (impl) | substrate-ready; reference Pattern A impl |

CGP capability registries (full ESA family, etc.) will be authored
in subsequent phases. This document describes the **execution
substrate** — the machinery through which evidence for capabilities
is produced.

## §3. How HeadlessRunner fits

Two complementary patterns of execution evidence are unified by the
CGP runner contract:

### Pattern A — Scenario execution + checkpoint receipts

A scenario is a callable that performs governed operations against a
real kernel. The runner sweeps through scenarios, emits checkpoint
receipts between them, and aggregates outcomes into a structured
result:

- **Input:** scenario functions (or `@gate_test`-tagged functions
  on a module)
- **Process:** real machinery execution (HR-S-01); structured
  result with declared limits (HR-S-02); evidence-picture
  completeness via checkpoint receipts (HR-S-03 + HR-S-05);
  profile-based injection (HR-S-04); governed test discovery
  (HR-S-06)
- **Output:** `ScenarioResult` / `SweepResult`
  (pass/fail/skip/hang/refuse + receipt deltas + anomaly scores +
  checkpoint hashes)
- **Reference implementation:** `ugk.cgp.runner.HeadlessRunner`
  (the `ugk.testing.headless_runner.HeadlessRunner` class,
  re-exported under the canonical CGP path). 16-method canonical
  surface per HR Domain Codex v0.5. Substrate-clean — no GUI
  dependency. Adapted from build4 lineage for the UGK kernel.

### Pattern B — Coverage-map dispatched instruments

A coverage map (projected from a consumer's codex) declares which
invariants are bound to which instruments. The runner reads the
map, executes each instrument as a subprocess, collects per-invariant
verdicts:

- **Input:** selector ("core" / "live" / "full") + coverage map
- **Process:** per-invariant instrument execution; structured
  verdict per binding
- **Output:** per-invariant verdict table (tuple of
  `EvidenceArtifact`)
- **Reference implementation:** AbleTools `governed_runner.py`
  (external to UGK; structurally conformant via the CGPRunner
  Protocol)

### The unifying contract: CGPRunner

`ugk.cgp.runner.CGPRunner` is a `runtime_checkable` Protocol whose
**required** surface is the Pattern-A trio only: `run_scenario` /
`run_gate_tests` / `assert_clean`. The Pattern-B coverage methods
(`dispatch_coverage` / `coverage_report`) are **not** part of the
Protocol; they are an additional Pattern-B surface. A Pattern-B or
hybrid runner therefore satisfies `CGPRunner` only if it also implements
that Pattern-A trio; `isinstance(my_runner, CGPRunner)` checks the trio,
not the coverage methods.

Pattern A is the *preferred* CGP evidence runner pattern; the
existing `HeadlessRunner` is the reference implementation. New
consumers should reach for it unless they have an established Pattern
B (or other shape) that better fits their architecture. CTR coverage
analysis (§6) operates over both pattern outputs.

## §4. How to run UGK headlessly

The minimum example: ceremony a kernel, open a session, run a scenario:

```python
from ugk.kernel import GovernanceKernel
from ugk.cgp.runner import HeadlessRunner

# 1. Stand up a kernel
kernel = GovernanceKernel()
kernel._ceremony()           # found the deployment (one-time per process)
kernel.open_session()

# 2. Wrap it with a runner
runner = HeadlessRunner(kernel)

# 3. Define a scenario
def my_scenario(kernel):
    # the scenario callback receives the GovernanceKernel directly
    # (run_scenario calls scenario_fn(kernel))
    kernel.execute(
        op="some_governed_op",
        authority="USER",
        intent="example.run",
        jurisdiction="cgp-doc-example",
    )

# 4. Execute and inspect
result = runner.run_scenario(my_scenario, scenario_name="example")
print(result.outcome)               # "pass" / "fail" / "skip" / "hang" / "refuse"
print(result.receipts_emitted)      # tuple of Receipt instances
print(result.anomaly_score)         # 0.0 = clean

# 5. Assert across a sweep
sweep = runner.run_gate_tests(my_test_module)
runner.assert_clean(sweep)          # raises if any anomaly
```

For sweep semantics:

```python
# Structural sweep — checks structural invariants over the kernel
sweep = runner.structural_sweep(target=kernel)
runner.assert_clean(sweep)

# Cap-52 sweep — op-pair latency anomaly detection
sweep = runner.cap52_sweep(target=kernel)
# Anomaly is reported via sweep.anomaly_score; not a fail by default

# Epistemic sweep — evidence-picture completeness audit
sweep = runner.epistemic_sweep(target=kernel)
```

Per HR-S-01: every scenario writes receipts to the actual UGK store.
No simulation. No mock receipts. The receipt chain after a sweep is
the audit trail.

## §5. How downstream apps inherit the CGP runner contract

Two adoption paths are supported and both are valid:

### Path (a) — Direct inheritance of `HeadlessRunner`

A consumer that wants Pattern A execution evidence with the
reference implementation simply imports it:

```python
from ugk.cgp.runner import HeadlessRunner

class MyConsumerRunner(HeadlessRunner):
    def my_consumer_sweep(self, target):
        # add consumer-specific sweep methods
        return self.run_gate_tests(target)
```

The full 16-method HR-S surface is inherited unchanged. The
consumer's runner is automatically CGPRunner-conformant.

### Path (b) — Protocol satisfaction (different shape)

A consumer with an established execution shape (e.g., a
coverage-map dispatcher) implements the CGPRunner Protocol
structurally:

```python
from ugk.cgp.runner import CGPRunner, ScenarioResult, SweepResult

class MyDispatchRunner:
    """Pattern B: coverage-map dispatcher."""

    def run_scenario(self, scenario_fn, *args, **kwargs) -> ScenarioResult:
        # consumer-specific scenario execution
        ...

    def run_gate_tests(self, module) -> SweepResult:
        ...

    def assert_clean(self, result, allow_anomaly=False):
        ...

# Runtime conformance check
my_runner = MyDispatchRunner()
assert isinstance(my_runner, CGPRunner)
```

Either path produces `ScenarioResult` / `SweepResult` instances that
flow into the shared CTR coverage analysis (§6) and the receipt
substrate (the UGK store).

### Consumer adoption status (current snapshot)

- **AbleTools** uses Path (b): `abletools/tests/governed_runner.py`
  implements a coverage-map-dispatched Pattern B runner. It satisfies
  CGPRunner structurally and emits per-invariant verdicts.
- **CPVM** does not currently expose its own runner. The CPVM
  AuthoritativeChain provides posture evidence
  (`chain.compute_posture()`); test execution is via `cpvm.conformance`.
- **Semantic Navigator** has its own HeadlessRunner (v0.7, more
  features than the UGK v0.5 reference but the same canonical
  surface). It is Path (a)–adjacent: forked rather than directly
  inherited, but structurally Pattern A.

## §6. How capability evidence maps connect to the runner

`ugk.capability_evidence` is the registry-agnostic helper that lets
each consumer declare which capabilities apply, bind each one to a
named gate, and verify the bindings resolve. The CGP execution
substrate provides the *runtime machinery* through which those gates
execute and emit their evidence.

The flow:

```
   consumer-side
   ─────────────
   evidence_scope.py             ←── consumer declares scope
       │   SCOPE: dict[cap_id, {name, status, gate, deterministic,...}]
       │
       ▼
   ugk.capability_evidence
   .load_scope(module)           ←── helper parses SCOPE
       │   tuple[CapabilityClaim, ...]
       │
       ▼
   ugk.capability_evidence
   .verify_evidence_map(claims,  ←── helper asserts every DONE/PARTIAL
                       gates_dir)     claim has its named gate file
       │   (bool, str)
       │
       ▼
   the named gate                ←── conformance/<gate>.py executes …
       │
       ▼
   ugk.cgp.runner                ←── … which is, in turn, a sweep run
   (HeadlessRunner or other)         through the CGPRunner contract
       │
       ▼
   ScenarioResult / SweepResult  ←── governed evidence emitted to
                                     UGK receipt store
       │
       ▼
   ugk.cgp.ctr.CTR.analyse(
       test_fns, evidence_source ←── CTR analyzes the evidence picture
       ="governed_receipt_chain")
       │
       ▼
   CoverageReport                ←── per-invariant coverage + gaps
                                     (CTR-S-02 reporting)
```

Each layer of the pipeline is independently swappable:

- Different consumers declare different `SCOPE` dicts.
- Different gates implement different evidence checks.
- Different runners (HeadlessRunner, AbleTools governed_runner, future
  consumers) satisfy the CGPRunner Protocol independently.
- Different `evidence_source` strings let CTR distinguish coverage
  computed from different runner outputs (`"governed_receipt_chain"`,
  `"pytest_plugin"`, `"coverage_map_dispatch"`, …).

The receipt substrate (the UGK store) is the shared persistence layer
across all of this. Receipts written by one runner are readable and
verifiable by any CGP consumer with access to that store.

## §7. Canonical APIs

The Tier 2 path table (canonical CGP-facing surfaces):

| Canonical path | What it does | Implementation alias |
|---|---|---|
| `ugk.cgp.compute(kernel)` | Mode 1 posture compute (CGP-ADAPTER) | `ugk.cgp.posture.compute` |
| `ugk.cgp.compute_from_store(store, …)` | Mode 2 posture compute (store-only consumers) | `ugk.cgp.posture.compute_from_store` |
| `ugk.cgp.required_attributes()` | Kernel-shape introspection for posture compute | `ugk.cgp.posture.required_attributes` |
| `ugk.cgp.runner.HeadlessRunner` | Reference Pattern A runner | `ugk.testing.headless_runner.HeadlessRunner` |
| `ugk.cgp.runner.CGPRunner` | Runtime-checkable runner contract | (Protocol declaration; no alias) |
| `ugk.cgp.runner.ScenarioInput` / `EvidenceArtifact` / `InterpretiveEvidencePack` | Canonical input/output types | (new declarations; no alias) |
| `ugk.cgp.runner.ScenarioResult` / `BatchResult` / `SweepResult` / `ConvergenceFingerprint` | Result types | `ugk.testing.headless_runner.*` |
| `ugk.cgp.ctr.gate_test` | Decorator binding a test to an invariant (CTR-S-01) | `ugk.ctr.gate_test` |
| `ugk.cgp.ctr.CTR` | Coverage analyzer (CTR-S-02) | `ugk.ctr.CTR` |
| `ugk.cgp.ctr.CoverageReport` | Structured coverage result (CTR-T-13) | `ugk.ctr.CoverageReport` |
| `ugk.cgp.srsa.srsa_vector(kernel)` | 10-axis SRSA reliance vector | `ugk.core.srsa.srsa_vector` |
| `ugk.capability_evidence` | Registry-agnostic scope/evidence helper | (no canonical CGP alias — already canonical at this path) |

## §8. Compatibility aliases

All implementation paths below remain VALID FOREVER. They are not
deprecated; they emit no warnings; consumers may use them
indefinitely. The Tier 2 canonical paths above are offered for
discoverability and forward consistency, not as a forced migration.

| Compatibility alias | Resolves to | Why preserved |
|---|---|---|
| `ugk.testing.headless_runner` | The HR implementation module | Referenced by other UGK modules; widely-used existing path |
| `ugk.testing` | Re-export of HR symbols | Existing package convention |
| `ugk.ctr` | The CTR implementation module | Referenced by HR and liveness_gate; widely-used |
| `ugk.core.srsa` | The SRSA implementation module | Referenced by liveness_gate |
| `ugk.core.esa` | The kernel-native ESA evaluator | Distinct from the future `ugk.cgp.esa` registry; both will coexist |

The CGP-ESA capability registry (`ugk.cgp.esa`) is a separate future
phase. When it lands, `ugk.core.esa` (the kernel-cap evaluator) will
remain unchanged; the registry will describe the full CGP-ESA family
of which kernel caps are one realization.

## §9. Cross-references

- **`ugk.capability_evidence`** — registry-agnostic helper for
  consumer scope/evidence-map verification. Already canonical
  at this import path (no Tier 2 promotion needed).
- **`ugk.cgp.compute` / `ugk.cgp.compute_from_store`** — the CGP
  posture adapter (Mode 1 / Mode 2 entry points). See the
  CGP-ADAPTER design documents for full background.
- **CPVM bridge** — `cpvm.bridge.AuthoritativeChain.compute_posture()`
  provides the Mode 2 entry point for store-only CPVM consumers
  via the canonical `ugk.cgp.compute_from_store`.
- **AbleTools facade** —
  `abletools.governance.abletools_organs.Organs.compute_posture()`
  provides the Mode 3 entry point for vendored-kernel consumers.

## §10. Substrate stability statement

The UGK constitutional substrate is UNCHANGED by any of the CGP
execution-substrate work described in this document:

- `ugk/invariants.py` **was** byte-identical to the M2.3 canonical at the M2.3 line this work was authored against; the **current r123 frame** is `law_hash a3992e45...`
  (`law_hash 546a9e90fd780dec…`).
- As of the M2.3 line, the conformance suite was **78 gates** and the M2 vector suite **39 vectors**, and the execution substrate adds none over that baseline. **Current frame (as of release r125): 100 conformance gates, 46 ADRs, `law_hash a3992e45...`.** Whether this additivity statement re-validates over the advanced frame is a separate grounding question, not asserted here.
- No new error codes are declared.
- No new constitutional declarations exist.
- No new charter / authority-model / will-store / intent-vocabulary
  changes.
- The Receipt schema, `GOVERNANCE_OPS`, `REAL_OPS`, `PHANTOM_OPS`
  are unchanged.

CGP infrastructure is purely additive. Consumers who do not adopt
the Tier 2 canonical paths continue to work identically against the
existing Tier 1 paths. Consumers who adopt Tier 2 paths gain
discoverability and forward consistency without sacrificing
compatibility.

---

**Document version:** 1.0 (CGP-SUBSTRATE implementation phase)
**Authoritative source for canonical APIs:** the module docstrings of
the `ugk.cgp.*` packages themselves.
**For corrections or updates:** the substrate doc evolves with the
ugk.cgp.* surface. Implementation paths (Tier 1) and the
constitutional substrate are stable across substrate-doc revisions.
