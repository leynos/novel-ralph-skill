"""Cross-check, idempotence, and self-recovery for ``reconcile`` (2.3.2, Work item 6).

These pin the integration-level guarantees of the ``check``/``reconcile`` pair:

- **cross-check** (D-SHARED): on every corpus tree the ``ReconcileAction`` ``check``
  reports equals the action ``reconcile`` enacts, so the two cannot drift;
- **idempotence**: a second ``reconcile`` over an already-reconciled tree is a
  ``none`` no-op (exit ``0``, ``state.toml`` byte-for-byte unchanged) and a second
  ``check`` exits ``0``;
- **self-recovery** (D-SELF): an interruption inside the manual bracket — after the
  intent record is written but before the bracket clears — leaves a populated
  ``operation="reconcile"`` ``[pending_turn]`` on disk, and a subsequent
  ``reconcile`` re-derives and finishes the repair, even when the interruption
  falls *after* the ``log.md`` receipt is appended (the receipt-loss window the
  round-1 plan opened is closed).

The corpus is taken by the sanctioned ``working_corpus as wc`` value import; the
commands are driven through :func:`novel_ralph_skill.contract.runner.run` and the
``reconcile`` body is also called directly for the self-recovery seam.
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
import working_corpus as wc
from _state_corpus_support import load_succeeds

from novel_ralph_skill.commands import _reconcile
from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import (
    derive_reconciliation,
    load_state,
)

if typ.TYPE_CHECKING:
    from pathlib import Path

_COMMAND = "novel-state"

# The four word-count/pending-turn variants plus every other materialising tree
# exercise the full cross-check; the coherent baseline anchors the NONE path.
# ``manifest-extra-entry`` is excluded: it is a drafting-phase missing-directory
# subset the user-facing ``check`` now relaxes (ADR 009 / D1), so ``check`` reports
# ``none`` while the strict ``derive_reconciliation`` that ``reconcile`` runs still
# REFUSEs — the deliberate strict/relaxed split, pinned by
# ``test_relaxed_check_and_strict_reconcile_split`` below rather than this
# action-agreement loop.
_CROSS_CHECK_VARIANTS: tuple[str, ...] = tuple(
    name for name in wc.INCOHERENT_VARIANTS if name != "manifest-extra-entry"
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


def _check_reported_action(working: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Return the reconciliation action ``check`` reports (``none`` when absent)."""
    _code, env = _drive(working, "check", monkeypatch)
    result = typ.cast("dict[str, object]", env["result"])
    if "reconciliation" not in result:
        return "none"
    reconciliation = typ.cast("dict[str, object]", result["reconciliation"])
    return typ.cast("str", reconciliation["action"])


