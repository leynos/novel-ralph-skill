"""Atomic-write tests for ``write_text_atomically`` (roadmap task 4.1.1).

These guard the shared text twin of :func:`write_document_atomically`: the
pre-rendered-string atomic write the ``novel-compile`` write path uses for
``compiled.md`` (ExecPlan Decision Log D-WRITER). They mirror the byte-level,
snapshot-free discipline of ``tests/test_state_document.py``'s atomic-write
suite — exact bytes on success, atomic overwrite, and no stray temp file (and
the prior file left untorn) on a failed write — and live in their own module so
``test_state_document.py`` stays within the AGENTS.md 400-line cap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from novel_ralph_skill.state.document import write_text_atomically


def test_write_text_atomically_writes_exact_bytes(tmp_path: Path) -> None:
    """``write_text_atomically`` leaves exactly the given text on disk.

    The text twin adds no trailing newline or reflow of its own, so the
    ``novel-compile`` write path (roadmap 4.1.1) gets byte-exact output.
    """
    path = tmp_path / "compiled.md"
    body = "first chapter\n\nsecond chapter"
    write_text_atomically(body, path)
    assert path.read_text(encoding="utf-8") == body


def test_write_text_atomically_overwrites_existing_file(tmp_path: Path) -> None:
    """A second ``write_text_atomically`` overwrites the prior file atomically."""
    path = tmp_path / "compiled.md"
    write_text_atomically("stale body", path)
    write_text_atomically("fresh body", path)
    assert path.read_text(encoding="utf-8") == "fresh body"


def test_write_text_atomically_raises_and_leaves_no_temp_on_missing_parent(
    tmp_path: Path,
) -> None:
    """A write whose parent is absent raises ``OSError`` and leaks no temp file.

    ``NamedTemporaryFile(dir=path.parent)`` raises ``FileNotFoundError`` (an
    ``OSError``) when the directory does not exist, exactly the channel
    ``novel-compile`` routes to exit ``3`` for an absent ``manuscript/``. No
    ``.state.toml.*`` temp file must survive in the ancestor directory.
    """
    target = tmp_path / "absent" / "compiled.md"
    with pytest.raises(OSError):  # noqa: PT011 - the absent-parent fault is the assertion
        write_text_atomically("body", target)
    leftovers = [child for child in tmp_path.iterdir() if child.is_file()]
    assert leftovers == [], f"a failed write left stray temp files: {leftovers}"


def test_write_text_atomically_leaves_prior_file_and_no_temp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rename failure leaves the prior file and no stray temp file behind."""
    path = tmp_path / "compiled.md"
    write_text_atomically("prior body", path)

    def _boom(self: Path, target: Path) -> None:
        """Raise as if the rename failed mid-write."""
        del self, target
        msg = "simulated rename failure"
        raise OSError(msg)

    monkeypatch.setattr(Path, "replace", _boom)
    with pytest.raises(OSError, match="simulated rename failure"):
        write_text_atomically("fresh body", path)
    assert path.read_text(encoding="utf-8") == "prior body", (
        "a failed write must leave the prior file untorn"
    )
    leftovers = [
        child
        for child in tmp_path.iterdir()
        if child.name != "compiled.md" and child.is_file()
    ]
    assert leftovers == [], f"a failed write left stray temp files: {leftovers}"
