"""Hand-maintained inventory of skill markdown references for the guard tests.

This support module is the single home for ``_KNOWN_SKILL_MARKDOWN``, the
reviewed inventory of executable-carrying skill markdown files that
``tests/test_state_layout_reference.py`` pins as an intentional tripwire. It was
extracted from that test module once the widened guard plus the markdown-like
extension tripwire (roadmap 7.6.3.6) pushed the module past the 400-line cap
(AGENTS.md lines 24-27); the sanctioned reconciliation for a genuine cap breach
is to promote the shared datum to a non-``test_*.py`` support module imported by
the consuming test module, mirroring ``tests/_state_layout_scanner.py`` and
``tests/_planted_recipes.py``.

``tests/_skill_markdown_inventory.py`` is inside ``PYTHON_TARGETS``
(``Makefile``), so it carries the full Ruff lint and format, 100%
``interrogate`` docstring coverage, Pylint, and ``ty`` typecheck gates; the
``**/test_*.py`` per-file-ignores do not match it.
"""

from __future__ import annotations

import typing as typ

# The skill markdown set the multi-file guard scans, anchored under
# ``skill/novel-ralph/``. ``test_discovery_covers_known_skill_files`` pins this
# inventory as an intentional tripwire: adding or removing a reference fails that
# test and forces a human to inspect the new file. The guard itself never
# consults this list — it scans whatever the discovery glob returns — so a stale
# inventory cannot neuter it.
#
# This inventory is hand-maintained and must NOT be derived from the discovery
# glob: rebuilding it from ``skill/novel-ralph/**/*.md`` would make
# ``test_discovery_covers_known_skill_files`` tautological and silently optimise
# the tripwire away, so the literal frozenset is load-bearing and must stay
# typed out by hand.
KNOWN_SKILL_MARKDOWN: typ.Final[frozenset[str]] = frozenset({
    "skill/novel-ralph/SKILL.md",
    "skill/novel-ralph/references/conflict-attractor.md",
    "skill/novel-ralph/references/critic-personas.md",
    "skill/novel-ralph/references/desloppify-checklist.md",
    "skill/novel-ralph/references/done-conditions.md",
    "skill/novel-ralph/references/jtbd-novel.md",
    "skill/novel-ralph/references/state-layout.md",
    "skill/novel-ralph/references/stc-beat-sheet.md",
})
