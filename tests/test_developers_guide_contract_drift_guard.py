"""Pin the ``docs/developers-guide.md`` command-contract restatement to code.

Roadmap task 6.3.9 closes the *last* unguarded copy of the shared interface
contract. The developer-facing guide restates the disambiguated exit-code table
("### Disambiguated exit codes") and the six-field JSON envelope field set
("### The shared JSON envelope"); this is the one restatement copy no test
pinned. A change to the ``ExitCode`` enum, the ``Envelope`` field set, or
``ENVELOPE_SCHEMA_VERSION`` that is not kept in lockstep would silently stale
the developer-facing copy.

This module is a docs-level drift-guard following the repository's established
prose-guard pattern (``tests/test_skill_contract_drift_guard.py``, roadmap
6.3.7): it reads ``docs/developers-guide.md`` in process through the shared
``read_repo_text`` fixture (``tests/conftest.py``) — no subprocess. It *does*
import the contract module's pure data (``ExitCode``, ``Envelope`` fields,
``ENVELOPE_SCHEMA_VERSION``); that import is the load-bearing coupling that ties
the guide's restatement to the code source the roadmap names, exactly as
``tests/test_contract_envelope_snapshots.py`` already imports the contract
directly. The markdown parsing lives in the pure sibling module
``tests/_skill_contract_scanner.py`` so both files stay under the 400-line cap.

Two structural divergences from the SKILL guard are pinned with verified
evidence (ExecPlan Decision Log):

* **Two-column exit-code table.** The guide's exit-code table has only two
  columns (Code, Meaning), narrower than the SKILL (3), ADR-003 (3), and design
  §3.2 (4) copies. :func:`extract_exit_code_meanings` is column-count tolerant
  (it reads columns 0 and 1 only), so the two-column table parses unchanged. The
  guard compares the integer code set exactly but the Meaning cell by per-code
  *keyword* presence, never by exact string (the guide's Meaning wording differs
  from the other copies), and ignores every column after the Meaning column.
* **Fence-free inline envelope field-list.** The guide's envelope section names
  the field set inline as a single brace-list,
  ``{command, schema_version, ok, working_dir, result, messages}``, and carries
  NO fenced ``json`` skeleton. The guard reads it with
  :func:`extract_brace_field_list` rather than :func:`extract_fenced_json`.

One carve-out is deliberate and must not be "tightened" into a false failure
(ExecPlan Decision Log): the guide names ``schema_version`` only as a *field
name* in the brace-list, NOT as a literal value. The guide carries no
``schema_version: 1`` literal in this section (the SKILL/design fenced skeletons
do; the guide does not). The guard pins ``schema_version`` as a field name in
contract position; the field-set/order coupling to ``Envelope`` (which includes
``schema_version``) plus the import of ``ENVELOPE_SCHEMA_VERSION`` is the
load-bearing tie. A future reader must not add a non-existent value assertion.
"""

from __future__ import annotations

import dataclasses
import typing as typ

import pytest
from _skill_contract_scanner import (
    extract_brace_field_list,
    extract_exit_code_meanings,
    parse_markdown_table,
    slice_doc_region,
)

from novel_ralph_skill.contract.envelope import ENVELOPE_SCHEMA_VERSION, Envelope
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from conftest import RepoTextReader

# ``ENVELOPE_SCHEMA_VERSION`` is imported to tie the guard to the schema-version
# constant via the field-set coupling (see the module docstring carve-out); the
# guide carries no literal value to compare, so it is referenced here as the
# documented anchor rather than asserted against a parsed literal.
_SCHEMA_VERSION_CONSTANT = ENVELOPE_SCHEMA_VERSION

_GUIDE_PARTS = ("docs", "developers-guide.md")

# Developers'-guide command-contract anchors. The envelope field-list sits
# between its H3 and the exit-code H3; the exit-code table sits between its H3
# and the next H3 ("### State and on-disk layout"). All anchoring is by heading
# text, never line number.
_ENVELOPE_HEADING = "### The shared JSON envelope"
_ENVELOPE_END = "### Disambiguated exit codes"
_EXIT_HEADING = "### Disambiguated exit codes"
_EXIT_END = "### State and on-disk layout"

