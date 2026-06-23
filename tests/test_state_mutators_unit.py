"""Unit and property tests for the ``novel-state`` mutator helpers (roadmap 2.2.2).

These pin the two document-load fault helpers and the ``set-cursor`` equivalence
without the Cyclopts layer:

- the fault-subclass facts (``tomlkit.ParseError`` is a ``ValueError``;
  ``NonExistentKey`` is a ``KeyError``) so a future ``tomlkit``/``tomllib`` bump
  cannot silently regress the exit-``3`` contract (ExecPlan Decision Log D4);
- :func:`_load_document_or_state_error` over a missing and an unparseable path,
  and :func:`_state_view_or_state_error` over a structurally-incomplete document
  and a bad-phase-string document, each raising ``StateInputError`` — the
  typed-view derivation cannot escape the exit-``3`` channel (BR2-1);
- a Hypothesis property: over generated ``(chapter, scene, beat)`` cursors
  against a fixed populated manifest, the ``set-cursor`` body succeeds iff
  ``validate_state`` of the proposed state is empty, and refuses otherwise — the
  "set-cursor accepts exactly the coherent cursors" equivalence to the validator
  (design §9; AGENTS.md "property tests … over a range of inputs"). Hypothesis is
  the right adversary (an oracle, the validator, is available; python-verification
  selection matrix), confirmed before loading the deep-dive skill.
"""

from __future__ import annotations

import contextlib
import typing as typ

