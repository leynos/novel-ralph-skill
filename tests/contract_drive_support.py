"""Shared in-process drive seam for the cross-command contract suites.

This module is a pytest plugin registered through ``pytest_plugins`` in
``tests/conftest.py`` (roadmap 6.3.2). It is the single home for the in-process
command-drive scaffolding that the §6.2.1 command-surface matrix
(``tests/test_command_surface_matrix.py``) first grew and the §6.3.2
cross-command contract package (``tests/cross_command_contract/``) reuses: the
:class:`CommandSpec` identity tuple, the per-cell phase-tree builder
(:func:`build_phase_tree`), the volatile-field redaction guard
(:func:`assert_no_volatile_fields` and :data:`VOLATILE_PATTERN`), the
deterministic compiled-path token the guard exempts
(:data:`DETERMINISTIC_PATH_TOKEN`), the shared JSON-aware ``working_dir``
snapshot-normaliser (:func:`normalise_working_dir` with
:data:`WORKING_DIR_TOKEN`) that the mutator snapshots and the installed-binary
boundary proof both route through (roadmap 6.3.4), and the in-process ``drive``
fixture that drives a command through
:func:`novel_ralph_skill.contract.runner.run` and captures its exit code and
rendered stdout.

It lives beside ``conftest.py`` rather than inside it solely because hosting the
seam there would push ``conftest.py`` past the 400-line module cap (AGENTS.md);
registering it as a plugin keeps every helper and the ``drive`` fixture
available by name exactly as a ``conftest`` fixture would be, the same way
``tests/installed_binary_fixtures.py`` is registered. The developers-guide
"Shared test scaffolding" rule forbids new copies of existing scaffolding and
cross-module value imports, so the matrix module and the cross-command package
consume these by name (the fixture by parameter name, the pure helpers by a
runtime import of this plugin module, sanctioned because a plugin module is
``conftest``-equivalent for shared scaffolding) rather than re-spelling them.

Like ``conftest.py`` this module is inside ``PYTHON_TARGETS`` (``Makefile``), so
it carries a module docstring, a docstring on every helper and fixture, and
raises :class:`AssertionError` directly rather than using a bare ``assert``.
"""

from __future__ import annotations

import json
import re
import typing as typ

import pytest
import working_corpus as wc

from novel_ralph_skill.contract.runner import RunContext, run

if typ.TYPE_CHECKING:
    import collections.abc as cabc
    from pathlib import Path

    import cyclopts


class CommandSpec(typ.NamedTuple):
    """One command surface: its spaced console name, ``build_app`` factory, argv.

    Bundling the three identity fields keeps the drive helper's and tests'
    parameter lists within the project's argument-count gate (Pylint
    ``too-many-arguments``) while still naming each field at the call site. This
    is the shared shape the §6.2.1 matrix's local ``_ReadCommand`` and the
    §6.3.2 cross-command suites both build their registries from.

    Attributes
    ----------
    name : str
        The spaced ``novel <verb>`` console name stamped into the envelope.
    build_app : Callable[[], cyclopts.App]
        The command's ``build_app`` factory.
    argv : list[str]
        The argument vector that selects the command's body-producing verb.
    """

    name: str
    build_app: cabc.Callable[[], cyclopts.App]
    argv: list[str]


# Matches the shapes that would churn a snapshot: an absolute or multi-segment
# path, an ISO-8601 date, or a clock time. Mirrors the desloppify/done guard in
# ``tests/test_novel_done_snapshots.py``; promoted here so every cross-command
# suite shares one redaction pattern.
VOLATILE_PATTERN = re.compile(
    r"(?:^|[\"\s])/[^/\"\s]+"
    r"|/[^/\"\s]+/"
    r"|\d{4}-\d{2}-\d{2}"
    r"|\d{2}:\d{2}:\d{2}"
)

# The one deterministic working-relative path token the compile checker emits.
# It is a fixed contract constant by construction
# (``tests/test_compile_check_snapshots.py`` line 8), not a volatile per-run
# path, so the volatile guard exempts it rather than flagging it as
# multi-segment-path churn. The snapshot still pins it verbatim.
DETERMINISTIC_PATH_TOKEN = "working/manuscript/compiled.md"  # noqa: S105  # a path, not a secret

# The fixed working-relative sentinel the synthetic ``RunContext`` injects. A
# ``working_dir`` carrying exactly this token is the deterministic contract
# constant, not the machine-dependent absolute path ``novel.main`` stamps, so
# the normaliser below leaves it verbatim.
WORKING_DIR_SENTINEL = "working"

# The stable token the normaliser substitutes for a machine-dependent
# ``working_dir`` so a snapshot stays machine-independent.
WORKING_DIR_TOKEN = "<working-dir>"  # noqa: S105  # a redaction token, not a secret


