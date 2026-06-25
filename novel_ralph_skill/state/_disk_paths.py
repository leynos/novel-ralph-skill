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
from pathlib import PurePosixPath

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path


def _chapter_dir_name(number: int) -> str:
    """Return the ``chapter-NN`` directory name for a one-based chapter number."""
    return f"chapter-{number:02d}"


def _chapter_number_of(pure: PurePosixPath) -> int | None:
    """Return the chapter number of a ``manuscript/chapter-NN`` path, else ``None``.

    ``None`` signals a path that is not a well-formed chapter directory under
    ``manuscript/`` (so the caller treats the declaration as malformed).
    """
    if pure.parent.name != "manuscript" or not pure.name.startswith("chapter-"):
        return None
    suffix = pure.name.removeprefix("chapter-")
    return int(suffix) if suffix.isdigit() else None


def _declared_chapter_numbers(paths: cabc.Sequence[str]) -> set[int] | None:
    """Return the chapter numbers a ``set-chapters`` turn's ``chapter-NN/`` paths name.

    Each declared chapter path ends in ``manuscript/chapter-NN``; the trailing
    ``NN`` is parsed back to an integer. A ``state.toml`` path is skipped. Returns
    ``None`` when *any* other path is not a well-formed ``chapter-NN`` directory
    under ``manuscript/``, so a malformed declaration falls through to REFUSE rather
    than being silently treated as explained (roadmap task 2.2.3, Work item 3a).
    """
    numbers: set[int] = set()
    for path in paths:
        pure = PurePosixPath(path)
        if pure.name == "state.toml":
            continue
        number = _chapter_number_of(pure)
        if number is None:
            return None
        numbers.add(number)
    return numbers


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
