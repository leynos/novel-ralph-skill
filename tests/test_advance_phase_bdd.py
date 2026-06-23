"""Bind the out-of-order ``advance-phase`` refusal scenario to its step module.

This is the behavioural proof of the roadmap 2.2.2 success criterion: an
out-of-order ``advance-phase`` is refused with exit ``3`` and leaves the prior
state intact (design §3.2, §4.1, §9). It binds
``tests/features/advance_phase_refusal.feature`` to the step definitions in
``tests/steps/advance_phase_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``torn_turn`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.advance_phase_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/advance_phase_refusal.feature")
