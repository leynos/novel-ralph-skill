"""Pure ``critic-notes.md`` BLOCKER-finding grammar for the ``novel-done`` clause.

The spiteful critic's strict output format (``critic-personas.md``, "Resolving a
BLOCKER"; roadmap 3.1.5) writes blockers as ``### Bn — <label>`` finding headings
under a ``## BLOCKER`` section heading. These two pure ``str``-classifying
helpers re-express that grammar so the
:func:`~novel_ralph_skill.state.done_predicate.no_unresolved_blockers` clause and
its tests can classify a notes body — or a single heading line — without a
filesystem round-trip (audit-3.1.4 Finding 4).

They live in their own module so
:mod:`novel_ralph_skill.state.done_predicate` stays under the AGENTS.md 400-line
cap once the heading-aware parser lands (ExecPlan D-BLOCKER-MODULE), mirroring the
:mod:`novel_ralph_skill.state._disk_paths` split. The module writes nothing and
holds no state; the file-fault boundary stays in ``done_predicate.py``.
"""

from __future__ import annotations

import typing as typ

# The spiteful critic's strict output format (``critic-personas.md``, "Resolving
# a BLOCKER"; roadmap 3.1.5). A blocker is a ``### Bn — <label>`` finding heading
# *under* the ``## BLOCKER`` section heading: the section is entered on a line
# whose stripped text equals ``## BLOCKER`` and left on the next ``##``-level
# heading. A finding is resolved when its heading line ends with a single space
# and then the ``[resolved]`` token and nothing after it. The grammar is
# case-sensitive (D-BLOCKER-CASE) and the token must be the *trailing* marker
# (D-BLOCKER-POSITIONAL/D-BLOCKER-TRAILING), so an incidental mid-line quotation
# or trailing text after the token leaves the finding unresolved.
_BLOCKER_SECTION: typ.Final = "## BLOCKER"
# The finding-heading prefix; a finding is ``### B`` followed by one or more
# digits, then the ``—`` label (we only require the digit run, per the critic's
# ``B1``/``B2`` numbering).
_FINDING_PREFIX: typ.Final = "### B"
_SECTION_PREFIX: typ.Final = "## "
# why: the token spells a resolution marker, not a credential; the S105
# hardcoded-password heuristic only sees the literal string assignment.
_RESOLVED_TOKEN: typ.Final = "[resolved]"  # noqa: S105
# A finding heading is resolved only when it ends with a space then the token,
# so a heading whose label happens to be exactly ``[resolved]`` (no separating
# space) does not self-resolve.
_RESOLVED_SUFFIX: typ.Final = f" {_RESOLVED_TOKEN}"


def _line_is_unresolved_blocker_finding(stripped: str) -> bool:
    """Return whether a stripped line is an *unresolved* ``### Bn`` finding.

    True when ``stripped`` is a ``### B<digits>`` finding heading (the spiteful
    critic's strict ``B1``/``B2`` numbering; ``critic-personas.md``) that does
    **not** end with a space then the ``[resolved]`` token. The token is the
    *trailing* marker (D-BLOCKER-POSITIONAL, D-BLOCKER-TRAILING): an incidental
    mid-line mention or any trailing text after the token leaves the finding
    unresolved by design. The match is case-sensitive (D-BLOCKER-CASE).

    Pure ``str -> bool`` (audit-3.1.4 Finding 4), so the unit and property tests
    classify strings without a filesystem round-trip.
    """
    if not stripped.startswith(_FINDING_PREFIX):
        return False
    digits = stripped[len(_FINDING_PREFIX) :]
    # Require at least one digit immediately after ``### B`` so a ``### Beat``
    # heading (no digit) is not mistaken for a finding.
    if not digits or not digits[0].isdigit():
        return False
    return not stripped.endswith(_RESOLVED_SUFFIX)


def _body_has_unresolved_blocker(body: str) -> bool:
    """Return whether ``body`` carries an unresolved BLOCKER finding.

    Walks the lines tracking whether the cursor sits inside the ``## BLOCKER``
    section: it is entered on a line whose stripped text equals ``## BLOCKER``
    and left on the next ``##``-level section heading. A finding line inside that
    section that :func:`_line_is_unresolved_blocker_finding` deems unresolved
    fails the clause. The convergence sentinel ``No BLOCKER. No MAJOR.``
    (``critic-personas.md``) writes no ``## BLOCKER`` heading, so it is clean by
    construction (D-BLOCKER-SENTINEL).

    Pure ``str -> bool`` over the in-memory body; the file-fault boundary lives
    in :func:`~novel_ralph_skill.state.done_predicate._contains_unresolved_blocker`.
    """
    in_blocker_section = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(_SECTION_PREFIX):
            in_blocker_section = stripped == _BLOCKER_SECTION
            continue
        if in_blocker_section and _line_is_unresolved_blocker_finding(stripped):
            return True
    return False
