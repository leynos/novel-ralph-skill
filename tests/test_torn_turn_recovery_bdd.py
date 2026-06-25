"""Bind the torn-turn recovery scenario to its step module.

This is the behavioural proof of roadmap task 6.2.5: a torn ``[pending_turn]``
produced by a *real* interrupted ``novel-state reconcile`` command is detected by
``check`` (exit 4, ``complete-pending-turn``) and recovered by ``reconcile``
(re-run under bounded harness re-entry, each exit 0) until a follow-up ``check``
is clean, with the author-owned drafts byte-for-byte intact and no ``working/``
file removed — every command driven through the command entry path, not the
bracket primitive. It binds ``tests/features/torn_turn_recovery.feature`` to the
step definitions in ``tests/steps/torn_turn_recovery_steps.py``; the star-import
brings the ``given``/``when``/``then`` callables into this module's namespace
where ``scenarios`` discovers them, mirroring the ``reconcile`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.torn_turn_recovery_steps import *  # noqa: F403 - register step defs

scenarios("features/torn_turn_recovery.feature")
