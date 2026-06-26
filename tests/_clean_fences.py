"""Verified-clean fence corpus the state-write guard must never flag.

This support module is the single home for the clean-case corpus the broadened
fence scanner is pinned against in
``tests/test_state_layout_reference.py::TestFindDirectStateWriteRecipes``. Each
entry shares the same skeleton — "this fenced (or fence-free) snippet carries no
direct ``state.toml`` write, so :func:`find_direct_state_write_recipes` returns
an empty list" — so the per-rationale methods were folded into one parametrized
``test_clean_fence_not_flagged`` keyed by these ids (roadmap 7.6.3.7). The
rationale that was each method's docstring now lives in the per-entry comments
below and survives as the test ``ids``.

Promoting the corpus to a shared non-``test_*.py`` support module (mirroring
``tests/_planted_recipes.py``) keeps the consuming test module under the
400-line cap (AGENTS.md lines 24-27).

``tests/_clean_fences.py`` is inside ``PYTHON_TARGETS`` (``Makefile``), so it
carries the full Ruff lint and format, 100% ``interrogate`` docstring coverage,
Pylint, and ``ty`` typecheck gates; the ``**/test_*.py`` per-file-ignores do not
match it.
"""

from __future__ import annotations

import typing as typ
from types import MappingProxyType

# One verified-clean snippet per rationale, keyed by a stable id reused as the
# parametrize ``id``. The corpus is wrapped in a read-only ``MappingProxyType``
# so a consuming test cannot mutate the shared canonical set across runs.
CLEAN_FENCES: typ.Final[MappingProxyType[str, str]] = MappingProxyType({
    # Atomic-write *prose* (no fence): the line-60-61 summary plus the numbered
    # "Discipline" list carry the discipline outside any fence, so they are never
    # scanned. Reconstructed synthetically rather than copied from the reference.
    "atomic-write-prose": (
        "The agent's primary memory is written atomically (write to "
        "`state.toml.new`, fsync, rename) at the end.\n\n"
        "Discipline:\n\n"
        "1. Write state.toml via a temporary file in working/, then "
        "atomically rename it over working/state.toml, so a crash never "
        "leaves a torn file.\n"
    ),
    # The sanctioned atomic-write pattern (design §3.4, §5.3) writes the
    # ``state.toml.new`` temporary and renames it over the live file. The
    # live-file gate is anchored on a filename boundary, so the temp write is not
    # mistaken for a direct edit. Before the anchor fix the bare ``state.toml``
    # substring inside ``state.toml.new`` false-flagged this.
    "python-write-to-new-temp": (
        "```python\n"
        "tmp = Path('working/state.toml.new')\n"
        "tmp.write_text(serialise(doc))\n"
        "tmp.replace(tmp.with_suffix(''))  # atomic rename over the live file\n"
        "```\n"
    ),
    # Mirrors the Python case for the shell redirect rule: a redirect to the
    # ``state.toml.new`` temporary, renamed over the live file via a
    # parameter-expanded destination, is the atomic discipline, not a direct
    # write. Before the anchor fix the redirect rule matched the bare
    # ``state.toml`` inside ``state.toml.new``.
    "shell-redirect-to-new-temp": (
        "```sh\n"
        "tmp=working/state.toml.new\n"
        "printf 'x = 1\\n' > \"$tmp\"\n"
        'mv "$tmp" "${tmp%.new}"  # atomic rename over the live file\n'
        "```\n"
    ),
    # A read-only ``open(..., "rb")`` of state.toml carries no write signal.
    "read-only-open": (
        "```python\n"
        "import tomllib\n"
        'data = tomllib.load(open("working/state.toml", "rb"))\n'
        "```\n"
    ),
    # A redirect to a different path is not flagged.
    "unrelated-redirect": "```sh\necho done > /tmp/foo\n```\n",
    # Pairs with the no-space planted rows: allowing zero-or-more whitespace after
    # the operator must not loosen the path anchor, so ``echo done >/tmp/foo``
    # (no space, different path) stays clean.
    "unrelated-no-space-redirect": "```sh\necho done >/tmp/foo\n```\n",
    # Pairs with the indented-recipe planted row: dedenting the fence body must
    # not turn a path-anchored redirect into a redirect-anywhere rule, so a
    # list-nested ``echo done > /tmp/foo`` is still ignored.
    "indented-unrelated-redirect": (
        "1. Marker step:\n\n   ```sh\n   echo done > /tmp/foo\n   ```\n"
    ),
    # A ``pycon`` REPL transcript that only reads state.toml: the ``>>>`` prompt
    # must not be misread as a ``>>`` append operator, so a read-only
    # ``tomllib.load(open(..., "rb"))`` session carries no write signal.
    "pycon-read-only-session": (
        "```pycon\n"
        ">>> import tomllib\n"
        '>>> tomllib.load(open("working/state.toml", "rb"))\n'
        "```\n"
    ),
    # A ``novel state`` invocation example is not flagged.
    "novel-state-example": "```sh\nnovel state set-cursor --chapter 7\n```\n",
    # A ``toml`` fence naming state.toml is illustration, not a recipe; only
    # executable fences are scanned.
    "non-executable-fence": (
        "```toml\n# working/state.toml schema\nschema_version = 1\n```\n"
    ),
})
