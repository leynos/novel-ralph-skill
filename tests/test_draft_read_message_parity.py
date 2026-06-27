"""Anti-drift proof that the six draft-read boundaries share one remedy clause.

Roadmap §6.3.5 exists to stop the six draft-read boundaries —
``_disk_evidence_or_state_error``, ``_recount``, ``_wordcount``, ``_novel_done``,
``_desloppify.source_chapters``, and ``_compile`` — from emitting divergent
exit-3 messages. They now all route through the one
:func:`~novel_ralph_skill.commands.state_sourcing._draft_read_error` formatter, so
this test drives each from a coherent ``working/`` tree whose first chapter draft
is corrupt and asserts the one **formatter-owned remedy substring** (the fixed
inspect/repair clause) appears in every boundary's ``messages``. A one-sided
re-wording of that clause reintroduces the drift the test catches.

It deliberately does **not** assert byte-for-byte identity *across* boundaries:
the formatter interpolates the reported ``working/`` directory, and the six
boundaries pass different directories under different commands, so two messages
match verbatim only when their reported directory matches (ExecPlan advisory A3).
The remedy clause is the part the formatter owns and shares.

The mutator view-derivation boundary is **not** in this draft-read parity set —
it reuses ``_state_input_error``'s present-but-corrupt arm, already guarded by
``test_state_input_message_parity.py::test_both_load_boundaries_emit_identical_corrupt_message``;
its message is pinned by the Work item 4 unit guard in
``test_complete_final_pass_unit.py``.
"""

from __future__ import annotations

import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands import _compile, _desloppify, _novel_done, _wordcount
from novel_ralph_skill.commands import novel_state as _novel_state
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts

# The fixed inspect/repair clause ``_draft_read_error`` owns; every draft-read
# boundary must surface it verbatim. Pinned here so a one-sided re-wording of the
# formatter (or a boundary that stops routing through it) fails this assertion.
_REMEDY_CLAUSE = "is unreadable or corrupt — inspect and repair it, or restore it"

# One representative command per draft-read boundary. ``novel compile`` exercises
# the ``compile_manuscript`` tail and ``novel compile --check`` the
# ``check_compiled`` tail, so both of ``_compile``'s draft-read arms are covered.
_BOUNDARIES: tuple[tuple[str, str, cabc.Callable[[], object], list[str]], ...] = (
    ("check", "novel state", _novel_state.build_app, ["check"]),
    ("recount", "novel state", _novel_state.build_app, ["recount"]),
    ("wordcount", "novel wordcount", _wordcount.build_app, []),
    ("done", "novel done", _novel_done.build_app, []),
    ("desloppify", "novel desloppify", _desloppify.build_app, []),
    ("compile", "novel compile", _compile.build_app, []),
    ("compile-check", "novel compile", _compile.build_app, ["--check"]),
)


def test_every_draft_read_boundary_shares_the_remedy_clause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every draft-read boundary surfaces the one formatter-owned remedy clause.

    Drives each boundary from a coherent ``final-pass`` tree whose first chapter
    draft is corrupt invalid UTF-8, then asserts the fixed inspect/repair clause
    appears in each boundary's exit-3 ``messages``. Proves all six route through the
    one ``_draft_read_error`` formatter (roadmap §6.3.5).

    The ``final-pass`` phase is chosen (not the mid-drafting baseline) because it
    carries a present ``compiled.md``, so the ``done`` and ``compile --check``
    boundaries — which read a draft only when ``compiled.md`` is present — also
    reach the draft-read arm rather than short-circuiting on an absent compile.
    """
    working = wc.build_working_tree(wc.PHASE_STATES["final-pass"], tmp_path)
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    assert chapters, "the baseline tree must contain at least one chapter"
    (chapters[0] / "draft.md").write_bytes(b"\xff\xfe invalid words here")

    for label, command, build_app, argv in _BOUNDARIES:
        monkeypatch.chdir(working.parent)
        with pytest.raises(SystemExit) as excinfo:
            run(
                typ.cast("cyclopts.App", build_app()),
                argv,
                RunContext(command=command, working_dir="working", human=False),
            )
        code = typ.cast("int", excinfo.value.code)
        envelope = json.loads(capsys.readouterr().out or "{}")
        messages = tuple(envelope.get("messages", ()))
        text = "\n".join(messages)

        assert code == ExitCode.STATE_ERROR, f"the {label} boundary must exit 3"
        assert _REMEDY_CLAUSE in text, (
            f"the {label} boundary must share the formatter-owned remedy clause; "
            f"got {messages!r}"
        )
