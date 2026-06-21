# Logisphere design review — roadmap 1.2.1 (round 1)

Reviewer: adversarial design panel (Pandalump, Wafflecat, Buzzy Bee, Telefono,
Doggylump, Dinolump) plus pre-mortem and alternatives checkpoint.
Date: 2026-06-21.

Verdict: PROCEED WITH CONDITIONS (no blocking defects; advisories below).

## What was verified empirically (not trusted from the plan)

- cyclopts resolves to 4.18.0 under `requires-python >=3.14` (Python 3.14.3).
- Stub exit-code matrix, reproduced with the plan's exact `make_stub_app`
  construction:
  - no-arg -> `SystemExit(2)`; positional token -> `SystemExit(2)` (requires
    `*tokens: str`, confirmed: a no-arg default raises `UnusedCliTokensError`);
  - unknown `--option` -> `SystemExit(1)` with `exit_on_error=True`, and raises
    `cyclopts.UnknownOptionError` (a `CycloptsError`) with `exit_on_error=False`;
  - `--help` -> `SystemExit(0)`; `--version` -> `SystemExit(0)`, including when
    `cyclopts.App(name=name)` is built with **no** `version=` argument (the
    Interfaces code sketch). All five paths match the plan.
- pytest-timeout 2.4.0 + pytest-xdist 3.8.0: `@pytest.mark.timeout(N)` overrides
  a smaller project `timeout` under `-n auto`; a marked test passes while an
  unmarked sibling is killed by the project default. Risk 3 mitigation holds.
- cuprum source (read-only sibling): `ProgramCatalogue(projects=...)`,
  `ProjectSettings(name, programs, documentation_locations, noise_rules)` (frozen
  dataclass, all four fields required), `Program = NewType("Program", str)`,
  `sh.make(program, *, catalogue=...)`, `CommandResult.exit_code/.stdout/.stderr/
  .ok`. The scripting-standards `Catalogue.from_programs`/`sh.scoped` API does not
  exist. The plan's Decision Log is accurate.
- uv 0.9.21 (matches the plan's `--no-project` claim).
- Makefile: `test` is `uv run pytest -v -n auto`; `all = build check-fmt lint
  typecheck test`; `audit` is separate; `typecheck` is `ty check`;
  `PYTHON_TARGETS = novel_ralph_skill tests`. Plan accurate.
- Design/ADR boundary: design §3.2 code table (2 = usage error, "bad arguments");
  roadmap 1.2.1 success = bare invocation exits 2 without crashing; roadmap 1.3.1
  success explicitly = "a malformed invocation yields code 2"; ADR-003 line 117
  and ADR-005 lines 50-51 = the envelope and exit-code helper are built in 1.3.1
  and enforced by the shared scaffolding. The plan's deferral of unknown-option
  -> 2 to 1.3.1, and its stub emitting human prose with no envelope, are
  design-conformant, not violations.
- developers-guide has the "The five commands" section; users-guide has no
  command-install section yet (work item 4 adds one). Both targets exist.

## Advisory findings (non-blocking; harden if cheap)

1. (Doggylump/Buzzy Bee) The e2e `uv build` relies on **inherited cwd** being
   the project root. cuprum `ExecutionContext.cwd` defaults to `None`, so the
   build of the current project depends on the xdist worker's cwd. It works
   under xdist today, but is implicit. Harden by passing an explicit project
   path to the build (e.g. `uv build --wheel <project_dir> --out-dir <tmp>`) or
   by asserting exactly one wheel artefact exists in `out_dir` before install.
   Already partly covered by reading `CommandResult.exit_code`, but an explicit
   cwd/path is more robust.

2. (Telefono/Dinolump) The unit test that pins unknown `--option` -> exit 1 is
   **provisional**: roadmap 1.3.1 wires "bad arguments -> 2", at which point
   this assertion must change. The plan acknowledges the deferral but should
   mark the test/Decision Log as "provisional until 1.3.1" so a future reader
   does not treat exit 1 as a permanent contract.

3. (Pandalump) Tolerances cap at 9 files / 300 net lines. Work item 3 alone
   edits pyproject.toml plus two test files and the Decision Log foresees a
   re-probe; the budget is adequate but tight if the cuprum API needs
   adjustment on the locked version. No change required, just noted.

4. (Wafflecat — alternatives checkpoint) Strongest alternative: skip the cuprum
   catalogue in the e2e test and run **all** steps (uv build/venv/install and the
   five scripts) via a single scoped subprocess, since the test already takes
   one justified raw-subprocess exception for the absolute-path scripts.
   Trade-off: it
   would drop the cuprum dev-dependency and simplify the test, but it abandons the
   scripting-standards mandate to route bare program names (`uv`) through cuprum.
   The plan's split (cuprum for `uv`, subprocess for absolute paths) is the more
   standards-conformant choice and is correctly justified. Alternative rejected;
   the plan is on solid ground here.

## Pre-mortem (six months on)

- Most likely failure: the e2e test flakes or times out on a cold cache when the
  whole suite runs `-n auto`, because build+venv+install lands on the same worker
  as other slow work. Mitigation already in plan (180s per-test override, verified)
  plus the `slow` mark; advisory 1 (explicit build path) further de-risks.
- Second: a future agent "fixes" the exit-1 unknown-option assertion to 2 inside
  1.2.1 and re-implements parser behaviour, violating the deterministic boundary.
  Mitigation: advisory 2 (mark the assertion provisional, cite 1.3.1).
- Third: cuprum's locked version drifts from the sibling checkout and the symbol
  names move. Mitigation already in plan (implementer re-reads catalogue.py/
  program.py/sh.py before relying on symbols; invariant fixed).

## Conclusion

No blocking defects. Every load-bearing external claim (cyclopts exit codes,
pytest-timeout-under-xdist, cuprum API, uv behaviour) was verified against the
real source or runtime, not memory. The design/ADR boundary is honoured. The four
work items are atomic, ordered, testable, and complete. Address the advisories at
the implementer's discretion; advisory 2 (provisional test marker) is the most
valuable for preventing a future boundary violation.
