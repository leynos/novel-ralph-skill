"""Bind the @slow, POSIX-only installed per-chapter loop scenario (roadmap 6.2.2).

This is the installed-binary half of the per-chapter loop: it re-drives the
clean pass and the stale-compile catch through the built wheel's console-scripts,
proving the harness-trusted exit codes at the real packaging boundary (design §9
lines 835-847; ADR-003; ADR-006). It lives in its **own** feature and binder,
separate from the cross-platform in-process scenarios, so the POSIX skip and the
180s timeout attach only here and cannot leak onto the in-process scenarios
(ExecPlan Decision D-INSTALLED-SPLIT).

The scenario is bound with the ``pytest_bdd.scenario(...)`` **decorator** rather
than a bare ``scenarios(...)`` call: a function decorated with ``@scenario``
"behaves like a normal test function" (pytest-bdd 8.1.0 docs), so the stacked
``@pytest.mark.*`` decorators attach to the produced test item exactly as on a
plain pytest function, the same mechanism ``tests/test_console_scripts_e2e.py``
and ``tests/test_recount_e2e.py`` use. ``@pytest.mark.timeout(180)`` supersedes
the global ini ``timeout = 30`` for this slow wheel-build item (pytest-timeout
2.4.0 marker priority). The import root is ``steps.<module>``, not
``tests.steps.<module>`` (ExecPlan advisory A2).
"""

from __future__ import annotations

import os
import typing as typ

import pytest
from pytest_bdd import scenario
from steps.per_chapter_loop_installed_steps import *  # noqa: F403 - register steps

if typ.TYPE_CHECKING:
    import collections.abc as cabc

_REQUIRED_MARKS = frozenset({"slow", "timeout", "skipif"})


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.skipif(
    os.name != "posix",
    reason="installed loop e2e is POSIX-only; see ADR 006",
)
@scenario(
    "features/per_chapter_loop_installed.feature",
    "the installed loop passes clean and catches a stale compile",
)
def test_installed_per_chapter_loop() -> None:
    """Bind the installed loop scenario, carrying the slow/timeout/POSIX marks."""


@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.skipif(
    os.name != "posix",
    reason="installed loop e2e is POSIX-only; see ADR 006",
)
@scenario(
    "features/per_chapter_loop_installed.feature",
    "the installed loop refuses an out-of-order advance-phase",
)
def test_installed_advance_phase_refused() -> None:
    """Bind the installed refused-advance scenario, carrying the same three marks.

    This closes audit-6.2.2 Finding 7: the runner-stamped exit-3 refusal of an
    out-of-order ``advance-phase`` (design §3.2, §4.1) is now proven over the real
    installed console-script, not only in-process. The module-scoped
    ``installed_novel_state`` fixture means this scenario reuses the same wheel
    build and venv install as the clean-pass scenario, so no second wheel is built.
    """


def test_installed_scenario_carries_marks() -> None:
    """Guard that the installed scenario keeps its slow, timeout, and POSIX marks.

    A future edit that drops a mark would silently weaken the installed boundary —
    running the wheel build on a non-POSIX leg, or under the global 30s timeout
    rather than the 180s budget — with no test failing. Reading the stacked marks
    off the bound function's ``pytestmark`` list (where ``@pytest.mark.*``
    decorators accumulate) makes such a drop fail this named, wheel-free guard
    instead (ExecPlan Risk "installed scenario silently loses its marks"). The
    function's ``pytestmark`` attribute is used rather than a collected ``Item``'s
    ``iter_markers`` because this plain sibling test has no handle on the other
    test's collected item; the attribute is the documented accrual point for
    stacked decorators and is read identically on every platform.
    """
    # ``pytestmark`` is attached dynamically by the stacked ``@pytest.mark.*``
    # decorators, so the static checker cannot see it; read it through ``getattr``
    # with the documented ``list[pytest.MarkDecorator]`` shape.
    applied = typ.cast(
        "cabc.Sequence[pytest.MarkDecorator]",
        getattr(test_installed_per_chapter_loop, "pytestmark", ()),
    )
    marks = {mark.name for mark in applied}
    assert marks >= _REQUIRED_MARKS, (
        f"the installed scenario must keep {sorted(_REQUIRED_MARKS)}; "
        f"got {sorted(marks)}"
    )


def test_installed_advance_refused_carries_marks() -> None:
    """Guard that the refused-advance scenario keeps its slow/timeout/POSIX marks.

    Mirrors ``test_installed_scenario_carries_marks`` for the second installed
    scenario (roadmap 6.2.9). Dropping a mark from ``test_installed_advance_phase_
    refused`` would run its wheel build on a non-POSIX leg or under the global 30s
    timeout rather than the 180s budget, with no scenario failing; this wheel-free
    guard, read off the bound function's ``pytestmark``, fails instead (ExecPlan
    Risk 1). It runs on every platform.
    """
    applied = typ.cast(
        "cabc.Sequence[pytest.MarkDecorator]",
        getattr(test_installed_advance_phase_refused, "pytestmark", ()),
    )
    marks = {mark.name for mark in applied}
    assert marks >= _REQUIRED_MARKS, (
        f"the refused-advance scenario must keep {sorted(_REQUIRED_MARKS)}; "
        f"got {sorted(marks)}"
    )
