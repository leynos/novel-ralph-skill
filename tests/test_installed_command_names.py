"""Pin the registry-sourced legacy-to-spaced derivation the installed e2e use.

The installed-binary e2e suites migrate (roadmap task 1.2.13) from invoking the
legacy per-command console-scripts (``novel-state``, ``desloppify``, …) to
invoking the single ``novel`` multiplexer with a spaced subcommand surface
(``novel state``, ``novel desloppify``, …). Each consumer derives the spaced
envelope name and the multiplexer *mount verb* **inline from production code**
(:mod:`novel_ralph_skill.commands.names`), never from a shared test-module value
(ExecPlan Decision Log D8). This fast in-process unit test pins that derivation:

- ``dict(zip(COMMAND_NAMES, SUBCOMMAND_NAMES, strict=True))`` maps each legacy
  name to its spaced name, because the two tuples pair positionally in surface
  order;
- the mount verb for a spaced name ``s`` is ``s.split(" ", 1)[1]``, exact because
  every spaced name is exactly ``"novel <verb>"``.

By asserting the positional pairing and the two-token shape, a future registry
reordering or rename fails loudly here rather than silently mis-mapping the
installed invocations. This module imports **only** production ``names`` — no
test-module value import — so it carries no cross-module test coupling.
"""

from __future__ import annotations

from novel_ralph_skill.commands.names import COMMAND_NAMES, SUBCOMMAND_NAMES


def test_legacy_to_spaced_pairing() -> None:
    """Each legacy console-script name maps to its spaced multiplexer name."""
    spaced = dict(zip(COMMAND_NAMES, SUBCOMMAND_NAMES, strict=True))
    assert spaced == {
        "novel-state": "novel state",
        "novel-done": "novel done",
        "novel-compile": "novel compile",
        "desloppify": "novel desloppify",
        "wordcount": "novel wordcount",
    }


def test_mount_verb_derivation() -> None:
    """The mount verb is the bare second token of each spaced name."""
    verbs = [spaced.split(" ", 1)[1] for spaced in SUBCOMMAND_NAMES]
    assert verbs == ["state", "done", "compile", "desloppify", "wordcount"]
    for spaced in SUBCOMMAND_NAMES:
        head, _, verb = spaced.partition(" ")
        assert head == "novel"
        assert verb
        assert " " not in verb


def test_registry_tuples_pair_positionally() -> None:
    """``COMMAND_NAMES`` and ``SUBCOMMAND_NAMES`` share length and surface order.

    This is the loud-failure guard for a future registry reordering: it is what
    makes ``zip(..., strict=True)`` an exact legacy-to-spaced pairing rather than
    a silent mis-mapping.
    """
    assert len(COMMAND_NAMES) == len(SUBCOMMAND_NAMES)
    assert all(spaced.startswith("novel ") for spaced in SUBCOMMAND_NAMES)
