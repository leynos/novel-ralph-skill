"""Pure-function scanner for the ``SKILL.md`` command-contract restatement.

This support module carries the markdown parsing helpers used by
``tests/test_skill_contract_drift_guard.py`` (roadmap 6.3.7) and
``tests/test_developers_guide_contract_drift_guard.py`` (roadmap 6.3.9). It is
extracted so the guard modules stay under the 400-line cap (AGENTS.md lines
24-27), mirroring the ``tests/_state_layout_scanner.py`` split. The functions
are pure over document text — they take the document as a parameter and never
touch the filesystem, shell out, or import ``novel_ralph_skill``.

The exit-code helpers are shape-tolerant across every restatement copy: the
guide's exit-code table has only two columns (Code, Meaning), narrower than the
SKILL (3), ADR-003 (3), and design §3.2 (4) copies, and
:func:`extract_exit_code_meanings` reads columns 0 and 1 only, so the
two-column table parses unchanged. The envelope field set is read two ways:
:func:`extract_fenced_json` for the SKILL/design ``json`` skeletons, and
:func:`extract_brace_field_list` for the developers' guide, which names the
field set inline as a fence-free ``{...}`` brace-list.

The guard pins the agent-facing exit-code table and envelope skeleton in
``skill/novel-ralph/SKILL.md`` to the live ``ExitCode`` enum, the ``Envelope``
field set/order, and ``ENVELOPE_SCHEMA_VERSION``, and cross-checks them against
the canonical ADR-003 Table 2 (``docs/adr-003-shared-interface-contract.md``)
and the harness design §3.1/§3.2 (``docs/novel-ralph-harness-design.md``).

Two parsing carve-outs are load-bearing and recorded in the ExecPlan Decision
Log:

* The three exit-code tables differ in column count (ADR-003 = 3, design §3.2 =
  4, SKILL = 3). :func:`extract_exit_code_meanings` therefore keys the integer
  code (column 0) to the Meaning cell (column 1) *only* and is column-count
  tolerant, discarding every later column.
* The design doc carries two ``json`` fences: the §3.1 six-field skeleton and a
  §4 ``novel done`` example that omits ``working_dir``. Callers must narrow the
  design text to the §3.1 region with :func:`slice_doc_region` *before*
  :func:`extract_fenced_json`, so the wrong fence is never read.
"""

from __future__ import annotations

import re

# A markdown table-separator row is a run of cells whose content is only dashes,
# colons, and spaces (GitHub-flavoured alignment markers). It must be skipped so
# it is never mistaken for a data row.
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")

# The fewest cells an exit-code data row needs: the integer code (column 0) and
# its Meaning (column 1). Rows shorter than this carry no Meaning and are skipped.
_MIN_CODE_ROW_CELLS = 2

# An inline ``{...}`` brace-list naming a field set in document prose. The body
# is captured non-greedily so the FIRST brace-list in the region wins (the
# region-narrowing contract: the caller slices to the envelope section first,
# then takes the first brace-list).
_BRACE_LIST = re.compile(r"\{(?P<body>[^{}]*)\}")

# A fenced code block opening with the requested info string. CommonMark allows
# up to three leading spaces and a fence run of three or more backticks; the
# closing run back-references the opening run so length and character match. The
# body is captured non-greedily so the FIRST matching fence wins (the B1
# ordering contract: callers slice to §3.1 first, then take the first fence).
_FENCE_TEMPLATE = (
    r"^ {{0,3}}(?P<fence>`{{3,}}|~{{3,}}){lang}[^\n]*\n"
    r"(?P<body>.*?)^ {{0,3}}(?P=fence)"
)


def slice_doc_region(text: str, start: str, end: str, *, source: str) -> str:
    """Return the slice of ``text`` from ``start`` up to (excluding) ``end``.

    Pure string slicing over a document's text. ``start`` must appear before
    ``end``; the returned slice runs from the start of ``start`` up to (but
    excluding) ``end``. Both markers must be present, so a renamed or removed
    heading fails loudly rather than yielding an empty region that silently
    passes downstream assertions.

    Unlike the deflation guard's private ``_slice_between``, this slicer names
    ``source`` in its failure message, so a missing anchor in the design doc or
    ADR-003 does not misreport "not found in SKILL.md" (ExecPlan Decision Log).

    Parameters
    ----------
    text : str
        The full document text to slice.
    start : str
        The opening anchor; the slice begins at its first occurrence.
    end : str
        The closing anchor; the slice ends just before its first occurrence
        after ``start``.
    source : str
        A human-readable label for the document, named in failure messages.

    Returns
    -------
    str
        The text from ``start`` up to (but excluding) ``end``.

    Raises
    ------
    ValueError
        If either anchor is absent, or ``end`` does not follow ``start``.
    """
    begin = text.find(start)
    if begin == -1:
        msg = f"anchor {start!r} not found in {source}"
        raise ValueError(msg)
    finish = text.find(end, begin + len(start))
    if finish == -1:
        msg = f"anchor {end!r} not found after {start!r} in {source}"
        raise ValueError(msg)
    return text[begin:finish]


