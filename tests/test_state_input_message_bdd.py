"""Bind the cross-class actionable exit-3 message scenario to its step module.

This is the behavioural proof of the roadmap §6.3.1 success criterion: a mutator,
a checker, and a reader each run from a directory with no ``working/`` tree exit
``3`` with an actionable, cwd-naming, ``novel state init``-suggesting message that
carries no raw ``Errno`` and is byte-for-byte identical across the three classes
(design §3.2; ADR-003). It binds ``tests/features/state_input_message.feature`` to
the step definitions in ``tests/steps/state_input_message_steps.py``; the
star-import brings the ``given``/``when``/``then`` callables into this module's
namespace where ``scenarios`` discovers them, mirroring the ``recount`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.state_input_message_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/state_input_message.feature")
