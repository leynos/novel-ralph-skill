# Logisphere design review — roadmap 6.2.8 ExecPlan (round 2)

Verdict: PROCEED. The round-1 blocker B1 is resolved by construction; no new
blocking defect was found. Two minor advisories only.

## Round-1 blocker B1 — resolved

B1 was: the proposed `_drive_error_arm(command, arm, tmp_path, drive, *, human)`
helper had five total parameters and tripped the project's PyPy-backed Pylint
`R0913 (5/4)`, so `make lint`/`make all` could not go green.

The round-2 plan fixes this by bundling `(command, arm)` into a single
`_ERROR_CELLS` cell, so the helper becomes `_drive_error_cell(cell, tmp_path,
drive, *, human)` — four total parameters (three positional + one keyword-only)
— and the tests become four (machine) and three (human) parameters.

Verified the fix holds by construction against the real module and config, not
trusted from the plan's summary:

- `pyproject.toml`: `max-args = 4` and `max-positional-arguments = 4`
  (`[tool.pylint.design]`); the `enable` block re-enables `too-many-arguments`
  and `too-many-positional-arguments`; the Ruff per-file-ignore of
  `PLR0913`/`PLR0917` for `test_*.py` does not silence the separate Pylint pass.
  All as the plan's Constraints state.
- The module **already** carries `_drive_machine_envelope(command, phase,
  tmp_path, drive)` (four positional params) and
  `test_machine_envelope_matrix(cell, tmp_path, drive, snapshot)` (four params),
  both of which pass `make all` today. The plan's `_drive_error_cell` and
  `test_error_arm_machine_envelope` are structurally identical four-parameter
  forms that mirror these existing, gate-passing templates exactly. This is
  decisive in-repo evidence that the four-parameter form is clean.
- The PyPy pylint shim itself could not be re-run here (the sandbox blocks
  downloading/executing the external GitHub shim), but the config-level gate and
  the existing four-parameter helpers in the same module make the conclusion
  certain without it. Round-1 already empirically reproduced both the failing
  five-parameter `R0913 (5/4)` and the passing four-parameter form.

## Re-verified load-bearing claims (round 2 spot-checks)

- runner.py exit-2/exit-3 arms: `except CycloptsError` -> `_emit` + `sys.exit(2)`
  and `except StateInputError` -> `_emit` + `sys.exit(3)` (runner.py 224-238).
  The plan cites 225-239/223-239 — a one-line citation drift, immaterial.
- `RunContext(command=..., working_dir="working", human=...)`: `working_dir` is
  the literal "working" carried from the context, not derived from the
  filesystem, so `envelope["working_dir"] == "working"` holds even when
  `working/` is absent (state arm). Confirmed.
- The redacted error envelope `{command, schema_version, ok:false,
  working_dir:"working", result:{}, messages:["<redacted>"]}` passes
  `_assert_no_volatile_fields` — the `_VOLATILE_PATTERN` does not match
  `"working"` (no slash) and the errno path lived only in `messages`, now
  redacted. Reproduced directly.
- `build_working_tree(spec, dest)` signature matches the helper's
  `wc.build_working_tree(wc.PHASE_STATES["drafting"], root)` call.
- The helper's chdir target (`working.parent == root`, which is `mkdir`'d) exists
  for both arms; `working/` is materialised only for the usage arm. Correct.
- cyclopts locked at 4.18.0, syrupy present (uv.lock). Cyclopts behaviour is
  asserted from empirical in-process drives (round-1 verified), not memory — this
  satisfies the verify-or-pin obligation. cuprum is genuinely uninvolved
  (in-process through `run`).
- Roadmap task 6.2.8 text and audit Finding 5 match the plan's framing; the fork
  (close the gap vs carry it) is the audit's own binary.
- `make all` excludes markdownlint/nixie, which the plan correctly runs
  separately for Work item 2.

## Advisories (non-blocking)

- A1 (Telefono / docs precision). Work item 2's "Documentation to read first"
  sub-bullet says the error-mode-by-command bullet "must now be removed from the
  gap list and turned into a covered-surface statement". There is **no such
  bullet** in the current `Carried gaps` section (the four bullets are
  mutator-by-phase, exhaustive-eleven-phase, incoherent-variant-by-phase, and
  installed-binary). Audit Finding 5 itself says the section "does not name the
  error-mode-by-command gap". The correct action is to **add a covered-surface
  statement** and ensure no existing bullet understates coverage — which the
  plan's main step 1 already says ("a short paragraph (not a carried-gap
  bullet)"; "Ensure no carried-gap bullet now understates coverage"). The net
  edit is achievable as written; only the read-first framing is loose. Tighten
  the wording so the implementer does not hunt for a bullet to delete.

- A2 (Doggylump). The `"Unknown option:"` and `"cannot load working/state.toml"`
  prefixes are Cyclopts-owned / command-body-owned text respectively. The plan
  already rates the Cyclopts churn low/low and pins exit code 2 plus the redacted
  skeleton as the primary contract; the `len(messages) == 1` count (A1 from
  round 1, now adopted) restores the multi-line-message signal the redaction
  would otherwise hide. Acceptable; keep the prefix assertions narrow.

## Trail

Skills: `logisphere-design-review`. Design docs and sources relied on:
`docs/novel-ralph-harness-design.md` §2.3/§3.2/§9; `docs/adr-003`;
`docs/developers-guide.md` (matrix section, lines 85-114);
`docs/issues/audit-6.2.1.md` Finding 5; `docs/roadmap.md` task 6.2.8;
`AGENTS.md` (snapshot discipline, gates); `pyproject.toml` (Ruff/Pylint config,
`max-args`/`enable` blocks); `Makefile` (lint chain, PYLINT/PYTHON targets);
`novel_ralph_skill/contract/runner.py` (exit-2/3 arms, RunContext);
`tests/test_command_surface_matrix.py` (registry, `drive` fixture, existing
four-param helpers, volatile guard, `Carried gaps` docstring);
`tests/working_corpus/_builder.py` (`build_working_tree` signature); `uv.lock`
(cyclopts 4.18.0, syrupy). The volatile-guard and gate reasoning were reproduced
directly; the external PyPy pylint shim could not be executed in the sandbox but
the conclusion is anchored by the module's existing gate-passing four-parameter
helpers.
