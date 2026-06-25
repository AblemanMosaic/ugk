"""ugk/gate_probe.py — ALT §10 removal test: constitutive gate probing (444).

ALT-I-01: ConstitutiveProbeResult is content-addressed.
          CONSTITUTIVE: gate refused at least one tested input.
          CEREMONIAL: gate admitted all inputs — a named, located governance gap.
          UNPROBED: no refusing_inputs supplied.
ALT-I-04: phi_score() computes φ(S) = ceremonial ops / total APPLICATION_OPs.
"""
from __future__ import annotations
import hashlib, time
from dataclasses import dataclass
from typing import Optional
from ugk.storage.binding import canonical_json as _cj

CONSTITUTIVE="CONSTITUTIVE"; CEREMONIAL="CEREMONIAL"; UNPROBED="UNPROBED"

@dataclass(frozen=True)
class ConstitutiveProbeResult:
    result_hash:str; op:str; status:str
    refusing_inputs_tested:int; all_refused:bool; timestamp:str

    def verify_hash(self):
        body={"all_refused":self.all_refused,"op":self.op,
              "refusing_inputs_tested":self.refusing_inputs_tested,
              "status":self.status,"timestamp":self.timestamp}
        return hashlib.sha256(_cj(body)).hexdigest()==self.result_hash


def probe_constitutive(op,kernel,refusing_inputs=None):
    """Run the ALT §10 removal test. refusing_inputs: list of dicts, each may
    contain __gate__ key mapping to a callable returning bool."""
    ts=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
    if not refusing_inputs:
        body={"all_refused":False,"op":op,"refusing_inputs_tested":0,"status":UNPROBED,"timestamp":ts}
        return ConstitutiveProbeResult(result_hash=hashlib.sha256(_cj(body)).hexdigest(),
            op=op,status=UNPROBED,refusing_inputs_tested=0,all_refused=False,timestamp=ts)
    refused=0
    for params in refusing_inputs:
        gate_fn=params.pop("__gate__",None) if isinstance(params,dict) else None
        if gate_fn is not None and not gate_fn():
            refused+=1
    all_refused=(refused==len(refusing_inputs))
    status=CONSTITUTIVE if refused>0 else CEREMONIAL
    body={"all_refused":all_refused,"op":op,"refusing_inputs_tested":len(refusing_inputs),
          "status":status,"timestamp":ts}
    return ConstitutiveProbeResult(result_hash=hashlib.sha256(_cj(body)).hexdigest(),
        op=op,status=status,refusing_inputs_tested=len(refusing_inputs),
        all_refused=all_refused,timestamp=ts)


def phi_score(governance_ops,op_probe_results=None):
    """φ(S) = fraction of APPLICATION_OPs that are ceremonial or unprobed."""
    from ugk.schema import _KERNEL_OPS,_UNIVERSAL_OPS
    app_ops=[op for op in governance_ops if op not in _KERNEL_OPS and op not in _UNIVERSAL_OPS]
    if not app_ops: return 0.0
    ceremonial=0
    for op in app_ops:
        if op_probe_results and op in op_probe_results:
            if op_probe_results[op].status==CEREMONIAL: ceremonial+=1
        else:
            ceremonial+=1
    return ceremonial/len(app_ops)

__all__=["ConstitutiveProbeResult","probe_constitutive","phi_score","CONSTITUTIVE","CEREMONIAL","UNPROBED"]
