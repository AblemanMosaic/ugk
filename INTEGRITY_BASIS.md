# Integrity Basis Note (R4 closure — integrity clarification)

**Status:** integrity is cryptographic, not file-mode. Closes Thread B R4 as documentation.

Amendment-ledger and genesis-anchor integrity derive from cryptography and gate-enforced checks, not
from file permissions:

- **Signed records** — every `AmendmentRecord` carries an Ed25519 Governor signature over its canonical
  body; tampering breaks the signature (`is_admissible` condition 3, era-aware).
- **Genesis anchoring** — the genesis amendment is pinned by `amendment_admissibility_gate`
  (`startswith 5fe68bbc`) and bound by the genesis seal (`validate_genesis_seal`); an alternate genesis
  fails the gate.
- **Lineage validation** — append-only `prior → successor` law-hash lineage plus `existing_successors`
  (no duplicate successor) is enforced on every admission.
- **Admissibility checks** — the 83-gate suite enforces these properties on every release.

**File permissions are operational posture, not the primary trust basis.** Runtime `0o444` enforcement
(`ugk harden`) applies to **Grundnorm modules** (constitutional code/invariants/roots), not to arbitrary
data artifacts. The amendment ledger is **evidence of constitutional history, not constitutional law**;
promoting it into the Grundnorm set would change the meaning of UL-G-01 to solve a problem already
solved by signatures and lineage. Note also that packaging strips file modes (pip: `0o444 → 0o644`),
so file mode is not a transferable trust property; the cryptographic basis above is.
