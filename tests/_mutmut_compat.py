"""Make the test suite runnable under mutmut's in-process runner.

Two workarounds, both active only when ``MUTANT_UNDER_TEST`` is set (i.e.
inside a mutmut stats or mutant run) and both no-ops for the ordinary test
suite:

1. mutmut 3.6.0's ``record_trampoline_hit`` re-resolves the configured
   ``source_paths`` with ``Path.resolve(strict=True)`` against the
   *current* working directory on every trampoline hit
   (boxed/mutmut#526). Dozens of test modules here change directory into
   per-test temporary trees via ``monkeypatch.chdir``, so under mutmut
   the first product-code call after a ``chdir`` raises
   ``FileNotFoundError`` (``<tmp>/novel_ralph_skill`` does not exist) and
   aborts the stats run. Upstream fixed the hot path on ``main``
   (boxed/mutmut#527), but no released version carries the fix. Until one
   does, this plugin resolves the cached mutmut configuration's
   ``source_paths`` to absolute paths once, at ``pytest_configure`` time,
   while the working directory is still mutmut's ``mutants/`` sandbox
   root; the later strict re-resolutions then operate on absolute,
   existing paths and are immune to ``chdir``.

2. mutmut executes pytest several times inside one process (clean run,
   stats run, then one run per mutant). Class-based ``@given`` tests get
   a fresh instance per pass, so Hypothesis's ``differing_executors``
   health check — which treats each instance as a distinct executor —
   fails the second pass of any such test. A mutmut-only settings profile
   suppresses that health check and lifts the per-example deadline, which
   is timing noise under mutation load; mutmut applies its own per-mutant
   timeout regardless.

The shim lives in its own plugin module rather than ``tests/conftest.py``
because ``conftest`` sits close to the 400-line cap (AGENTS.md lines
24-27); ``conftest`` registers it via ``pytest_plugins``, mirroring
``tests/corpus_fixtures.py``. ``tests/_mutmut_compat.py`` is inside
``PYTHON_TARGETS`` (``Makefile``), so it carries the full Ruff lint and
format, 100% ``interrogate`` docstring coverage, Pylint, and ``ty``
typecheck gates.
"""

from __future__ import annotations

import os
import typing as typ

if typ.TYPE_CHECKING:
    import pytest


def _absolutise_mutmut_source_paths() -> None:
    """Resolve mutmut's configured source paths to absolute paths once.

    The mutmut configuration singleton caches ``source_paths`` exactly as
    written in ``pyproject.toml`` — relative paths — and
    ``record_trampoline_hit`` re-resolves them strictly against the
    current working directory (boxed/mutmut#526). Resolving them here,
    while the working directory is still the ``mutants/`` sandbox root,
    keeps those later strict resolutions valid after tests change
    directory.
    """
    try:
        from mutmut.configuration import Config
    except ImportError:  # pragma: no cover - mutmut absent in plain runs
        return
    configuration = Config.get()
    configuration.source_paths = [path.resolve() for path in configuration.source_paths]


def _load_mutmut_hypothesis_profile() -> None:
    """Register and load a Hypothesis profile tolerant of mutmut's runner.

    mutmut runs pytest repeatedly in one process, so class-based
    ``@given`` tests execute under a fresh instance per pass and trip the
    ``differing_executors`` health check on the second pass. The per-test
    executors are equivalent, so the check is a false positive here. The
    per-example deadline is lifted as well: wall-clock timing under a
    mutation run measures machine load, not the property, and mutmut
    enforces its own per-mutant timeout.
    """
    from hypothesis import HealthCheck, settings

    settings.register_profile(
        "mutmut",
        deadline=None,
        suppress_health_check=[HealthCheck.differing_executors],
    )
    settings.load_profile("mutmut")


def pytest_configure(config: pytest.Config) -> None:
    """Apply the mutmut workarounds before collection starts.

    Parameters
    ----------
    config : pytest.Config
        The pytest configuration object; unused, required by the hook
        signature.
    """
    del config
    if os.environ.get("MUTANT_UNDER_TEST") is None:
        return
    _absolutise_mutmut_source_paths()
    _load_mutmut_hypothesis_profile()
