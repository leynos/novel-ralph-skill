"""Refuse-class handling in ``check`` and ``reconcile`` (roadmap 2.3.2, Work item 5).

These finalise the ``REFUSE`` path (D-REPORT — the single action both the three
§5.4 contradictions and the reported-not-repaired ``cursor-plan-present`` map to):

- every refuse-class variant exits ``4`` in **both** commands with action
  ``refuse``;
- ``reconcile`` on a refuse-class tree leaves ``state.toml`` byte-for-byte
  unchanged but appends a ``refuse`` receipt to ``log.md``;
- a ``scene-cursor-without-plan`` tree carries a ``refuse`` reconciliation (never
  ``none``) and ``reconcile`` exits ``4`` (never ``0``) — the round-2
  blocking-point-4 regression guard;
- a machine-envelope snapshot of the refuse path, paired with a semantic action
  assertion.

The corpus is taken by the sanctioned ``working_corpus as wc`` value import; both
commands are driven through :func:`novel_ralph_skill.contract.runner.run` under an
explicit ``monkeypatch.chdir``.
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    from pathlib import Path

    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel state"

# The refuse-class variants that exit 4 with action ``refuse`` in BOTH commands.
# ``manifest-extra-entry`` (a drafting missing-directory subset) is deliberately
# excluded: the user-facing ``check`` now relaxes it to exit 0 (ADR 009 / D1) while
# ``reconcile`` still REFUSEs, so it is no longer a both-commands refuse — that
# split is pinned by ``test_manifest_extra_entry_reconcile_still_refuses`` below and
# by ``test_reconcile_integration.test_relaxed_check_and_strict_reconcile_split``.
# The orphan ``draft-without-manifest-entry`` keeps the bijection refuse-class
# coverage for both commands.
_REFUSE_VARIANTS: tuple[str, ...] = (
    "done-flag-empty-draft",
    "done-flag-absent-draft",
    "compiled-not-concatenation-of-drafts",
    "draft-without-manifest-entry",
    "scene-cursor-without-plan",
    "beat-cursor-without-plan",
)


def _drive(
    working: Path, command: str, monkeypatch: pytest.MonkeyPatch
) -> tuple[int, dict[str, object]]:
    """Run ``command`` from ``working.parent`` and return ``(exit_code, envelope)``."""
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            [command],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), json.loads(stream.getvalue() or "{}")


def _action(envelope: dict[str, object], *, from_check: bool) -> object:
    """Return the reconciliation/refusal action from a captured envelope.

    ``check`` nests the action under ``result.reconciliation.action``;
    ``reconcile`` reports it directly as ``result.action``.
    """
    result = typ.cast("dict[str, object]", envelope["result"])
    if from_check:
        reconciliation = typ.cast("dict[str, object]", result["reconciliation"])
        return reconciliation["action"]
    return result["action"]


@pytest.mark.parametrize("variant", _REFUSE_VARIANTS)
def test_refuse_class_exits_four_in_both_commands(
    variant: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refuse-class tree exits ``4`` with action ``refuse`` in check and reconcile."""
    spec, _expected = wc.INCOHERENT_VARIANTS[variant]
    working = wc.build_working_tree(spec, tmp_path)

    check_code, check_env = _drive(working, "check", monkeypatch)
    assert check_code == ExitCode.ACTIONABLE_FINDING, variant
    assert _action(check_env, from_check=True) == "refuse", variant

    reconcile_code, reconcile_env = _drive(working, "reconcile", monkeypatch)
    assert reconcile_code == ExitCode.ACTIONABLE_FINDING, variant
    assert _action(reconcile_env, from_check=False) == "refuse", variant


@pytest.mark.parametrize("variant", _REFUSE_VARIANTS)
def test_reconcile_refuse_leaves_state_and_logs_refusal(
    variant: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``reconcile`` on a refuse tree keeps ``state.toml`` and logs ``refuse``."""
    spec, _expected = wc.INCOHERENT_VARIANTS[variant]
    working = wc.build_working_tree(spec, tmp_path)
    before = (working / "state.toml").read_bytes()

    code, _env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING, variant

    assert (working / "state.toml").read_bytes() == before, (
        "reconcile must leave state.toml byte-for-byte unchanged on a refusal"
    )
    assert "refuse" in (working / "log.md").read_text(encoding="utf-8"), (
        "reconcile must append a refuse receipt to log.md"
    )


def test_manifest_extra_entry_reconcile_still_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``reconcile`` still REFUSEs the drafting missing-directory subset (ADR 009 / D1).

    The user-facing ``check`` relaxes ``manifest-extra-entry`` (exit 0), but
    ``reconcile`` reads the strict bijection, so it exits 4 with action ``refuse``,
    leaves ``state.toml`` byte-for-byte unchanged, and logs the refusal. This pins
    that the relaxation is scoped to ``check`` and never weakens the reconcile path.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["manifest-extra-entry"]
    working = wc.build_working_tree(spec, tmp_path)
    before = (working / "state.toml").read_bytes()

    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert _action(env, from_check=False) == "refuse"
    assert (working / "state.toml").read_bytes() == before, (
        "reconcile must leave state.toml byte-for-byte unchanged on a refusal"
    )
    assert "refuse" in (working / "log.md").read_text(encoding="utf-8")


def test_cursor_plan_present_never_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``scene-cursor-without-plan`` tree refuses, never ``none`` (round-2 guard).

    The round-2 blocking-point-4 regression guard: ``cursor-plan-present`` maps to
    ``REFUSE`` (exit 4), never falling through to ``NONE`` (exit 0) while ``check``
    exits 4. So ``check``'s exit-4 payload carries a ``refuse`` reconciliation and
    ``reconcile`` exits 4, never 0.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["scene-cursor-without-plan"]
    working = wc.build_working_tree(spec, tmp_path)

    check_code, check_env = _drive(working, "check", monkeypatch)
    assert check_code == ExitCode.ACTIONABLE_FINDING
    assert _action(check_env, from_check=True) == "refuse"

    reconcile_code, reconcile_env = _drive(working, "reconcile", monkeypatch)
    assert reconcile_code == ExitCode.ACTIONABLE_FINDING
    assert _action(reconcile_env, from_check=False) == "refuse"


def test_reconcile_refuse_envelope_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin the ``reconcile`` refuse envelope; pair the snapshot with the action."""
    spec, _expected = wc.INCOHERENT_VARIANTS["done-flag-empty-draft"]
    working = wc.build_working_tree(spec, tmp_path)
    code, env = _drive(working, "reconcile", monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING
    assert _action(env, from_check=False) == "refuse"
    assert json.dumps(env, sort_keys=True) == snapshot
