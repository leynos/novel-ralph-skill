"""Unit tests pinning the compile-currency seam in ``compile_model``.

These pin the three seam members roadmap task 7.1.1 promotes into
:mod:`novel_ralph_skill.state.compile_model` as the single owners of the
compile-currency projection and the ``compiled.md`` path (audit-4.1.2
Findings 1 and 2):

- :func:`~novel_ralph_skill.state.compile_is_current`, the content-polarity
  projection whose three-valued truth table is exhaustively asserted so a
  future fourth :class:`CompiledComparison` member forces a decision here;
- :data:`~novel_ralph_skill.state.COMPILED_REL`, the byte-exact
  working-prefixed envelope token the snapshot suites also pin, restated at
  the seam so a hand-edit to the constant is red here too;
- :func:`~novel_ralph_skill.state.compiled_manuscript_path`, the single
  filesystem join, whose POSIX form must reproduce ``COMPILED_REL`` without a
  doubled ``working/`` prefix.

The closed three-value enumeration needs no Hypothesis/CrossHair adversary
(``python-verification``): there is no generated input space and the logic is a
one-line projection, so example-based parametrization is exhaustive.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from novel_ralph_skill.state import (
    COMPILED_REL,
    CompiledComparison,
    compile_is_current,
    compiled_manuscript_path,
)


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        (CompiledComparison.MATCHES, True),
        (CompiledComparison.ABSENT, False),
        (CompiledComparison.DIVERGES, False),
    ],
    ids=lambda value: value.value if isinstance(value, CompiledComparison) else None,
)
def test_compile_is_current_truth_table(
    verdict: CompiledComparison, *, expected: bool
) -> None:
    """``compile_is_current`` holds only for ``MATCHES``."""
    assert compile_is_current(verdict) is expected


def test_compile_is_current_covers_every_verdict() -> None:
    """The truth table above enumerates every ``CompiledComparison`` member.

    A future fourth member would leave this set non-empty, forcing a decision on
    its polarity rather than letting it default silently.
    """
    pinned = {
        CompiledComparison.MATCHES,
        CompiledComparison.ABSENT,
        CompiledComparison.DIVERGES,
    }
    assert set(CompiledComparison) == pinned


def test_compiled_rel_is_the_working_prefixed_token() -> None:
    """``COMPILED_REL`` is the byte-exact working-prefixed envelope token."""
    assert COMPILED_REL == "working/manuscript/compiled.md"


def test_compiled_manuscript_path_joins_without_doubling_prefix() -> None:
    """The join takes an already-``working/``-anchored directory.

    Joining the ``working/`` directory reproduces the envelope token exactly,
    with no doubled prefix, so the ``Path`` seam and the string token agree.
    """
    working = Path("working")
    expected = working / "manuscript" / "compiled.md"
    assert compiled_manuscript_path(working) == expected
    assert compiled_manuscript_path(working).as_posix() == COMPILED_REL
