"""Guard against any direct ``state.toml``-write recipe in the reference.

ADR-002 (``docs/adr-002-toml-round-trip-tomlkit.md``) selects ``tomlkit`` over
``tomli_w`` as the only sanctioned writer, and design §4.1
(``docs/novel-ralph-harness-design.md``) eliminates direct editing of
``state.toml`` in favour of validated ``novel-state`` subcommands. The
state-layout skill reference
(``skill/novel-ralph/references/state-layout.md``) once demonstrated state
mutation with a Python heredoc that imported the undeclared ``tomli_w``
dependency and hand-edited ``state.toml`` — a pattern both documents reject.

This guard forbids *any* direct ``state.toml``-write recipe inside an
executable code fence (``python``/``py``/``sh``/``bash``/``shell``/
``console``), not just the historical ``tomli_w`` form. It scans only
executable fences, so it leaves untouched the atomic-write *prose* the design
mandates (write to ``state.toml.new``, fsync, rename — design §3.4 and §5.3,
carried as prose in the reference) and any ``novel-state`` invocation example.
Rewriting the reference prose to point at the ``novel-state`` commands remains
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
from _state_layout_scanner import find_direct_state_write_recipes

if typ.TYPE_CHECKING:
    from conftest import RepoTextReader

_STATE_LAYOUT_PARTS = ("skill", "novel-ralph", "references", "state-layout.md")


# One forbidden hand-edit recipe per covered form, keyed by a stable id. Each
# is a fenced executable block that writes ``state.toml`` and must be flagged.
# Triple-quoted literals avoid the implicit string concatenation a tuple of
# line fragments would introduce inside a collection literal (ruff ISC).
_PLANTED_RECIPES: dict[str, str] = {
    "tomlkit-dump": (
        '```python\ntomlkit.dump(doc, open("working/state.toml", "w"))\n```\n'
    ),
    "tomllib-plus-write-text": (
        "```python\n"
        'doc = tomllib.load(open("working/state.toml", "rb"))\n'
        'Path("working/state.toml").write_text("x = 1")\n'
        "```\n"
    ),
    "raw-open-write": '```python\nopen("working/state.toml", "w").write("x")\n```\n',
    "historical-tomli_w-heredoc": (
        "```python\n"
        'with open("working/state.toml", "wb") as f:\n'
        "    tomli_w.dump(doc, f)\n"
        "```\n"
    ),
    "shell-cat-heredoc": "```sh\ncat > working/state.toml <<'EOF'\nx=1\nEOF\n```\n",
    "shell-cat-heredoc-no-space": (
        "```sh\ncat >working/state.toml <<'EOF'\nx=1\nEOF\n```\n"
    ),
    "shell-append": "```sh\necho 'x = 1' >> working/state.toml\n```\n",
    "shell-redirect-no-space": "```sh\necho 'x = 1' >working/state.toml\n```\n",
    "shell-append-no-space": "```sh\necho 'x = 1' >>working/state.toml\n```\n",
    "path-write-bytes": (
        '```python\nPath("working/state.toml").write_bytes(b"x")\n```\n'
    ),
    "tilde-raw-open-write": (
        '~~~python\nopen("working/state.toml", "w").write("x")\n~~~\n'
    ),
    "quad-backtick-raw-open-write": (
        '````python\nopen("working/state.toml", "w").write("x")\n````\n'
    ),
    "shell-tee": "```sh\necho 'x = 1' | tee working/state.toml\n```\n",
    "shell-tee-append": "```sh\necho 'x = 1' | tee -a working/state.toml\n```\n",
    "python3-raw-open-write": (
        '```python3\nopen("working/state.toml", "w").write("x = 1")\n```\n'
    ),
    "indented-list-step-append": (
        "1. Edit the state file directly:\n\n"
        "   ```sh\n"
        "   echo 'x = 1' >> working/state.toml\n"
        "   ```\n"
    ),
    "backstop-unknown-writer": (
        '```python\nmywriter("working/state.toml").write(serialise(doc))\n```\n'
    ),
}


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
            "writes state.toml outside novel-state (design §4.1, ADR-002)"
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

    def test_atomic_write_prose_not_flagged(self) -> None:
        """Atomic-write *prose* (no fence) is never flagged.

        Synthetic fixture reconstructing the real reference's prose — the
        line-60-61 summary plus the numbered "Discipline" list — which carries
        the atomic-write discipline outside any fence. It is not a copy of a
        fenced block.
        """
        prose = (
            "The agent's primary memory is written atomically (write to "
            "`state.toml.new`, fsync, rename) at the end.\n\n"
            "Discipline:\n\n"
            "1. Write state.toml via a temporary file in working/, then "
            "atomically rename it over working/state.toml, so a crash never "
            "leaves a torn file.\n"
        )
        assert not find_direct_state_write_recipes(prose)

    def test_python_write_to_new_temp_not_flagged(self) -> None:
        """A Python write to the ``state.toml.new`` temporary is clean.

        The sanctioned atomic-write pattern (design §3.4, §5.3) writes the
        ``state.toml.new`` temporary and renames it over the live file. The
        live-file gate is anchored on a filename boundary, so the
        ``state.toml.new`` write — where the live ``state.toml`` is never named
        as a bare reference — must not be mistaken for a direct edit. Before the
        anchor fix the bare ``state.toml`` substring inside ``state.toml.new``
        false-flagged this temp-file write.
        """
        fence = (
            "```python\n"
            "tmp = Path('working/state.toml.new')\n"
            "tmp.write_text(serialise(doc))\n"
            "tmp.replace(tmp.with_suffix(''))  # atomic rename over the live file\n"
            "```\n"
        )
        assert not find_direct_state_write_recipes(fence)

    def test_shell_redirect_to_new_temp_not_flagged(self) -> None:
        """A shell redirect to the ``state.toml.new`` temporary is clean.

        Mirrors the Python case for the shell redirect rule: a redirect to the
        ``state.toml.new`` temporary, renamed over the live file via a
        parameter-expanded destination, is the atomic discipline, not a direct
        write. Before the anchor fix the redirect rule matched the bare
        ``state.toml`` inside ``state.toml.new``.
        """
        fence = (
            "```sh\n"
            "tmp=working/state.toml.new\n"
            "printf 'x = 1\\n' > \"$tmp\"\n"
            'mv "$tmp" "${tmp%.new}"  # atomic rename over the live file\n'
            "```\n"
        )
        assert not find_direct_state_write_recipes(fence)

    def test_read_only_open_not_flagged(self) -> None:
        """A read-only ``open(..., "rb")`` of state.toml is not flagged."""
        fence = (
            "```python\n"
            "import tomllib\n"
            'data = tomllib.load(open("working/state.toml", "rb"))\n'
            "```\n"
        )
        assert not find_direct_state_write_recipes(fence)

    def test_unrelated_redirect_not_flagged(self) -> None:
        """A redirect to a different path is not flagged."""
        fence = "```sh\necho done > /tmp/foo\n```\n"
        assert not find_direct_state_write_recipes(fence)

    def test_unrelated_no_space_redirect_not_flagged(self) -> None:
        """A no-space redirect to a different path is not flagged.

        Pairs with the no-space planted rows: allowing zero-or-more whitespace
        after the operator must not loosen the path anchor, so
        ``echo done >/tmp/foo`` (no space, different path) stays clean.
        """
        fence = "```sh\necho done >/tmp/foo\n```\n"
        assert not find_direct_state_write_recipes(fence)

    def test_indented_unrelated_redirect_not_flagged(self) -> None:
        """An indented redirect to a different path stays clean.

        Pairs with the indented-recipe planted row: dedenting the fence body
        must not turn a path-anchored redirect into a redirect-anywhere rule,
        so a list-nested ``echo done > /tmp/foo`` is still ignored.
        """
        fence = "1. Marker step:\n\n   ```sh\n   echo done > /tmp/foo\n   ```\n"
        assert not find_direct_state_write_recipes(fence)

    def test_pycon_read_only_session_not_flagged(self) -> None:
        """A ``pycon`` REPL transcript that only reads state.toml is clean.

        The ``>>>`` prompt must not be misread as a ``>>`` append operator, so
        a read-only ``tomllib.load(open(..., "rb"))`` console session carries
        no write signal and is not flagged.
        """
        fence = (
            "```pycon\n"
            ">>> import tomllib\n"
            '>>> tomllib.load(open("working/state.toml", "rb"))\n'
            "```\n"
        )
        assert not find_direct_state_write_recipes(fence)

    def test_novel_state_example_not_flagged(self) -> None:
        """A ``novel-state`` invocation example is not flagged."""
        fence = "```sh\nnovel-state set-cursor --chapter 7\n```\n"
        assert not find_direct_state_write_recipes(fence)

    def test_non_executable_fence_ignored(self) -> None:
        """A ``toml`` fence naming state.toml is illustration, not a recipe."""
        fence = "```toml\n# working/state.toml schema\nschema_version = 1\n```\n"
        assert not find_direct_state_write_recipes(fence)

    @pytest.mark.parametrize(
        ("label", "recipe"),
        list(_PLANTED_RECIPES.items()),
        ids=list(_PLANTED_RECIPES),
    )
    def test_planted_recipe_is_flagged(self, label: str, recipe: str) -> None:
        """Each planted hand-edit recipe form is flagged."""
        messages = find_direct_state_write_recipes(recipe)
        assert messages, f"planted recipe {label!r} should be flagged"
