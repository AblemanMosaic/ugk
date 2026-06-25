"""ugk.module_registry — logical identity of constitutionally-significant modules.

PURPOSE (path-decoupling): conformance gates historically referenced protected modules by
root-relative FILENAME literals ("store.py", "kernel.py", ...). That coupled constitutional
identity to physical file paths, which blocked any physical package reorganization (moving a
file silently broke a gate, and law_hash could be perturbed by blanket import rewrites).

This registry declares the SEMANTIC SET of protected/structural modules by their IMPORTABLE
identity. Gates resolve a module's actual on-disk file via `importlib`/`__file__` at runtime,
so the gate follows the module wherever it physically lives. The constitutional STATEMENT
("these modules are Grundnorm / read-only / structural") is preserved; the PATH MECHANISM is
removed.

This module imports nothing from the substrate at load time (only stdlib), so it adds no
import-cycle risk and is safe for gates to import.
"""
from __future__ import annotations
import importlib
from pathlib import Path

# --- The Grundnorm set: constitutionally protected modules (must be read-only 444). ---
# Declared by DOTTED MODULE NAME (logical identity), NOT filename. Order is not significant.
GRUNDNORM_MODULES = (
    "ugk.kernel",
    "ugk.schema",
    "ugk.storage.store",
    "ugk.storage.binding",
    "ugk.transport.broker",
    "ugk.invariants",
    "ugk.dimensions",
)

# --- The law module: the single source of law_hash. Stable at package root by design. ---
LAW_MODULE = "ugk.invariants"

# --- Public facade surfaces (thin-facade structural proof). ---
FACADE_SURFACES = (
    "ugk.cli",
    "ugk.transport.rpc",
    "ugk.transport.agent",
)

# --- Constitutional-record module (record-consistency gate). ---
RECORD_MODULE = "ugk.adr"


def resolve_path(dotted: str) -> Path:
    """Resolve a dotted module name to its on-disk file Path via import identity.

    This is the decoupling primitive: a gate asks for the module by logical name and gets
    its current physical location, so moving the file does not break the gate.
    """
    mod = importlib.import_module(dotted)
    f = getattr(mod, "__file__", None)
    if f is None:
        raise RuntimeError(f"module {dotted!r} has no __file__ (namespace package?)")
    return Path(f).resolve()


def grundnorm_paths() -> list[Path]:
    """Resolve all Grundnorm modules to their current on-disk paths (by identity)."""
    return [resolve_path(m) for m in GRUNDNORM_MODULES]


def law_path() -> Path:
    """Resolve the law module (ugk.invariants) to its on-disk path."""
    return resolve_path(LAW_MODULE)


def facade_paths() -> list[Path]:
    return [resolve_path(m) for m in FACADE_SURFACES]


def record_path() -> Path:
    return resolve_path(RECORD_MODULE)


__all__ = [
    "GRUNDNORM_MODULES", "LAW_MODULE", "FACADE_SURFACES", "RECORD_MODULE",
    "resolve_path", "grundnorm_paths", "law_path", "facade_paths", "record_path",
]
