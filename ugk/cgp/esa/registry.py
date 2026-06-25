"""ugk.cgp.esa.registry — CGP-ESA capability family registry.

The REGISTRY dict is the machine-checkable companion to
ugk/docs/CGP_CAPABILITIES.md. Each entry declares a CGP-owned capability
in the ESA family, with the legacy ESA cap ID preserved for compat.

Ontology (ratified):
  - CGP owns the capability.
  - Realizations live in consumers (UGK, AbleTools, Navigator, CPVM,
    future).
  - Evidence is emitted through the shared receipt substrate via the
    CGP execution substrate (ugk.cgp.runner / ugk.cgp.ctr).

Scope (per Option-b anchor enumeration ratified by Governor):
  - ~25 anchor caps with full per-cap detail (Classes I/II/III)
  - Class IV/V/VI not enumerated in REGISTRY; covered in
    CGP_CAPABILITIES.md as reference / appendices
  - Pattern families (Cap-34..36, Cap-41..48, etc.) described in
    the markdown doc, not as individual REGISTRY entries

Class definitions:
  I    CGP substrate-general, deterministic
  II   CGP receipt-backed (deterministic aggregation over receipts)
  III  CGP interpretive (deterministic layer + interpretive layer)

Per-cap entry shape (required fields):
  legacy_esa_id          str
  name                   str
  class                  "I" | "II" | "III"
  abstract               str  realization-agnostic statement of the
                              capability
  realizations           dict[consumer_name, {path, status,
                               deterministic, gate, evidence_class,
                               notes}]
  evidence               str  shape of evidence (gate / receipt
                              aggregation / interpretive pack)
  deterministic_layer    str  what's mechanically checkable
  interpretive_layer     str|None  Class III only
  interpretive_evidence_template  dict|None  Class III only
  related_invariants     tuple[str, ...]
  notes                  str
"""
from __future__ import annotations
from typing import Any


# --------------------------------------------------------------------------
# REGISTRY — anchor enumeration
# --------------------------------------------------------------------------

