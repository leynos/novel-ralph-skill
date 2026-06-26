"""Behavioural tests for the entry point's ``working_dir`` stamp (roadmap 6.3.4).

Drive the production entry point :func:`novel_ralph_skill.commands.novel.main`
from a chosen directory and assert it stamps the *absolute, resolved* ``working/``
path into the envelope ``working_dir`` field, not the bare ``"working"`` token.
Nothing else drives ``main``'s own ``RunContext`` construction, so these are the
proof that the production path surfaces the resolved path: a no-``working/`` arm
shows ``<dir>/working``, and an inside-``working/`` arm shows the visible
``working/working`` footgun.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from novel_ralph_skill.commands import novel
from novel_ralph_skill.contract.exit_codes import ExitCode

_COMMAND = ("novel", "state", "check")


def test_main_stamps_absolute_resolved_working_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """From a directory with no ``working/``, the envelope names ``<dir>/working``."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [*_COMMAND])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.STATE_ERROR, "no working/ must exit 3"
    envelope = json.loads(capsys.readouterr().out)
    expected = str((tmp_path / "working").resolve())
    assert envelope["working_dir"] == expected, (
        "main must stamp the absolute resolved working/ path"
    )
    stamped = Path(envelope["working_dir"])
    assert stamped.is_absolute(), "the stamped working_dir must be absolute"
    assert stamped.name == "working", "the stamped path must end in a 'working' dir"


def test_main_surfaces_inside_working_footgun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Run from inside ``working/`` and see the visible ``working/working`` path."""
    (tmp_path / "working").mkdir()
    monkeypatch.chdir(tmp_path / "working")
    monkeypatch.setattr(sys, "argv", [*_COMMAND])
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    assert excinfo.value.code == ExitCode.STATE_ERROR, "inside working/ must exit 3"
    envelope = json.loads(capsys.readouterr().out)
    expected = str((tmp_path / "working" / "working").resolve())
    assert envelope["working_dir"] == expected, (
        "the footgun must be visible as the absolute working/working path"
    )
    stamped = Path(envelope["working_dir"])
    assert stamped.is_absolute(), "the stamped working_dir must be absolute"
    assert stamped.parts[-2:] == ("working", "working"), (
        "running inside working/ must surface a nested working/working tail"
    )
