# Verifier Boundary Note (R3 closure — boundary clarification)

**Status:** architectural boundary, not a defect. Closes Thread B R3 as documentation.

The continuity proof harness (`tools/grbsa/proof_model_b.py`, "Proof Model B") is **intentionally
Governor-verified out-of-band**. The system does **not** claim to verify its own verifier.

- The **conformance suite** (83 gates) verifies the constitutional substrate from within the artifact.
- The **continuity harness** (Proof Model B) verifies cross-release continuity. It is run
  **independently by the Governor**, and its verdict is checked by the Governor — it is not
  self-certified by the system.
- "Who verifies the verifier" is answered by the Governor, deliberately and explicitly. A system that
  certified its own verifier would be making an unfounded self-referential trust claim; UGK does not.

This boundary is a design property of the Governor/Coder protocol, not a protection gap. Proof Model B
is therefore not in the Grundnorm read-only set and is not required to be — its integrity to the
Governor comes from being deterministic, auditable, and independently re-runnable, not from file mode.
