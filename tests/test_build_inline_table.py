"""Pin :func:`build_inline_table`, the single inline-table builder (task 7.2.1).

These suites guard the contract the five former hand-copied builders relied on
(``recount``, ``init``, ``set-chapters``'s two sites, and the corpus builder):
an :class:`~tomlkit.items.InlineTable` is returned, keys serialise in insertion
order (the load-bearing claim for ``recount``'s byte-for-byte determinism),
mixed-type values survive, the source mapping is not aliased, and the empty case
dumps an empty inline table. They live in their own module so neither this file
nor ``tests/test_state_document.py`` breaches the 400-line cap (AGENTS.md).
"""

from __future__ import annotations

import typing as typ

import tomlkit
import tomlkit.items
from hypothesis import given, settings
from hypothesis import strategies as st

from novel_ralph_skill.state.document import build_inline_table

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def _dump_inline(pairs: cabc.Mapping[str, object]) -> str:
    """Return the dumped one-line form of ``build_inline_table(pairs)``.

    Embeds the inline table under a stable key in a document and serialises it,
    so a test can assert the exact ``key = {…}`` line the helper produces.
    """
    document = tomlkit.document()
    document["x"] = build_inline_table(pairs)
    return tomlkit.dumps(document).strip()


class TestBuildInlineTable:
    """Pin the example-based contract of :func:`build_inline_table`."""

    def test_returns_inline_table(self) -> None:
        """The return value is a ``tomlkit`` inline table, not a block table."""
        result = build_inline_table({"a": 1})
        assert isinstance(result, tomlkit.items.InlineTable), (
            "build_inline_table must return an InlineTable, not a block table"
        )

    def test_preserves_insertion_order(self) -> None:
        """Keys dump in insertion order, not sorted — ``recount``'s determinism."""
        dumped = _dump_inline({"b": 2, "a": 1})
        assert dumped == "x = {b = 2, a = 1}", (
            f"keys must dump in insertion order, not sorted; got {dumped!r}"
        )

    def test_preserves_mixed_type_values(self) -> None:
        """Mixed ``int``/``str`` values survive in order (the chapter-array case)."""
        dumped = _dump_inline({
            "number": 1,
            "slug": "a",
            "title": "A",
            "target_words": 10,
        })
        assert (
            dumped == 'x = {number = 1, slug = "a", title = "A", target_words = 10}'
        ), f"mixed int/str values must survive in order; got {dumped!r}"

    def test_does_not_alias_source_mapping(self) -> None:
        """Mutating ``pairs`` after the call leaves the returned table unchanged."""
        source: dict[str, object] = {"a": 1}
        table = build_inline_table(source)
        source["a"] = 999
        source["b"] = 2
        document = tomlkit.document()
        document["x"] = table
        dumped = tomlkit.dumps(document).strip()
        assert dumped == "x = {a = 1}", (
            f"the table must not alias the source mapping; got {dumped!r}"
        )

    def test_empty_mapping_dumps_empty_inline_table(self) -> None:
        """``build_inline_table({})`` dumps an empty inline table (the init case)."""
        dumped = _dump_inline({})
        assert dumped == "x = {}", (
            f"an empty mapping must dump an empty inline table; got {dumped!r}"
        )

    @settings(max_examples=50)
    @given(
        st.lists(
            # Bare-word TOML keys keep the dumped form ``key = value`` so a key
            # can be re-parsed from the dump; ``unique`` stops duplicate keys
            # collapsing and masking a reorder.
            st.from_regex(r"[a-z][a-z0-9_]{0,7}", fullmatch=True),
            unique=True,
        )
    )
    def test_preserves_arbitrary_order_in_dump(self, keys: list[str]) -> None:
        """The *dumped* key order equals the source's iteration order, for any dict.

        A genuine range-of-inputs invariant (``python-verification``):
        ``recount``'s byte-for-byte determinism rests on the helper never
        reordering keys, so a property over arbitrary insertion orders pins what
        the examples cannot. The assertion reads the order back out of the
        serialised dump (not the in-memory table) so it pins the on-disk bytes.
        """
        source = {key: index for index, key in enumerate(keys)}
        dumped = _dump_inline(source)
        # Recover the dumped key order from ``x = {k0 = 0, k1 = 1, …}`` (or the
        # empty ``x = {}``) by splitting each ``key = value`` pair on its first
        # ``=``.
        body = dumped.removeprefix("x = {").removesuffix("}").strip()
        dumped_keys = (
            [pair.split("=", 1)[0].strip() for pair in body.split(",")] if body else []
        )
        assert dumped_keys == keys, (
            f"the dumped key order must equal the source's order; got {dumped_keys}"
        )
