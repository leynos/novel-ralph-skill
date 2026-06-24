"""Pytest fixture plugin exposing the divergent-table corpus category by name.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py``, alongside the ``corpus_fixtures`` and
``corpus_live_draft_fixtures`` plugins. It re-exposes the
``DIVERGENT_TABLE_VARIANTS`` corpus category (roadmap 2.1.5, 2.1.6) by fixture
name: the divergent-table trees whose ``[word_counts].by_chapter`` table
deliberately belies the on-disk ``draft.md`` bodies — one member over-counts both
proxy quantities, the other under-counts them — so the draft-reading live oracle
and the table-reading §5.2 validator disagree on at least one proxy.

These fixtures live here rather than in ``corpus_fixtures`` solely because that
module is at the 400-line cap (AGENTS.md lines 24-27): adding the two fixtures
inline would breach the enforced Pylint ``too-many-lines`` ceiling with no
sanctioned remedy. A second registered plugin keeps every fixture available by
name exactly as a ``conftest`` fixture would be, mirroring how
``corpus_live_draft_fixtures.py`` was carved out for the same reason. The split
is along the divergent-table seam: ``corpus_fixtures`` builds and structurally
checks coherent and incoherent trees, while this module exposes the
intentionally table-versus-draft divergent category.

Like ``conftest.py`` this module is inside ``PYTHON_TARGETS``, so it carries a
module docstring and a docstring on every fixture.
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
def divergent_table_variant_names() -> tuple[str, ...]:
    """Return the tuple of divergent-table variant keys.

    Delivering the keys by fixture lets a test iterate the divergent-table set
    without a runtime value import of the ``DIVERGENT_TABLE_VARIANTS`` mapping.

    Returns
    -------
    tuple[str, ...]
        The ``DIVERGENT_TABLE_VARIANTS`` keys.
    """
    return tuple(wc.DIVERGENT_TABLE_VARIANTS)


@pytest.fixture
def divergent_table_tree(
    tmp_path: Path,
) -> cabc.Callable[[str], tuple[WorkingTreeSpec, Path]]:
    """Return a factory building a named divergent-table variant.

    The factory hands back the spec alongside the built tree so the test can run
    the structural oracle and the live-draft reader without naming the
    ``DIVERGENT_TABLE_VARIANTS`` mapping itself.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Callable[[str], tuple[WorkingTreeSpec, Path]]
        A callable ``(name) -> (spec, working_dir)`` that builds the named
        divergent-table variant in its own subdirectory of ``tmp_path``.
    """

    def _build(name: str) -> tuple[WorkingTreeSpec, Path]:
        """Build the named divergent variant; return its spec and ``working/``."""
        spec = wc.DIVERGENT_TABLE_VARIANTS[name]
        dest = tmp_path / name
        dest.mkdir(exist_ok=True)
        return spec, wc.build_working_tree(spec, dest)

    return _build