REGISTRY: dict[str, dict[str, Any]] = {

    # ======================================================================
    # CLASS I — CGP substrate-general (deterministic)
    # ======================================================================

    "CGP-ESA-Cap-1": {
        "legacy_esa_id": "Cap-1",
        "name": "Causal Accountability",
        "class": "I",
        "abstract": (
            "Every governed session begins with a session_open receipt at "
            "sequence #1; subsequent operations are causally chained via "
            "prior_receipt_hash. The receipt stream is the audit trail."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.kernel.GovernanceKernel.open_session",
                "status": "DONE",
                "deterministic": True,
                "gate": "session_open implicit (chain_gate verifies)",
                "evidence_class": "gate-suite",
                "notes": "session_open is the canonical first receipt.",
            },
            "Navigator": {
                "path": "navigator.governance.kernel.NavigatorKernel.open_session",
                "status": "DONE",
                "deterministic": True,
                "gate": "session_open receipt + UL-S-04",
                "evidence_class": "scenario-sweep",
                "notes": "Navigator wraps GovernanceKernel with the same discipline.",
            },
            "AbleTools": {
                "path": "abletools.governance.kernel.make_kernel + session_open",
                "status": "DONE",
                "deterministic": True,
                "gate": "esa_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
            "CPVM": {
                "path": "cpvm.bridge.AuthoritativeChain",
                "status": "PARTIAL",
                "deterministic": True,
                "gate": "test_thr_gates",
                "evidence_class": "gate-suite",
                "notes": "CPVM authoritative chain wraps a kernel session.",
            },
        },
        "evidence": "gate:session_open_at_seq_1 + chain hash verification",
        "deterministic_layer": (
            "First receipt in any session has op='session_open' and "
            "sequence number = 1; chain hash binds to genesis."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("UL-S-04", "NBER-1", "S-04"),
        "notes": "Foundational capability; satisfied at kernel substrate level.",
    },

    "CGP-ESA-Cap-2": {
        "legacy_esa_id": "Cap-2",
        "name": "Refusal Record",
        "class": "I",
        "abstract": (
            "Every refusal is recorded as a structured receipt with the "
            "refusal reason, the attempted op, and the refusing authority."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.kernel.GovernanceKernel.refuse",
                "status": "DONE",
                "deterministic": True,
                "gate": "admission_gate",
                "evidence_class": "gate-suite",
                "notes": "Three-tier admit/refuse discipline in execute().",
            },
            "AbleTools": {
                "path": "abletools.governance.kernel (refuse forwarded)",
                "status": "DONE",
                "deterministic": True,
                "gate": "refusal_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
        },
        "evidence": "gate:refuse-emits-receipt with structured payload",
        "deterministic_layer": (
            "Refusal receipt schema: {op, reason, authority, intent, "
            "jurisdiction}; receipt persisted before refusal propagates."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("UL-S-04", "S-04", "EH-S-01"),
        "notes": "First-class refusal per fail-closed discipline.",
    },

    "CGP-ESA-Cap-4": {
        "legacy_esa_id": "Cap-4",
        "name": "Integrity Proof (semantic hash)",
        "class": "I",
        "abstract": (
            "Every receipt is bound by a content-addressed semantic hash "
            "(DM-S-03) that the chain references; tampering with a receipt "
            "invalidates the hash and breaks the chain."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.storage.binding.semantic_hash",
                "status": "DONE",
                "deterministic": True,
                "gate": "chain_gate",
                "evidence_class": "gate-suite",
                "notes": "DM-S-03 canonical semantic hash.",
            },
            "AbleTools": {
                "path": "abletools.governance.binding.semantic_hash",
                "status": "DONE",
                "deterministic": True,
                "gate": "nonrepudiation_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
            "CPVM": {
                "path": "cpvm._vendor.ugk.binding",
                "status": "DONE",
                "deterministic": True,
                "gate": "test_thr_gates (chain-equivalent)",
                "evidence_class": "gate-suite",
                "notes": "Vendored UGK binding module.",
            },
        },
        "evidence": "gate:tamper-detection over a curated receipt sequence",
        "deterministic_layer": (
            "Semantic hash is a deterministic function of canonical "
            "receipt content; any byte change yields a different hash."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("DM-S-03", "CSH-S-01"),
        "notes": "Cryptographic substrate of the chain.",
    },

    "CGP-ESA-Cap-7": {
        "legacy_esa_id": "Cap-7",
        "name": "Receipt Cardinality Audit",
        "class": "I",
        "abstract": (
            "The receipt store exposes a stable count of receipts that "
            "matches the chain length and the number of persisted entries."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.storage.store.UGKReceiptStore.receipt_count",
                "status": "DONE",
                "deterministic": True,
                "gate": "chain_gate (count == chain length)",
                "evidence_class": "gate-suite",
                "notes": "",
            },
        },
        "evidence": "deterministic aggregation: store.receipt_count() "
                   "== len(chain.read_all())",
        "deterministic_layer": (
            "receipt_count() is a pure read of persistent state; equality "
            "with chain length is decidable."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("S-04",),
        "notes": "",
    },

    "CGP-ESA-Cap-12": {
        "legacy_esa_id": "Cap-12",
        "name": "Causal Chain Verification",
        "class": "I",
        "abstract": (
            "The full receipt stream's hash chain can be verified end to "
            "end; verify_stream_hash returns True iff every prior_receipt_"
            "hash references the immediately preceding receipt."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.storage.store.UGKReceiptStore.verify_stream_hash",
                "status": "DONE",
                "deterministic": True,
                "gate": "chain_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
            "AbleTools": {
                "path": "abletools.conformance.chain_gate",
                "status": "DONE",
                "deterministic": True,
                "gate": "chain_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
            "CPVM": {
                "path": "cpvm.guarded_state (chain verification at write)",
                "status": "DONE",
                "deterministic": True,
                "gate": "test_thr_gates._g_seam_*",
                "evidence_class": "gate-suite",
                "notes": "",
            },
        },
        "evidence": "gate:chain-verification on fresh-store + on adversarial-store",
        "deterministic_layer": (
            "verify_stream_hash() walks the chain; returns Boolean."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("CSH-S-01", "UL-S-04"),
        "notes": "",
    },

    "CGP-ESA-Cap-22": {
        "legacy_esa_id": "Cap-22",
        "name": "Receipt Chain Completeness",
        "class": "I",
        "abstract": (
            "The receipt chain has no gaps in sequence numbers and every "
            "receipt's chain hash matches the recomputed canonical hash."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.storage.store.UGKReceiptStore (monotonic sequence + h_r)",
                "status": "DONE",
                "deterministic": True,
                "gate": "chain_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
            "AbleTools": {
                "path": "abletools.conformance.esa_gate",
                "status": "DONE",
                "deterministic": True,
                "gate": "esa_gate",
                "evidence_class": "gate-suite",
                "notes": "esa_gate is the ESA-family receipt-completeness check.",
            },
        },
        "evidence": "gate:sequence-monotonicity + hash-recomputation",
        "deterministic_layer": (
            "For each receipt r at sequence n: r.sequence == n, "
            "r.h_r == semantic_hash(canonical(r))."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("DM-S-03", "S-04", "CSH-S-01"),
        "notes": "The cap most consumers reach for to assert chain integrity.",
    },

    "CGP-ESA-Cap-67": {
        "legacy_esa_id": "Cap-67",
        "name": "Governance Op Registry Integrity",
        "class": "I",
        "abstract": (
            "GOVERNANCE_OPS, REAL_OPS, and PHANTOM_OPS satisfy a "
            "partition/disjoint/coverage invariant: every REAL_OP is in "
            "GOVERNANCE_OPS; no op is both REAL and PHANTOM; the union "
            "covers the declared registry."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.schema (REAL_OPS, PHANTOM_OPS, GOVERNANCE_OPS)",
                "status": "DONE",
                "deterministic": True,
                "gate": "application_ops_gate",
                "evidence_class": "gate-suite",
                "notes": "Schema-load assertions enforce at import time.",
            },
        },
        "evidence": "module-load assertions + application_ops_gate",
        "deterministic_layer": (
            "REAL_OPS ⊆ GOVERNANCE_OPS; REAL_OPS ∩ PHANTOM_OPS = ∅; "
            "len(REAL_OPS) + len(PHANTOM_OPS) == len(GOVERNANCE_OPS)."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("DECOMP-T0-02",),
        "notes": "",
    },

    "CGP-ESA-Cap-88": {
        "legacy_esa_id": "Cap-88",
        "name": "CRP Determinism",
        "class": "I",
        "abstract": (
            "Projected output (validators, ABCs, structural tests) is a "
            "deterministic function of the codex sidebar; two runs of the "
            "projector against the same codex produce byte-identical output."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.crp_determinism_auditor",
                "status": "DONE",
                "deterministic": True,
                "gate": "Navigator's TV-S-06 HR sweep",
                "evidence_class": "scenario-sweep",
                "notes": "Generalizes to any codex-projected system.",
            },
        },
        "evidence": "deterministic two-build hash equivalence",
        "deterministic_layer": (
            "sha256(projector_output(codex, seed=s)) "
            "== sha256(projector_output(codex, seed=s))."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("CSH-S-01",),
        "notes": "Applies to any CRP toolchain, not just Navigator's.",
    },

    "CGP-ESA-Cap-89": {
        "legacy_esa_id": "Cap-89",
        "name": "CRP Codex Coherence",
        "class": "I",
        "abstract": (
            "Codex narrative claims (e.g., 'this system has N caps') are "
            "consistent with runtime state (registry has N entries); "
            "narrative and source agree."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.crp_codex_coherence_auditor",
                "status": "DONE",
                "deterministic": True,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep",
                "notes": "Generalizes; runtime narrative checks across any codex.",
            },
        },
        "evidence": "deterministic codex-vs-runtime field comparison",
        "deterministic_layer": (
            "For each narrative claim with a runtime counterpart, the "
            "values match (or the divergence is recorded as a known carry)."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("CX-CONV-01",),
        "notes": "",
    },

    "CGP-ESA-Cap-90": {
        "legacy_esa_id": "Cap-90",
        "name": "CRP Subclass Validation",
        "class": "I",
        "abstract": (
            "Source classes inheriting from codex-projected ABCs satisfy "
            "the structural contract (methods present, signatures match); "
            "violations raise CRP-γ-* at class definition time."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.crp_subclass_validation_auditor",
                "status": "DONE",
                "deterministic": True,
                "gate": "Navigator HR sweep + Cap-90 receipt-emission",
                "evidence_class": "scenario-sweep",
                "notes": "5/5 sidebars validated in current Navigator state.",
            },
            "AbleTools": {
                "path": "abletools.conformance.census_k4 (partial — "
                        "different shape; same discipline)",
                "status": "PARTIAL",
                "deterministic": True,
                "gate": "census_k4",
                "evidence_class": "gate-suite",
                "notes": "Census-based rather than ABC-based; still CTR-aligned.",
            },
        },
        "evidence": "ABC __init_subclass__ raises CRP-γ-* on contract miss",
        "deterministic_layer": (
            "For each declared method m in the sidebar: hasattr(cls, m) "
            "and signature(cls.m) == signature(spec.m)."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("CRP-γ-CONTRACT-INCOMPLETE",
                                "CRP-γ-SIGNATURE-MISMATCH"),
        "notes": "Most heavily-referenced cap in Navigator codex (136 refs).",
    },

    "CGP-ESA-NBER-1": {
        "legacy_esa_id": "NBER-1",
        "name": "Receipt-Before-Effect Discipline",
        "class": "I",
        "abstract": (
            "No governed effect occurs without a corresponding receipt "
            "having been persisted first; the receipt write precedes the "
            "side effect on every code path."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.kernel.GovernanceKernel.execute "
                        "(receipt → effect ordering)",
                "status": "DONE",
                "deterministic": True,
                "gate": "admission_gate + chain_gate",
                "evidence_class": "gate-suite",
                "notes": "Substrate-level discipline.",
            },
            "AbleTools": {
                "path": "abletools.governance.kernel (forwards UGK)",
                "status": "DONE",
                "deterministic": True,
                "gate": "esa_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
        },
        "evidence": "gate:adversarial-effect-without-receipt is REFUSED",
        "deterministic_layer": (
            "For each side effect, there exists a preceding receipt "
            "with matching op/authority/intent."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("S-04", "UL-S-04"),
        "notes": "The discipline that makes the receipt stream complete.",
    },

    "CGP-ESA-T0-03": {
        "legacy_esa_id": "T0-03",
        "name": "UGKReceiptStore Method Contract",
        "class": "I",
        "abstract": (
            "The UGKReceiptStore class exposes the canonical method "
            "surface (append, read_all, verify_stream_hash, etc.) with "
            "stable signatures; subclasses must satisfy this contract."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.storage.store.UGKReceiptStore",
                "status": "DONE",
                "deterministic": True,
                "gate": "structural contract assertions at import",
                "evidence_class": "gate-suite",
                "notes": "",
            },
        },
        "evidence": "method presence + signature equality at class load",
        "deterministic_layer": (
            "For each declared method m: hasattr(UGKReceiptStore, m); "
            "inspect.signature(m) matches the codex sidebar spec."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("DECOMP-T0-03",),
        "notes": "Decomp-level contract; mirrored in Navigator/CPVM consumers.",
    },

    # ======================================================================
    # CLASS II — CGP receipt-backed (deterministic aggregation)
    # ======================================================================

    "CGP-ESA-Cap-3": {
        "legacy_esa_id": "Cap-3",
        "name": "Authority Trace",
        "class": "II",
        "abstract": (
            "Every receipt carries an authority field; the authority "
            "trace across a session is queryable and matches the warrant "
            "store's declared authority bindings."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.store (Receipt.authority field) + "
                        "ugk.kernel (WarrantStore)",
                "status": "DONE",
                "deterministic": True,
                "gate": "authority_model_gate",
                "evidence_class": "gate-suite",
                "notes": "",
            },
            "AbleTools": {
                "path": "abletools.governance.kernel (forwards UGK)",
                "status": "PARTIAL",
                "deterministic": True,
                "gate": "authority_model_gate",
                "evidence_class": "gate-suite",
                "notes": "Partial: warrant queries are present; "
                          "per-receipt aggregation deferred.",
            },
        },
        "evidence": "receipt-stream aggregation: distinct authorities + "
                   "warrant-store join",
        "deterministic_layer": (
            "GROUP BY authority over the receipt stream; JOIN against "
            "WarrantStore.list_warrants()."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("CHARTER-S-01",),
        "notes": "",
    },

    "CGP-ESA-Cap-20": {
        "legacy_esa_id": "Cap-20",
        "name": "Model-Realization Fidelity",
        "class": "II",
        "abstract": (
            "A declared model (data, ops, surface) is faithfully rendered "
            "by the realization that claims to drive it; the realization "
            "does not present a 'phantom compliance' state. (Previously "
            "framed GUI-specific; under corrected ontology this is "
            "realization-agnostic.)"
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.display_fidelity.DisplayFidelityChecker",
                "status": "DONE",
                "deterministic": True,
                "gate": "Cap-20 receipt + EVS-S-09",
                "evidence_class": "scenario-sweep",
                "notes": "GUI realization: widget tree vs model.",
            },
        },
        "evidence": "receipt:render_fidelity_check with fidelity_ok=True/False",
        "deterministic_layer": (
            "For each declared model entry, the realization exposes a "
            "matching surface element with identical labeling."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("EVS-S-09",),
        "notes": "Future realizations possible: API serializer fidelity, "
                 "doc-generator fidelity, CLI-output fidelity.",
    },

    "CGP-ESA-Cap-21": {
        "legacy_esa_id": "Cap-21",
        "name": "Operation Reachability",
        "class": "II",
        "abstract": (
            "Every declared op has at least one path through which the "
            "realization invokes it; no op is declared but unreachable "
            "from the realization's exposed surface."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.reachability_auditor + UI_PATH_REGISTRY",
                "status": "DONE",
                "deterministic": True,
                "gate": "reachability_gap receipt for unmapped ops",
                "evidence_class": "scenario-sweep",
                "notes": "GUI realization: each op has a UI path.",
            },
        },
        "evidence": "receipt:reachability_gap is empty for declared ops",
        "deterministic_layer": (
            "for op in REAL_OPS: exists path in PATH_REGISTRY where "
            "path.op == op."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("DECOMP-T0-02",),
        "notes": "Future realizations: CLI command paths, REST endpoint "
                 "registry, MCP tool exposure.",
    },

    "CGP-ESA-Cap-52-base": {
        "legacy_esa_id": "Cap-52",
        "name": "Op-Pair Latency Anomaly Detection (base)",
        "class": "II",
        "abstract": (
            "Inter-op latencies are aggregated over the receipt stream; "
            "anomalously slow or fast pairs surface as findings."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.latency_anomaly.OpPairLatencyDetector",
                "status": "DONE",
                "deterministic": True,
                "gate": "Cap-52 sweep (HR.cap52_sweep)",
                "evidence_class": "scenario-sweep",
                "notes": "Base form: statistical aggregation over receipt timing.",
            },
        },
        "evidence": "scenario-sweep anomaly score from HR.cap52_sweep",
        "deterministic_layer": (
            "For each (op_a, op_b) pair: median latency over receipt "
            "stream; flag pairs > N stdev from baseline."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("OS-S-04",),
        "notes": "The 5-mode extension is Cap-52-modes (Class VI aspirational).",
    },

    "CGP-ESA-Cap-53": {
        "legacy_esa_id": "Cap-53",
        "name": "Subsystem Liveness Monitor",
        "class": "II",
        "abstract": (
            "Background subsystems (workers, schedulers, monitors) emit "
            "periodic liveness receipts; absence indicates subsystem stall."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.esa_health.ESAHealthStore + "
                        "ehm_workers",
                "status": "DONE",
                "deterministic": True,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep",
                "notes": "Worker lifecycle aggregation.",
            },
        },
        "evidence": "receipt: liveness heartbeat present within threshold",
        "deterministic_layer": (
            "For each subsystem s: time since s's last heartbeat receipt "
            "< threshold."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("OS-S-03",),
        "notes": "",
    },

    "CGP-ESA-Cap-57": {
        "legacy_esa_id": "Cap-57",
        "name": "Receipt Profile Convergence",
        "class": "II",
        "abstract": (
            "Two builds of the same governed system produce convergent "
            "receipt profiles (same ops, same sequence shape, identical "
            "convergence fingerprint)."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.convergence_fingerprint",
                "status": "DONE",
                "deterministic": True,
                "gate": "HR.verify_convergence_fingerprint",
                "evidence_class": "scenario-sweep",
                "notes": "Anti-fabrication: build twice, fingerprints match.",
            },
            "UGK": {
                "path": "ugk.cgp.runner.ConvergenceFingerprint",
                "status": "DONE",
                "deterministic": True,
                "gate": "HR-T-16",
                "evidence_class": "scenario-sweep",
                "notes": "ConvergenceFingerprint dataclass available at substrate.",
            },
        },
        "evidence": "fingerprint equality across independent build runs",
        "deterministic_layer": (
            "ConvergenceFingerprint(build_a) == ConvergenceFingerprint(build_b)."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("HR-T-16",),
        "notes": "Reproducible-build property at receipt-stream level.",
    },

    "CGP-ESA-Cap-58": {
        "legacy_esa_id": "Cap-58",
        "name": "Behavior Realization Audit",
        "class": "II",
        "abstract": (
            "Every declared behavior (op handler, action, command) has a "
            "realized implementation reachable by the runtime; unrealized "
            "declarations surface as findings. (Reclassified from "
            "GUI-specific 'gesture realization' under corrected ontology.)"
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.gesture_realization_auditor_runtime",
                "status": "DONE",
                "deterministic": True,
                "gate": "Cap-58 runtime sweep",
                "evidence_class": "scenario-sweep",
                "notes": "GUI realization: Qt widget tree walk. Finding "
                          "kinds: ok / display_dark / widget_missing / "
                          "handler_disconnected.",
            },
        },
        "evidence": "receipt: per-behavior realization-finding (ok | gap)",
        "deterministic_layer": (
            "for behavior b in DECLARED_BEHAVIORS: exists handler h such "
            "that h is reachable from realization entry point."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("EVS-S-09",),
        "notes": "Future realizations: CLI action audit, API handler "
                 "audit, batch-job realization audit.",
    },

    "CGP-ESA-Cap-59": {
        "legacy_esa_id": "Cap-59",
        "name": "Receipt Volume Health",
        "class": "II",
        "abstract": (
            "Receipt emission rate stays within declared bounds; "
            "anomalous spikes or drops surface as findings."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.esa_health (volume thresholds)",
                "status": "DONE",
                "deterministic": True,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep",
                "notes": "",
            },
        },
        "evidence": "receipt-stream aggregation: count(receipts) over "
                   "rolling window vs threshold",
        "deterministic_layer": (
            "len(receipts in window W) in [lo_threshold, hi_threshold]."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("OS-S-03",),
        "notes": "",
    },

    "CGP-ESA-Cap-13": {
        "legacy_esa_id": "Cap-13",
        "name": "Receipt Distribution Audit",
        "class": "II",
        "abstract": (
            "Distribution of receipts across ops, authorities, and "
            "jurisdictions is queryable and matches expected proportions "
            "for the consumer's workload profile."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.store (queryable receipt stream)",
                "status": "PARTIAL",
                "deterministic": True,
                "gate": "n/a (primitive available; no canonical aggregator)",
                "evidence_class": "scenario-sweep",
                "notes": "Aggregation primitive present; "
                          "per-consumer thresholds defined by consumer.",
            },
        },
        "evidence": "deterministic aggregation: per-op count distribution",
        "deterministic_layer": (
            "GROUP BY op COUNT(*) over the receipt stream."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": (),
        "notes": "",
    },

    # ======================================================================
    # CLASS III — CGP interpretive (deterministic + interpretive layer)
    # ======================================================================

    "CGP-ESA-Cap-31": {
        "legacy_esa_id": "Cap-31",
        "name": "Structural Completeness Audit",
        "class": "III",
        "abstract": (
            "The implementation is structurally complete with respect to "
            "the declared invariant surface: every declared invariant has "
            "a binding artifact (gate, validator, sidebar), and the "
            "binding is non-trivial."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.structural_auditor (R3 census)",
                "status": "DONE",
                "deterministic": False,
                "gate": "Navigator HR.structural_sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Census output is deterministic; "
                          "completeness verdict is interpretive.",
            },
            "AbleTools": {
                "path": "abletools.conformance.census_k4",
                "status": "PARTIAL",
                "deterministic": True,
                "gate": "census_k4",
                "evidence_class": "gate-suite",
                "notes": "census_k4 generates the deterministic count; "
                          "completeness interpretation is human review.",
            },
        },
        "evidence": (
            "deterministic census output (count of bindings per invariant) "
            "PLUS interpretive completeness verdict in a signed pack"
        ),
        "deterministic_layer": (
            "for each invariant i: count(artifacts bound to i) is "
            "computable; gaps (count==0) are listed."
        ),
        "interpretive_layer": (
            "Given the census output, is the implementation 'complete' "
            "for the declared surface? Some gaps are intentional (waivers, "
            "future work) and some are real omissions; distinguishing "
            "requires judgment."
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "Given the R3 census output, is the implementation "
                "structurally complete for the declared invariant surface? "
                "List unjustified gaps and recommend disposition."
            ),
            "input_artifacts": (
                "census_k4 output + declared invariant list + waiver registry"
            ),
            "output_format": (
                "verdict ∈ {complete, partial-acceptable, partial-with-gaps, "
                "absent} + per-gap classification (waived | future | "
                "actual-gap) + cited rationale"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("ST-S-01", "ST-S-02"),
        "notes": "Pattern: Cap-32..36 follow this shape with sub-family "
                 "variations (hardcoded scan, error path completeness, etc).",
    },

    "CGP-ESA-Cap-32": {
        "legacy_esa_id": "Cap-32",
        "name": "Hardcoded-Value Scan",
        "class": "III",
        "abstract": (
            "Source modules are scanned for hardcoded values that should "
            "be config-driven; matches are reported with confidence levels."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.* ConfigAuditor (KNOWN_HARDCODED scan)",
                "status": "DONE",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Scan finds candidates; intentionality is interpretive.",
            },
        },
        "evidence": "deterministic scan output + interpretive disposition pack",
        "deterministic_layer": (
            "Regex / AST scan over source files for declared hardcoded "
            "patterns; each match has a (file, line, value) tuple."
        ),
        "interpretive_layer": (
            "For each match, is it intentional (e.g., a constant), a "
            "config-leak (should be in config), or a fixture?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "For each hardcoded-value match, classify as intentional / "
                "config-leak / fixture; recommend extraction where "
                "appropriate."
            ),
            "input_artifacts": "ConfigAuditor scan output",
            "output_format": "per-match classification + recommended action",
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("ST-S-04",),
        "notes": "",
    },

    "CGP-ESA-Cap-33": {
        "legacy_esa_id": "Cap-33",
        "name": "Error Path Completeness",
        "class": "III",
        "abstract": (
            "Every declared error code has a path that emits it; every "
            "code path that can fail has a declared error code."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core (error_codes block presence) "
                        "+ tests/test_error_paths",
                "status": "PARTIAL",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Declaration check is deterministic; "
                          "fail-path coverage is interpretive.",
            },
            "AbleTools": {
                "path": "abletools.conformance.error_codes_gate",
                "status": "DONE",
                "deterministic": True,
                "gate": "error_codes_gate",
                "evidence_class": "gate-suite",
                "notes": "AbleTools' realization is deterministic — "
                          "declaration-only, no coverage interpretation.",
            },
        },
        "evidence": "declaration set match + path-coverage interpretive pack",
        "deterministic_layer": (
            "for code in DECLARED_ERROR_CODES: exists raise site; "
            "for raise site: exists declared code in error_codes block."
        ),
        "interpretive_layer": (
            "Are all the error paths that SHOULD be declared actually "
            "declared? Some failure modes may be unconsidered."
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "Given the declared-vs-raised error code mapping, are "
                "there failure modes in the implementation that lack a "
                "declared error code?"
            ),
            "input_artifacts": (
                "error_codes_gate output + source code review"
            ),
            "output_format": (
                "list of undeclared failure modes (if any) + recommended "
                "additions"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("EH-S-01", "EVS-S-08"),
        "notes": "",
    },

    "CGP-ESA-Cap-56": {
        "legacy_esa_id": "Cap-56",
        "name": "CTR Parsed Invariant Count",
        "class": "III",
        "abstract": (
            "The number of invariants the CTR parser extracts from the "
            "codex matches an independent count of declared invariants; "
            "drift indicates parser bug or codex inconsistency."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.ctr.analyzer (parsed count) + "
                        "narrative count assertion",
                "status": "DONE",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Parser count deterministic; whether the parser "
                          "is correctly scoped is interpretive.",
            },
        },
        "evidence": "parsed_count == narrative_count check + scope "
                   "interpretation",
        "deterministic_layer": (
            "len(parser.extract_invariants(codex)) "
            "== narrative_declared_count."
        ),
        "interpretive_layer": (
            "Is the parser scoped to the right invariant population? "
            "False matches and missed declarations require human review."
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "If the parsed count differs from the narrative count, "
                "is the parser scope correct, or is the codex narrative "
                "stale?"
            ),
            "input_artifacts": (
                "parser output + narrative count + codex source"
            ),
            "output_format": (
                "diagnosis (parser bug | narrative stale | actual drift) "
                "+ recommended action"
            ),
            "review_authority": "Governor",
        },
        "related_invariants": ("CTR-S-02",),
        "notes": "",
    },

    "CGP-ESA-Cap-73": {
        "legacy_esa_id": "Cap-73",
        "name": "Test Suite Representativeness",
        "class": "III",
        "abstract": (
            "The test suite adequately samples the governed surface "
            "(declared ops, behaviors, paths); coverage ratio meets the "
            "advisory floor."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.test_representativeness_auditor",
                "status": "DONE",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Ratio computation deterministic; "
                          "'representative' threshold is interpretive.",
            },
        },
        "evidence": "deterministic ratio computation + interpretive "
                   "'representative-enough' verdict",
        "deterministic_layer": (
            "ratio = covered_surface / total_declared_surface; "
            "ratio >= advisory_floor."
        ),
        "interpretive_layer": (
            "Does the covered subset actually exercise the important "
            "paths, or is it concentrated on easy cases?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "Given the coverage ratio and which surface elements are "
                "covered, is the test suite representative of the "
                "governed surface, or biased toward easy cases?"
            ),
            "input_artifacts": (
                "TestRepresentativenessAuditor output + coverage map"
            ),
            "output_format": (
                "verdict (representative | biased) + recommended "
                "additions to balance coverage"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("CTR-S-05", "EVS-S-01"),
        "notes": "",
    },

    "CGP-ESA-Cap-83": {
        "legacy_esa_id": "Cap-83",
        "name": "Cross-Session Persistence",
        "class": "III",
        "abstract": (
            "State that should persist across sessions does persist; "
            "state that should not, doesn't."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator runtime (state lifecycle) + tests",
                "status": "PARTIAL",
                "deterministic": False,
                "gate": "n/a (runtime check; carry)",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Carry: runtime check not yet implemented.",
            },
        },
        "evidence": "session-boundary state diff + intentionality pack",
        "deterministic_layer": (
            "Snapshot state at session close; snapshot again at next "
            "session open; diff."
        ),
        "interpretive_layer": (
            "For each diff entry, is the persistence (or non-persistence) "
            "intentional?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "For each state element that changed (or did not) across "
                "session boundary, is the behavior intentional per the "
                "system's declared persistence model?"
            ),
            "input_artifacts": (
                "state snapshots + persistence model declaration"
            ),
            "output_format": (
                "per-element verdict (intentional-persist | "
                "intentional-ephemeral | unintended-drift) + recommendation"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": (),
        "notes": "Carry in Navigator; pattern available for any consumer.",
    },

    # ======================================================================
    # TRACK 3 EXPANSION — promoted pattern entries (legacy IDs in numeric
    # order: Cap-34, 35, 36, 41, 42, 48)
    # ======================================================================

    "CGP-ESA-Cap-34": {
        "legacy_esa_id": "Cap-34",
        "name": "Structural Completeness — Class Names",
        "class": "III",
        "abstract": (
            "For each declared class in the codex, a class of the same name "
            "exists in source; for each class in source, a corresponding "
            "codex declaration exists. Drift surfaces as findings classified "
            "by interpretive review."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.structural_auditor (declared vs "
                        "source class enumeration)",
                "status": "DONE",
                "deterministic": False,
                "gate": "Navigator HR.structural_sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Set-match is deterministic; classifying source-only "
                          "classes as intentional vs drift is interpretive.",
            },
        },
        "evidence": "symmetric diff (codex-classes ⊕ source-classes) + "
                   "interpretive classification pack",
        "deterministic_layer": (
            "declared_classes(codex) ⊕ source_classes(modules) is computable: "
            "(in_both, codex_only, source_only) triple."
        ),
        "interpretive_layer": (
            "For each codex_only entry: speculative codex addition or "
            "pending source impl? For each source_only entry: legitimate "
            "helper or undeclared drift?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "Classify each codex-only / source-only class as: "
                "speculative-codex-entry / pending-source-impl / "
                "legitimate-source-helper / drift-to-fix."
            ),
            "input_artifacts": (
                "structural_auditor symmetric diff output"
            ),
            "output_format": (
                "per-entry classification + recommended action"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("ST-S-01", "DECOMP-T0-03"),
        "notes": "Promoted from Cap-31 pattern family (Track 3). "
                 "Distinct from Cap-31 which is the broader completeness "
                 "audit; Cap-34 narrows to class-name population.",
    },

    "CGP-ESA-Cap-35": {
        "legacy_esa_id": "Cap-35",
        "name": "Structural Completeness — Method Signatures",
        "class": "III",
        "abstract": (
            "For each declared class, the methods declared in the codex "
            "match the methods in source by name AND signature; signature "
            "drift is detected and surfaced for interpretive review."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.crp_subclass_validation_auditor "
                        "(method name + signature equality)",
                "status": "PARTIAL",
                "deterministic": False,
                "gate": "Navigator HR sweep + Cap-90 evidence",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Name+signature check is deterministic for ABC "
                          "sidebars (Phase γ); helper-classification of "
                          "undeclared methods is interpretive. Superset of "
                          "Cap-90.",
            },
        },
        "evidence": "method-set diff + signature comparison + interpretive "
                   "helper-classification pack",
        "deterministic_layer": (
            "For each declared method m: hasattr(cls, m) AND "
            "inspect.signature(cls.m) == declared signature. Undeclared "
            "method set is enumerable."
        ),
        "interpretive_layer": (
            "For undeclared source methods: accepted private helper, "
            "candidate for promotion to codex, or accidental addition?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "For each undeclared method in source, classify as: "
                "accepted-private-helper / consider-promoting / "
                "accidental-addition."
            ),
            "input_artifacts": (
                "method-name diff + signature comparison output"
            ),
            "output_format": (
                "per-method classification + recommended action"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("ST-S-02", "DECOMP-T0-03",
                                "CRP-γ-CONTRACT-INCOMPLETE",
                                "CRP-γ-SIGNATURE-MISMATCH"),
        "notes": "Promoted from Cap-31 pattern family (Track 3). "
                 "Coexists with Cap-90: Cap-90 is the Class I narrow "
                 "ABC-subclass deterministic validation; Cap-35 is the "
                 "broader Class III method-set abstract that includes "
                 "interpretive helper classification.",
    },

    "CGP-ESA-Cap-36": {
        "legacy_esa_id": "Cap-36",
        "name": "Structural Completeness — Module Boundaries",
        "class": "III",
        "abstract": (
            "The module boundaries declared in the codex (which classes "
            "live in which module) match source layout; cross-module "
            "references are declared in cross_module_invariants blocks."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.core.structural_auditor (declared vs "
                        "actual module paths + cross-module import audit)",
                "status": "PARTIAL",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Module-path check is deterministic; legitimacy "
                          "of undeclared cross-module imports is interpretive.",
            },
        },
        "evidence": "module-path diff + cross-module import report + "
                   "interpretive classification pack",
        "deterministic_layer": (
            "For each codex-declared class c with declared_module m: "
            "actual_module(c) == m. For each cross-module import in source: "
            "presence in declared cross_module_invariants is decidable."
        ),
        "interpretive_layer": (
            "Undeclared cross-module imports may be: standard-library, "
            "accepted utility, drift requiring declaration, or "
            "architectural violation."
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "For each undeclared cross-module import, classify as: "
                "standard-library / accepted-utility / declare-as-invariant "
                "/ architectural-violation."
            ),
            "input_artifacts": (
                "module-path diff + cross-module import report"
            ),
            "output_format": (
                "per-import classification + action"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("ST-S-03", "DECOMP-T0-03"),
        "notes": "Promoted from Cap-31 pattern family (Track 3).",
    },

    "CGP-ESA-Cap-41": {
        "legacy_esa_id": "Cap-41",
        "name": "Receipt Stream Lineage",
        "class": "II",
        "abstract": (
            "The lineage of each receipt (causal chain from session open "
            "to current point) is queryable and stable; replay produces "
            "identical lineage for identical inputs."
        ),
        "realizations": {
            "UGK": {
                "path": "ugk.storage.store.UGKReceiptStore.read_all + "
                        "verify_stream_hash",
                "status": "DONE",
                "deterministic": True,
                "gate": "chain_gate",
                "evidence_class": "gate-suite",
                "notes": "Stream is causally ordered; lineage encoded in "
                          "prior_receipt_hash.",
            },
            "Navigator": {
                "path": "navigator HR.run_batch (HR-S-05 batched execution "
                        "with checkpoint receipts)",
                "status": "DONE",
                "deterministic": True,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep",
                "notes": "Contiguous chain across scenarios.",
            },
        },
        "evidence": "deterministic lineage walk: each receipt's "
                   "prior_receipt_hash references the previous in sequence",
        "deterministic_layer": (
            "For each receipt r at sequence n > 1: r.prior_receipt_hash "
            "== h_r(receipt at sequence n-1). Walking the chain from "
            "genesis to any receipt produces a deterministic lineage."
        ),
        "interpretive_layer": None,
        "interpretive_evidence_template": None,
        "related_invariants": ("CSH-S-01", "UL-S-04", "HR-S-05"),
        "notes": "Promoted (Track 3). Closely related to Cap-12 (Causal "
                 "Chain Verification, Class I): Cap-12 verifies lineage "
                 "integrity; Cap-41 is the broader 'lineage as queryable "
                 "artifact' abstract.",
    },

    "CGP-ESA-Cap-42": {
        "legacy_esa_id": "Cap-42",
        "name": "Op-Coverage Audit",
        "class": "III",
        "abstract": (
            "The set of ops actually exercised over a representative "
            "workload covers the declared REAL_OPS surface to an adequate "
            "threshold; under-exercised ops surface as findings for "
            "interpretive classification."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator HR sweeps (per-op count distribution "
                        "over receipt stream)",
                "status": "PARTIAL",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Coverage ratio is deterministic; "
                          "'representative workload?' is interpretive.",
            },
        },
        "evidence": "deterministic ratio computation + interpretive "
                   "per-op-rarity classification pack",
        "deterministic_layer": (
            "coverage_ratio = |distinct ops in receipt stream| / "
            "|REAL_OPS|. under-exercised_set = REAL_OPS \\ {ops in stream}."
        ),
        "interpretive_layer": (
            "For each under-exercised op: adequately-exercised (false "
            "positive), rare-by-design (acceptable, e.g. emergency "
            "refusal), or under-tested (add coverage)?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "For each under-exercised op, classify as: "
                "adequately-exercised / rare-by-design / under-tested."
            ),
            "input_artifacts": (
                "coverage ratio + per-op count distribution + REAL_OPS "
                "reference"
            ),
            "output_format": (
                "per-op classification + recommended additions"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("CTR-S-05", "EVS-S-01"),
        "notes": "Promoted (Track 3). Distinct from Cap-73 (Test Suite "
                 "Representativeness): Cap-73 asks about test surface "
                 "match; Cap-42 asks specifically about op-set coverage.",
    },

    "CGP-ESA-Cap-48": {
        "legacy_esa_id": "Cap-48",
        "name": "Test-Path Reachability",
        "class": "III",
        "abstract": (
            "Every declared test path (gate, scenario, sweep) is reachable "
            "from the canonical entry point; orphaned tests (declared but "
            "unreachable) and extras (discovered but undeclared) surface "
            "for interpretive classification."
        ),
        "realizations": {
            "Navigator": {
                "path": "navigator.testing.headless_runner."
                        "collect_gate_tests + TEST_REGISTRY cross-check "
                        "(HR-S-06)",
                "status": "DONE",
                "deterministic": False,
                "gate": "Navigator HR sweep",
                "evidence_class": "scenario-sweep + interpretive-pack",
                "notes": "Discovery is deterministic; orphan/extra "
                          "intentionality is interpretive.",
            },
            "AbleTools": {
                "path": "abletools.tests.governed_runner "
                        "(coverage_map.json bindings)",
                "status": "PARTIAL",
                "deterministic": True,
                "gate": "via acis test",
                "evidence_class": "coverage-map",
                "notes": "Coverage-dispatch shape; same discipline.",
            },
        },
        "evidence": "discovered-tests ⊕ declared-tests diff + interpretive "
                   "orphan/extra classification pack",
        "deterministic_layer": (
            "discovered_tests(module) ⊕ declared_tests(registry) is a "
            "symmetric diff. orphan_set = declared \\ discovered. "
            "extra_set = discovered \\ declared."
        ),
        "interpretive_layer": (
            "Orphan classification: registry-stale, test renamed, or "
            "pending-impl? Extra classification: ad-hoc-to-declare, "
            "ephemeral-debugging, or accepted-helper?"
        ),
        "interpretive_evidence_template": {
            "reviewer_question": (
                "For each orphan/extra test, classify as: registry-stale "
                "/ pending-impl / ad-hoc / ephemeral / declare-formally."
            ),
            "input_artifacts": (
                "discovered-tests vs declared-tests diff"
            ),
            "output_format": (
                "per-test classification + recommended action"
            ),
            "review_authority": "designated_auditor",
        },
        "related_invariants": ("CTR-S-06", "HR-S-06"),
        "notes": "Promoted (Track 3).",
    },

}


# --------------------------------------------------------------------------
# Module-level invariants asserted at import time (Phase ζ / Cap-67 style)
# --------------------------------------------------------------------------

_VALID_CLASSES = frozenset({"I", "II", "III"})

_REQUIRED_FIELDS = frozenset({
    "legacy_esa_id", "name", "class", "abstract",
    "realizations", "evidence",
    "deterministic_layer", "interpretive_layer",
    "interpretive_evidence_template",
    "related_invariants", "notes",
})


def _validate_registry() -> None:
    """Module-load assertions: registry is well-formed.

    Raises ValueError at import time if any entry fails. This is the
    Phase-ε-style data_shape check; failure prevents the module from
    importing rather than producing misleading runtime behavior.
    """
    seen_legacy: dict[str, str] = {}
    for cap_id, entry in REGISTRY.items():
        # Key shape
        if not (cap_id.startswith("CGP-ESA-")):
            raise ValueError(
                f"CGP-ESA-REGISTRY: bad cap_id shape: {cap_id!r}"
            )
        # Required fields
        missing = _REQUIRED_FIELDS - entry.keys()
        if missing:
            raise ValueError(
                f"CGP-ESA-REGISTRY: {cap_id} missing fields: {sorted(missing)}"
            )
        # Class value
        if entry["class"] not in _VALID_CLASSES:
            raise ValueError(
                f"CGP-ESA-REGISTRY: {cap_id} class={entry['class']!r} "
                f"not in {sorted(_VALID_CLASSES)}"
            )
        # Class III must have interpretive_evidence_template populated
        if entry["class"] == "III":
            if entry["interpretive_evidence_template"] is None:
                raise ValueError(
                    f"CGP-ESA-REGISTRY: {cap_id} is Class III but "
                    f"interpretive_evidence_template is None"
                )
            t = entry["interpretive_evidence_template"]
            for k in ("reviewer_question", "input_artifacts",
                      "output_format", "review_authority"):
                if k not in t:
                    raise ValueError(
                        f"CGP-ESA-REGISTRY: {cap_id} interpretive_evidence_"
                        f"template missing {k!r}"
                    )
        # Class I/II must have interpretive_evidence_template None
        else:
            if entry["interpretive_evidence_template"] is not None:
                raise ValueError(
                    f"CGP-ESA-REGISTRY: {cap_id} is Class {entry['class']} "
                    f"but interpretive_evidence_template is non-None"
                )
        # Realizations non-empty
        if not entry["realizations"]:
            raise ValueError(
                f"CGP-ESA-REGISTRY: {cap_id} has empty realizations dict"
            )
        # Legacy ID injectivity
        legacy = entry["legacy_esa_id"]
        if legacy in seen_legacy:
            raise ValueError(
                f"CGP-ESA-REGISTRY: legacy_esa_id {legacy!r} bound to both "
                f"{seen_legacy[legacy]} and {cap_id}"
            )
        seen_legacy[legacy] = cap_id


_validate_registry()
