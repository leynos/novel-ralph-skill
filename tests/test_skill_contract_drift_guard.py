"""Pin the ``SKILL.md`` command-contract restatement to the code.

Roadmap task 6.3.7 closes the last unguarded copy of the shared interface
contract. The agent-facing skill (``skill/novel-ralph/SKILL.md``) restates the
disambiguated exit-code table (design §3.2) and the six-field JSON envelope
skeleton (design §3.1). A change to the ``ExitCode`` enum, the ``Envelope``
field set, or ``ENVELOPE_SCHEMA_VERSION`` would silently stale the table the
dogfooding agent reads.

This module is a docs-level drift-guard following the repository's established
prose-guard pattern (``tests/test_skill_deflation_guard.py``): it reads
``SKILL.md`` in process through the shared ``read_repo_text`` fixture
(``tests/conftest.py``) — no subprocess. It imports the contract module's pure
data (``ExitCode``, ``Envelope`` fields, ``ENVELOPE_SCHEMA_VERSION``); that
import is the load-bearing coupling tying the SKILL restatement to the code
source the roadmap names. The markdown parsing lives in the pure sibling module
``tests/_skill_contract_scanner.py`` so both files stay under the 400-line cap.

Two carve-outs are deliberate and must not be "tightened" into false failures
(ExecPlan Decision Log):

* **Meaning column only, by keyword.** The three exit-code tables differ in
  column count and in Meaning *wording* (SKILL "Usage error; the invocation is
  wrong" vs ADR/design "Usage error"). The guard compares the integer code set
  exactly but the Meaning cell by per-code *keyword* presence, never by exact
  string, ignoring every column after the Meaning column.
* **``working_dir`` example value is free.** ``SKILL.md`` shows the literal
  token ``"working"`` whereas design §3.1 shows the resolved absolute path
  ``"/home/me/my-novel/working"`` (roadmap §6.3.4). The guard pins the envelope
  field *set and order* and the ``schema_version`` *value* across both
  skeletons, but NOT ``working_dir``'s example value.
"""

from __future__ import annotations

import json
import typing as typ

import pytest
from _skill_contract_scanner import (
    extract_exit_code_meanings,
    extract_fenced_json,
    parse_markdown_table,
    slice_doc_region,
)

from novel_ralph_skill.contract.envelope import (
    ENVELOPE_FIELD_ORDER,
    ENVELOPE_SCHEMA_VERSION,
)
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from conftest import RepoTextReader

_SKILL_PARTS = ("skill", "novel-ralph", "SKILL.md")
_DESIGN_PARTS = ("docs", "novel-ralph-harness-design.md")
_ADR_PARTS = ("docs", "adr-003-shared-interface-contract.md")

# SKILL.md command-contract anchors. The exit-code table sits between its H3 and
# the envelope-schema H3; the envelope region (skeleton plus field bullets) runs
# from the envelope-schema H3 to the next H3. All anchoring is by heading text,
# never line number.
_EXIT_TABLE_HEADING = "### Exit-code table"
_ENVELOPE_HEADING = "### Envelope schema"
_ENVELOPE_END = "### Invocation discipline"

# Design §3.1 "Output modes" carries the six-field envelope skeleton; §3.2 is the
# next H3. The slice excludes the second, five-field ``novel done`` example in §4
# that omits ``working_dir`` (B1).
_DESIGN_ENVELOPE_START = "### 3.1"
_DESIGN_ENVELOPE_END = "### 3.2"

# Cross-document slice anchors. Design §3.2's exit table sits between its
# heading and §3.3; ADR-003 Table 2 sits between the "Adopt Option A" sentence
# and its ``_Table 2:`` caption.
_DESIGN_EXIT_START = "### 3.2"
_DESIGN_EXIT_END = "### 3.3"
_ADR_TABLE_START = "Adopt Option A. The exit-code table is:"
_ADR_TABLE_END = "_Table 2:"

# Per-code Meaning keywords derived from the ``ExitCode`` enum, NOT copied from
# any document. Keying off the enum member is the load-bearing coupling: an enum
# rename forces a keyword update here, which then re-pins all three tables. The
# keywords are matched case-insensitively against each Meaning cell.
_CODE_KEYWORDS: dict[ExitCode, tuple[str, ...]] = {
    ExitCode.SUCCESS: ("success",),
    ExitCode.BENIGN_NEGATIVE: ("benign",),
    ExitCode.USAGE_ERROR: ("usage",),
    ExitCode.STATE_ERROR: ("state",),
    ExitCode.ACTIONABLE_FINDING: ("actionable", "finding"),
}


@pytest.fixture
def skill_text(read_repo_text: RepoTextReader) -> str:
    """Return the UTF-8 text of ``skill/novel-ralph/SKILL.md``."""
    return read_repo_text(*_SKILL_PARTS)


@pytest.fixture
def design_text(read_repo_text: RepoTextReader) -> str:
    """Return the UTF-8 text of ``docs/novel-ralph-harness-design.md``."""
    return read_repo_text(*_DESIGN_PARTS)