_GUIDE_SOURCE = "developers-guide.md"

# Per-code Meaning keywords derived from the ``ExitCode`` enum, NOT copied from
# the guide. Keying off the enum member is the load-bearing coupling: an enum
# rename forces a keyword update here, which then re-pins the guide table. The
# keywords are matched case-insensitively against each Meaning cell. A small
# local copy is kept (rather than importing the 6.3.7 guard's table) to avoid
# coupling two test modules (ExecPlan WI2 Decision Log).
_CODE_KEYWORDS: dict[ExitCode, tuple[str, ...]] = {
    ExitCode.SUCCESS: ("success",),
    ExitCode.BENIGN_NEGATIVE: ("benign",),
    ExitCode.USAGE_ERROR: ("usage",),
    ExitCode.STATE_ERROR: ("state",),
    ExitCode.ACTIONABLE_FINDING: ("actionable", "finding"),
}


@pytest.fixture
def guide_text(read_repo_text: RepoTextReader) -> str:
    """Return the UTF-8 text of ``docs/developers-guide.md``."""
    return read_repo_text(*_GUIDE_PARTS)


@pytest.fixture
def exit_table_region(guide_text: str) -> str:
    """Return the guide exit-code-table region, between its H3 and the next H3."""
    return slice_doc_region(guide_text, _EXIT_HEADING, _EXIT_END, source=_GUIDE_SOURCE)


@pytest.fixture
def envelope_region(guide_text: str) -> str:
    """Return the guide envelope region, between its H3 and the exit-code H3."""
    return slice_doc_region(
        guide_text, _ENVELOPE_HEADING, _ENVELOPE_END, source=_GUIDE_SOURCE
    )


@pytest.fixture
def guide_exit_meanings(exit_table_region: str) -> dict[int, str]:
    """Return the guide exit-code-to-Meaning map from the two-column table."""
    return extract_exit_code_meanings(parse_markdown_table(exit_table_region))


@pytest.fixture
def guide_envelope_fields(envelope_region: str) -> list[str]:
    """Return the ordered envelope field names from the inline brace-list."""
    return extract_brace_field_list(envelope_region, source=_GUIDE_SOURCE)


def _meaning_has_keyword(meaning: str, keywords: tuple[str, ...]) -> bool:
    """Return whether any of ``keywords`` appears in ``meaning`` (case-insensitive)."""
    lowered = meaning.lower()
    return any(keyword in lowered for keyword in keywords)


def _envelope_field_order() -> list[str]:
    """Return the contract envelope field names in declaration order."""
    return [field.name for field in dataclasses.fields(Envelope)]


class TestDevelopersGuideExitCodeTableDriftGuard:
    """Pin the guide exit-code table to the ``ExitCode`` enum."""

    def test_guide_exit_codes_cover_exactly_the_enum(
        self, guide_exit_meanings: dict[int, str]
    ) -> None:
        """The guide table's code set equals the ``ExitCode`` value set.

        Adding or removing an ``ExitCode`` member without updating the guide
        table — or vice versa — fails here.
        """
        assert set(guide_exit_meanings) == {code.value for code in ExitCode}

    def test_guide_exit_code_meanings_match_keywords(
        self, guide_exit_meanings: dict[int, str]
    ) -> None:
        """Each guide Meaning cell carries its per-code enum keyword.

        Keywords are pinned, not whole sentences, so benign re-wording of the
        Meaning cell does not churn the guard (ExecPlan Risks: brittleness).
        """
        for code, keywords in _CODE_KEYWORDS.items():
            meaning = guide_exit_meanings[code.value]
            assert _meaning_has_keyword(meaning, keywords), (
                f"guide Meaning for code {code.value} ({meaning!r}) "
                f"lacks any of {keywords!r}"
            )


