#!/usr/bin/env python3
"""Mint-time archive hygiene assertion (r95 / AD-30, acceptance criterion 8).

Fails closed if a release tarball's index contains any Python bytecode (`*.pyc`) or `__pycache__`
directory entry. The shipped UGK archive is built pyc-clean (the .pyc files reviewers observe are
generated only by RUNNING the extracted code), but this makes that property MACHINE-CHECKED at mint
so the ambiguity cannot recur. Usage:

    python3 tools/archive_hygiene_check.py /mnt/user-data/outputs/ugk-v0.1.0-release-rNN.tar.gz

Exit 0 + "HYGIENE PASS" when clean; exit 1 + a listing of offending entries otherwise.
"""
from __future__ import annotations
import sys
import tarfile


def check(tarball_path: str):
    offenders = []
    with tarfile.open(tarball_path, "r:*") as tf:
        for name in tf.getnames():
            low = name.lower()
            if low.endswith(".pyc") or "__pycache__" in low or low.endswith(".pyo"):
                offenders.append(name)
    return offenders


def main(argv):
    if len(argv) != 2:
        print("usage: archive_hygiene_check.py <tarball>")
        return 2
    offenders = check(argv[1])
    if offenders:
        print("HYGIENE FAIL: %d bytecode/__pycache__ entries in %s:" % (len(offenders), argv[1]))
        for o in offenders[:50]:
            print("  " + o)
        return 1
    print("HYGIENE PASS: %s contains 0 pyc/pyo/__pycache__ entries." % argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
