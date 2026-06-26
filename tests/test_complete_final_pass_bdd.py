"""Bind the ``complete-final-pass`` behavioural scenario to its step module.

This is the named-command behavioural proof of the roadmap 2.2.4 success
criterion: ``complete-final-pass`` flips ``gates.final.final_pass_complete`` true
and leaves the tree coherent so a follow-up ``novel-state check`` exits ``0``
(design §4.1). It binds ``tests/features/complete_final_pass.feature`` to the step
definitions in ``tests/steps/complete_final_pass_steps.py``; the star-import brings
the ``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``advance_phase`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.complete_final_pass_steps import *  # noqa: F403 - register pytest-bdd steps

scenarios("features/complete_final_pass.feature")
