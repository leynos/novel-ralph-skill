"""Unit tests for the contract-level ``drive`` entry-point seam (7.3.5).

The :func:`~novel_ralph_skill.contract.runner.drive` seam owns the
build-:class:`~novel_ralph_skill.contract.runner.RunContext`-then-call-``run``
plumbing the ``novel`` entry point used to spell inline. These tests pin the
*seam half* of the roadmap-1.3.6 transitive invariant ``main -> drive -> run``:
that ``drive`` forwards its app and argv unchanged to ``run`` under a
faithfully constructed :class:`RunContext`, and that it never swallows ``run``'s
``SystemExit``. The complementary *entry-point half* (``main`` routes through
``drive``) lives in
``tests/test_contract_app_centralisation.py::test_novel_entry_point_routes_through_the_shared_seam``.
"""

from __future__ import annotations

import typing as typ

import pytest

from novel_ralph_skill.contract import drive
from novel_ralph_skill.contract.runner import RunContext, make_contract_app

if typ.TYPE_CHECKING:
    import collections.abc as cabc

    import cyclopts


def test_drive_forwards_app_and_argv_to_run_under_a_faithful_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``drive`` forwards ``app``/``argv`` to ``run`` with a faithful context.

    This is the *seam half* of the 1.3.6 transitive invariant: the migrated
    entry-point tripwire proves ``main`` routes through ``drive``; this proves
    ``drive`` forwards to ``run`` carrying the exact ``command``/``working_dir``/
    ``human`` scalars it was handed, wrapped in a :class:`RunContext`.
    """
    captured: dict[str, object] = {}

    def _capture_run(
        app: cyclopts.App,
        argv: cabc.Sequence[str],
        context: RunContext,
    ) -> None:
        """Capture ``run``'s arguments instead of exiting the process."""
        captured["app"] = app
        captured["argv"] = argv
        captured["context"] = context

    monkeypatch.setattr("novel_ralph_skill.contract.runner.run", _capture_run)

    app = make_contract_app("novel")
    argv = ["x"]
    drive(app, argv, command="novel state", working_dir="/abs/working", human=True)

    assert captured["app"] is app
    assert captured["argv"] is argv
    context = captured["context"]
    assert isinstance(context, RunContext)
    assert context.command == "novel state"
    assert context.working_dir == "/abs/working"
    assert context.human is True


def test_drive_propagates_run_system_exit() -> None:
    """``drive`` does not swallow ``run``'s ``SystemExit`` (the seam exits).

    Driving a real contract app with a ``--help`` argv reaches ``run``'s
    help/version arm, which exits ``0``. The seam must let that ``SystemExit``
    propagate rather than absorbing it, so callers see ``drive`` never returns;
    the exit code is asserted to be ``0`` to pin the documented help-path code.
    """
    app = make_contract_app("novel")
    with pytest.raises(SystemExit) as exc_info:
        drive(app, ["--help"], command="novel", working_dir="/abs/working", human=False)
    assert exc_info.value.code == 0
