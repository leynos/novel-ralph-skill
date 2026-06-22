# Logisphere adversarial design review — roadmap 1.3.1 ExecPlan (Round 2)

Reviewer: Logisphere crew (adversarial). Date: 2026-06-22.
Subject: `docs/execplans/roadmap-1-3-1.md` (Status: DRAFT, revised round 2).
Verdict: **PASS** — the four round-1 blocking defects (B1-B4) are resolved and
verified; no new blocking defect found. Advisory notes below should be folded in
during implementation but do not gate the plan.

Sources consulted (read from disk, not from the planner's summary):
`docs/execplans/roadmap-1-3-1.md`, `docs/execplans/roadmap-1-3-1.review-r1.md`,
`docs/adr-003-shared-interface-contract.md`,
`docs/novel-ralph-harness-design.md` §3.1/§3.2/§3.3/§3.4/§9/§10,
`docs/developers-guide.md` (envelope / exit-code sections),
`docs/roadmap.md` (1.3.1), `AGENTS.md` (gates),
`pyproject.toml`, `novel_ralph_skill/commands/{names.py,stub.py}`,
`tests/test_tomlkit_dependency.py`, the cuprum read-only sibling, and the
official Cyclopts v4.18.0 docs (api.html, packaging.html, app_calling.html,
firecrawl).

## Round-1 blocking defects: resolution check

### B1 (result_action control-flow) — RESOLVED and verified

The plan's fix is `result_action="return_value"`, which it claims is a
documented v4.18.0 built-in mode returning the body value to the caller. This is
the linchpin of the whole task, so it was verified directly against the official
`api.html` (not trusted from the planner's citation):

- `App.result_action` accepts the literal `"return_value"` as a built-in mode,
  documented verbatim as: *"Returns the command's value unchanged. Use for
  embedding Cyclopts in other Python code or testing."*
- `packaging.html` confirms the default `"print_non_int_sys_exit"` calls
  `sys.exit()` on the body return (int → `sys.exit(int)`, None → `sys.exit(0)`),
  i.e. the round-1 B1 mechanism gap is real and the chosen fix removes it.

The fix is propagated consistently (Orientation pinning, Risks, Decision Log,
Work item 1 tripwire, Work item 4 responsibilities, acceptance, interface
allow-list). Sound.

### B2 (load-bearing Cyclopts behaviour unpinned) — RESOLVED

Work item 1 now commits `tests/test_cyclopts_contract.py`, a
version+behaviour tripwire pinning `LOCKED_CYCLOPTS_VERSION = "4.18.0"` plus the
four load-bearing behaviours, mirroring `tests/test_tomlkit_dependency.py`. The
pinned behaviours were each verified against the official docs:

- `exit_on_error` default `True` → `sys.exit(1)` on a Cyclopts runtime error;
  under `exit_on_error=False` a `CycloptsError` subclass is raised. (app_calling)
- `print_error` default `True`; `help_on_error` exists, default `False`. The
  panel-suppression kwargs are real. (app_calling)
- `--help`/`--version` *bypass the command body and `result_action`*, exiting 0.
  This is the official wording, and it is what makes the plan's
  "`--help`/`--version` exempt from the envelope" claim correct even under
  `result_action="return_value"`. (app_calling)
- `UnknownCommandError`, `UnknownOptionError`, `MissingArgumentError` are the
  `CycloptsError` subclasses. (app_calling)

### B3 (dependency guard weakened the cited pattern) — RESOLVED

Work item 2's guard now pins exact locked versions
(`LOCKED_HYPOTHESIS_VERSION`, `LOCKED_SYRUPY_VERSION`) read off `uv.lock`, with
a documented `importlib.metadata.version("syrupy")` fallback, matching the
tomlkit
tripwire it cites. No longer a presence-only check.

### B4 (pytest-bdd added without a §9 mandate) — RESOLVED

`pytest-bdd` and the `tests/features` / `tests/steps` suite are dropped. This is
design-derived, not asserted: §9 assigns the exit-code contract to "CLI
error-path tests" and pins the 1-vs-4 distinction to `novel-done`, explicitly
stating the simpler surfaces need "only snapshot coverage ... not a
property-based or behavioural suite of their own." The 1-vs-4 harness meaning is
now asserted by the Work item 4 CLI error-path tests (1 != 4, both `ok: false`,
non-interchangeable) plus the Work item 5 Hypothesis property. Dependency count
drops to two (hypothesis, syrupy), both dev-only, within Tolerances.

Round-1 non-blocking A1 (snapshot redaction named non-existent fields), A2
(`--help`/`--version` exemption unpinned), and A3 (mutator-refusal→3 note) are
also addressed (redaction limited to `working_dir`; a `--help`/`--version`→0-no-
envelope test added; the §3.4 note folded into Work item 6).

## Independent verification of remaining locked-library claims

- **No uncited memory-based locked-library claim survives.** Every load-bearing
  Cyclopts behaviour is now cited to a specific v4.18.0 page and pinned by the
  Work item 1 tripwire. All four were re-verified by firecrawl against the
  official docs for this review and match.
- **pytest-timeout under pytest-xdist:** the plan makes *no* claim about this
  interaction, so the review brief's trap is avoided. `timeout = 30` is already
  configured in `pyproject.toml` and the plan does not touch it. The only xdist
  remark is that Hypothesis coexists with xdist, which is a Hypothesis
  compatibility property, not load-bearing for the contract.
- **cuprum:** correctly absent. The cuprum sibling (`catalogue.py`, `sh.py`,
  `program.py`, `builders/`) is a subprocess-execution catalogue; this module
  shells out to nothing (design §9), so importing cuprum would be wrong. The
  plan's "no cuprum" stance is verified against the real source.
- **msgspec:** banned-from-`from`-import in Ruff config and absent from the lock;
  the stdlib `dataclasses`+`json` choice is sound and adds no runtime dep.

## Advisory (fold in during implementation; non-blocking)

1. **Wrapper behaviour on an unexpected body exception is unspecified.** The
   `run` wrapper catches `CycloptsError`→2 and `StateInputError`→3, and maps a
   returned `ExitCode`→0/1/4. It does not say what happens if the body raises
   something *else* (a genuine bug). With `exit_on_error=False` and
   `result_action="return_value"`, such an exception propagates as a traceback
   with a non-contract exit status. Design §10 mandates a clean exit 3 only for
   state faults, so crashing on a real bug is defensible — but the plan should
   *state the choice* (no catch-all; genuine bugs surface as crashes, not as a
   spurious contract code) so Work item 4 does not accidentally swallow bugs into
   a misleading exit 2/3. Add one sentence to Work item 4 and, ideally, a test
   asserting a non-contract exception is not coerced into a contract code.

2. **`--human` is indeterminate on a parse failure.** On a `CycloptsError` the
   parse did not complete, so whether `--human` was requested may be unknown. The
   plan says emit the usage-error envelope "in the active mode"; specify that the
   wrapper falls back to machine mode (the default) when the mode cannot be
   resolved, so the usage-error path is deterministic. Minor; the Work item 4
   usage-error test should assert a machine envelope in this case (it already
   asserts a machine envelope on the unknown-subcommand path, so this is
   mostly a wording tightening).

3. **`build_envelope` stamping `schema_version` is implicit.** The
   `build_envelope` signature omits `schema_version`, so it must stamp
   `ENVELOPE_SCHEMA_VERSION` internally (the right design — single source). State
   this explicitly in Work item 3 so the implementer does not add a
   `schema_version` parameter and reintroduce a way to emit an inconsistent
   version.

4. **`--human` plumbing idiom is deferred.** The `run` signature's
   `human_flag_seen` parameter is in tension with `app(...)` owning the parse;
   the plan defers the exact idiom (named `App.meta` global-flag) to
   implementation while fixing the observable contract and its tests. This is
   acceptable execplan latitude — the contract and Work item 4 tests pin the
   behaviour regardless of idiom — but the implementer must record the chosen
   idiom in the Decision Log as the plan instructs.

## Confirmed-sound aspects (not defects)

- Envelope field set/order, `ok`-mirrors-exit-0 invariant, and the five-code
  table match ADR-003 and design §3.1/§3.2 exactly.
- `COMMAND_NAMES` single-source-of-truth import path is correct; `command`
  passed to `run` is the top-level console-script name (one of the five), so
  `build_envelope`'s `command in COMMAND_NAMES` validation holds on every path,
  including the unknown-*subcommand* usage error.
- Work items are atomic, ordered (deps → frame → wrapper → property/snapshots →
  docs), independently committable, and each ends `make all` green. Red/green is
  specified per item.
- Typecheck gate is `ty` (AGENTS.md), markdown gates are
  `make markdownlint`/`make nixie`; the plan invokes them for the doc commit.
- The deterministic/judgemental boundary is respected: this module is pure
  deterministic plumbing with no model-side judgement, and §3.4 mutator-refusal
  → exit 3 (never 1) is carried into the Work item 6 docs note.

## Verdict

The plan is implementable and design-conformant as written. The four round-1
blocking defects are resolved and independently re-verified against the official
Cyclopts v4.18.0 documentation. The four advisory notes are wording/edge
tightenings the implementer should fold in, not design defects. **PASS.**
