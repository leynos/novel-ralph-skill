"""Bind the torn-multi-file-turn ``pytest-bdd`` scenario to its step module.

This is the suite's first behavioural test (AGENTS.md mandates ``pytest-bdd``
for behavioural tests). It binds ``tests/features/torn_turn.feature`` to the step
definitions in ``tests/steps/torn_turn_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them.

The scenario proves the roadmap 2.2.1 success criterion: a write interrupted
before completion leaves a populated ``[pending_turn]`` record for the next turn
to reconcile (design §3.4, §10).
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.torn_turn_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/torn_turn.feature")
