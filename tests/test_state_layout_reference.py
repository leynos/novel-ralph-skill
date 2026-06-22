"""Fast guard on the absence of the dead ``tomli_w`` snippet.

ADR-002 (``docs/adr-002-toml-round-trip-tomlkit.md``) selects ``tomlkit`` over
``tomli_w``, and design §4.1 eliminates direct editing of ``state.toml`` in
favour of validated ``novel-state`` subcommands. The state-layout skill
reference (``skill/novel-ralph/references/state-layout.md``) once demonstrated
state mutation with a Python heredoc that imported the undeclared ``tomli_w``
dependency and hand-edited ``state.toml`` — a pattern both documents reject.

This guard pins the snippet's absence by static parse so a regression fails
``make test`` rather than shipping silently and tempting a reader to copy the
forbidden pattern. It reads the reference with ``pathlib`` and asserts simple
substrings; it does not shell out. The guard is substring-specific by design:
it pins only ``tomli_w`` / ``import tomli_w`` / ``tomli_w.dump(``, not every
possible direct-edit recipe (broadening it would collide with roadmap task
6.2.3, which owns pointing the reference prose at the ``novel-state`` commands).
"""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _state_layout_text() -> str:
    """Return the state-layout skill reference as text."""
    return (
        _PROJECT_ROOT / "skill" / "novel-ralph" / "references" / "state-layout.md"
    ).read_text(encoding="utf-8")


class TestStateLayoutReference:
    """Pin the absence of the dead ``tomli_w`` snippet from the reference."""

    def test_no_tomli_w_token(self) -> None:
        """The bare ``tomli_w`` token does not appear in the reference."""
        assert "tomli_w" not in _state_layout_text(), (
            "the dead tomli_w snippet must stay removed from "
            "state-layout.md (ADR-002 selects tomlkit; design §4.1 "
            "eliminates direct editing of state.toml)"
        )

    def test_no_tomli_w_import_or_dump(self) -> None:
        """Neither the ``import`` nor the ``dump`` call site reappears.

        The deleted heredoc imported the dependency in the comma form
        ``import tomllib, tomli_w, os`` and wrote ``state.toml`` with
        ``tomli_w.dump(...)`` (Finding 1, ``docs/issues/audit-1.2.2.md``
        lines 26-27). Pin both the comma-form import token and the call
        site so a re-introduced snippet fails ``make test``.
        """
        text = _state_layout_text()
        assert "tomllib, tomli_w" not in text, (
            "the dead `import tomllib, tomli_w, os` line must stay removed "
            "from state-layout.md"
        )
        assert "tomli_w.dump(" not in text, (
            "the dead `tomli_w.dump(` call must stay removed from state-layout.md"
        )
