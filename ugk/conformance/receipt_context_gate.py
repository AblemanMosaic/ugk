"""ugk/conformance/receipt_context_gate.py — receipt-time context gate (IEL / AD-25).

Proves ReceiptContextResolver binds verification to the RECEIPT-TIME frame (from receipt-bound
evidence), not live state, and correctly reports drift when a receipt predates an amendment. A
receipt interpretable 50 years later must use the law_hash/legend_hash it committed, regardless of
how far the live frame has since moved."""
from __future__ import annotations

from ugk.integrity import ReceiptContextResolver, IntegrityContext, VerificationLevel
from ugk.storage.store import Receipt


def _mk(law_hash, legend_hash, ts=1.0):
    return Receipt(op="x", authority="a", parameters={}, intent="i", jurisdiction="j",
                   confidence="c", timestamp=ts, failed=False, session_dkn="d",
                   law_hash=law_hash, legend_hash=legend_hash, warrant_id="", intent_ref="")


def run():
    live_law, live_leg = "LIVE_LAW", "LIVE_LEG"

    # a receipt written under an OLD frame (predates an amendment)
    r_old = _mk("OLD_LAW", "OLD_LEG")
    ctx = ReceiptContextResolver.resolve(r_old)
    if ctx.law_hash != "OLD_LAW" or ctx.legend_hash != "OLD_LEG":
        return False, "resolver returned the wrong (non-receipt-time) frame: %s/%s" % (ctx.law_hash, ctx.legend_hash)
    if not ReceiptContextResolver.drifted(r_old, live_law_hash=live_law, live_legend_hash=live_leg):
        return False, "drift NOT detected for a receipt whose frame differs from live"

    # a receipt written under the CURRENT frame -> no drift
    r_now = _mk(live_law, live_leg)
    if ReceiptContextResolver.drifted(r_now, live_law_hash=live_law, live_legend_hash=live_leg):
        return False, "false drift reported for a receipt matching the live frame"
    if ReceiptContextResolver.resolve(r_now).law_hash != live_law:
        return False, "resolver did not return the receipt-time frame for a current receipt"

    # IntegrityContext bundles the live frame + default bar
    ic = IntegrityContext(law_hash=live_law, legend_hash=live_leg, schema_hash="S")
    if ic.required_level is not VerificationLevel.BODY:
        return False, "IntegrityContext default required_level is not BODY"

    return True, ("ReceiptContextResolver binds to receipt-time frame (not live) and reports drift "
                  "correctly across an amendment; IntegrityContext bundles the live frame at BODY bar")


if __name__ == "__main__":
    ok, detail = run()
    print(("PASS" if ok else "FAIL") + "  receipt_context_gate — " + detail)
    raise SystemExit(0 if ok else 1)
