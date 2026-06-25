#!/usr/bin/env python3
"""ugk/conformance/m2_vectors_runner.py — Phase M2.1 executable vector runner.

Exercises the M2.1 vector set (REV3 §Deliverable 7.B, narrowed to what is
testable in M2.1 isolation):

  Determinism / structure:
    EV-001          primary positive (full H_s/H_c/H_m/H_j/H_r computation)
    EV-D01          determinism — same input twice → byte-identical H_r
    EV-D02          determinism — fresh process invocation → byte-identical H_r
    EV-D03          per-leaf independence — small change in one c_i input
                    changes only that H_i and H_r, no other H_j

  Merkle structure (worked examples from REV3 §Deliverable 2):
    EV-MS-3         3 leaves
    EV-MS-4         4 leaves
    EV-MS-6         6 leaves
    EV-MS-7         7 leaves

  Boundary / freshness:
    EV-N05          NotYetAdmissible (current_epoch < valid_from)
    EV-FR-01        valid epoch — signed FreshnessClaim verifies in-window  (M2.3e)
    EV-FR-02        expired epoch — current_epoch > valid_until → ExpiredEdge  (M2.3e)
    EV-FR-03        invalid signature — tampered window_sig → SignatureInvalid  (M2.3e)
    EV-FR-04        epoch transition — N expires, N+1 admits, signatures distinct  (M2.3e)

  Commitment Minimality gate:
    EV-CM-01        registered principled redundancy (strict-mode 7 leaves) passes
    EV-CM-02        unregistered redundancy (hypothetical extra leaf) fails

  Attack vector:
    EV-AV-001       strict-mode self-describing identity catches a substitution
                    that context-external mode admits (via merkle proof opening)

Vectors NOT included (depend on machinery outside M2.1+M2.3e isolation):
    EV-N01          ExpiredEdge in full D_c form — covered structurally by
                    EV-FR-02; full decision-procedure form awaits M2.3l
    EV-N02..EV-N04  NamespaceNonMember, ContextMismatch, UnderRecordedCollapse —
                    require D_j decision and binding_verification_gate (M2.3k/l)
    EV-I01..EV-I06  §11 decisional-independence vectors — require full
                    witness opening machinery (M2.3m)

Run: `python3 -m ugk.conformance.m2_vectors_runner`
Exit 0 iff every vector passes.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from typing import Callable

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ugk.storage.binding_m2 import (  # noqa: E402
    H_s, H_c, H_m, H_j, H_id_P, H_id_Sigma, H_id_Phi,
    compute_H_r, build_inclusion_proof, verify_inclusion_proof,
    commitment_minimality_gate, freshness_check,
    TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J,
    TAG_ID_P, TAG_ID_SIGMA, TAG_ID_PHI,
    DS_NODE, DS_R, DS_SINGLELEAF, ID_ROOT,
    _sha256, _leaf_encoding,
    CANONICALIZATION_DOMAINS, PRINCIPLED_REDUNDANCY_REGISTRY,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixture inputs (deterministic; no wall-clock, no randomness)
# ─────────────────────────────────────────────────────────────────────────────

FIXTURE = {
    "op": "policy_evaluate",
    "inputs": {"rule": "allow", "limit": 5},
    "authority_chain": ["Root", "Org", "Service", "Key"],
    "policy_id": "P_7",
    "capabilities": ["evaluate"],
    "warrant_basis": ["W_1"],
    "parent_H_r": "0" * 64,
    "freshness": {
        "phase_code": "production",
        "epoch_counter": 1700000000,
        "valid_from":    1700000000,
        "valid_until":   1700100000,
        "window_sig":    "00" * 64,
    },
    "intent": "execute policy",
    "intent_ref": "id://intent/1",
    "legend_hash": "a" * 64,
    "semantic_lineage": ["parse", "normalize"],
    "phase_code": "production",
    "mosaic_root": "m" * 64,
    "session_id": "session_001",
    "authority_key": "k" * 64,
    "semantic_regime_id": "Sigma_0",
}


def _compute_all_leaf_hashes(fx: dict, *, policy_id: str | None = None) -> dict:
    pid = policy_id if policy_id is not None else fx["policy_id"]
    return {
        "h_s":  H_s(fx["op"], fx["inputs"]),
        "h_c":  H_c(fx["authority_chain"], pid, fx["capabilities"],
                    fx["warrant_basis"], fx["parent_H_r"], fx["freshness"]),
        "h_m":  H_m(fx["intent"], fx["intent_ref"], fx["legend_hash"],
                    fx["semantic_lineage"], semantic_regime_id=fx["semantic_regime_id"]),
        "h_j":  H_j(fx["phase_code"], fx["mosaic_root"],
                    fx["session_id"], fx["authority_key"]),
        "h_idP":     H_id_P(pid),
        "h_idSigma": H_id_Sigma(fx["semantic_regime_id"]),
        "h_idPhi":   H_id_Phi(fx["phase_code"]),
    }


def _context_external_leaves(hashes: dict) -> list[tuple[int, bytes]]:
    return [
        (TAG_H_S, hashes["h_s"]),
        (TAG_H_C, hashes["h_c"]),
        (TAG_H_M, hashes["h_m"]),
        (TAG_H_J, hashes["h_j"]),
    ]


def _strict_leaves(hashes: dict) -> list[tuple[int, bytes]]:
    return _context_external_leaves(hashes) + [
        (TAG_ID_P,     hashes["h_idP"]),
        (TAG_ID_SIGMA, hashes["h_idSigma"]),
        (TAG_ID_PHI,   hashes["h_idPhi"]),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Individual vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_001_primary() -> tuple[bool, str]:
    h = _compute_all_leaf_hashes(FIXTURE)
    leaves = _context_external_leaves(h)
    H_r = compute_H_r(leaves)
    if len(H_r) != 32:
        return False, f"H_r length {len(H_r)} != 32"
    return True, f"H_r={H_r.hex()[:16]}..."


def ev_d01_determinism_same_input() -> tuple[bool, str]:
    h1 = _compute_all_leaf_hashes(FIXTURE)
    h2 = _compute_all_leaf_hashes(FIXTURE)
    for k in h1:
        if h1[k] != h2[k]:
            return False, f"H_i {k} differs between runs"
    H_r1 = compute_H_r(_context_external_leaves(h1))
    H_r2 = compute_H_r(_context_external_leaves(h2))
    if H_r1 != H_r2:
        return False, "H_r differs between identical runs"
    return True, "H_s/H_c/H_m/H_j/H_r all byte-identical across runs"


def ev_d02_determinism_fresh_process() -> tuple[bool, str]:
    """Run the H_r computation in a fresh subprocess and compare."""
    h = _compute_all_leaf_hashes(FIXTURE)
    H_r_this = compute_H_r(_context_external_leaves(h)).hex()

    # absolute path to UGK root so subprocess can import ugk.*
    ugk_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    script = (
        "import sys; sys.path.insert(0, " + repr(ugk_root) + ")\n"
        "from ugk.storage.binding_m2 import (H_s, H_c, H_m, H_j, compute_H_r,\n"
        "    TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J)\n"
        "fx = " + repr(FIXTURE) + "\n"
        "h_s = H_s(fx['op'], fx['inputs'])\n"
        "h_c = H_c(fx['authority_chain'], fx['policy_id'], fx['capabilities'],\n"
        "          fx['warrant_basis'], fx['parent_H_r'], fx['freshness'])\n"
        "h_m = H_m(fx['intent'], fx['intent_ref'], fx['legend_hash'], fx['semantic_lineage'], semantic_regime_id=fx['semantic_regime_id'])\n"
        "h_j = H_j(fx['phase_code'], fx['mosaic_root'], fx['session_id'], fx['authority_key'])\n"
        "H_r = compute_H_r([(TAG_H_S, h_s), (TAG_H_C, h_c), (TAG_H_M, h_m), (TAG_H_J, h_j)])\n"
        "print(H_r.hex())\n"
    )
    script_path = os.path.join(tempfile.gettempdir(), "m2_d02_subproc.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return False, f"subprocess failed: {result.stderr.strip()[:300]}"
    H_r_other = result.stdout.strip()
    if H_r_this != H_r_other:
        return False, f"H_r differs across processes: {H_r_this[:16]} vs {H_r_other[:16]}"
    return True, f"H_r byte-identical across two Python processes: {H_r_this[:16]}..."


def _ev_pairwise_independence(i: str, j: str) -> tuple[bool, str]:
    """For ordered pair (i, j) over the core commitments {s, c, m}, perturb
    c_i's input and verify H_i changes while H_j does NOT.

    Reduced form of THR §11 decisional independence: tests the cryptographic-
    independence half (each H_i is a separate, independent hash). The full
    decisional-independence half (showing D_i=1 with D_j=0) requires the
    D_s/D_c/D_m decision procedures, which land at M2.3.
    """
    assert i in {"s", "c", "m"} and j in {"s", "c", "m"} and i != j

    # Which fixture field, when perturbed, alters c_i's input WITHOUT touching
    # any other c_k's input domain. Selections are disjoint across c_i's:
    #   c_s domain: {op, inputs}
    #   c_c domain: {authority_chain, policy_id, capabilities, warrant_basis,
    #                parent_H_r, freshness}
    #   c_m domain: {intent, intent_ref, legend_hash, semantic_lineage}
    perturb_field = {
        "s": ("inputs",       {"rule": "allow", "limit": 99}),    # in c_s domain only
        "c": ("policy_id",    "P_DIFFERENT"),                     # in c_c domain only
        "m": ("intent",       "execute policy v2"),               # in c_m domain only
    }
    field, new_value = perturb_field[i]

    baseline = _compute_all_leaf_hashes(FIXTURE)

    perturbed_fx = dict(FIXTURE)
    perturbed_fx[field] = new_value
    perturbed = _compute_all_leaf_hashes(perturbed_fx)

    H_key = {"s": "h_s", "c": "h_c", "m": "h_m"}
    if baseline[H_key[i]] == perturbed[H_key[i]]:
        return False, f"H_{i} did NOT change when c_{i} input was perturbed"
    if baseline[H_key[j]] != perturbed[H_key[j]]:
        return False, (f"H_{j} CHANGED when only c_{i} input was perturbed "
                       f"(cryptographic independence violated)")
    return True, f"H_{i} changed, H_{j} unchanged (independence preserved)"


def ev_d03_per_leaf_independence_summary() -> tuple[bool, str]:
    """Summary of EV-D03's original coverage scope, kept for continuity.
    The full pairwise grid is now in EV-I01..EV-I06 (reduced form).
    """
    h = _compute_all_leaf_hashes(FIXTURE)
    H_r_baseline = compute_H_r(_context_external_leaves(h))

    perturbed_fx = dict(FIXTURE)
    perturbed_fx["inputs"] = {"rule": "allow", "limit": 99}
    perturbed = _compute_all_leaf_hashes(perturbed_fx)
    H_r_perturbed = compute_H_r(_context_external_leaves(perturbed))

    # Summary: H_r changes iff any leaf changes (global nonrepudiation)
    if H_r_baseline == H_r_perturbed:
        return False, "H_r did NOT change when c_s input was perturbed"
    return True, "H_r changes when any c_i input is perturbed (CHC-S-03 global nonrepudiation)"


def ev_ms_n_leaves(n: int) -> tuple[bool, str]:
    """Worked merkle example for n leaves (REV3 §Deliverable 2)."""
    if n not in (3, 4, 6, 7):
        return False, f"unsupported n={n}"
    h = _compute_all_leaf_hashes(FIXTURE)
    if n == 3:
        leaves = [(TAG_H_S, h["h_s"]), (TAG_H_C, h["h_c"]), (TAG_H_M, h["h_m"])]
    elif n == 4:
        leaves = _context_external_leaves(h)
    elif n == 6:
        # strict without H_j (rare per REV3) — H_s, H_c, H_m, id_P, id_Sigma; only 5
        # The worked example for 6 was H_s,H_c,H_m,H_j,id_P,id_Sigma. Use that.
        leaves = _context_external_leaves(h) + [
            (TAG_ID_P, h["h_idP"]),
            (TAG_ID_SIGMA, h["h_idSigma"]),
        ]
    else:  # n == 7
        leaves = _strict_leaves(h)
    H_r = compute_H_r(leaves)
    # Verify by also computing inclusion proofs for each leaf
    for tag, _hash in leaves:
        leaf_enc, path = build_inclusion_proof(leaves, tag)
        if not verify_inclusion_proof(H_r, leaf_enc, path):
            return False, f"inclusion proof for tag {tag:#04x} fails to verify"
    return True, f"H_r={H_r.hex()[:16]}..., all {n} inclusion proofs verify"


def ev_n05_not_yet_admissible() -> tuple[bool, str]:
    """current_epoch < valid_from must emit NotYetAdmissible."""
    fc = {
        "phase_code":    "production",
        "epoch_counter": 100,
        "valid_from":    100,
        "valid_until":   200,
        "window_sig":    "00" * 64,
    }
    # In-window: OK
    ok, err = freshness_check(fc, current_epoch=150, current_phase_code="production")
    if not ok or err is not None:
        return False, f"in-window unexpectedly failed: ok={ok}, err={err}"
    # Pre-window: NotYetAdmissible
    ok, err = freshness_check(fc, current_epoch=50, current_phase_code="production")
    if ok or err != "NotYetAdmissible":
        return False, f"pre-window: expected NotYetAdmissible, got ok={ok}, err={err}"
    # Post-window: ExpiredEdge (confirm we don't conflate)
    ok, err = freshness_check(fc, current_epoch=250, current_phase_code="production")
    if ok or err != "ExpiredEdge":
        return False, f"post-window: expected ExpiredEdge, got ok={ok}, err={err}"
    # Wrong phase: PhaseMismatch
    ok, err = freshness_check(fc, current_epoch=150, current_phase_code="staging")
    if ok or err != "PhaseMismatch":
        return False, f"wrong phase: expected PhaseMismatch, got ok={ok}, err={err}"
    return True, "all four freshness boundary cases emit correct error codes"


def ev_cm_01_registered_principled_redundancy() -> tuple[bool, str]:
    """Strict-mode 7 leaves (id_P, id_Sigma, id_Phi are registered redundancies
    with H_c, H_m, H_j as carriers) — gate accepts."""
    ok, reason = commitment_minimality_gate(
        {"H_s", "H_c", "H_m", "H_j", "id_P", "id_Sigma", "id_Phi"}
    )
    if not ok:
        return False, f"strict-mode 7 leaves rejected: {reason}"
    # Subset checks: removing the carrier should not flip the verdict
    # because the redundancy is only detected when carrier is present
    ok, reason = commitment_minimality_gate({"H_s", "H_c", "H_m"})
    if not ok:
        return False, f"minimal 3 leaves rejected: {reason}"
    return True, "registered principled redundancies pass; minimal 3-leaf set passes"


def ev_cm_02_unregistered_redundancy() -> tuple[bool, str]:
    """Hypothetical extra leaf whose domain is a subset of H_c, but not in
    PRINCIPLED_REDUNDANCY_REGISTRY → gate rejects with explicit reason."""
    extended_domains = dict(CANONICALIZATION_DOMAINS)
    # synthesize a hypothetical leaf whose domain = {policy_id}
    # — same as id_P's domain, would be redundant with H_c if not registered
    extended_domains["H_hypothetical_redundant"] = frozenset({"policy_id"})
    # registry NOT extended — H_hypothetical_redundant is not principled
    ok, reason = commitment_minimality_gate(
        {"H_s", "H_c", "H_m", "H_hypothetical_redundant"},
        domains=extended_domains,
        # registry default → PRINCIPLED_REDUNDANCY_REGISTRY (does NOT include hypothetical)
    )
    if ok:
        return False, "gate accepted unregistered redundancy (should reject)"
    if "H_hypothetical_redundant" not in reason:
        return False, f"reason doesn't name the offending leaf: {reason}"
    if "H_c" not in reason:
        return False, f"reason doesn't name the carrier leaf H_c: {reason}"
    return True, f"unregistered redundancy correctly rejected: {reason}"


def ev_av_001_strict_mode_self_describing_identity() -> tuple[bool, str]:
    """The headline attack vector (REV3 Appendix EV).

    Demonstrates that under strict mode, a consumer holding H_r alone (no
    witnesses) can verify policy_id via merkle inclusion proof of the id_P
    leaf. Under context-external mode, no id_P leaf exists, so the same
    verification is impossible.

    Construction:
      - R under (P_2 = "development"); compute H_r under both modes
      - Adversary claims the H_r references P_1 = "production"
      - Strict mode: consumer opens id_P leaf via proof; sees P_2 ≠ P_1 → refuted
      - Context-external mode: no id_P leaf; consumer cannot derive P from H_r alone
    """
    fx = dict(FIXTURE)

    # ── 1. Construct R_dev under P_2 in strict mode ──
    P_2 = "development"
    P_1 = "production"
    h_P2 = _compute_all_leaf_hashes(fx, policy_id=P_2)
    h_P1 = _compute_all_leaf_hashes(fx, policy_id=P_1)

    # Strict mode H_r values
    H_r_strict_P2 = compute_H_r(_strict_leaves(h_P2))
    H_r_strict_P1 = compute_H_r(_strict_leaves(h_P1))
    # Context-external mode H_r values
    H_r_ce_P2 = compute_H_r(_context_external_leaves(h_P2))
    H_r_ce_P1 = compute_H_r(_context_external_leaves(h_P1))

    # ── 2. Sanity: H_r differs across policies in both modes ──
    # (H_c includes policy_id, so even context-external H_r differs.
    # The attack is NOT about H_r equality — it's about whether the
    # consumer can determine policy_id FROM H_r ALONE.)
    if H_r_strict_P1 == H_r_strict_P2:
        return False, "strict-mode H_r equal across different policies (impossible)"
    if H_r_ce_P1 == H_r_ce_P2:
        return False, "context-external H_r equal across different policies (impossible)"

    # ── 3. THE KEY DEMONSTRATION ──
    # Consumer S_d holds H_r_strict_P2 (the actual receipt under P_2).
    # Adversary claims to S_d: "this H_r references policy P_1".
    # S_d wants to verify the policy_id WITHOUT retrieving the H_c witness.

    # Strict mode: S_d can open the id_P leaf via merkle proof against H_r alone.
    strict_leaves_P2 = _strict_leaves(h_P2)
    actual_idP_leaf_enc, path = build_inclusion_proof(strict_leaves_P2, TAG_ID_P)
    # S_d verifies the actual P_2 leaf against the receipt's H_r — passes.
    if not verify_inclusion_proof(H_r_strict_P2, actual_idP_leaf_enc, path):
        return False, "strict mode: actual id_P leaf proof failed against actual H_r"

    # Adversary claims policy_id = P_1, supplies a fake leaf encoding for P_1.
    fake_idP_leaf_enc = _leaf_encoding(TAG_ID_P, H_id_P(P_1))
    # S_d verifies the FAKE leaf against the receipt's H_r — must REJECT.
    if verify_inclusion_proof(H_r_strict_P2, fake_idP_leaf_enc, path):
        return False, ("strict mode: fake id_P leaf for P_1 verified against H_r for P_2 "
                       "(would mean substitution succeeded — defense broken)")

    # ── 4. Context-external mode: no id_P leaf exists ──
    # build_inclusion_proof for TAG_ID_P over context-external leaves must raise.
    ce_leaves_P2 = _context_external_leaves(h_P2)
    try:
        build_inclusion_proof(ce_leaves_P2, TAG_ID_P)
        return False, ("context-external mode: build_inclusion_proof for id_P unexpectedly "
                       "succeeded — id_P should not be present as a leaf")
    except ValueError:
        pass  # expected: id_P not in context-external leaf set

    # In context-external mode, S_d holds only H_r_ce_P2 and has no way to
    # derive policy_id without retrieving the H_c witness. Adversary's claim
    # of P_1 cannot be refuted from H_r_ce_P2 alone.

    # ── 5. Verdict ──
    return True, (
        "strict mode catches substitution via id_P merkle proof; "
        "context-external admits the attack (no id_P leaf to open against H_r alone)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3e — FreshnessClaim / EpochIssuance vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_fr_01_valid_epoch() -> tuple[bool, str]:
    """EV-FR-01: signed FreshnessClaim verifies inside the declared window."""
    from ugk import freshness as F
    from ugk import invariants as inv
    ei = F.sign_epoch_issuance(
        phase_id=inv.ID_PHI_0, epoch_counter=7,
        valid_from=100, valid_until=200,
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )
    claim = F.build_freshness_claim_from_epoch(ei)
    # Verify at three in-window epochs
    for current_epoch in (100, 150, 200):
        ok, err = F.verify_freshness_claim(
            claim, current_epoch=current_epoch,
            current_phase_id=inv.ID_PHI_0,
            governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX,
        )
        if not ok:
            return False, f"in-window epoch {current_epoch} rejected: {err}"
    return True, "signed FreshnessClaim verifies at lower-bound, mid-window, and upper-bound epochs"


def ev_fr_02_expired_epoch() -> tuple[bool, str]:
    """EV-FR-02: current_epoch > valid_until → ExpiredEdge."""
    from ugk import freshness as F
    from ugk import invariants as inv
    ei = F.sign_epoch_issuance(
        phase_id=inv.ID_PHI_0, epoch_counter=7,
        valid_from=100, valid_until=200,
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )
    claim = F.build_freshness_claim_from_epoch(ei)
    # current_epoch = 201, one past valid_until
    ok, err = F.verify_freshness_claim(
        claim, current_epoch=201,
        current_phase_id=inv.ID_PHI_0,
        governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX,
    )
    if ok:
        return False, "expired epoch unexpectedly accepted"
    if err != "ExpiredEdge":
        return False, f"wrong error code: got {err!r}, expected 'ExpiredEdge'"
    # Verify the SIGNATURE itself is still valid (only the window is past)
    ok2, err2 = F.verify_epoch_issuance(ei, F.DEFAULT_TEST_PUBKEY_HEX)
    if not ok2:
        return False, f"signature unexpectedly failed: {err2}"
    return True, "expired window rejected with ExpiredEdge; underlying signature still cryptographically valid"


def ev_fr_03_invalid_signature() -> tuple[bool, str]:
    """EV-FR-03: tampered window_sig → SignatureInvalid (boundary checks pass)."""
    import dataclasses as dc
    from ugk import freshness as F
    from ugk import invariants as inv
    ei = F.sign_epoch_issuance(
        phase_id=inv.ID_PHI_0, epoch_counter=7,
        valid_from=100, valid_until=200,
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )
    # Tamper: flip the last byte of the signature
    bad_sig = ei.signature[:-2] + ("00" if ei.signature[-2:] != "00" else "01")
    tampered_ei = dc.replace(ei, signature=bad_sig)
    claim = F.build_freshness_claim_from_epoch(tampered_ei)
    ok, err = F.verify_freshness_claim(
        claim, current_epoch=150,  # in-window, so signature is the only failing check
        current_phase_id=inv.ID_PHI_0,
        governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX,
    )
    if ok:
        return False, "tampered signature unexpectedly accepted"
    if err != "SignatureInvalid":
        return False, f"wrong error code: got {err!r}, expected 'SignatureInvalid'"
    # Cross-check at the EpochIssuance layer
    ok2, err2 = F.verify_epoch_issuance(tampered_ei, F.DEFAULT_TEST_PUBKEY_HEX)
    if ok2 or err2 != "SignatureInvalid":
        return False, f"EpochIssuance signature check unexpectedly: ok={ok2}, err={err2}"
    return True, "tampered window_sig produces SignatureInvalid at both FreshnessClaim and EpochIssuance layers; structural fields still pass"


def ev_fr_04_epoch_transition() -> tuple[bool, str]:
    """EV-FR-04: epoch transition — receipt under epoch N expires at N's
    valid_until; new epoch N+1 admits later receipts. Signatures differ
    between epochs even when keys are identical."""
    from ugk import freshness as F
    from ugk import invariants as inv
    # Epoch N: covers [100, 200]
    N = 5
    epoch_N = F.sign_epoch_issuance(
        phase_id=inv.ID_PHI_0, epoch_counter=N,
        valid_from=100, valid_until=200,
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )
    # Epoch N+1: covers [201, 300]
    epoch_Np1 = F.sign_epoch_issuance(
        phase_id=inv.ID_PHI_0, epoch_counter=N + 1,
        valid_from=201, valid_until=300,
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )

    # (a) Signatures differ — same key signs different payloads
    if epoch_N.signature == epoch_Np1.signature:
        return False, "epoch N and N+1 produced identical signatures (impossible — disjoint payloads)"

    # (b) Both signatures individually verify
    for label, ei in [("epoch N", epoch_N), ("epoch N+1", epoch_Np1)]:
        ok, err = F.verify_epoch_issuance(ei, F.DEFAULT_TEST_PUBKEY_HEX)
        if not ok:
            return False, f"{label} signature failed: {err}"

    # (c) At time T=150: epoch N admits, epoch N+1 does NOT (NotYetAdmissible)
    claim_N   = F.build_freshness_claim_from_epoch(epoch_N)
    claim_Np1 = F.build_freshness_claim_from_epoch(epoch_Np1)
    ok_N_at_150,   _ = F.verify_freshness_claim(claim_N,   current_epoch=150,
                                                current_phase_id=inv.ID_PHI_0,
                                                governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX)
    ok_Np1_at_150, err_Np1_150 = F.verify_freshness_claim(claim_Np1, current_epoch=150,
                                                current_phase_id=inv.ID_PHI_0,
                                                governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX)
    if not ok_N_at_150:
        return False, "at time 150: epoch N should admit but did not"
    if ok_Np1_at_150 or err_Np1_150 != "NotYetAdmissible":
        return False, f"at time 150: epoch N+1 admission should be NotYetAdmissible, got ok={ok_Np1_at_150}, err={err_Np1_150!r}"

    # (d) At time T=250: epoch N is ExpiredEdge, epoch N+1 admits
    ok_N_at_250,   err_N_250 = F.verify_freshness_claim(claim_N,   current_epoch=250,
                                                current_phase_id=inv.ID_PHI_0,
                                                governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX)
    ok_Np1_at_250, _ = F.verify_freshness_claim(claim_Np1, current_epoch=250,
                                                current_phase_id=inv.ID_PHI_0,
                                                governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX)
    if ok_N_at_250 or err_N_250 != "ExpiredEdge":
        return False, f"at time 250: epoch N should be ExpiredEdge, got ok={ok_N_at_250}, err={err_N_250!r}"
    if not ok_Np1_at_250:
        return False, "at time 250: epoch N+1 should admit but did not"

    return True, "epoch transition: at T=150 only N admits (N+1 NotYetAdmissible); at T=250 only N+1 admits (N ExpiredEdge); signatures distinct and individually valid"


# ─────────────────────────────────────────────────────────────────────────────
# M2.3g — Policy vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_pl_01_policy_version_changes_h_c_and_h_r() -> tuple[bool, str]:
    """EV-PL-01: signing two versions of the same Policy produces distinct
    id(P); receipts under each policy have distinct H_c and H_r values
    even when all other inputs are identical."""
    from ugk.governance import policy as P
    from ugk import freshness as F
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import (
        H_s, H_c, H_m, H_j, H_id_P, H_id_Sigma, H_id_Phi, compute_H_r,
        TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J,
        TAG_ID_P, TAG_ID_SIGMA, TAG_ID_PHI,
    )

    # Two versions of the same policy
    p_v1 = P.sign_policy(
        subjects=("jurisdiction:production",),
        decision_rules=("default-allow",),
        version="v1",
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )
    p_v2 = P.sign_policy(
        subjects=("jurisdiction:production",),
        decision_rules=("default-allow",),
        version="v2",
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )

    id_v1 = P.id_policy(p_v1)
    id_v2 = P.id_policy(p_v2)
    if id_v1 == id_v2:
        return False, "version change did not alter id(P)"

    # Verify both Policies cryptographically
    ok_v1, err_v1 = P.verify_policy(p_v1, F.DEFAULT_TEST_PUBKEY_HEX)
    ok_v2, err_v2 = P.verify_policy(p_v2, F.DEFAULT_TEST_PUBKEY_HEX)
    if not ok_v1 or not ok_v2:
        return False, f"signature verification failed: v1 err={err_v1}, v2 err={err_v2}"

    # Construct identical receipts EXCEPT for policy_id, compute H_c and H_r
    def _make_h_c(policy_id_hex: str):
        freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))
        return H_c(
            authority_chain=["Operator"],
            policy_id=policy_id_hex,
            capabilities=[],
            warrant_basis=["W_1"],
            parent_H_r="00" * 64,
            freshness=freshness,
        )

    def _make_h_r(policy_id_hex: str):
        freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))
        h_s = H_s("policy_evaluate", {"x": 1})
        h_c = _make_h_c(policy_id_hex)
        h_m = H_m("intent", "id://intent/1", "a" * 64, [],
                  semantic_regime_id=inv.ID_SIGMA_0)
        h_j = H_j(freshness["phase_code"], "0" * 64, "dkn_001", "Operator")
        leaves = [
            (TAG_H_S, h_s), (TAG_H_C, h_c),
            (TAG_H_M, h_m), (TAG_H_J, h_j),
            (TAG_ID_P,     H_id_P(policy_id_hex)),
            (TAG_ID_SIGMA, H_id_Sigma(inv.ID_SIGMA_0)),
            (TAG_ID_PHI,   H_id_Phi(inv.ID_PHI_0)),
        ]
        return compute_H_r(leaves).hex()

    h_c_v1 = _make_h_c(id_v1).hex()
    h_c_v2 = _make_h_c(id_v2).hex()
    if h_c_v1 == h_c_v2:
        return False, "H_c is identical across policy versions (it should differ)"

    h_r_v1 = _make_h_r(id_v1)
    h_r_v2 = _make_h_r(id_v2)
    if h_r_v1 == h_r_v2:
        return False, "H_r is identical across policy versions (it should differ)"

    return True, (
        f"id(P_v1)={id_v1[:8]}.. id(P_v2)={id_v2[:8]}.. → "
        f"H_c[v1]={h_c_v1[:8]}.. H_c[v2]={h_c_v2[:8]}.. → "
        f"H_r[v1]={h_r_v1[:8]}.. H_r[v2]={h_r_v2[:8]}.."
    )


def ev_pl_02_policy_signature_invalid() -> tuple[bool, str]:
    """EV-PL-02: tampered Policy signature → SignatureInvalid; wrong issuer
    → IssuerMismatch. Analogous to EV-FR-03 for FreshnessClaim."""
    import dataclasses as dc
    from ugk.governance import policy as P
    from ugk import freshness as F

    p = P.sign_policy(
        subjects=("jurisdiction:test",),
        decision_rules=("rule-a",),
        version="v1",
        issuer_key_id=F.DEFAULT_TEST_PUBKEY_HEX,
        signer_privkey_hex=F.DEFAULT_TEST_PRIVKEY_HEX,
    )
    # Sanity: original verifies
    ok, err = P.verify_policy(p, F.DEFAULT_TEST_PUBKEY_HEX)
    if not ok:
        return False, f"original Policy signature unexpectedly invalid: {err}"

    # (a) Tamper signature → SignatureInvalid
    bad_sig = dc.replace(p, signature=p.signature[:-2] + ("00" if p.signature[-2:] != "00" else "01"))
    ok, err = P.verify_policy(bad_sig, F.DEFAULT_TEST_PUBKEY_HEX)
    if ok or err != "SignatureInvalid":
        return False, f"tampered signature unexpectedly: ok={ok}, err={err!r}"

    # (b) Tamper subjects (sig stays) → SignatureInvalid (payload mismatch)
    bad_subj = dc.replace(p, subjects=("jurisdiction:attacker-injected",))
    ok, err = P.verify_policy(bad_subj, F.DEFAULT_TEST_PUBKEY_HEX)
    if ok or err != "SignatureInvalid":
        return False, f"tampered subjects unexpectedly: ok={ok}, err={err!r}"

    # (c) Wrong issuer pubkey → IssuerMismatch
    ok, err = P.verify_policy(p, "deadbeef" + "00" * 28)
    if ok or err != "IssuerMismatch":
        return False, f"wrong issuer unexpectedly: ok={ok}, err={err!r}"

    return True, "tampered signature → SignatureInvalid; tampered subjects → SignatureInvalid; wrong pubkey → IssuerMismatch"


# ─────────────────────────────────────────────────────────────────────────────
# M2.3f — Authority key vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_ak_01_authority_key_change_alters_h_j_and_h_r() -> tuple[bool, str]:
    """EV-AK-01: changing an authority's key identifier produces a different
    H_j (since c_j canonicalizes authority_key) and consequently a different
    H_r (since H_j is one of the merkle leaves), with all other receipt
    inputs held constant.

    Demonstrates that H_j now binds a governed authority key, not the
    authority name string. Pre-M2.3f, H_j would have been a function of
    the authority NAME; post-M2.3f, it is a function of the key ID, so
    swapping the key (without renaming the authority) shifts H_j.
    """
    from ugk import authority_keys as AK
    from ugk import freshness as F
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import (
        H_s, H_c, H_m, H_j, H_id_P, H_id_Sigma, H_id_Phi, compute_H_r,
        TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J,
        TAG_ID_P, TAG_ID_SIGMA, TAG_ID_PHI,
    )

    # Two different key identifiers for the same authority name
    k_a = "a" * 64  # 64-hex key id
    k_b = "b" * 64
    if k_a == k_b:
        return False, "test setup error: keys not distinct"

    def _make_h_j_and_h_r(authority_key_v: str):
        freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))
        # Hold ALL other inputs constant — only authority_key varies
        h_s = H_s("policy_evaluate", {"x": 1})
        h_c = H_c(["Operator"], "policy_id_fixed", [], ["W_1"],
                  "00" * 64, freshness)
        h_m = H_m("intent", "id://intent/1", "a" * 64, [],
                  semantic_regime_id=inv.ID_SIGMA_0)
        h_j = H_j(freshness["phase_code"], "0" * 64, "dkn_001", authority_key_v)
        leaves = [
            (TAG_H_S, h_s), (TAG_H_C, h_c),
            (TAG_H_M, h_m), (TAG_H_J, h_j),
            (TAG_ID_P,     H_id_P("policy_id_fixed")),
            (TAG_ID_SIGMA, H_id_Sigma(inv.ID_SIGMA_0)),
            (TAG_ID_PHI,   H_id_Phi(inv.ID_PHI_0)),
        ]
        return h_j.hex(), compute_H_r(leaves).hex()

    h_j_a, h_r_a = _make_h_j_and_h_r(k_a)
    h_j_b, h_r_b = _make_h_j_and_h_r(k_b)

    if h_j_a == h_j_b:
        return False, "H_j identical across distinct authority keys (it should differ)"
    if h_r_a == h_r_b:
        return False, "H_r identical across distinct authority keys (it should differ)"

    # Additional verification: pre-M2.3f-era would have used the authority
    # NAME directly. Demonstrate the move from name to key id.
    name_based_h_j, _ = _make_h_j_and_h_r("Operator")  # pre-M2.3f shape
    key_based_h_j, _  = _make_h_j_and_h_r(AK.derive_authority_key_id("Operator"))
    if name_based_h_j == key_based_h_j:
        return False, "M2.3f shift incomplete: name-based and key-id-based H_j coincide"

    return True, (
        f"H_j({k_a[:8]}..)={h_j_a[:8]}.. vs H_j({k_b[:8]}..)={h_j_b[:8]}..  →  "
        f"H_r differs; pre-M2.3f H_j('Operator')={name_based_h_j[:8]}.. "
        f"vs M2.3f H_j(key_id)={key_based_h_j[:8]}.."
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3h — G_c authority graph vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_gc_01_multi_hop_chain_alters_h_c_and_h_r() -> tuple[bool, str]:
    """EV-GC-01: a multi-hop authority chain produces different H_c and H_r
    values than a single-hop chain, even with the same terminal authority,
    because the c_c canonicalization commits to the full edge list."""
    from ugk import authority_graph as AG
    from ugk import freshness as F
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import (
        H_c, H_s, H_m, H_j, H_id_P, H_id_Sigma, H_id_Phi, compute_H_r,
        TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J,
        TAG_ID_P, TAG_ID_SIGMA, TAG_ID_PHI,
    )

    freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))

    def _make_h_c_and_h_r(chain):
        h_s = H_s("policy_evaluate", {"x": 1})
        h_c = H_c(authority_chain=chain, policy_id="fixed_pid",
                  capabilities=[], warrant_basis=["W_1"],
                  parent_H_r="00" * 64, freshness=freshness)
        h_m = H_m("intent", "id://intent/1", "a" * 64, [],
                  semantic_regime_id=inv.ID_SIGMA_0)
        h_j = H_j(freshness["phase_code"], "0" * 64, "dkn_001", "fixed_key")
        leaves = [
            (TAG_H_S, h_s), (TAG_H_C, h_c),
            (TAG_H_M, h_m), (TAG_H_J, h_j),
            (TAG_ID_P,     H_id_P("fixed_pid")),
            (TAG_ID_SIGMA, H_id_Sigma(inv.ID_SIGMA_0)),
            (TAG_ID_PHI,   H_id_Phi(inv.ID_PHI_0)),
        ]
        return h_c.hex(), compute_H_r(leaves).hex()

    # Setup A: single-hop Governor → JobRunner (default)
    AG.clear_graph()
    single_hop = AG.canonical_path_as_dicts("JobRunner")
    if len(single_hop) != 1:
        return False, f"single-hop setup error: expected 1 edge, got {len(single_hop)}"

    # Setup B: three-hop Governor → OpsRoot → DeployBot → JobRunner
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(issuer="Governor",  subject="OpsRoot"))
    AG.register_edge(AG.sign_authority_edge(issuer="OpsRoot",   subject="DeployBot"))
    AG.register_edge(AG.sign_authority_edge(issuer="DeployBot", subject="JobRunner"))
    multi_hop = AG.canonical_path_as_dicts("JobRunner")
    if len(multi_hop) != 3:
        return False, f"multi-hop setup error: expected 3 edges, got {len(multi_hop)}"

    # Verify both chains end-to-end (signatures + contiguity + rooting)
    ok_s, err_s = AG.verify_canonical_path(
        [AG.AuthorityEdge(**{k: tuple(v) if k == "capability_set" else v
                             for k, v in e.items()}) for e in single_hop],
        governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX,
    )
    # Reset and verify multi-hop via the live graph (avoids dict→dataclass round-trip)
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(issuer="Governor",  subject="OpsRoot"))
    AG.register_edge(AG.sign_authority_edge(issuer="OpsRoot",   subject="DeployBot"))
    AG.register_edge(AG.sign_authority_edge(issuer="DeployBot", subject="JobRunner"))
    path_objs = AG.canonical_path_for("JobRunner")
    ok_m, err_m = AG.verify_canonical_path(path_objs,
                                            governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX)
    if not (ok_s and ok_m):
        return False, f"path verification failed: single={err_s}, multi={err_m}"

    # Compute H_c and H_r under each chain shape — terminal authority identical
    h_c_single, h_r_single = _make_h_c_and_h_r(single_hop)
    h_c_multi,  h_r_multi  = _make_h_c_and_h_r(multi_hop)

    if h_c_single == h_c_multi:
        return False, "H_c identical for single-hop vs multi-hop chain (should differ)"
    if h_r_single == h_r_multi:
        return False, "H_r identical for single-hop vs multi-hop chain (should differ)"

    # Reset graph for downstream vector isolation
    AG.clear_graph()

    return True, (
        f"single-hop (1 edge): H_c={h_c_single[:10]}.. H_r={h_r_single[:10]}..  vs  "
        f"multi-hop (3 edges): H_c={h_c_multi[:10]}.. H_r={h_r_multi[:10]}..; "
        f"both paths verify end-to-end"
    )


def ev_gc_02_edge_expiry_detection() -> tuple[bool, str]:
    """EV-GC-02: an edge with a narrow validity window is admitted while
    current_time is inside the window and rejected with ExpiredEdge once
    current_time exceeds valid_until."""
    from ugk import authority_graph as AG
    from ugk import freshness as F

    AG.clear_graph()
    narrow_edge = AG.sign_authority_edge(
        issuer="Governor", subject="ShortLived",
        edge_time=0, valid_until=100,
    )
    AG.register_edge(narrow_edge)
    path = AG.canonical_path_for("ShortLived")

    # In-window
    ok_in, err_in = AG.verify_canonical_path(
        path, governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX, current_time=50,
    )
    if not ok_in:
        return False, f"in-window verification failed unexpectedly: {err_in}"

    # At-boundary (valid_until inclusive)
    ok_bd, err_bd = AG.verify_canonical_path(
        path, governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX, current_time=100,
    )
    if not ok_bd:
        return False, f"boundary verification (current_time=valid_until) failed: {err_bd}"

    # Past expiry
    ok_post, err_post = AG.verify_canonical_path(
        path, governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX, current_time=150,
    )
    if ok_post or err_post != "ExpiredEdge":
        return False, f"post-expiry should be ExpiredEdge, got ok={ok_post}, err={err_post}"

    # No time supplied → expiry check skipped, signature still verifies
    ok_no, err_no = AG.verify_canonical_path(
        path, governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX,
    )
    if not ok_no:
        return False, f"without current_time, verification should still pass: {err_no}"

    AG.clear_graph()
    return True, (
        f"valid_until=100; current_time=50 → ADMIT; current_time=100 → ADMIT (inclusive); "
        f"current_time=150 → ExpiredEdge; no current_time → ADMIT (sig-only)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3i — Capability attenuation vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_cp_01_legitimate_attenuation_binds_into_h_c() -> tuple[bool, str]:
    """EV-CP-01: legitimate attenuation along a multi-hop chain produces
    a smaller effective set at the terminus; the effective set propagates
    into H_c (different from same-chain with no attenuation)."""
    from ugk import authority_graph as AG
    from ugk import capabilities as CAP
    from ugk import freshness as F
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import (
        H_c, H_s, H_m, H_j, H_id_P, H_id_Sigma, H_id_Phi, compute_H_r,
        TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J,
        TAG_ID_P, TAG_ID_SIGMA, TAG_ID_PHI,
    )
    FULL = CAP.default_capability_set()  # full vocabulary

    # Setup A: 3-hop chain with progressive attenuation
    # Governor (FULL) → A (FULL) → B (evaluate,read,write) → C (read,write)
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="A", capability_set=FULL))
    AG.register_edge(AG.sign_authority_edge(
        issuer="A", subject="B", capability_set=("evaluate", "read", "write")))
    AG.register_edge(AG.sign_authority_edge(
        issuer="B", subject="C", capability_set=("read", "write")))
    path_att = AG.canonical_path_for("C")
    eff_att, err_att = CAP.compute_effective_capabilities(path_att)
    if err_att is not None or sorted(eff_att) != ["read", "write"]:
        return False, f"attenuation incorrect: eff={sorted(eff_att) if eff_att else None}, err={err_att}"

    chain_att = AG.canonical_path_as_dicts("C")

    # Setup B: same path TOPOLOGY but no attenuation (full set at every hop)
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="A", capability_set=FULL))
    AG.register_edge(AG.sign_authority_edge(
        issuer="A", subject="B", capability_set=FULL))
    AG.register_edge(AG.sign_authority_edge(
        issuer="B", subject="C", capability_set=FULL))
    path_full = AG.canonical_path_for("C")
    eff_full, _ = CAP.compute_effective_capabilities(path_full)
    chain_full = AG.canonical_path_as_dicts("C")

    # Construct H_c under each, with all other receipt inputs identical
    freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))

    def _h_c_and_h_r(chain_dicts, caps_list):
        h_s = H_s("policy_evaluate", {"x": 1})
        h_c = H_c(authority_chain=chain_dicts, policy_id="fixed_pid",
                  capabilities=caps_list, warrant_basis=["W_1"],
                  parent_H_r="00" * 64, freshness=freshness)
        h_m = H_m("intent", "id://intent/1", "a" * 64, [],
                  semantic_regime_id=inv.ID_SIGMA_0)
        h_j = H_j(freshness["phase_code"], "0" * 64, "dkn", "fixed_key")
        leaves = [
            (TAG_H_S, h_s), (TAG_H_C, h_c), (TAG_H_M, h_m), (TAG_H_J, h_j),
            (TAG_ID_P, H_id_P("fixed_pid")),
            (TAG_ID_SIGMA, H_id_Sigma(inv.ID_SIGMA_0)),
            (TAG_ID_PHI, H_id_Phi(inv.ID_PHI_0)),
        ]
        return h_c.hex(), compute_H_r(leaves).hex()

    h_c_att, h_r_att = _h_c_and_h_r(chain_att, ["read", "write"])
    h_c_full, h_r_full = _h_c_and_h_r(chain_full, sorted(FULL))

    if h_c_att == h_c_full:
        return False, "H_c identical for attenuated vs full chain (should differ)"
    if h_r_att == h_r_full:
        return False, "H_r identical for attenuated vs full chain (should differ)"

    AG.clear_graph()
    return True, (
        f"attenuated chain eff={sorted(eff_att)} → H_c={h_c_att[:10]}.., H_r={h_r_att[:10]}..; "
        f"full chain eff={sorted(eff_full)} → H_c={h_c_full[:10]}.., H_r={h_r_full[:10]}.."
    )


def ev_cp_02_capability_escalation_detection() -> tuple[bool, str]:
    """EV-CP-02: an edge claiming a capability absent from the parent's
    effective set produces CapabilityEscalation. Out-of-vocabulary
    capabilities are also caught via the same mechanism (Governor's set
    is exactly CAPABILITY_VOCABULARY)."""
    from ugk import authority_graph as AG
    from ugk import capabilities as CAP

    # (a) Sibling escalation: child claims write when parent only has read
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="ReadOnly", capability_set=("read",)))
    AG.register_edge(AG.sign_authority_edge(
        issuer="ReadOnly", subject="Sneaky", capability_set=("read", "write")))
    path = AG.canonical_path_for("Sneaky")
    eff, err = CAP.compute_effective_capabilities(path)
    if eff is not None or err != "CapabilityEscalation":
        return False, f"sibling escalation should be CapabilityEscalation: eff={eff}, err={err}"

    # (b) Out-of-vocabulary capability detected
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="X",
        capability_set=("read", "bogus_capability")))
    path = AG.canonical_path_for("X")
    eff, err = CAP.compute_effective_capabilities(path)
    if eff is not None or err != "CapabilityEscalation":
        return False, f"out-of-vocab should be CapabilityEscalation: eff={eff}, err={err}"

    # (c) attenuates() predicate direct
    if not CAP.attenuates({"read", "write"}, {"read"}):
        return False, "attenuates({r,w},{r}) should be True"
    if CAP.attenuates({"read"}, {"read", "write"}):
        return False, "attenuates({r},{r,w}) should be False"

    # (d) Combined verify also detects escalation
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="P", capability_set=("read",)))
    AG.register_edge(AG.sign_authority_edge(
        issuer="P", subject="Q", capability_set=("write",)))  # escalation
    path = AG.canonical_path_for("Q")
    from ugk import freshness as F
    eff, err = CAP.verify_authority_chain_with_capabilities(
        path, governor_pubkey_hex=F.DEFAULT_TEST_PUBKEY_HEX)
    if eff is not None or err != "CapabilityEscalation":
        return False, f"combined verify should detect escalation: eff={eff}, err={err}"

    AG.clear_graph()
    return True, (
        "sibling escalation, out-of-vocabulary capability, and parent-disjoint escalation "
        "all produce CapabilityEscalation; attenuates() predicate behaves correctly"
    )


def ev_cp_03_intermediate_hop_alters_h_c() -> tuple[bool, str]:
    """EV-CP-03: changing the capability_set on an intermediate edge of a
    multi-hop chain changes H_c — even when the TERMINAL effective set
    is identical — because the canonical authority_chain edge list itself
    is bound into c_c (each edge's signature differs when capability_set
    differs)."""
    from ugk import authority_graph as AG
    from ugk import capabilities as CAP
    from ugk import freshness as F
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import H_c

    freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))

    # Chain A: Governor (full) → M (read,write) → T (read)
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="M",
        capability_set=("read", "write")))
    AG.register_edge(AG.sign_authority_edge(
        issuer="M", subject="T",
        capability_set=("read",)))
    chain_A = AG.canonical_path_as_dicts("T")
    eff_A, _ = CAP.compute_effective_capabilities(AG.canonical_path_for("T"))

    # Chain B: Governor (full) → M (read,write,evaluate) → T (read)
    #   intermediate hop has different (broader) capability_set, but
    #   T's terminal effective set is still {read}
    AG.clear_graph()
    AG.register_edge(AG.sign_authority_edge(
        issuer="Governor", subject="M",
        capability_set=("evaluate", "read", "write")))
    AG.register_edge(AG.sign_authority_edge(
        issuer="M", subject="T",
        capability_set=("read",)))
    chain_B = AG.canonical_path_as_dicts("T")
    eff_B, _ = CAP.compute_effective_capabilities(AG.canonical_path_for("T"))

    # Terminal effective sets are identical
    if sorted(eff_A) != sorted(eff_B):
        return False, f"terminal sets should match: A={sorted(eff_A)}, B={sorted(eff_B)}"
    if sorted(eff_A) != ["read"]:
        return False, f"expected terminal {{read}}, got {sorted(eff_A)}"

    # But the chain dict lists differ (intermediate edge signatures differ)
    if chain_A == chain_B:
        return False, "chain dicts unexpectedly identical despite intermediate set change"

    # H_c with identical capabilities but different authority_chain → differs
    h_c_A = H_c(authority_chain=chain_A, policy_id="p",
                capabilities=sorted(eff_A), warrant_basis=[],
                parent_H_r="00" * 64, freshness=freshness).hex()
    h_c_B = H_c(authority_chain=chain_B, policy_id="p",
                capabilities=sorted(eff_B), warrant_basis=[],
                parent_H_r="00" * 64, freshness=freshness).hex()
    if h_c_A == h_c_B:
        return False, "H_c identical despite different intermediate edges"

    AG.clear_graph()
    return True, (
        f"terminal effective set identical ({sorted(eff_A)}) but intermediate "
        f"capability_set varied; H_c[A]={h_c_A[:10]}.. ≠ H_c[B]={h_c_B[:10]}.."
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3j — Semantic lineage vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_ln_01_lineage_chains_h_m_across_receipts() -> tuple[bool, str]:
    """EV-LN-01: H_m of a second receipt binds the first receipt's H_m
    via semantic_lineage; receipts with vs without lineage produce
    distinct H_m values; the chain is reconstructible from the receipt
    sequence."""
    from ugk import lineage as L
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import H_m

    # Receipt 1 (root): no prior → empty lineage
    lineage_root = L.lineage_as_dicts(L.build_lineage(None))
    h_m_1 = H_m("intent_1", "id://intent/1", "a" * 64,
                lineage_root, semantic_regime_id=inv.ID_SIGMA_0).hex()
    if lineage_root != []:
        return False, f"root lineage should be empty list, got {lineage_root}"

    # Receipt 2: lineage references receipt 1's H_m
    lineage_2 = L.lineage_as_dicts(L.build_lineage(h_m_1, "id://intent/1"))
    h_m_2 = H_m("intent_2", "id://intent/2", "a" * 64,
                lineage_2, semantic_regime_id=inv.ID_SIGMA_0).hex()

    # Verify structure
    if len(lineage_2) != 1:
        return False, f"second receipt lineage should be 1 edge, got {len(lineage_2)}"
    edge = lineage_2[0]
    if edge["parent_h_m"] != h_m_1:
        return False, f"lineage parent_h_m mismatch: {edge['parent_h_m']} vs {h_m_1}"
    if edge["edge_position"] != 0:
        return False, f"edge_position should be 0, got {edge['edge_position']}"

    # H_m of receipt 2 binds the lineage: compare with hypothetical
    # "receipt 2 with empty lineage" — same other inputs except for lineage
    h_m_2_no_lineage = H_m("intent_2", "id://intent/2", "a" * 64,
                            [], semantic_regime_id=inv.ID_SIGMA_0).hex()
    if h_m_2 == h_m_2_no_lineage:
        return False, "H_m with and without lineage unexpectedly identical"

    # Receipt 3: lineage references receipt 2's H_m
    lineage_3 = L.lineage_as_dicts(L.build_lineage(h_m_2, "id://intent/2"))
    h_m_3 = H_m("intent_3", "id://intent/3", "a" * 64,
                lineage_3, semantic_regime_id=inv.ID_SIGMA_0).hex()
    if lineage_3[0]["parent_h_m"] != h_m_2:
        return False, "receipt 3 lineage should reference receipt 2's H_m"

    return True, (
        f"chain reconstructed: receipt1.h_m={h_m_1[:10]}.. → "
        f"receipt2 lineage parent=receipt1.h_m → receipt2.h_m={h_m_2[:10]}.. → "
        f"receipt3 lineage parent=receipt2.h_m → receipt3.h_m={h_m_3[:10]}..; "
        f"lineage vs no-lineage H_m distinct ({h_m_2[:8]} vs {h_m_2_no_lineage[:8]})"
    )


def ev_ln_02_lineage_tampering_breaks_round_trip() -> tuple[bool, str]:
    """EV-LN-02: altering the parent_h_m reference in a lineage edge
    produces a different H_m, which breaks the H_r round-trip — this is
    the cryptographic anchoring that obviates the need for signed
    lineage edges."""
    from ugk import lineage as L
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import H_m

    # Legitimate chain
    h_m_parent = "a1b2c3d4" * 8  # 64-hex
    legit_lineage = L.lineage_as_dicts(L.build_lineage(h_m_parent, "id://parent"))
    legit_h_m = H_m("op", "id://child", "ff" * 32,
                    legit_lineage, semantic_regime_id=inv.ID_SIGMA_0).hex()

    # Tamper: change parent_h_m to a different hash (different "ancestor")
    tampered_parent = "deadbeef" * 8  # different 64-hex
    tampered_lineage = L.lineage_as_dicts(L.build_lineage(tampered_parent, "id://parent"))
    tampered_h_m = H_m("op", "id://child", "ff" * 32,
                       tampered_lineage, semantic_regime_id=inv.ID_SIGMA_0).hex()

    if legit_h_m == tampered_h_m:
        return False, "tampered parent_h_m unexpectedly produced same H_m"

    # Tamper: change parent_intent_ref (the human-readable provenance)
    intent_tampered_lineage = L.lineage_as_dicts(
        L.build_lineage(h_m_parent, "id://injected"))
    intent_tampered_h_m = H_m("op", "id://child", "ff" * 32,
                              intent_tampered_lineage,
                              semantic_regime_id=inv.ID_SIGMA_0).hex()
    if legit_h_m == intent_tampered_h_m:
        return False, "tampered parent_intent_ref unexpectedly produced same H_m"

    # Confirm root lineage is empty list
    empty_lineage = L.lineage_as_dicts(L.build_lineage(None))
    if empty_lineage != []:
        return False, "root receipt lineage should be empty list"
    root_h_m = H_m("op", "id://child", "ff" * 32,
                   empty_lineage, semantic_regime_id=inv.ID_SIGMA_0).hex()
    if root_h_m == legit_h_m:
        return False, "root H_m (empty lineage) unexpectedly matches lineaged H_m"

    return True, (
        f"legit H_m={legit_h_m[:10]}..; tampered-parent_h_m H_m={tampered_h_m[:10]}.. (distinct); "
        f"tampered-intent_ref H_m={intent_tampered_h_m[:10]}.. (distinct); "
        f"root (no lineage) H_m={root_h_m[:10]}.. (distinct); "
        f"any tampering breaks H_m → breaks H_r round-trip"
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3k — Namespace / mosaic_root vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_ns_01_mosaic_root_commits_to_namespace() -> tuple[bool, str]:
    """EV-NS-01: MOSAIC_ROOT_PHI_0 is the SHA-256 of canonical JSON of
    sorted NAMESPACE_PHI_0 entries; the value used in store/gate is
    independently reproducible from the constitutional namespace."""
    import hashlib, json
    from ugk import namespace as NS
    from ugk.invariants import NAMESPACE_PHI_0

    # Independent recomputation
    sorted_names = sorted(NAMESPACE_PHI_0)
    expected = hashlib.sha256(
        json.dumps(sorted_names, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    if expected != NS.MOSAIC_ROOT_PHI_0:
        return False, f"independent recompute mismatch: {expected} vs {NS.MOSAIC_ROOT_PHI_0}"

    # Membership predicate operational
    for name in sorted_names:
        if not NS.is_member(name):
            return False, f"declared name {name!r} reports non-member"
    if NS.is_member("op:nonexistent"):
        return False, "unknown name unexpectedly reports member"

    # Batch validation
    ok_all, _ = NS.validate_name_keys(sorted_names)
    if not ok_all:
        return False, "batch validation of all declared names failed"
    ok_mix, err_mix = NS.validate_name_keys(sorted_names + ["op:bogus"])
    if ok_mix or err_mix != "NamespaceNonMember":
        return False, f"mixed-validity batch should fail NamespaceNonMember; got ok={ok_mix}, err={err_mix}"

    return True, (
        f"MOSAIC_ROOT_PHI_0 = {NS.MOSAIC_ROOT_PHI_0[:16]}.. matches SHA-256 of "
        f"canonical JSON of {len(NAMESPACE_PHI_0)} sorted name_keys; "
        f"membership predicate and batch validation behave correctly"
    )


def ev_ns_02_namespace_change_alters_h_j_and_h_r() -> tuple[bool, str]:
    """EV-NS-02: extending the namespace changes mosaic_root; receipts
    constructed with the extended root produce different H_j (and
    therefore different H_r) than receipts under the canonical root.
    Demonstrates that namespace state is cryptographically time-stamped
    via H_j."""
    from ugk import namespace as NS
    from ugk import freshness as F
    from ugk import invariants as inv
    from ugk.storage.binding_m2 import H_j, H_s, H_c, H_m, H_id_P, H_id_Sigma, H_id_Phi, compute_H_r
    from ugk.storage.binding_m2 import (
        TAG_H_S, TAG_H_C, TAG_H_M, TAG_H_J,
        TAG_ID_P, TAG_ID_SIGMA, TAG_ID_PHI,
    )

    # Canonical root vs extended-namespace root
    extended_ns = set(inv.NAMESPACE_PHI_0) | {"op:experimental"}
    extended_root = NS.compute_mosaic_root(extended_ns)
    if extended_root == NS.MOSAIC_ROOT_PHI_0:
        return False, "extended namespace produced same root (impossible — distinct content)"

    # Build H_j under each root with all other inputs held constant
    freshness = F.build_freshness_claim_from_epoch(F.default_epoch(inv.ID_PHI_0))

    def _h_j_and_h_r(mosaic_root_v):
        h_s = H_s("policy_evaluate", {"x": 1})
        h_c = H_c(authority_chain=[], policy_id="fixed_pid",
                  capabilities=[], warrant_basis=["W"],
                  parent_H_r="00" * 64, freshness=freshness)
        h_m = H_m("intent", "id://intent/1", "a" * 64, [],
                  semantic_regime_id=inv.ID_SIGMA_0)
        h_j = H_j(freshness["phase_code"], mosaic_root_v, "dkn_001", "fixed_key")
        leaves = [
            (TAG_H_S, h_s), (TAG_H_C, h_c),
            (TAG_H_M, h_m), (TAG_H_J, h_j),
            (TAG_ID_P,     H_id_P("fixed_pid")),
            (TAG_ID_SIGMA, H_id_Sigma(inv.ID_SIGMA_0)),
            (TAG_ID_PHI,   H_id_Phi(inv.ID_PHI_0)),
        ]
        return h_j.hex(), compute_H_r(leaves).hex()

    h_j_canonical, h_r_canonical = _h_j_and_h_r(NS.MOSAIC_ROOT_PHI_0)
    h_j_extended,  h_r_extended  = _h_j_and_h_r(extended_root)

    if h_j_canonical == h_j_extended:
        return False, "H_j identical across distinct mosaic_roots (impossible)"
    if h_r_canonical == h_r_extended:
        return False, "H_r identical across distinct mosaic_roots (impossible)"

    # Also exercise the placeholder mosaic_root="0"*64 (M2.2 era) to show
    # the shift from placeholder to governed root
    h_j_placeholder, h_r_placeholder = _h_j_and_h_r("0" * 64)
    if h_j_placeholder == h_j_canonical:
        return False, "placeholder M2.2 root produced same H_j as governed root (impossible)"

    return True, (
        f"NAMESPACE_PHI_0 ({len(inv.NAMESPACE_PHI_0)} entries) → root {NS.MOSAIC_ROOT_PHI_0[:10]}..; "
        f"extended (+1 entry) → root {extended_root[:10]}..; H_j[canonical]={h_j_canonical[:10]}.. "
        f"≠ H_j[extended]={h_j_extended[:10]}.. ≠ H_j[M2.2-placeholder]={h_j_placeholder[:10]}.."
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3l — Decision-procedure boundary vectors (EV-N series activation)
# ─────────────────────────────────────────────────────────────────────────────
# These vectors were deferred from M2.1 (REV3 Appendix C boundary vectors)
# until decision-procedure machinery existed. M2.3l activates them.

def ev_n01_expired_edge_in_d_c_full_form() -> tuple[bool, str]:
    """EV-N01: D_c on a receipt whose authority chain contains an expired
    edge, with current_time > edge.valid_until, produces ExpiredEdge.

    Constructs a deliberately-narrow-window edge in the default graph,
    builds a receipt under that authority, then runs D_c with
    current_time past the expiry boundary.
    """
    from ugk.kernel import GovernanceKernel
    from ugk import authority_graph as AG
    from ugk import decision as D
    from ugk import freshness as F

    # Setup: clear graph + register narrow-window edge for a fresh authority
    AG.clear_graph()
    narrow_edge = AG.sign_authority_edge(
        issuer="Governor", subject="ShortLivedAuth",
        capability_set=("attest", "bind", "evaluate", "read", "write"),
        edge_time=0, valid_until=100,  # narrow window
    )
    AG.register_edge(narrow_edge)

    # Build a receipt under that authority — store.write uses the
    # registered (expiring) edge for authority_chain in H_c
    k = GovernanceKernel()
    k.open_session()
    k.execute(op="crp_evidence", authority="ShortLivedAuth",
              parameters={"test": "ev_n01"})
    receipts = k.store.all_receipts()
    # Find a receipt with the expiring authority
    target = next((r for r in receipts if r.authority == "ShortLivedAuth"), None)
    if target is None:
        AG.clear_graph()
        return False, "could not locate receipt with ShortLivedAuth"

    # In-window: D_c with current_time=50 should pass (signature + structure ok)
    ok_in, err_in = D.D_c(target, current_time=50)
    if not ok_in:
        AG.clear_graph()
        return False, f"in-window D_c failed unexpectedly: err={err_in}"

    # Past-expiry: D_c with current_time=150 should produce ExpiredEdge
    ok_post, err_post = D.D_c(target, current_time=150)
    AG.clear_graph()
    if ok_post:
        return False, "D_c with current_time>valid_until unexpectedly passed"
    if err_post != "ExpiredEdge":
        return False, f"expected ExpiredEdge, got err={err_post!r}"

    return True, (
        f"D_c with current_time=50 (in-window) → PASS; "
        f"D_c with current_time=150 (past valid_until=100) → ExpiredEdge"
    )


def ev_n02_namespace_non_member_via_d_j() -> tuple[bool, str]:
    """EV-N02: D_j in strict_namespace mode rejects a receipt whose op
    is not in NAMESPACE_PHI_0 with NamespaceNonMember.

    Three scenarios:
      (a) Receipt with op:crp_evidence (NOT in M_Phi) under strict mode
          → NamespaceNonMember
      (b) Same receipt under permissive mode (default) → PASS
      (c) Receipt with op:policy_evaluate (IN M_Phi) under strict mode
          → PASS (op is a member)

    Note: receipts are constructed via UGKReceiptStore.write directly
    (not kernel.execute) to bypass governance-status gating on certain
    ops — decision procedures operate on receipt objects irrespective
    of the kernel that produced them.
    """
    from ugk.storage.store import UGKReceiptStore
    from ugk import authority_graph as AG
    from ugk import decision as D
    from ugk import invariants as inv

    AG.clear_graph()
    LH = "064f7476e01f16b69ebb33a11244d6fb3d8d639b05c958573f7d6c080b191246"
    LEG = "a7e2a9c9fdc2e73c403f5b191a3e84fcda06071dc2790606d8f0e2e4516552ff"
    store = UGKReceiptStore(":memory:")
    crp = store.write(op="crp_evidence", authority="ev_n02_auth",
                       parameters={"i": 1}, intent="test_n02_crp",
                       jurisdiction="production", session_dkn="dkn_n02_1",
                       law_hash=LH, legend_hash=LEG, warrant_id="W_n02_1",
                       intent_ref="id://intent/n02/1")
    pol = store.write(op="policy_evaluate", authority="ev_n02_auth",
                       parameters={"i": 2}, intent="test_n02_pol",
                       jurisdiction="production", session_dkn="dkn_n02_2",
                       law_hash=LH, legend_hash=LEG, warrant_id="W_n02_2",
                       intent_ref="id://intent/n02/2")

    # (a) op:crp_evidence under strict mode → NamespaceNonMember
    ok, err = D.D_j(crp, strict_namespace=True)
    if ok or err != "NamespaceNonMember":
        AG.clear_graph()
        return False, f"(a) op:crp_evidence strict mode: expected NamespaceNonMember, got ok={ok}, err={err}"

    # (b) op:crp_evidence permissive (default) → PASS
    ok, err = D.D_j(crp, strict_namespace=False)
    if not ok or err is not None:
        AG.clear_graph()
        return False, f"(b) op:crp_evidence permissive: expected PASS, got ok={ok}, err={err}"

    # (c) op:policy_evaluate strict mode → PASS (in NAMESPACE_PHI_0)
    ok, err = D.D_j(pol, strict_namespace=True)
    if not ok or err is not None:
        AG.clear_graph()
        return False, f"(c) op:policy_evaluate strict mode: expected PASS, got ok={ok}, err={err}"

    # Explicit name_keys override path: provide a NON-MEMBER name explicitly
    ok, err = D.D_j(pol, strict_namespace=True,
                    name_keys_to_check=["op:policy_evaluate", "user:eve"])
    if ok or err != "NamespaceNonMember":
        AG.clear_graph()
        return False, f"explicit name_keys override: expected NamespaceNonMember, got ok={ok}, err={err}"

    AG.clear_graph()
    return True, (
        "op:crp_evidence under strict → NamespaceNonMember; "
        "op:crp_evidence under permissive → PASS; "
        "op:policy_evaluate under strict → PASS; "
        "explicit name_keys with non-member → NamespaceNonMember"
    )


# ─────────────────────────────────────────────────────────────────────────────
# M2.3m — Witness opening vectors
# ─────────────────────────────────────────────────────────────────────────────

def ev_w_01_open_verify_all_strict_mode_leaves() -> tuple[bool, str]:
    """EV-W-01: construct and verify a witness for each of the 7
    strict-mode leaves of a real receipt; all verifications pass."""
    from ugk.storage.store import UGKReceiptStore
    from ugk.storage import binding_m2 as m2
    from ugk import authority_graph as AG
    from ugk import witness as W

    AG.clear_graph()
    LH = "064f7476e01f16b69ebb33a11244d6fb3d8d639b05c958573f7d6c080b191246"
    LEG = "a7e2a9c9fdc2e73c403f5b191a3e84fcda06071dc2790606d8f0e2e4516552ff"
    store = UGKReceiptStore(":memory:")
    r = store.write(op="policy_evaluate", authority="EV_W_01_Auth",
                     parameters={"x": 1}, intent="ev_w_01",
                     jurisdiction="production", session_dkn="dkn_w01",
                     law_hash=LH, legend_hash=LEG, warrant_id="W_w01",
                     intent_ref="id://intent/w/01")

    tags = [m2.TAG_H_S, m2.TAG_H_C, m2.TAG_H_M, m2.TAG_H_J,
            m2.TAG_ID_P, m2.TAG_ID_SIGMA, m2.TAG_ID_PHI]
    for tag in tags:
        wit = W.construct_witness(r, tag)
        ok, err = W.verify_witness(wit)
        if not ok:
            AG.clear_graph()
            return False, f"witness for leaf_tag={tag}: ok={ok}, err={err}"
        # Each strict-mode tree of 7 leaves has path depth 3 (ceil(log2(7))=3)
        if len(wit.inclusion_path) != 3:
            AG.clear_graph()
            return False, f"unexpected path length for leaf_tag={tag}: {len(wit.inclusion_path)}"

    AG.clear_graph()
    return True, (
        f"all 7 strict-mode leaves (H_s, H_c, H_m, H_j, id_P, id_Sigma, id_Phi) "
        f"open + verify with inclusion path depth 3"
    )


def ev_w_02_witness_tamper_detection() -> tuple[bool, str]:
    """EV-W-02: tampering with any of (opened_input, inclusion_path
    sibling, claimed H_r) breaks witness verification, demonstrating
    the merkle integrity guarantee."""
    import dataclasses as dc
    from ugk.storage.store import UGKReceiptStore
    from ugk.storage import binding_m2 as m2
    from ugk import authority_graph as AG
    from ugk import witness as W

    AG.clear_graph()
    LH = "064f7476e01f16b69ebb33a11244d6fb3d8d639b05c958573f7d6c080b191246"
    LEG = "a7e2a9c9fdc2e73c403f5b191a3e84fcda06071dc2790606d8f0e2e4516552ff"
    store = UGKReceiptStore(":memory:")
    r = store.write(op="policy_evaluate", authority="EV_W_02_Auth",
                     parameters={"x": 2}, intent="ev_w_02",
                     jurisdiction="production", session_dkn="dkn_w02",
                     law_hash=LH, legend_hash=LEG, warrant_id="W_w02",
                     intent_ref="id://intent/w/02")

    wit_hs = W.construct_witness(r, m2.TAG_H_S)
    # Baseline: untampered verifies
    ok, err = W.verify_witness(wit_hs)
    if not ok:
        AG.clear_graph()
        return False, f"baseline witness failed: ok={ok}, err={err}"

    # (a) Tamper opened_input — substitute op
    tamper_a = dc.replace(wit_hs, opened_input={"op": "injected", "parameters": {}})
    ok, err = W.verify_witness(tamper_a)
    if ok or err != "NonCanonical":
        AG.clear_graph()
        return False, f"(a) tampered opened_input: expected NonCanonical, got ok={ok}, err={err}"

    # (b) Tamper inclusion_path sibling — replace first sibling with garbage
    wit_hc = W.construct_witness(r, m2.TAG_H_C)
    bad_sibling = bytes.fromhex("de" * 32)
    bad_path = [(bad_sibling, wit_hc.inclusion_path[0][1])] + list(wit_hc.inclusion_path[1:])
    tamper_b = dc.replace(wit_hc, inclusion_path=bad_path)
    ok, err = W.verify_witness(tamper_b)
    if ok or err != "NonCanonical":
        AG.clear_graph()
        return False, f"(b) tampered sibling: expected NonCanonical, got ok={ok}, err={err}"

    # (c) Tamper claimed H_r — substitute a different root
    tamper_c = dc.replace(wit_hs, h_r_claimed="ff" * 32)
    ok, err = W.verify_witness(tamper_c)
    if ok or err != "NonCanonical":
        AG.clear_graph()
        return False, f"(c) tampered H_r: expected NonCanonical, got ok={ok}, err={err}"

    # (d) Tamper side flag in inclusion_path — flip L/R on one sibling
    if wit_hc.inclusion_path:
        first_sib, first_side = wit_hc.inclusion_path[0]
        flipped = "L" if first_side == "R" else "R"
        flipped_path = [(first_sib, flipped)] + list(wit_hc.inclusion_path[1:])
        tamper_d = dc.replace(wit_hc, inclusion_path=flipped_path)
        ok, err = W.verify_witness(tamper_d)
        if ok or err != "NonCanonical":
            AG.clear_graph()
            return False, f"(d) flipped side flag: expected NonCanonical, got ok={ok}, err={err}"

    AG.clear_graph()
    return True, (
        "tampered opened_input → NonCanonical; tampered sibling → NonCanonical; "
        "tampered H_r → NonCanonical; flipped path side → NonCanonical"
    )


def ev_n04_under_recorded_collapse() -> tuple[bool, str]:
    """EV-N04: UnderRecordedCollapse activates when a context-external mode
    receipt is presented without any required witness (neither recovery
    nor collapse). Completes the EV-N* boundary vector series.

    Per REV3 §4.5: context-external mode omits identity leaves
    (id_P/id_Sigma/id_Phi); admissibility then requires external witnesses
    to bind the receipt's identity claims. When BOTH the recovery witness
    and collapse witness are absent, UnderRecordedCollapse fires.
    """
    from ugk import witness as W
    from ugk.storage.store import UGKReceiptStore
    from ugk.storage import binding_m2 as m2
    from ugk import authority_graph as AG

    # (a) Strict mode never triggers UnderRecordedCollapse (identity leaves
    #     are in-tree).
    ok, err = W.verify_well_recorded(W.MODE_STRICT)
    if not ok or err is not None:
        return False, f"(a) strict mode should always pass: ok={ok}, err={err}"

    # (b) Context-external mode with NO witnesses → UnderRecordedCollapse
    ok, err = W.verify_well_recorded(W.MODE_CONTEXT_EXTERNAL)
    if ok or err != "UnderRecordedCollapse":
        return False, f"(b) context-external + no witnesses: expected UnderRecordedCollapse, got ok={ok}, err={err}"

    # (c) Context-external mode with explicit None witnesses → same
    ok, err = W.verify_well_recorded(W.MODE_CONTEXT_EXTERNAL,
                                      witnesses={"recovery": None, "collapse": None})
    if ok or err != "UnderRecordedCollapse":
        return False, f"(c) context-external + explicit Nones: expected UnderRecordedCollapse, got ok={ok}, err={err}"

    # (d) Context-external + recovery witness only → PASS (witness covers
    #     identity disclosure requirement)
    AG.clear_graph()
    LH = "064f7476e01f16b69ebb33a11244d6fb3d8d639b05c958573f7d6c080b191246"
    LEG = "a7e2a9c9fdc2e73c403f5b191a3e84fcda06071dc2790606d8f0e2e4516552ff"
    store = UGKReceiptStore(":memory:")
    r = store.write(op="policy_evaluate", authority="EV_N04_Auth",
                     parameters={"x": 4}, intent="ev_n04",
                     jurisdiction="production", session_dkn="dkn_n04",
                     law_hash=LH, legend_hash=LEG, warrant_id="W_n04",
                     intent_ref="id://intent/n/04")
    recovery_wit = W.construct_witness(r, m2.TAG_ID_P)
    ok, err = W.verify_well_recorded(W.MODE_CONTEXT_EXTERNAL,
                                      witnesses={"recovery": recovery_wit})
    if not ok or err is not None:
        AG.clear_graph()
        return False, f"(d) context-external + recovery witness: expected PASS, got ok={ok}, err={err}"

    # (e) Context-external + collapse witness only → PASS (either witness suffices)
    collapse_wit = W.construct_witness(r, m2.TAG_H_J)
    ok, err = W.verify_well_recorded(W.MODE_CONTEXT_EXTERNAL,
                                      witnesses={"collapse": collapse_wit})
    if not ok or err is not None:
        AG.clear_graph()
        return False, f"(e) context-external + collapse witness: expected PASS, got ok={ok}, err={err}"

    # (f) Both witnesses verifiable against H_r
    ok_r, err_r = W.verify_witness(recovery_wit)
    ok_c, err_c = W.verify_witness(collapse_wit)
    if not ok_r or not ok_c:
        AG.clear_graph()
        return False, f"(f) witnesses themselves should verify: recovery={ok_r}, collapse={ok_c}"

    AG.clear_graph()
    return True, (
        "strict mode → PASS; context-external + no witnesses → UnderRecordedCollapse; "
        "context-external + recovery only → PASS; context-external + collapse only → PASS; "
        "both witnesses verify against H_r"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

VECTORS: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("EV-001 primary",                              ev_001_primary),
    ("EV-D01 determinism same-input",               ev_d01_determinism_same_input),
    ("EV-D02 determinism fresh-process",            ev_d02_determinism_fresh_process),
    ("EV-D03 global nonrepudiation summary",        ev_d03_per_leaf_independence_summary),
    # EV-I01..EV-I06 reduced form — cryptographic-independence half of THR §11.
    # Six ordered pairs (i, j) over core commitments {s, c, m}.
    # Full decisional independence (D_i=1, D_j=0) requires decision procedures
    # that land at M2.3.
    ("EV-I01-reduced: perturb c_s → H_s↕, H_c=",   lambda: _ev_pairwise_independence("s", "c")),
    ("EV-I02-reduced: perturb c_s → H_s↕, H_m=",   lambda: _ev_pairwise_independence("s", "m")),
    ("EV-I03-reduced: perturb c_c → H_c↕, H_s=",   lambda: _ev_pairwise_independence("c", "s")),
    ("EV-I04-reduced: perturb c_c → H_c↕, H_m=",   lambda: _ev_pairwise_independence("c", "m")),
    ("EV-I05-reduced: perturb c_m → H_m↕, H_s=",   lambda: _ev_pairwise_independence("m", "s")),
    ("EV-I06-reduced: perturb c_m → H_m↕, H_c=",   lambda: _ev_pairwise_independence("m", "c")),
    ("EV-MS-3 merkle worked example (3 leaves)",    lambda: ev_ms_n_leaves(3)),
    ("EV-MS-4 merkle worked example (4 leaves)",    lambda: ev_ms_n_leaves(4)),
    ("EV-MS-6 merkle worked example (6 leaves)",    lambda: ev_ms_n_leaves(6)),
    ("EV-MS-7 merkle worked example (7 leaves)",    lambda: ev_ms_n_leaves(7)),
    ("EV-N05 NotYetAdmissible boundary",            ev_n05_not_yet_admissible),
    ("EV-CM-01 registered principled redundancy",   ev_cm_01_registered_principled_redundancy),
    ("EV-CM-02 unregistered redundancy rejected",   ev_cm_02_unregistered_redundancy),
    ("EV-AV-001 strict-mode self-describing id",    ev_av_001_strict_mode_self_describing_identity),
    # M2.3e freshness vectors — Governor-signed epoch infrastructure
    ("EV-FR-01 valid epoch (in-window verify)",     ev_fr_01_valid_epoch),
    ("EV-FR-02 expired epoch (ExpiredEdge)",        ev_fr_02_expired_epoch),
    ("EV-FR-03 invalid signature (SignatureInvalid)", ev_fr_03_invalid_signature),
    ("EV-FR-04 epoch transition",                   ev_fr_04_epoch_transition),
    # M2.3g policy vectors — Governor-signed Policy artifacts + id(P) integration
    ("EV-PL-01 policy version → H_c, H_r differ",   ev_pl_01_policy_version_changes_h_c_and_h_r),
    ("EV-PL-02 policy signature invalid",           ev_pl_02_policy_signature_invalid),
    # M2.3f authority-key vector — authority_key now governed identifier
    ("EV-AK-01 authority-key change → H_j, H_r differ", ev_ak_01_authority_key_change_alters_h_j_and_h_r),
    # M2.3h G_c authority graph vectors — canonical path through G_c
    ("EV-GC-01 multi-hop chain → H_c, H_r differ",  ev_gc_01_multi_hop_chain_alters_h_c_and_h_r),
    ("EV-GC-02 edge expiry detection",              ev_gc_02_edge_expiry_detection),
    # M2.3i capability attenuation vectors — effective set binds into H_c
    ("EV-CP-01 legitimate attenuation → H_c, H_r", ev_cp_01_legitimate_attenuation_binds_into_h_c),
    ("EV-CP-02 capability escalation detection",   ev_cp_02_capability_escalation_detection),
    ("EV-CP-03 intermediate hop alters H_c",        ev_cp_03_intermediate_hop_alters_h_c),
    # M2.3j semantic lineage vectors — H_m chain binding
    ("EV-LN-01 lineage chains H_m across receipts", ev_ln_01_lineage_chains_h_m_across_receipts),
    ("EV-LN-02 lineage tampering breaks H_m",       ev_ln_02_lineage_tampering_breaks_round_trip),
    # M2.3k namespace / mosaic_root vectors — H_j commitment to M_Phi
    ("EV-NS-01 mosaic_root commits to namespace",   ev_ns_01_mosaic_root_commits_to_namespace),
    ("EV-NS-02 namespace change → H_j, H_r differ", ev_ns_02_namespace_change_alters_h_j_and_h_r),
    # M2.3l decision-procedure boundary vectors — EV-N series activation
    ("EV-N01 ExpiredEdge via D_c full form",        ev_n01_expired_edge_in_d_c_full_form),
    ("EV-N02 NamespaceNonMember via D_j",           ev_n02_namespace_non_member_via_d_j),
    # M2.3m witness opening + final EV-N* completion
    ("EV-W-01 open + verify all 7 strict leaves",  ev_w_01_open_verify_all_strict_mode_leaves),
    ("EV-W-02 witness tamper detection",            ev_w_02_witness_tamper_detection),
    ("EV-N04 UnderRecordedCollapse (context-ext.)", ev_n04_under_recorded_collapse),
]


def main() -> int:
    print(f"Phase M2.1 executable vector runner")
    print(f"=" * 76)
    n_pass = 0
    n_fail = 0
    for name, fn in VECTORS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        verdict = "PASS" if ok else "FAIL"
        print(f"  {verdict}  {name:50}  {detail}")
        if ok:
            n_pass += 1
        else:
            n_fail += 1
    print(f"=" * 76)
    print(f"  {n_pass}/{len(VECTORS)} passed  |  {n_fail} failed")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
