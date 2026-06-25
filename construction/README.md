# construction/ — CGProj construction gates (maintained DEEP surface, not release-acceptance)

This directory holds the **CGProj construction phase gates** (`phase1`…`phase6`) that built and
validated the projection / execution-jurisdiction layer, plus their shared `execution_jurisdiction.py`
helper and provenance notes.

## Status (r87): MAINTAINED deep verification surface

As of r87 these gates are **maintained** and exercised by `verify_deep.sh`, the deep verification
surface. This supersedes the r85 framing (which quarantined them as frozen, do-not-run scaffolding):
they are now repaired and expected to pass.

- Sibling gates resolve relative to this directory (not the old `tools/cgproj/` location).
- Conformance-count checks are **posture-tolerant**: a leg passes on `0 failed` + a `PASS` verdict;
  a not-established posture warning (e.g. `grundnorm_readonly_gate` before `ugk harden`) is tolerated.
  This is a deliberate loosening of the original RC-era exact-count assertions — these gates assert
  "nothing fails," not "hardened posture." Run `ugk harden` first if you want a fully-established run.
- Subprocess legs use a grandchild-proof bounded runner (own process group, temp-file output,
  process-group kill on timeout), so they terminate deterministically instead of hanging.
- Corpus-dependent legs (e.g. phase6's reconciliation against an earlier baseline) report
  **not-established** when the baseline archive is not supplied, rather than failing.

## Two surfaces, distinct roles

- **Release acceptance** (the gate that governs whether a release ships): `verify_release.sh`
  (the 83-gate suite + pins) plus Proof Model B / G6 (content-addressed continuity + attestation).
- **Deep verification** (additional archival/construction confidence): `verify_deep.sh`, which runs
  the release verifier, all CGProj phase gates here, G6, and the standalone overlay probes, each
  bounded, with a final per-leg table.

Release acceptance does NOT depend on this directory; `verify_deep.sh` additionally exercises it.
