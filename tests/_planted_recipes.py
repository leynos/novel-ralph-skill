"""Shared corpus of planted ``state.toml``-write recipes for the guard tests.

This support module is the single home for the planted hand-edit recipe corpus
the state-write guard tests assert against. It was extracted from
``tests/test_state_layout_reference.py`` once the widened multi-file guard
(roadmap 7.3.3) pushed that module past the 400-line cap (AGENTS.md lines 24-27).
The plan's sanctioned reconciliation for a genuine cap breach is to promote the
corpus to a shared non-``test_*.py`` support module imported by every consuming
test module — mirroring how ``tests/_state_layout_scanner.py`` is shared — rather
than a cross-module *private* import, which ``tests/conftest.py`` and six
post-merge audits exist to eliminate.

``tests/_planted_recipes.py`` is inside ``PYTHON_TARGETS`` (``Makefile``), so it
carries the full Ruff lint and format, 100% ``interrogate`` docstring coverage,
Pylint, and ``ty`` typecheck gates; the ``**/test_*.py`` per-file-ignores do not
match it.

Each entry is a fenced executable block that writes ``state.toml`` and so must be
flagged by :func:`_state_layout_scanner.find_direct_state_write_recipes`. The keys
are stable ids used in the parametrized test reports. Multi-line recipes are
written as parenthesized implicit string concatenation with explicit newline
escapes rather than triple-quoted literals, so the fence's own triple backticks
need no escaping and the short and multi-line entries share one quoting style.
"""

from __future__ import annotations

import typing as typ
from types import MappingProxyType

# One forbidden hand-edit recipe per covered form, keyed by a stable id. The
# corpus is wrapped in a read-only ``MappingProxyType`` view so a consuming test
# cannot mutate the shared canonical set across runs.
PLANTED_RECIPES: typ.Final[MappingProxyType[str, str]] = MappingProxyType({
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
    # One flagged recipe per under-exercised executable label (``py``, ``py3``,
    # ``pycon``, ``bash``, ``shell``, ``console``): every member of
    # ``_EXECUTABLE_INFO_STRINGS`` carries a positive case, so dropping a label
    # from the frozenset fails a test rather than silently shrinking the guard
    # (roadmap 7.6.3.1).
    "py-raw-open-write": ('```py\nopen("working/state.toml", "w").write("x")\n```\n'),
    "py3-write-text": ('```py3\nPath("working/state.toml").write_text("x = 1")\n```\n'),
    "pycon-write-text": (
        "```pycon\n"
        ">>> from pathlib import Path\n"
        '>>> Path("working/state.toml").write_text("x = 1")\n'
        "```\n"
    ),
    "bash-redirect": "```bash\necho 'x = 1' > working/state.toml\n```\n",
    "shell-redirect": "```shell\necho 'x = 1' > working/state.toml\n```\n",
    "console-redirect": "```console\n$ echo 'x = 1' > working/state.toml\n```\n",
})
