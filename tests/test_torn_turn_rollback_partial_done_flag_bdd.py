"""Bind the partial-landed done.flag torn-turn ROLLBACK scenario to its steps.

This is the behavioural proof of roadmap task 6.2.14 — the partial-landed
``done.flag`` sibling of the partial-landed ``draft.md`` ROLLBACK scenario task
6.2.12 added, and the residue-bearing counterpart of the never-landed
``done.flag`` row task 6.2.13 added. A torn ``[pending_turn]`` produced by a
*real* §3.4 ``pending_turn`` bracket raising mid-turn over a coherent baseline —
declaring an unrecoverable ``working/manuscript/chapter-99/done.flag`` (operation
``mark-done``) that never lands, *after a partial done.flag residue landed* as a
``.tmp`` sibling inside an existing manifest chapter directory (the §3.4 temp-file
remnant a ``Path.replace`` never promoted) — is detected by ``check`` (exit 4,
``rollback-pending-turn``) and rolled back by ``reconcile`` in a single pass (exit
0): the record cleared, a ``rollback-pending-turn`` receipt appended to
``log.md``, a follow-up ``check`` clean, the partial residue preserved
byte-for-byte on disk and unreferenced by state, the author-owned drafts
byte-for-byte intact, no ``working/`` file removed, and no unexpected file
fabricated — every command driven through the command entry path, not the bracket
primitive (design §5.4 item 2). It closes the partial-landed ``done.flag`` cell of
the §5.4 rollback surface left after 6.2.12 and 6.2.13.

It binds ``tests/features/torn_turn_rollback_partial_done_flag.feature`` to the
step definitions in ``tests/steps/torn_turn_rollback_partial_done_flag_steps.py``;
the star-import brings the ``given``/``when``/``then`` callables into this module's
namespace where ``scenarios`` discovers them, mirroring the partial-landed
``draft.md`` ROLLBACK wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.torn_turn_rollback_partial_done_flag_steps import *  # noqa: F403 - register steps

scenarios("features/torn_turn_rollback_partial_done_flag.feature")
