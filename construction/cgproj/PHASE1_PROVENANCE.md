# CGProj Phase 1 + Lazy-Init Addendum — Provenance & Gate Report (r11)

## Archive lineage
- r9-clean baseline: b98108e93f41cd9e83ebd24088ead9c534f853ccdfac26b70fb0694d63d04aa0
- r10 (Phase 1 CGProj files): a866d79443d2275eee3bb6f8b94b714cb99bfd417ecede0480f31dfe7737f6b2
- r11 (this archive: r10 + authorized lazy ugk/__init__.py): sha in detached record

## Change in r11 (single authorized addendum)
**Only file changed: `ugk/__init__.py`** — converted from eager execution imports to PEP 562
lazy `__getattr__` resolution. No other file touched. This was separately authorized as the
scoped boundary fix for import-isolation Check B.

### What the change does
- Replaces the eager `from ugk.kernel import ...` / governance / storage / transport / schema /
  core block with a `_LAZY_EXPORTS` name->module map plus `__getattr__` / `__dir__`.
- Public API preserved EXACTLY: `from ugk import X`, `import ugk; ugk.X`, `from ugk import *`
  (via `__all__`), and AttributeError on bogus names all behave as before. Only import *timing*
  changes — no symbol added or removed.
- The CLI state-dir pre-import hook (lines 1-55) is preserved verbatim.

### Why
`import ugk.projections` must import the parent `ugk` package first; with eager imports that
pulled the entire execution jurisdiction in, failing isolation Check B. Lazy resolution severs it.

## law_hash
- UNCHANGED: 546a9e90fd780dec098d833b4a960f20db530bca9f946244a4ae3d7ebe156820
- law_hash is the sha of invariants.py, independent of __init__.py — verified empirically pre/post.

## Phase 1 Structural Validity Gate — PASS (unchanged from r10)
7 patterns / 5 domains; frozen (neg-control has teeth); 20 refs resolve (neg-control: bogus fails);
no downward ref; boundaries present; primitives are string labels only.

## Import-isolation — A PASS, B PASS (now fixed), C PASS
- A (import ugk does NOT load ugk.projections): PASS
- B (import ugk.projections does NOT load execution-jurisdiction modules): **PASS** — was the
  r10 blocker; resolved by the lazy __init__. Verified: zero execution modules in sys.modules
  after `import ugk.projections`. `import ugk` alone also loads zero execution modules.
- C (static: no projection file imports an execution-jurisdiction module): PASS
- Negative control: an eager `import ugk.kernel` IS detectable by the B-check (check is not vacuous).

## Public-API contract verification
- all 17 __all__ names resolve via lazy __getattr__: PASS
- 3 non-__all__ governor exports (GovernorSignatureRequired, verify_governor, governor_key_status)
  resolve on direct access: PASS
- from ugk import X / import * / bogus->AttributeError / caching-into-globals: PASS

## Behavioral non-regression
- UGK conformance: 78/78 gates pass from the r11 tree.
- import ugk -> v0.1.0, CGP-ESA REGISTRY 33.

## Status
Phase 1 complete; import-isolation B now passing under the authorized lazy-__init__ addendum.
No Phase 2+ work performed. Only `ugk/__init__.py` changed relative to r10.
