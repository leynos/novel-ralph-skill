"""Pytest fixtures exposing the ``novel-done`` predicate corpus by name.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py``, beside ``corpus_fixtures`` and its siblings. It re-exposes
the roadmap 3.1.1 ``novel-done`` corpus — the all-six-clauses-hold tree, the
per-clause failers, the ``[resolved]``/near-miss BLOCKER trees, and the two
oracle twins — as fixtures, so test modules consume them by parameter name and
never by a runtime value import (the developers-guide "Shared test scaffolding"
rule).

It lives in its own module rather than in ``corpus_fixtures.py`` because that
module is already at the 400-line cap (AGENTS.md lines 24-27); registering this
as a plugin keeps every fixture available by name exactly as a ``conftest``
fixture would be. Like ``corpus_fixtures.py`` it carries a module docstring, a
docstring on every fixture, and raises :class:`AssertionError` directly rather
than using a bare ``assert``.
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
def all_hold_tree(tmp_path: Path) -> cabc.Callable[[], Path]:
    """Return a factory building the all-six-clauses-hold ``novel-done`` tree.

    Returns
    -------
    Callable[[], Path]
        A callable ``() -> Path`` materialising ``DONE_PREDICATE_ALL_HOLD`` under
        ``tmp_path`` and returning the ``working/`` path.
    """

    def _build() -> Path:
        """Build the all-hold tree under the test's ``tmp_path``."""
        return wc.build_working_tree(wc.DONE_PREDICATE_ALL_HOLD, tmp_path)

    return _build


@pytest.fixture
def done_predicate_failer_names() -> tuple[str, ...]:
    """Return the per-clause failer keys.

    Returns
    -------
    tuple[str, ...]
        The ``DONE_PREDICATE_FAILERS`` keys, one per ``novel-done`` clause toggle.
    """
    return tuple(wc.DONE_PREDICATE_FAILERS)


@pytest.fixture
def done_predicate_failer_tree(
    tmp_path: Path,
) -> cabc.Callable[[str], tuple[WorkingTreeSpec, Path]]:
    """Return a factory building a named per-clause failer tree.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Callable[[str], tuple[WorkingTreeSpec, Path]]
        A callable ``(name) -> (spec, working_dir)`` building the named failer in
        its own subdirectory of ``tmp_path``.
    """

    def _build(name: str) -> tuple[WorkingTreeSpec, Path]:
        """Build the named failer; return its spec and ``working/`` path."""
        spec = wc.DONE_PREDICATE_FAILERS[name]
        dest = tmp_path / name
        dest.mkdir(exist_ok=True)
        return spec, wc.build_working_tree(spec, dest)

    return _build


@pytest.fixture
def blocker_edge_trees(
    tmp_path: Path,
) -> cabc.Callable[[], tuple[Path, Path]]:
    """Return a factory building the ``[resolved]`` and near-miss BLOCKER trees.

    Returns
    -------
    Callable[[], tuple[Path, Path]]
        A callable ``() -> (resolved_working, near_miss_working)`` building the
        two BLOCKER edge trees in separate subdirectories of ``tmp_path``.
    """

    def _build() -> tuple[Path, Path]:
        """Build the resolved and near-miss BLOCKER trees under ``tmp_path``."""
        resolved = tmp_path / "resolved"
        near_miss = tmp_path / "near-miss"
        resolved.mkdir()
        near_miss.mkdir()
        return (
            wc.build_working_tree(wc.DONE_PREDICATE_RESOLVED_BLOCKER, resolved),
            wc.build_working_tree(wc.DONE_PREDICATE_NEAR_MISS_BLOCKER, near_miss),
        )

    return _build


@pytest.fixture
def sole_stale_compile_tree(tmp_path: Path) -> cabc.Callable[[], Path]:
    """Return a factory building the sole-stale-compile ``novel-done`` tree.

    Returns
    -------
    Callable[[], Path]
        A callable ``() -> Path`` materialising
        ``DONE_PREDICATE_SOLE_STALE_COMPILE`` (every clause holds except
        ``compile_consistent``, false on a present-but-divergent count-coincident
        ``compiled.md``) and returning the ``working/`` path.
    """

    def _build() -> Path:
        """Build the sole-stale-compile tree under the test's ``tmp_path``."""
        return wc.build_working_tree(wc.DONE_PREDICATE_SOLE_STALE_COMPILE, tmp_path)

    return _build


@pytest.fixture
def mid_draft_stale_tree(tmp_path: Path) -> cabc.Callable[[], Path]:
    """Return a factory building the mid-draft-stale ``novel-done`` tree.

    Returns
    -------
    Callable[[], Path]
        A callable ``() -> Path`` materialising
        ``DONE_PREDICATE_MID_DRAFT_STALE`` (a drafting clause unmet *and* a stale
        ``compiled.md``) and returning the ``working/`` path.
    """

    def _build() -> Path:
        """Build the mid-draft-stale tree under the test's ``tmp_path``."""
        return wc.build_working_tree(wc.DONE_PREDICATE_MID_DRAFT_STALE, tmp_path)

    return _build


@pytest.fixture
def oracle_reviews_present() -> cabc.Callable[[Path], bool]:
    """Return the corpus-side review-existence oracle twin.

    Returns
    -------
    Callable[[Path], bool]
        A callable ``(working_dir) -> bool`` reporting whether all three
        ``reviews/knitting-NN.md`` files exist (the ``knitting_gates_passed``
        review half twin).
    """
    return wc.oracle_reviews_all_present


@pytest.fixture
def oracle_no_blockers() -> cabc.Callable[[Path], bool]:
    """Return the corpus-side BLOCKER-scan oracle twin.

    Returns
    -------
    Callable[[Path], bool]
        A callable ``(working_dir) -> bool`` reporting whether no manifest
        chapter carries an unresolved BLOCKER (the ``no_unresolved_blockers``
        twin).
    """
    return wc.oracle_no_unresolved_blockers