@pytest.mark.parametrize("variant", _CROSS_CHECK_VARIANTS)
def test_check_and_reconcile_actions_agree(
    variant: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The action ``check`` reports equals the action ``reconcile`` enacts (D-SHARED).

    Both call the same ``derive_reconciliation``; this pins that ``check``'s reported
    action and ``reconcile``'s enacted action are the same on every materialising
    variant (the parse-rejected ``phase-not-in-enum`` tree never reaches either).
    """
    working = wc.build_working_tree(wc.INCOHERENT_VARIANTS[variant][0], tmp_path)
    if not load_succeeds(working):
        pytest.skip("parse-rejected tree never reaches the reconciliation")

    state = load_state(working / "state.toml")
    expected = str(derive_reconciliation(state, working).action)

    assert _check_reported_action(working, monkeypatch) == expected, variant

    _code, reconcile_env = _drive(working, "reconcile", monkeypatch)
    enacted = typ.cast("dict[str, object]", reconcile_env["result"])["action"]
    assert enacted == expected, variant


def test_relaxed_check_and_strict_reconcile_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``check`` relaxes the drafting subset while ``reconcile`` stays strict (D1).

    ``manifest-extra-entry`` is a drafting-phase tree with a manifest entry whose
    directory is absent — the missing-directory direction the user-facing ``check``
    now relaxes (ADR 009). So ``check`` exits ``0`` and reports ``none`` (no
    reconciliation), while the strict ``derive_reconciliation`` that ``reconcile``
    runs still REFUSEs (exit ``4``). This is the deliberate strict/relaxed split the
    action-agreement loop excludes; it pins that the relaxation did not leak into
    ``reconcile``.
    """
    working = wc.build_working_tree(
        wc.INCOHERENT_VARIANTS["manifest-extra-entry"][0], tmp_path
    )
    state = load_state(working / "state.toml")
    assert str(derive_reconciliation(state, working).action) == "refuse"

    check_code, _check_env = _drive(working, "check", monkeypatch)
    assert check_code == ExitCode.SUCCESS
    assert _check_reported_action(working, monkeypatch) == "none"

    reconcile_code, reconcile_env = _drive(working, "reconcile", monkeypatch)
    assert reconcile_code == ExitCode.ACTIONABLE_FINDING
    enacted = typ.cast("dict[str, object]", reconcile_env["result"])["action"]
    assert enacted == "refuse"


def test_second_reconcile_is_a_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second ``reconcile`` over a repaired tree is a ``none`` no-op write."""
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    first_code, _first = _drive(working, "reconcile", monkeypatch)
    assert first_code == ExitCode.SUCCESS

    before = (working / "state.toml").read_bytes()
    second_code, second_env = _drive(working, "reconcile", monkeypatch)
    assert second_code == ExitCode.SUCCESS
    assert typ.cast("dict[str, object]", second_env["result"])["action"] == "none", (
        "a second reconcile must be a no-op"
    )
    assert (working / "state.toml").read_bytes() == before, (
        "a second reconcile must leave state.toml byte-for-byte unchanged"
    )

    recheck_code, _recheck = _drive(working, "check", monkeypatch)
    assert recheck_code == ExitCode.SUCCESS, "the reconciled tree must re-check clean"


def test_interrupted_reconcile_leaves_recoverable_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An interruption after the receipt but before the clear is recoverable (D-SELF).

    The receipt-loss window the round-1 plan opened is closed: an exception raised
    *after* the ``log.md`` receipt is appended but *before* the bracket clears leaves
    a populated ``operation="reconcile"`` ``[pending_turn]`` on disk — a *recoverable*
    torn turn, not a corrupted state — and repeated ``reconcile`` runs (the harness
    re-entry model) re-derive and converge the tree to coherence. An interrupted
    ``RECOUNT`` converges in two passes: the first recovery clears the leftover
    record, the second re-applies the still-pending recount, mirroring the harness's
    idempotent re-entry until ``check`` reports clean.
    """
    spec, _expected = wc.INCOHERENT_VARIANTS["done-claim-stale-word-counts"]
    working = wc.build_working_tree(spec, tmp_path)
    monkeypatch.chdir(working.parent)

    class _CrashError(RuntimeError):
        """Sentinel raised to simulate a crash after the receipt is appended."""

    real_append = _reconcile._append_recovery_entry

    def _append_then_crash(working_dir: Path, line: str) -> None:
        """Append the receipt (as production does) then raise, simulating a crash."""
        real_append(working_dir, line)
        raise _CrashError

    monkeypatch.setattr(_reconcile, "_append_recovery_entry", _append_then_crash)
    with pytest.raises(_CrashError):
        _reconcile.reconcile()

    # The intent record survived with reconcile's own operation: a recoverable torn
    # turn, not a corrupted state.
    interrupted = load_state(working / "state.toml")
    assert interrupted.pending_turn is not None, (
        "the interrupted reconcile must leave a populated pending_turn record"
    )
    assert interrupted.pending_turn.operation == "reconcile", (
        "the leftover record must name reconcile as the in-flight operation"
    )

    # Fresh reconcile runs (production behaviour restored) converge the tree, the
    # harness re-entry model: clear the leftover record, then re-apply the recount.
    # The bound (range(3)) is a safety net against an infinite loop; convergence
    # must take *exactly* two passes, so a regression that silently needs more
    # re-entry passes is pinned, not masked by the bound.
    monkeypatch.setattr(_reconcile, "_append_recovery_entry", real_append)
    passes = 0
    for _attempt in range(3):
        code, _env = _drive(working, "reconcile", monkeypatch)
        passes += 1
        assert code == ExitCode.SUCCESS, "each recovery reconcile must exit 0"
        if _drive(working, "check", monkeypatch)[0] == ExitCode.SUCCESS:
            break
    else:
        pytest.fail("repeated reconcile did not converge the interrupted tree")
    assert passes == 2, (
        f"the interrupted recount must converge in exactly two passes, took {passes}"
    )

    recovered = load_state(working / "state.toml")
    assert recovered.pending_turn is None, "the recovered tree must be settled"
