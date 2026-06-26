"""Guard against any direct ``state.toml``-write recipe in the reference.

ADR-002 (``docs/adr-002-toml-round-trip-tomlkit.md``) selects ``tomlkit`` over
``tomli_w`` as the only sanctioned writer, and design §4.1
(``docs/novel-ralph-harness-design.md``) eliminates direct editing of
``state.toml`` in favour of validated ``novel state`` subcommands. The
state-layout skill reference
(``skill/novel-ralph/references/state-layout.md``) once demonstrated state
mutation with a Python heredoc that imported the undeclared ``tomli_w``
dependency and hand-edited ``state.toml`` — a pattern both documents reject.

This guard forbids *any* direct ``state.toml``-write recipe inside an
executable code fence (``python``/``py``/``sh``/``bash``/``shell``/
``console``), not just the historical ``tomli_w`` form. It scans only
executable fences, so it leaves untouched the atomic-write *prose* the design
mandates (write to ``state.toml.new``, fsync, rename — design §3.4 and §5.3,
carried as prose in the reference) and any ``novel state`` invocation example.
Rewriting the reference prose to point at the ``novel state`` commands remains
roadmap task 6.2.3's job; 1.2.8 only hardens the guard.

It reads the reference through the shared ``read_repo_text`` fixture
(``tests/conftest.py``, roadmap 1.2.7) and asserts in process; it does not shell
out, import ``novel_ralph_skill``, or read any other file. The fence-scanner
itself lives in ``tests/_state_layout_scanner.py`` as pure functions over
markdown text (extracted under roadmap addendum 1.2.8.2 to keep this module
under the 400-line cap); this module imports
:func:`find_direct_state_write_recipes` from there and pins the corpus of
planted recipes and verified clean cases against it.
"""

from __future__ import annotations

import typing as typ

