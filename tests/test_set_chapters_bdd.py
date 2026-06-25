"""Bind the ``set-chapters`` behavioural scenarios to their step module.

This is the behavioural proof of the roadmap 2.2.3 success criteria: a coherent
plan reaches ``[chapters]`` only through the command and ``check`` then exits 0;
an incoherent, duplicate, or re-run plan is refused with exit 3 and writes
nothing; and a partial-directory torn turn is completed by ``reconcile`` (design
§4.1, §5.1, §5.2, §5.4; ADR 008). It binds ``tests/features/set_chapters.feature``
to the step definitions in ``tests/steps/set_chapters_steps.py``; the star-import
brings the ``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``recount`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.set_chapters_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/set_chapters.feature")
