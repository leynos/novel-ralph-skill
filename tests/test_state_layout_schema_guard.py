"""Guard against drift between the emitted state schema and the reference.

``novel-state init`` emits a ``state.toml`` whose authoritative on-disk layout
is documented in ``skill/novel-ralph/references/state-layout.md`` (design
``docs/novel-ralph-harness-design.md`` §5.1, first paragraph). Beta testing
surfaced two drifts: the emitted document carries a top-level ``chapters`` array
and a ``[drafting.critic].convergence_target`` field, neither of which the
reference described. Roadmap task 2.1.8 reconciles the reference and adds this
guard so the reference cannot silently fall out of sync with ``init`` again.

The guard derives the required leaf-name and table-header sets from the
*serialised* shape of the ``init`` document
(``tomlkit.dumps(build_initial_document(...))``), not from a type-based walk of
the in-memory document. The serialised dump is exactly the textual shape the
documented fence must mirror, so requiring a documented line for each emitted
line is drift-correct by construction (Decision Log D5). Two emitted-vs-fence
shape mismatches fall out automatically and correctly:

* ``gates`` is a parent-only table carrying no scalar leaf, so ``tomlkit.dumps``
  emits no bare ``[gates]`` line — only ``[gates.knitting]``/``[gates.final]``
  (design line 604). Deriving the header net from the dump excludes ``gates``
  (and any future parent-only table) with no special-case.
* the empty ``chapters`` array serialises as the bare leaf line ``chapters =
  []``, but the reference documents the *populated* manifest as a
  ``[[chapters]]`` block. ``chapters`` is therefore the one emitted leaf the
  guard excludes from the required-leaf set (Decision Log D6); its sub-fields
  are checked separately against :class:`ChapterEntry`.

The guard reads the reference through the shared ``read_repo_text`` fixture
(``tests/conftest.py``; developers-guide "Shared test scaffolding") and asserts
each emitted leaf name and table header appears in the extracted ``toml`` fence
as the corresponding TOML syntax (a ``name =`` line, a ``[header]`` line). It
does not parse the fence as TOML, because the ``by_chapter`` line carries a
literal ``...`` placeholder that is intentionally invalid TOML (Decision Log
D3).
"""

from __future__ import annotations

import dataclasses
import re
import typing as typ

import pytest
import tomlkit

from novel_ralph_skill.state import ChapterEntry, build_initial_document

if typ.TYPE_CHECKING:
    from conftest import RepoTextReader

_STATE_LAYOUT_PARTS = ("skill", "novel-ralph", "references", "state-layout.md")

# Design §5.1 is the authority the failure messages cite, so a drift failure
# tells the author exactly which clause to consult.
_DESIGN_REF = "design §5.1 (docs/novel-ralph-harness-design.md)"

# A representative ``init`` document. The argument values are inert for the
# emitted *shape*: the guard checks key names and table headers, never values.
_SAMPLE_DOCUMENT = build_initial_document(
    title="T",
    slug="s",
    target_word_count=80000,
    created_at="2026-01-01T00:00:00Z",
)
_SAMPLE_DUMP = tomlkit.dumps(_SAMPLE_DOCUMENT)

# A ``[header]`` or ``[[header]]`` line: the dotted header captured for the
# header net. ``\s*$`` rejects a line carrying anything after the bracket.
_HEADER_LINE_RE = re.compile(r"^\[\[?(?P<header>[^\[\]]+)\]\]?\s*$")

# A ``key = …`` assignment at the start of a (dedented) line: the leaf name
# captured for the leaf net. A TOML bare key is letters, digits, underscores,
# and hyphens; quoted keys do not occur in the ``init`` dump.
_LEAF_LINE_RE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+)\s*=")

# The single emitted leaf excluded from the required-leaf set: the empty
# ``chapters`` array serialises as ``chapters = []`` but is documented as the
# populated ``[[chapters]]`` manifest block, not a ``chapters =`` scalar
# (Decision Log D6). ``test_chapters_manifest_is_documented`` checks it instead.
_CHAPTERS_LEAF_EXCEPTION = "chapters"


def _emitted_table_headers(dump: str) -> tuple[str, ...]:
    """Return the distinct ``[header]``/``[[header]]`` lines the dump emits.

    Parameters
    ----------
    dump : str
        The serialised ``init`` document.

    Returns
    -------
    tuple[str, ...]
        The dotted header names in first-appearance order. Parent-only tables
        (``gates``) emit no bare header line and so do not appear (Decision
        Log D5).
    """
    headers: dict[str, None] = {}
    for line in dump.splitlines():
        match = _HEADER_LINE_RE.match(line.strip())
        if match is not None:
            headers.setdefault(match.group("header"), None)
    return tuple(headers)


