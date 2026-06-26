"""Step definitions for the ``novel-compile`` regeneration scenarios.

These drive ``novel-compile`` against a working tree with three drafted chapters
and a stale ``compiled.md``, and assert the roadmap 4.1.1 success criteria: the
compile exits ``0``, ``working/manuscript/compiled.md`` equals the manifest-ordered
draft concatenation, and a second run over unchanged drafts yields a byte-for-byte
identical file (determinism/idempotence; design §4.3, §10). The empty-manifest
scenario asserts the exit-``3`` refusal writes no ``compiled.md``.

The command is driven through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, exactly as the contract
tests do, so the externally observable exit code is what the scenario asserts.
The runner step ``chdir``s into the prepared tree's parent first because
``novel-compile`` resolves a cwd-relative ``working/`` (Decision Log D-CWD), as
the recount steps do. Fixture state flows between steps through
``target_fixture`` returns, the pytest-bdd idiom.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml`` exempts
from the assert/argument-count rules) and is imported into the scenario binder
``tests/test_compile_bdd.py``.
"""

from __future__ import annotations

import contextlib
import dataclasses as dc
import io
import json
import typing as typ

import pytest
import working_corpus as wc
from pytest_bdd import given, then, when

from novel_ralph_skill.commands._compile import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

# The three drafted chapters' word counts; the expected concatenation is exact.
_COUNTS: tuple[int, ...] = (3, 5, 4)
# Deliberately stale bytes for the pre-existing compiled.md, so the compile has
# something to overwrite (and the idempotence assertion is meaningful).
_STALE_COMPILED = "STALE — not the ordered concatenation"


@dc.dataclass(slots=True)
class _Outcome:
    """The built tree, the exit code, and the envelope captured across steps.

    ``compiled_before`` captures ``compiled.md``'s bytes at build time, so the
    present-but-stale no-write Then can assert the file is left byte-for-byte
    unchanged after a ``--check`` run (ExecPlan D-STALE-NOWRITE). ``envelope``
    holds the parsed machine-mode envelope so the ``diverged`` field is pinned
    behaviourally (it is ``None`` for the write-path scenarios that do not capture
    stdout).
    """

    working: Path
    exit_code: int | None = None
    compiled_before: bytes | None = None
    envelope: dict[str, object] | None = None


def _run_compile(working: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    """Drive ``novel-compile`` through ``run`` from ``working.parent``; return code."""
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [],
            RunContext(command="novel compile", working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code)


def _run_check(
    working: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[int, dict[str, object]]:
    """Drive ``novel-compile --check`` through ``run``; return code and envelope.

    Passes ``["--check"]`` (not ``[]``) so the read-only checker, not the write
    path, is exercised, and captures stdout so the ``diverged`` field can be
    asserted behaviourally (ExecPlan D-CHECK-ARGV).
    """
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["--check"],
            RunContext(command="novel compile", working_dir="working", human=False),
        )
    envelope = typ.cast("dict[str, object]", json.loads(stream.getvalue()))
    return typ.cast("int", excinfo.value.code), envelope


def _coherent_spec() -> wc.WorkingTreeSpec:
    """Return a three-chapter ``drafting`` spec carrying a coherent ``compiled.md``."""
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(_COUNTS, start=1)
    )
    return wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        # COMPILED_AUTO writes the hash-equal coherent concatenation (MATCHES).
        compiled=wc.COMPILED_AUTO,
    )


def _expected_concatenation() -> str:
    """Return the manifest-ordered draft concatenation the compile must write."""
    return wc.concatenate_drafts([wc.draft_body(count) for count in _COUNTS])


@given(
    "a working tree with three drafted chapters and a stale compiled.md",
    target_fixture="outcome",
)
def drafting_tree_with_stale_compiled(tmp_path: Path) -> _Outcome:
    """Build a three-chapter ``drafting`` tree carrying a stale ``compiled.md``.

    Returns
    -------
    _Outcome
        The built ``working/`` path; the exit code is filled in by the run step.
    """
    chapters = tuple(
        wc.ChapterSpec(
            number=number,
            slug=f"chapter-{number:02d}",
            title=f"Chapter {number}",
            target_words=20000,
            draft_words=count,
            has_done_flag=False,
        )
        for number, count in enumerate(_COUNTS, start=1)
    )
    spec = wc.WorkingTreeSpec(
        phase_current="drafting",
        phase_completed=wc.PHASE_ORDER[:8],
        chapters=chapters,
        target_words=80000,
        consecutive_clean=0,
        convergence_target=1,
        current_chapter=len(chapters),
        # A stale compiled.md the deterministic compile must overwrite.
        compiled=_STALE_COMPILED,
    )
    return _Outcome(working=wc.build_working_tree(spec, tmp_path))


@given(
    "a working tree whose chapter manifest is empty",
    target_fixture="outcome",
)
def empty_manifest_tree(tmp_path: Path) -> _Outcome:
    """Build a pre-drafting ``premise`` tree (empty manifest, no ``compiled.md``)."""
    return _Outcome(working=wc.build_working_tree(wc.PHASE_STATES["premise"], tmp_path))