@pytest.fixture
def adr_text(read_repo_text: RepoTextReader) -> str:
    """Return the UTF-8 text of ``docs/adr-003-shared-interface-contract.md``."""
    return read_repo_text(*_ADR_PARTS)


@pytest.fixture
def exit_table_region(skill_text: str) -> str:
    """Return the SKILL exit-code-table region, between its H3 and the next H3."""
    return slice_doc_region(
        skill_text, _EXIT_TABLE_HEADING, _ENVELOPE_HEADING, source="SKILL.md"
    )


@pytest.fixture
def design_envelope_region(design_text: str) -> str:
    """Return the design §3.1 region holding the six-field envelope skeleton."""
    return slice_doc_region(
        design_text,
        _DESIGN_ENVELOPE_START,
        _DESIGN_ENVELOPE_END,
        source="novel-ralph-harness-design.md",
    )


@pytest.fixture
def skill_exit_meanings(exit_table_region: str) -> dict[int, str]:
    """Return the SKILL exit-code-to-Meaning map from the exit-code table."""
    return extract_exit_code_meanings(parse_markdown_table(exit_table_region))


@pytest.fixture
def design_exit_meanings(design_text: str) -> dict[int, str]:
    """Return the design §3.2 exit-code-to-Meaning map (four-column table)."""
    region = slice_doc_region(
        design_text,
        _DESIGN_EXIT_START,
        _DESIGN_EXIT_END,
        source="novel-ralph-harness-design.md",
    )
    return extract_exit_code_meanings(parse_markdown_table(region))


@pytest.fixture
def adr_exit_meanings(adr_text: str) -> dict[int, str]:
    """Return the ADR-003 Table 2 exit-code-to-Meaning map."""
    region = slice_doc_region(
        adr_text,
        _ADR_TABLE_START,
        _ADR_TABLE_END,
        source="adr-003-shared-interface-contract.md",
    )
    return extract_exit_code_meanings(parse_markdown_table(region))


@pytest.fixture
def envelope_region(skill_text: str) -> str:
    """Return the SKILL envelope region: the skeleton and the field bullets."""
    return slice_doc_region(
        skill_text, _ENVELOPE_HEADING, _ENVELOPE_END, source="SKILL.md"
    )


@pytest.fixture
def skill_envelope_keys(envelope_region: str) -> list[str]:
    """Return the ordered key list of the SKILL envelope JSON skeleton."""
    body = extract_fenced_json(envelope_region)
    parsed = json.loads(body)
    return list(parsed.keys())


@pytest.fixture
def skill_envelope_schema_version(envelope_region: str) -> object:
    """Return the ``schema_version`` value from the SKILL envelope skeleton."""
    parsed = json.loads(extract_fenced_json(envelope_region))
    return parsed["schema_version"]


@pytest.fixture
def design_envelope_keys(design_envelope_region: str) -> list[str]:
    """Return the ordered key list of the design §3.1 envelope skeleton.

    The design text is narrowed to the §3.1 region *before* the first ``json``
    fence is extracted, so the §4 five-field ``novel done`` example that omits
    ``working_dir`` is never read (B1). The fixture asserts ``working_dir`` is
    present, so a future doc reshuffle that pulls the wrong fence fails loudly
    here rather than silently downstream.
    """
    body = extract_fenced_json(design_envelope_region)
    assert "working_dir" in body, (
        "design §3.1 skeleton lost working_dir; the §3.1 slice may have pulled "
        "the wrong fence (B1)"
    )
    return list(json.loads(body).keys())


def _meaning_has_keyword(meaning: str, keywords: tuple[str, ...]) -> bool:
    """Return whether any of ``keywords`` appears in ``meaning`` (case-insensitive)."""
    lowered = meaning.lower()
    return any(keyword in lowered for keyword in keywords)


def _envelope_field_order() -> list[str]:
    """Return the contract envelope field names in declaration order.

    Reads the canonical
    :data:`novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER` rather than
    re-deriving it from ``dataclasses.fields(Envelope)``, so this guard shares
    the single source of truth with the renderer and the cross-command oracle
    (roadmap 7.1.5).
    """
    return list(ENVELOPE_FIELD_ORDER)


