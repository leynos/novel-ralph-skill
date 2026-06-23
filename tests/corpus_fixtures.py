"""Pytest fixture plugin exposing the ``working_corpus`` package by name.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py``. It is the runtime importer of the ``working_corpus``
package and re-exposes every corpus datum as a fixture, so test modules consume
the corpus by fixture parameter name and never by a runtime value import (the
developers-guide "Shared test scaffolding" rule).

It lives beside ``conftest.py`` rather than inside it solely because the corpus
fixture surface would push ``conftest.py`` past the 400-line module cap (AGENTS.md
lines 24-27); registering it as a plugin keeps every fixture available by name
exactly as a ``conftest`` fixture would be. The spec *types* are still re-exported
from ``conftest`` under its ``TYPE_CHECKING`` guard, so a test annotation uses the
sanctioned ``from conftest import WorkingTreeSpec`` carve-out.

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

    from working_corpus import ChapterSpec, WorkingTreeSpec


@pytest.fixture
def make_chapter_spec() -> cabc.Callable[..., ChapterSpec]:
    """Return the :class:`ChapterSpec` constructor.

    Handing the constructor through a fixture lets a test build a chapter spec
    without a runtime value import of the corpus package.

    Returns
    -------
    Callable[..., ChapterSpec]
        The keyword-only :class:`ChapterSpec` constructor.
    """
    return wc.ChapterSpec


@pytest.fixture
def make_working_tree_spec() -> cabc.Callable[..., WorkingTreeSpec]:
    """Return the :class:`WorkingTreeSpec` constructor.

    Returns
    -------
    Callable[..., WorkingTreeSpec]
        The keyword-only :class:`WorkingTreeSpec` constructor.
    """
    return wc.WorkingTreeSpec


@pytest.fixture
def build_tree() -> cabc.Callable[[WorkingTreeSpec, Path], Path]:
    """Return the :func:`build_working_tree` builder.

    Returns
    -------
    Callable[[WorkingTreeSpec, Path], Path]
        A callable ``(spec, dest) -> Path`` materialising ``spec`` under
        ``dest`` and returning the ``working/`` path.
    """
    return wc.build_working_tree


@pytest.fixture
def concatenate() -> cabc.Callable[[cabc.Sequence[str]], str]:
    """Return the :func:`concatenate_drafts` compile helper.

    Returns
    -------
    Callable[[Sequence[str]], str]
        A callable joining ordered draft bodies with ``CORPUS_SEPARATOR``.
    """
    return wc.concatenate_drafts


@pytest.fixture
def compile_probe(
    build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
    concatenate: cabc.Callable[[cabc.Sequence[str]], str],
) -> tuple[
    cabc.Callable[[WorkingTreeSpec, Path], Path],
    cabc.Callable[[cabc.Sequence[str]], str],
]:
    """Return the builder and concatenation helper as one bundle.

    Bundling the two callables a compile-model test needs keeps the test's
    parameter list within the project's argument-count gate while still
    delivering both by fixture name.

    Returns
    -------
    tuple[Callable[..., Path], Callable[[Sequence[str]], str]]
        The :func:`build_working_tree` builder and the
        :func:`concatenate_drafts` helper.
    """
    return build_tree, concatenate


@pytest.fixture
def phase_names() -> tuple[str, ...]:
    """Return the eleven phase enum members in order.

    Delivering the phase order by fixture lets a test iterate the phases
    without a runtime value import of the corpus ``PHASE_ORDER`` constant.

    Returns
    -------
    tuple[str, ...]
        The phase enum members ``premise`` … ``done``, in order.
    """
    return wc.PHASE_ORDER


@pytest.fixture
def phase_state_tree(tmp_path: Path) -> cabc.Callable[[str], Path]:
    """Return a factory building the coherent tree for a named phase.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Callable[[str], Path]
        A callable ``(phase) -> Path`` materialising ``PHASE_STATES[phase]``
        under ``tmp_path`` and returning the ``working/`` path. The phase string
        is the only argument; the spec lookup happens inside the factory.
    """

    def _build(phase: str) -> Path:
        """Build the coherent tree for ``phase`` under the test's ``tmp_path``."""
        # A per-phase subdirectory keeps repeated calls within one test from
        # inheriting a previous phase's ``compiled.md`` or chapter directories.
        dest = tmp_path / phase
        dest.mkdir(exist_ok=True)
        return wc.build_working_tree(wc.PHASE_STATES[phase], dest)

    return _build


@pytest.fixture
def baseline_tree(tmp_path: Path) -> cabc.Callable[[], Path]:
    """Return a factory building the canonical coherent baseline tree.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Callable[[], Path]
        A callable ``() -> Path`` materialising ``COHERENT_BASELINE`` under
        ``tmp_path`` and returning the ``working/`` path.
    """

    def _build() -> Path:
        """Build the coherent baseline tree under the test's ``tmp_path``."""
        return wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)

    return _build


