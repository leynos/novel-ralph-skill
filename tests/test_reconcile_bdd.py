"""Bind the ``reconcile`` recovery scenario to its step module.

This is the behavioural proof of the roadmap 2.3.2 headline success clause
(`docs/roadmap.md:651-652`): a settled tree whose ``state.toml`` claims a done
chapter the drafts deny is detected by ``check`` (exit 4), repaired by
``reconcile`` (exit 0, rewriting ``[word_counts]`` and logging a recovery entry,
removing no file), and re-checked clean (exit 0). It binds
``tests/features/reconcile.feature`` to the step definitions in
``tests/steps/reconcile_steps.py``; the star-import brings the
``given``/``when``/``then`` callables into this module's namespace where
``scenarios`` discovers them, mirroring the ``recount`` wiring.
"""

from __future__ import annotations

from pytest_bdd import scenarios
from steps.reconcile_steps import *  # noqa: F403 - register pytest-bdd step defs

scenarios("features/reconcile.feature")
