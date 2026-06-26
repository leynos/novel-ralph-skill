"""Step definitions for the cross-boundary actionable draft-read message scenario.

These drive one representative command per draft-read boundary — ``novel state
check`` (``_disk_evidence_or_state_error``), ``novel state recount`` (``_recount``),
``novel wordcount`` (``_wordcount``), ``novel done`` (``_novel_done``), ``novel
desloppify`` (``_desloppify.source_chapters``), and ``novel compile`` /
``novel compile --check`` (``_compile``) — from a coherent ``working/`` tree whose
first chapter ``draft.md`` is corrupt invalid UTF-8, and assert the roadmap §6.3.5
success criterion: each exits ``3`` with an actionable message that names the
``working/`` tree and an inspect/repair remedy, carries no raw ``Errno``,
``{exc}`` repr, traceback, or ``init`` suggestion, and no old raw string.

The seventh boundary — the mutator view-derivation
``_state_mutators._state_view_or_state_error`` — is *not* a draft-read fault. It is
exercised by a separate scenario that corrupts ``state.toml`` to a
parseable-but-structurally-incomplete document and asserts the
``_state_input_error`` present-but-corrupt remedy naming the ``state.toml`` path
(ExecPlan Decision D7), visibly distinct from the draft-read prose.

The commands are driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper exactly as the surface
matrix does, so the externally observable exit code and rendered envelope are what
the scenario asserts. Each runner ``chdir``s into the prepared tree's parent
first, because every command resolves a cwd-relative ``working/state.toml``.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binders
``tests/test_draft_read_message_bdd.py``.
"""

from __future__ import annotations

import dataclasses as dc
import json
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands import _compile, _desloppify, _novel_done, _wordcount
from novel_ralph_skill.commands import novel_state as _novel_state
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts


@dc.dataclass(frozen=True, slots=True)
class _Boundary:
    """One draft-read boundary to exercise: its label, console name, app, and argv."""

    label: str
    command: str
    build_app: cabc.Callable[[], cyclopts.App]
    argv: list[str]


# One representative command per draft-read boundary. ``novel compile`` covers the
# ``compile_manuscript`` tail and ``novel compile --check`` the ``check_compiled``
# tail, so both of ``_compile``'s draft-read arms are proven.
_BOUNDARIES: tuple[_Boundary, ...] = (
    _Boundary("check", "novel state", _novel_state.build_app, ["check"]),
    _Boundary("recount", "novel state", _novel_state.build_app, ["recount"]),
    _Boundary("wordcount", "novel wordcount", _wordcount.build_app, []),
    _Boundary("done", "novel done", _novel_done.build_app, []),
    _Boundary("desloppify", "novel desloppify", _desloppify.build_app, []),
    _Boundary("compile", "novel compile", _compile.build_app, []),
    _Boundary("compile-check", "novel compile", _compile.build_app, ["--check"]),
)


@dc.dataclass(slots=True)
class _DraftReadOutcome:
    """The faulted ``working/`` tree and the per-boundary exit codes and messages."""

    working: Path
    results: dict[str, tuple[int, tuple[str, ...]]] = dc.field(default_factory=dict)


@dc.dataclass(slots=True)
class _ViewDerivationOutcome:
    """The structurally-incomplete tree and the captured exit code and messages."""

    working: Path
    code: int = 0
    messages: tuple[str, ...] = ()


def _first_chapter_dir(working: Path) -> Path:
    """Return the lowest-numbered ``chapter-NN`` directory under ``manuscript/``."""
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    assert chapters, "the baseline tree must contain at least one chapter directory"
    return chapters[0]


def _run(
    boundary: _Boundary,
    working: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, tuple[str, ...]]:
    """Drive one boundary from ``working.parent`` via ``run``; return code, messages."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            boundary.build_app(),
            boundary.argv,
            RunContext(command=boundary.command, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    envelope = json.loads(capsys.readouterr().out or "{}")
    return code, tuple(envelope.get("messages", ()))


@given(
    "a coherent working/ tree whose first chapter draft is corrupt",
    target_fixture="draft_read_outcome",
)
def corrupt_draft_tree(tmp_path: Path) -> _DraftReadOutcome:
    """Build a coherent ``final-pass`` tree and corrupt its first chapter ``draft.md``.

    The ``final-pass`` phase carries a present ``compiled.md``, so the ``done`` and
    ``compile --check`` boundaries — which read a draft only when ``compiled.md`` is
    present — also reach the draft-read arm rather than short-circuiting on an
    absent compile.

    Returns
    -------
    _DraftReadOutcome
        The faulted tree; the per-boundary results are filled in by the run step.
    """
    working = wc.build_working_tree(wc.PHASE_STATES["final-pass"], tmp_path)
    draft = _first_chapter_dir(working) / "draft.md"
    # Invalid UTF-8 makes ``read_text(encoding="utf-8")`` raise ``UnicodeDecodeError``
    # (a ``ValueError`` subclass in ``STATE_INPUT_ERRORS``), the draft-read fault.
    draft.write_bytes(b"\xff\xfe invalid words here")
    return _DraftReadOutcome(working=working)


@when("each draft-read command runs against the corrupt tree")
def run_each_boundary(
    draft_read_outcome: _DraftReadOutcome,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Drive every draft-read boundary against the faulted tree, capturing prose."""
    for boundary in _BOUNDARIES:
        draft_read_outcome.results[boundary.label] = _run(
            boundary, draft_read_outcome.working, monkeypatch, capsys
        )