import pytest
from _clean_fences import CLEAN_FENCES
from _planted_recipes import PLANTED_RECIPES
from _skill_markdown_inventory import KNOWN_SKILL_MARKDOWN
from _state_layout_scanner import (
    find_direct_state_write_recipes,
    find_direct_state_write_recipes_in_files,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

    from conftest import RepoTextReader

_STATE_LAYOUT_PARTS = ("skill", "novel-ralph", "references", "state-layout.md")

# The hand-maintained tripwire inventory ``KNOWN_SKILL_MARKDOWN`` (and its "must
# not be derived from the glob" rationale) lives in
# ``tests/_skill_markdown_inventory.py`` (roadmap 7.6.3.6: keep this under 400).


@pytest.fixture
def skill_markdown_documents(
    project_root: Path,
    read_repo_text: RepoTextReader,
) -> dict[str, str]:
    """Return ``{repo_relative_posix_path: text}`` for every skill markdown file.

    Discovery globs ``skill/novel-ralph/**/*.md`` under ``project_root`` and reads
    each file through the injected ``read_repo_text`` callable, passing the file's
    parts relative to ``project_root`` so the single sanctioned UTF-8 reader is
    reused rather than duplicated. Building the map in a fixture (not at module
    level) is required because ``read_repo_text`` is itself a fixture and so is
    unavailable at collection time. Keys are repo-relative POSIX paths so a guard
    failure names the offending file unambiguously.
    """
    documents: dict[str, str] = {}
    for path in sorted(project_root.glob("skill/novel-ralph/**/*.md")):
        parts = path.relative_to(project_root).parts
        documents["/".join(parts)] = read_repo_text(*parts)
    return documents


class TestStateLayoutReference:
    """Pin the absence of any direct ``state.toml``-write recipe."""

    def test_reference_has_no_direct_write_recipe(
        self,
        read_repo_text: RepoTextReader,
    ) -> None:
        """The current reference carries no hand-edit recipe."""
        assert not find_direct_state_write_recipes(
            read_repo_text(*_STATE_LAYOUT_PARTS)
        ), (
            "state-layout.md must not carry a copy-pasteable recipe that "
            "writes state.toml outside novel state (design §4.1, ADR-002)"
        )

    def test_no_tomli_w_token(
        self,
        read_repo_text: RepoTextReader,
    ) -> None:
        """The bare ``tomli_w`` token does not appear in the reference.

        A named regression of the 1.2.6 case: pin the specific historical
        substring cheaply alongside the broadened fence scanner.
        """
        assert "tomli_w" not in read_repo_text(*_STATE_LAYOUT_PARTS), (
            "the dead tomli_w snippet must stay removed from "
            "state-layout.md (ADR-002 selects tomlkit; design §4.1 "
            "eliminates direct editing of state.toml)"
        )

    def test_no_tomli_w_import_or_dump(
        self,
        read_repo_text: RepoTextReader,
    ) -> None:
        """Neither the ``import`` nor the ``dump`` call site reappears.

        The deleted heredoc imported the dependency in the comma form
        ``import tomllib, tomli_w, os`` and wrote ``state.toml`` with
        ``tomli_w.dump(...)`` (Finding 1, ``docs/issues/audit-1.2.2.md``
        lines 26-27). Pin both the comma-form import token and the call
        site so a re-introduced snippet fails ``make test``.
        """
        text = read_repo_text(*_STATE_LAYOUT_PARTS)
        assert "tomllib, tomli_w" not in text, (
            "the dead `import tomllib, tomli_w, os` line must stay removed "
            "from state-layout.md"
        )
        assert "tomli_w.dump(" not in text, (
            "the dead `tomli_w.dump(` call must stay removed from state-layout.md"
        )


class TestFindDirectStateWriteRecipes:
    """Exercise the broadened fence scanner against the verified surface."""

    @pytest.mark.parametrize(
        ("case_id", "snippet"),
        list(CLEAN_FENCES.items()),
        ids=list(CLEAN_FENCES),
    )
    def test_clean_fence_not_flagged(self, case_id: str, snippet: str) -> None:
        """Each verified-clean snippet carries no direct ``state.toml`` write.

        The per-rationale clean cases (atomic-write prose, the two
        ``state.toml.new`` temp-file writes, read-only opens, unrelated and
        indented redirects, the ``pycon`` read-only session, the ``novel state``
        example, and the non-executable fence) share a single skeleton, so they
        are folded into this parametrized table; the former per-method docstrings
        survive as the ``CLEAN_FENCES`` entry comments and as the ``case_id``
        ids (roadmap 7.6.3.7).
        """
        assert not find_direct_state_write_recipes(snippet), (
            f"clean case {case_id!r} must not be flagged"
        )

    @pytest.mark.parametrize(
        ("label", "recipe"),
        list(PLANTED_RECIPES.items()),
        ids=list(PLANTED_RECIPES),
    )
    def test_planted_recipe_is_flagged(self, label: str, recipe: str) -> None:
        """Each planted hand-edit recipe form is flagged."""
        messages = find_direct_state_write_recipes(recipe)
        assert messages, f"planted recipe {label!r} should be flagged"


class TestFindDirectStateWriteRecipesInFiles:
    """Exercise the multi-file driver that aggregates per-document findings."""

    def test_clean_documents_return_empty_mapping(self) -> None:
        """Two clean documents aggregate to an empty mapping."""
        documents = {
            "a.md": "```python\ntomllib.load(open('s', 'rb'))\n```\n",
            "b.md": "Just prose naming state.toml outside any fence.\n",
        }
        assert not find_direct_state_write_recipes_in_files(documents)

    def test_recipe_in_one_document_keyed_by_label(self) -> None:
        """One recipe-bearing document yields a one-key mapping under its label.

        The message list equals the single-file
        :func:`find_direct_state_write_recipes` result for that text, pinning
        the no-duplication invariant: the driver is the detector applied per
        file, not a second matcher.
        """
        recipe = PLANTED_RECIPES["raw-open-write"]
        documents = {"dirty.md": recipe, "clean.md": "nothing to see here\n"}
        findings = find_direct_state_write_recipes_in_files(documents)
        assert set(findings) == {"dirty.md"}
        assert findings["dirty.md"] == find_direct_state_write_recipes(recipe)

    def test_recipe_in_several_documents_all_reported(self) -> None:
        """Two recipe-bearing documents both appear; a clean third does not."""
        documents = {
            "first.md": PLANTED_RECIPES["raw-open-write"],
            "second.md": PLANTED_RECIPES["shell-append"],
            "third.md": "clean prose\n",
        }
        findings = find_direct_state_write_recipes_in_files(documents)
        assert set(findings) == {"first.md", "second.md"}

    def test_empty_mapping_returns_empty(self) -> None:
        """The empty-input edge case returns an empty mapping."""
        assert not find_direct_state_write_recipes_in_files({})


class TestSkillReferenceGuard:
    """Guard every executable-carrying skill markdown file, not just one."""

    def test_no_skill_reference_carries_direct_write_recipe(
        self,
        skill_markdown_documents: dict[str, str],
    ) -> None:
        """No skill markdown file carries a direct ``state.toml``-write recipe.

        This is the acceptance-bearing guard. It is fully glob-driven over
        ``skill/novel-ralph/**/*.md`` and carries zero per-file edits: adding a
        new reference needs no change here (roadmap 7.3.3 "single shared scanner,
        with no per-file duplication"). The per-file detector already embeds
        design §4.1 and ADR-002 in each message, so the failure report only joins
        the offending file labels with their message lists; it invents no second
        message format.
        """
        findings = find_direct_state_write_recipes_in_files(skill_markdown_documents)
        report = "; ".join(
            f"{label}: {' | '.join(messages)}"
            for label, messages in sorted(findings.items())
        )
        assert not findings, (
            "skill markdown must not carry a copy-pasteable recipe that writes "
            f"state.toml outside novel state (design §4.1, ADR-002): {report}"
        )

    def test_discovery_covers_known_skill_files(
        self,
        skill_markdown_documents: dict[str, str],
    ) -> None:
        """The discovered label set equals the known skill markdown inventory.

        This is an intentional tripwire, not the acceptance guard and not a
        second detector. Its hard-coded eight-name inventory lives only here, by
        design: when a contributor adds or removes a reference this assertion
        fails and forces a human to inspect the new file and consciously update
        the reviewed inventory. The guard above scans whatever the glob returns,
        so a stale inventory cannot neuter it.
        """
        assert set(skill_markdown_documents) == KNOWN_SKILL_MARKDOWN

    def test_no_non_md_markdown_like_reference(self, project_root: Path) -> None:
        """No ``.markdown``/``.mdx``/``.mkd`` reference hides from the guard.

        The discovery glob is hard-coded to ``**/*.md``, so a markdown-like
        reference under another extension would carry a hand-edit recipe the
        multi-file guard never scans. This tripwire pins the gate assumption that
        every executable-carrying skill reference ends in ``.md``; a stray file
        fails here and forces a human to widen the glob (task 7.6.4).
        """
        stray = sorted(
            "/".join(path.relative_to(project_root).parts)
            for suffix in (".markdown", ".mdx", ".mkd")
            for path in project_root.glob(f"skill/novel-ralph/**/*{suffix}")
        )
        assert not stray, (
            "markdown-like skill references must use the .md extension so the "
            f"**/*.md discovery glob scans them; widen the glob (task 7.6.4): {stray}"
        )

    def test_done_conditions_predicate_pseudocode_not_flagged(self) -> None:
        """The read-only predicate ``python`` fence shape is not flagged.

        A regression pin reconstructing the ``done-conditions.md`` predicate
        pseudocode as a synthetic fixture (it only *reads* state via
        ``read_state_toml`` and ``state[...]``), so the test does not couple to
        the reference's exact current wording. It carries no write primitive on
        ``state.toml`` and must stay clean.
        """
        fence = (
            "```python\n"
            "# Pseudocode for the predicate check\n"
            "def novel_is_done(working_dir):\n"
            "    state = read_state_toml(working_dir)\n"
            '    if state["phase"]["current"] != "done":\n'
            "        return False\n"
            "    return novel_predicate(working_dir, state)\n"
            "```\n"
        )
        assert not find_direct_state_write_recipes(fence)

    @pytest.mark.parametrize(
        "recipe_id",
        ["raw-open-write", "shell-redirect-no-space", "indented-list-step-append"],
    )
    def test_planted_recipe_in_another_file_is_flagged(self, recipe_id: str) -> None:
        """A recipe planted in a non-``state-layout.md`` file is reported.

        Embeds a named ``PLANTED_RECIPES`` form into a synthetic
        ``done-conditions.md`` document and asserts the driver reports it under
        that label, proving the guard's reach extends beyond ``state-layout.md``.
        The per-form matrix already lives in ``test_planted_recipe_is_flagged``,
        so re-running every form through the driver would be duplication, not
        coverage; three representative ids suffice.
        """
        label = "skill/novel-ralph/references/done-conditions.md"
        documents = {label: PLANTED_RECIPES[recipe_id]}
        findings = find_direct_state_write_recipes_in_files(documents)
        assert set(findings) == {label}, (
            f"planted recipe {recipe_id!r} in {label} should be flagged"
        )