def normalise_working_dir(raw: str) -> str:
    """Replace machine-dependent ``working_dir`` values with a stable token.

    Both the in-process mutator snapshots and the installed-binary boundary
    proof pin a rendered envelope whose ``working_dir`` — top-level or in the
    ``result`` body — can carry the absolute resolved path ``novel.main`` stamps
    (roadmap 6.3.4). That path is machine-dependent, so a verbatim snapshot
    would churn per machine. This helper is JSON-aware rather than
    pattern-based: it parses the envelope, reads the *real* ``working_dir``
    string at each contract site, and replaces that exact literal in ``raw`` —
    preserving the renderer's key order and whitespace byte-for-byte, so a
    future serialiser change cannot silently desynchronise the redaction the way
    an anchored regex would. The fixed :data:`WORKING_DIR_SENTINEL` token the
    synthetic ``RunContext`` injects is left verbatim, since it is a
    deterministic contract constant, not a per-machine path.

    Parameters
    ----------
    raw : str
        The rendered machine-mode envelope JSON string.

    Returns
    -------
    str
        ``raw`` with each machine-dependent ``working_dir`` literal replaced by
        :data:`WORKING_DIR_TOKEN`, leaving every other byte untouched.
    """
    envelope = json.loads(raw)
    candidates: list[str] = []
    top = envelope.get("working_dir")
    if isinstance(top, str) and top != WORKING_DIR_SENTINEL:
        candidates.append(top)
    result = envelope.get("result")
    if isinstance(result, dict):
        body = result.get("working_dir")
        if isinstance(body, str) and body != WORKING_DIR_SENTINEL:
            candidates.append(body)
    normalised = raw
    for value in candidates:
        normalised = normalised.replace(
            json.dumps(value), json.dumps(WORKING_DIR_TOKEN)
        )
    return normalised


def build_phase_tree(phase: str, tmp_path: Path) -> Path:
    """Build the coherent ``working/`` tree for ``phase`` under ``tmp_path``.

    A per-phase subdirectory keeps repeated builds within one test from
    inheriting a previous phase's tree, mirroring the ``phase_state_tree``
    factory (``tests/corpus_fixtures.py``).

    Parameters
    ----------
    phase : str
        The phase enum member name to build.
    tmp_path : Path
        The per-test temporary directory the tree is built under.

    Returns
    -------
    Path
        The materialised ``working/`` path.
    """
    dest = tmp_path / phase
    dest.mkdir(exist_ok=True)
    return wc.build_working_tree(wc.PHASE_STATES[phase], dest)


def assert_no_volatile_fields(envelope: dict[str, object]) -> None:
    """Assert the rendered envelope carries no timestamp or absolute path.

    Reuses the volatile-field guard pattern from
    ``tests/test_novel_done_snapshots.py`` so a churn-prone field cannot
    silently slip into a snapshot.

    Parameters
    ----------
    envelope : dict[str, object]
        The parsed machine-mode envelope.

    Raises
    ------
    AssertionError
        If a volatile token or key is present in the rendered envelope.
    """
    rendered = json.dumps(envelope).replace(DETERMINISTIC_PATH_TOKEN, "<compiled>")
    match = VOLATILE_PATTERN.search(rendered)
    if match is not None:
        msg = f"unexpected volatile token {match.group()!r} in envelope: {rendered}"
        raise AssertionError(msg)
    for key in ("timestamp", "created_at", "now", "time"):
        if key in rendered:
            msg = f"unexpected volatile key {key!r} in envelope"
            raise AssertionError(msg)


class Driver(typ.Protocol):
    """An in-process command driver bundling the chdir and capture mechanics."""

    def __call__(
        self, command: CommandSpec, working: Path, *, human: bool
    ) -> tuple[int, str]:
        """Drive ``command`` from ``working.parent``; return ``(code, out)``."""


@pytest.fixture
def drive(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> Driver:
    """Return an in-process driver for a command over a working tree.

    Bundling ``monkeypatch`` and ``capsys`` into one fixture keeps each test's
    parameter list within the project's argument-count gate (Pylint
    ``too-many-arguments``) while still delivering the capture mechanics by
    fixture name. The returned callable is modelled on
    ``tests/test_novel_done_snapshots.py::_run_capture``: it changes directory
    with ``monkeypatch.chdir`` (auto-reverted, xdist-safe — never a bare
    ``os.chdir``) and captures stdout via the ``capsys`` fixture. The caller
    ``json.loads`` the text for machine mode and keeps it raw for human mode.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Supplies the auto-reverted ``chdir``.
    capsys : pytest.CaptureFixture[str]
        Captures the rendered stdout.

    Returns
    -------
    Driver
        A callable ``(command, working, *, human) -> (code, out)``.
    """

    def _drive(command: CommandSpec, working: Path, *, human: bool) -> tuple[int, str]:
        """Drive ``command`` from ``working.parent``; return ``(code, out)``."""
        monkeypatch.chdir(working.parent)
        with pytest.raises(SystemExit) as excinfo:
            run(
                command.build_app(),
                command.argv,
                RunContext(command=command.name, working_dir="working", human=human),
            )
        return int(typ.cast("int", excinfo.value.code)), capsys.readouterr().out

    return _drive
