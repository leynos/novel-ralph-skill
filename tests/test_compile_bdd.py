"""Bind the ``novel-compile`` regeneration scenarios to their step module.

This is the behavioural proof of the roadmap 4.1.1 success criteria: a compile
over a three-chapter drafting tree regenerates the manifest-ordered
``compiled.md`` and is byte-for-byte idempotent on a second run, while an empty
chapter manifest refuses with exit ``3`` and writes nothing (design §4.3, §10).
It binds ``tests/features/compile.feature`` to the step definitions in
``tests/steps/compile_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``recount`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.compile_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/compile.feature")
