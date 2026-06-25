"""Bind the partial-landed torn-turn ROLLBACK scenario to its step module.

This is the behavioural proof of roadmap task 6.2.12 — the *partial-landed*
sibling of the *never-landed* ROLLBACK scenario task 6.2.7 added. A torn
``[pending_turn]`` produced by a *real* §3.4 ``pending_turn`` bracket raising
mid-turn over a coherent baseline — declaring an unrecoverable next-chapter
``draft.md`` that never lands, *after a partial draft residue landed* inside an
existing manifest chapter directory (the §3.4 temp-file remnant a ``Path.replace``
never promoted) — is detected by ``check`` (exit 4, ``rollback-pending-turn``)
and rolled back by ``reconcile`` in a single pass (exit 0): the record cleared, a
``rollback-pending-turn`` receipt appended to ``log.md``, a follow-up ``check``
clean, the partial residue preserved byte-for-byte on disk and unreferenced by
state, the author-owned drafts byte-for-byte intact, no ``working/`` file removed,
and no unexpected file fabricated — every command driven through the command
entry path, not the bracket primitive (design §5.4 item 2). It binds
``tests/features/torn_turn_rollback_partial.feature`` to the step definitions in
``tests/steps/torn_turn_rollback_partial_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the never-landed ROLLBACK wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.torn_turn_rollback_partial_steps import *  # noqa: F403 - register steps

scenarios("features/torn_turn_rollback_partial.feature")
