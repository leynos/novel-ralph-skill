"""Pytest fixture plugin exposing the live-draft corpus oracle by name.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py``, alongside the ``corpus_fixtures`` plugin. It carries the
live-draft cross-check surface — the owned-invariant oracle and the live count
reader — that reconciles the §5.2 validator against the on-disk ``draft.md``
bodies rather than the ``[word_counts]`` table.

These fixtures live here rather than in ``corpus_fixtures`` solely because the
combined corpus fixture surface would push ``corpus_fixtures`` past the 400-line
module cap (AGENTS.md lines 24-27); a second registered plugin keeps every
fixture available by name exactly as a ``conftest`` fixture would be. The split
is along the live-draft seam: ``corpus_fixtures`` builds and structurally checks
trees, while this module reads them as a live draft.

Like ``conftest.py`` this module is inside ``PYTHON_TARGETS``, so it carries a
module docstring, a docstring on every fixture, and raises :class:`AssertionError`
directly rather than using a bare ``assert``.
"""

from __future__ import annotations

import typing as typ

import pytest
import working_corpus as wc

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from working_corpus import WorkingTreeSpec


@pytest.fixture
def check_live_draft() -> cabc.Callable[[WorkingTreeSpec, Path], set[str]]:
    """Return the live-draft owned-invariant oracle ``(spec, working_dir)``.

    Returns
    -------
    Callable[[WorkingTreeSpec, Path], set[str]]
        A callable ``(spec, working_dir) -> set[str]`` returning the owned
        invariant names a tree violates under the live-draft read (the two proxy
        invariants reconciled against the on-disk ``draft.md`` bodies rather than
        the ``[word_counts]`` table).
    """
    return wc.live_draft_owned


@pytest.fixture
def live_draft_counts() -> cabc.Callable[[Path], tuple[int, int]]:
    """Return the live ``(drafted_words, drafted_chapters)`` reader for draft.md.

    Returns
    -------
    Callable[[Path], tuple[int, int]]
        A callable ``(working_dir) -> (drafted_words_total,
        drafted_chapters_count)`` recovering both honest-draft quantities from the
        on-disk ``draft.md`` bodies.
    """
    return wc.live_draft_counts
