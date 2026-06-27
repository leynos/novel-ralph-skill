"""Durable guard that the spaced-name-to-verb split lives in exactly one place.

Roadmap task 7.3.8 consolidated the spaced-name-to-verb derivation
(``name.split(" ", 1)[1]``) into
:data:`novel_ralph_skill.contract.names.SUBCOMMAND_VERBS`, which every consumer
now reads through :data:`SUBCOMMAND_VERBS` or
:func:`~novel_ralph_skill.contract.names.verb_for`. Two prior audits (1.2.13
Finding 3, 1.2.15 Finding 1) flagged the open-coded idiom, and 1.2.15 reproduced
it rather than consolidating it, so the debt persisted across two tasks.

This module is the lasting regression guard the one-shot acceptance grep cannot
be: it walks the production and test trees and asserts the *live* split idiom
appears in exactly one place — the ``SUBCOMMAND_VERBS`` definition in
``novel_ralph_skill/contract/names.py``. A re-introduced inline split in any new
or existing module fails here without waiting for a third audit. Modelled on
``tests/test_legacy_surface_retired.py``'s source-scan guards.

Documentation and comment mentions of the idiom (its appearance in docstrings,
comments, or any string literal) are not live code, so the scan tokenizes each
module and drops every string, comment, and f-string token before counting;
this guard module itself carries the pattern as a string literal, so it is also
excluded from the walk the way ``test_legacy_surface_retired.py`` excludes the
decorator lines.
"""

from __future__ import annotations

import io
import token
import tokenize
import typing as typ

if typ.TYPE_CHECKING:
    from pathlib import Path

# The live spaced-name-to-verb split idiom, in code form (a receiver followed by
# ``.split(" ", 1)[1]``). The single surviving occurrence defines
# ``SUBCOMMAND_VERBS`` in ``novel_ralph_skill/contract/names.py``.
_SPLIT_IDIOM = '.split(" ", 1)[1]'

# The one production and test trees the guard walks.
_SCANNED_TREES: tuple[str, ...] = ("novel_ralph_skill", "tests")

# The single file that legitimately defines the idiom, relative to the repo root.
_OWNING_FILE = "novel_ralph_skill/contract/names.py"

# This guard module's own path, excluded because it carries the idiom as a string
# literal (``_SPLIT_IDIOM``) and in prose, not as a live derivation.
_GUARD_MODULE = "tests/test_verb_derivation_home.py"

# The token kinds that are documentation, not live code: docstrings and other
# string literals, comments, and (since 3.12) the f-string text/middle tokens.
_NON_CODE_TOKENS = frozenset({
    token.STRING,
    token.COMMENT,
    token.FSTRING_START,
    token.FSTRING_MIDDLE,
    token.FSTRING_END,
})


def _non_code_offsets(source: str) -> set[int]:
    """Return the character offsets ``source`` spends inside non-code tokens.

    Tokenizes ``source`` and collects every character offset that falls within a
    string literal, comment, or f-string text token. The idiom itself contains a
    ``" "`` string literal, so dropping those tokens wholesale would shred a live
    occurrence; instead the caller counts substring matches that *start* outside
    these offsets, so a documentation or string-literal mention of the idiom is
    excluded while the live ``name.split(" ", 1)[1]`` expression — whose leading
    ``.`` is an OP token, not part of any string or comment — still counts.

    Parameters
    ----------
    source : str
        A Python module's source text.

    Returns
    -------
    set[int]
        The flat character offsets covered by non-code tokens.
    """
    lines = source.splitlines(keepends=True)
    line_start = [0]
    for line in lines:
        line_start.append(line_start[-1] + len(line))
    offsets: set[int] = set()
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok in tokens:
        if tok.type not in _NON_CODE_TOKENS:
            continue
        (start_row, start_col), (end_row, end_col) = tok.start, tok.end
        start = line_start[start_row - 1] + start_col
        end = line_start[end_row - 1] + end_col
        offsets.update(range(start, end))
    return offsets


def _live_idiom_count(source: str) -> int:
    """Return how many *live* split idioms ``source`` contains.

    Counts occurrences of the split idiom whose first character lies in live
    code — outside any string literal, comment, or f-string text token (see
    :func:`_non_code_offsets`). A docstring or comment mention of the idiom, or a
    deliberate string-literal copy of it (as this guard module itself holds in
    :data:`_SPLIT_IDIOM`), starts inside a non-code token and is excluded; a live
    ``name.split(" ", 1)[1]`` expression starts at its leading ``.`` OP token and
    is counted.

    Parameters
    ----------
    source : str
        A Python module's source text.

    Returns
    -------
    int
        The number of live split-idiom occurrences.
    """
    non_code = _non_code_offsets(source)
    count = 0
    start = source.find(_SPLIT_IDIOM)
    while start != -1:
        if start not in non_code:
            count += 1
        start = source.find(_SPLIT_IDIOM, start + 1)
    return count


def test_split_idiom_survives_only_in_the_registry(project_root: Path) -> None:
    """The spaced-name-to-verb split idiom lives in exactly one place.

    Walks ``novel_ralph_skill/`` and ``tests/`` (excluding this guard module) and
    asserts the live ``.split(" ", 1)[1]`` idiom appears exactly once, in the
    ``SUBCOMMAND_VERBS`` definition in ``contract/names.py`` (roadmap task 7.3.8).
    A re-introduced inline split anywhere else fails here, making the
    consolidation durable rather than a one-shot grep.
    """
    offenders: dict[str, int] = {}
    owning_count = 0
    for tree in _SCANNED_TREES:
        for path in sorted((project_root / tree).rglob("*.py")):
            rel = path.relative_to(project_root).as_posix()
            if rel == _GUARD_MODULE:
                continue
            count = _live_idiom_count(path.read_text(encoding="utf-8"))
            if count == 0:
                continue
            if rel == _OWNING_FILE:
                owning_count = count
            else:
                offenders[rel] = count
    assert not offenders, (
        "the spaced-name-to-verb split idiom must live only in "
        f"{_OWNING_FILE}; re-introduced inline in: {offenders}"
    )
    assert owning_count == 1, (
        f"{_OWNING_FILE} must hold exactly one split idiom "
        f"(the SUBCOMMAND_VERBS definition); found {owning_count}"
    )
