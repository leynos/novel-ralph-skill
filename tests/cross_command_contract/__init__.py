"""The cross-command envelope-and-exit-code identity proof (roadmap 6.3.2).

This package is the single home for the suite that proves every one of the
harness's five spaced commands (``novel state``, ``novel done``,
``novel compile``, ``novel desloppify``, ``novel wordcount``) presents the
*same* output contract: the same six-field envelope skeleton in the same order
with the same field types, the same ``ok`` to exit-code mapping, and the same
error-channel shapes (design §3.1, §3.2; ADR-003 Table 2). Where §6.2.1's
command-surface matrix (``tests/test_command_surface_matrix.py``) pins each
*read* command's own shape across the eleven phases, this package asserts the
shapes are *identical across commands* and extends the identity proof to the
``novel state`` mutators §6.2.1 explicitly excluded (its module docstring lines
54-71).

The package is split by concern (envelope shape, ok/exit mapping, error
channels, mutator identity) so no module breaches the 400-line cap (AGENTS.md).
Every module drives in-process through
:func:`novel_ralph_skill.contract.runner.run` over the ``working_corpus`` trees,
reusing the shared ``drive`` fixture and redaction helpers promoted to
``tests/contract_drive_support.py``.

Carried gaps (documented rather than silently omitted, design §9 lines 819-821).
The corpus does not let every command reach every exit-code channel, so the
suite asserts exactly the constructible (command, channel) cells and carries the
rest as named gaps:

- exit 4 (actionable finding) is constructible for only ``novel state check``
  (an ``incoherent_tree`` variant), ``novel compile --check`` (a ``drafting``
  tree), and ``novel desloppify`` (an em-dash-flood draft); ``novel done`` and
  ``novel wordcount`` cannot reach it over the corpus, so their exit-4 cells are
  carried gaps;
- exit 1 (benign negative) is constructible only for ``novel done`` (the corpus
  never satisfies its done predicate), so every other command's exit-1 cell is a
  carried gap;
- the usage (exit 2) and state (exit 3) arms are command-agnostic — ``--nope``
  faults at parse and an absent ``working/`` faults at load identically for all
  five commands — so they are the cross-command identity arms.
"""

from __future__ import annotations

import typing as typ

from contract_drive_support import CommandSpec

from novel_ralph_skill.commands import (
    _compile,
    _desloppify,
    _novel_done,
    _wordcount,
    novel_state,
)
from novel_ralph_skill.contract.envelope import ENVELOPE_FIELD_ORDER

# The five spaced command surfaces under the cross-command identity proof.
# ``novel state`` is keyed on its read ``check`` query; ``novel compile`` on
# ``--check`` (the read-only checker, never the write path). These are the
# body-producing argvs every shared-skeleton assertion drives, distinct from the
# mutator argvs ``test_mutator_identity`` builds.
COMMANDS: typ.Final[tuple[CommandSpec, ...]] = (
    CommandSpec("novel state", novel_state.build_app, ["check"]),
    CommandSpec("novel done", _novel_done.build_app, []),
    CommandSpec("novel wordcount", _wordcount.build_app, []),
    CommandSpec("novel compile", _compile.build_app, ["--check"]),
    CommandSpec("novel desloppify", _desloppify.build_app, []),
)

# The phase whose coherent tree every command can be driven over to produce a
# body envelope. ``final-pass`` carries a populated three-chapter manifest and a
# matching ``compiled.md``, so ``novel compile --check`` passes (exit 0) here
# rather than refusing (exit 3) as it does over the pre-drafting phases.
BODY_PHASE: typ.Final[str] = "final-pass"

# The fixed working-directory constant every envelope stamps (design §3.1); the
# harness always operates on the ``working/`` directory, never a flag-supplied
# path.
WORKING_DIR_CONSTANT: typ.Final[str] = "working"

# The six contract-fixed envelope keys, in the order ``render_machine`` emits
# them (``result`` before ``messages``; ADR-003, design §3.1). Every command's
# machine envelope must carry exactly these keys in this order. Re-exported from
# the canonical ``novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER`` so
# this package carries no second hand-spelled copy of the order.
ENVELOPE_KEY_ORDER: typ.Final[tuple[str, ...]] = ENVELOPE_FIELD_ORDER
