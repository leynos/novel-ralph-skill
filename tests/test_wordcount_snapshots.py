"""Snapshot and gate-boundary tests for the ``wordcount`` envelope (task 6.1.1).

These complete design §9's coverage for ``wordcount``: snapshot the machine-mode
JSON envelope for a representative drafting-era tree, paired with semantic
assertions so the snapshot is never the only guard (AGENTS.md "avoid snapshot-only
coverage"), and pin the gate-boundary examples the roadmap success criterion names
— a manuscript drafted to *exactly* each of the 30/50/80% gates, one *past* the
final gate, and a ``target == 0`` tree — plus the trigger-versus-flag distinction
(a tree whose drafted ratio crosses 30% but whose recorded ``done_30`` flag is
``false``). The snapshot is paired with the volatile-field guard and the
per-chapter-sums-to-current invariant.
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest

from novel_ralph_skill.commands._wordcount import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run
from novel_ralph_skill.state import GATE_THRESHOLDS

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from conftest import WorkingTreeSpec
    from syrupy.assertion import SnapshotAssertion

_COMMAND = "wordcount"

if typ.TYPE_CHECKING:

    class TreeAtRatio(typ.Protocol):
        """Materialise a drafting-era tree at a target/draft/gate shape."""

        def __call__(
            self,
            *,
            target: int,
            drafts: tuple[int, ...],
            gates: tuple[bool, bool, bool] = ...,
        ) -> Path:
            """Return the ``working/`` path of the materialised tree."""

    class RatioRunner(typ.Protocol):
        """Build a tree at a target/draft/gate shape, run ``wordcount``, return it."""

        def __call__(
            self,
            *,
            target: int,
            drafts: tuple[int, ...],
            gates: tuple[bool, bool, bool] = ...,
        ) -> tuple[int, dict[str, object]]:
            """Return ``(exit_code, envelope)`` for the materialised tree."""


def _result(envelope: dict[str, object]) -> dict[str, object]:
    """Return the ``result`` sub-mapping of ``envelope``."""
    return typ.cast("dict[str, object]", envelope["result"])


def _cumulative(envelope: dict[str, object]) -> dict[str, object]:
    """Return the ``result.cumulative`` block of ``envelope``."""
    return typ.cast("dict[str, object]", _result(envelope)["cumulative"])


# Matches the shapes that would churn a snapshot: an absolute or multi-segment
# path, an ISO-8601 date, or a clock time; modelled on the desloppify snapshot
# guard (``tests/test_desloppify_snapshots.py``).
_VOLATILE_PATTERN = re.compile(
    r"(?:^|[\"\s])/[^/\"\s]+"
    r"|/[^/\"\s]+/"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{2}:\d{2}:\d{2}"
)


def _assert_no_volatile_fields(envelope: dict[str, object]) -> None:
    """Assert the rendered envelope carries no timestamp or absolute path."""
    rendered = json.dumps(envelope)
    match = _VOLATILE_PATTERN.search(rendered)
    assert match is None, (
        f"unexpected volatile token {match.group()!r} in envelope: {rendered}"
        if match is not None
        else ""
    )
    for key in ("timestamp", "created_at", "now", "time"):
        assert key not in rendered, f"unexpected volatile key {key!r} in envelope"


@pytest.fixture
def build_at_ratio(
    make_working_tree_spec: cabc.Callable[..., WorkingTreeSpec],
    make_chapter_spec: cabc.Callable[..., object],
    build_tree: cabc.Callable[[WorkingTreeSpec, Path], Path],
    tmp_path: Path,
) -> TreeAtRatio:
    """Return a builder that materialises a drafting-era tree at a given shape.

    Bundling the three corpus builders and ``tmp_path`` into one fixture keeps the
    consuming fixture's parameter list within the project's argument-count gate
    (Pylint ``too-many-arguments``) while still delivering the build flow by
    fixture name. The returned callable takes the novel ``target``, the per-chapter
    ``drafts``, and the three recorded knitting-gate flags, and returns the
    materialised ``working/`` path.
    """

    def _build(
        *,
        target: int,
        drafts: tuple[int, ...],
        gates: tuple[bool, bool, bool] = (False, False, False),
    ) -> Path:
        """Materialise the tree at the given shape and return its ``working/``."""
        done_30, done_50, done_80 = gates
        chapters = tuple(
            make_chapter_spec(
                number=index + 1,
                slug=f"chapter-{index + 1:02d}",
                title=f"Chapter {index + 1}",
                target_words=target // len(drafts) if drafts else target,
                draft_words=words,
                has_done_flag=False,
            )
            for index, words in enumerate(drafts)
        )
        spec = make_working_tree_spec(
            phase_current="drafting",
            phase_completed=(),
            chapters=chapters,
            target_words=target,
            consecutive_clean=0,
            convergence_target=1,
            current_chapter=len(chapters),
            done_30=done_30,
            done_50=done_50,
            done_80=done_80,
        )
        return build_tree(spec, tmp_path)

    return _build


@pytest.fixture
def run_at_ratio(
    build_at_ratio: TreeAtRatio,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> RatioRunner:
    """Return a runner that materialises a tree at a ratio and runs ``wordcount``.

    Builds the tree via :func:`build_at_ratio`, runs the real ``wordcount`` app in
    its parent directory, and returns ``(exit_code, envelope)``.
    """

    def _run(
        *,
        target: int,
        drafts: tuple[int, ...],
        gates: tuple[bool, bool, bool] = (False, False, False),
    ) -> tuple[int, dict[str, object]]:
        """Materialise and run, returning ``(code, envelope)``."""
        working = build_at_ratio(target=target, drafts=drafts, gates=gates)
        monkeypatch.chdir(working.parent)
        with pytest.raises(SystemExit) as excinfo:
            run(
                build_app(),
                [],
                RunContext(command=_COMMAND, working_dir="working", human=False),
            )
        raw = capsys.readouterr().out
        return int(typ.cast("int", excinfo.value.code)), json.loads(raw)

    return _run


def test_representative_tree_envelope_snapshot(
    run_at_ratio: RatioRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """A representative drafting-era tree snapshots its whole-manuscript envelope.

    Paired with semantic guards: the per-chapter table sums to ``current``, the
    next-gate distance is non-negative, the triggers agree with the drafted ratio,
    and nothing volatile can silently churn the snapshot.
    """
    target = 20000
    drafts = (4000, 3000)
    code, envelope = run_at_ratio(
        target=target, drafts=drafts, gates=(True, False, False)
    )
    assert code == ExitCode.SUCCESS, f"expected exit 0, got {code}"
    assert envelope["ok"] is True, envelope
    cumulative = _cumulative(envelope)
    chapters = typ.cast("list[dict[str, int]]", _result(envelope)["chapters"])
    assert sum(row["words"] for row in chapters) == cumulative["current"]
    distance = cumulative["next_gate_distance"]
    assert distance is None or typ.cast("int", distance) >= 0, "distance non-negative"
    ratio = sum(drafts) / target
    assert cumulative["gate_triggered_30"] is (ratio >= GATE_THRESHOLDS[0])
    assert cumulative["gate_triggered_50"] is (ratio >= GATE_THRESHOLDS[1])
    _assert_no_volatile_fields(envelope)
    assert envelope == snapshot


@pytest.mark.parametrize(
    ("gate_index", "trigger_key", "next_threshold"),
    [
        (0, "gate_triggered_30", GATE_THRESHOLDS[1]),
        (1, "gate_triggered_50", GATE_THRESHOLDS[2]),
        (2, "gate_triggered_80", None),
    ],
)
def test_exactly_on_gate_boundary(
    gate_index: int,
    trigger_key: str,
    next_threshold: float | None,
    run_at_ratio: RatioRunner,
) -> None:
    """A tree drafted to exactly a gate reports it just reached, distance >= 0.

    Pins the §9 / roadmap success criterion and the A3 tie-break: at exactly 30%
    the 30% gate is reached and the *next* gate is 50% with a positive distance.
    """
    target = 10000
    drafted = round(GATE_THRESHOLDS[gate_index] * target)
    _code, envelope = run_at_ratio(target=target, drafts=(drafted,))
    cumulative = _cumulative(envelope)
    assert cumulative[trigger_key] is True, f"{trigger_key} must be just reached"
    assert cumulative["next_gate_threshold"] == next_threshold, cumulative
    if next_threshold is None:
        assert cumulative["next_gate_distance"] is None, cumulative
    else:
        distance = typ.cast("int", cumulative["next_gate_distance"])
        assert distance > 0, "next-gate distance is strictly positive between gates"


def test_past_final_gate_envelope(run_at_ratio: RatioRunner) -> None:
    """Past 80% the envelope carries ``null`` next-gate fields, never negative."""
    _code, envelope = run_at_ratio(target=10000, drafts=(9000,))
    cumulative = _cumulative(envelope)
    assert cumulative["gate_triggered_80"] is True, cumulative
    assert cumulative["next_gate_threshold"] is None, cumulative
    assert cumulative["next_gate_distance"] is None, cumulative


def test_target_zero_envelope(run_at_ratio: RatioRunner) -> None:
    """A ``target == 0`` tree short-circuits: no triggers, ``null`` geometry."""
    code, envelope = run_at_ratio(target=0, drafts=(0,))
    assert code == ExitCode.SUCCESS, f"expected exit 0, got {code}"
    cumulative = _cumulative(envelope)
    assert cumulative["percent_of_target"] is None, cumulative
    assert cumulative["gate_triggered_30"] is False, cumulative
    assert cumulative["next_gate_threshold"] is None, cumulative
    assert cumulative["next_gate_distance"] is None, cumulative


def test_trigger_distinct_from_recorded_flag(run_at_ratio: RatioRunner) -> None:
    """The report shows the derived trigger even when ``done_30`` is ``false``.

    A drafted ratio past 30% with the recorded ``done_30`` flag still ``false``
    (the knitting pass not yet integrated) must report ``gate_triggered_30: true``
    and never echo the recorded flag (ExecPlan "Triggers, not gate flags").
    """
    # 35% drafted crosses the 30% gate; the recorded done_30 flag stays false.
    _code, envelope = run_at_ratio(
        target=10000, drafts=(3500,), gates=(False, False, False)
    )
    cumulative = _cumulative(envelope)
    assert cumulative["gate_triggered_30"] is True, "the derived trigger is reached"
    # The report must not surface the recorded gate flag under any key.
    rendered = json.dumps(envelope)
    assert "done_30" not in rendered, "wordcount must not echo the recorded gate flag"
