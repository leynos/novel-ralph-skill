"""Contract that each push and pull request runs the test suite once.

`ci.yml` runs the suite under coverage on every push to `main` and every
pull request. An `act-validation.yml` workflow used to run
`make test WITH_ACT=1` on the same events. No test reads the
`RUN_ACT_VALIDATION` variable that flag sets, so a collection selects the
same 1,580 tests either way, and the workflow ran the whole suite a second
time. It was removed. These tests keep a second suite run from returning.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
COVERAGE_ACTION = "leynos/shared-actions/.github/actions/generate-coverage@"
MAKE_VALUE_OPTIONS = frozenset({
    "-C",
    "-f",
    "-I",
    "-o",
    "-W",
    "--directory",
    "--file",
    "--makefile",
})
SUITE_TARGETS = frozenset({"test", "all"})
SEPARATORS = re.compile(r"&&|\|\||[;|\n]")
PYTEST = re.compile(r"\bpytest\b")


def _make_targets(words: list[str]) -> list[str]:
    """Return the targets of a ``make`` call: its words less options and values."""
    start = next(
        (i for i, word in enumerate(words) if word == "make" or word.endswith("/make")),
        None,
    )
    if start is None:
        return []
    found: list[str] = []
    skip = False
    for word in words[start + 1 :]:
        if skip:
            skip = False
        elif word in MAKE_VALUE_OPTIONS:
            skip = True
        elif not word.startswith("-") and "=" not in word:
            found.append(word)
    return found


def runs_suite(command: str) -> bool:
    """Report whether a shell command runs the suite, in any spelling.

    Examples
    --------
    >>> runs_suite("make -C . test")
    True
    >>> runs_suite("make test-workflow-contracts")
    False
    """
    return bool(PYTEST.search(command)) or any(
        SUITE_TARGETS & set(_make_targets(segment.split()))
        for segment in SEPARATORS.split(command)
    )


def _steps() -> list[tuple[str, dict]]:
    """Return every step of every workflow, labelled by file and job."""
    found: list[tuple[str, dict]] = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job_name, job in (document.get("jobs") or {}).items():
            found.extend(
                (f"{path.name}/{job_name}", step) for step in job.get("steps") or []
            )
    return found


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("make test", True),
        ("make test WITH_ACT=1", True),
        ("make -j2 test", True),
        ("make -C . test", True),
        ("make all", True),
        ("set -eu && make test", True),
        ("uv run pytest -v", True),
        ("make test-workflow-contracts", False),
        ("make typecheck", False),
    ],
)
def test_the_suite_pattern(command: str, *, expected: bool) -> None:
    """Recognize every spelling of a suite run, and nothing longer."""
    assert runs_suite(command) is expected, command


def test_no_workflow_step_runs_the_suite() -> None:
    """Refuse a plain suite run anywhere; the coverage action is the one run."""
    repeated = [
        (where, step.get("run"))
        for where, step in _steps()
        if runs_suite(str(step.get("run", "")))
    ]
    assert not repeated, f"the suite runs outside coverage in {repeated!r}"


def test_coverage_runs_on_every_push_and_pull_request() -> None:
    """Require one unguarded coverage step in `ci.yml` on both events."""
    document = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
    triggers = document.get("on", document.get(True))
    assert {"push", "pull_request"} <= set(triggers), "ci.yml must run on both"
    coverage = [
        step
        for where, step in _steps()
        if where.startswith("ci.yml/")
        and str(step.get("uses", "")).startswith(COVERAGE_ACTION)
    ]
    assert len(coverage) == 1, "expected one coverage step in ci.yml"
    assert "if" not in coverage[0], "the coverage step must run on every event"
