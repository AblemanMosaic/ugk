"""ugk/conformance/grundnorm_readonly_gate.py — UL-G-01: Grundnorm integrity.

Two propositions, split cleanly (they were previously conflated):

  ESTABLISHMENT (separate check, posture_established()):
      Has the deployment deliberately ESTABLISHED the read-only posture by running
      `ugk harden`? Establishment is recorded in DEPLOYMENT STATE
      (genesis_dir()/GRUNDNORM_POSTURE.json), never inside the package — pip strips
      file modes (0o444 -> 0o644) but copies package data, so a packaged marker would
      re-collapse establishment into integrity and produce false FAILs on vanilla
      installs. Establishment is about the deliberate act, not the current modes.

  INTEGRITY (this gate, UL-G-01):
      GIVEN an established posture, are all protected Grundnorm modules still read-only?

Tri-state outcome:
      established + all 0o444    -> PASS              (intact)
      established + any writable -> FAIL              (tamper of an established posture)
      not established            -> NOT_ESTABLISHED   (no integrity proposition asserted)

A vanilla install that never ran `ugk harden` reports NOT_ESTABLISHED, which the batch
counts as a distinct bucket (not a failure). A hardened deployment that becomes writable
is a hard FAIL.
"""
import os
import stat
import json

from ugk.conformance import NOT_ESTABLISHED

_RECORD_NAME = "GRUNDNORM_POSTURE.json"


def posture_established():
    """Separate establishment proposition: is the read-only posture established?

    Established iff a well-formed deployment-state record exists in genesis_dir().
    Returns (established: bool, detail: str). Mode bits are deliberately NOT consulted
    here — establishment reflects the `ugk harden` act, integrity reflects the modes.
    """
    from ugk._paths import genesis_dir
    rec = genesis_dir() / _RECORD_NAME
    if not rec.exists():
        return False, f"no establishment record at {rec} (run `ugk harden`)"
    try:
        data = json.loads(rec.read_text())
    except Exception as e:
        return False, f"establishment record unreadable at {rec}: {type(e).__name__}: {e}"
    if data.get("posture") == "grundnorm_readonly" and data.get("established") is True:
        return True, f"established (record: {rec})"
    return False, f"establishment record malformed at {rec}"


def run():
    from ugk.module_registry import grundnorm_paths, GRUNDNORM_MODULES

    # Step 1 — verify establishment (separate proposition / precondition).
    established, est_detail = posture_established()
    if not established:
        # No integrity claim is asserted over an unestablished posture.
        return NOT_ESTABLISHED, f"Grundnorm read-only posture not established — {est_detail}"

    # Step 2 — verify integrity, given establishment.
    # A file is read-only iff none of the write bits (owner/group/other) are set.
    # (os.access is unreliable: it returns True for root even on a 0o444 file.)
    def _is_readonly(path):
        mode = os.stat(path).st_mode
        return not bool(mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

    # Resolve protected modules by LOGICAL IDENTITY (registry), not root-relative paths.
    paths = grundnorm_paths()
    writable = [str(p) for p in paths if not _is_readonly(p)]
    if writable:
        return False, (f"Grundnorm tamper — posture {est_detail}, but writable modules "
                       f"detected: {writable}")
    return True, (f"posture {est_detail}; all {len(GRUNDNORM_MODULES)} Grundnorm modules "
                  f"read-only (0o444)")


if __name__ == "__main__":
    status, detail = run()
    label = {True: "PASS", False: "FAIL"}.get(status, "NOT-ESTABLISHED")
    print(f"grundnorm_readonly_gate: {label}  {detail}")
