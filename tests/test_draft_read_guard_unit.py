"""Unit proof for the shared draft-read fault guard (exit-3 context manager).

These tests pin the executable specification for
:func:`novel_ralph_skill.commands.state_sourcing.draft_read_guard`: the context
manager that re-raises any :data:`STATE_INPUT_ERRORS` member a wrapped chapter
draft read raises as the actionable exit-``3``
:class:`~novel_ralph_skill.contract.runner.StateInputError` that
:func:`_draft_read_error` builds, chaining the caught exception via ``from``
(roadmap §7.3.3; design §3.2). It is the single home for the
``try/except STATE_INPUT_ERRORS → _draft_read_error`` shell the draft-read
boundaries previously open-coded.

The message itself is pinned in ``tests/test_draft_read_message_unit.py``; the
cross-boundary parity proof lives in
``tests/test_draft_read_message_parity.py``. This file pins the *guard*'s
control flow: which faults it translates, that it chains the cause, that a clean
block raises nothing, and that an out-of-tuple exception escapes unchanged. The
invariant is small and enumerable, so a parametrized unit test is the pinning
adversary (AGENTS.md: property/verification tooling is for invariants over a
range of inputs; here the fault set is finite).
"""

from __future__ import annotations

import pathlib

import pytest

from novel_ralph_skill.commands.state_sourcing import (
    _draft_read_error,
    draft_read_guard,
)
from novel_ralph_skill.contract.runner import StateInputError

_REPORTED_DIR = pathlib.Path("working")


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
            id="undecodable-draft-valueerror-subclass",
        ),
        pytest.param(
            PermissionError(13, "Permission denied"),
            id="unreadable-draft-oserror",
        ),
        pytest.param(KeyError("missing"), id="keyerror"),
    ],
)
def test_guard_translates_state_input_errors_to_exit_three(exc: Exception) -> None:
    """Each ``STATE_INPUT_ERRORS`` member becomes the actionable exit-3 error.

    A representative member of the shared tuple — an ``UnicodeDecodeError`` (the
    ``ValueError`` subclass a bad-UTF-8 body raises), a ``PermissionError`` (an
    ``OSError``), and a ``KeyError`` — raised inside the guard re-emerges as a
    :class:`StateInputError` whose single ``messages`` entry equals the one
    :func:`_draft_read_error` builds for the same reported directory, and whose
    ``__cause__`` is the original fault (the ``from exc`` chain).
    """
    with (
        pytest.raises(StateInputError) as excinfo,
        draft_read_guard(_REPORTED_DIR),
    ):
        raise exc

    (message,) = excinfo.value.messages
    assert message == _draft_read_error(_REPORTED_DIR).messages[0], (
        "the guard must re-raise the formatter-owned draft-read message verbatim"
    )
    assert excinfo.value.__cause__ is exc, "the original fault must be chained"


def test_clean_block_raises_nothing() -> None:
    """A guard around a fault-free block completes without raising."""
    with draft_read_guard(_REPORTED_DIR):
        result = "read ok"

    assert result == "read ok", "a fault-free block must run and raise nothing"


def test_guard_does_not_catch_out_of_tuple_exceptions() -> None:
    """An exception outside ``STATE_INPUT_ERRORS`` propagates unchanged.

    ``RuntimeError`` is not a member of the tuple, so the guard must let it
    escape untranslated rather than mis-routing an unrelated fault to exit ``3``.
    """
    sentinel = RuntimeError("not a state-input fault")

    with (
        pytest.raises(RuntimeError) as excinfo,
        draft_read_guard(_REPORTED_DIR),
    ):
        raise sentinel

    assert excinfo.value is sentinel, (
        "an out-of-tuple exception must escape the guard untranslated"
    )
