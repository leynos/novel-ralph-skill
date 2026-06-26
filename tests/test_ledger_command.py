"""In-process behavioural tests for ``desloppify --ledger`` (roadmap 7.1.2).

These drive the real ``desloppify`` Cyclopts app through the shared
:func:`novel_ralph_skill.contract.runner.run` wrapper, mirroring
``tests/test_desloppify_command.py`` (``monkeypatch.chdir`` into a materialised
``working/`` parent, ``capsys`` to read the emitted envelope). They pin the
observable exit-code outcomes of the ledger mode (design §6.3, §3.2): an
over-ration device exits ``4`` naming the device in ``result.violations``; a
within-ration tree exits ``0`` with empty ``violations``; and the malformed
content (exit 2) and undecodable file (exit 3) fault routes are each
distinguishable by exit code alone.

The ledger is per-novel user data supplied by a filesystem ``--ledger PATH``, so
each test writes a small ledger into ``tmp_path`` and a device-bearing (or clean)
draft into the materialised ``working/`` tree, then runs the whole-manuscript
scan. A ``max_count`` over-spend is the robust acceptance case: three literal hits
over ``max_count = 2`` is an over-ration regardless of chapter attribution.
"""

from __future__ import annotations

import json
import pathlib
import typing as typ

import pytest

from novel_ralph_skill.commands._desloppify import build_app
from novel_ralph_skill.contract.exit_codes import ExitCode
from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

_COMMAND = "novel desloppify"

# The bad-ledger fixture directory, derived from ``__file__`` so collection does
# not depend on the current working directory.
_LEDGERS_DIR = pathlib.Path(__file__).resolve().parent / "data" / "ledgers"

# Bad-ledger fixtures under tests/data/ledgers/, each pinning one loader fault.
_BAD_LEDGER_FIXTURES = (
    "no-ration.toml",
    "two-windows.toml",
    "bad-pattern.toml",
    "duplicate-id.toml",
    "non-positive-max-count.toml",
)

# A one-device ledger rationing the ``sternum`` motif to two spends across the
# whole manuscript. Three literal hits over this bound is an over-ration.
_MAX_COUNT_LEDGER = """\
schema_version = 1

[[device]]
id = "sternum"
pattern = "\\\\bsternum\\\\b"
max_count = 2
"""


def _run(argv: list[str]) -> None:
    """Drive the ``desloppify`` app over ``argv`` through :func:`run`."""
    run(
        build_app(),
        argv,
        RunContext(command=_COMMAND, working_dir="working", human=False),
    )


