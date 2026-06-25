"""grbsa_runtime — GRBSA G3 runtime (GateAdapter beachhead). Imports ugk read-only; no ugk/ object."""
from .gate_adapter import (
    GateAdapter, GateReceipt, GateResultEnvelope, ReceiptCore, ResultEnvelopeCore,
    gate_success, PostureRefusal, verdict_tuple_normalizer,
)
from .projection_adapter import (
    ProjectionAdapter, ProjectionReceipt, ProjectionResultEnvelope, projection_success,
)
from .explain_adapter import (
    ExplainAdapter, ExplainReceipt, ExplainResultEnvelope, explain_success,
)
from .execution_adapter import (
    ExecutionAdapter, ExecutionReceipt, ExecutionResultEnvelope, execution_success,
)

__all__ = [
    "GateAdapter", "GateReceipt", "GateResultEnvelope", "ReceiptCore", "ResultEnvelopeCore",
    "gate_success", "PostureRefusal", "verdict_tuple_normalizer",
    "ProjectionAdapter", "ProjectionReceipt", "ProjectionResultEnvelope", "projection_success",
    "ExplainAdapter", "ExplainReceipt", "ExplainResultEnvelope", "explain_success",
    "ExecutionAdapter", "ExecutionReceipt", "ExecutionResultEnvelope", "execution_success",
]
