"""Bind the ``set-gate`` behavioural scenarios to their step module.

This is the named-command behavioural proof of the headline ``set-gate`` mutator's
roadmap 2.2.4 arms: a ``--knitting-30`` repair on a crossed-ratio prior exits ``0``
and stays coherent, the same flag on a sub-threshold prior is refused (exit ``3``,
file intact), and a no-flag ``set-gate`` faults with the usage envelope (exit
``2``, file intact) (design sections 4.1, 5.2). It binds
``tests/features/set_gate.feature`` to the step definitions in
``tests/steps/set_gate_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``complete_final_pass`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.set_gate_steps import *  # noqa: F403 - register pytest-bdd steps

scenarios("features/set_gate.feature")