def _envelope(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    """Return the JSON envelope ``run`` emitted to stdout."""
    return json.loads(capsys.readouterr().out)


def _result(envelope: dict[str, object]) -> dict[str, object]:
    """Return the ``result`` sub-mapping of ``envelope``."""
    return typ.cast("dict[str, object]", envelope["result"])


def _write_all_drafts(working: Path, text: str) -> None:
    """Write ``text`` to every existing chapter ``draft.md`` under ``working``."""
    for chapter_dir in (working / "manuscript").glob("chapter-*"):
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text(text, encoding="utf-8")


def _first_chapter_dir(working: Path) -> Path:
    """Return the lowest-numbered ``chapter-NN`` directory under ``working``."""
    chapters = sorted((working / "manuscript").glob("chapter-*"))
    assert chapters, "baseline tree must contain at least one chapter directory"
    return chapters[0]


def _ledger_at(tmp_path: Path, text: str) -> str:
    """Write ``text`` to a ``device-ledger.toml`` under ``tmp_path`` and return it."""
    ledger = tmp_path / "device-ledger.toml"
    ledger.write_text(text, encoding="utf-8")
    return str(ledger)


def test_over_ration_exits_four_naming_device(
    baseline_tree: cabc.Callable[[], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An over-spent device exits ``4`` and names it in ``result.violations``."""
    working = baseline_tree()
    _write_all_drafts(working, "a plain calm line\n")
    # Three "sternum" over max_count 2 is an over-ration.
    _first_chapter_dir(working).joinpath("draft.md").write_text(
        "sternum\nsternum\nsternum\n", encoding="utf-8"
    )
    ledger = _ledger_at(tmp_path, _MAX_COUNT_LEDGER)
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", ledger])
    assert excinfo.value.code == ExitCode.ACTIONABLE_FINDING, (
        "over-ration device must exit ACTIONABLE_FINDING"
    )
    envelope = _envelope(capsys)
    assert envelope["ok"] is False, "over-ration envelope must report ok=False"
    violations = typ.cast("list[str]", _result(envelope)["violations"])
    assert "sternum" in violations, f"sternum not in violations {violations}"


def test_within_ration_exits_zero(
    baseline_tree: cabc.Callable[[], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A within-ration manuscript exits ``0`` with empty violations."""
    working = baseline_tree()
    _write_all_drafts(working, "a plain calm line\n")
    # Two "sternum" is exactly at max_count 2: within ration.
    _first_chapter_dir(working).joinpath("draft.md").write_text(
        "sternum\nsternum\n", encoding="utf-8"
    )
    ledger = _ledger_at(tmp_path, _MAX_COUNT_LEDGER)
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", ledger])
    assert excinfo.value.code == ExitCode.SUCCESS, "within-ration scan must exit 0"
    envelope = _envelope(capsys)
    assert envelope["ok"] is True, "within-ration envelope must report ok=True"
    assert _result(envelope)["violations"] == [], "within ration has no violations"


def test_recompute_from_disk_drops_finding(
    baseline_tree: cabc.Callable[[], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Editing a draft to remove a spend drops the finding with no ledger edit.

    Proves the count is recomputed from disk on every run (design §6.3): the same
    ledger over an over-spending then an edited within-ration draft flips the exit
    code from ``4`` to ``0`` without touching the ledger file.
    """
    working = baseline_tree()
    _write_all_drafts(working, "a plain calm line\n")
    draft = _first_chapter_dir(working).joinpath("draft.md")
    draft.write_text("sternum\nsternum\nsternum\n", encoding="utf-8")
    ledger = _ledger_at(tmp_path, _MAX_COUNT_LEDGER)
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as over:
        _run(["--ledger", ledger])
    assert over.value.code == ExitCode.ACTIONABLE_FINDING, (
        "over-spending draft must exit ACTIONABLE_FINDING"
    )
    capsys.readouterr()  # discard the first envelope
    # Remove one spend and re-run; the ledger file is untouched.
    draft.write_text("sternum\nsternum\n", encoding="utf-8")
    with pytest.raises(SystemExit) as under:
        _run(["--ledger", ledger])
    assert under.value.code == ExitCode.SUCCESS, (
        "the edited within-ration draft must exit 0 with no ledger edit"
    )
    assert _result(_envelope(capsys))["violations"] == [], (
        "removing a spend drops the violation"
    )


@pytest.mark.parametrize("fixture", _BAD_LEDGER_FIXTURES)
def test_malformed_ledger_fixtures_exit_two(
    fixture: str,
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each malformed-content ledger fixture exits ``2`` (usage error)."""
    working = baseline_tree()
    ledger = (_LEDGERS_DIR / fixture).resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", str(ledger)])
    assert excinfo.value.code == ExitCode.USAGE_ERROR, (
        f"{fixture} must be a usage error"
    )
    assert _envelope(capsys)["ok"] is False, "a malformed ledger reports ok=False"


def test_undecodable_ledger_exits_three(
    baseline_tree: cabc.Callable[[], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An undecodable ledger file exits ``3`` (the state/input file channel)."""
    working = baseline_tree()
    ledger = (_LEDGERS_DIR / "undecodable.toml").resolve()
    monkeypatch.chdir(working.parent)
    with pytest.raises(SystemExit) as excinfo:
        _run(["--ledger", str(ledger)])
    assert excinfo.value.code == ExitCode.STATE_ERROR, (
        "an undecodable ledger file must exit STATE_ERROR"
    )
    assert _envelope(capsys)["ok"] is False, "an undecodable ledger reports ok=False"
