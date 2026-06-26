"""Unit proof for the shared actionable draft-read (exit-3) message helper.

These tests pin the executable specification for
:func:`novel_ralph_skill.commands.novel_state._draft_read_error`: the message a
present-but-faulted ``draft.md``/``compiled.md`` read emits on the exit-3
channel. Unlike :func:`_state_input_error`, the draft-read formatter has a single
arm — the ``working/`` tree exists, so ``novel state init`` is the wrong remedy —
and it names the read ``working/`` tree and asks for inspection or repair without
leaking a raw ``Errno``, a ``{exc}`` repr, or a traceback marker (roadmap
§6.3.5; ExecPlan Decision D2).

The cross-boundary parity and behavioural proofs live in
``tests/test_draft_read_message_parity.py`` and
``tests/test_draft_read_message_bdd.py``; the structurally-incomplete
``state.toml`` fault is a *state-document* fault routed through
:func:`_state_input_error` instead (Decision D7) and is proven elsewhere.
"""

from __future__ import annotations

import pathlib

import pytest

from novel_ralph_skill.commands.novel_state import _draft_read_error
from novel_ralph_skill.contract.runner import StateInputError


@pytest.mark.parametrize(
    ("exc", "forbidden_fragment"),
    [
        pytest.param(
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
            "invalid start byte",
            id="undecodable-draft",
        ),
        pytest.param(
            PermissionError(13, "Permission denied"),
            "Permission denied",
            id="unreadable-draft",
        ),
    ],
)
def test_draft_read_message_is_actionable(
    exc: Exception, forbidden_fragment: str
) -> None:
    """The draft-read message names the ``working/`` tree and a repair remedy.

    Exercises a representative pair of :data:`STATE_INPUT_ERRORS` members — an
    undecodable body (``UnicodeDecodeError``) and an unreadable file
    (``PermissionError``) — to prove the message text is independent of the
    caught fault: it never interpolates the ``{exc}`` repr or a raw ``Errno``.
    Each case forbids its *own* distinctive fragment (the codec detail for the
    decode fault, the ``Permission denied`` text for the read fault) so a leak of
    either fault's repr is caught independently.
    """
    reported_dir = pathlib.Path("working")

    error = _draft_read_error(reported_dir, exc)

    assert isinstance(error, StateInputError)
    (message,) = error.messages
    assert str(reported_dir) in message, "the message must name the working/ tree"
    assert "inspect and repair" in message, "the message must offer a repair remedy"
    assert "novel state init" not in message, (
        "a present-but-faulted draft must not advise init; the tree exists"
    )
    assert "Errno" not in message, "the message must not leak a raw Errno"
    assert forbidden_fragment not in message, (
        "the message must not leak this fault's caught-exception repr"
    )
    assert "Traceback" not in message, "the message must not leak a traceback marker"


def test_draft_read_error_chains_the_cause() -> None:
    """Raising the error ``from exc`` preserves the cause for debugging.

    The actionable prose carries no ``{exc}`` text, but the chained cause must
    survive so a developer can still inspect the original fault.
    """
    cause = PermissionError(13, "Permission denied")

    with pytest.raises(StateInputError) as excinfo:
        raise _draft_read_error(pathlib.Path("working"), cause) from cause

    assert excinfo.value.__cause__ is cause, "the original fault must be chained"
