"""Shared on-disk manuscript path helpers for the §5.4 disk-evidence detector.

These pure helpers join and parse the ``manuscript/chapter-NN/`` layout
(``state-layout.md``) and classify the manifest/on-disk bijection break. They live
in their own module so both the structural predicates in
:mod:`novel_ralph_skill.state.disk_evidence` and the word-count cluster in
:mod:`novel_ralph_skill.state._disk_word_counts` can read disk through one
definition without importing each other (keeping ``disk_evidence.py`` under the
AGENTS.md 400-line cap once the §5.4 word-count twins are split out). The
:func:`_classify_bijection` helper additionally lives here so both
``manifest-disk-bijection`` production sites —
:mod:`novel_ralph_skill.state.disk_evidence` and
:mod:`novel_ralph_skill.state.reconcile` — share one coherence rule
(audit:2.1.7 Findings 1 and 2) without either importing the other.
"""

from __future__ import annotations

import dataclasses
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


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class _BijectionBreak:
    """The classified break between the chapter manifest and the on-disk dirs.

    The single classification both ``manifest-disk-bijection`` production sites
    share (audit:2.1.7 Findings 1 and 2):
    :func:`~novel_ralph_skill.state.disk_evidence._check_manifest_disk_bijection`
    (the §5.4 detector) and
    :func:`~novel_ralph_skill.state.reconcile._set_chapters_turn_explains_bijection`
    (the reconciler's scoped precedence exception). It splits the break into its
    two directions and pins the contiguity-from-1 notion so the coherence rule
    lives in exactly one place rather than being recomputed inline at each site.

    Attributes
    ----------
    manifest, on_disk : frozenset[int]
        The manifest chapter numbers and the on-disk ``chapter-NN/`` numbers.
    orphans : frozenset[int]
        ``on_disk - manifest`` — a directory with no manifest entry (the
        ``draft-without-manifest-entry`` direction).
    missing : frozenset[int]
        ``manifest - on_disk`` — a manifest entry with no directory (the
        ``manifest-extra-entry`` direction).
    contiguous : bool
        Whether the manifest is the contiguous run ``1..len(manifest)`` (no gap).
    """

    manifest: frozenset[int]
    on_disk: frozenset[int]
    orphans: frozenset[int]
    missing: frozenset[int]
    contiguous: bool

    @property
    def coherent_subset(self) -> bool:
        """Whether the on-disk set is a coherent subset of the manifest.

        ``True`` when the only possible break is the missing-directory direction:
        no orphan and a contiguous manifest. This is exactly the shape the ADR 009
        drafting relaxation suppresses, and the precondition the torn
        ``set-chapters`` precedence requires before the missing dirs can explain
        the break.
        """
        return not self.orphans and self.contiguous

    @property
    def is_bijection(self) -> bool:
        """Whether manifest and on-disk are an exact, contiguous bijection."""
        return self.coherent_subset and not self.missing

    def describe(self) -> str:
        """Return the bijection violation detail: summary plus broken direction(s).

        The historical summary line leads (so snapshot churn is bounded to an
        appended clause), followed by the direction(s) the predicate actually
        computed: orphan directories, manifest entries without directories, and a
        non-contiguous manifest. The relaxation suppresses the detector before this
        is reached for a pure missing-only drafting subset, so a fired break always
        names at least one direction.
        """
        summary = (
            f"manifest chapters {sorted(self.manifest)} are not in bijection with "
            f"the on-disk chapter directories {sorted(self.on_disk)}"
        )
        reasons: list[str] = []
        if self.orphans:
            reasons.append(f"orphan directories {sorted(self.orphans)}")
        if self.missing:
            reasons.append(
                f"manifest entries without directories {sorted(self.missing)}"
            )
        if not self.contiguous:
            reasons.append("non-contiguous manifest")
        if not reasons:
            return summary
        return f"{summary} ({'; '.join(reasons)})"


def _classify_bijection(
    manifest: cabc.Iterable[int], on_disk: cabc.Iterable[int]
) -> _BijectionBreak:
    """Classify the manifest/on-disk break into a frozen :class:`_BijectionBreak`.

    Pure: takes the two chapter-number iterables and returns the directional break
    and the contiguity-from-1 verdict, with no disk access of its own. Both
    production sites consume it so the coherence notion (``coherent_subset``) and
    the ``sorted(manifest) == list(range(1, len(manifest) + 1))`` contiguity literal
    live exactly once (audit:2.1.7 Findings 1 and 2).

    The corpus oracle twin (``tests/working_corpus/_oracle_disk.py``) keeps its own
    independent reimplementation by design (the deliberate-twin discipline), so this
    helper is deliberately not shared with it.
    """
    manifest_set = frozenset(manifest)
    on_disk_set = frozenset(on_disk)
    return _BijectionBreak(
        manifest=manifest_set,
        on_disk=on_disk_set,
        orphans=on_disk_set - manifest_set,
        missing=manifest_set - on_disk_set,
        contiguous=sorted(manifest_set) == list(range(1, len(manifest_set) + 1)),
    )


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