def _emitted_leaf_names(document: tomlkit.TOMLDocument, dump: str) -> tuple[str, ...]:
    """Return the required leaf names the dump emits, less the ``chapters`` leaf.

    The leaf net is the set of ``key =`` assignment lines the dump emits, plus
    the inner keys of the ``last_finding_counts`` inline table (which serialise
    on one physical line and so are not their own ``key =`` lines). The single
    name ``chapters`` is removed before returning (Decision Log D6).

    Parameters
    ----------
    document : tomlkit.TOMLDocument
        The in-memory ``init`` document, read for the inline-table inner keys.
    dump : str
        The serialised ``init`` document, the source of the ``key =`` lines.

    Returns
    -------
    tuple[str, ...]
        The required leaf names in first-appearance order.
    """
    names: dict[str, None] = {}
    for line in dump.splitlines():
        match = _LEAF_LINE_RE.match(line.strip())
        if match is not None:
            names.setdefault(match.group("key"), None)
    # ``last_finding_counts`` serialises inline, so its inner names do not appear
    # as their own ``key =`` lines; read them from the in-memory inline table.
    inline = document["drafting"]["critic"]["last_finding_counts"]  # type: ignore[index]
    for key in inline.keys():  # noqa: SIM118 - tomlkit item, not a plain dict
        names.setdefault(key, None)
    names.pop(_CHAPTERS_LEAF_EXCEPTION, None)
    return tuple(names)


def _chapter_manifest_fields() -> tuple[str, ...]:
    """Return the chapter-manifest field names from :class:`ChapterEntry`.

    ``init`` emits an empty ``chapters`` array, so the manifest sub-fields live
    only in the schema, not in the emitted document (Decision Log D4). Deriving
    them from the dataclass means a future ``ChapterEntry`` field must be
    documented too.

    Returns
    -------
    tuple[str, ...]
        ``("number", "slug", "title", "target_words")``.
    """
    return tuple(field.name for field in dataclasses.fields(ChapterEntry))


def _extract_schema_fence(reference: str) -> str:
    """Return the body of the ``toml`` fence under ``## state.toml schema``.

    Parameters
    ----------
    reference : str
        The full ``state-layout.md`` text.

    Returns
    -------
    str
        The text between the opening ```` ```toml ```` fence and its closing
        fence in the ``## state.toml schema`` section.

    Raises
    ------
    AssertionError
        If the section or its ``toml`` fence cannot be located.
    """
    section = re.search(
        r"^## state\.toml schema\b(?P<body>.*?)^## ",
        reference,
        re.DOTALL | re.MULTILINE,
    )
    if section is None:
        msg = "state-layout.md must carry a '## state.toml schema' section"
        raise AssertionError(msg)
    fence = re.search(
        r"^```toml\n(?P<fence>.*?)^```",
        section.group("body"),
        re.DOTALL | re.MULTILINE,
    )
    if fence is None:
        msg = "the '## state.toml schema' section must carry a ```toml fence"
        raise AssertionError(msg)
    return fence.group("fence")


def _chapters_block(fence: str) -> str:
    """Return the ``[[chapters]]`` sub-block of the extracted fence.

    The sub-block runs from the ``[[chapters]]`` header line up to (but not
    including) the next table header line or the end of the fence, whichever
    comes first. Checking the manifest fields against this sub-block — rather
    than the whole fence — ensures the shared ``slug``/``title`` names (also
    under ``[novel]``) are genuinely exercised inside the manifest example
    (review round 2 blocking point B-R2.2).

    Parameters
    ----------
    fence : str
        The extracted ``toml`` fence body.

    Returns
    -------
    str
        The ``[[chapters]]`` sub-block, or the empty string when no
        ``[[chapters]]`` header is present.
    """
    lines = fence.splitlines()
    block: list[str] = []
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[[chapters]]":
            in_block = True
            block.append(line)
            continue
        if in_block and _HEADER_LINE_RE.match(stripped) is not None:
            break
        if in_block:
            block.append(line)
    return "\n".join(block)


def _leaf_is_documented(name: str, fence: str) -> bool:
    """Return whether ``name`` appears as a ``name =`` line in ``fence``.

    Parameters
    ----------
    name : str
        The leaf key to find.
    fence : str
        The text to search (the whole fence or a ``[[chapters]]`` sub-block).

    Returns
    -------
    bool
        ``True`` when a ``name`` followed by optional whitespace and ``=``
        appears at the start of a (stripped) line in ``fence``.
    """
    pattern = re.compile(rf"^{re.escape(name)}\s*=", re.MULTILINE)
    return any(pattern.match(line.strip()) is not None for line in fence.splitlines())


