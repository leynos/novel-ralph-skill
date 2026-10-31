"""Contract that each push and pull request runs the test suite once.

``ci.yml`` runs the suite under coverage on every pull request, and
``coverage-main.yml`` runs it under coverage on every push to ``main``, because
main owns the CodeScene upload (CV-005) and a pull request never reaches
CodeScene. An ``act-validation.yml`` workflow used to run
``make test WITH_ACT=1`` on the same events. No test reads the
``RUN_ACT_VALIDATION`` variable that flag sets, so a collection selects the
same 1,580 tests either way, and the workflow ran the whole suite a second
time. It was removed. These tests keep a second suite run from returning,
across every workflow and every local composite action, since a step there
runs as part of whatever uses it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.suite_commands import runs_suite

GITHUB = Path(__file__).resolve().parents[1] / ".github"
COVERAGE_ACTION = "leynos/shared-actions/.github/actions/generate-coverage@"


def _documents() -> dict[str, dict]:
    """Parse every workflow and local composite action, by relative path."""
    paths = [*GITHUB.glob("workflows/*.y*ml"), *GITHUB.glob("actions/**/action.y*ml")]
    return {
        str(path.relative_to(GITHUB)): yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(paths)
    }


def _steps(document: dict) -> list[dict]:
    """Return every step of a workflow's jobs or of a composite action."""
    runs = document.get("runs")
    found = list(runs.get("steps") or []) if isinstance(runs, dict) else []
    for job in (document.get("jobs") or {}).values():
        found.extend(job.get("steps") or [])
    return found


def _coverage_placements() -> list[tuple[str, dict, dict]]:
    """Return each coverage step with its document and enclosing job.

    A composite action's steps have no job, so they are paired with an empty
    mapping, which carries no guard.
    """
    found: list[tuple[str, dict, dict]] = []
    for where, document in _documents().items():
        runs = document.get("runs")
        owners = [({}, runs)] if isinstance(runs, dict) else []
        owners.extend((job, job) for job in (document.get("jobs") or {}).values())
        found.extend(
            (where, job, step)
            for job, owner in owners
            for step in owner.get("steps") or []
            if str(step.get("uses", "")).startswith(COVERAGE_ACTION)
        )
    return found


def _triggers(document: dict) -> dict:
    """Return a workflow's triggers, read under ``on`` or its boolean form."""
    value = document.get("on", document.get(True))
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return dict.fromkeys(value)
    return {value: None}


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("make test", True),
        ("make test WITH_ACT=1", True),
        ("make -j2 test", True),
        ("make -C . test", True),
        ("make all", True),
        ("make", True),
        ('make "test"', True),
        ("make lint&&make test", True),
        ("set -eu && make test", True),
        ("uv run pytest -v", True),
        ("uv run --with 'pytest>=8' python -m pytest -q", True),
        ("env RUN_ACT_VALIDATION=1 make test", True),
        ("env -u HOME make test", True),
        ("python3.13 -m pytest", True),
        ("make \\\ntest", True),
        ("make lint # then\nmake test", True),
        ("echo 'pre;make test;post'", False),
        ('echo "a && make test"', False),
        ("# make test", False),
        ("make test-workflow-contracts", False),
        ("make typecheck", False),
        ("echo pytest", False),
    ],
)
def test_the_suite_pattern(command: str, *, expected: bool) -> None:
    """Recognize every spelling of a suite run, and nothing longer."""
    assert runs_suite(command) is expected, command


def test_no_local_step_runs_the_suite() -> None:
    """Refuse a plain suite run in any workflow or local composite action."""
    repeated = [
        (where, step.get("run"))
        for where, document in _documents().items()
        for step in _steps(document)
        if runs_suite(str(step.get("run", "")))
    ]
    assert not repeated, f"the suite runs outside coverage in {repeated!r}"


def test_coverage_runs_once_per_event() -> None:
    """Require one coverage step in ``ci.yml`` and one in ``coverage-main.yml``.

    The pull-request lane carries the pull-request guard and its job is
    unguarded. The publisher's job and step are unguarded, and it triggers on
    pushes to main alone, so no event runs the suite twice and none skips it.
    """
    placements = _coverage_placements()
    assert [where for where, _, _ in placements] == [
        "workflows/ci.yml",
        "workflows/coverage-main.yml",
    ], placements
    (_, lane_job, lane_step), (_, publisher_job, publisher_step) = placements
    assert "if" not in lane_job, "the pull-request lane's job must not be guarded"
    assert lane_step.get("if") == "github.event_name == 'pull_request'", (
        "the pull-request lane must run on pull requests, and only there"
    )
    assert "if" not in publisher_job, "the publisher's job must not be guarded"
    assert "if" not in publisher_step, "the publisher's coverage step is guarded"
    publisher = _documents()["workflows/coverage-main.yml"]
    assert "push" in _triggers(publisher), "the publisher must run on push"
    assert "pull_request" not in _triggers(publisher), "a pull request must not publish"
    push = _triggers(publisher)["push"] or {}
    assert push.get("branches") == ["main"], "the publisher must run on pushes to main"
    filters = sorted({"paths", "paths-ignore"} & set(push))
    assert not filters, f"path filters {filters} would skip pushes to main"


def test_ci_runs_on_every_pull_request_and_push_to_main() -> None:
    """Require an unfiltered pull-request trigger and a push naming main."""
    triggers = _triggers(_documents()["workflows/ci.yml"])
    assert "pull_request" in triggers, "ci.yml must run on pull requests"
    assert triggers["pull_request"] in (None, {}), triggers["pull_request"]
    push = triggers.get("push") or {}
    branches = push.get("branches")
    names = branches if isinstance(branches, list) else [branches]
    assert "main" in names, "ci.yml must run on every push to main"
    filters = sorted({"paths", "paths-ignore"} & set(push))
    assert not filters, f"path filters {filters} would skip pushes to main"
