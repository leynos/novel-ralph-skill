"""Structural tripwire that the four real commands consume the contract factory.

The four production ``build_app`` constructors (``novel-state``,
``novel-done``, ``novel-compile``, ``desloppify``) and their four console-script
entry points are required to route through the centralised
:func:`~novel_ralph_skill.contract.runner.make_contract_app` factory and the
shared :func:`~novel_ralph_skill.commands.stub._drive`/
:func:`~novel_ralph_skill.contract.runner.run` seam (roadmap task 1.3.6,
review:1.3.6 and audit:1.3.6 Finding 3). Existing coverage proves this only
indirectly — the console-scripts end-to-end suite and the per-command suites
exercise behaviour, so a future edit re-inlining a bare ``cyclopts.App`` in one
``build_app()`` or re-inlining the ``parse_global_flags``/``run`` plumbing in one
entry point would still pass every existing test.

This module is the cheap structural guard the factory makes possible. It pins
two halves of the 1.3.6 success criterion directly:

(a) each production ``build_app`` callable returns an app carrying the four-flag
    contract (``result_action``, ``exit_on_error``, ``print_error``,
    ``help_on_error``) in their cyclopts 4.18.0 normalised forms; and
(b) each real entry point routes through the shared ``_drive``/``run`` seam,
    confirmed by monkeypatching :func:`~novel_ralph_skill.commands.stub.run` and
    observing that every entry point invokes it with a four-flag-contract app.
"""

from __future__ import annotations

import sys
import typing as typ

import cyclopts
import pytest

from novel_ralph_skill.commands import stub

if typ.TYPE_CHECKING:
    import collections.abc as cabc


def _real_build_apps() -> tuple[tuple[str, cabc.Callable[[], cyclopts.App]], ...]:
    """Return ``(name, build_app)`` for the four production constructors.

    Imported lazily inside the helper so the deferred-import discipline the
    entry points keep (audit-3.1.1 Finding 4) is mirrored here rather than
    forcing every command module to import at collection time.
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


# The four real console-script entry points (``wordcount`` stays a stub and is
# excluded — it never drives a contract app). Each is the ``stub`` attribute the
# ``[project.scripts]`` table targets.
_REAL_ENTRY_POINTS: tuple[tuple[str, cabc.Callable[[], None]], ...] = (
    ("novel-state", stub.novel_state),
    ("novel-done", stub.novel_done),
    ("novel-compile", stub.novel_compile),
    ("desloppify", stub.desloppify),
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


@pytest.mark.parametrize(
    ("name", "entry_point"),
    _REAL_ENTRY_POINTS,
    ids=[name for name, _ in _REAL_ENTRY_POINTS],
)
def test_real_entry_point_routes_through_the_shared_seam(
    name: str,
    entry_point: cabc.Callable[[], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each real entry point drives its app through ``_drive``/``run`` (half b).

    The shared :func:`~novel_ralph_skill.contract.runner.run` seam is monkeypatched
    on the ``stub`` module so it captures the app it is handed rather than exiting
    the process. A re-inlined entry point that bypassed ``_drive`` would never
    reach this seam, failing the ``invoked`` assertion; one that bypassed
    ``make_contract_app`` would hand over an app without the four-flag contract,
    failing :func:`_assert_four_flag_contract`.
    """
    captured: dict[str, object] = {}

    def _capture_run(
        app: cyclopts.App,
        argv: cabc.Sequence[str],
        context: object,
    ) -> None:
        """Capture ``run``'s arguments instead of exiting the process."""
        captured["app"] = app
        captured["argv"] = list(argv)
        captured["context"] = context

    monkeypatch.setattr(stub, "run", _capture_run)
    # Pin a clean, no-argument argv so ``parse_global_flags`` has a stable input
    # and the residual argv reaching the captured seam is empty.
    monkeypatch.setattr(sys, "argv", [name])

    entry_point()

    assert "app" in captured, f"{name} did not route through the shared run seam"
    app = captured["app"]
    assert isinstance(app, cyclopts.App)
    assert app.name == (name,)
    _assert_four_flag_contract(app)
    assert captured["argv"] == []
