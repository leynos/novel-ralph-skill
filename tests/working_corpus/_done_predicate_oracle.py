"""Corpus-side oracle twins for the two new ``novel-done`` disk clauses.

The ``novel-done`` ``knitting_gates_passed`` review-existence read and
``no_unresolved_blockers`` BLOCKER scan are disk-evidence reads of the same shape
the §5.4 detector's clauses are, so each gets an independent corpus-side twin
that reads the materialised ``working/`` tree (ExecPlan D-TWIN). The twins must
**not** import the production predicate they cross-check; a corpus test pins each
equal to its production counterpart on every ``novel-done`` corpus tree, exactly
as :mod:`._oracle_disk` twins ``disk_evidence``.

The two twins mirror the production
:func:`~novel_ralph_skill.state.done_predicate.knitting_gates_passed` review half
and :func:`~novel_ralph_skill.state.done_predicate.no_unresolved_blockers`,
re-implementing the existence read and the D-BLOCKER substring rule
independently.
"""

from __future__ import annotations

import tomllib
import typing as typ

from ._specs import chapter_dir_name

if typ.TYPE_CHECKING:
    from pathlib import Path

# The three knitting percentages the review-existence twin checks, an
# independent copy of the production ``KNITTING_PERCENTAGES`` a test pins equal.
KNITTING_PERCENTAGES: tuple[int, int, int] = (30, 50, 80)

# The D-BLOCKER-POSITIONAL format, re-spelled independently of the production
# constants so the twin is a genuine cross-check rather than a re-export. The
# token is a *trailing* marker: a line is resolved only when its stripped text
# ends with it, so an incidental mid-line mention does not clear the blocker.
_BLOCKER_PREFIX = "BLOCKER"
_RESOLVED_TOKEN = "[resolved]"  # noqa: S105 - a resolution marker, not a credential


def reviews_all_present(working_dir: Path) -> bool:
    """Return whether all three ``reviews/knitting-NN.md`` files exist on disk.

    The corpus-side twin of the production ``knitting_gates_passed`` clause's
    review-existence half: it reads only the ``reviews/`` directory, never the
    gate booleans (which are pure-state, not disk-evidence).
    """
    reviews = working_dir / "reviews"
    return all(
        (reviews / f"knitting-{percentage}.md").exists()
        for percentage in KNITTING_PERCENTAGES
    )


def _manifest_numbers(working_dir: Path) -> list[int]:
    """Return the manifest chapter numbers from the materialised ``state.toml``."""
    state = tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))
    return sorted(chapter["number"] for chapter in state["chapters"])


def _notes_has_unresolved_blocker(notes_path: Path) -> bool:
    """Return whether ``notes_path`` carries an unresolved BLOCKER line."""
    if not notes_path.exists():
        return False
    body = notes_path.read_text(encoding="utf-8")
    return any(
        stripped.startswith(_BLOCKER_PREFIX) and not stripped.endswith(_RESOLVED_TOKEN)
        for stripped in (line.strip() for line in body.splitlines())
    )


def no_unresolved_blockers(working_dir: Path) -> bool:
    """Return whether no manifest chapter has an unresolved BLOCKER finding.

    The corpus-side twin of the production ``no_unresolved_blockers`` clause: it
    reads the manifest from ``state.toml`` and scans each chapter's
    ``critic-notes.md`` with an independently re-spelled D-BLOCKER rule. An absent
    notes file is clean.
    """
    manuscript = working_dir / "manuscript"
    return not any(
        _notes_has_unresolved_blocker(
            manuscript / chapter_dir_name(number) / "critic-notes.md"
        )
        for number in _manifest_numbers(working_dir)
    )