@pytest.fixture
def coherent_oracle_cases(
    tmp_path: Path,
) -> list[tuple[WorkingTreeSpec, Path]]:
    """Return ``(spec, working_dir)`` pairs for every coherent corpus tree.

    The baseline and all eleven phase states are each built in their own
    subdirectory of ``tmp_path`` so the trees do not clobber one another. The
    pairs let a test assert the oracle returns the empty tuple for every
    coherent tree without naming the corpus mappings.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the trees are built under.

    Returns
    -------
    list[tuple[WorkingTreeSpec, Path]]
        One ``(spec, working_dir)`` pair per coherent tree.
    """
    cases: list[tuple[WorkingTreeSpec, Path]] = []
    named = {"baseline": wc.COHERENT_BASELINE, **wc.PHASE_STATES}
    for label, spec in named.items():
        dest = tmp_path / label
        dest.mkdir()
        cases.append((spec, wc.build_working_tree(spec, dest)))
    return cases


@pytest.fixture
def incoherent_variant_names() -> tuple[str, ...]:
    """Return the tuple of incoherent-variant keys.

    Delivering the keys by fixture lets a test iterate the variant set without a
    runtime value import of the ``INCOHERENT_VARIANTS`` mapping.

    Returns
    -------
    tuple[str, ...]
        The ``INCOHERENT_VARIANTS`` keys.
    """
    return tuple(wc.INCOHERENT_VARIANTS)


@pytest.fixture
def incoherent_tree(
    tmp_path: Path,
) -> cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]]:
    """Return a factory building a named incoherent variant.

    The factory hands back the spec alongside the built tree so the test can run
    the structural oracle (which reads the spec) without naming the
    ``INCOHERENT_VARIANTS`` mapping itself.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Callable[[str], tuple[WorkingTreeSpec, Path, str]]
        A callable ``(name) -> (spec, working_dir, expected_invariant_name)``
        that builds the named variant under ``tmp_path`` and reports the single
        invariant name it is built to violate.
    """

    def _build(name: str) -> tuple[WorkingTreeSpec, Path, str]:
        """Build the named variant; return its spec, tree, and expected name."""
        spec, expected = wc.INCOHERENT_VARIANTS[name]
        # Build each variant in its own subdirectory so repeated calls within one
        # test do not inherit a previous variant's ``compiled.md`` or chapters.
        dest = tmp_path / name
        dest.mkdir(exist_ok=True)
        return spec, wc.build_working_tree(spec, dest), expected

    return _build


@pytest.fixture
def done_flag_permutation_names() -> tuple[str, ...]:
    """Return the tuple of ``done.flag`` permutation keys.

    Delivering the keys by fixture lets a test iterate the permutation set
    without a runtime value import of the ``DONE_FLAG_PERMUTATIONS`` mapping.

    Returns
    -------
    tuple[str, ...]
        The ``DONE_FLAG_PERMUTATIONS`` keys.
    """
    return tuple(wc.DONE_FLAG_PERMUTATIONS)


@pytest.fixture
def done_flag_tree(
    tmp_path: Path,
) -> cabc.Callable[[str], tuple[WorkingTreeSpec, Path]]:
    """Return a factory building a named ``done.flag`` permutation.

    The factory hands back the spec alongside the built tree so the test can run
    the structural oracle without naming the ``DONE_FLAG_PERMUTATIONS`` mapping.

    Parameters
    ----------
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Callable[[str], tuple[WorkingTreeSpec, Path]]
        A callable ``(name) -> (spec, working_dir)`` that builds the named
        permutation in its own subdirectory of ``tmp_path``.
    """

    def _build(name: str) -> tuple[WorkingTreeSpec, Path]:
        """Build the named permutation; return its spec and ``working/`` path."""
        spec = wc.DONE_FLAG_PERMUTATIONS[name]
        dest = tmp_path / name
        dest.mkdir(exist_ok=True)
        return spec, wc.build_working_tree(spec, dest)

    return _build


@pytest.fixture
def check_corpus() -> cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]]:
    """Return the :func:`corpus_check` structural oracle.

    Returns
    -------
    Callable[[WorkingTreeSpec, Path], tuple[str, ...]]
        A callable ``(spec, working_dir) -> tuple[str, ...]`` returning the
        invariant names the tree violates (an empty tuple means coherent).
    """
    return wc.corpus_check


@pytest.fixture
def corpus_invariant_names() -> tuple[str, ...]:
    """Return the oracle's stable invariant-name vocabulary.

    Returns
    -------
    tuple[str, ...]
        The ``CORPUS_INVARIANT_NAMES`` tuple, the same strings task 2.1.2's
        validator keys its cross-check on.
    """
    return wc.CORPUS_INVARIANT_NAMES


@pytest.fixture
def corpus_gate_thresholds() -> tuple[float, float, float]:
    """Return the corpus's knitting-gate threshold triple.

    Returns
    -------
    tuple[float, float, float]
        The ``GATE_THRESHOLDS`` triple, the corpus's independent copy of the
        §5.2 ``0.30 / 0.50 / 0.80`` thresholds; a test pins it equal to the
        production validator constant so the two cannot drift (audit:2.1.2
        finding 1).
    """
    return wc.GATE_THRESHOLDS
