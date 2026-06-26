"""Bind the cross-command contract scenarios to their step module (roadmap 6.3.2).

This is the behavioural, human-readable face of the cross-command envelope-and-
exit-code identity proof (Work item 3): a parametrised ``Scenario Outline`` over
the five spaced commands asserting the shared envelope skeleton, the ok-to-exit
mapping, and the two command-agnostic error-channel shapes (usage, state). It
binds ``tests/features/cross_command_contract.feature`` to the step definitions
in ``tests/steps/cross_command_contract_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the other ``*_bdd`` binders.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.cross_command_contract_steps import *  # noqa: F403 - register step defs

scenarios("features/cross_command_contract.feature")
