"""grbsa_runtime.explain_adapter — ExplainAdapter (GRBSA G4c).

Wraps the EXISTING CGProj explain surface as a receipt-bound continuation. Success semantics =
NON-INVENTION + (object-level) COMPLETENESS + non-vacuity. The governing rule, carried verbatim from
CGProj Phase 5b: explain may OMIT, explain may REPHRASE, explain may NOT INVENT.

r28/r29 (de-tangled): the non-invention + completeness predicate is reconstructed IN-LANE from the
import-clean projection library (`ugk.projections.explain`, `patterns`, `domain_mappings`) — see
`_corpus_truth_sets` and `reconstructed_invention_violations` below. No gate script is executed on any
path; the CGProj Phase-5b gate is NOT modified. Completeness is object-level (explain_keys vs corpus
pattern:/domain: key set); within-object omission is allowed.
"""
from __future__ import annotations
from dataclasses import dataclass
import sys, os, hashlib
from typing import Optional

from .gate_adapter import ReceiptCore, ResultEnvelopeCore, PostureRefusal, _Trace
try:
    from ugk.scale.oracle import POSTURE_OPS as _POSTURE_OPS
except Exception:  # pragma: no cover
    _POSTURE_OPS = set()


# ---- Explain domain extensions ----
@dataclass(frozen=True)
class ExplainReceipt:
    core: ReceiptCore
    explain_identity: str
    corpus_signature: tuple        # sorted corpus_keys — the object set explain is accountable to
    domain: str = "explain"        # explicit category tag (Category-Separation)


@dataclass(frozen=True)
class ExplainResultEnvelope:
    core: ResultEnvelopeCore
    invention_violations: tuple    # ((key, claim), ...) — cited claims NOT in corpus (empty = clean)
    covered_keys: tuple            # sorted explain_keys actually projected
    missing_keys: tuple            # corpus objects with no projection (orphans / incompleteness)
    domain: str = "explain"        # explicit category tag (Category-Separation)


# ---- success semantics: a PREDICATE over receipt+envelope (in neither core/extension) ----
def explain_success(receipt: ExplainReceipt, envelope: ExplainResultEnvelope) -> bool:
    """NON-INVENTION (no cited claim outside corpus) AND object-level COMPLETENESS (covered == the
    receipt's corpus_signature, no missing) AND non-vacuity (>=1 corpus object). Within-object
    omission is allowed (rephrase/omit ok); inventing a claim or dropping an object is not."""
    # Category-Separation guard: certifies ONLY the explain domain; mismatch => CLEAN False.
    if getattr(receipt, "domain", None) != "explain" or getattr(envelope, "domain", None) != "explain":
        return False
    if len(envelope.invention_violations) != 0:
        return False                                  # invention => fail (load-bearing)
    if len(receipt.corpus_signature) == 0:
        return False                                  # vacuous: zero corpus objects
    if tuple(envelope.covered_keys) != tuple(receipt.corpus_signature):
        return False                                  # incomplete coverage
    if len(envelope.missing_keys) != 0:
        return False                                  # orphan / missing object
    return True


def _corpus_truth_sets(P, DM):
    """Reconstruct phase5b's corpus truth sets from the import-clean projection library (same source
    phase5b uses). Faithful to phase5b's _pattern_prims/_domain_prims/CORPUS_PAT_REFS."""
    def _pattern_prims(p):
        return set(p.primitives) | {x for s in p.seams for x in s.ugk_primitives}
    def _domain_prims(d):
        return {x for s in d.integration_points for x in s.ugk_primitives}
    corpus_pat = {p.id: _pattern_prims(p) for p in P.PATTERNS}
    corpus_pat_refs = {d.id: set(d.patterns) for d in DM.DOMAIN_MAPPINGS}
    corpus_dom = {d.id: _domain_prims(d) for d in DM.DOMAIN_MAPPINGS}
    return corpus_pat, corpus_pat_refs, corpus_dom


def reconstructed_invention_violations(projections, EX, corpus_pat, corpus_pat_refs, corpus_dom):
    """In-lane reconstruction of phase5b.invention_violations — uses ONLY the import-clean explain
    surface (EX.cited_primitives/cited_pattern_refs) + the corpus truth sets. Executes NO gate script.
    Behavior validated by the G4c gate's import-clean bounded fixture (no gate-script execution)."""
    bad = []
    for key, text in projections.items():
        kind, oid = key.split(":", 1)
        prims = set(EX.cited_primitives(text))
        if kind == "pattern":
            allowed = corpus_pat.get(oid, set())
            bad += [(key, "prim:" + x) for x in prims - allowed]
        else:
            allowed = corpus_dom.get(oid, set())
            bad += [(key, "prim:" + x) for x in prims - allowed]
            refs = set(EX.cited_pattern_refs(text))
            bad += [(key, "ref:" + x) for x in refs - corpus_pat_refs.get(oid, set())]
    return bad


