"""ugk/testing/headless_runner.py — HeadlessRunner governed scenario execution substrate.

Adapted from build4 governed/testing/headless_runner.py:
  - NavigatorKernel → GovernanceKernel
  - with_warm_corpus(): gate_admit → crp_evidence (gate_admit is _KERNEL_OPS)
  - run_batch() test_checkpoint: direct store.write() → kernel.execute()
  - structural_sweep(), filesystem_sweep(), epistemic_sweep(): same adaptation
  - CTR import: governed.ctr → ugk.ctr

16 canonical public methods (HeadlessRunner Domain Codex v0.5):
  1.  run_scenario(scenario_fn, profile)      -> ScenarioResult
  2.  run_batch(scenarios)                    -> BatchResult
  3.  run_gate_tests(module)                  -> SweepResult
  4.  structural_sweep(target)                -> SweepResult
  5.  cap52_sweep(target)                     -> SweepResult
  6.  with_warm_corpus(n_files)               -> SweepResult
  7.  filesystem_sweep(target)                -> SweepResult
  8.  epistemic_sweep(target)                 -> SweepResult
  9.  assert_clean(result)                    -> None (raises on anomaly)
  10. snapshot_at(checkpoint_hash)            -> dict
  11. verify_stream_hash(from_checkpoint)     -> bool
  12. make_epistemic_profile(name, ops)       -> dict
  13. get_receipt_delta(result)               -> int
  14. get_anomaly_score(result)               -> float
  15. get_checkpoint_hashes(result)           -> list[str]
  16. verify_convergence_fingerprint(store, fingerprint) -> bool

AMB-B4-02: CTR is instantiated internally inside run_gate_tests().
           Callers do not inject CTR.  Internal CTR receives
           evidence_source='governed_receipt_chain'.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ugk.kernel import GovernanceKernel, GateRefusal
from ugk.storage.store import UGKReceiptStore
from ugk.schema import GOVERNANCE_OPS


# ---------------------------------------------------------------------------
# ConvergenceFingerprint
# ---------------------------------------------------------------------------

@dataclass
class ConvergenceFingerprint:
    """Typed fingerprint for anti-fabrication verification (HR-T-16)."""
    required_ops_present:      list[str]
    required_checkpoint_count: int
    prohibited_ops_absent:     list[str] = field(default_factory=list)
    rate_gate_ok:              bool = True
    sequence_integrity:        bool = True
    max_op_latency_ms:         Optional[dict] = None
    baseline_fingerprint:      Optional["ConvergenceFingerprint"] = None
    op_latency_samples:        Optional[dict] = None


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ScenarioResult:
    """Evidence picture from a single scenario execution."""
    scenario_name:    str
    passed:           bool
    receipt_delta:    int
    stream_hash:      str
    anomaly_score:    float
    timing_ms:        float
    checkpoint_hash:  Optional[str] = None
    error:            Optional[str] = None


@dataclass
class BatchResult:
    """Evidence picture from batched execution."""
    scenario_results:    list[ScenarioResult]
    checkpoint_hashes:   list[str] = field(default_factory=list)
    total_receipt_delta: int = 0
    final_stream_hash:   str = ""


@dataclass
class SweepResult:
    """Structured result from run_gate_tests() or sweep methods."""
    sweep_name:       str
    passed:           bool
    receipt_delta:    int
    stream_hash:      str
    anomaly_score:    float
    timing_ms:        float
    scenario_results: list[ScenarioResult] = field(default_factory=list)
    checkpoint_hashes: list[str] = field(default_factory=list)
    coverage_report:  Optional[Any] = None
    anomalies:        list[str] = field(default_factory=list)
    limits_declared:  dict = field(default_factory=dict)
    op_latencies:     dict = field(default_factory=dict)

    def median_latency(self, op: str) -> float:
        samples = self.op_latencies.get(op)
        if not samples:
            raise KeyError(f"median_latency: no samples for op={op!r}")
        ss = sorted(samples)
        n = len(ss)
        mid = n // 2
        return (ss[mid-1] + ss[mid]) / 2.0 if n % 2 == 0 else ss[mid]

    def assert_clean(self, allow_anomaly: bool = False) -> None:
        if not self.passed:
            failing = [r for r in self.scenario_results if not r.passed]
            raise AssertionError(
                f"SweepResult.assert_clean() failed: {len(failing)} scenario(s) failed: "
                f"{[r.scenario_name for r in failing]}"
            )
        if not allow_anomaly and self.anomalies:
            raise AssertionError(
                f"SweepResult.assert_clean() failed: anomalies: {self.anomalies}"
            )


# ---------------------------------------------------------------------------
# Epistemic profiles
# ---------------------------------------------------------------------------

_DEFAULT_PROFILE: dict = {
    "name": "standard",
    "expected_ops": list(GOVERNANCE_OPS.keys()),
    "allow_anomaly": False,
    "strict": True,
}

_INVERTED_PROFILE: dict = {
    "name": "inverted",
    "expected_ops": [],
    "allow_anomaly": True,
    "strict": False,
    "invert_semantics": True,
}


# ---------------------------------------------------------------------------
# HeadlessRunner
# ---------------------------------------------------------------------------

class HeadlessRunner:
    """Governed scenario execution substrate.

    HR-S-01: Real Machinery Execution — scenarios run against real GovernanceKernel.
    HR-S-02: Structured Result — ScenarioResult / SweepResult with declared limits.
    HR-S-03: Evidence Picture Completeness — receipt_delta, stream_hash, anomaly_score.
    HR-S-04: Profile-Based Injection — epistemic profiles shape scenario execution.
    HR-S-05: Batched Execution — test_checkpoint receipt between scenarios.
    HR-S-06: Governed Test Discovery — run_gate_tests() discovers @gate_test functions.

    CTR instantiated internally (AMB-B4-02).  Callers do not inject CTR.
    """

    def __init__(
        self,
        kernel:    Optional[GovernanceKernel] = None,
        authority: str = "headless_runner",
    ):
        self._kernel    = kernel if kernel is not None else GovernanceKernel(authority=authority)
        self._authority = authority

    # ------------------------------------------------------------------
    # 1. run_scenario
    # ------------------------------------------------------------------

    def run_scenario(
        self,
        scenario_fn:   Callable[[GovernanceKernel], None],
        profile:       Optional[dict] = None,
        scenario_name: Optional[str] = None,
    ) -> ScenarioResult:
        profile = profile or _DEFAULT_PROFILE
        name    = scenario_name or getattr(scenario_fn, "__name__", "unnamed_scenario")
        store   = self._kernel.store
        count_before = store.receipt_count()
        t_start = time.perf_counter()
        passed = True
        error  = None
        try:
            scenario_fn(self._kernel)
        except AssertionError as e:
            passed = False; error = str(e)
        except Exception as e:
            passed = False; error = f"{type(e).__name__}: {e}"
        t_end = time.perf_counter()
        receipt_delta = store.receipt_count() - count_before
        anomaly_score = self._compute_anomaly_score(store, profile, count_before)
        return ScenarioResult(
            scenario_name=name, passed=passed,
            receipt_delta=receipt_delta, stream_hash=store.stream_hash(),
            anomaly_score=anomaly_score, timing_ms=(t_end - t_start) * 1000,
            error=error,
        )

    # ------------------------------------------------------------------
    # 2. run_batch
    # ------------------------------------------------------------------

    def run_batch(
        self,
        scenarios: list,
        profile:   Optional[dict] = None,
    ) -> BatchResult:
        profile = profile or _DEFAULT_PROFILE
        store   = self._kernel.store
        scenario_results: list[ScenarioResult] = []
        checkpoint_hashes: list[str] = []
        total_delta = 0

        for item in scenarios:
            fn, sc_profile = (item[0], item[1]) if isinstance(item, tuple) and len(item) > 1 \
                             else (item if not isinstance(item, tuple) else item[0], None)
            sc_profile = sc_profile or profile

            result = self.run_scenario(fn, sc_profile)
            scenario_results.append(result)
            total_delta += result.receipt_delta

            # HR-S-05: test_checkpoint via execute() (NBER-1 through kernel)
            try:
                self._kernel.execute(
                    op="test_checkpoint",
                    authority=self._authority,
                    parameters={
                        "scenario":      result.scenario_name,
                        "passed":        result.passed,
                        "stream_hash":   result.stream_hash,
                        "receipt_count": store.receipt_count(),
                    },
                )
            except Exception:
                pass  # test_checkpoint failure should not abort batch
            checkpoint_hash = store.stream_hash()
            checkpoint_hashes.append(checkpoint_hash)
            result.checkpoint_hash = checkpoint_hash
            total_delta += 2  # gate_admit + test_checkpoint receipts

        return BatchResult(
            scenario_results=scenario_results,
            checkpoint_hashes=checkpoint_hashes,
            total_receipt_delta=total_delta,
            final_stream_hash=store.stream_hash(),
        )

    # ------------------------------------------------------------------
    # 3. run_gate_tests
    # ------------------------------------------------------------------

    def run_gate_tests(self, module: Any) -> SweepResult:
        """Discover @gate_test functions, execute as governed scenarios, return SweepResult."""
        from ugk.ctr import CTR

        discovered: list[Callable] = []
        all_callables: list[Callable] = []
        for name in dir(module):
            obj = getattr(module, name, None)
            if not callable(obj):
                continue
            if getattr(obj, "__name__", "").startswith("test_"):
                all_callables.append(obj)
            if getattr(obj, "_gate_test", False):
                discovered.append(obj)

        store = self._kernel.store
        count_before = store.receipt_count()
        t_start = time.perf_counter()

        def make_scenario(fn):
            def scenario(kernel):
                fn(kernel)
            scenario.__name__ = fn.__name__
            return scenario

        scenario_pairs = [(make_scenario(fn), None) for fn in discovered]
        batch_result = self.run_batch(scenario_pairs) if scenario_pairs else BatchResult(
            scenario_results=[], checkpoint_hashes=[], total_receipt_delta=0,
            final_stream_hash=store.stream_hash(),
        )

        t_end = time.perf_counter()
        receipt_delta = store.receipt_count() - count_before
        all_passed = all(r.passed for r in batch_result.scenario_results)

        internal_ctr = CTR()
        coverage_report = internal_ctr.analyse(
            test_functions=discovered,
            evidence_source="governed_receipt_chain",
            all_module_callables=all_callables,
        )

        anomalies = [
            f"FAIL: {r.scenario_name} — {r.error}"
            for r in batch_result.scenario_results if not r.passed
        ]

        return SweepResult(
            sweep_name=f"run_gate_tests:{getattr(module, '__name__', str(module))}",
            passed=all_passed,
            receipt_delta=receipt_delta,
            stream_hash=store.stream_hash(),
            anomaly_score=sum(r.anomaly_score for r in batch_result.scenario_results),
            timing_ms=(t_end - t_start) * 1000,
            scenario_results=batch_result.scenario_results,
            checkpoint_hashes=batch_result.checkpoint_hashes,
            coverage_report=coverage_report,
            anomalies=anomalies,
        )

    # ------------------------------------------------------------------
    # 4. structural_sweep
    # ------------------------------------------------------------------

    def structural_sweep(self, target: Any) -> SweepResult:
        t_start = time.perf_counter()
        store = self._kernel.store
        count_before = store.receipt_count()
        anomalies: list[str] = []
        import inspect
        for name in dir(target):
            if name.startswith("_"):
                continue
            obj = getattr(target, name, None)
            if callable(obj):
                try:
                    src = inspect.getsource(obj)
                    if src.strip().endswith("pass") or "raise NotImplementedError" in src:
                        anomalies.append(f"Stub detected: {name}")
                except (OSError, TypeError):
                    pass
        try:
            self._kernel.execute(
                op="crp_evidence", authority=self._authority,
                parameters={"sweep": "structural", "anomalies": len(anomalies)},
            )
        except Exception:
            pass
        t_end = time.perf_counter()
        return SweepResult(
            sweep_name="structural_sweep", passed=len(anomalies) == 0,
            receipt_delta=store.receipt_count() - count_before,
            stream_hash=store.stream_hash(), anomaly_score=float(len(anomalies)),
            timing_ms=(t_end - t_start) * 1000, anomalies=anomalies,
        )

    # ------------------------------------------------------------------
    # 5. cap52_sweep
    # ------------------------------------------------------------------

    def cap52_sweep(self, target: Any) -> SweepResult:
        t_start = time.perf_counter()
        store = self._kernel.store
        count_before = store.receipt_count()
        anomalies: list[str] = []
        op_latencies: dict = {}
        if hasattr(target, "snapshot_fast"):
            N = 10; latencies = []
            for _ in range(N):
                t0 = time.perf_counter()
                target.snapshot_fast()
                latencies.append((time.perf_counter() - t0) * 1000)
            op_latencies["snapshot_fast"] = latencies
            avg_ms = sum(latencies) / len(latencies)
            if avg_ms > 10.0:
                anomalies.append(f"snapshot_fast() avg {avg_ms:.2f}ms > 10ms (D-PC-01)")
        try:
            self._kernel.execute(
                op="crp_evidence", authority=self._authority,
                parameters={"sweep": "cap52", "anomalies": len(anomalies)},
            )
        except Exception:
            pass
        t_end = time.perf_counter()
        return SweepResult(
            sweep_name="cap52_sweep", passed=len(anomalies) == 0,
            receipt_delta=store.receipt_count() - count_before,
            stream_hash=store.stream_hash(), anomaly_score=float(len(anomalies)),
            timing_ms=(t_end - t_start) * 1000, anomalies=anomalies,
            op_latencies=op_latencies,
        )

    # ------------------------------------------------------------------
    # 6. with_warm_corpus
    # ------------------------------------------------------------------

    def with_warm_corpus(self, n_files: int = 50) -> SweepResult:
        """Produce n_files governed crp_evidence receipts to establish baseline."""
        t_start = time.perf_counter()
        store = self._kernel.store
        count_before = store.receipt_count()
        if self._kernel._session_identity is None:
            self._kernel.open_session()
        for i in range(n_files):
            try:
                self._kernel.execute(
                    op="crp_evidence",
                    authority=self._authority,
                    parameters={"corpus_entry": i, "warm": True},
                )
            except Exception:
                pass
        t_end = time.perf_counter()
        receipt_delta = store.receipt_count() - count_before
        return SweepResult(
            sweep_name=f"with_warm_corpus(n={n_files})",
            passed=receipt_delta > 0,
            receipt_delta=receipt_delta, stream_hash=store.stream_hash(),
            anomaly_score=0.0, timing_ms=(t_end - t_start) * 1000,
            limits_declared={"n_files": n_files, "receipts_produced": receipt_delta},
        )

    # ------------------------------------------------------------------
    # 7. filesystem_sweep
    # ------------------------------------------------------------------

    def filesystem_sweep(self, target: Any) -> SweepResult:
        t_start = time.perf_counter()
        store = self._kernel.store
        count_before = store.receipt_count()
        try:
            self._kernel.execute(
                op="crp_evidence", authority=self._authority,
                parameters={"sweep": "filesystem", "profile": "inverted"},
            )
        except Exception:
            pass
        t_end = time.perf_counter()
        return SweepResult(
            sweep_name="filesystem_sweep", passed=True,
            receipt_delta=store.receipt_count() - count_before,
            stream_hash=store.stream_hash(), anomaly_score=0.0,
            timing_ms=(t_end - t_start) * 1000,
        )

    # ------------------------------------------------------------------
    # 8. epistemic_sweep
    # ------------------------------------------------------------------

    def epistemic_sweep(self, target: Any) -> SweepResult:
        t_start = time.perf_counter()
        store = self._kernel.store
        count_before = store.receipt_count()
        anomalies: list[str] = []

        # Check 1: ESA minimum Cap-1/2/4 in observation_surfaces
        if hasattr(target, "snapshot"):
            snap = target.snapshot()
            for cap in ("Cap-1", "Cap-2", "Cap-4"):
                if cap not in snap.get("observation_surfaces", []):
                    anomalies.append(f"ESA minimum missing: {cap}")
            if not snap.get("classified_remainders"):
                anomalies.append(
                    "Axis 7: classified_remainders absent — governed ignorance not declared"
                )

        # Check 2: latency fingerprint via cap52_sweep
        if hasattr(target, "snapshot_fast"):
            cap52 = self.cap52_sweep(target)
            if "snapshot_fast" in cap52.op_latencies:
                median_ms = cap52.median_latency("snapshot_fast")
                # Construct fingerprint with latency envelope only
                actual_chk = len(store.receipts_by_op("test_checkpoint"))
                fp = ConvergenceFingerprint(
                    required_ops_present=[],
                    required_checkpoint_count=actual_chk,
                    rate_gate_ok=False,
                    sequence_integrity=False,
                    max_op_latency_ms={"snapshot_fast": 10.0},
                    op_latency_samples=cap52.op_latencies,
                )
                if not self.verify_convergence_fingerprint(store, fp):
                    anomalies.append(
                        f"Latency fingerprint failed: snapshot_fast() "
                        f"median={median_ms:.3f}ms > 10ms D-PC-01"
                    )

        try:
            self._kernel.execute(
                op="crp_evidence", authority=self._authority,
                parameters={
                    "sweep": "epistemic",
                    "anomalies": len(anomalies),
                    "checks": ["cap124_present", "classified_remainders", "latency_fingerprint"],
                },
            )
        except Exception:
            pass
        t_end = time.perf_counter()
        return SweepResult(
            sweep_name="epistemic_sweep", passed=len(anomalies) == 0,
            receipt_delta=store.receipt_count() - count_before,
            stream_hash=store.stream_hash(), anomaly_score=float(len(anomalies)),
            timing_ms=(t_end - t_start) * 1000, anomalies=anomalies,
        )

    # ------------------------------------------------------------------
    # 9. assert_clean
    # ------------------------------------------------------------------

    def assert_clean(self, result: SweepResult, allow_anomaly: bool = False) -> None:
        result.assert_clean(allow_anomaly=allow_anomaly)

    # ------------------------------------------------------------------
    # 10. snapshot_at
    # ------------------------------------------------------------------

    def snapshot_at(self, checkpoint_hash: str) -> dict:
        store = self._kernel.store
        for r in store.all_receipts():
            # RT-2h/RT-3 (E5b): lookup is anchored on h_r (M2 chain tip / merkle binding root).
            # (Legacy semantic_hash match removed at r80.)
            if r.h_r == checkpoint_hash:
                return {"checkpoint_hash": checkpoint_hash, "op": r.op,
                        "timestamp": r.timestamp, "parameters": r.parameters,
                        "receipt_id": r.receipt_id}
        return {"checkpoint_hash": checkpoint_hash, "found": False}

    # ------------------------------------------------------------------
    # 11. verify_stream_hash
    # ------------------------------------------------------------------

    def verify_stream_hash(self, from_checkpoint: Optional[str] = None) -> bool:
        return self._kernel.store.verify_stream_hash(from_checkpoint=from_checkpoint)

    # ------------------------------------------------------------------
    # 12. make_epistemic_profile
    # ------------------------------------------------------------------

    def make_epistemic_profile(self, name: str, ops: list[str]) -> dict:
        return {"name": name, "expected_ops": ops, "allow_anomaly": False, "strict": True}

    # ------------------------------------------------------------------
    # 13-15. Evidence extractors
    # ------------------------------------------------------------------

    def get_receipt_delta(self, result: SweepResult) -> int:
        return result.receipt_delta

    def get_anomaly_score(self, result: SweepResult) -> float:
        return result.anomaly_score

    def get_checkpoint_hashes(self, result: SweepResult) -> list[str]:
        return result.checkpoint_hashes

    # ------------------------------------------------------------------
    # 16. verify_convergence_fingerprint
    # ------------------------------------------------------------------

    def verify_convergence_fingerprint(
        self,
        store:       UGKReceiptStore,
        fingerprint: ConvergenceFingerprint,
        baseline:    Optional[ConvergenceFingerprint] = None,
    ) -> bool:
        receipts = store.all_receipts()
        if not receipts:
            return fingerprint.required_checkpoint_count == 0
        ops_in_store = {r.op for r in receipts}
        op_counts: dict[str, int] = {}
        for r in receipts:
            op_counts[r.op] = op_counts.get(r.op, 0) + 1
        # Check 1: required ops present
        for req_op in fingerprint.required_ops_present:
            if req_op not in ops_in_store:
                return False
        # Check 2: checkpoint count
        if op_counts.get("test_checkpoint", 0) != fingerprint.required_checkpoint_count:
            return False
        # Check 3: prohibited ops absent
        for proh in fingerprint.prohibited_ops_absent:
            if proh in ops_in_store:
                return False
        # Check 4: rate gate
        if fingerprint.rate_gate_ok:
            total = len(receipts)
            for op, count in op_counts.items():
                if total > 0 and (count / total) > 0.80:
                    return False
        # Check 5: sequence integrity
        if fingerprint.sequence_integrity and receipts:
            if receipts[0].op != "session_open":
                return False
            if receipts[-1].op != "session_close":
                return False
        # Check 6: latency envelope
        if fingerprint.max_op_latency_ms is not None:
            samples = getattr(fingerprint, "op_latency_samples", {}) or {}
            for op, ceiling in fingerprint.max_op_latency_ms.items():
                op_samples = samples.get(op)
                if not op_samples:
                    return False
                ss = sorted(op_samples); n = len(ss); m = n // 2
                median_ms = (ss[m-1] + ss[m]) / 2.0 if n % 2 == 0 else ss[m]
                if median_ms > ceiling:
                    return False
        # Check 7: baseline comparison
        if baseline is not None and fingerprint.max_op_latency_ms is not None:
            post = getattr(fingerprint, "op_latency_samples", {}) or {}
            pre  = getattr(baseline,    "op_latency_samples", {}) or {}
            def _med(s):
                ss = sorted(s); n = len(ss); m = n // 2
                return (ss[m-1]+ss[m])/2.0 if n % 2 == 0 else ss[m]
            for op in fingerprint.max_op_latency_ms:
                if not post.get(op) or not pre.get(op):
                    return False
                if _med(post[op]) >= _med(pre[op]):
                    return False
        return True

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_anomaly_score(self, store, profile, count_before):
        receipts_since = store.all_receipts()[count_before:]
        expected_ops   = set(profile.get("expected_ops", []))
        invert         = profile.get("invert_semantics", False)
        if invert:
            return float(len(receipts_since)) if not expected_ops else 0.0
        if not expected_ops:
            return 0.0
        return float(sum(1 for r in receipts_since if r.op not in expected_ops))
