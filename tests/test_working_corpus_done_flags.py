"""Self-tests for the coherent ``done.flag`` permutation corpus (roadmap 1.3.2).

These exercise the Work item 4 ``done.flag`` permutations: coherent
multi-chapter trees differing only in which chapters carry ``done.flag``. The
corpus is consumed by pytest fixture parameter name; this module performs no
runtime value import of corpus data and names a spec *type* only under
``if TYPE_CHECKING:`` via the sanctioned ``from conftest import …`` carve-out.
"""

from __future__ import annotations

import typing as typ

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec


def _flagged_chapter_numbers(working: Path) -> list[int]:
    """Return the sorted chapter numbers carrying ``done.flag`` under ``working``."""
    manuscript = working / "manuscript"
    return sorted(
        int(flag.parent.name.removeprefix("chapter-"))
        for flag in manuscript.glob("chapter-*/done.flag")
    )


class TestDoneFlagPermutations:
    """Exercise the coherent ``done.flag`` permutation trees (Work item 4)."""

    # The expected one-based flagged-chapter set per permutation, named locally
    # (derived from the permutation-name semantics, not imported from the corpus).
    _EXPECTED: typ.ClassVar[dict[str, list[int]]] = {
        "none-flagged": [],
        "all-flagged": [1, 2, 3],
        "leading-prefix-flagged": [1, 2],
        "non-contiguous-subset-flagged": [1, 3],
    }

    def test_each_permutation_flags_named_chapters(
        self,
        done_flag_permutation_names: tuple[str, ...],
        done_flag_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
        check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
    ) -> None:
        """Each permutation flags exactly its chapters and stays coherent."""
        assert set(done_flag_permutation_names) == set(self._EXPECTED), (
            "the permutation set drifted from the test's expected patterns"
        )
        for name in done_flag_permutation_names:
            spec, working = done_flag_tree(name)
            assert _flagged_chapter_numbers(working) == self._EXPECTED[name], name
            assert check_corpus(spec, working) == (), (
                f"permutation {name!r} must stay coherent"
            )

    def test_non_contiguous_subset_has_gap(
        self,
        done_flag_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path]],
    ) -> None:
        """The non-contiguous permutation flags a chapter after an unflagged one."""
        _, working = done_flag_tree("non-contiguous-subset-flagged")
        flagged = set(_flagged_chapter_numbers(working))
        has_gap = any(
            any(earlier not in flagged for earlier in range(1, later))
            for later in flagged
        )
        assert has_gap, "a flagged chapter must follow an unflagged one"
