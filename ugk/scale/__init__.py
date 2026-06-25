"""ugk.scale — OPT-IN scale-lane subsystem (DORMANT by default).

This subsystem is integrated infrastructure, NOT default behavior:
  - ugk/__init__.py does NOT import this package on the default path.
  - execute() is unchanged and never calls into here.
  - the single commit lane remains canonical; one receipt per governed operation holds.
  - all scheduler/control actions are receipted under I5 (see scheduler.py).
  - the dependency oracle is conservative: empty/negative declarations are NOT evidence
    (earned-independence rule); unknown ⇒ dependent.

Enablement is explicit and opt-in, mirroring the A1 / rho dormant-capability pattern. A
deployment that does not enable scale pays nothing on the execution path; the modules simply
sit inert in the tree.

Usage (opt-in only):
    from ugk.scale import ScalePosture, is_enabled
    posture = ScalePosture(scale_enabled=True)   # deployment-gated decision
    if is_enabled(posture):
        from ugk.scale.scheduler import GovernedScheduler
        ...
"""
from dataclasses import dataclass

@dataclass
class ScalePosture:
    """Opt-in scale-lane posture. Dormant by default (scale_enabled=False).

    Like A1Posture / RhoPosture: the subsystem does nothing unless a deployment explicitly
    opts in. Integration adds the capability; it does not authorize or impose its use.
    """
    scale_enabled: bool = False

def is_enabled(posture: "ScalePosture") -> bool:
    """True only when a deployment has explicitly opted into the scale lane."""
    return bool(getattr(posture, "scale_enabled", False))

__all__ = ["ScalePosture", "is_enabled"]
