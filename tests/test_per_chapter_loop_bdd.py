"""Bind the in-process per-chapter deterministic-loop scenarios (roadmap 6.2.2).

This is the behavioural proof that the deterministic spine composes over a real
``working/`` tree (design §7.2, §9): a coherent chapter passes ``recount``,
``novel-done``, ``wordcount``, ``desloppify``, and ``novel-compile --check``
clean, a stale compile is caught, a crossed knitting gate is reported, and an
out-of-order phase advance is refused — every command driven through the shared
command boundary, not the body call. It binds
``tests/features/per_chapter_loop.feature`` to the step definitions in
``tests/steps/per_chapter_loop_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring ``tests/test_torn_turn_recovery_bdd.py``.

The import root is ``steps.<module>``, not ``tests.steps.<module>``:
``pyproject.toml`` sets ``testpaths = ["tests"]`` with no ``tests`` package import
root, so a ``tests.steps...`` import would ``ModuleNotFoundError`` (ExecPlan
advisory A2). This binder carries **no** marks: its scenarios run on every
platform under the global 30s timeout. The ``@slow``, POSIX-only installed
re-drive lives in its own feature and ``@scenario``-decorated binder
(``tests/test_per_chapter_loop_installed_bdd.py``) so no marker leaks across the
platform boundary (ExecPlan Decision D-INSTALLED-SPLIT).
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.per_chapter_loop_steps import *  # noqa: F403 - register step defs

scenarios("features/per_chapter_loop.feature")