import pytest
import tomlkit
import tomlkit.exceptions
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
    _state_view_or_state_error,
    set_cursor,
)
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import StateInputError
from novel_ralph_skill.state import (
    document_to_state,
    load_document,
    validate_state,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from novel_ralph_skill.contract.runner import CommandOutcome

# A ``state.toml`` that is valid TOML but missing every required table beyond
# ``schema_version``; ``load_document`` parses it but ``document_to_state`` ->
# ``parse_state`` rejects it (``NonExistentKey``).
_INCOMPLETE_STATE = "schema_version = 1\n"

# A ``state.toml`` whose ``[phase].current`` is not a phase enum member; it parses
# and reaches ``Phase(...)``, which raises ``ValueError``.
_BAD_PHASE_STATE = """\
schema_version = 1

[novel]
title = "T"
slug = "s"
target_word_count = 80000
created_at = "2026-06-23T00:00:00Z"

[phase]
current = "nope"
completed = []

[drafting]
current_chapter = 0
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
current = 0
by_chapter = {}
"""


def test_tomlkit_parse_error_is_value_error() -> None:
    """``tomlkit.ParseError`` is a ``ValueError`` subclass (Decision Log D4)."""
    assert issubclass(tomlkit.exceptions.ParseError, ValueError)


def test_tomlkit_nonexistent_key_is_key_error() -> None:
    """``tomlkit.NonExistentKey`` is a ``KeyError`` subclass (Decision Log D4)."""
    assert issubclass(tomlkit.exceptions.NonExistentKey, KeyError)


def test_load_document_helper_missing_path_raises(tmp_path: Path) -> None:
    """Loading a missing ``state.toml`` raises ``StateInputError`` (exit ``3``)."""
    with pytest.raises(StateInputError):
        _load_document_or_state_error(tmp_path / "state.toml")


def test_load_document_helper_unparseable_raises(tmp_path: Path) -> None:
    """Loading an unparseable ``state.toml`` raises ``StateInputError``."""
    path = tmp_path / "state.toml"
    path.write_text("not = toml =", encoding="utf-8")
    with pytest.raises(StateInputError):
        _load_document_or_state_error(path)


def test_state_view_helper_incomplete_document_raises() -> None:
    """An incomplete-but-valid-TOML document raises ``StateInputError`` (BR2-1).

    Called bare, ``document_to_state`` raises ``NonExistentKey`` here; the helper
    must route it to the exit-``3`` channel instead.
    """
    document = tomlkit.parse(_INCOMPLETE_STATE)
    # Confirm the bare call raises the lower-level fault the helper must wrap.
    with pytest.raises(KeyError):
        document_to_state(document)
    with pytest.raises(StateInputError):
        _state_view_or_state_error(document)


def test_state_view_helper_bad_phase_raises() -> None:
    """A bad-phase-string document raises ``StateInputError`` (BR2-1).

    Called bare, ``document_to_state`` raises ``ValueError`` from ``Phase(...)``;
    the helper must route it to the exit-``3`` channel.
    """
    document = tomlkit.parse(_BAD_PHASE_STATE)
    with pytest.raises(ValueError, match="nope"):
        document_to_state(document)
    with pytest.raises(StateInputError):
        _state_view_or_state_error(document)


_cursor_triples = st.tuples(
    st.integers(min_value=-2, max_value=6),
    st.integers(min_value=-1, max_value=4),
    st.integers(min_value=-1, max_value=4),
)


# The ``populated_chapter_planning_tree`` factory rebuilds and overwrites the
# tree into the shared ``tmp_path`` on every call, so the (function-scoped)
# fixture not being reset between generated inputs is harmless here — each
# example reconstructs the subject from scratch before driving the body.
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(cursor=_cursor_triples)
def test_set_cursor_accepts_exactly_coherent_cursors(
    populated_chapter_planning_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    cursor: tuple[int, int, int],
) -> None:
    """``set-cursor`` succeeds iff ``validate_state`` of the proposed state is empty.

    The oracle is the validator: editing the cursor in a fresh copy of the
    document and re-deriving the typed view gives the proposed state; the body
    must write (exit ``0``) exactly when that state is coherent and refuse (exit
    ``3``) otherwise. The tree is rebuilt every example so a successful write does
    not leak into the next case.
    """
    chapter, scene, beat = cursor
    working = populated_chapter_planning_tree()
    state_path = working / "state.toml"
    # The fixture builds a ``chapter-planning`` tree; move it into ``drafting``
    # so the populated manifest with a non-trivial cursor is the subject. The
    # cursor edits below are what the property varies.
    document = load_document(state_path)
    document["phase"]["completed"].append("chapter-planning")
    document["phase"]["current"] = "drafting"
    state_path.write_text(tomlkit.dumps(document), encoding="utf-8")

    # Compute the oracle verdict for the proposed cursor.
    probe = load_document(state_path)
    probe["drafting"]["current_chapter"] = chapter
    probe["drafting"]["current_scene"] = scene
    probe["drafting"]["current_beat"] = beat
    oracle_coherent = not validate_state(document_to_state(probe))

    # The chdir MUST precede the suppress block. ``set_cursor`` resolves its
    # target via ``_state_path()`` = ``Path('working')/'state.toml'`` — a
    # cwd-RELATIVE path evaluated at call time (_state_mutators.py:57-59). If cwd
    # is not ``working.parent`` when ``set_cursor`` runs, it cannot find
    # ``working/state.toml``, raises ``StateInputError`` (swallowed by the
    # suppress), and ``result_payload`` stays ``None`` — making the
    # ``oracle_coherent`` arm fail for every coherent example.
    monkeypatch.chdir(working.parent)
    outcome: CommandOutcome | None = None
    with contextlib.suppress(StateInputError):
        outcome = set_cursor(chapter=chapter, scene=scene, beat=beat)

    if oracle_coherent:
        assert outcome is not None
        assert outcome.code == ExitCode.SUCCESS
        # The write-shaped success ``result`` echoes the exact coherent cursor
        # over the whole input space, never the ``violations`` read shape
        # (roadmap 1.3.5; audit-2.2.2 Finding 2).
        assert dict(outcome.result) == {
            "current_chapter": chapter,
            "current_scene": scene,
            "current_beat": beat,
        }
        assert "violations" not in outcome.result
    else:
        assert outcome is None  # the body raised StateInputError (exit 3)


def test_advance_phase_append_preserves_untouched_tables(
    populated_chapter_planning_tree: cabc.Callable[[], Path],
) -> None:
    """Appending to ``completed`` and setting ``current`` touches only those keys.

    The append-to-array sub-case (a freshly built tree's ``completed`` array) was
    not specifically covered by the task 2.2.1 value-edit probe; this asserts the
    ``tomlkit`` round-trip rewrites only the touched array and scalar, leaving the
    other tables and any comments byte-for-byte (ExecPlan Risk "append
    round-trip", advisory A5).
    """
    working = populated_chapter_planning_tree()
    document = load_document(working / "state.toml")
    before = tomlkit.dumps(document)

    document["phase"]["completed"].append("chapter-planning")
    document["phase"]["current"] = "drafting"
    after = tomlkit.dumps(document)

    # The only lines that differ are the two touched ``[phase]`` keys; every other
    # table (``[novel]``, ``[gates]``, ``[word_counts]``, ``[[chapters]]``) and
    # any comments survive byte-for-byte.
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    changed = {
        line
        for line in set(before_lines).symmetric_difference(after_lines)
        if line.strip()
    }
    for line in changed:
        assert "current" in line or "completed" in line, (
            f"append disturbed an untouched line: {line!r}"
        )
    # The untouched tables are present in both renderings unchanged.
    for marker in ("[novel]", "[gates.knitting]", "[word_counts]", "chapters = ["):
        assert marker in before, f"{marker} missing before the append"
        assert marker in after, f"{marker} missing after the append"
