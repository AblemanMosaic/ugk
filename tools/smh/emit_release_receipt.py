"""SMH-I5 native release hook entry point. Called by mint_release.sh AFTER the archive is
sealed. Reads the final archive bytes (read-only), records ONE deep_export tier-transition
receipt into an EXTERNAL SMH ledger. Never touches the archive; never writes into the UGK chain."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smh_emission_hooks as H
import smh_tier_ledger as P2

def main(argv):
    if len(argv) < 3:
        print("usage: emit_release_receipt.py <archive_path> <external_ledger_path>", file=sys.stderr)
        return 2
    archive, ledger_path = argv[1], argv[2]
    led = P2.TierTransitionLedger(ledger_path)
    r = H.on_release_minted(archive, led)
    if not r.get("emitted"):
        print("SMH: NOT emitted (%s)" % r.get("class"), file=sys.stderr); return 1
    print("SMH: deep_export receipt %s recorded to external ledger %s" % (r["receipt_id"], ledger_path))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
