# Logisphere design review — roadmap 6.2.8 ExecPlan (round 1)

Verdict: REVISE. One blocking defect; the rest of the plan is accurate and
well-grounded.

## Blocking defect

### B1 — The proposed `_drive_error_arm` helper trips Pylint R0913

The plan's Work item 1 step 2 specifies:

```python
def _drive_error_arm(
    command: _ReadCommand, arm: _ErrorArm, tmp_path: Path, drive: _Driver,
    *, human: bool,
) -> tuple[int, str]:
```

That is five arguments (four positional plus one keyword-only). The project's
Pylint pass enables `too-many-arguments` (pyproject.toml line 297) with
`max-args = 4` and `max-positional-arguments = 4` (lines 180, 183), and Pylint
runs over `tests/` (`PYLINT_TARGETS = PYTHON_TARGETS = novel_ralph_skill tests`,
Makefile lines 15-17). The Ruff per-file-ignore of `PLR0913`/`PLR0917` for
`test_*.py` (pyproject.toml line 97) does **not** silence the separate
PyPy-backed Pylint pass.

Empirically confirmed with the project's own pylint runner:

```text
R0913: Too many arguments (5/4) (too-many-arguments)
```

`make lint` (hence `make all`, Makefile line 28) therefore fails, so Work item 1
cannot reach a green gate as written.

This contradicts the plan's own Constraints (lines 88-92), which assert the
slice "must not breach any other gate (`too-many-arguments`, `too-many-locals`)
... to stay within the argument-count gate". Every existing helper/test in the
module sits at exactly four arguments (e.g. `_drive_machine_envelope(command,
phase, tmp_path, drive)`, `test_machine_envelope_matrix(cell, tmp_path, drive,
snapshot)`); the proposed helper adds a fifth.

Addressable fix (planner's choice): bundle the inputs so the helper takes at
most four arguments — e.g. fold the chdir/build mechanics into the existing
`drive` fixture (or a sibling fixture) so the helper need not take both
`tmp_path` and `drive`; or pass a single prepared `(command, arm)` cell plus the
driver and `human`; or make `human` positional inside a 4-arg signature. The
fix must keep the helper at or below four total arguments and re-verify with the
project pylint runner, not merely Ruff.

## Verified — claims that hold

All load-bearing empirical claims were re-checked against the real source, not
trusted from the plan's summary.

- Exit-3 (absent `working/`), machine mode, all five commands: byte-identical
  `messages == ["cannot load working/state.toml: [Errno 2] No such file or
  directory: 'working/state.toml'"]`, `ok: false`, `result: {}`,
  `working_dir: "working"`. Matches Surprises and Risk 2.
- Exit-2 (`--nope`), machine mode: `Unknown option: --nope.` for four commands,
  `Unknown option: --nope. Did you mean --no-check?` for `novel-compile --check`.
  Matches Surprises and Risk 1. The exit-2 arm fires identically with or
  without a working tree (the parse error precedes the body), so the usage
  arm's `build_working=True` is harmless but not load-bearing — not a defect.
- Human mode stamps the command name on both arms for all five commands.
- `_ReadCommand._replace(argv=...)` works and leaves the original untouched.
- runner.py exit-2/exit-3 arms (lines 223-239), `parse_global_flags` running
  before `run`, and the `_emit` rendering path are exactly as described.
- Design §3.2 exit table, §9 CLI error-path strategy, ADR-001 deterministic
  boundary (the slice is wholly deterministic), audit Finding 5, and the
  developers-guide matrix section all match the plan's citations.
- syrupy 5.3.2, pytest-randomly, pytest-xdist, pytest-timeout all locked and
  present; `--snapshot-update` and `-p no:randomly` are valid.
- cuprum is genuinely uninvolved (in-process through `run`); the
  cuprum-research obligation is satisfied by exclusion. Cyclopts 4.18.0 (locked)
  behaviour is verified empirically here rather than from memory.
- Work items are atomic, correctly ordered (slice before prose), and testable;
  validation commands are concrete and correct; `make all` excludes
  markdownlint/nixie, which the plan correctly runs separately for Work item 2.

## Advisory (non-blocking)

- A1 (Telefono): the redacted snapshot pins only `messages: ["<redacted>"]`
  plus the skeleton. Consider asserting `len(messages) == 1` (not merely
  non-empty) so a future arm that accidentally emits multiple message lines is
  caught, since the redaction collapses that signal.
- A2 (Doggylump pre-mortem): the message-prefix assertion `"Unknown option:"`
  is Cyclopts-owned text; the plan already rates this low/low and pins exit code
  2 as the primary contract. Acceptable, but a Cyclopts upgrade is the most
  likely future churn source — keep the prefix assertion narrow.
- A3 (Wafflecat): the credible alternative — document the gap as carried rather
  than close it — is explicitly evaluated and reasonably rejected (closing is
  cheap once the arms are proven command-agnostic). No straw man; the fork is
  sound.

## Trail

Design docs and skills relied on: `logisphere-design-review` skill;
`docs/novel-ralph-harness-design.md` §3.2/§9; `docs/adr-001`/`adr-003`;
`docs/developers-guide.md`; `docs/issues/audit-6.2.1.md` Finding 5;
`docs/roadmap.md` task 6.2.8; `AGENTS.md` (snapshot discipline, gates);
`pyproject.toml` (Ruff and Pylint config); `Makefile` (target chain,
PYLINT/PYTHON targets); `novel_ralph_skill/contract/runner.py`;
`tests/test_command_surface_matrix.py`. Empirical drives run against the real
five command apps and the project's PyPy-backed pylint runner.
