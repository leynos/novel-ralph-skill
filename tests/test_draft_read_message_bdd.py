"""Bind the cross-boundary actionable draft-read message scenarios to their steps.

This is the behavioural proof of the roadmap §6.3.5 success criterion: each
draft-read boundary, driven against a coherent ``working/`` tree whose first
chapter ``draft.md`` is corrupt, exits ``3`` with an actionable message that names
the ``working/`` tree and an inspect/repair remedy and leaks no raw ``Errno``,
``{exc}`` repr, traceback, ``init`` suggestion, or old raw string; and the mutator
view-derivation boundary reuses the ``_state_input_error`` present-but-corrupt
remedy naming the ``state.toml`` path, kept distinct from the draft-read prose
(ExecPlan Decision D7; design §3.2; ADR-003). It binds
``tests/features/draft_read_message.feature`` to the step definitions in
``tests/steps/draft_read_message_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``state_input_message`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.draft_read_message_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/draft_read_message.feature")