class TestDevelopersGuideEnvelopeFieldListDriftGuard:
    """Pin the guide envelope field-list to the ``Envelope`` field set/order."""

    def test_guide_envelope_fields_match_dataclass(
        self, guide_envelope_fields: list[str]
    ) -> None:
        """The guide field-list order equals the ``Envelope`` field order.

        Pins the field set AND order to the code: ``render_machine`` builds the
        JSON in this exact order, so a field added, dropped, renamed, or
        reordered in the dataclass without updating the brace-list — or vice
        versa — fails here.
        """
        assert guide_envelope_fields == _envelope_field_order()

    def test_guide_envelope_names_schema_version_field(
        self, guide_envelope_fields: list[str]
    ) -> None:
        """The guide field-list names ``schema_version`` as a field.

        Per the Decision-Log carve-out, this pins ``schema_version`` as a *field
        name in contract position*, NOT as a literal value: the guide carries no
        ``schema_version: 1`` literal in this section. The import of
        ``ENVELOPE_SCHEMA_VERSION`` (referenced as ``_SCHEMA_VERSION_CONSTANT``)
        ties the guard to the constant through the field-set coupling; a future
        reader must not "tighten" this into a non-existent value assertion.
        """
        assert _SCHEMA_VERSION_CONSTANT == ENVELOPE_SCHEMA_VERSION
        assert "schema_version" in guide_envelope_fields


class TestDevelopersGuideContractGuardNonVacuous:
    """Prove the sliced regions are non-empty, so no guard passes vacuously."""

    def test_regions_are_non_empty(
        self,
        exit_table_region: str,
        envelope_region: str,
        guide_envelope_fields: list[str],
    ) -> None:
        """Each sliced region still carries its expected marker.

        A renamed heading or a removed field-list would yield a region whose
        markers vanish; this asserts the guide exit-table region keeps its
        ``| 0`` code row, the envelope region keeps ``schema_version``, and the
        extracted field-list carries ``working_dir`` and exactly six fields, so a
        future heading rename or a second stray brace-list cannot silently neuter
        the drift guards above. The ``| 0`` marker tolerates the table's cell
        padding (``| 0    |``).
        """
        assert "| 0" in exit_table_region
        assert "schema_version" in envelope_region
        assert "working_dir" in guide_envelope_fields
        assert len(guide_envelope_fields) == len(_envelope_field_order())


class TestDevelopersGuideContractScanner:
    """Unit-test the pure scanner over planted in-string fixtures.

    These pin the guide-specific parsing shapes: a *two-column* exit-code table
    (the column-count-tolerant path) and the fence-free inline brace-list
    (:func:`extract_brace_field_list`).
    """

    _TWO_COLUMN_TABLE = (
        "| Code | Meaning |\n"
        "| ---- | ------- |\n"
        "| 0    | Success here |\n"
        "| 1    | Benign negative |\n"
    )

    def test_parse_two_column_table_keeps_both_cells(self) -> None:
        """A two-column table parses to ``(code, meaning)`` pairs."""
        rows = parse_markdown_table(self._TWO_COLUMN_TABLE)
        assert rows[0] == ("Code", "Meaning")
        assert ("0", "Success here") in rows

    def test_extract_meanings_reads_two_column_table(self) -> None:
        """The column-count-tolerant extractor reads the guide's table shape."""
        meanings = extract_exit_code_meanings(
            parse_markdown_table(self._TWO_COLUMN_TABLE)
        )
        assert meanings == {0: "Success here", 1: "Benign negative"}

    def test_extract_brace_field_list_returns_ordered_fields(self) -> None:
        """The first brace-list is split into ordered, stripped field names."""
        region = "prose\n`{a, b, c}` more prose\n"
        assert extract_brace_field_list(region, source="planted") == ["a", "b", "c"]

    def test_extract_brace_field_list_strips_backticks(self) -> None:
        """Backtick-quoted field names are stripped of their backticks."""
        region = "the field set is {`x`, `y`} in order\n"
        assert extract_brace_field_list(region, source="planted") == ["x", "y"]

    def test_extract_brace_field_list_takes_first_list(self) -> None:
        """With two brace-lists, the FIRST is returned (region-narrowing contract)."""
        region = "{first, set} then later {second, shorter}\n"
        assert extract_brace_field_list(region, source="planted") == ["first", "set"]

    def test_extract_brace_field_list_loud_on_missing_list(self) -> None:
        """A region with no brace-list raises naming the source, not silently empty."""
        with pytest.raises(ValueError, match="no brace-list found in planted"):
            extract_brace_field_list("prose with no braces at all\n", source="planted")
