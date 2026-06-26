"""Anti-drift proof that both state-load boundaries emit identical exit-3 prose.

Roadmap §6.3.1 exists to stop the reader/checker loader and the mutator loader
from emitting divergent state-input (exit-3) messages. Both now route through the
one :func:`~novel_ralph_skill.commands.novel_state._state_input_error` helper, so
this test drives each from the same ``working/``-less directory and asserts their
``messages`` are byte-for-byte identical. It fails the moment either boundary
forks its own message string again.
"""

from __future__ import annotations

import typing as typ

import pytest

from novel_ralph_skill.commands._state_mutators import (
    _load_document_or_state_error,
)
from novel_ralph_skill.commands.novel_state import (
    _load_or_state_error,
    state_path,
)
from novel_ralph_skill.contract.runner import StateInputError

if typ.TYPE_CHECKING:
    import pathlib


def test_both_load_boundaries_emit_identical_missing_message(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reader and mutator loaders emit byte-for-byte identical prose.

    The reader loader uses ``tomllib`` and the mutator loader uses ``tomlkit``,
    yet both must surface the same actionable message because they share the one
    :func:`_state_input_error` helper. A divergence in either fails here.
    """
    monkeypatch.chdir(tmp_path)
    path = state_path()

    with pytest.raises(StateInputError) as reader:
        _load_or_state_error(path)
    with pytest.raises(StateInputError) as mutator:
        _load_document_or_state_error(path)

    assert reader.value.messages == mutator.value.messages, (
        "the reader and mutator loaders must emit identical actionable prose"
    )
