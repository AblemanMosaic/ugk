"""ugk/lineage.py — Semantic lineage binding (Roadmap W-09).

M2.3j replaces the M2.2-era `semantic_lineage=[]` empty-list placeholder
in H_m with a governed lineage structure. Each receipt's lineage binds
the prior receipt's H_m, creating an H_m → H_m chain in the M-commitment
domain analogous to the parent_H_r → H_r chain in the R-commitment domain.

Why no signatures on lineage edges:
  Lineage edges carry parent_h_m as a cryptographic hash. Tampering with
  the parent reference produces an H_m that no longer matches when an
  independent verifier recomputes from a known starting point; the
  H_r round-trip then fails. The Ed25519-signed edges of G_c
  (AuthorityEdge) are needed because they assert *authority delegations*
  by the Governor — semantic provenance does not require an authoritative
  attestation, only a cryptographic anchor. Lineage edges are therefore
  unsigned structured references.

Boundary with M2.3k (namespace / M_Phi):
  semantic_lineage at M2.3j carries ONLY cryptographic references:
    - parent_h_m (64-hex)
    - parent_intent_ref (opaque string, treated as identifier-of-something)
    - edge_position (int)
  No name field is validated against any namespace at this subphase.
  M2.3k (ratified) introduced M_Phi (the phase namespace) for the
  mosaic_root slot in H_j. The two concerns are orthogonal today:
  lineage tracks semantic-state provenance in H_m; namespace tracks
  named-entity validity in H_j.

  Forward note: if a later subphase chooses to carry named references
  inside LineageEdge (e.g. a "parent_name" field), M2.3k's M_Phi check
  would naturally extend to those names. The schema is forward-compatible.

Public surface:
  LineageEdge          — frozen dataclass; structural lineage reference
  build_lineage(...)   — construct lineage list from prior receipt info
  lineage_as_dicts(...) — convert list[LineageEdge] to list[dict] for c_m
  GENESIS_LINEAGE      — empty list (root receipt convention)

Determinism: same prior receipt → byte-identical lineage list → byte-
identical H_m contribution. No signatures, so no randomness anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Root convention: receipts with no prior have an empty lineage list.
GENESIS_LINEAGE: list = []


@dataclass(frozen=True)
class LineageEdge:
    """Structural reference to a prior semantic state in the H_m chain.

    Fields:
      parent_h_m         — hex of the parent's H_m commitment (64 chars)
      parent_intent_ref  — opaque parent identifier (intent_ref string,
                            may be empty); included for provenance
                            readability — NOT semantically required
                            (cryptographic binding is via parent_h_m alone)
      edge_position      — 0 for immediate parent; forward-compat slot
                            for multi-parent semantic merges (always 0
                            at M2.3j; the data model accommodates)

    No signature field. The cryptographic anchor is parent_h_m: any
    alteration of the reference produces an H_m that no longer matches
    the recomputation path of independent verifiers.
    """
    parent_h_m:        str
    parent_intent_ref: str
    edge_position:     int = 0

    def to_canonical_dict(self) -> dict:
        """Canonical dict form for JCS canonicalization as a member of
        the semantic_lineage list input to c_m."""
        return {
            "parent_h_m":        self.parent_h_m,
            "parent_intent_ref": self.parent_intent_ref,
            "edge_position":     self.edge_position,
        }


def build_lineage(
    parent_h_m: Optional[str],
    parent_intent_ref: Optional[str] = None,
) -> list[LineageEdge]:
    """Construct the default single-edge lineage from a prior receipt.

    If parent_h_m is None (no prior receipt in this session), returns
    the empty lineage (root convention). Otherwise returns a one-element
    list with edge_position=0 (immediate parent).

    parent_intent_ref defaults to empty string when not provided.
    """
    if parent_h_m is None:
        return list(GENESIS_LINEAGE)
    return [LineageEdge(
        parent_h_m=parent_h_m,
        parent_intent_ref=parent_intent_ref or "",
        edge_position=0,
    )]


def lineage_as_dicts(lineage: list[LineageEdge]) -> list[dict]:
    """Convert a list of LineageEdge to list[dict] for c_m canonicalization."""
    return [e.to_canonical_dict() for e in lineage]


__all__ = [
    "LineageEdge",
    "GENESIS_LINEAGE",
    "build_lineage",
    "lineage_as_dicts",
]
