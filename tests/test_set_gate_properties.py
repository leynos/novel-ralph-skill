"""Property tests for ``novel-state set-gate`` (roadmap 2.2.4; Hypothesis).

Pins the load-bearing semantic: ``set-gate`` accepts exactly the ratio-consistent
knitting-gate flag set and refuses any contradicting one (design §5.2 invariant 7;
ExecPlan Decision D4/D8). The strategy draws three chapter ``draft_words`` (so the
drafted ratio lands in a controlled range) and an independent prior gate-boolean
triple, builds the tree, then drives ``set-gate`` with the ratio-mandated flag set
and asserts exit 0 plus a coherent result; a contradicting flag set asserts exit 3
and an unchanged file.

To forbid a vacuous pass (Doggylump pre-mortem signal 3), the property records via
:func:`hypothesis.event` and requires at least one generated case where the
ratio-mandated flag set actually changes a gate value from the prior — an
observable repair flip — so the strategy is not silently degenerate.
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
from _gate_drafting_fixtures import gate_spec
from hypothesis import event, given, settings
from hypothesis import strategies as st

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc

_COMMAND = "novel state"
_TARGET_WORDS = 80000
_THRESHOLDS = (0.30, 0.50, 0.80)
_FLAG_NAMES = ("knitting-30", "knitting-50", "knitting-80")
_GATE_KEYS = ("done_30", "done_50", "done_80")

# Counts generated cases where the mandated triple differs from the prior — an
# observable gate flip. ``teardown_module`` asserts it is positive so the property
# cannot pass vacuously over a silently degenerate strategy (Doggylump pre-mortem
# signal 3): ``event()`` alone only records statistics, it does not enforce.
_observable_flips = 0


def teardown_module(module: object) -> None:
    """Fail the module if no generated case exercised an observable gate flip."""
    assert _observable_flips > 0, (
        "the set-gate property never generated an observable flip; the strategy is "
        "degenerate and the property may pass vacuously"
    )


def _mandated(ratio: float) -> tuple[bool, bool, bool]:
    """Return the ratio-mandated knitting-gate triple for ``ratio``."""
    low, mid, high = _THRESHOLDS
    return ratio >= low, ratio >= mid, ratio >= high


def _flags_for(triple: tuple[bool, bool, bool]) -> list[str]:
    """Return the ``set-gate`` argv asserting ``triple`` over all three gates."""
    argv = ["set-gate"]
    for name, value in zip(_FLAG_NAMES, triple, strict=True):
        argv.append(f"--{name}" if value else f"--no-{name}")
    return argv


@contextlib.contextmanager
def _chdir(target: Path) -> cabc.Iterator[None]:
    """Change directory to ``target`` for the block, restoring it afterwards.

    A context manager rather than the ``monkeypatch`` fixture so the property
    body holds no function-scoped fixture, which Hypothesis flags because such
    fixtures are not reset between generated inputs.
    """
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


def _assert_mandated_accepted(working: Path, mandated: tuple[bool, bool, bool]) -> None:
    """Assert ``set-gate`` accepts the ratio-mandated triple and writes it."""
    code, envelope = _drive(working, _flags_for(mandated))
    assert code == ExitCode.SUCCESS, f"mandated set was refused: {envelope}"
    assert envelope["ok"] is True, f"mandated set envelope must be ok: {envelope}"
    raw = tomllib.loads((working / "state.toml").read_text("utf-8"))
    written = tuple(raw["gates"]["knitting"][key] for key in _GATE_KEYS)
    assert written == mandated, "the written gates must equal the ratio-mandated set"


def _assert_contradiction_refused(
    working: Path, mandated: tuple[bool, bool, bool]
) -> None:
    """Assert a ratio-contradicting set exits 3 and leaves the file unchanged."""
    # Flip the first gate so the proposed state disagrees with the drafted ratio.
    contradicting = (not mandated[0], mandated[1], mandated[2])
    before = (working / "state.toml").read_bytes()
    code, _ = _drive(working, _flags_for(contradicting))
    assert code == ExitCode.STATE_ERROR, "a ratio-contradicting set must exit 3"
    assert (working / "state.toml").read_bytes() == before, (
        "a refused set must leave state.toml byte-for-byte unchanged"
    )


@settings(max_examples=25, deadline=None)
@given(
    draft_words=st.integers(min_value=0, max_value=30000),
    prior=st.tuples(st.booleans(), st.booleans(), st.booleans()),
)
def test_set_gate_accepts_exactly_the_ratio_mandated_triple(
    draft_words: int,
    prior: tuple[bool, bool, bool],
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The mandated flag set exits 0 and is coherent; a contradicting one exits 3."""
    mandated = _mandated(3 * draft_words / _TARGET_WORDS)
    working = wc.build_working_tree(
        gate_spec(
            draft_words=draft_words,
            done_30=prior[0],
            done_50=prior[1],
            done_80=prior[2],
        ),
        tmp_path_factory.mktemp("set_gate_prop"),
    )
    if mandated != prior:
        event("observable-flip")
        global _observable_flips  # module-level non-vacuity counter
        _observable_flips += 1
    _assert_mandated_accepted(working, mandated)
    _assert_contradiction_refused(working, mandated)
