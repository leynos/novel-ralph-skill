"""Bind the ``recount`` re-derivation scenario to its step module.

This is the behavioural proof of the roadmap 2.3.1 success criteria: a recount
over a tree with two drafted chapters writes the summed counts and is idempotent
on a second run (design §4.1, §5.2 invariant 3, §9). It binds
``tests/features/recount.feature`` to the step definitions in
``tests/steps/recount_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``advance_phase`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.recount_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/recount.feature")
