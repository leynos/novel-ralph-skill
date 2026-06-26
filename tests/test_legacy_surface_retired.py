"""Durable manifest that the legacy console-script surface is fully retired.

Roadmap task 1.2.15 removed the five legacy entry points
(``novel-state``/``novel-done``/``novel-compile``/``desloppify``/``wordcount``),
the ``novel_ralph_skill.commands.stub`` module, and the
``COMMAND_NAMES``/``COMMAND_ENTRY_POINTS``/``STUB_MODULE`` registry symbols,
leaving exactly one ``novel`` multiplexer console-script. This module is the
lasting regression guard the one-shot grep gates cannot be: it asserts on the
*imported symbols* and the *parsed* ``[project.scripts]`` table — immune to the
two grep pitfalls the ExecPlan documents (``SUBCOMMAND_NAMES`` substring-matches
``COMMAND_NAMES``; the snapshots store the command in three serialisations) —
plus two source-scan cases that pin the idiom-bearing and human-output stamps no
symbol check can see (ExecPlan Decision Log D6/D7/D8, B3/B6/B7/B8).
"""

from __future__ import annotations

import importlib.util
import typing as typ

from novel_ralph_skill.commands import names

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

# The five legacy console-script literals, hyphenated where they were hyphenated.
_LEGACY_LITERALS: tuple[str, ...] = (
    "novel-state",
    "novel-done",
    "novel-compile",
    "desloppify",
    "wordcount",
)

# The four idiom-bearing source modules that stamp a legacy command name through
# a shape the ``COMMAND_NAMES``/``command="…"`` patterns cannot see (ExecPlan
# ``$IDIOM_SOURCES``; B3/B6/B7). After 1.2.15 none carries a *hyphenated* legacy
# command literal; the kept module aliases (``_desloppify``/``_wordcount``) and
# the bare mount verbs (``desloppify``/``wordcount`` as argv tokens or Gherkin
# step text) are not legacy command-name stamps, so the guard scans for the
# hyphenated forms — the only shape a stamp now takes.
_IDIOM_SOURCES: tuple[str, ...] = (
    "tests/test_command_surface_matrix.py",
    "tests/steps/per_chapter_loop_steps.py",
    "tests/multiplexer_support.py",
    "tests/test_multiplexer_behaviour.py",
)

# The six in-process e2e modules WI3 re-pointed from ``stub.<entry>()`` onto
# ``novel.main()``; the durable B8 guard scans them for a human-rendered
# ``command: <legacy>`` header (the colon-space form ``render_human`` emits).
_REPOINTED_E2E: tuple[str, ...] = (
    "tests/test_reconcile_e2e.py",
    "tests/test_compile_e2e.py",
    "tests/test_compile_check_integration.py",
    "tests/test_novel_state_check.py",
    "tests/test_set_chapters_e2e.py",
    "tests/test_recount_e2e.py",
)


def test_registry_drops_the_legacy_symbols() -> None:
    """``names`` exposes none of the deleted legacy registry symbols."""
    assert not hasattr(names, "COMMAND_NAMES")
    assert not hasattr(names, "COMMAND_ENTRY_POINTS")
    assert not hasattr(names, "STUB_MODULE")


def test_stub_module_is_gone() -> None:
    """The legacy ``stub`` module no longer exists as an importable module."""
    assert importlib.util.find_spec("novel_ralph_skill.commands.stub") is None


def test_script_table_is_novel_only() -> None:
    """The registry-derived ``[project.scripts]`` table is exactly ``novel``."""
    assert tuple(names.project_scripts_table()) == ("novel",)


def test_pyproject_scripts_is_novel_only(
    pyproject: dict[str, object],
    project_scripts: cabc.Callable[[cabc.Mapping[str, object]], dict[str, object]],
) -> None:
    """The parsed ``[project.scripts]`` table has exactly the ``novel`` key."""
    assert tuple(project_scripts(pyproject)) == ("novel",)


def _stamp_lines(text: str) -> str:
    """Return ``text`` minus the lines that are not legacy command-name stamps.

    Two residue classes legitimately retain a hyphenated legacy substring after
    1.2.15 and are excluded so the membership check is a true stamp guard
    (ExecPlan Surprises, WI2 implementation): the ``@when``/``@then``/``@given``
    Gherkin step-binding decorators in the per-chapter-loop steps (which must
    match ``tests/features/per_chapter_loop.feature`` verbatim — scenario prose
    scoped to the 1.2.14/1.2.16 sweeps), and any per-step docstring that mirrors
    that step text. A genuine stamp (a dict key, ``RunContext`` value,
    ``_ReadCommand``/``_BY_NAME`` literal, or ``_Operation`` field) never lives on
    a decorator line, so dropping them cannot hide a re-introduced stamp.
    """
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("@when(", "@then(", "@given(")):
            continue
        kept.append(line)
    return "\n".join(kept)


def test_no_legacy_command_literals_in_idiom_sources(project_root: Path) -> None:
    """No idiom-bearing source module carries a hyphenated legacy command stamp.

    The B3/B6/B7 durable guard: these four modules stamp a legacy command name
    through a dict key, helper argument, ``NamedTuple`` field, or
    ``_ReadCommand``/``_BY_NAME``/``if name ==`` literal — shapes the symbol
    checks above cannot see. After the 1.2.15 sweep each carries only the spaced
    ``novel <verb>`` names; a re-introduced hyphenated stamp fails here without
    waiting for the guard to narrow. The Gherkin step-binding decorators (which
    must match the unswept feature file) are excluded — see :func:`_stamp_lines`.
    """
    hyphenated = tuple(literal for literal in _LEGACY_LITERALS if "-" in literal)
    for rel in _IDIOM_SOURCES:
        text = _stamp_lines((project_root / rel).read_text(encoding="utf-8"))
        for literal in hyphenated:
            assert literal not in text, f"{rel} re-introduced {literal!r}"


def test_no_legacy_human_command_header_in_repointed_e2e(project_root: Path) -> None:
    """No re-pointed e2e module asserts a human-rendered ``command: <legacy>``.

    The B8 durable guard: ``render_human`` emits ``command: <name>`` (colon-space),
    a shape neither the symbol checks nor the idiom scan above catch. Each
    re-pointed module now drives ``novel.main()`` (stamping ``command: novel
    <verb>``), so a re-introduced ``command: <legacy>`` human header fails here.
    """
    for rel in _REPOINTED_E2E:
        text = (project_root / rel).read_text(encoding="utf-8")
        for literal in _LEGACY_LITERALS:
            assert f"command: {literal}" not in text, (
                f"{rel} re-introduced human header 'command: {literal}'"
            )
