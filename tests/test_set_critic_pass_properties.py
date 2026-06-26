"""Property tests for ``novel-state set-critic-pass`` (roadmap 2.2.4; Hypothesis).

Pins the write-time precondition (Decision D6): for a coherent baseline,
``set-critic-pass --pass p`` exits ``0`` and stays coherent for every ``p >= 1``
(the critic §5.2 sub-rules bound ``consecutive_clean``/``convergence_target``, not
``pass``), and exits ``3`` with the file unchanged for every ``p < 1``. The
strategy draws ``p`` across a band straddling 1 so both arms are exercised.

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

_COMMAND = "novel-state"


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
@given(pass_number=st.integers(min_value=-3, max_value=8))
def test_set_critic_pass_accepts_at_least_one_refuses_below(
    pass_number: int,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """``pass >= 1`` exits 0 and stays coherent; ``pass < 1`` exits 3, file intact."""
    working = wc.build_working_tree(
        wc.PHASE_STATES["drafting"], tmp_path_factory.mktemp("set_critic_prop")
    )
    before = (working / "state.toml").read_bytes()
    code, _ = _drive(working, ["set-critic-pass", "--pass", str(pass_number)])
    if pass_number >= 1:
        assert code == ExitCode.SUCCESS, f"--pass {pass_number} must exit 0"
        raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
        assert raw["drafting"]["critic"]["pass"] == pass_number, (
            "the accepted pass must be written verbatim"
        )
        check_code, check_envelope = _drive(working, ["check"])
        assert check_code == ExitCode.SUCCESS, (
            "check must stay coherent after an accepted set"
        )
        assert check_envelope["ok"] is True, (
            "the post-set check envelope must remain ok"
        )
    else:
        assert code == ExitCode.STATE_ERROR, f"--pass {pass_number} must exit 3"
        assert (working / "state.toml").read_bytes() == before, (
            "a refused set must leave state.toml unchanged"
        )
