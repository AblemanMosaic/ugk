"""ugk/conformance — conformance gates (78 total; + 39 M2 vectors).

Gates implement run() -> (status, str). status is tri-state:
  - True             PASS  — the gate's proposition holds.
  - False            FAIL  — the proposition is violated.
  - NOT_ESTABLISHED        — the proposition has an unmet PRECONDITION and no
                             pass/fail claim is asserted (e.g. an integrity gate
                             over a posture that was never established). This is
                             NEITHER pass nor fail; the batch reports it as a
                             distinct bucket so "not established" is never folded
                             into either outcome.
Self-contained (temp dbs). Batch via run_gates_batch.py (single interpreter,
os._exit finisher, three-bucket reporting).
"""

# Tri-state sentinel shared by tri-state gates and the batch runner. A distinct
# string (not a bool) so the batch can classify it explicitly; the batch counts
# "passed" with `status is True` so this value can never be mis-tallied as a pass.
NOT_ESTABLISHED = "NOT_ESTABLISHED"
