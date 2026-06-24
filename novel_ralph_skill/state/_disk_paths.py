"""Shared on-disk manuscript path helpers for the §5.4 disk-evidence detector.

These two pure helpers join and parse the ``manuscript/chapter-NN/`` layout
(``state-layout.md``). They live in their own module so both the structural
predicates in :mod:`novel_ralph_skill.state.disk_evidence` and the word-count
cluster in :mod:`novel_ralph_skill.state._disk_word_counts` can read disk through
one definition without importing each other (keeping ``disk_evidence.py`` under
the AGENTS.md 400-line cap once the §5.4 word-count twins are split out).
"""

from __future__ import annotations

import typing as typ

if typ.TYPE_CHECKING:
    from pathlib import Path


def _chapter_dir_name(number: int) -> str:
    """Return the ``chapter-NN`` directory name for a one-based chapter number."""
    return f"chapter-{number:02d}"


def _on_disk_chapter_numbers(working_dir: Path) -> set[int]:
    """Return the chapter numbers materialised under ``manuscript/``.

    Globs ``manuscript/chapter-*`` directories and parses the two-digit suffix.
    A directory whose suffix is not a valid ``chapter-NN`` integer is ignored, so
    a stray non-chapter directory never crashes the bijection check.
    """
    numbers: set[int] = set()
    for entry in (working_dir / "manuscript").glob("chapter-*"):
        if not entry.is_dir():
            continue
        suffix = entry.name.removeprefix("chapter-")
        if suffix.isdigit():
            numbers.add(int(suffix))
    return numbers
