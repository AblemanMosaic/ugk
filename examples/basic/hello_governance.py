"""hello_governance.py — the smallest "hello governance" for UGK v0.1.0.

It shows the whole point in one screen:
  1. an ADMITTED operation commits a receipt BEFORE its effect runs;
  2. a REFUSED operation fails closed — the effect never runs;
  3. the receipt chain stays intact.

One-time ceremony note: UGK loads the governor key at import, so founding a fresh
governance happens in this process and the demo then runs in a clean child process.
That handoff is the only ceremony here; everything in main() is the actual story.

Run:  python examples/basic/hello_governance.py
"""
import os, sys, tempfile, subprocess

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _found_then_handoff():
    """Write a dev charter into a throwaway dir, then re-run this file in a fresh process."""
    state = tempfile.mkdtemp(prefix="ugk_hello_")
    os.environ["UGK_GENESIS_DIR"] = state
    from ugk.conformance._fixture import fixture_pubkey, DEV_FIXTURE_PRIVKEY
    from ugk import DeploymentManifest, write_charter_artifacts
    manifest = DeploymentManifest.create(fixture_pubkey(), "hello-governance", "example", "trace_only")
    write_charter_artifacts(manifest, genesis_dir=state, force=True)
    open(os.path.join(state, "GENESIS_PRIVKEY.hex"), "w").write(DEV_FIXTURE_PRIVKEY + "\n")
    env = {**os.environ, "_UGK_HELLO_DIR": state, "_UGK_HELLO_FOUNDED": "1"}
    sys.exit(subprocess.call([sys.executable, __file__], env=env))


def main():
    if os.environ.get("_UGK_HELLO_FOUNDED") != "1":
        _found_then_handoff()

    state = os.environ["_UGK_HELLO_DIR"]
    os.environ["UGK_GENESIS_DIR"] = state

    from ugk import GovernanceKernel, UGKReceiptStore
    from ugk.kernel import EffectAtomicity, GateRefusal

    store = UGKReceiptStore(db_path=os.path.join(state, "ugk.db"))
    k = GovernanceKernel(store=store, authority="hello")
    k._ceremony()
    k.open_session()

    # 1. An admitted operation. The receipt is committed before the effect runs.
    effect_ran = {"yes": False}
    k.execute(op="test_checkpoint", authority="hello", parameters={"msg": "hello, governance"},
              gate=lambda: True, effect=lambda: effect_ran.__setitem__("yes", True),
              layer="I", effect_atomicity=EffectAtomicity.NON_ATOMIC)
    print(f"ADMIT  : 'test_checkpoint' admitted; effect ran = {effect_ran['yes']}; "
          f"receipts on chain = {len(store.all_receipts())}")

    # 2. A refused operation. The gate says no, so the effect must never run.
    blocked = {"ran": False}
    try:
        k.execute(op="test_checkpoint", authority="hello", parameters={"msg": "should not happen"},
                  gate=lambda: False, effect=lambda: blocked.__setitem__("ran", True),
                  layer="I", effect_atomicity=EffectAtomicity.NON_ATOMIC)
        print("REFUSE : (unexpected) operation was not refused")
    except GateRefusal:
        print(f"REFUSE : 'test_checkpoint' refused at the gate (fail-closed); effect ran = {blocked['ran']}")

    k.close_session()
    print(f"CHAIN  : {len(store.all_receipts())} receipts; chain intact = {store.verify_stream_hash()}")
    print("\nThat is governance: every outcome is a committed receipt, and refusal is a "
          "first-class outcome — the effect never runs without one.")


if __name__ == "__main__":
    main()