def _header_is_documented(header: str, fence: str) -> bool:
    """Return whether ``header`` appears as a ``[header]``/``[[header]]`` line.

    Parameters
    ----------
    header : str
        The dotted table header to find.
    fence : str
        The extracted ``toml`` fence body.

    Returns
    -------
    bool
        ``True`` when a ``[header]`` or ``[[header]]`` line appears in ``fence``.
    """
    for line in fence.splitlines():
        match = _HEADER_LINE_RE.match(line.strip())
        if match is not None and match.group("header") == header:
            return True
    return False


_EMITTED_TABLE_HEADERS = _emitted_table_headers(_SAMPLE_DUMP)
_EMITTED_LEAF_NAMES = _emitted_leaf_names(_SAMPLE_DOCUMENT, _SAMPLE_DUMP)


class TestEmittedSchemaIsDocumented:
    """Pin that every leaf and table header ``init`` emits is documented."""

    def test_convergence_target_is_documented(
        self,
        read_repo_text: RepoTextReader,
    ) -> None:
        """The ``convergence_target`` leaf is documented in the schema fence.

        A named regression pin for one of the two beta-test drifts: the field
        the emitter sets in ``_drafting_table``. It overlaps the parametrized
        leaf net deliberately so the headline drift carries its own test.
        """
        fence = _extract_schema_fence(read_repo_text(*_STATE_LAYOUT_PARTS))
        assert _leaf_is_documented("convergence_target", fence), (
            "[drafting.critic].convergence_target is emitted by novel-state init "
            f"but is not documented in the state.toml schema fence ({_DESIGN_REF})"
        )

    def test_chapters_manifest_is_documented(
        self,
        read_repo_text: RepoTextReader,
    ) -> None:
        """The ``[[chapters]]`` manifest and its four fields are documented.

        The fields come from :class:`ChapterEntry`, not the emitted (empty)
        array (Decision Log D4). They are checked against the ``[[chapters]]``
        sub-block, not the whole fence, so the shared ``slug``/``title`` names
        must appear inside the manifest example (review round 2 B-R2.2).
        """
        fence = _extract_schema_fence(read_repo_text(*_STATE_LAYOUT_PARTS))
        assert _header_is_documented("chapters", fence), (
            "the chapter manifest is emitted by novel-state init but no "
            f"[[chapters]] block is documented in the schema fence ({_DESIGN_REF})"
        )
        block = _chapters_block(fence)
        for field in _chapter_manifest_fields():
            assert _leaf_is_documented(field, block), (
                f"the [[chapters]] manifest field {field!r} (ChapterEntry) is "
                f"not documented inside the [[chapters]] example ({_DESIGN_REF})"
            )

    @pytest.mark.parametrize("header", _EMITTED_TABLE_HEADERS)
    def test_every_emitted_table_header_is_documented(
        self,
        header: str,
        read_repo_text: RepoTextReader,
    ) -> None:
        """Every table header ``init`` emits appears in the schema fence.

        Parametrized over the serialised dump's distinct header lines, so a new
        table added to the emitter without being documented fails here. There is
        no ``[gates]`` row (parent-only table, no bare header emitted — D5) and
        no ``[chapters]`` row (the empty array emits a leaf, not a header — D6).
        """
        fence = _extract_schema_fence(read_repo_text(*_STATE_LAYOUT_PARTS))
        assert _header_is_documented(header, fence), (
            f"table [{header}] is emitted by novel-state init but is not "
            f"documented in the state.toml schema fence ({_DESIGN_REF})"
        )

    @pytest.mark.parametrize("leaf", _EMITTED_LEAF_NAMES)
    def test_every_emitted_leaf_is_documented(
        self,
        leaf: str,
        read_repo_text: RepoTextReader,
    ) -> None:
        """Every leaf ``init`` emits appears in the schema fence.

        The comprehensive drift net (review round 1 B1): a new leaf under any
        table added to the emitter without being documented fails here. The
        single name ``chapters`` is excluded (D6) and checked as the manifest
        by ``test_chapters_manifest_is_documented`` instead.
        """
        fence = _extract_schema_fence(read_repo_text(*_STATE_LAYOUT_PARTS))
        assert _leaf_is_documented(leaf, fence), (
            f"leaf {leaf!r} is emitted by novel-state init but is not documented "
            f"in the state.toml schema fence ({_DESIGN_REF})"
        )