@when("novel-compile runs against that tree")
def run_compile(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-compile`` through ``run`` and capture the exit code."""
    outcome.exit_code = _run_compile(outcome.working, monkeypatch)


@then("novel-compile exits 0")
def asserts_exit_zero(outcome: _Outcome) -> None:
    """Assert the compile exited ``0`` (success)."""
    assert outcome.exit_code == ExitCode.SUCCESS, (
        f"expected exit 0, got {outcome.exit_code}"
    )


@then("novel-compile exits 3")
def asserts_exit_three(outcome: _Outcome) -> None:
    """Assert the compile refused with exit ``3`` (the state channel)."""
    assert outcome.exit_code == ExitCode.STATE_ERROR, (
        f"expected exit 3, got {outcome.exit_code}"
    )


@then("compiled.md equals the manifest-ordered concatenation of the drafts")
def asserts_ordered_concatenation(outcome: _Outcome) -> None:
    """Assert ``compiled.md`` is the ascending-order draft concatenation."""
    compiled = outcome.working / "manuscript" / "compiled.md"
    assert compiled.read_text(encoding="utf-8") == _expected_concatenation(), (
        "compiled.md must equal the manifest-ordered draft concatenation"
    )


@then("a second novel-compile leaves compiled.md byte-for-byte unchanged")
def asserts_idempotent(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert a second compile over unchanged drafts is byte-for-byte identical."""
    compiled = outcome.working / "manuscript" / "compiled.md"
    before = compiled.read_bytes()
    second_code = _run_compile(outcome.working, monkeypatch)
    assert second_code == ExitCode.SUCCESS, (
        f"the second compile should also exit 0, got {second_code}"
    )
    after = compiled.read_bytes()
    assert after == before, "a second compile must leave compiled.md byte-for-byte"


@then("no compiled.md is written")
def asserts_no_compiled(outcome: _Outcome) -> None:
    """Assert the refusal wrote no ``compiled.md``."""
    compiled = outcome.working / "manuscript" / "compiled.md"
    assert not compiled.exists(), "an empty-manifest refusal must write no compiled.md"


@given(
    "a working tree whose compiled.md matches the drafts",
    target_fixture="outcome",
)
def coherent_tree(tmp_path: Path) -> _Outcome:
    """Build a coherent tree whose ``compiled.md`` equals the drafts (MATCHES).

    Captures ``compiled.md``'s bytes at build time so the no-write Then can assert
    the present file is left byte-for-byte unchanged after ``--check``.

    Returns
    -------
    _Outcome
        The built ``working/`` path and the captured pre-run ``compiled.md`` bytes.
    """
    working = wc.build_working_tree(_coherent_spec(), tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    return _Outcome(working=working, compiled_before=compiled.read_bytes())


@given(
    "a working tree with a present-but-stale compiled.md",
    target_fixture="outcome",
)
def present_stale_tree(tmp_path: Path) -> _Outcome:
    """Build a tree whose present ``compiled.md`` diverges from the drafts.

    Reuses the coherent spec but overwrites ``compiled.md`` with stale bytes so
    the present file is the DIVERGES case, and captures those bytes so the
    no-write Then can assert they are unchanged after ``--check``.

    Returns
    -------
    _Outcome
        The built ``working/`` path and the captured pre-run stale bytes.
    """
    spec = dc.replace(_coherent_spec(), compiled=_STALE_COMPILED)
    working = wc.build_working_tree(spec, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    return _Outcome(working=working, compiled_before=compiled.read_bytes())


@given(
    "a working tree with no compiled.md",
    target_fixture="outcome",
)
def absent_compiled_tree(tmp_path: Path) -> _Outcome:
    """Build a coherent-draft tree carrying no ``compiled.md`` (the ABSENT case)."""
    spec = dc.replace(_coherent_spec(), compiled=None)
    return _Outcome(working=wc.build_working_tree(spec, tmp_path))


@when("novel-compile --check runs against that tree")
def run_check(outcome: _Outcome, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive ``novel-compile --check`` and capture the exit code and envelope."""
    outcome.exit_code, outcome.envelope = _run_check(outcome.working, monkeypatch)


@then("novel-compile exits 4")
def asserts_exit_four(outcome: _Outcome) -> None:
    """Assert ``--check`` reported an actionable finding with exit ``4``."""
    assert outcome.exit_code == ExitCode.ACTIONABLE_FINDING, (
        f"expected exit 4, got {outcome.exit_code}"
    )


@then("the envelope reports diverged false")
def asserts_diverged_false(outcome: _Outcome) -> None:
    """Assert the captured envelope reports ``result.diverged`` is ``False``."""
    assert outcome.envelope is not None, "the --check run must capture an envelope"
    result = typ.cast("dict[str, object]", outcome.envelope["result"])
    assert result["diverged"] is False, "a current compile must report diverged false"


@then("the envelope reports diverged true")
def asserts_diverged_true(outcome: _Outcome) -> None:
    """Assert the captured envelope reports ``result.diverged`` is ``True``."""
    assert outcome.envelope is not None, "the --check run must capture an envelope"
    result = typ.cast("dict[str, object]", outcome.envelope["result"])
    assert result["diverged"] is True, (
        "a stale/absent compile must report diverged true"
    )


@then("the present compiled.md is left byte-for-byte unchanged")
def asserts_compiled_unchanged(outcome: _Outcome) -> None:
    """Assert the present ``compiled.md`` is byte-for-byte unchanged after ``--check``.

    The no-write invariant on the *present* path: ``not compiled.exists()`` is
    false here, so the absent-file Then cannot express it (ExecPlan
    D-STALE-NOWRITE); this captures and compares the bytes instead.
    """
    assert outcome.compiled_before is not None, "the Given must capture prior bytes"
    compiled = outcome.working / "manuscript" / "compiled.md"
    assert compiled.read_bytes() == outcome.compiled_before, (
        "--check must leave the present compiled.md byte-for-byte unchanged"
    )
