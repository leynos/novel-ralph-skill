"""Step definitions for the torn-multi-file-turn behavioural scenario.

These steps drive the ``pending_turn`` bracket through an interrupted turn and
assert the on-disk recovery signature: a populated ``[pending_turn]`` naming the
operation and the declared paths, with the prior tables intact (design §3.4).
The fixture state (the ``state.toml`` path and the declared paths) flows between
steps through ``target_fixture`` returns, the pytest-bdd idiom for sharing
context without module-level mutable state.

This module lives under ``tests/steps/`` (the directory ``pyproject.toml``
exempts from the assert/argument-count rules) and is imported into the scenario
binder ``tests/test_torn_turn_bdd.py``.
"""

from __future__ import annotations

import typing as typ

import pytest
from pytest_bdd import given, parsers, then, when

from novel_ralph_skill.state.document import load_document, pending_turn
from novel_ralph_skill.state.parse import parse_state
from novel_ralph_skill.state.schema import PendingTurn

if typ.TYPE_CHECKING:
    from pathlib import Path

# The paths the interrupted turn declares it will write; pinned so the
# Then-steps assert the record names exactly these.
_DECLARED_PATHS = ("working/state.toml", "working/manuscript/compiled.md")

# A settled, comment-bearing ``state.toml`` with no ``[pending_turn]``. Kept
# minimal but schema-valid so ``parse_state`` reconstructs it; the scenario
# asserts the prior ``[word_counts]`` table survives the torn turn.
_SETTLED_STATE_TOML = """\
schema_version = 1

[novel]
title = "The Lantern Keeper"
slug = "the-lantern-keeper"
target_word_count = 80000
created_at = "2026-06-22T09:00:00Z"

[phase]
current = "drafting"
completed = ["premise"]

[drafting]
current_chapter = 1
current_scene = 0
current_beat = 0

[drafting.critic]
pass = 1
consecutive_clean = 0
convergence_target = 1
last_finding_counts = { blocker = 0, major = 0, minor = 0, taste = 0 }

[drafting.fangirl]
last_chapter_passed = 0

[gates.knitting]
done_30 = false
done_50 = false
done_80 = false

[gates.final]
final_pass_complete = false

[word_counts]
target = 80000
current = 3200  # running total across compiled chapters
by_chapter = { "01" = 3200 }

[[chapters]]
number = 1
slug = "chapter-01"
title = "Arrival"
target_words = 4000
"""


class _ArtefactError(RuntimeError):
    """Sentinel raised inside the bracket to simulate a turn dying mid-write."""


@given("a settled state.toml with no pending_turn", target_fixture="state_path")
def settled_state(tmp_path: Path) -> Path:
    """Write a settled ``state.toml`` and return its path.

    Returns
    -------
    pathlib.Path
        The path to the settled ``state.toml`` under the test's ``tmp_path``.
    """
    path = tmp_path / "state.toml"
    path.write_text(_SETTLED_STATE_TOML, encoding="utf-8")
    assert parse_state(load_document(path)).pending_turn is None, (
        "the Given step must start from a settled state with no pending_turn"
    )
    return path


@when(
    parsers.parse('a pending_turn bracket for "{operation}" raises before clean exit')
)
def bracket_raises(state_path: Path, operation: str) -> None:
    """Open the bracket for ``operation`` and raise inside the artefact step.

    The raise simulates a turn dying after the intent record is written but
    before the bracket's clean-exit clear runs (design §3.4). The
    ``_ArtefactError`` is swallowed here so the scenario proceeds to assert the
    on-disk state; the bracket leaves the populated record on disk.
    """
    # The bracket body must raise to simulate the torn turn, so pytest.raises
    # wraps the multi-statement body (PT012).
    with (  # noqa: PT012
        pytest.raises(_ArtefactError),
        pending_turn(state_path, operation=operation, paths=_DECLARED_PATHS),
    ):
        msg = "artefact step died mid-turn"
        raise _ArtefactError(msg)


@then(
    parsers.parse(
        'state.toml carries a pending_turn for "{operation}" naming the declared paths'
    )
)
def record_is_populated(state_path: Path, operation: str) -> None:
    """Assert the on-disk record names ``operation`` and the declared paths."""
    state = parse_state(load_document(state_path))
    assert state.pending_turn == PendingTurn(
        operation=operation, paths=_DECLARED_PATHS
    ), "the torn turn did not leave the expected pending_turn record"


@then("the prior word_counts table is intact")
def prior_tables_intact(state_path: Path) -> None:
    """Assert the prior ``[word_counts]`` table survived the torn turn."""
    state = parse_state(load_document(state_path))
    assert state.word_counts.current == 3200, "the prior word_counts table changed"
    assert state.word_counts.target == 80000, "the prior word_counts table changed"
