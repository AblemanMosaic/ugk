"""application_ops_example.py — a runnable governed-operation example (UGK v0.1.0).

Founds an ephemeral deployment with the PUBLIC conformance dev fixture (the identity the
gate suite uses), into an isolated temp dir, then runs one governed operation end-to-end
and prints the receipt chain. Never writes into the package tree.

Kernel identity loads at IMPORT time from genesis/GENESIS_KEY.pub, so we write the
founding into a temp dir, point UGK_GENESIS_DIR at it, and re-exec ONCE in a fresh
interpreter that adopts the founding. The temp dir is shared with the child via env.

Run:  PYTHONPATH=. python examples/governed/application_ops_example.py
"""
import os, sys
# Make `ugk` importable when run as a plain script from anywhere
# (python examples/foo.py), not only with PYTHONPATH=. from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import os, sys, tempfile

def _found_and_reexec():
    state_dir = tempfile.mkdtemp(prefix="ugk_example_")
    os.environ["UGK_GENESIS_DIR"] = state_dir
    from ugk.conformance._fixture import fixture_pubkey, DEV_FIXTURE_PRIVKEY
    from ugk import DeploymentManifest, write_charter_artifacts
    m = DeploymentManifest.create(
        fixture_pubkey(), "application-ops-example", "example", "trace_only")
    write_charter_artifacts(m, genesis_dir=state_dir, force=True)
    open(os.path.join(state_dir, "GENESIS_PRIVKEY.hex"), "w").write(DEV_FIXTURE_PRIVKEY + "\n")
    os.environ["_UGK_EXAMPLE_DIR"] = state_dir
    import subprocess
    sys.exit(subprocess.call([sys.executable, __file__],
                             env={**os.environ, "_UGK_EXAMPLE_FOUNDED": "1"}))

def main():
    from ugk.kernel import EffectAtomicity
    if os.environ.get("_UGK_EXAMPLE_FOUNDED") != "1":
        _found_and_reexec()
    state_dir = os.environ["_UGK_EXAMPLE_DIR"]
    os.environ["UGK_GENESIS_DIR"] = state_dir   # ensure child resolves same genesis

    from ugk import GovernanceKernel
    from ugk import UGKReceiptStore
    from ugk import WarrantStore
    store = UGKReceiptStore(db_path=os.path.join(state_dir, "ugk.db"))
    ws    = WarrantStore(db_path=os.path.join(state_dir, "ugk_warrants.db"))
    k = GovernanceKernel(store=store, authority="example-operator")
    k._ceremony()
    k.open_session()
    k.set_warrant_store(ws)
    result = k.execute(
        op="test_checkpoint",
        authority="example-operator",
        parameters={"record": "demo", "value": 42},
        gate=lambda: True,
        effect=lambda: {"written": True},
        layer="I", effect_atomicity=EffectAtomicity.NON_ATOMIC,
    )
    print("governed op result:", result)
    k.close_session()
    print("receipts written:", len(store.all_receipts()))
    print("chain intact:", store.verify_stream_hash())
    print("state dir (isolated):", state_dir)

if __name__ == "__main__":
    main()
