# Security Policy

## What UGK is and is not

UGK is a constitutional computing substrate — it makes governance *constitutive*
of operations by enforcing receipt-before-effect at the kernel level. It is not
a security product, an access-control system, or a cryptographic library.

Understanding the distinction matters for security assessment:

- **What UGK enforces:** that governed operations produce a receipt before
  executing, that the receipt chain is tamper-evident, and that authority is
  derived from admissibility under declared governance rules rather than from
  the presence of evidence.

- **What UGK does not enforce:** OS-level process isolation, network access
  controls, secret management, or the correctness of application-supplied
  gate functions.

The honest limits of UGK's governance closure are declared in
`CLASSIFIED_REMAINDERS` within the kernel itself:

```
CR-01: OS layer — OS does not provide receipt infrastructure
CR-02: Python runtime internals — CPython bytecode not receipted
CR-03: SQLite WAL layer — filesystem ops below SQLite not receipted
CR-04: effect() callable internals — opaque unless it also calls kernel.execute()
```

These are architectural declarations, not defects.

## Cryptographic scope

UGK uses:
- **SHA-256** (Python stdlib `hashlib`) — for receipt chain hashing, CHC
  semantic hash computation, DKN identity derivation, and constitutional
  frame binding (`law_hash`, `LEGEND_HASH`)
- **Ed25519** (vendored zero-dependency implementation in `ugk/vendor/ed25519.py`)
  — for governor key generation, genesis seal signing, and warrant signing

The Ed25519 implementation is vendored for zero-dependency deployment. It is
a standard implementation and has not been modified for UGK.

Security assumptions: SHA-256 collision resistance and Ed25519 unforgeability
under standard cryptographic assumptions. If either primitive is broken, the
receipt chain's tamper-evidence guarantees degrade accordingly.

## Reporting a vulnerability

If you discover a security issue in UGK — including implementation bugs in the
vendored Ed25519, incorrect hash computations, receipt chain bypass paths, or
authority escalation through the warrant or will systems — please report it
privately before disclosure.

**Contact:** ableman.research@gmail.com

**Include in your report:**
- A description of the vulnerability and its impact
- Which component is affected (`ugk/kernel.py`, `ugk/vendor/ed25519.py`, a
  specific gate, etc.)
- A minimal reproduction if possible
- Whether you believe this is exploitable in a deployed UGK instance

We will acknowledge receipt within 48 hours and aim to resolve confirmed
vulnerabilities within 14 days. We will credit researchers in the CHANGELOG
unless you prefer otherwise.

## Supported versions

UGK v0.1.0 is the current version. Prior builds are internal development
artifacts and are not supported.

## Deployment security

UGK's Grundnorm layer files (`kernel.py`, `schema.py`, `store.py`,
`binding.py`, `broker.py`, `invariants.py`, `dimensions.py`) are installed
with `444` permissions (read-only). The `grundnorm_readonly_gate` verifies
this at runtime.

These permissions protect against non-admin modification of the kernel layer.
They do not protect against an attacker with write access to `site-packages`.
OS-level confinement of the Python process (containers, seccomp, VMs) provides
defense-in-depth beyond what UGK can supply at the software layer.
