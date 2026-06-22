"""Focused unit tests for the shared venv-scripts-directory resolver.

These exercise the ``venv_scripts_dir`` resolver fixture directly so the
``venv``-scheme resolution is proven without paying the slow
wheel-build-and-install cost of the full end-to-end suite. The resolver — and
therefore this suite — is POSIX-only per ADR 006; the suite is skipped on
non-POSIX platforms.
"""

from __future__ import annotations

import os
import typing as typ

import pytest
from cuprum import sh
from cuprum.program import Program

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    from cuprum import ProgramCatalogue

# why: the resolver and the e2e it serves are POSIX-only (ADR 006); the Windows
# branch was dead and wrong, so the suite is skipped on non-POSIX platforms.
pytestmark = pytest.mark.skipif(
    os.name != "posix",
    reason="console-scripts venv resolver is POSIX-only; see ADR 006",
)


class TestVenvScriptsDir:
    """Group the resolver assertions that exercise ``venv_scripts_dir``."""

    def test_resolver_points_at_venv_bin(
        self,
        tmp_path: Path,
        single_program_catalogue: cabc.Callable[[str, Program], ProgramCatalogue],
        venv_scripts_dir: cabc.Callable[[Path], Path],
    ) -> None:
        """The resolver returns the ``uv venv`` bin directory, not a roaming path."""
        venv_dir = tmp_path / "venv"
        catalogue = single_program_catalogue("novel-ralph-resolver-test", Program("uv"))
        result = sh.make(Program("uv"), catalogue=catalogue)(
            "venv", str(venv_dir)
        ).run_sync(capture=True)
        assert result.exit_code == 0, f"uv venv failed: {result.stderr}"

        scripts_dir = venv_scripts_dir(venv_dir)

        assert scripts_dir.is_dir(), (
            f"resolved scripts dir does not exist: {scripts_dir}"
        )
        assert (scripts_dir / "python").exists(), (
            f"venv python launcher not found under {scripts_dir}"
        )
        # The bin directory must live inside the venv, not a roaming user path.
        assert venv_dir in scripts_dir.parents, (
            f"{scripts_dir} is not inside the venv {venv_dir}"
        )

    def test_resolver_is_posix_shaped(
        self,
        tmp_path: Path,
        venv_scripts_dir: cabc.Callable[[Path], Path],
    ) -> None:
        """On POSIX the resolved scripts directory is ``bin``, not ``Scripts``."""
        scripts_dir = venv_scripts_dir(tmp_path / "venv")

        assert scripts_dir.name == "bin", (
            f"expected POSIX 'bin' scripts directory, got {scripts_dir.name}"
        )
