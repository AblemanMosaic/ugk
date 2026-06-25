"""IMPLEMENTATION_CODEX freshness gate.

The implementation codex is a human-authored navigation layer. This gate proves
that its machine-readable entries remain anchored to known sources and existing
implementation surfaces. It does not make the document constitutional law.
"""
from __future__ import annotations

import re
from pathlib import Path

from ugk.conformance import NOT_ESTABLISHED
from ugk.implementation_codex import codex_path, load_entries


REQUIRED_FIELDS = {
    "concept_id",
    "concept_name",
    "status",
    "role_in_substrate",
    "what_it_is_not",
    "instantiates",
    "source_refs",
    "implementation_surfaces",
    "related",
    "agent_operational_rule",
    "common_failure_mode",
    "freshness_owner",
    "last_verified_release",
    "claim_ceiling",
}

VALID_STATUS = {
    "live",
    "dormant",
    "reserved",
    "generated",
    "bounded-external",
    "posture",
    "design-only",
}

CORE_CONCEPTS = {
    "terminal-outcome-lattice",
    "defer-lifecycle",
    "native-bridge",
    "bridge-binding",
    "effect-atomicity",
    "amendment-ledger",
    "proof-model-b",
    "verifier-boundary",
    "classified-remainders",
    "compliance-posture-scalar",
    "epoch-seal-semantics",
    "rho-integration-posture",
    "mcir-smh-resolver-boundary",
    "generated-codex-boundary",
    "release-certification-stack",
    "grundnorm-layer",
    "integrity-basis",
    "ck-canon-float-ban",
    "wge-reactor",
    "three-tier-jurisdiction",
    "three-disjunct-receipt",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _head_release(root: Path) -> int | None:
    release = root / "RELEASE.txt"
    if not release.exists():
        return None
    match = re.search(r"\brelease:\s+r(\d+)\b", release.read_text(encoding="utf-8", errors="replace"))
    return int(match.group(1)) if match else None


def _release_ref_exists(root: Path, ref: str) -> bool:
    needle = ref.split(":", 1)[1]
    for rel in (
        "RELEASE.txt",
        "tools/grbsa/continuity_surfaces.json",
        "tools/grbsa/CONTINUITY_ATTESTATION.json",
    ):
        path = root / rel
        if path.exists() and needle in path.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def _source_ref_errors(root: Path, ref: str, invariant_ids: set[str], adr_ids: set[str]) -> list[str]:
    if ref.startswith("invariant:"):
        inv_id = ref.split(":", 1)[1]
        return [] if inv_id in invariant_ids else [f"unknown invariant ref {ref}"]
    if ref.startswith("adr:"):
        adr_id = ref.split(":", 1)[1]
        return [] if adr_id in adr_ids else [f"unknown ADR ref {ref}"]
    if ref.startswith("doc:"):
        rel = ref.split(":", 1)[1]
        return [] if (root / rel).exists() else [f"missing doc ref {ref}"]
    if ref.startswith("release:"):
        return [] if _release_ref_exists(root, ref) else [f"missing release ref {ref}"]
    return [f"unsupported source ref {ref}"]


def run():
    root = _root()
    path = codex_path(root)
    if not path.exists():
        return NOT_ESTABLISHED, "IMPLEMENTATION_CODEX.md not present in this source tree"

    from ugk.adr import ADR_REGISTRY
    from ugk.invariants import INVARIANT_REGISTRY

    failures: list[str] = []
    stale: list[str] = []

    try:
        entries = list(load_entries(root).values())
    except Exception as exc:
        return False, f"IMPLEMENTATION_CODEX.md JSON block parse failed: {exc}"

    if not entries:
        return False, "IMPLEMENTATION_CODEX.md contains no concept entries"

    by_id: dict[str, dict] = {}
    for entry in entries:
        cid = entry.get("concept_id")
        if not isinstance(cid, str) or not cid:
            failures.append("entry missing string concept_id")
            continue
        if cid in by_id:
            failures.append(f"duplicate concept_id {cid}")
        by_id[cid] = entry

        missing = sorted(REQUIRED_FIELDS - set(entry))
        if missing:
            failures.append(f"{cid}: missing fields {', '.join(missing)}")
            continue

        if entry["status"] not in VALID_STATUS:
            failures.append(f"{cid}: invalid status {entry['status']!r}")
        for field in ("source_refs", "implementation_surfaces", "related"):
            if not isinstance(entry[field], list):
                failures.append(f"{cid}: {field} must be a list")
        if not entry.get("source_refs"):
            failures.append(f"{cid}: source_refs must be non-empty")
        if not entry.get("claim_ceiling"):
            failures.append(f"{cid}: claim_ceiling must be non-empty")
        if not re.fullmatch(r"r\d+", str(entry.get("last_verified_release", ""))):
            failures.append(f"{cid}: last_verified_release must be rN")

        for ref in entry.get("source_refs", []):
            if not isinstance(ref, str):
                failures.append(f"{cid}: non-string source ref {ref!r}")
                continue
            failures.extend(f"{cid}: {err}" for err in _source_ref_errors(root, ref, set(INVARIANT_REGISTRY), set(ADR_REGISTRY)))

        for surface in entry.get("implementation_surfaces", []):
            if not isinstance(surface, str):
                failures.append(f"{cid}: non-string surface {surface!r}")
            elif not (root / surface).exists():
                failures.append(f"{cid}: missing implementation surface {surface}")

        rel_match = re.fullmatch(r"r(\d+)", str(entry.get("last_verified_release", "")))
        head = _head_release(root)
        if rel_match and head is not None and head - int(rel_match.group(1)) > 2:
            stale.append(f"{cid}@{entry['last_verified_release']}")

    missing_core = sorted(CORE_CONCEPTS - set(by_id))
    if missing_core:
        failures.append("missing core concepts: " + ", ".join(missing_core))

    if failures:
        return False, "; ".join(failures[:10]) + (f"; +{len(failures)-10} more" if len(failures) > 10 else "")
    if stale:
        return NOT_ESTABLISHED, "stale implementation codex entries: " + ", ".join(stale[:10])
    return True, f"IMPLEMENTATION_CODEX.md fresh: {len(entries)} entries; {len(CORE_CONCEPTS)} core concepts covered"


if __name__ == "__main__":
    status, detail = run()
    if status is True:
        print("PASS", detail)
        raise SystemExit(0)
    if status == NOT_ESTABLISHED:
        print("N/EST", detail)
        raise SystemExit(0)
    print("FAIL", detail)
    raise SystemExit(1)
