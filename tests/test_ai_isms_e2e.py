"""End-to-end proof the installed ``desloppify`` ships its ai-isms pack (7.1.1).

This is the defence of the ExecPlan high-severity Risk "pack not in wheel" for the
second packaged pack: build a wheel from this package, install it into a throwaway
virtual environment, resolve the installed ``ai-isms.toml`` through the *installed*
package's :func:`ai_isms_pack_path` resolver (proving the pack travelled and is
reachable via ``importlib.resources`` after a real install), then run the installed
``desloppify --pack <that path>`` over a ``working/`` tree whose draft carries an
AI-ism.

The run goes through a cuprum catalogue that **registers the exact absolute script
path** — the registration is the execution gate (``cuprum/sh.py:make`` calls
``catalogue.lookup``, which raises ``UnknownProgramError`` for any unregistered
program) — exactly as the offenders e2e (``tests/test_desloppify_e2e.py``) does. An
AI-ism-bearing tree exits ``4`` and names the rule in the stdout JSON. The e2e is
POSIX-only (ADR-006) and slow (build + venv + install), so it is skipped off POSIX
and given an explicit 180s timeout that supersedes the 30s project default.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import sysconfig
import typing as typ
from pathlib import Path

import pytest
from cuprum import ProgramCatalogue, ProjectSettings, sh
from cuprum.program import Program
from cuprum.sh import ExecutionContext

if typ.TYPE_CHECKING:
    import collections.abc as cabc

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Resolve the installed ai-isms pack through the installed resolver, so the test
# proves the resolver and the packaged data both travelled in the wheel rather
# than hand-building a site-packages path the install might not match.
_RESOLVE_PACK = (
    "from novel_ralph_skill.commands._desloppify_report import ai_isms_pack_path; "
    "print(ai_isms_pack_path())"
)


def _one_program_catalogue(name: str, program: Program) -> ProgramCatalogue:
    """Return a one-project cuprum catalogue allowlisting exactly ``program``.

    A local copy of the ``single_program_catalogue`` fixture's builder: the
    module-scoped install fixture cannot request the function-scoped fixture, and
    the catalogue is a stateless value, so building it directly keeps the wheel
    install at module scope (CodeRabbit WI4 finding) without a scope clash.
    """
    return ProgramCatalogue(
        projects=(
            ProjectSettings(
                name=name,
                programs=(program,),
                documentation_locations=(),
                noise_rules=(),
            ),
        )
    )


def _scripts_dir(venv_dir: Path) -> Path:
    """Return ``venv_dir``'s executable-scripts directory (``bin`` on POSIX).

    A local copy of the ``venv_scripts_dir`` fixture's resolver, for the same
    scope reason as :func:`_one_program_catalogue`. POSIX-only per ADR-006; the
    callers carry the POSIX skip guard.
    """
    return Path(
        sysconfig.get_path(
            "scripts",
            "venv",
            vars={"base": str(venv_dir), "platbase": str(venv_dir)},
        )
    )


def _materialise_working(dest: Path, baseline: Path, draft_text: str) -> None:
    """Copy ``baseline`` to ``dest/working`` and overwrite each draft with text.

    Mirrors ``tests/test_desloppify_e2e.py``: copying the corpus ``baseline_tree``
    into the subprocess cwd keeps the e2e in lock-step with the real state schema,
    and overwriting every chapter draft with ``draft_text`` lets the test control
    exactly which AI-isms are present.
    """
    working = dest / "working"
    shutil.copytree(baseline, working)
    for chapter_dir in (working / "manuscript").glob("chapter-*"):
        draft = chapter_dir / "draft.md"
        if draft.exists():
            draft.write_text(draft_text, encoding="utf-8")


def _resolve_installed_pack(venv_python: Path) -> Path:
    """Return the installed ``ai-isms.toml`` path via the installed resolver.

    Runs the installed package's :func:`ai_isms_pack_path` under the venv's
    interpreter, so the test proves the resolver *and* the packaged data both
    travelled in the wheel rather than hand-building a site-packages path.
    """
    python = Program(str(venv_python))
    resolve = sh.make(
        python, catalogue=_one_program_catalogue("ai-isms-resolve", python)
    )
    resolved = resolve("-c", _RESOLVE_PACK).run_sync(capture=True)
    assert resolved.exit_code == 0, resolved.stderr
    pack_path = Path((resolved.stdout or "").strip())
    assert pack_path.is_file(), f"installed ai-isms.toml not found at {pack_path}"
    return pack_path


def _build_and_install(tmp_path: Path) -> tuple[Path, Path]:
    """Build a wheel, install it into a fresh venv, and return script + pack paths.

    Returns the installed ``desloppify`` script path and the installed
    ``ai-isms.toml`` path resolved by the installed package's resolver.
    """
    venv_dir = tmp_path / "venv"
    uv = sh.make(
        Program("uv"), catalogue=_one_program_catalogue("ai-isms-e2e", Program("uv"))
    )
    build = uv(
        "build", "--wheel", str(_PROJECT_ROOT), "--out-dir", str(tmp_path / "wheels")
    ).run_sync()
    assert build.exit_code == 0, build.stderr
    wheels = sorted((tmp_path / "wheels").glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, found {wheels}"

    venv = uv("venv", str(venv_dir)).run_sync()
    assert venv.exit_code == 0, venv.stderr
    scripts_dir = _scripts_dir(venv_dir)
    venv_python = scripts_dir / "python"
    install = uv(
        "pip", "install", "--python", str(venv_python), str(wheels[0])
    ).run_sync()
    assert install.exit_code == 0, install.stderr

    script_path = scripts_dir / "desloppify"
    assert script_path.exists(), f"desloppify not installed at {script_path}"

    pack_path = _resolve_installed_pack(venv_python)
    return script_path, pack_path


@pytest.fixture(scope="module")
def installed_desloppify(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    """Build and install the wheel once per module; share script + pack paths.

    The wheel build, venv create, and install are the slow part of the e2e, so
    they run once and every parametrised case reuses the installed script and
    resolved pack (CodeRabbit WI4 finding). Each case still materializes its own
    throwaway ``working/`` tree, so the cases stay independent.
    """
    tmp_path = tmp_path_factory.mktemp("ai-isms-install")
    return _build_and_install(tmp_path)


@dataclasses.dataclass(frozen=True, slots=True)
class _AiIsmCase:
    """One installed-``desloppify`` e2e case: a draft and its expected verdict.

    Bundling the parametrize columns into one value keeps the test signature at
    four parameters, within the project's Pylint ``max-args`` limit, while leaving
    the cases readable.

    Attributes
    ----------
    draft : str
        The chapter draft text every chapter is overwritten with.
    exit_code : int
        The expected process exit code (``0`` clean, ``4`` actionable finding).
    violation : str | None
        The rule id the ``violations`` list must contain, or ``None`` for a clean
        run.
    """

    draft: str
    exit_code: int
    violation: str | None


@pytest.mark.skipif(
    os.name != "posix",
    reason="console-script e2e is POSIX-only; see ADR 006",
)
@pytest.mark.slow
@pytest.mark.timeout(180)
@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            _AiIsmCase(
                draft="This paragraph is load-bearing in the argument.\n",
                exit_code=4,
                violation="load-bearing",
            ),
            id="flags-ai-ism",
        ),
        pytest.param(
            _AiIsmCase(
                draft="A calm sentence with plain words.\n",
                exit_code=0,
                violation=None,
            ),
            id="clean-tree",
        ),
    ],
)
def test_installed_desloppify_ai_isms(
    case: _AiIsmCase,
    tmp_path: Path,
    baseline_tree: cabc.Callable[[], Path],
    installed_desloppify: tuple[Path, Path],
) -> None:
    """The installed ``desloppify --pack ai-isms.toml`` honours the ai-isms pack.

    Proves the packaged ``ai-isms.toml`` travels in the wheel and resolves through
    ``importlib.resources`` after a real install: an AI-ism-bearing draft exits
    ``4`` naming the rule, and clean prose exits ``0``. The 180s timeout supersedes
    the 30s project default.
    """
    script_path, pack_path = installed_desloppify
    dest = tmp_path / "run"
    dest.mkdir()
    _materialise_working(dest, baseline_tree(), case.draft)

    prog = Program(str(script_path))
    catalogue = _one_program_catalogue("ai-isms-run", prog)
    result = sh.make(prog, catalogue=catalogue)("--pack", str(pack_path)).run_sync(
        context=ExecutionContext(cwd=dest), capture=True
    )
    assert result.exit_code == case.exit_code, result.stderr
    envelope = json.loads(result.stdout or "{}")
    # ``ok`` is exactly "exit code 0", so derive it from the expected code.
    expected_ok = case.exit_code == 0
    assert envelope["ok"] is expected_ok, f"expected ok={expected_ok}, got {envelope}"
    violations = envelope["result"]["violations"]
    if case.violation is not None:
        assert case.violation in violations, f"{case.violation} not in {violations}"
    else:
        # The clean case must report no findings at all, not merely ``ok``.
        assert violations == [], f"expected no violations, got {violations}"
