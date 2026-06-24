"""Cross-subcommand ``violations``-ownership guard (roadmap 1.3.5).

``violations`` is the ``check`` *query*'s read shape and belongs to exactly one
``novel-state`` subcommand. The three write *mutators* (``init``, ``set-cursor``,
``advance-phase``) name what they changed in ``result`` and must never echo it
(design §3.3 command/query segregation; audit-2.2.2 Finding 2). This guard pins
that ownership as a test so a future mutator (``recount``, ``reconcile``) cannot
re-introduce the echo silently — extend the parametrization with its argv +
fixture row asserting ``violations`` absent when those mutators land.

Each arm needs a *different* precondition, so the guard cannot share one cwd:
``init`` refuses (exit ``3``) when ``working/state.toml`` already exists, so it
runs from a *bare* ``tmp_path`` with no pre-existing tree; ``set-cursor``,
``advance-phase``, and ``check`` each need a *populated, coherent* tree, and each
a different one. A single shared chdir would drive ``init`` into an exit-``3``
refusal, silently inverting the guard. Each parameter case therefore carries a
small setup callable that builds (and ``chdir``'s into) the tree its arm needs.
"""

from __future__ import annotations

import collections.abc as cabc
import json
import typing as typ

import pytest

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-state"

# Each setup callable takes the ``request`` fixture, builds the tree its arm
# needs, and ``chdir``'s into the directory the subcommand must run from. It
# pulls ``monkeypatch``/``tmp_path`` and the relevant tree factory off the
# request so the parametrized test stays within pylint's argument budget. It
# returns nothing; the guard only reads the envelope afterwards.
_SetUp = cabc.Callable[[pytest.FixtureRequest], None]
# The single subcommand that owns the ``violations`` read shape.
_CHECK_SUBCOMMAND = "check"


def _monkeypatch(request: pytest.FixtureRequest) -> pytest.MonkeyPatch:
    """Return the active ``monkeypatch`` fixture for ``request``."""
    return typ.cast("pytest.MonkeyPatch", request.getfixturevalue("monkeypatch"))


def _drive_and_capture(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict[str, object]]:
    """Run ``argv`` through :func:`run` and return ``(exit_code, envelope)``."""
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    return code, json.loads(capsys.readouterr().out)


def _setup_init(request: pytest.FixtureRequest) -> None:
    """``init`` runs from a bare cwd with no pre-existing ``working/``."""
    tmp_path = typ.cast("Path", request.getfixturevalue("tmp_path"))
    _monkeypatch(request).chdir(tmp_path)


def _setup_set_cursor(request: pytest.FixtureRequest) -> None:
    """``set-cursor`` runs against a populated ``drafting`` tree."""
    factory = typ.cast(
        "cabc.Callable[[str], Path]", request.getfixturevalue("phase_state_tree")
    )
    _monkeypatch(request).chdir(factory("drafting").parent)


def _setup_advance_phase(request: pytest.FixtureRequest) -> None:
    """``advance-phase`` runs against a coherent ``premise`` tree."""
    factory = typ.cast(
        "cabc.Callable[[str], Path]", request.getfixturevalue("phase_state_tree")
    )
    _monkeypatch(request).chdir(factory("premise").parent)


def _setup_recount(request: pytest.FixtureRequest) -> None:
    """``recount`` runs against the coherent baseline tree."""
    factory = typ.cast(
        "cabc.Callable[[], Path]", request.getfixturevalue("baseline_tree")
    )
    _monkeypatch(request).chdir(factory().parent)


def _setup_check(request: pytest.FixtureRequest) -> None:
    """``check`` runs against the coherent baseline tree."""
    factory = typ.cast(
        "cabc.Callable[[], Path]", request.getfixturevalue("baseline_tree")
    )
    _monkeypatch(request).chdir(factory().parent)


@pytest.mark.parametrize(
    ("argv", "setup"),
    [
        (["init", "--title", "T", "--slug", "s"], _setup_init),
        (
            ["set-cursor", "--chapter", "2", "--scene", "0", "--beat", "0"],
            _setup_set_cursor,
        ),
        (["advance-phase"], _setup_advance_phase),
        (["recount"], _setup_recount),
        ([_CHECK_SUBCOMMAND], _setup_check),
    ],
    ids=["init", "set-cursor", "advance-phase", "recount", "check"],
)
def test_violations_belongs_to_check_alone(
    argv: list[str],
    setup: _SetUp,
    request: pytest.FixtureRequest,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Only ``check`` carries ``violations``; the three mutators never do.

    Every arm here exits ``ExitCode.SUCCESS``; the ``violations`` ownership is
    derived from the subcommand, so only ``check`` is expected to carry the key.
    Presence, not emptiness, is the assertion: ``check``'s empty ``[]`` still
    carries the key, while a mutator success ``result`` has no ``violations`` key
    at all (design §3.3; audit-2.2.2 Finding 2).
    """
    setup(request)
    subcommand = argv[0]
    code, envelope = _drive_and_capture(argv, capsys)
    assert code == ExitCode.SUCCESS, (
        f"{subcommand!r} expected exit {ExitCode.SUCCESS!r}, got {code!r}"
    )
    result = typ.cast("dict[str, object]", envelope["result"])
    violations_expected = subcommand == _CHECK_SUBCOMMAND
    assert ("violations" in result) is violations_expected, (
        f"{subcommand!r}: expected 'violations' "
        f"{'present' if violations_expected else 'absent'} in result, "
        f"but it was {'present' if 'violations' in result else 'absent'}"
    )
