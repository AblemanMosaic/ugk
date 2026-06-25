"""tools/cgproj/execution_jurisdiction.py — THE single authoritative execution-jurisdiction set.

Consumed by BOTH the Phase 2 (Execution Removability / Non-Authority) gate and the Phase 4.5
(Jurisdiction) gate, so the jurisdiction boundary cannot silently drift between them. Changing the
execution-jurisdiction definition is changing it for every gate at once — which is the point.

Two representations of the SAME boundary:
  * EXECUTION_MODULE_PREFIXES — module-name prefixes; the authoritative boundary used for import
    barriers and for detecting which execution modules loaded in a process.
  * EXECUTION_MODULE_FILES — named source files under the repo, used for static import scanning.
The conformance gate directory (ugk/conformance/) is ALSO part of the execution jurisdiction for
static scanning; helpers below expand it.

This module is non-runtime test tooling (stdlib only); it imports nothing from ugk.
"""
import os

# Authoritative boundary: execution-jurisdiction module-name prefixes.
EXECUTION_MODULE_PREFIXES = (
    "ugk.kernel",
    "ugk.invariants",
    "ugk.module_registry",
    "ugk.storage",
    "ugk.governance",
    "ugk.authority",
    "ugk.scale",
    "ugk.schema",
    "ugk.transport",
    "ugk.core",
    "ugk.conformance",
)

# Named execution-jurisdiction source files (static-scan surface).
EXECUTION_MODULE_FILES = (
    "ugk/kernel.py", "ugk/invariants.py", "ugk/module_registry.py",
    "ugk/storage/store.py", "ugk/storage/binding.py",
    "ugk/governance/policy.py", "ugk/governance/governor.py", "ugk/governance/warrant.py",
    "ugk/authority/authority_model.py", "ugk/capabilities.py",
    "ugk/scale/oracle.py", "ugk/scale/scheduler.py",
)


def is_execution_module(name):
    """True iff a module name is in the execution jurisdiction."""
    return any(name == p or name.startswith(p + ".") for p in EXECUTION_MODULE_PREFIXES)


def loaded_execution_modules(modules):
    """Given an iterable of module names (e.g. sys.modules), return the execution ones, sorted."""
    return sorted(m for m in modules if is_execution_module(m))


def static_scan_files(repo):
    """All execution-jurisdiction source files to scan: named files + every ugk/conformance/*.py."""
    files = [os.path.join(repo, rel) for rel in EXECUTION_MODULE_FILES]
    conf_dir = os.path.join(repo, "ugk", "conformance")
    if os.path.isdir(conf_dir):
        for dp, _, fns in os.walk(conf_dir):
            for f in fns:
                if f.endswith(".py"):
                    files.append(os.path.join(dp, f))
    return [f for f in files if os.path.exists(f)]


# --- Same-process import barrier (does NOT rely on startup sitecustomize ordering) ---
# The prior sitecustomize approach could be shadowed by an earlier sitecustomize on sys.path in some
# environments, leaving the barrier inactive. Instead we install the meta_path barrier DIRECTLY in
# the target process as a prelude, before importing/running anything, then run the target via runpy.
import subprocess


def barrier_prelude(prefixes, sentinel_path, repo):
    """Python source that, run FIRST in a process, installs a meta_path import barrier for `prefixes`,
    writes a sentinel proving it ran in THIS process, and puts `repo` on sys.path. No sitecustomize."""
    return (
        "import sys\n"
        "sys.path.insert(0, " + repr(repo) + ")\n"
        "from importlib.abc import MetaPathFinder\n"
        "open(" + repr(sentinel_path) + ", 'a').write('loaded\\n')\n"
        "_PREFIXES = " + repr(tuple(prefixes)) + "\n"
        "class _Bar(MetaPathFinder):\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        for p in _PREFIXES:\n"
        "            if name == p or name.startswith(p + '.'):\n"
        "                raise ImportError('barred jurisdiction module: ' + name)\n"
        "        return None\n"
        "sys.meta_path.insert(0, _Bar())\n"
    )


import tempfile as _tempfile, os as _os, signal as _signal

class _BR:
    """Result shim (.returncode/.stdout/.stderr) for the bounded runner."""
    def __init__(self, rc, out): self.returncode = rc; self.stdout = out; self.stderr = ""

def bounded_run(cmd, *, env=None, cwd=None, timeout=120):
    """Grandchild-proof bounded runner: own process group (start_new_session), output to a temp FILE
    (never an OS pipe -> no deadlock when a grandchild holds the stdout FD), whole process group killed
    on timeout. Returns within ~timeout instead of hanging. Shared by phase2 + the barrier runners."""
    with _tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as f:
        proc = subprocess.Popen(cmd, env=env, cwd=cwd, stdout=f, stderr=subprocess.STDOUT,
                                text=True, start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                _os.killpg(_os.getpgid(proc.pid), _signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(); f.seek(0); return _BR(124, f.read())
        f.seek(0); return _BR(proc.returncode, f.read())


def run_module_under_barrier(py, module, prefixes, sentinel_path, repo, *, env=None, cwd=None, timeout=120):
    """Run `python -m module` equivalent under an in-process barrier (via runpy), barrier proven by sentinel."""
    code = barrier_prelude(prefixes, sentinel_path, repo) + \
        "import runpy; runpy.run_module(" + repr(module) + ", run_name='__main__')\n"
    return bounded_run([py, "-c", code], env=env, cwd=cwd, timeout=timeout)


def run_code_under_barrier(py, code_after, prefixes, sentinel_path, repo, *, env=None, cwd=None, timeout=120):
    """Run arbitrary `code_after` under an in-process barrier (barrier installed first, proven by sentinel)."""
    code = barrier_prelude(prefixes, sentinel_path, repo) + code_after
    return bounded_run([py, "-c", code], env=env, cwd=cwd, timeout=timeout)


__all__ = [
    "EXECUTION_MODULE_PREFIXES", "EXECUTION_MODULE_FILES",
    "is_execution_module", "loaded_execution_modules", "static_scan_files",
    "barrier_prelude", "run_module_under_barrier", "run_code_under_barrier",
]
