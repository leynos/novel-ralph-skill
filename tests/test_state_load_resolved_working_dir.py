"""Unit tests for :func:`resolved_working_dir` (roadmap 6.3.4).

Pin that the new accessor returns the absolute, resolved ``working/`` path the
production entry point stamps, that it succeeds when ``working/`` is absent (the
non-strict ``Path.resolve()`` semantics the exit-``3`` arm relies on), and that
it stays coherent with :func:`working_dir` so the two accessors cannot drift.
"""

from __future__ import annotations

import typing as typ

from novel_ralph_skill.commands.state_sourcing import (
    resolved_working_dir,
    working_dir,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_resolved_working_dir_is_absolute_cwd_join(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It resolves ``working/`` against the cwd to an absolute path."""
    monkeypatch.chdir(tmp_path)
    resolved = resolved_working_dir()
    assert resolved == tmp_path.resolve() / "working", (
        "resolved_working_dir must join the resolved cwd with 'working'"
    )
    assert resolved.is_absolute(), "resolved_working_dir must return an absolute path"


def test_resolved_working_dir_succeeds_without_working_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It succeeds even when no ``working/`` exists (non-strict resolve)."""
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / "working").exists(), "the test requires no working/ on disk"
    # Must not raise despite the absent target, and still yields an absolute path.
    assert resolved_working_dir().is_absolute(), (
        "resolved_working_dir must succeed and stay absolute without working/"
    )


def test_resolved_working_dir_matches_working_dir_resolve(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It equals ``working_dir().resolve()`` so the accessors stay coherent."""
    monkeypatch.chdir(tmp_path)
    assert resolved_working_dir() == working_dir().resolve(), (
        "resolved_working_dir must equal working_dir().resolve() for coherence"
    )