def parse_markdown_table(region: str) -> list[tuple[str, ...]]:
    """Return the data rows of the first markdown table in ``region``.

    Splits a GitHub-flavoured markdown table into stripped cell tuples. It
    tolerates optional leading and trailing pipes and collapses padding
    whitespace, and skips the header separator (``---``) row. Each returned
    tuple has the column count of its source table, which differs by table
    (ADR-003 = 3, design §3.2 = 4, SKILL = 3); callers must not assume a fixed
    width.

    Both the header row and the data rows are returned; the separator row alone
    is dropped, since only it carries the dashes-and-colons alignment markers.

    Parameters
    ----------
    region : str
        The document region containing the table (and possibly surrounding
        prose, which is ignored — only pipe-bearing lines are parsed).

    Returns
    -------
    list[tuple[str, ...]]
        One stripped cell tuple per table row, header included, separator
        excluded.
    """
    rows: list[tuple[str, ...]] = []
    for line in region.splitlines():
        stripped = line.strip()
        if "|" not in stripped:
            continue
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if all(_SEPARATOR_CELL.match(cell) for cell in cells if cell):
            # The alignment row (only dashes/colons) carries no data.
            continue
        rows.append(cells)
    return rows


def extract_exit_code_meanings(rows: list[tuple[str, ...]]) -> dict[int, str]:
    """Map each integer exit code (column 0) to its Meaning cell (column 1).

    This is the column-count-tolerant exit-row extractor (ExecPlan B2 fix): it
    reads columns 0 and 1 and discards every later column, so design §3.2's
    fourth "Example" column does not shift cells. Only the Meaning column is
    load-bearing across the three tables; the Harness-response, Agent-response,
    and Example columns are presentational and deliberately left free.

    Rows whose column-0 cell is not an integer (the header row, or a stray
    blank line) are skipped, so a non-data row cannot corrupt the map.

    Parameters
    ----------
    rows : list[tuple[str, ...]]
        Table rows from :func:`parse_markdown_table`.

    Returns
    -------
    dict[int, str]
        A mapping from each integer code to its Meaning cell text.
    """
    meanings: dict[int, str] = {}
    for cells in rows:
        if len(cells) < _MIN_CODE_ROW_CELLS:
            continue
        try:
            code = int(cells[0])
        except ValueError:
            continue
        meanings[code] = cells[1]
    return meanings


def extract_fenced_json(region: str, fence_lang: str = "json") -> str:
    """Return the body of the first ``fence_lang`` fenced block in ``region``.

    Pulls the FIRST fenced code block whose info string starts with
    ``fence_lang`` out of the region it is given, failing loudly if none is
    present (a vacuous-pass guard). It operates on whatever region the caller
    passes, so to read the design §3.1 envelope skeleton the caller MUST narrow
    the design text to the §3.1 slice first (ExecPlan B1); otherwise a region
    passed too wide risks pulling a later, wrong fence.

    Parameters
    ----------
    region : str
        The document region to search.
    fence_lang : str, optional
        The fenced-block info-string prefix to match (default ``"json"``).

    Returns
    -------
    str
        The body text of the first matching fenced block.

    Raises
    ------
    ValueError
        If ``region`` holds no ``fence_lang`` fenced block.
    """
    pattern = re.compile(
        _FENCE_TEMPLATE.format(lang=re.escape(fence_lang)),
        re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(region)
    if match is None:
        msg = f"no {fence_lang!r} fenced block found in region"
        raise ValueError(msg)
    return match.group("body")


def extract_brace_field_list(region: str, *, source: str) -> list[str]:
    """Return the ordered field names of the first ``{...}`` brace-list.

    This is the fence-free counterpart of :func:`extract_fenced_json`, used for
    the developers' guide (roadmap 6.3.9): its "### The shared JSON envelope"
    section names the envelope field set inline as a single brace-list,
    ``{command, schema_version, ok, working_dir, result, messages}``, rather than
    in a ``json`` fence. The helper finds the FIRST brace-list in the region it
    is given, splits it on commas, and strips surrounding whitespace and
    backticks from each field, returning the field names in document order. The
    caller must narrow the region to the envelope section first (with
    :func:`slice_doc_region`), so a second, stray brace-list elsewhere is never
    read. It fails loudly when no brace-list is present, mirroring
    :func:`extract_fenced_json`'s vacuous-pass guard.

    Empty comma-split fragments (e.g. a trailing comma) are discarded, so a
    cosmetic trailing comma does not introduce a spurious blank field.

    Parameters
    ----------
    region : str
        The document region to search (already narrowed by the caller).
    source : str
        A human-readable label for the document, named in failure messages.

    Returns
    -------
    list[str]
        The brace-list field names in order, stripped of whitespace and
        backticks.

    Raises
    ------
    ValueError
        If ``region`` holds no ``{...}`` brace-list.
    """
    match = _BRACE_LIST.search(region)
    if match is None:
        msg = f"no brace-list found in {source}"
        raise ValueError(msg)
    fields: list[str] = []
    for raw in match.group("body").split(","):
        field = raw.strip().strip("`").strip()
        if field:
            fields.append(field)
    return fields