@then("each draft-read command exits 3")
def asserts_each_draft_read_exits_three(draft_read_outcome: _DraftReadOutcome) -> None:
    """Assert every draft-read boundary exited ``3`` (the state-input channel)."""
    for label, (code, _messages) in draft_read_outcome.results.items():
        assert code == ExitCode.STATE_ERROR, f"the {label} should exit 3, got {code}"


@then("each draft-read message names the working/ tree and an inspect/repair remedy")
def asserts_draft_read_actionable(draft_read_outcome: _DraftReadOutcome) -> None:
    """Assert each boundary names the ``working/`` tree and the repair remedy."""
    for label, (_code, messages) in draft_read_outcome.results.items():
        text = "\n".join(messages)
        assert "working" in text, (
            f"the {label} message must name the working/ tree; got {messages!r}"
        )
        assert "inspect and repair" in text, (
            f"the {label} message must offer a repair remedy; got {messages!r}"
        )


@then("no draft-read message leaks raw noise or an init suggestion")
def asserts_draft_read_no_noise(draft_read_outcome: _DraftReadOutcome) -> None:
    """Assert no boundary leaks an ``Errno``, traceback, ``init``, or old raw text."""
    for label, (_code, messages) in draft_read_outcome.results.items():
        text = "\n".join(messages)
        assert "Errno" not in text, f"the {label} message must not leak an Errno"
        assert "Traceback" not in text, f"the {label} must not leak a traceback"
        assert "novel state init" not in text, (
            f"the {label} must not advise init; the tree exists"
        )
        assert "cannot read chapter drafts" not in text, (
            f"the {label} must not emit the old raw draft-read string"
        )


@given(
    "a working/ tree whose state.toml is structurally incomplete",
    target_fixture="view_derivation_outcome",
)
def incomplete_state_tree(tmp_path: Path) -> _ViewDerivationOutcome:
    """Build a coherent tree, then strip ``[gates]`` so the view derivation fails.

    The document still parses as TOML, so ``state.toml`` exists and
    ``_state_input_error``'s present-but-corrupt arm fires (ExecPlan Decision D7).

    Returns
    -------
    _ViewDerivationOutcome
        The faulted tree; the captured result is filled in by the run step.
    """
    working = wc.build_working_tree(wc.PHASE_STATES["final-pass"], tmp_path)
    raw = (working / "state.toml").read_text("utf-8")
    truncated = raw.split("[gates", maxsplit=1)[0]
    (working / "state.toml").write_text(truncated, encoding="utf-8")
    return _ViewDerivationOutcome(working=working)


@when("a mutator runs against the structurally incomplete state")
def run_mutator(
    view_derivation_outcome: _ViewDerivationOutcome,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Drive ``novel state set-cursor`` against the structurally-incomplete state."""
    boundary = _Boundary(
        "set-cursor",
        "novel state",
        _novel_state.build_app,
        ["set-cursor", "--chapter", "1"],
    )
    code, messages = _run(
        boundary, view_derivation_outcome.working, monkeypatch, capsys
    )
    view_derivation_outcome.code = code
    view_derivation_outcome.messages = messages


@then("the mutator exits 3")
def asserts_mutator_exits_three(
    view_derivation_outcome: _ViewDerivationOutcome,
) -> None:
    """Assert the mutator exited ``3`` (the state-input channel)."""
    assert view_derivation_outcome.code == ExitCode.STATE_ERROR, (
        f"the mutator should exit 3, got {view_derivation_outcome.code}"
    )


@then("the mutator message names the state.toml path and an inspect/repair remedy")
def asserts_view_derivation_actionable(
    view_derivation_outcome: _ViewDerivationOutcome,
) -> None:
    """Assert the mutator reuses the present-but-corrupt remedy naming state.toml."""
    text = "\n".join(view_derivation_outcome.messages)
    assert "state.toml" in text, "the message must name the state.toml path"
    assert "is unreadable or corrupt; inspect and repair it" in text, (
        "the view-derivation fault must reuse the present-but-corrupt remedy (D7)"
    )


@then("the mutator message leaks no raw structurally-incomplete text")
def asserts_view_derivation_no_noise(
    view_derivation_outcome: _ViewDerivationOutcome,
) -> None:
    """Assert the mutator leaks no old raw text, ``Errno``, traceback, or ``init``."""
    text = "\n".join(view_derivation_outcome.messages)
    assert "state is structurally incomplete" not in text, (
        "the old raw structurally-incomplete string must no longer leak"
    )
    assert "Errno" not in text, "the message must not leak an Errno"
    assert "Traceback" not in text, "the message must not leak a traceback"
    assert "novel state init" not in text, (
        "a present-but-corrupt state.toml must not advise init; the file exists"
    )
