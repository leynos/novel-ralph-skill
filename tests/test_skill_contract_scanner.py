"""Unit-test the pure markdown scanner backing the SKILL drift-guard.

The scanner (``tests/_skill_contract_scanner.py``) is the pure markdown-parsing
sibling of ``tests/test_skill_contract_drift_guard.py``; the two are split so
both files stay under the 400-line cap. These tests pin the scanner directly
over planted in-string fixtures, with no document or contract import, so a
parser regression fails here rather than silently neutering the drift-guards.
"""

from __future__ import annotations

import json

import pytest
from _skill_contract_scanner import (
    extract_exit_code_meanings,
    extract_fenced_json,
    parse_markdown_table,
    slice_doc_region,
)


class TestSkillContractScanner:
    """Unit-test the pure markdown scanner over planted in-string fixtures."""

    _PLANTED_TABLE = (
        "| Code | Meaning | Response | Example |\n"
        "| ---- | ------- | -------- | ------- |\n"
        "| 0    | Success here | proceed | ok |\n"
        "| 1    | Benign negative | loop | nope |\n"
    )

    def test_parse_markdown_table_skips_separator(self) -> None:
        """The dashes-and-colons alignment row is dropped, header is kept."""
        rows = parse_markdown_table(self._PLANTED_TABLE)
        assert rows[0] == ("Code", "Meaning", "Response", "Example")
        assert ("----", "-------", "--------", "-------") not in rows
        assert len(rows) == 3

    def test_parse_markdown_table_tolerates_padding(self) -> None:
        """Padding whitespace inside cells is stripped."""
        rows = parse_markdown_table("|  a  |  b  |\n| --- | --- |\n|  c  |  d  |\n")
        assert rows == [("a", "b"), ("c", "d")]

    def test_extract_meanings_keys_code_to_meaning(self) -> None:
        """Column 0 maps to column 1 only; later columns are discarded."""
        meanings = extract_exit_code_meanings(parse_markdown_table(self._PLANTED_TABLE))
        assert meanings == {0: "Success here", 1: "Benign negative"}

    def test_extract_meanings_skips_non_integer_rows(self) -> None:
        """A row whose first cell is not an integer is skipped, not crashed on."""
        table = (
            "| Code | Meaning |\n"
            "| ---- | ------- |\n"
            "| x    | bogus   |\n"
            "| 3    | State error |\n"
        )
        assert extract_exit_code_meanings(parse_markdown_table(table)) == {
            3: "State error"
        }

    def test_slice_doc_region_loud_on_missing_anchor(self) -> None:
        """A missing anchor raises naming the source, not silently empty."""
        with pytest.raises(ValueError, match="not found in design"):
            slice_doc_region("no anchors here", "### 9.9", "### 9.8", source="design")

    def test_extract_fenced_json_returns_block_body(self) -> None:
        """The fenced JSON body is returned without the fence markers."""
        region = 'prose\n```json\n{"a": 1}\n```\nmore prose\n'
        assert json.loads(extract_fenced_json(region)) == {"a": 1}

    def test_extract_fenced_json_loud_on_missing_fence(self) -> None:
        """A region with no JSON fence raises rather than passing vacuously."""
        with pytest.raises(ValueError, match="no 'json' fenced block"):
            extract_fenced_json("prose with no fence at all\n")

    def test_extract_fenced_json_returns_first_of_two(self) -> None:
        """With two JSON fences, the FIRST is returned (the B1 ordering contract)."""
        region = '```json\n{"first": true}\n```\n```json\n{"second": true}\n```\n'
        assert json.loads(extract_fenced_json(region)) == {"first": True}
