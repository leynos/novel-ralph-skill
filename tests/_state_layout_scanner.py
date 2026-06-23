"""Pure-function scanner for direct ``state.toml``-write recipes.

This support module carries the fence-scanner helpers used by
``tests/test_state_layout_reference.py``. It is extracted so the test module
stays under the 400-line cap (roadmap addendum 1.2.8.2). The functions are pure
over markdown text — they take the document as a parameter and never touch the
filesystem, shell out, or import ``novel_ralph_skill``.

ADR-002 (``docs/adr-002-toml-round-trip-tomlkit.md``) selects ``tomlkit`` over
``tomli_w`` as the only sanctioned writer, and design §4.1
(``docs/novel-ralph-harness-design.md``) eliminates direct editing of
``state.toml`` in favour of validated ``novel-state`` subcommands. The scanner
forbids *any* direct ``state.toml``-write recipe inside an executable code fence
(``python``/``py``/``sh``/``bash``/``shell``/``console``), leaving untouched the
atomic-write *prose* the design mandates and any ``novel-state`` invocation
example.
"""

from __future__ import annotations

import re

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
# path, including a bare ``state.toml``. The trailing ``(?![\w.])`` boundary
# anchors the match on the *live* file: ``state.toml`` must not be followed by a
# filename-continuation character, so a write-then-rename illustration targeting
# only the ``state.toml.new`` temporary (design §3.4, §5.3) is not mistaken for a
# direct edit of the live file. A following quote, space, paren, redirect, or
# end-of-line all satisfy the boundary, so every genuine bare-``state.toml``
# reference still trips the gate.
_STATE_FILE_RE = re.compile(r"state\.toml(?![\w.])")

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
# ``tomllib.load(open(..., "rb"))`` console session. The trailing ``(?![\w.])``
# boundary mirrors :data:`_STATE_FILE_RE`: a redirect to the ``state.toml.new``
# temporary in a write-then-rename illustration (design §3.4, §5.3) targets the
# temp file, not the live one, so it must not be read as a direct write.
_REDIRECT_RE = re.compile(
    r"(?:tee(?:\s+-\S+)*\s+|(?<!>)>>?\s*)\S*state\.toml(?![\w.])",
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

    A fence is a hand-edit recipe when its body names the live ``state.toml``
    together with a write primitive: a known library writer, an ``open(`` paired
    with a write-mode literal, a redirect or heredoc targeting the path, or — as
    a backstop for unknown writers — a bare ``.write(`` call. A read-only
    ``open(..., "rb")`` carries no write signal and is therefore not flagged.

    The gate matches the *live* file via :data:`_STATE_FILE_RE`, so a fence that
    only touches the ``state.toml.new`` temporary (the sanctioned
    write-then-rename illustration, design §3.4 and §5.3) is not flagged.
    """
    if not _STATE_FILE_RE.search(body):
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


def find_direct_state_write_recipes_in_files(
    documents: dict[str, str],
) -> dict[str, list[str]]:
    """Return, per document label, the direct-write recipes it carries.

    ``documents`` maps a human-readable label (e.g. a repo-relative path) to the
    document's markdown text. The return maps each label whose document carries
    at least one recipe to its non-empty message list; clean documents are
    omitted, so an empty return mapping means every document is clean. The driver
    calls :func:`find_direct_state_write_recipes` once per document and adds no
    second matcher, so multi-file coverage reuses the single-file detector
    verbatim (roadmap 7.3.3; design §4.1; ADR-002).
    """
    findings: dict[str, list[str]] = {}
    for label, markdown in documents.items():
        messages = find_direct_state_write_recipes(markdown)
        if messages:
            findings[label] = messages
    return findings
