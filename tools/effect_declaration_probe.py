#!/usr/bin/env python3
"""tools/effect_declaration_probe.py - r102-a / AD-37 (scaffolding probe).

Static, source-level proof of acceptance criterion 7: every in-tree execute()
callsite that passes a *real* effect (an effect argument that is not the literal
None) declares an EffectAtomicity via the effect_atomicity keyword.

This is a deep/clean-room probe, NOT a member of the conformance batch. It scans
the source tree with the AST only - it imports nothing and executes no governed
code - so it can be pointed at an extracted release archive.

r107 / AD-40 adds the first legitimate dynamic declaration seam: the broker
(LocalBrokerServer) propagates the caller's effect and declared class from a
GovernedRequest to kernel.execute(). This probe recognizes that EXACT pattern
(effect=request.effect AND effect_atomicity=request.effect_atomicity) as a
"propagated declaration" - not a class literal, not an unknown class. The
recognition is narrow: any other dynamic effect_atomicity value still has to earn
recognition explicitly.

r111 / AD-42 adds the SECOND such seam: the GRBSA ExecutionAdapter propagates the
caller's effect and declared class from its own instance (effect=self.effect AND
effect_atomicity=self.effect_atomicity) to kernel.execute(). Recognized identically
and just as narrowly.

Usage:  python3 tools/effect_declaration_probe.py [REPO_ROOT]   (default: cwd)
Exit 0 iff no undeclared real-effect callsite remains; exit 1 otherwise.
"""
import ast
import os
import sys

# Atomicity class values the kernel currently accepts at the protocol boundary
# (mirrors ugk.kernel.EffectAtomicity; the probe is source-only and must not
# import the kernel). r102-a implements only NON_ATOMIC; the rest are reserved.
_KNOWN_CLASSES = {"PURE", "STORE_LOCAL", "EXTERNAL_REVERSIBLE", "EXTERNAL_IRREVERSIBLE", "NON_ATOMIC"}
_SCAN_DIRS = ("ugk", "tools", "examples", "construction")


def _is_none_literal(node):
    return isinstance(node, ast.Constant) and node.value is None


def _declared_class(call):
    """Return the declared atomicity class name for an effect_atomicity kwarg, or None."""
    for kw in call.keywords:
        if kw.arg == "effect_atomicity":
            v = kw.value
            # EffectAtomicity.NON_ATOMIC -> Attribute(attr='NON_ATOMIC')
            if isinstance(v, ast.Attribute):
                return v.attr
            # bare NON_ATOMIC (imported name) -> Name(id='NON_ATOMIC')
            if isinstance(v, ast.Name):
                return v.id
            return "<non-literal>"
    return None


def _is_attr_over(node, base, attr):
    """True iff node is exactly `<base>.<attr>` - an Attribute access over a bare Name `base`."""
    return (isinstance(node, ast.Attribute) and node.attr == attr
            and isinstance(node.value, ast.Name) and node.value.id == base)


def _is_request_attr(node, attr):
    """True iff node is exactly `request.<attr>` - an Attribute access over a bare Name `request`."""
    return _is_attr_over(node, "request", attr)


def _is_propagation_seam(kws):
    """A single execute() callsite that propagates BOTH the caller's effect AND the caller's declared
    class verbatim from a carrier, recognized NARROWLY for the two legitimate seams in the tree:

      - r107 / AD-40 broker (LocalBrokerServer): a GovernedRequest named `request` --
        effect=request.effect AND effect_atomicity=request.effect_atomicity;
      - r111 / AD-42 GRBSA ExecutionAdapter: the adapter's own instance --
        effect=self.effect AND effect_atomicity=self.effect_atomicity.

    Deliberately narrow: any other dynamic effect_atomicity value (a different attribute, a bare name,
    or one half of a seam without the matching effect propagation) is NOT recognized and must earn
    recognition explicitly.
    """
    if "effect_atomicity" not in kws or "effect" not in kws:
        return False
    ev, av = kws["effect"].value, kws["effect_atomicity"].value
    broker  = _is_attr_over(ev, "request", "effect") and _is_attr_over(av, "request", "effect_atomicity")
    adapter = _is_attr_over(ev, "self", "effect") and _is_attr_over(av, "self", "effect_atomicity")
    return broker or adapter


def scan(root):
    declared = []      # (path, lineno, class_name)
    undeclared = []    # (path, lineno)
    propagated = []    # (path, lineno) - r107/AD-40 broker propagation seam
    none_effect = 0
    files = 0
    roots = [os.path.join(root, d) for d in _SCAN_DIRS if os.path.isdir(os.path.join(root, d))]
    if not roots:
        roots = [root]
    for base in roots:
        for dirpath, _, fnames in os.walk(base):
            if "__pycache__" in dirpath:
                continue
            for fn in fnames:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    tree = ast.parse(open(p, encoding="utf-8").read())
                except (SyntaxError, UnicodeDecodeError) as e:
                    # A parse failure is itself a contract problem - surface it.
                    undeclared.append((p, "PARSE-FAIL: %s" % e))
                    continue
                files += 1
                for n in ast.walk(tree):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute":
                        kws = {k.arg: k for k in n.keywords}
                        if "effect" not in kws:
                            continue
                        if _is_none_literal(kws["effect"].value):
                            none_effect += 1
                            continue
                        if _is_propagation_seam(kws):
                            # r107/AD-40: the broker propagates the caller's effect AND declared
                            # class verbatim from a GovernedRequest. A propagated declaration -
                            # NOT a class literal and NOT an unknown class.
                            propagated.append((p, kws["effect"].value.lineno))
                            continue
                        cls = _declared_class(n)
                        if cls is None:
                            undeclared.append((p, kws["effect"].value.lineno))
                        else:
                            declared.append((p, kws["effect"].value.lineno, cls))
    return declared, undeclared, propagated, none_effect, files


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    declared, undeclared, propagated, none_effect, files = scan(root)
    print("effect_declaration_probe (r102-a / AD-37; r107 / AD-40 propagation seam)")
    print("  scanned root      : %s" % os.path.abspath(root))
    print("  python files      : %d" % files)
    print("  effect=None calls  : %d  (no declaration required)" % none_effect)
    print("  real-effect calls  : %d declared, %d UNDECLARED" % (len(declared), len(undeclared)))
    print("  propagated declarations: %d  (r107/AD-40 broker + r111/AD-42 adapter seams: effect+class propagated verbatim from the caller's carrier)" % len(propagated))
    # literal class breakdown (kept visible; the propagation seam is NOT a class literal, so the
    # old broker NON_ATOMIC hardcode removal remains visible as a count shift here)
    by_class = {}
    for _, _, c in declared:
        by_class[c] = by_class.get(c, 0) + 1
    if by_class:
        print("  declared classes   : %s" % ", ".join("%s=%d" % (k, by_class[k]) for k in sorted(by_class)))
    # unknown-class declarations are a soft warning (kernel would fail them closed at runtime).
    # The recognized propagation seam is NOT counted here - it is a propagated declaration.
    unknown = sorted({c for _, _, c in declared if c not in _KNOWN_CLASSES})
    print("  unknown classes declared: %d" % len(unknown))
    if unknown:
        print("  WARNING unknown classes declared (kernel fails these closed): %s" % ", ".join(unknown))
    if undeclared:
        print("\nFAIL: real-effect execute() callsites WITHOUT an EffectAtomicity declaration:")
        for p, ln in undeclared:
            print("  %s:%s" % (p, ln))
        return 1
    print("\nPASS: every in-tree real-effect execute() callsite declares an EffectAtomicity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
