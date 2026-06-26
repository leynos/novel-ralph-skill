"""End-to-end coherence of ``novel-compile`` then ``novel-state check`` (4.1.1.1).

The function-level round-trip oracle in ``tests/test_compile_unit.py`` pins the
load-bearing invariant directly: after :func:`compile_manuscript`,
``check_disk_evidence`` reports no ``compiled-matches-drafts`` divergence. That
pin calls the detector in-process and so cannot see drift between the two
commands' own cwd-relative resolvers and JSON envelopes.

This thin integration test is the defence-in-depth twin: it drives **the real
``novel`` console-script entry point** in sequence over one ``working/`` tree —
``novel compile`` then ``novel state check`` through ``novel.main()`` — and
asserts
the compile writes ``compiled.md`` and the subsequent check exits ``0`` with an
empty ``result.violations``. A future change to either command's resolver or
envelope that desynchronises the pair would fail here even though the
function-level pin still passes (roadmap addendum 4.1.1.1, from review:4.1.1).
"""

from __future__ import annotations

import json
import sys
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.commands import novel
from novel_ralph_skill.contract.exit_codes import ExitCode

if typ.TYPE_CHECKING:
    from pathlib import Path


def _drive(
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[ExitCode, dict[str, object]]:
    """Run the ``novel`` multiplexer over ``argv``; return its code and envelope.

    Parameters
    ----------
    argv : list[str]
        The command-line arguments, including ``argv[0]`` (always ``"novel"``);
        the remaining tokens are the subcommand verb and its arguments.
    monkeypatch : pytest.MonkeyPatch
        Patches ``sys.argv`` for the call.
    capsys : pytest.CaptureFixture[str]
        Captures the JSON envelope emitted to stdout.

    Returns
    -------
    tuple[ExitCode, dict[str, object]]
        The process exit code and the parsed stdout envelope.
    """
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as excinfo:
        novel.main()
    envelope = json.loads(capsys.readouterr().out)
    return typ.cast("ExitCode", excinfo.value.code), envelope


def test_compile_then_check_round_trips_through_entry_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Compiling then checking through both real entry points stays coherent.

    Over the canonical coherent drafting tree (no ``compiled.md`` yet),
    ``novel-compile`` exits ``0`` and writes the file, then ``novel-state check``
    exits ``0`` with no violations — proving the two commands agree end-to-end.
    """
    working = wc.build_working_tree(wc.COHERENT_BASELINE, tmp_path)
    compiled = working / "manuscript" / "compiled.md"
    assert not compiled.exists()
    monkeypatch.chdir(working.parent)

    compile_code, compile_envelope = _drive(
        ["novel", "compile"],
        monkeypatch,
        capsys,
    )
    assert compile_code == ExitCode.SUCCESS
    assert compile_envelope["ok"] is True
    compile_result = typ.cast("dict[str, object]", compile_envelope["result"])
    assert compile_result["compiled"] == "working/manuscript/compiled.md"
    assert compiled.exists()

    check_code, check_envelope = _drive(
        ["novel", "state", "check"],
        monkeypatch,
        capsys,
    )
    assert check_code == ExitCode.SUCCESS
    assert check_envelope["ok"] is True
    check_result = typ.cast("dict[str, object]", check_envelope["result"])
    assert check_result["violations"] == []