class ExplainAdapter:
    """Wraps the CGProj explain surface as a receipt-bound continuation.

    Test seams (used ONLY by the equivalence gate's negative controls):
      _emit_receipt_before_effect=False -> NBER-1 violation
      _inject_invented_claim=True       -> add a cited claim NOT in corpus (load-bearing control)
      _drop_corpus_object=<key>         -> drop one object from explain coverage (completeness)
    """
    def __init__(self, repo: str, *, op: str = "explain_verify",
                 explain_identity: str = "cgproj/explain/v1",
                 _emit_receipt_before_effect: bool = True,
                 _inject_invented_claim: bool = False,
                 _drop_corpus_object: Optional[str] = None):
        self.repo = repo
        self.op = op
        self.explain_identity = explain_identity
        self._emit_receipt_before_effect = _emit_receipt_before_effect
        self._inject_invented_claim = _inject_invented_claim
        self._drop_corpus_object = _drop_corpus_object

    def _admissibility(self) -> tuple:
        if self.op in _POSTURE_OPS:
            raise PostureRefusal("adapter attempted posture op: " + self.op)
        return ("c_explain.v1",)

    def run(self) -> tuple:
        trace = _Trace()
        criteria = self._admissibility()                  # may raise PostureRefusal
        sys.path.insert(0, self.repo)
        # FIX A: source from IMPORT-CLEAN library surfaces only. Execute NO gate script (phase5b's
        # top level spawns the full conformance batch). Reconstruct corpus truth sets in-lane.
        from ugk.projections import explain as EX, patterns as P, domain_mappings as DM
        corpus_pat, corpus_pat_refs, corpus_dom = _corpus_truth_sets(P, DM)
        corpus_keys = {"pattern:" + p.id for p in P.PATTERNS} | \
                      {"domain:" + d.id for d in DM.DOMAIN_MAPPINGS}
        corpus_signature = tuple(sorted(corpus_keys))

        def _mint_receipt():
            core = ReceiptCore(
                proposal={"op": self.op, "explain_identity": self.explain_identity},
                criteria=criteria,
                evaluation=("admissible",),
                authority={"warrant": "explain-corpus", "law_ref": "law_hash"},
                outcome="admitted",
                lineage={"prior": "0" * 64, "position": 0, "produces_effects": ()},
            )
            return ExplainReceipt(core=core, explain_identity=self.explain_identity,
                                  corpus_signature=corpus_signature)

        def _verify():
            trace.mark("effect_ran")
            proj = dict(EX.explain_projections())          # real explain surface (import-clean)
            # NEG seam: inject an invented cited claim by APPENDING to the existing 'primitives: '
            # line in the REAL pipe-delimited format the checker reads (lowercase, first match,
            # ' | '-delimited). A mis-cased / extra line would not be seen by cited_primitives.
            if self._inject_invented_claim:
                k = next(iter(proj))
                lines = proj[k].splitlines()
                injected = False
                for i, ln in enumerate(lines):
                    if ln.startswith("primitives: "):
                        lines[i] = ln + " | __INVENTED_PRIMITIVE_NOT_IN_CORPUS__"
                        injected = True
                        break
                if not injected:  # no primitives line — add one in the real format
                    lines.append("primitives: __INVENTED_PRIMITIVE_NOT_IN_CORPUS__")
                proj[k] = "\n".join(lines)
            violations = reconstructed_invention_violations(proj, EX, corpus_pat, corpus_pat_refs, corpus_dom)
            explain_keys = set(proj.keys())
            # NEG seam: drop one corpus object from coverage
            if self._drop_corpus_object is not None:
                explain_keys.discard(self._drop_corpus_object)
            covered = tuple(sorted(explain_keys & corpus_keys))
            missing = tuple(sorted(corpus_keys - explain_keys))
            return violations, covered, missing

        if self._emit_receipt_before_effect:
            trace.mark("receipt_minted")
            receipt = _mint_receipt()
            violations, covered, missing = _verify()
        else:                                              # NEG seam: effect before receipt
            violations, covered, missing = _verify()
            trace.mark("receipt_minted")
            receipt = _mint_receipt()

        clean = (len(violations) == 0 and tuple(covered) == corpus_signature and len(missing) == 0)
        env = ExplainResultEnvelope(
            core=ResultEnvelopeCore(
                status="pass" if clean else "fail",
                evidence_refs=tuple(covered),
                timing={},
                result_hash=hashlib.sha256(repr((tuple(violations), covered, missing)).encode()).hexdigest(),
                lineage={"produced_effects": (), "delta": len(covered)},
            ),
            invention_violations=tuple(violations),
            covered_keys=tuple(covered),
            missing_keys=tuple(missing),
        )
        return receipt, env, trace
