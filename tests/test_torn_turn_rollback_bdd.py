"""Bind the torn-turn ROLLBACK scenario to its step module.

This is the behavioural proof of roadmap task 6.2.7 — the symmetric half of the
disposition task 6.2.5 proved for COMPLETE. A torn ``[pending_turn]`` produced by
a *real* §3.4 ``pending_turn`` bracket raising mid-turn over a coherent baseline —
declaring an unrecoverable ``draft.md`` that never lands — is detected by
``check`` (exit 4, ``rollback-pending-turn``) and rolled back by ``reconcile`` in
a single pass (exit 0): the record cleared, a ``rollback-pending-turn`` receipt
appended to ``log.md``, a follow-up ``check`` clean, the author-owned drafts
byte-for-byte intact, and no ``working/`` file removed — every command driven
through the command entry path, not the bracket primitive. It binds
``tests/features/torn_turn_rollback.feature`` to the step definitions in
``tests/steps/torn_turn_rollback_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the recovery wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.torn_turn_rollback_steps import *  # noqa: F403 - register step defs

scenarios("features/torn_turn_rollback.feature")
