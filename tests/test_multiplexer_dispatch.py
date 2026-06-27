"""Unit tests for the ``novel`` multiplexer shape (roadmap task 1.2.12, ADR 007).

ADR 007 fixes the final command surface as a single ``novel`` multiplexer:
``novel state …``, ``novel done``, ``novel compile``, ``novel desloppify``, and
``novel wordcount``. This module pins the *shape* of the dispatcher built by
:func:`novel_ralph_skill.commands.novel.build_multiplexer`: it carries the
four-flag contract (the tripwire mirroring ``tests/test_contract_app_factory.py``
so a dropped flag fails here rather than silently changing exit behaviour), and
``_command_name_for`` maps residual argv to the spaced registry name driven from
the registry, not inline literals. The registered-mounts assertion — that the
built parent registers exactly the construction table's (and so the registry's)
verbs — lives once in ``tests/test_multiplexer_mount_table.py``
(``test_build_multiplexer_registers_exactly_the_table_verbs``), tied to the
registry rather than to a hand-spelled verb literal, so it is not duplicated
here.

The in-process behavioural coverage — legacy-vs-multiplexer envelope equality
over the corpus and every exit arm — lives in
``tests/test_multiplexer_behaviour.py``; the shared ``driver`` fixture comes from
``tests/multiplexer_support.py`` (registered through ``conftest``).
"""

from __future__ import annotations

import pytest

from novel_ralph_skill.commands import novel
from novel_ralph_skill.commands.names import SUBCOMMAND_NAMES, verb_for

# The three boolean contract flags the multiplexer must carry so the shared
# ``run`` wrapper owns every exit and envelope. ``result_action`` is asserted
# separately because cyclopts stores it tuple-wrapped. Mirrors the tripwire in
# ``tests/test_contract_app_factory.py``: a future edit that drops a flag fails
# here rather than silently changing exit behaviour.
_CONTRACT_BOOLEAN_FLAGS: tuple[str, ...] = (
    "exit_on_error",
    "print_error",
    "help_on_error",
)


def test_verb_for_subcommand_is_registry_driven() -> None:
    """The dispatcher's private verb map is built from the registry accessor.

    Pins that ``_VERB_FOR_SUBCOMMAND`` derives each verb through
    :func:`~novel_ralph_skill.commands.names.verb_for` rather than re-spelling
    ``split(" ", 1)[1]`` inline (roadmap task 7.3.8). A future inline re-spelling
    that diverged from the registry would fail here.
    """
    expected = {name: verb_for(name) for name in SUBCOMMAND_NAMES}
    assert expected == novel._VERB_FOR_SUBCOMMAND


def test_multiplexer_returns_the_leaf_body_value() -> None:
    """The multiplexer carries ``result_action="return_value"`` (the tripwire).

    Cyclopts stores ``result_action`` tuple-wrapped, so the parent must return the
    mounted leaf body's value to ``run`` rather than ``sys.exit`` on it. A future
    edit that drops this flag fails here rather than silently changing exit
    behaviour (mirrors ``tests/test_contract_app_factory.py``).
    """
    assert novel.build_multiplexer().result_action == ("return_value",)


@pytest.mark.parametrize("flag", _CONTRACT_BOOLEAN_FLAGS)
def test_multiplexer_carries_contract_flags(flag: str) -> None:
    """The multiplexer carries the boolean contract flags (the dropped-flag tripwire).

    ``exit_on_error=False`` makes a usage fault raise rather than exit ``1``;
    ``print_error``/``help_on_error`` keep Cyclopts from owning the diagnostic
    channel, so the shared ``run`` wrapper owns every exit and envelope.
    """
    assert getattr(novel.build_multiplexer(), flag) is False


@pytest.mark.parametrize(
    ("residual", "expected"),
    [
        (["state", "check"], "novel state"),
        (["done"], "novel done"),
        (["compile", "--check"], "novel compile"),
        (["desloppify"], "novel desloppify"),
        (["wordcount"], "novel wordcount"),
        ([], "novel"),
        (["--help"], "novel"),
        (["--version"], "novel"),
    ],
    ids=[
        "state",
        "done",
        "compile",
        "desloppify",
        "wordcount",
        "bare",
        "help",
        "version",
    ],
)
def test_command_name_for_maps_residual_argv(
    residual: list[str], expected: str
) -> None:
    """``_command_name_for`` maps residual argv to the spaced registry name."""
    assert novel._command_name_for(residual) == expected


@pytest.mark.parametrize(
    "spaced_argv",
    [
        ["state", "check"],
        ["done"],
        ["compile", "--check"],
        ["desloppify"],
        ["wordcount"],
    ],
    ids=["state", "done", "compile", "desloppify", "wordcount"],
)
def test_command_name_for_uses_the_registry_not_literals(
    spaced_argv: list[str],
) -> None:
    """Every spaced name ``_command_name_for`` can return is in the registry.

    Guards Decision Log D4: the entry point consults the registry, so a name it
    stamps cannot drift from the single source of truth.
    """
    assert novel._command_name_for(spaced_argv) in SUBCOMMAND_NAMES


@pytest.mark.parametrize(
    "residual",
    [
        ["bogus"],
        ["foo.toml"],
        ["--config", "foo.toml"],
    ],
    ids=["unknown-verb", "stray-value", "value-carrying-flag-leak"],
)
def test_command_name_for_falls_back_on_unrecognised_tokens(
    residual: list[str],
) -> None:
    """An unrecognised leading token resolves to the bare ``novel`` surface name.

    Pins the single-value-less-global-flag assumption (roadmap 1.2.12.1): a stray
    value left by a hypothetical value-carrying global flag (``--config
    foo.toml``) — or any unknown verb — must never be stamped as a subcommand
    name. The guard falls back to ``"novel"`` so the latent regression cannot land
    silently when the global-flag surface grows.
    """
    assert novel._command_name_for(residual) == "novel"
