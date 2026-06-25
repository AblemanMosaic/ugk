"""governed_session.py — minimal runnable governed session (UGK v0.1.0).

Smallest correct found→open→execute→close flow against the shipped tree, founded with
the public conformance dev fixture into an isolated temp dir. On an UNCHARTERED tree a
bare _ceremony() fails closed (GovernanceNotFounded, CHARTER-S-01) by design; this
example founds first, so it runs.

Run:  PYTHONPATH=. python examples/basic/governed_session.py
"""
import os, sys
# Make `ugk` importable when run as a plain script from anywhere
# (python examples/foo.py), not only with PYTHONPATH=. from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import os, sys, tempfile

def _found_and_reexec():
    state_dir = tempfile.mkdtemp(prefix="ugk_session_")
    os.environ["UGK_GENESIS_DIR"] = state_dir
    from ugk.conformance._fixture import fixture_pubkey, DEV_FIXTURE_PRIVKEY
    from ugk import DeploymentManifest, write_charter_artifacts
    m = DeploymentManifest.create(
        fixture_pubkey(), "governed-session-example", "example", "trace_only")
    write_charter_artifacts(m, genesis_dir=state_dir, force=True)
    open(os.path.join(state_dir, "GENESIS_PRIVKEY.hex"), "w").write(DEV_FIXTURE_PRIVKEY + "\n")
    os.environ["_UGK_SESSION_DIR"] = state_dir
    import subprocess
    sys.exit(subprocess.call([sys.executable, __file__],
                             env={**os.environ, "_UGK_SESSION_FOUNDED": "1"}))

def main():
    from ugk.kernel import EffectAtomicity
    if os.environ.get("_UGK_SESSION_FOUNDED") != "1":
        _found_and_reexec()
    state_dir = os.environ["_UGK_SESSION_DIR"]
    os.environ["UGK_GENESIS_DIR"] = state_dir

    from ugk import GovernanceKernel
    from ugk import UGKReceiptStore
    store = UGKReceiptStore(db_path=os.path.join(state_dir, "ugk.db"))
    k = GovernanceKernel(store=store, authority="session-example")
    k._ceremony()
    sid = k.open_session()
    print("session opened:", sid)
    k.execute(op="test_checkpoint", authority="session-example", parameters={"msg": "hello"},
              gate=lambda: True, effect=lambda: None, layer="I", effect_atomicity=EffectAtomicity.NON_ATOMIC)
    k.close_session()
    print("receipts:", len(store.all_receipts()), "| chain intact:", store.verify_stream_hash())

if __name__ == "__main__":
    main()
