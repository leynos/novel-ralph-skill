"""Pin :func:`build_chapter_array`, the single ``[[chapters]]`` array builder.

This suite guards the array-of-inline-tables skeleton that ``set-chapters``
(``_chapter_array``) and the working-corpus reference builder (``_chapters_array``)
both route through (roadmap task 7.2.1.1, the deferred Decision D-ARRAY-FOLLOWUP):
a multiline :class:`~tomlkit.items.Array` is returned, each record dumps as one
inline table per line in the on-disk schema key order (``number``, ``slug``,
``title``, ``target_words``), the caller's record order is preserved unchanged,
and the empty case dumps an empty array. It mirrors
``tests/test_build_inline_table.py`` and lives in its own module so neither that
file nor ``tests/test_state_document.py`` breaches the 400-line cap (AGENTS.md).
"""

from __future__ import annotations

import tomlkit
import tomlkit.items
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state.document import ChapterRecord, build_chapter_array


def _dump_chapters(records: list[ChapterRecord]) -> str:
    """Return the dumped ``[[chapters]]`` form of ``build_chapter_array(records)``.

    Embeds the array under the ``chapters`` key in a document and serialises it,
    so a test can assert the exact on-disk bytes the helper produces.
    """
    document = tomlkit.document()
    document["chapters"] = build_chapter_array(records)
    return tomlkit.dumps(document).strip()


_ONE = ChapterRecord(number=1, slug="opening", title="Opening", target_words=2500)
_TWO = ChapterRecord(number=2, slug="rising", title="Rising", target_words=3000)


class TestBuildChapterArray:
    """Pin the example-based contract of :func:`build_chapter_array`."""

    def test_returns_multiline_array(self) -> None:
        """The return value is a ``tomlkit`` array marked multiline."""
        result = build_chapter_array([_ONE])
        assert isinstance(result, tomlkit.items.Array), (
            "build_chapter_array must return a tomlkit Array"
        )

    def test_preserves_schema_key_order(self) -> None:
        """Each entry dumps its four keys in on-disk schema order, one per line."""
        dumped = _dump_chapters([_ONE])
        assert dumped == (
            "chapters = [\n"
            '    {number = 1, slug = "opening", title = "Opening", '
            "target_words = 2500},\n"
            "]"
        ), f"a single entry must dump in schema key order; got {dumped!r}"

    def test_preserves_record_order(self) -> None:
        """The array keeps the caller's record order; it does not re-sort."""
        dumped = _dump_chapters([_TWO, _ONE])
        numbers = [
            line.split("number = ", 1)[1].split(",", 1)[0]
            for line in dumped.splitlines()
            if "number = " in line
        ]
        assert numbers == ["2", "1"], (
            f"the array must preserve the caller's record order; got {numbers}"
        )

    def test_empty_records_dump_empty_array(self) -> None:
        """``build_chapter_array([])`` dumps an empty ``chapters`` array."""
        dumped = _dump_chapters([])
        assert dumped == "chapters = []", (
            f"an empty record sequence must dump an empty array; got {dumped!r}"
        )

    @settings(max_examples=50)
    @given(
        st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=9999),
                st.from_regex(r"[a-z][a-z0-9-]{0,15}", fullmatch=True),
                st.text(
                    alphabet=st.characters(min_codepoint=65, max_codepoint=90),
                    min_size=1,
                    max_size=8,
                ),
                st.integers(min_value=0, max_value=100000),
            ),
        )
    )
    def test_dumped_number_order_equals_record_order(
        self, raw: list[tuple[int, str, str, int]]
    ) -> None:
        """The dumped ``number`` order equals the record order, for any sequence.

        A range-of-inputs invariant (``python-verification``): both call sites
        rely on the helper emitting entries in the order handed to it, so a
        property over arbitrary record sequences pins what the examples cannot.
        The order is read back out of the serialised dump, so it pins the
        on-disk bytes rather than the in-memory array.
        """
        records = [
            ChapterRecord(number=n, slug=s, title=t, target_words=w)
            for n, s, t, w in raw
        ]
        dumped = _dump_chapters(records)
        dumped_numbers = [
            int(line.split("number = ", 1)[1].split(",", 1)[0])
            for line in dumped.splitlines()
            if "number = " in line
        ]
        assert dumped_numbers == [record.number for record in records], (
            f"the dumped number order must equal the record order; got {dumped_numbers}"
        )
