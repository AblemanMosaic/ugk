# schema_hash — Structure Frame-Pin (v0.1.0)

**Status:** implemented and gated (`tools/schema_hash_conformance.py`).

## What it is

`schema_hash` is the **structure** leg of the integrity frame triad:

| leg           | answers          | source                          |
|---------------|------------------|---------------------------------|
| `law_hash`    | behavior (rules) | SHA-256(`invariants.py`)        |
| `legend_hash` | meaning (vocab)  | the sealed legend               |
| `schema_hash` | **structure**    | SHA-256 over `PRAGMA table_info`|

It is computed at store startup over every user table's column shape (name, type,
notnull, default, pk), tables sorted, columns in cid order, `sqlite_*` internal tables
and index/trigger SQL excluded. It is a pure function of the container shape — stable
within and across processes (`bcb3397f…`).

`EXPECTED_SCHEMA_HASH` pins the canonical shape for this release. `schema_frame_intact()`
reports whether the live shape matches the anchor. The triad is exposed read-only in the
kernel integrity snapshot and the CLI `status` output.

## Deliberate scope boundaries

- **Observe-and-report only.** A drifted schema is *reported* (`schema_frame_intact ==
  False`); it is **never** a refuse-on-mismatch gate. The store keeps writing. Drift
  *detection* is the point; drift *handling* is not.
- **Frame-level, not per-receipt.** `schema_hash` is **not** a receipts column and is not
  injected into individual receipts. Interpretive closure belongs to the frame/epoch;
  receipts inherit it. This avoids per-receipt metadata growth and avoids the circularity
  of fingerprinting a table whose shape would then include the fingerprint.

## Explicitly OUT OF SCOPE for v0.1.0

- **Live schema migration / governed `schema_migrated` receipts.** Mutating a live store's
  shape under governance (versioned migration, epoch re-pin on frame change) is a separate,
  deferred track. B-schema_hash provides drift *detection*; it does not perform or govern
  *mutation*.
- **Bootstrap schema creation** remains a declared remainder (the initial container shape
  is created, not migrated).
