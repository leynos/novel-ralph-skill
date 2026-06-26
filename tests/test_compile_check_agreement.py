"""Pin ``novel-compile --check`` ⇔ ``compile_consistent`` agreement.

The roadmap 4.1.2 headline criterion: ``novel-compile --check`` and the
``novel-done`` ``compile_consistent`` clause agree on every corpus fixture
because they share the one verdict routine
(:func:`~novel_ralph_skill.state.compiled_matches_drafts`). This pins the
biconditional ``(--check satisfied) ⇔ compile_consistent`` over corpus specs
spanning the three verdicts: ``MATCHES`` (``DONE_PREDICATE_ALL_HOLD``),
``DIVERGES`` (``DONE_PREDICATE_SOLE_STALE_COMPILE`` and the obvious-stale
control), and ``ABSENT`` (``DONE_PREDICATE_ALL_HOLD`` with ``compiled=None``).

This is a finite enumeration over named corpus specs, not a generated input
space, so a parametrized table test is the right tool and Hypothesis is not
required (``python-verification``: example-based suffices when the domain is the
finite set of named fixtures; AGENTS.md property-test trigger does not apply to a
closed enumeration). The ``--check`` side drives ``run(build_app(), ["--check"],
…)`` — argv ``["--check"]``, not ``[]`` — so the exit code compared is genuinely
the checker's, never the write path's (ExecPlan D-CHECK-ARGV, R-AGREE).
"""

from __future__ import annotations

import contextlib
import dataclasses as dc
import io
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands._compile import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import load_state
from novel_ralph_skill.state.done_predicate import compile_consistent

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel compile"

# Corpus specs spanning the three verdicts the shared routine distinguishes:
# MATCHES (coherent), DIVERGES (present-but-stale, both the subtle
# count-coincident body and the obvious control), and ABSENT (no compiled.md).
_AGREEMENT_SPECS: dict[str, wc.WorkingTreeSpec] = {
    "matches": wc.DONE_PREDICATE_ALL_HOLD,
    "diverges_count_coincident": wc.DONE_PREDICATE_SOLE_STALE_COMPILE,
    "diverges_obvious": wc.DONE_PREDICATE_OBVIOUS_STALE_COMPILE,
    "absent": dc.replace(wc.DONE_PREDICATE_ALL_HOLD, compiled=None),
}


def _check_satisfied(working: Path, monkeypatch: pytest.MonkeyPatch) -> bool:
    """Return whether ``novel-compile --check`` is satisfied (exit ``0``).

    Drives ``run(build_app(), ["--check"], …)`` so the exit code is the
    checker's; a ``MATCHES`` verdict exits ``0`` (satisfied) and an ``ABSENT`` or
    ``DIVERGES`` verdict exits ``4`` (a finding), never any other code on these
    well-formed trees.
    """
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["--check"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    code = excinfo.value.code
    assert code in {ExitCode.SUCCESS, ExitCode.ACTIONABLE_FINDING}, (
        f"a well-formed --check verdict must be exit 0 or 4, got {code}"
    )
    return code == ExitCode.SUCCESS


@pytest.mark.parametrize("name", list(_AGREEMENT_SPECS))
def test_check_agrees_with_compile_consistent(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--check`` is satisfied iff the ``compile_consistent`` clause holds.

    The load-bearing acceptance: it falsifies any future drift between the
    command-line ``--check`` surface and the ``novel-done`` compile clause, both
    of which read the one shared verdict routine.
    """
    working = wc.build_working_tree(_AGREEMENT_SPECS[name], tmp_path)
    # Read the clause verdict against the same tree (it takes the working
    # directory explicitly, so no chdir is needed for this side).
    clause = compile_consistent(load_state(working / "state.toml"), working)
    satisfied = _check_satisfied(working, monkeypatch)
    assert satisfied is clause, (
        f"{name}: --check satisfied ({satisfied}) must equal "
        f"compile_consistent ({clause})"
    )
