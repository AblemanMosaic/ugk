# B3 — Key Provenance: Architectural Note (durable)

**Status:** verified. This note records an architectural distinction that MUST survive
future refactors.

## The distinction

The keygen creation-provenance artifact is an **identity / provenance artifact**. It is
**not a governance receipt**.

- **Creation provenance** (this artifact) answers: *"where did this key originate?"*
  It is emitted by `keygen` at key-creation time, is **public-only** (never contains
  private-key material), is **founding-independent** (requires no founded chain, no
  kernel, no `execute()` path, no store interaction), and asserts **identity (WHO)**,
  not authority.

- **Binding** (founding, `charter`) answers: *"when did this key become authoritative?"*
  Authority originates at binding — it requires the Ed25519 secret — never at creation.

These are different questions and remain different artifacts.

## Why it holds structurally (not just by prose)

The forward-link between the two is a **structural** consequence of an existing
constitutional primitive, not a newly invented linkage mechanism:

    pubkey_fingerprint == mosaic_id(pubkey) == manifest.mosaic_root

`mosaic_id(pubkey) = SHA-256(pubkey)` is documented in `ugk/storage/binding.py` as
"identity (proves WHO), not authority." The same deterministic public-key function
underlies both creation provenance and founding identity, so B3b required **no charter
modification**.

## Why it survives refactors

The distinction is **executable**, not merely documented: `tools/b3_conformance.py`
asserts that `_cmd_keygen` contains no `_make_kernel`, no `.execute(`, and no
`UGKReceiptStore` usage. Any future refactor that reclassified key generation as
governance activity (routing it through a founded chain / receipt path) would **fail the
B3 conformance gate**. The gate is the durable guard; this note is its rationale.

## Invariants (do not regress)

1. Provenance artifact is public-only — never private-key material.
2. `pubkey_fingerprint` is a pure function of the public key (`mosaic_id`).
3. keygen remains founding-independent (no kernel / execute / store).
4. Authority begins at binding (founding), never at creation.