class TestSkillExitCodeTableDriftGuard:
    """Pin the SKILL exit-code table to ``ExitCode`` and the canonical docs."""

    def test_skill_exit_codes_cover_exactly_the_enum(
        self, skill_exit_meanings: dict[int, str]
    ) -> None:
        """The SKILL table's code set equals the ``ExitCode`` value set.

        Adding or removing an ``ExitCode`` member without updating the SKILL
        table — or vice versa — fails here.
        """
        assert set(skill_exit_meanings) == {code.value for code in ExitCode}

    def test_skill_exit_code_meanings_match_keywords(
        self, skill_exit_meanings: dict[int, str]
    ) -> None:
        """Each SKILL Meaning cell carries its per-code enum keyword.

        Keywords are pinned, not whole sentences, so benign re-wording of the
        Meaning cell does not churn the guard (ExecPlan Risks: brittleness).
        """
        for code, keywords in _CODE_KEYWORDS.items():
            meaning = skill_exit_meanings[code.value]
            assert _meaning_has_keyword(meaning, keywords), (
                f"SKILL Meaning for code {code.value} ({meaning!r}) "
                f"lacks any of {keywords!r}"
            )

    def test_skill_exit_table_agrees_with_adr003_and_design(
        self,
        skill_exit_meanings: dict[int, str],
        adr_exit_meanings: dict[int, str],
        design_exit_meanings: dict[int, str],
    ) -> None:
        """SKILL, ADR-003 Table 2, and design §3.2 share each per-code keyword.

        Pins the roadmap "matches ADR-003 Table 2 / design §3.2" clause against
        the canonical documents, by per-code keyword presence (not exact Meaning
        string, which differs across the three tables — B2).
        """
        assert set(adr_exit_meanings) == {code.value for code in ExitCode}
        assert set(design_exit_meanings) == {code.value for code in ExitCode}
        for code, keywords in _CODE_KEYWORDS.items():
            for label, meanings in (
                ("ADR-003 Table 2", adr_exit_meanings),
                ("design §3.2", design_exit_meanings),
                ("SKILL.md", skill_exit_meanings),
            ):
                meaning = meanings[code.value]
                assert _meaning_has_keyword(meaning, keywords), (
                    f"{label} Meaning for code {code.value} ({meaning!r}) "
                    f"lacks any of {keywords!r}"
                )


class TestSkillEnvelopeSkeletonDriftGuard:
    """Pin the SKILL envelope skeleton to ``Envelope`` and the design §3.1 copy."""

    def test_skill_envelope_fields_match_dataclass(
        self, skill_envelope_keys: list[str]
    ) -> None:
        """The SKILL skeleton's key order equals the ``Envelope`` field order.

        Pins the field set AND order to the code: ``render_machine`` builds the
        JSON in this exact order, so a field added, dropped, renamed, or
        reordered in the dataclass without updating the skeleton fails here.
        """
        assert skill_envelope_keys == _envelope_field_order()

    def test_skill_envelope_schema_version_matches_constant(
        self, skill_envelope_schema_version: object
    ) -> None:
        """The SKILL skeleton's ``schema_version`` equals the code constant."""
        assert skill_envelope_schema_version == ENVELOPE_SCHEMA_VERSION

    def test_design_envelope_schema_version_matches_constant(
        self, design_envelope_region: str
    ) -> None:
        """The design §3.1 skeleton's ``schema_version`` equals the constant.

        Without this, a drift in design §3.1 alone (e.g. ``schema_version: 2``)
        would slip past every other guard (6.3.7.1). ADR-003 names the field
        only in prose, with no literal envelope value to pin.
        """
        parsed = json.loads(extract_fenced_json(design_envelope_region))
        assert parsed["schema_version"] == ENVELOPE_SCHEMA_VERSION

    def test_skill_envelope_matches_design_field_order(
        self,
        skill_envelope_keys: list[str],
        design_envelope_keys: list[str],
    ) -> None:
        """The SKILL and design §3.1 skeletons share field set and order.

        Per the Decision-Log carve-out, only the key *order/set* is pinned, NOT
        ``working_dir``'s example value (SKILL's ``"working"`` vs design's
        resolved absolute path). The ``working_dir`` membership assertion guards
        against the design region yielding the working_dir-less §4 example (B1).
        """
        assert "working_dir" in design_envelope_keys
        assert design_envelope_keys == skill_envelope_keys

    def test_skill_envelope_bullets_name_every_field(
        self, envelope_region: str
    ) -> None:
        """Every envelope field is documented as a backtick-quoted bullet.

        A field added to the skeleton without prose, or prose left behind after
        a field removal, fails. Keyword (field-name) presence, not sentence text.
        """
        for name in _envelope_field_order():
            assert f"`{name}`" in envelope_region, (
                f"envelope field {name!r} lacks a documented bullet"
            )


class TestSkillContractGuardNonVacuous:
    """Prove the sliced regions are non-empty, so no guard passes vacuously."""

    def test_regions_are_non_empty(
        self,
        exit_table_region: str,
        envelope_region: str,
        design_envelope_region: str,
    ) -> None:
        """Each sliced region still carries its expected marker.

        A renamed heading or a wrong-fence pull (B1) would yield a region whose
        markers vanish; this asserts the SKILL exit-table region keeps its
        ``| 0`` code row (padding-tolerant), the SKILL envelope region keeps
        ``"schema_version"``, and the design §3.1 region keeps ``"working_dir"``,
        so the drift guards above cannot silently neuter.
        """
        assert "| 0" in exit_table_region
        assert '"schema_version"' in envelope_region
        assert '"working_dir"' in design_envelope_region
