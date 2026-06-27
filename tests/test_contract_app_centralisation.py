"""Structural tripwire that the real surface consumes the contract factory.

The four production ``build_app`` constructors (``novel-state``,
``novel-done``, ``novel-compile``, ``desloppify``) and the sole ``novel``
console-script entry point are required to route through the centralised
:func:`~novel_ralph_skill.contract.runner.make_contract_app` factory and the
shared :func:`~novel_ralph_skill.contract.runner.run` seam (roadmap task 1.3.6,
review:1.3.6 and audit:1.3.6 Finding 3). Existing coverage proves this only
indirectly — the console-scripts end-to-end suite and the per-command suites
exercise behaviour, so a future edit re-inlining a bare ``cyclopts.App`` in one
``build_app()`` or re-inlining the ``parse_global_flags``/``run`` plumbing in the
entry point would still pass every existing test.

This module is the cheap structural guard the factory makes possible. It pins
two halves of the 1.3.6 success criterion directly:

(a) each production ``build_app`` callable returns an app carrying the four-flag
    contract (``result_action``, ``exit_on_error``, ``print_error``,
    ``help_on_error``) in their cyclopts 4.18.0 normalised forms; and
(b) the real ``novel`` entry point routes the multiplexer through the
    contract-level :func:`~novel_ralph_skill.contract.runner.drive` seam, which
    forwards to the shared ``run`` seam (roadmap task 7.3.5). This is confirmed
    by monkeypatching :func:`~novel_ralph_skill.commands.novel.drive` and
    observing that :func:`~novel_ralph_skill.commands.novel.main` invokes it with
    a four-flag-contract ``build_multiplexer()`` app (Decision Log D2 — re-homed
    from the deleted legacy entry points onto the surviving multiplexer, then
    re-homed again from ``run`` onto ``drive`` by 7.3.5). This is the
    *entry-point half* of the ``main -> drive -> run`` transitive invariant; the
    *seam half* (``drive`` forwards to ``run``) is proven by
    ``tests/test_contract_drive_seam.py``.
"""

from __future__ import annotations

import typing as typ

import cyclopts
import pytest

from novel_ralph_skill.commands import novel

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def _real_build_apps() -> tuple[tuple[str, cabc.Callable[[], cyclopts.App]], ...]:
    """Return ``(name, build_app)`` for the four production constructors.

    Imported lazily inside the helper so the deferred-import discipline the
    entry point keeps (audit-3.1.1 Finding 4) is mirrored here rather than
    forcing every command module to import at collection time. The ``name`` is
    the leaf app's own cyclopts label (a production-module concern unchanged by
    the multiplexer migration), not an envelope ``command`` stamp.
    """
    from novel_ralph_skill.commands import (
        _compile,
        _desloppify,
        _novel_done,
        novel_state,
    )

    return (
        ("novel-state", novel_state.build_app),
        ("novel-done", _novel_done.build_app),
        ("novel-compile", _compile.build_app),
        ("desloppify", _desloppify.build_app),
    )


_REAL_BUILD_APPS = _real_build_apps()


def _assert_four_flag_contract(app: cyclopts.App) -> None:
    """Assert ``app`` carries the four-flag contract in its normalised forms.

    cyclopts 4.18.0 tuple-wraps ``result_action`` on construction but leaves the
    three boolean flags as plain ``False``; the factory test pins these forms
    against :func:`~novel_ralph_skill.contract.runner.make_contract_app` and they
    are reused here so a re-inlined bare ``cyclopts.App`` is caught.
    """
    assert app.result_action == ("return_value",)
    assert app.exit_on_error is False
    assert app.print_error is False
    assert app.help_on_error is False


@pytest.mark.parametrize(
    ("name", "build_app"),
    _REAL_BUILD_APPS,
    ids=[name for name, _ in _REAL_BUILD_APPS],
)
def test_real_build_app_carries_the_four_flag_contract(
    name: str,
    build_app: cabc.Callable[[], cyclopts.App],
) -> None:
    """Each production ``build_app`` returns a four-flag-contract app (half a)."""
    app = build_app()
    assert isinstance(app, cyclopts.App)
    assert app.name == (name,)
    _assert_four_flag_contract(app)


def test_novel_entry_point_routes_through_the_shared_seam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``novel`` entry point drives the multiplexer through ``drive`` (half b).

    The contract-level :func:`~novel_ralph_skill.contract.runner.drive` seam is
    monkeypatched on the ``novel`` module so it captures the app it is handed
    rather than exiting the process. A re-inlined entry point that bypassed the
    seam would never reach it, failing the ``invoked`` assertion; one that
    bypassed ``make_contract_app`` would hand over a parent app without the
    four-flag contract, failing :func:`_assert_four_flag_contract`.

    This pins the entry-point half of the ``main -> drive -> run`` transitive
    invariant. The seam half (``drive`` forwards to ``run``) is proven by
    ``tests/test_contract_drive_seam.py``.
    """
    captured: dict[str, object] = {}

    def _capture_drive(  # pylint: disable=too-many-arguments
        app: cyclopts.App,
        argv: cabc.Sequence[str],
        *,
        command: str,
        working_dir: str,
        human: bool,
    ) -> None:
        """Capture ``drive``'s arguments instead of exiting the process."""
        captured["app"] = app
        captured["argv"] = list(argv)
        captured["command"] = command
        captured["working_dir"] = working_dir
        captured["human"] = human

    monkeypatch.setattr(novel, "drive", _capture_drive)
    # Pin a clean, no-argument argv so ``parse_global_flags`` has a stable input
    # and the residual argv reaching the captured seam is empty.
    monkeypatch.setattr("sys.argv", ["novel"])

    novel.main()

    assert "app" in captured, "novel did not route through the shared drive seam"
    app = captured["app"]
    assert isinstance(app, cyclopts.App)
    assert app.name == ("novel",)
    _assert_four_flag_contract(app)
    assert captured["argv"] == []
