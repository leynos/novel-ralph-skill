"""Bind the ``novel-done`` six-clause scenarios to their step module.

This is the behavioural proof of the roadmap 3.1.1 success criterion: the
predicate exits ``0`` only on the all-six-clauses-hold tree and ``1`` while any
single clause is false (design §4.2, §3.2). It binds
``tests/features/novel_done.feature`` to the step definitions in
``tests/steps/novel_done_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``recount`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.novel_done_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/novel_done.feature")
