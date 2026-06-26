"""Property tests for ``novel-state set-fangirl`` (roadmap 2.2.4; Hypothesis).

Pins the write-time precondition (Decision D6): for a coherent baseline with N
manifest chapters, ``set-fangirl --last-chapter k`` exits ``0`` and stays coherent
for every ``k`` in ``[0, N]``, and exits ``3`` with the file unchanged for every
``k`` outside it. The strategy draws ``k`` across a band straddling ``[0, N]`` so
both the accepted and the refused arms are exercised.

The drive avoids function-scoped fixtures (``monkeypatch``/``capsys``) because
Hypothesis does not reset them between generated inputs; a context-manager
``chdir`` and :func:`contextlib.redirect_stdout` stand in.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tomllib
import typing as typ
from pathlib import Path

import pytest
import working_corpus as wc
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc

_COMMAND = "novel state"
# The ``drafting`` corpus tree carries a three-chapter manifest.
_MANIFEST_CHAPTERS = 3


@contextlib.contextmanager
def _chdir(target: Path) -> cabc.Iterator[None]:
    """Change directory to ``target`` for the block, restoring it afterwards."""
    prior = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prior)


def _drive(working: Path, argv: list[str]) -> tuple[int, dict[str, object]]:
    """Drive ``argv`` from ``working.parent``; return ``(exit_code, envelope)``."""
    stream = io.StringIO()
    with (
        _chdir(working.parent),
        contextlib.redirect_stdout(stream),
        pytest.raises(SystemExit) as excinfo,
    ):
        run(
            build_app(),
            argv,
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    code = typ.cast("int", excinfo.value.code)
    return code, json.loads(stream.getvalue() or "{}")


@settings(max_examples=25, deadline=None)
@given(last_chapter=st.integers(min_value=-2, max_value=_MANIFEST_CHAPTERS + 2))
def test_set_fangirl_accepts_in_range_refuses_out_of_range(
    last_chapter: int,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """In-range ``last_chapter`` exits 0 and is coherent; out-of-range exits 3."""
    working = wc.build_working_tree(
        wc.PHASE_STATES["drafting"], tmp_path_factory.mktemp("set_fangirl_prop")
    )
    before = (working / "state.toml").read_bytes()
    code, _ = _drive(working, ["set-fangirl", "--last-chapter", str(last_chapter)])
    if 0 <= last_chapter <= _MANIFEST_CHAPTERS:
        assert code == ExitCode.SUCCESS, f"--last-chapter {last_chapter} must exit 0"
        raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
        assert raw["drafting"]["fangirl"]["last_chapter_passed"] == last_chapter, (
            "the in-range value must be written verbatim"
        )
        check_code, check_envelope = _drive(working, ["check"])
        assert check_code == ExitCode.SUCCESS, (
            "check must stay coherent after an accepted set"
        )
        assert check_envelope["ok"] is True, (
            "the post-set check envelope must remain ok"
        )
    else:
        assert code == ExitCode.STATE_ERROR, (
            f"--last-chapter {last_chapter} must exit 3"
        )
        assert (working / "state.toml").read_bytes() == before, (
            "a refused set must leave state.toml unchanged"
        )
