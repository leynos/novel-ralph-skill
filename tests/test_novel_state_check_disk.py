"""Disk-aware behaviour, corpus agreement, and snapshots for ``check`` (2.3.2).

These pin the externally observable contract of the now disk-aware ``check``:

- a disk-evidence-stale tree exits ``4`` naming the disk-evidence invariant in
  ``result.violations`` and carries a ``result.reconciliation`` describing the
  action (``recount`` / ``refuse``);
- the whole-corpus agreement test pins the production union detector
  (``validate_state`` unioned with ``check_disk_evidence``) to the oracle's
  ``corpus_check`` verdict on every coherent tree and ``INCOHERENT_VARIANTS``
  member — the safety net under the twin predicates (mirroring
  ``test_validate_state_corpus.py::test_incoherent_agreement_restricted_to_owned``);
- ``check`` writes nothing on the disk-evidence path (the strengthened
  byte-for-byte tree-unchanged guard);
- machine-mode envelope snapshots for the headline ``recount`` tree and one
  refuse-class tree, each paired with a semantic assertion on the action name.

The command is driven through :func:`novel_ralph_skill.contract.runner.run` under
an explicit ``monkeypatch.chdir`` into the materialised fixture parent so the
default ``./working/`` resolves there. The corpus is taken by the sanctioned
``working_corpus as wc`` value import the other corpus suites use.
"""

from __future__ import annotations

import contextlib
import io
import json
import typing as typ

import pytest
from _state_corpus_support import load_succeeds

from novel_ralph_skill.commands.novel_state import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import (
    check_disk_evidence,
    load_state,
    validate_state,
)

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec
    from syrupy.assertion import SnapshotAssertion

_COMMAND = "novel-state"


def _drive_check(working: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[int, str]:
    """Run ``check`` from ``working.parent`` and return ``(exit_code, raw_stdout)``."""
    monkeypatch.chdir(working.parent)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), pytest.raises(SystemExit) as excinfo:
        run(
            build_app(),
            ["check"],
            RunContext(command=_COMMAND, working_dir="working", human=False),
        )
    return typ.cast("int", excinfo.value.code), stream.getvalue()


def _result(raw: str) -> dict[str, object]:
    """Return the ``result`` mapping from a captured machine envelope."""
    return typ.cast("dict[str, object]", json.loads(raw)["result"])


