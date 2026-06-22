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
helpers below are pure functions over markdown text, taking the document as a
parameter rather than touching the filesystem.
"""

from __future__ import annotations

import re
import typing as typ

import pytest

if typ.TYPE_CHECKING:
    import collections.abc as cabc

_STATE_LAYOUT_PARTS = ("skill", "novel-ralph", "references", "state-layout.md")

# The Python-flavoured info strings within the executable set. The bare
# ``.write(`` backstop (an unknown writer reached by ``.write(`` on the state
# path) only makes sense for Python fences, where ``.write(`` is a method call
# rather than a shell token.
_PYTHON_INFO_STRINGS = frozenset({"python", "python3", "py", "py3", "pycon"})

# Fences whose bodies a reader could copy and run as a mutation script: the
# Python set above plus the shells. Fences labelled
# ``text``/``toml``/``markdown``/``json`` are illustration only and are never
# scanned, so the ``toml`` schema fence and the atomic-write prose (which lives
# outside any fence) cannot trip the guard.
_EXECUTABLE_INFO_STRINGS = _PYTHON_INFO_STRINGS | frozenset({
    "sh",
    "bash",
    "shell",
    "console",
})

# Capture each fenced block: the fence run on the opening fence, its info
# string, and the body up to (but excluding) the closing fence. ``re.DOTALL``
# lets the body span lines; ``re.MULTILINE`` anchors the fences to line starts.
# CommonMark permits up to three leading spaces before a fence, so the opening
# and closing markers allow ``{0,3}`` of indentation; otherwise a fence nested
# in a numbered-list step (which state-layout.md's "Discipline" lists use) would
# be invisible to the scan, a reachable bypass. The captured indentation is
# stripped from the body before the write-token rule runs (see
# :func:`_dedent_fence_body`).
# CommonMark permits both backtick and tilde fences, and a fence run is *three
# or more* of the marker character, with the closing run the same character and
# at least as long as the opening. Hard-coding ``` would let a ``~~~python`` or
# a four-backtick fence carry a hand-edit recipe past the scan. ``(?P<fence>``
# captures the opening run (``` {3,} `` or ``~{3,}``); the closing fence
# back-references that exact run via ``(?P=fence)`` so the closing marker matches
# character and length. A backtick info string may not contain a backtick
# (CommonMark), so the info string excludes the fence character.
_FENCE_RE = re.compile(
    r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^\n`]*)\n"
    r"(?P<body>.*?)^ {0,3}(?P=fence)",
    re.DOTALL | re.MULTILINE,
)

# The state file the guard protects. Matching the bare filename (rather than a
# fixed ``working/`` prefix) catches recipes that reference the file by any
# path, including a bare ``state.toml``.
_STATE_FILE = "state.toml"

# Library and method write tokens that target a TOML document directly. Any of
# these alongside ``state.toml`` in an executable fence is a hand-edit recipe.
# ``.write_bytes(`` is included alongside its text sibling: binary mode is the
# natural TOML-write form (the historical heredoc and ``tomli_w`` both use
# ``wb``), so a ``Path(...).write_bytes(...)`` to the state file must be caught
# — the bare ``.write(`` backstop does not contain the ``.write_bytes(``
# substring and would otherwise miss it.
_LIBRARY_WRITE_TOKENS = (
    "tomlkit.dump",
    "tomli_w",
    ".write_text(",
    ".write_bytes(",
    ".writelines(",
)

# Python write-mode literals that, paired with ``open(`` and ``state.toml``,
# signal a write (so a read-only ``open(..., "rb")`` is left alone).
_WRITE_MODE_RE = re.compile(r"""["'][rb]*[wax]\+?[rb]*["']""")

# Shell redirects and heredocs whose target is the ``state.toml`` path. Every
# rule is anchored to the path, never redirect-anywhere, so an unrelated
# ``echo done > /tmp/foo`` fence stays clean. ``tee`` may carry flag tokens
# before the path (e.g. the append form ``tee -a working/state.toml``), so
# optional ``-`` flags are allowed between ``tee`` and the path. POSIX shells
# treat ``>file`` and ``> file`` identically — the whitespace after the operator
# is optional — so the redirect operators allow ``\s*`` before the path; a
# required ``\s+`` would let the copy-pasteable no-space forms
# (``echo x >working/state.toml``) bypass the guard. ``tee`` still needs ``\s+``
# because ``teeworking/state.toml`` is a different command. The ``(?<!>)`` guard
# keeps a ``>>>`` REPL prompt in a ``pycon`` transcript from being read as a
# ``>>`` append operator, which would falsely flag a read-only
# ``tomllib.load(open(..., "rb"))`` console session.
_REDIRECT_RE = re.compile(
    r"(?:tee(?:\s+-\S+)*\s+|(?<!>)>>?\s*)\S*state\.toml",
)


def _dedent_fence_body(body: str, indent: str) -> str:
    """Strip the opening fence's indentation from each line of ``body``.

    CommonMark removes up to the opening fence's leading-space count from each
    content line of an indented fenced block. Mirroring that here keeps the
    write-token rule operating on the logical recipe text rather than on the
    list-step indentation, so an indented recipe is scanned identically to a
    flush-left one. Lines with less indentation than the opening fence have their
    existing leading space simply stripped, never under-run.
    """
    if not indent:
        return body
    width = len(indent)
    return "".join(
        line[width:] if line[:width].isspace() else line.lstrip(" ")
        for line in body.splitlines(keepends=True)
    )


def _iter_executable_fences(markdown: str) -> list[tuple[str, str]]:
    """Yield ``(info_string, body)`` for each executable code fence.

    The info string is normalised to its first whitespace-delimited token in
    lower case (e.g. ``"console title=…"`` becomes ``"console"``). Only fences
    whose info string is in :data:`_EXECUTABLE_INFO_STRINGS` are returned;
    illustration fences (``text``/``toml``/``markdown``/``json``) are skipped.
    The body is dedented by the opening fence's indentation so a recipe nested
    in a numbered-list step is scanned identically to a flush-left one.
    """
    fences: list[tuple[str, str]] = []
    for match in _FENCE_RE.finditer(markdown):
        info = match.group("info").strip().split()
        label = info[0].lower() if info else ""
        if label in _EXECUTABLE_INFO_STRINGS:
            body = _dedent_fence_body(match.group("body"), match.group("indent"))
            fences.append((label, body))
    return fences


def _write_token(label: str, body: str) -> str | None:
    """Return the write token a fence body uses on ``state.toml``, or ``None``.

    A fence is a hand-edit recipe when its body names ``state.toml`` together
    with a write primitive: a known library writer, an ``open(`` paired with a
    write-mode literal, a redirect or heredoc targeting the path, or — as a
    backstop for unknown writers — a bare ``.write(`` call. A read-only
    ``open(..., "rb")`` carries no write signal and is therefore not flagged.
    """
    if _STATE_FILE not in body:
        return None
    for token in _LIBRARY_WRITE_TOKENS:
        if token in body:
            return token
    if "open(" in body and _WRITE_MODE_RE.search(body):
        return "open(...) with write mode"
    if _REDIRECT_RE.search(body):
        return "shell redirect to state.toml"
    if label in _PYTHON_INFO_STRINGS and ".write(" in body:
        return ".write( on state.toml"
    return None


def find_direct_state_write_recipes(markdown: str) -> list[str]:
    """Return a message per executable code fence that writes ``state.toml``.

    Empty list means the document is clean. Each message names the offending
    fence's info string and the matched write token, so a failure points the
    author at the recipe and at design §4.1 (direct editing eliminated) and
    ADR-002 (``tomlkit`` is the only sanctioned writer).
    """
    messages: list[str] = []
    for label, body in _iter_executable_fences(markdown):
        token = _write_token(label, body)
        if token is not None:
            messages.append(
                f"`{label}` fence writes state.toml via {token}: direct "
                "editing of state.toml is eliminated (design §4.1, ADR-002); "
                "route mutations through novel-state"
            )
    return messages


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
        read_repo_text: cabc.Callable[..., str],
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
        read_repo_text: cabc.Callable[..., str],
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
        read_repo_text: cabc.Callable[..., str],
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
