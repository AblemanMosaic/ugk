"""ugk/core/esa.py — Kernel-native ESA self-check capabilities.

~5 governance-generic capabilities that any UGK instance can evaluate about
itself, regardless of application domain.  These are the minimum self-check
capabilities — not the full 90-cap AbleTools registry.

ESA_KERNEL_CAPS: the kernel-native capability descriptors.
run_selfcheck(kernel): assess all kernel caps, return ESAKernelReport.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ugk.kernel import GovernanceKernel


@dataclass(frozen=True)
class KernelCap:
    """Kernel-native ESA capability descriptor."""
    cap_id:              str
    name:                str
    description:         str
    super_family:        str  # realization | reconstruction | ...
    evidence_method:     str  # method name or check description


ESA_KERNEL_CAPS: dict[str, KernelCap] = {
    "KCap-1": KernelCap(
        cap_id="KCap-1",
        name="Governance Status Observability",
        description=(
            "kernel.status is observable and returns UNINITIALIZED or ACTIVE.  "
            "Callers can always determine the constitutional status."
        ),
        super_family="realization",
        evidence_method="kernel.status in (UNINITIALIZED, ACTIVE)",
    ),
    "KCap-2": KernelCap(
        cap_id="KCap-2",
        name="Grundnorm Integrity",
        description=(
            "Grundnorm files (444) are read-only after installation.  "
            "The constitutional layer cannot be silently modified."
        ),
        super_family="realization",
        evidence_method="grundnorm_readonly_gate",
    ),
    "KCap-3": KernelCap(
        cap_id="KCap-3",
        name="Receipt Chain Integrity",
        description=(
            "verify_stream_hash() recomputes the full receipt chain and "
            "returns True iff every hash matches and the chain is unbroken."
        ),
        super_family="realization",
        evidence_method="kernel.store.verify_stream_hash()",
    ),
    "KCap-4": KernelCap(
        cap_id="KCap-4",
        name="Classified Remainders Declared",
        description=(
            "CLASSIFIED_REMAINDERS (CR-01..04) are surfaced in snapshot() and "
            "snapshot_fast().  Governed ignorance is declared, not hidden."
        ),
        super_family="realization",
        evidence_method="'classified_remainders' in kernel.snapshot_fast()",
    ),
    "KCap-5": KernelCap(
        cap_id="KCap-5",
        name="SRSA Vector Computable",
        description=(
            "ugk.srsa_vector() returns a valid 10-axis SRSA vector for this "
            "kernel instance without any application-layer dependency."
        ),
        super_family="realization",
        evidence_method="ugk.srsa_vector()",
    ),
}


@dataclass
class ESAKernelReport:
    """Structured kernel ESA self-check result."""
    caps_checked:  int
    caps_passed:   int
    caps_failed:   int
    results:       dict[str, bool]  # {cap_id: passed}
    failures:      list[str]        # failure descriptions
    overall:       str              # "PASS" | "FAIL"


def run_selfcheck(kernel: "GovernanceKernel") -> ESAKernelReport:
    """Assess all kernel-native ESA capabilities.  Returns ESAKernelReport."""
    from ugk.kernel import STATUS_UNINITIALIZED, STATUS_ACTIVE, CLASSIFIED_REMAINDERS

    results: dict[str, bool] = {}
    failures: list[str] = []

    # KCap-1: governance status observable
    try:
        s = kernel.status
        ok = s in (STATUS_UNINITIALIZED, STATUS_ACTIVE)
        results["KCap-1"] = ok
        if not ok:
            failures.append(f"KCap-1: unexpected status {s!r}")
    except Exception as e:
        results["KCap-1"] = False
        failures.append(f"KCap-1: exception — {e}")

    # KCap-2: Grundnorm read-only (checked structurally — gate proof)
    try:
        import os, stat
        # Single source of truth: resolve protected modules via the registry by LOGICAL
        # identity (not hardcoded root-level filenames, which silently pass vacuously once a
        # module moves into a role-package). Mirrors grundnorm_readonly_gate.
        from ugk.module_registry import grundnorm_paths, GRUNDNORM_MODULES
        def _is_readonly(path):
            mode = os.stat(path).st_mode
            return not bool(mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        paths = grundnorm_paths()
        ok = all(_is_readonly(p) for p in paths)
        results["KCap-2"] = ok
        if not ok:
            writable = [str(p) for p in paths if not _is_readonly(p)]
            failures.append(f"KCap-2: writable Grundnorm modules: {writable}")
    except Exception as e:
        results["KCap-2"] = False
        failures.append(f"KCap-2: exception — {e}")

    # KCap-3: receipt chain integrity
    try:
        ok = kernel.store.verify_stream_hash()
        results["KCap-3"] = ok
        if not ok:
            failures.append("KCap-3: verify_stream_hash() returned False")
    except Exception as e:
        results["KCap-3"] = False
        failures.append(f"KCap-3: exception — {e}")

    # KCap-4: classified remainders declared
    try:
        snap = kernel.snapshot_fast()
        ok = ("classified_remainders" in snap
              and len(snap["classified_remainders"]) >= 4)
        results["KCap-4"] = ok
        if not ok:
            failures.append("KCap-4: classified_remainders missing or incomplete in snapshot_fast()")
    except Exception as e:
        results["KCap-4"] = False
        failures.append(f"KCap-4: exception — {e}")

    # KCap-5: SRSA vector computable
    try:
        from ugk.core.srsa import srsa_vector
        vec = srsa_vector(kernel)
        ok = isinstance(vec, dict) and len(vec) == 10
        results["KCap-5"] = ok
        if not ok:
            failures.append(f"KCap-5: srsa_vector() returned {type(vec)} with {len(vec) if isinstance(vec, dict) else '?'} axes")
    except Exception as e:
        results["KCap-5"] = False
        failures.append(f"KCap-5: exception — {e}")

    passed = sum(1 for v in results.values() if v)
    total  = len(results)
    return ESAKernelReport(
        caps_checked=total,
        caps_passed=passed,
        caps_failed=total - passed,
        results=results,
        failures=failures,
        overall="PASS" if passed == total else "FAIL",
    )


__all__ = ["KernelCap", "ESA_KERNEL_CAPS", "ESAKernelReport", "run_selfcheck"]