@pytest.mark.parametrize(
    "case",
    [
        ("done-flag-real-draft-undercount", "word-counts-match-drafts", "recount"),
        (
            "word-counts-cover-drafts-omits-drafted-chapter",
            "word-counts-cover-drafts",
            "recount",
        ),
        (
            "word-counts-cover-drafts-extra-table-key",
            "word-counts-cover-drafts",
            "recount",
        ),
        ("uncleared-pending-turn", "pending-turn-cleared", "complete-pending-turn"),
        ("done-flag-empty-draft", "done-flag-without-draft", "refuse"),
        # An ORPHAN directory still fires the bijection in every phase (ADR 009);
        # ``manifest-extra-entry`` (a manifest entry without a directory) is now
        # the drafting-relaxed case, proven exit-0 below.
        ("draft-without-manifest-entry", "manifest-disk-bijection", "refuse"),
        ("scene-cursor-without-plan", "cursor-plan-present", "refuse"),
        ("partial-init", "log-present", "recreate-log"),
    ],
)
def test_disk_evidence_tree_exits_four_with_reconciliation(
    case: tuple[str, str, str],
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A disk-evidence tree exits ``4`` naming the invariant and the reconciliation."""
    variant, invariant, action = case
    _spec, working, _expected = incoherent_tree(variant)
    code, raw = _drive_check(working, monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING, variant
    result = _result(raw)
    assert invariant in typ.cast("list[str]", result["violations"]), variant
    reconciliation = typ.cast("dict[str, object]", result["reconciliation"])
    assert reconciliation["action"] == action, variant
    assert invariant in typ.cast("list[str]", reconciliation["discrepancies"]), variant


def test_drafting_manifest_subset_exits_zero_through_check(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drafting tree whose disk is a manifest subset exits ``0`` (ADR 009).

    ``manifest-extra-entry`` is a drafting-phase tree with a manifest entry whose
    directory is absent (the missing-directory direction). The user-facing
    ``check`` relaxes this to disk-subset-of-manifest during drafting, so the tree
    exits ``0`` and, because the disk-evidence verdict is empty, carries no
    ``reconciliation`` key. The strict detector still fires it (proven by
    ``test_union_detector_agrees_with_corpus_oracle`` and ``test_disk_evidence``).
    """
    _spec, working, _expected = incoherent_tree("manifest-extra-entry")
    code, raw = _drive_check(working, monkeypatch)
    assert code == ExitCode.SUCCESS
    result = _result(raw)
    assert result["violations"] == []
    assert "reconciliation" not in result


def test_coherent_tree_carries_no_reconciliation(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A coherent tree exits ``0`` with no ``reconciliation`` key in ``result``."""
    code, raw = _drive_check(baseline_tree(), monkeypatch)
    assert code == ExitCode.SUCCESS
    result = _result(raw)
    assert result["violations"] == []
    assert "reconciliation" not in result


def test_check_writes_nothing_on_disk_evidence_path(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``check`` leaves the tree byte-for-byte unchanged on a disk-evidence exit-4.

    The strengthened ``test_check_writes_nothing`` guard for the §5.4 path: even
    when ``check`` derives and reports a reconciliation, it enacts nothing (design
    §3.3; the Constraint that ``check`` is strictly read-only).
    """
    _spec, working, _expected = incoherent_tree("done-flag-real-draft-undercount")
    before = {
        path: path.read_bytes() for path in sorted(working.rglob("*")) if path.is_file()
    }
    code, _raw = _drive_check(working, monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING
    after = {
        path: path.read_bytes() for path in sorted(working.rglob("*")) if path.is_file()
    }
    assert after == before


def test_union_detector_agrees_with_corpus_oracle(
    coherent_oracle_cases: list[tuple[WorkingTreeSpec, Path]],
    incoherent_variant_names: tuple[str, ...],
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
) -> None:
    """The production union detector equals the oracle's verdict on every tree.

    For every coherent tree and every ``INCOHERENT_VARIANTS`` member, the union of
    ``validate_state`` and ``check_disk_evidence`` returns exactly the oracle's
    ``corpus_check`` verdict, restricted to the full corpus vocabulary. This is the
    safety net pinning the twin predicates (Work item 3 headline).
    """
    cases: list[tuple[WorkingTreeSpec, Path]] = list(coherent_oracle_cases)
    for name in incoherent_variant_names:
        spec, working, _expected = incoherent_tree(name)
        cases.append((spec, working))
    for spec, working in cases:
        oracle = set(check_corpus(spec, working))
        if not load_succeeds(working):
            # A parse-rejected tree (``phase-not-in-enum``): the oracle's owned
            # label is parser-enforced upstream, so the union detector never runs.
            continue
        state = load_state(working / "state.toml")
        production = {v.invariant for v in validate_state(state)} | {
            v.invariant for v in check_disk_evidence(state, working)
        }
        assert production == oracle, working


def test_log_present_twin_agreement_over_partial_init_tree(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    check_corpus: cabc.Callable[[WorkingTreeSpec, Path], tuple[str, ...]],
) -> None:
    """Production and oracle agree on ``log-present`` over the log-absent tree.

    The spec-built agreement loop above never reaches ``log-present``: every
    spec-built tree has ``log.md`` (the builder always writes it), so the only way
    to a log-absent tree is the ``partial-init`` post-build mutation. This pins the
    twin agreement directly for the one invariant the spec-built corpus cannot
    express (roadmap task 2.3.4): both the production ``check_disk_evidence`` and
    the oracle ``corpus_check`` fire ``log-present`` and agree on this tree.
    """
    spec, working, _expected = incoherent_tree("partial-init")
    production = {
        v.invariant
        for v in check_disk_evidence(load_state(working / "state.toml"), working)
    }
    oracle = set(check_corpus(spec, working))
    assert "log-present" in production, "production must fire log-present"
    assert "log-present" in oracle, "the oracle must fire log-present"
    assert production == oracle, (
        "production and oracle must agree on the log-absent tree"
    )


def test_recount_envelope_snapshot(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin the headline ``recount`` envelope; pair the snapshot with the action."""
    _spec, working, _expected = incoherent_tree("done-flag-real-draft-undercount")
    code, raw = _drive_check(working, monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING
    reconciliation = typ.cast("dict[str, object]", _result(raw)["reconciliation"])
    assert reconciliation["action"] == "recount"
    assert raw == snapshot


def test_refuse_envelope_snapshot(
    incoherent_tree: cabc.Callable[[str], tuple[WorkingTreeSpec, Path, str]],
    monkeypatch: pytest.MonkeyPatch,
    snapshot: SnapshotAssertion,
) -> None:
    """Pin a refuse-class envelope; pair the snapshot with the action."""
    _spec, working, _expected = incoherent_tree("done-flag-empty-draft")
    code, raw = _drive_check(working, monkeypatch)
    assert code == ExitCode.ACTIONABLE_FINDING
    reconciliation = typ.cast("dict[str, object]", _result(raw)["reconciliation"])
    assert reconciliation["action"] == "refuse"
    assert raw == snapshot
