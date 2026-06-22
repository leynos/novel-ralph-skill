# Establish a docstring-coverage gate (interrogate) for the Python package

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

This is roadmap task 1.2.5 (`docs/roadmap.md` lines 118-123, step 1.2). It
closes a low-severity remediation raised by the audit of task 1.2.1: the
`interrogate` docstring-coverage tool was, at the time of that audit, "a dev
dependency with no configuration or Makefile/CI invocation, so docstring
coverage is unenforced". The audit's prescription is to lock the standard in
now, "while the modules are well documented", before the command bodies expand
the surface.

Since that audit, tasks 1.2.1-1.2.4 added a Makefile and CI invocation of
`interrogate` (verified below), so the gate already runs in `make lint` and in
CI. What is **still** genuinely missing — and what this task delivers — is the
**configuration** half of the remediation:

- There is no `[tool.interrogate]` table in `pyproject.toml`. The `100%`
  threshold and the scan scope live **only** as a command-line flag in the
  `Makefile` (`interrogate --fail-under 100 $(PYTHON_TARGETS)`, `Makefile`
  line 96). interrogate's own default `fail-under` is `80.0` (verified against
  `interrogate/config.py` line 57 and the official docs), so anyone who runs a
  bare `interrogate` (outside the Makefile, e.g. an IDE plugin, a pre-commit
  hook, or a contributor typing `uv run interrogate`) silently gets the 80%
  default, not the project's 100% standard. The standard is therefore not
  self-documenting and not robust to invocation outside the one Makefile line.
- There is no guard test that pins the gate's wiring (threshold, scan scope,
  and the Makefile/CI invocation), so a future edit that lowers `--fail-under`,
  drops the `interrogate` line, or removes the dev dependency would not be
  caught by `make test`.

The deliverable is therefore a **self-documenting, pinned docstring-coverage
gate**: a `[tool.interrogate]` configuration block in `pyproject.toml` that
records the 100% threshold and the intended scan behaviour as data; a `Makefile`
adjusted so the threshold is sourced from that config rather than re-spelt as a
literal flag (the `Makefile` still passes the paths, because interrogate's
config does not carry the path list); a guard test that asserts the
configuration, the Makefile invocation, and the dev dependency are all present
and mutually consistent; and reconciliation of **all** prose homes of the old
literal so contributors read one authoritative statement of the standard. An
exhaustive `git grep -niE 'interrogate.*(fail.under|100)'` across tracked files
(excluding `docs/execplans` and `uv.lock`) returns **exactly five** homes of the
literal, and this enumeration is provably complete:

1. `Makefile` line 96 — the recipe being changed (the source of truth being
   migrated to config).
2. **AGENTS.md** line 86 — inside the "generated Makefile wiring" list (a prose
   home).
3. **`docs/developers-guide.md`** line 12 — the one-line gate statement (a prose
   home).
4. **`docs/developers-guide.md`** line 157 — the CI-job paragraph (a prose home).
5. **`docs/users-guide.md`** line 18 — the user-facing description of what
   `lint-python` runs (a prose home).

So there are **four prose homes across three files** (AGENTS.md, the developers'
guide twice, and the users' guide), all of which currently spell the gate as
`interrogate --fail-under 100 $(PYTHON_TARGETS)`. When the Makefile drops the
literal `--fail-under 100`, those four prose statements become factually false
unless updated in the same change, so they are all part of the edit set (see
Constraints and work items 2-4). The design document
(`docs/novel-ralph-harness-design.md`) does **not** describe interrogate at all
(verified: grepping it for `interrogate`, `fail-under`, and `docstring coverage`
returns zero hits), so it is **not** an edit target.

To verify the implementation: `make lint` still enforces 100% docstring coverage
(now sourced from the config, not a literal CLI threshold) and stays green
against the already-fully-documented package; a new
`tests/test_interrogate_gate.py` asserts that `pyproject.toml` carries a
`[tool.interrogate]` table with `fail-under = 100`, that a single `Makefile`
recipe line invokes `interrogate` over `$(PYTHON_TARGETS)` (same-line
co-occurrence, so deleting the recipe line fails the gate even if some other
`interrogate` or `$(PYTHON_TARGETS)` mention survives), and that `interrogate` is
a declared dev dependency; AGENTS.md line 86, `docs/developers-guide.md`
lines 12-13 and 157, and `docs/users-guide.md` line 18 no longer spell the
dropped `--fail-under 100` literal; and
`make all`, `make markdownlint`, and `make nixie` are all green. Success is
observable as: a bare `uv run interrogate novel_ralph_skill tests` now fails
under 100% rather than passing under the silent 80% default, and any future
weakening of the threshold or removal of the invocation fails `make test`.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- All work must stay exclusively inside the worktree at
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-5`. Files in
  the root/control worktree must not be edited.
- The docstring-coverage **standard is 100%** and must not be weakened. This is
  fixed by AGENTS.md ("Every public module, class, and function carries a
  docstring; `interrogate` enforces 100% coverage", plus the Makefile-wiring
  list at line 86), by the existing `Makefile` flag, by the developers' guide
  (lines 12-13 and the CI paragraph at line 157), by the users' guide (line 18),
  and by roadmap precedent. The
  design document (`docs/novel-ralph-harness-design.md`) does **not** mention
  interrogate (verified by grep: zero hits for `interrogate`, `fail-under`, or
  `docstring coverage`), so it is not a source of this standard and not an edit
  target. This task makes the 100% threshold **self-documenting and pinned**; it
  does not change its value.
- The scan scope stays `$(PYTHON_TARGETS) = novel_ralph_skill tests`
  (`Makefile` line 15). interrogate must continue to scan **both** the package
  and the test tree, because every test function in the repo already carries a
  docstring and the 100% standard applies to tests too (verified: `make lint`
  passes today over both targets). This task does not narrow the scope, add an
  `exclude`, or stop scanning `tests/`.
- The externally observable behaviour of `make lint`, `make all`, and CI is
  unchanged in outcome: the package is already at 100% coverage, so the gate
  stays green before and after. This task adds configuration and a guard test;
  it must not cause any currently-passing gate to start failing, nor relax any
  gate.
- No new runtime or dev dependency. `interrogate` is already in
  `[dependency-groups] dev` (`pyproject.toml` line 20) and locked at `1.7.0`
  (`uv.lock`). `tomllib` is standard-library on Python 3.14
  (`requires-python = ">=3.14"`, `pyproject.toml` line 6) and is already used by
  `tests/test_pyproject_scripts.py` and `tests/test_command_names_registry.py`
  for the guard-test pattern. syrupy, hypothesis, and CrossHair are **not**
  locked (`uv.lock`); this task must not add them (see Decision Log).
- This task is **pure configuration plus packaging plus one guard test**. It
  adds no command behaviour, emits no program output, shells out to nothing at
  runtime, and touches no command body, the `make_stub_app` factory, the cuprum
  run-loop in `tests/test_console_scripts_e2e.py`, the command-name registry, or
  the `[project.scripts]` table. It does not introduce the shared JSON envelope
  or the `--human` switch (roadmap step 1.3).
- Prose, comments, docstrings, and commit messages use en-GB Oxford spelling
  ("-ize"/"-yse"/"-our"), per AGENTS.md and the `en-gb-oxendict` convention.
- Every public module, class, and function carries a docstring; `interrogate`
  enforces 100% coverage (the gate this task pins). No file exceeds 400 lines
  (AGENTS.md).
- Tests live in the top-level `tests/` tree, never inside the package (AGENTS.md
  "Python verification and testing"; the `novel_ralph_skill` package contains no
  tests so xdist-backed SlipCover coverage stays correct).
- Markdown prose wraps at 80 columns; code blocks at 120; tables and headings
  are not wrapped; list bullets use `-`; Mermaid is validated by nixie
  (AGENTS.md "Markdown guidance").

## Tolerances (exception triggers)

- Scope: if implementation requires changes to more than 8 files or more than
  140 net lines, stop and escalate. Expected files (seven besides this plan):
  this plan; `pyproject.toml` (the new `[tool.interrogate]` table); `Makefile`
  (the `lint-python` recipe line, to source the threshold from config);
  `tests/test_interrogate_gate.py` (new guard test); `AGENTS.md` (line 86, to
  drop the now-removed `--fail-under 100` literal from the Makefile-wiring list);
  `docs/developers-guide.md` (lines 12-13 and line 157, to drop the same literal
  and name the config); `docs/users-guide.md` (line 18, to drop the same literal
  from the user-facing `lint-python` description and name the config). This edit
  set is provably complete: the exhaustive `git grep` recorded in Purpose returns
  exactly these five homes of the literal (Makefile plus four prose statements),
  so no sixth doc can silently go stale. `docs/novel-ralph-harness-design.md` is
  **not** in the edit set (it does not mention interrogate). If a sixth home of
  the literal is found before committing, or any **command body**, the
  `make_stub_app` factory, the cuprum run-loop, the command-name registry, or
  the `[project.scripts]` targets must change, stop and escalate — that is
  outside 1.2.5.
- Threshold: the threshold is `100`. If the package is found **not** to be at
  100% coverage when the literal `--fail-under 100` flag is dropped in favour of
  the config (i.e. removing the flag changes the gate's pass/fail outcome), stop
  and escalate rather than lowering the threshold or adding an `exclude` to make
  the gate pass.
- Makefile recipe: this plan's chosen approach (option (a), see Decision Log) is
  to **keep** `interrogate` invoked from `make lint-python` and source the
  `fail-under` threshold from `[tool.interrogate]` (dropping the literal
  `--fail-under 100` from the recipe, keeping the `$(PYTHON_TARGETS)` paths), and
  to **reconcile** all four prose homes — AGENTS.md line 86,
  `docs/developers-guide.md` lines 12-13 and 157, and `docs/users-guide.md`
  line 18 — in the same change so no doc goes stale. The belt-and-braces
  alternative (option (b)) — **retain** the explicit `--fail-under 100` flag in
  the recipe so the gate is robust even if the config table is deleted, leaving
  AGENTS.md, the developers' guide, and the users' guide untouched — is a
  materially different decision about the source of truth. It is **not** the
  default: if the implementer finds reason to prefer it (for example, the
  reconciliation edits would exceed the file-count tolerance, a sixth prose home
  is discovered, or interrogate fails to honour the config on the target
  machine), stop and escalate so the recipe, the config, the guard test,
  AGENTS.md, the developers' guide, and the users' guide are made consistent
  rather than half-migrated.
- Dependencies: this task adds **no** new runtime or dev dependency. If the
  guard test appears to need syrupy, hypothesis, CrossHair, or any new package,
  stop and escalate (it does not: `tomllib` parses `pyproject.toml`, and the
  `Makefile` is read as text; the comparison is direct equality on small fixed
  values).
- Config surface: this plan commits to a **minimal** `[tool.interrogate]` table
  — `fail-under = 100` plus the small set of self-documenting ignore flags that
  match the package's actual structure (see Plan of work). If review prefers a
  larger or smaller set of keys (for example, adding `exclude`,
  `omit-covered-files`, or `style`), that changes what the gate measures; stop
  and escalate rather than adding scope-affecting keys mid-implementation.
- Iterations: if `make all` (or `make markdownlint` / `make nixie`) still fails
  after 3 focused fix attempts on the same gate, stop and escalate.

## Risks

- Risk: dropping the literal `--fail-under 100` from the `Makefile` and relying
  on the `[tool.interrogate]` config silently lowers the gate to interrogate's
  `80.0` default if the config is mis-read (wrong table name, wrong key
  spelling, or interrogate not detecting `pyproject.toml`).
  - Severity: high. Likelihood: low.
  - Mitigation: verified against `interrogate/config.py` (v1.7.0) that the table
    is `[tool.interrogate]` and keys are normalized `-`→`_`
    (`parse_pyproject_toml`, lines 122-136), and that interrogate auto-detects
    `pyproject.toml` from the project root (`find_project_config`, lines
    111-119; `read_config_file`, lines 196-255). The guard test asserts the
    config table exists with `fail-under = 100`. As a runtime check, the
    `Concrete steps` include a transcript proving `interrogate` reports
    `minimum: 100.0%` (not `80.0%`) when run with the config and **no** literal
    flag, confirming the config is honoured before the literal flag is removed.
    If the transcript shows `minimum: 80.0%`, this is the Makefile-recipe
    tolerance trigger — stop and escalate (the belt-and-braces option keeps the
    explicit flag).
- Risk: interrogate's config detection depends on the project root containing a
  `.git`/`pyproject.toml` marker; under `uv run` from a worktree the resolution
  could differ from a plain checkout.
  - Severity: medium. Likelihood: low.
  - Mitigation: `find_project_root` (`interrogate/config.py` lines 83-108)
    walks up from the scanned paths to the first directory containing `.git`,
    `.hg`, or `pyproject.toml`; the worktree root has `pyproject.toml`, so
    detection resolves to the worktree root. The `Concrete steps` transcript is
    run from the worktree root (the same cwd `make lint` uses), so the verified
    behaviour matches CI's.
- Risk: a future contributor lowers `fail-under`, deletes the `interrogate`
  line from `make lint-python`, or removes the dev dependency, reintroducing the
  unenforced-coverage gap this task closes.
  - Severity: medium. Likelihood: medium.
  - Mitigation: `tests/test_interrogate_gate.py` parses `pyproject.toml` and
    asserts `[tool.interrogate] fail-under == 100`; reads the `Makefile` text
    and asserts that a **single recipe line** invokes `interrogate` over
    `$(PYTHON_TARGETS)` (same-line co-occurrence); and asserts `interrogate` is
    a declared dev dependency. Any of those regressions fails `make test`, so the
    gate catches the omission rather than letting it ship. AGENTS.md line 86 and
    the developers'-guide lines name the config as the place the standard lives.
- Risk: documentation goes stale when the `--fail-under 100` literal is dropped
  from the Makefile. **Four** prose statements currently spell
  `interrogate --fail-under 100 $(PYTHON_TARGETS)`: AGENTS.md line 86,
  `docs/developers-guide.md` line 12, `docs/developers-guide.md` line 157, and
  `docs/users-guide.md` line 18 (the user-facing description of `lint-python`).
  Leaving any of them after the Makefile change ships a direct contradiction
  between an authoritative or user-facing quality-gate description and the actual
  recipe.
  - Severity: high. Likelihood: high (it is the certain consequence of the
    Makefile edit, not a chance event).
  - Mitigation: all four prose statements are in the edit set (work items 2, 3,
    and 4) and the file-count tolerance (8 files). The edit set is **provably
    complete**: the exhaustive `git grep -niE 'interrogate.*(fail.under|100)'`
    (excluding `docs/execplans` and `uv.lock`) recorded in Purpose returns
    exactly five homes (the Makefile plus those four prose statements) and no
    more, so no doc can silently survive un-reconciled. The plan reconciles all
    four in the same change that edits the Makefile, so the docs and recipe never
    disagree at any committed HEAD. The design document is **not** affected (it
    does not mention interrogate). If the reconciliation would push the change
    past the file-count tolerance, or a sixth home of the literal is discovered,
    that is the Makefile-recipe escalation trigger (prefer option (b), keep the
    literal).
- Risk: the guard test that reads the `Makefile` as text is brittle to harmless
  whitespace or ordering changes in the recipe, or gives a false pass if it only
  checks the two tokens independently (`$(PYTHON_TARGETS)` appears eight times in
  the Makefile, so an edit could delete the interrogate recipe line while another
  `$(PYTHON_TARGETS)` line survives).
  - Severity: medium. Likelihood: medium.
  - Mitigation: the test asserts **same-line co-occurrence** — it iterates the
    Makefile's lines and requires that at least one single line contains both the
    token `interrogate` and the substring `$(PYTHON_TARGETS)`. This is robust to
    reformatting (it is not an exact-line match) yet fails when the interrogate
    recipe line is deleted, even if other `interrogate` or `$(PYTHON_TARGETS)`
    mentions survive. The intent is pinned, not the formatting.
- Risk: adding self-documenting ignore flags (for example `ignore-init-module`)
  to `[tool.interrogate]` changes what is measured and could let an undocumented
  module slip through.
  - Severity: medium. Likelihood: low.
  - Mitigation: the plan's default config sets every `ignore-*` flag that could
    relax measurement to `false` (the interrogate default), so the table is
    documentary and does **not** narrow the gate. The only load-bearing key is
    `fail-under = 100`. Any key that would relax measurement is a
    config-surface tolerance trigger.

## Progress

- [x] Work item 1: Add the `[tool.interrogate]` configuration block to
  `pyproject.toml` (pinning `fail-under = 100` and documenting the gate's
  behaviour as data), and verify a bare `interrogate` run reports the 100%
  minimum from config. Done 2026-06-22: table added after `[tool.pylint.*]`,
  before `[tool.pytest.ini_options]`. Runtime transcript
  `uv run interrogate novel_ralph_skill tests` reports
  `RESULT: PASSED (minimum: 100.0%, actual: 100.0%)` — config governs (not the
  80.0% default). `make all` green. CodeRabbit raised only findings against the
  untracked planning artefact `roadmap-1-2-5.review-r2.md` (not in this edit
  set), so no actionable change.
- [x] Work item 2: Source the threshold from the config in the `Makefile`
  `lint-python` recipe (drop the literal `--fail-under 100`, keep the
  `$(PYTHON_TARGETS)` paths); reconcile AGENTS.md line 86 in the same commit so
  the authoritative quality-gate description does not contradict the recipe; and
  add `tests/test_interrogate_gate.py` pinning the config, the same-line
  invocation, and the dev dependency. Done 2026-06-22 (option (a), chosen
  default): Makefile line 96 now reads `interrogate $(PYTHON_TARGETS)`;
  AGENTS.md line 86 names `[tool.interrogate]` as the threshold's home. Guard
  test groups three example-based methods in `TestInterrogateGate`, parses
  `pyproject.toml` via `tomllib` with `match`-based table narrowing, and matches
  the dev dependency by a PEP 508-robust `_dist_name` regex (handles bare names,
  version specifiers, and extras). `make all` green (45 passed); the live
  transcript still reads `minimum: 100.0%`. CodeRabbit: resolved trivials
  (inline read, split-chain comment, class grouping) and majors (PEP 508 parse,
  `match`/`case` over `isinstance`); skipped one repeated "AGENTS.md is stale"
  finding — AGENTS.md is the live authoritative source for the 100% standard
  (per the standing rules and this plan), so removing the citation would reduce
  accuracy. Surprise: `make fmt` runs mdformat globally and reflowed many
  out-of-scope tracked docs, briefly breaking `make markdownlint`; reverted the
  reflows (stashed) and used targeted `ruff format` instead, restoring 0
  markdownlint errors.
- [x] Work item 3: Update `docs/developers-guide.md` (lines 12-13 and the CI
  paragraph at line 157) so the standard is stated once and points at
  `[tool.interrogate]` as where the threshold lives; do **not** edit the design
  document (it contains no interrogate reference). Run `make markdownlint` and
  `make nixie`. Done 2026-06-22: both prose homes drop `--fail-under 100`; the
  gate statement names `[tool.interrogate]` and the guard test, and the CI
  paragraph reads `interrogate` over `$(PYTHON_TARGETS)`. The design document
  was left untouched (verified: zero interrogate references). `make all`,
  `make markdownlint`, and `make nixie` all green; CodeRabbit returned zero
  findings.
- [x] Work item 4: Update `docs/users-guide.md` (line 18) so the user-facing
  `lint-python` description drops the `--fail-under 100` literal and names
  `[tool.interrogate]` as where the threshold lives. Run `make markdownlint` and
  `make nixie`. Done 2026-06-22: the `lint-python` description now runs
  Interrogate over `$(PYTHON_TARGETS)` and names `[tool.interrogate]` as the
  threshold's home; the surrounding Pylint/`uv tool run` sentences are
  unchanged. The exhaustive `git grep -niE 'interrogate.*(fail.under|100)'`
  (excluding `docs/execplans` and `uv.lock`) afterwards finds no surviving
  `--fail-under 100` literal in any prose; the only matches are the dev-guide
  "enforce 100%" wording and the guard test's intentional `fail-under == 100`
  assertion. `make all`, `make markdownlint`, and `make nixie` all green;
  CodeRabbit returned zero findings.

## Surprises & discoveries

- Observation: the roadmap remediation text ("no configuration or Makefile/CI
  invocation") reflects the **1.2.1-era** state, but the Makefile and CI
  invocation were added by tasks 1.2.1-1.2.4 and are present today.
  - Evidence: `Makefile` line 96 (`interrogate --fail-under 100
    $(PYTHON_TARGETS)`) inside `lint-python`; `.github/workflows/ci.yml` line 45
    (`run: make lint`); AGENTS.md line 86 and `docs/developers-guide.md`
    lines 12-13 (and line 157, the CI paragraph) already describe
    `interrogate --fail-under 100 $(PYTHON_TARGETS)`.
  - Impact: the live gap is the **configuration** half (no `[tool.interrogate]`
    table, threshold only as a CLI literal, no guard test). The plan targets
    that gap, not a from-scratch wiring of the tool.
- Observation: the design document does **not** mention interrogate, contrary to
  the round-1 draft's repeated claim of a design-doc "GitHub Actions" section.
  - Evidence: `grep -ni 'interrogate\|fail-under\|docstring cover'
    docs/novel-ralph-harness-design.md` returns zero matches (exit code 1).
  - Impact: the source map is corrected throughout this plan, and the design doc
    is dropped from the edit set. Work item 3 no longer directs an edit to a
    non-existent section.
- Observation (round 3): an exhaustive repo-wide grep for the literal finds
  **five** homes, not the three the round-2 draft enumerated — the user-facing
  `docs/users-guide.md` line 18 is a fourth prose home that the earlier drafts
  missed because they grepped only AGENTS.md, the developers' guide, and the
  design doc, never the whole tracked tree.
  - Evidence: `git grep -niE 'interrogate.*(fail.under|100)' -- ':!docs/execplans'
    ':!uv.lock'` returns exactly five lines: `Makefile:96`, `AGENTS.md:86`,
    `docs/developers-guide.md:12`, `docs/developers-guide.md:157`, and
    `docs/users-guide.md:18` (exit code 0). The users'-guide line reads "The
    `lint-python` target runs Ruff, then Interrogate with `interrogate
    --fail-under 100 $(PYTHON_TARGETS)` to enforce 100% docstring coverage…".
  - Impact: `docs/users-guide.md` joins the edit set as work item 4; the
    file-count tolerance rises to 8 (seven besides this plan); and every
    "two real homes"/"three statements" enumeration is corrected to "four prose
    homes across three files". Because the grep is exhaustive and pinned in the
    plan, the option-(a) edit set is provably complete: no sixth doc can silently
    contradict the recipe.
- Observation: interrogate's default `fail-under` is `80.0`, so a bare
  `interrogate` invocation (outside the Makefile) silently under-enforces.
  - Evidence: `interrogate/config.py` line 57 (`fail_under = attr.ib(default=
    80.0)`); official docs "RESULT: PASSED (minimum: 80.0%, actual: 100.0%)".
  - Impact: pinning `fail-under = 100` in `[tool.interrogate]` makes the
    standard hold for any invocation that auto-detects `pyproject.toml`, not
    only the one Makefile line — which is the substance of "locking the standard
    in".

## Decision log

- Decision: deliver the **configuration** half of the remediation (a
  `[tool.interrogate]` table pinning `fail-under = 100`, a guard test, and a
  developers'-guide line), not a from-scratch wiring of the tool.
  - Rationale: the Makefile/CI invocation already exists (tasks 1.2.1-1.2.4);
    the remediation's intent — "lock the standard in … cheapest before the
    command bodies expand the surface" — is satisfied by making the threshold
    self-documenting (config), robust to bare invocation, and pinned by a test.
  - Date/Author: 2026-06-22, planning agent.
- Decision (option (a), chosen): make `[tool.interrogate]` in `pyproject.toml`
  the source of truth for the threshold and **drop** the literal `--fail-under
  100` from the `Makefile` recipe (keeping the `$(PYTHON_TARGETS)` paths, which
  the config does not carry), **and reconcile in the same change** all four prose
  homes of the old literal — AGENTS.md line 86, `docs/developers-guide.md`
  lines 12-13 and 157, and `docs/users-guide.md` line 18 — so no authoritative or
  user-facing document goes stale.
  - Rationale: a single source for the threshold avoids drift between a Makefile
    literal and the config; interrogate auto-detects `pyproject.toml` and reads
    `[tool.interrogate]` (verified against `interrogate/config.py`), so the
    config governs every invocation, not only the Makefile's. The paths stay on
    the CLI because interrogate has no `paths` config key — paths are positional
    arguments, and `$(PYTHON_TARGETS)` already names them once in the Makefile.
    AGENTS.md is the project's authoritative quality-gate description, the
    developers' guide is the internal reference, and the users' guide documents
    what `lint-python` runs to a downstream audience; all are tracked and
    editable in the worktree, and leaving any of them spelling the removed literal
    would ship a direct contradiction, so all four prose homes join the edit set
    and the file-count tolerance (raised to 8 files). The edit set is **provably
    complete** because the exhaustive `git grep` (recorded in Purpose and
    Surprises) returns exactly five homes and no more.
  - Alternative (option (b), escalation only): keep the explicit `--fail-under
    100` in the recipe as belt-and-braces (so the gate survives deletion of the
    config table) and leave AGENTS.md, the developers' guide, and the users' guide
    untouched. This
    is **not** the default; it is the Makefile-recipe escalation trigger. Adopt
    it only by stopping and escalating (for example, if the reconciliation edits
    would exceed the file-count tolerance, a sixth prose home is discovered, or
    the config is not honoured on the target machine), so the recipe, config,
    guard test, AGENTS.md, the developers' guide, and the users' guide stay
    consistent rather than half-migrated.
  - Date/Author: 2026-06-22 (round 2; edit set widened round 3), planning agent.
- Decision (round 3): add `docs/users-guide.md` line 18 to the edit set as the
  fourth prose home of the literal, raise the file-count tolerance to 8 (seven
  besides this plan), and record the exhaustive grep that proves the edit set is
  complete before option (a) is committed.
  - Rationale: the round-2 design review found that the literal lives in **five**
    tracked homes, not three — the user-facing `docs/users-guide.md` line 18 was
    missed by the earlier drafts, which grepped only AGENTS.md, the developers'
    guide, and the design doc. Dropping `--fail-under 100` from the Makefile while
    leaving the users' guide untouched would ship exactly the recipe-versus-doc
    contradiction this plan's high-severity staleness risk is meant to prevent,
    and would silently exceed the file-count tolerance. Adding the users' guide
    and pinning the exhaustive `git grep` (exactly five homes) makes the
    option-(a) edit set provably exhaustive.
  - Date/Author: 2026-06-22 (round 3), planning agent.
- Decision: correct the source map — the `interrogate --fail-under 100
  $(PYTHON_TARGETS)` literal lives in AGENTS.md line 86, `docs/developers-guide.md`
  lines 12-13 and 157, and `docs/users-guide.md` line 18 (four prose homes across
  three files), plus the `Makefile` recipe at line 96, and **not** in any
  design-document "GitHub Actions" section. Drop the design document from the edit
  set entirely.
  - Rationale: `grep -ni 'interrogate\|fail-under\|docstring cover'
    docs/novel-ralph-harness-design.md` returns zero hits, while
    `git grep -niE 'interrogate.*(fail.under|100)'` (excluding `docs/execplans`
    and `uv.lock`) returns the five homes above. The round-1 draft attributed the
    literal to a phantom design-doc section, and the round-2 draft under-counted
    the prose homes; naming all four prose homes makes the reconciliation
    actionable and bounds the edit set.
  - Date/Author: 2026-06-22 (round 2; corrected round 3), planning agent.
- Decision: keep the `[tool.interrogate]` table **minimal** — `fail-under = 100`
  plus `ignore-*` flags explicitly set to their non-relaxing defaults
  (documentary), and **no** `exclude`, `omit-covered-files`, or `style` key.
  - Rationale: the only load-bearing key is the threshold; the package and tests
    are already at 100% with every node measured. Setting the ignore flags to
    `false` makes the config self-documenting (a reader sees exactly what is and
    is not exempt) without narrowing the gate. Adding `exclude` or
    `omit-covered-files` would change what is measured; that is a config-surface
    tolerance trigger.
  - Date/Author: 2026-06-22, planning agent.
- Decision: the guard test parses `pyproject.toml` with `tomllib` and reads the
  `Makefile` as text; it does **not** shell out to run `interrogate`.
  - Rationale: `make lint` already runs `interrogate` as the live gate, and the
    e2e build-and-run path is owned by `test_console_scripts_e2e.py`. A pytest
    that re-runs `interrogate` would be slow, redundant, and would duplicate the
    Makefile's job. Pinning the **wiring** (config value, invocation presence,
    dependency presence) by static parse is the precise, fast contract that
    catches the regressions this task guards against. This mirrors the existing
    `tests/test_pyproject_scripts.py` and `tests/test_command_names_registry.py`
    `tomllib` pattern. (Note: the scripting-standards `Catalogue.from_programs`
    example is **not** part of the locked cuprum `0.1.0` public surface —
    `cuprum/__init__.py` `__all__` at tag `v0.1.0` exports `ProgramCatalogue`,
    `ProjectSettings`, `Program`, `sh`, `scoped`, `CommandResult`, not
    `Catalogue`; a subprocess-based guard would have to use that real surface as
    `test_console_scripts_e2e.py` does. The static-parse guard avoids the
    question entirely and shells out to nothing.)
  - Date/Author: 2026-06-22, planning agent.
- Decision: add **no** snapshot (syrupy) or property (hypothesis/CrossHair)
  suite, and run **no** mutation pass (mutmut).
  - Rationale: per `python-verification`, the deliverable is example-based — a
    fixed threshold and a fixed invocation asserted by equality/substring — with
    no generated-input invariant and no multivariant output format. AGENTS.md
    gates snapshots to "multivariant output format consistency" and property
    tests to "an invariant over a range of inputs, states, orderings, or
    transitions"; neither applies. syrupy, hypothesis, and CrossHair are not
    locked; adding them would be an unjustified dependency. mutmut is out of
    scope for a config-and-wiring guard.
  - Date/Author: 2026-06-22, planning agent.

## Outcomes & retrospective

Completed 2026-06-22 (option (a), the chosen default).

- Config that landed: a minimal `[tool.interrogate]` table in `pyproject.toml`
  with `fail-under = 100` (the only load-bearing key) plus every `ignore-*` flag
  pinned to interrogate's non-relaxing default (`false`), so the table is
  documentary and narrows nothing. No `exclude`, `omit-covered-files`, or
  `style` key was added.
- Makefile: option (a) taken — the literal `--fail-under 100` was **removed**
  from the `lint-python` recipe (now `interrogate $(PYTHON_TARGETS)`); the
  threshold is sourced from the config. No escalation to option (b) was needed.
- Reconciliation: all four prose homes were updated — AGENTS.md line 86
  (work item 2), `docs/developers-guide.md` lines 12-13 and 157 (work item 3),
  and `docs/users-guide.md` line 18 (work item 4). The exhaustive
  `git grep -niE 'interrogate.*(fail.under|100)'` (excluding `docs/execplans`
  and `uv.lock`) afterwards finds no surviving `--fail-under 100` literal in any
  prose or in the Makefile.
- Runtime transcript: with the config present and no CLI flag,
  `uv run interrogate novel_ralph_skill tests` reports
  `RESULT: PASSED (minimum: 100.0%, actual: 100.0%)` — the config governs the
  threshold (not interrogate's 80.0% default).
- Files changed (besides this plan): `pyproject.toml`, `Makefile`, `AGENTS.md`,
  `docs/developers-guide.md`, `docs/users-guide.md`, and the new
  `tests/test_interrogate_gate.py` — six files, within the eight-file
  tolerance. Net change is well under the 140-line tolerance.
- The guard test caught no pre-existing mismatch (the package and tests were
  already at 100% and the wiring was consistent); it is the forward guard
  against future regressions.
- CodeRabbit: work item 1 raised only findings against the untracked planning
  artefact (no actionable change). Work item 2 went through three review passes,
  resolving trivials (inline read, split-chain comment, class grouping) and
  majors (PEP 508-robust dependency parse, `match`/`case` over `isinstance`),
  and skipping one repeated "AGENTS.md is stale" finding because AGENTS.md is the
  live authoritative source for the 100% standard. Work items 3 and 4 returned
  zero findings.
- `make all`, `make markdownlint`, and `make nixie` are green at each commit's
  HEAD.

## Context and orientation

The repository is the Python package skeleton becoming the deterministic spine
of the novel-ralph harness. Orient with these files; all paths are relative to
the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-5`:

- `pyproject.toml` — `[dependency-groups] dev` lists `interrogate` (line 20);
  `requires-python = ">=3.14"` (line 6); `[project.scripts]` (lines 10-15);
  Ruff config including `[tool.ruff.lint.pydocstyle] convention = "numpy"`
  (lines 161-162) and the `D` (pydocstyle) selection (line 67). There is
  **no** `[tool.interrogate]` table today — this task adds it.
- `Makefile` — `PYTHON_TARGETS ?= novel_ralph_skill tests` (line 15);
  `lint-python` (lines 94-97) runs Ruff, then
  `interrogate --fail-under 100 $(PYTHON_TARGETS)` (line 96), then PyPy-backed
  Pylint; `lint` depends on `lint-python` (line 92); `all` is
  `build check-fmt lint typecheck test` (line 28).
- `.github/workflows/ci.yml` — the `lint-test` job runs `make lint` (line 45)
  on `ubuntu-latest`, so interrogate runs in CI today.
- `novel_ralph_skill/` — `__init__.py`, `pure.py`, and `commands/`
  (`__init__.py`, `names.py`, `stub.py`); every module, class, and function is
  documented (the package is at 100% coverage; `make lint` passes).
- `tests/` — example-based pytest modules; `test_pyproject_scripts.py` and
  `test_command_names_registry.py` are the `tomllib`-driven guard tests this
  task mirrors. Every test function carries a docstring (interrogate scans
  `tests/` too, at 100%).
- `docs/roadmap.md` lines 118-123 — this task; lines 112-117 — the adjacent
  1.2.4 (the command-name registry, already done).
- `docs/developers-guide.md` lines 12-13 — the one-line statement that
  `make lint` runs `interrogate --fail-under 100 $(PYTHON_TARGETS)` for 100%
  docstring coverage; an edit target (work item 3). Line 157 — the CI-job
  paragraph that repeats the same literal; also an edit target.
- `docs/users-guide.md` lines 17-18 — the user-facing "Quality Gates" prose
  describing what `lint-python` runs: "The `lint-python` target runs Ruff, then
  Interrogate with `interrogate --fail-under 100 $(PYTHON_TARGETS)` to enforce
  100% docstring coverage…". This is the fourth prose home of the literal and an
  edit target (work item 4); it must drop the `--fail-under 100` literal when the
  Makefile recipe does.
- `docs/novel-ralph-harness-design.md` — context only, and **not** an edit
  target: it does not mention interrogate, `fail-under`, or docstring coverage
  (verified by grep, zero hits). There is no design-doc "GitHub Actions" section
  describing the gate; the gate literal lives in AGENTS.md, the developers'
  guide, and the users' guide (and the Makefile recipe), per the exhaustive grep
  recorded in Purpose.
- `AGENTS.md` — "Every public module, class, and function carries a docstring;
  `interrogate` enforces 100% coverage"; the "generated Makefile wiring" list at
  line 86 ("`make lint-python` runs `ruff check …`, enforces 100% docstring
  coverage with `interrogate --fail-under 100 $(PYTHON_TARGETS)`, and runs …
  Pylint"); the quality gates; tests under `tests/`; the 400-line limit; Markdown
  guidance. Line 86 is an edit target (work item 2): it must drop the
  `--fail-under 100` literal when the Makefile recipe does.
- `docs/scripting-standards.md` — the Cyclopts/cuprum conventions (context only;
  this task shells out to nothing at runtime and adds no script). Note its
  `Catalogue.from_programs` examples predate the locked cuprum surface.
- `uv.lock` — pins `interrogate 1.7.0`, `cuprum 0.1.0`, `cyclopts 4.18.0`; does
  **not** contain syrupy, hypothesis, or CrossHair.

External tool facts pinned at planning time (cite when relied on):

- `interrogate` `1.7.0`, source at
  `…/site-packages/interrogate/config.py` (the same version `uv.lock` pins):
  - `[tool.interrogate]` is the pyproject table; keys are normalized by
    replacing `--`/`-` with `_` (`parse_pyproject_toml`, lines 122-136). So
    `fail-under = 100` in TOML becomes `fail_under = 100`.
  - The config "override[s] option defaults, but still respect[s] option values
    provided via the CLI" — it is injected into `ctx.default_map`
    (`read_config_file`, lines 196-255), so a CLI `--fail-under` would **win**
    over the config value. This is why the plan removes the literal flag: with
    no CLI `--fail-under`, the config's `100` governs.
  - The default `fail_under` is `80.0` (`InterrogateConfig`, line 57), so the
    config is load-bearing for any bare invocation.
  - interrogate auto-detects `pyproject.toml` by walking up from the scanned
    paths to the first `.git`/`.hg`/`pyproject.toml` marker
    (`find_project_root`/`find_project_config`, lines 83-119).
- interrogate official docs (`interrogate.readthedocs.io`, v1.7.0): the
  configuration section is `[tool.interrogate]` with hyphenated keys
  (`fail-under = 80`, `ignore-init-method = false`, `ignore-module = false`,
  etc.); "interrogate will automatically detect a pyproject.toml file and pick
  up default values for the command line options". The docs' own tox example
  runs `interrogate --quiet --fail-under 95 src tests` (paths and threshold on
  the CLI even with a config block), confirming paths are positional and not a
  config key.
- cuprum `0.1.0` public surface at tag `v0.1.0`
  (`/data/leynos/Projects/cuprum`, `cuprum/__init__.py` `__all__`): exports
  `ProgramCatalogue`, `ProjectSettings`, `Program`, `sh`, `scoped`,
  `CommandResult` — **not** `Catalogue` or `Catalogue.from_programs`. Relevant
  only to record that the static-parse guard avoids cuprum entirely; the
  existing e2e (`test_console_scripts_e2e.py`) is the in-repo example of the
  real surface.

Terms of art, defined so the plan is self-contained:

- **Docstring coverage.** The fraction of modules, classes, methods, and
  functions that carry a docstring, as measured by `interrogate`. 100% means
  every such node is documented.
- **`fail-under`.** interrogate's threshold: it exits non-zero (failing the
  gate) when measured coverage is below this percentage. Default `80.0`; the
  project requires `100`.
- **Guard test.** A fast, example-based pytest that pins a configuration or
  wiring fact (here: the threshold value, the Makefile invocation, the
  dependency) so a regression fails `make test` rather than shipping silently.

Skills to load before touching code (per the global agent instructions and the
worktree standing rules):

- `python-router` first, to route to the smaller skills below.
- `python-testing` for the guard-test shape (a fast `tomllib`-driven parse of
  `pyproject.toml` plus a text read of the `Makefile`; robust substring
  assertions, not exact-line matches; full docstrings on test functions so
  interrogate stays at 100% over `tests/`).
- `python-verification` only to confirm that **no** Hypothesis/CrossHair/mutmut
  suite belongs here (example-based fixed-value assertions, not a generative
  contract); `hypothesis`, `crosshair`, and `mutmut` are not loaded or used.
- `leta` for navigating the package and test tree; `sem` for history.
- `en-gb-oxendict` for the docstring and developers'-guide prose.

Authoritative sources to read before editing:

- `docs/roadmap.md` lines 118-123 — task 1.2.5 and its remediation source.
- `AGENTS.md` — the 100% docstring-coverage standard, the Makefile-wiring list
  at line 86 (an edit target), the quality gates, tests-under-`tests/`, the
  400-line limit, the snapshot/property discipline, and Markdown guidance.
- `docs/developers-guide.md` lines 12-13 and line 157 — the two edit targets in
  the developers' guide (the gate statement and the CI paragraph).
- `docs/users-guide.md` lines 17-18 — the user-facing "Quality Gates" edit target
  (the `lint-python` description).
- `docs/novel-ralph-harness-design.md` — read for context, but it does **not**
  mention interrogate and is **not** an edit target (verified by grep).
- `.rules/python-00.md`, `.rules/python-return.md`, `.rules/python-pyproject.md`
  — house Python style, return, and packaging conventions.
- `interrogate/config.py` (v1.7.0) and `interrogate.readthedocs.io` — the
  `[tool.interrogate]` table, key normalization, default `fail-under`, and
  config auto-detection (pinned above).

## Plan of work

Four atomic, independently-committable work items, each ending with its own
validation; `make all` must be green before each commit, and every
Markdown-touching work item also runs `make markdownlint` and `make nixie`
(work item 2 edits AGENTS.md, work item 3 edits the developers' guide, and work
item 4 edits the users' guide, so all three run the Markdown gates). The items
are ordered so the configuration lands first and is proven to govern the gate (1),
then the Makefile is migrated to source the threshold from it, AGENTS.md is
reconciled in the same commit, and the guard test pins the wiring (2), then the
developers' guide converges on the single source (3), then the users' guide does
the same (4). Each commit leaves every gate green and ships no contradiction
between the Makefile recipe and any authoritative or user-facing document.

### Work item 1 — Add the `[tool.interrogate]` configuration block

Implements: roadmap task 1.2.5 ("locking the standard in now … `interrogate` …
with no configuration"); AGENTS.md ("`interrogate` enforces 100% coverage").

Add a `[tool.interrogate]` table to `pyproject.toml` (placed beside the other
`[tool.*]` tables, e.g. after `[tool.pylint.*]` and before
`[tool.pytest.ini_options]`, so the tool configuration stays grouped). The table
is minimal and self-documenting; the only load-bearing key is `fail-under`:

```toml
[tool.interrogate]
# Docstring-coverage gate. The project standard is 100% (AGENTS.md): every
# public module, class, and function carries a docstring. This value is the
# single source of truth for the threshold; the Makefile invokes interrogate
# over $(PYTHON_TARGETS) without re-spelling the threshold on the CLI.
fail-under = 100
# Ignore flags pinned to interrogate's non-relaxing defaults so the gate
# measures every node; they are documentary, not exemptions.
ignore-init-method = false
ignore-init-module = false
ignore-magic = false
ignore-private = false
ignore-semiprivate = false
ignore-module = false
ignore-nested-functions = false
```

(The exact key set is pinned by the implementer against the interrogate `1.7.0`
config surface; every `ignore-*` key is set to `false`, matching the tool's
defaults, so the table narrows nothing. Do **not** add `exclude`,
`omit-covered-files`, or `style` — those would change what is measured; that is
the config-surface tolerance trigger.)

Read first: `docs/roadmap.md` lines 118-123; AGENTS.md (the docstring-coverage
standard and Makefile wiring); `.rules/python-pyproject.md`; the interrogate
config facts pinned in `Context and orientation`.

Skills: `python-router`, then `python-verification` (to reconfirm no
property/snapshot suite belongs here). No code module changes in this item.

Tests added/updated: none in this item (the guard test lands in work item 2,
after the Makefile is migrated, so the test asserts the end state). The live
proof for this item is a runtime transcript (see `Concrete steps`): with the
config present and **no** literal `--fail-under` flag, `uv run interrogate
novel_ralph_skill tests` reports `minimum: 100.0%` (not `80.0%`) and passes,
proving the config governs the threshold.

Validation: `make all` stays green (the package is already at 100%, so the gate
— still driven by the unchanged Makefile line 96 in this item — passes); the
transcript confirms the config is honoured. If the transcript shows
`minimum: 80.0%`, stop and escalate (Makefile-recipe tolerance trigger).

### Work item 2 — Source the threshold from config, reconcile AGENTS.md, and pin the wiring with a guard test

Implements: roadmap task 1.2.5 (the Makefile invocation now sources the
threshold from the locked config; the gate is pinned against regression);
AGENTS.md line 86 (the authoritative quality-gate description) is kept truthful.

In `Makefile` `lint-python` (lines 94-97):

- Change the interrogate line from
  `$(UV_ENV) $(UV) run interrogate --fail-under 100 $(PYTHON_TARGETS)` to
  `$(UV_ENV) $(UV) run interrogate $(PYTHON_TARGETS)`, so the threshold is
  sourced from `[tool.interrogate] fail-under = 100` rather than a CLI literal.
  The `$(PYTHON_TARGETS)` paths stay on the CLI (interrogate has no `paths`
  config key). Everything else in the recipe (Ruff, Pylint) is unchanged.
  (Chosen approach, option (a), per Decision Log; the belt-and-braces
  alternative — keep the explicit `--fail-under 100` — is the Makefile-recipe
  escalation trigger.)

In `AGENTS.md` (line 86, inside the "generated Makefile wiring" list under
`make lint`):

- Drop the now-removed `--fail-under 100` literal so the description matches the
  recipe. Change "enforces 100% docstring coverage with `interrogate
  --fail-under 100 $(PYTHON_TARGETS)`" to read, for example, "enforces 100%
  docstring coverage by running `interrogate` over `$(PYTHON_TARGETS)` with the
  threshold pinned in `[tool.interrogate]` in `pyproject.toml`". Keep it factual,
  one or two wrapped lines at the file's prose width, en-GB Oxford spelling.
  Reconcile AGENTS.md in the **same commit** as the Makefile edit so no committed
  HEAD ships a contradiction between AGENTS.md and the recipe.

Add `tests/test_interrogate_gate.py`, the guard that pins the gate's wiring:

1. Parse `pyproject.toml` with `tomllib` and assert
   `data["tool"]["interrogate"]["fail-under"] == 100`, so the threshold cannot
   be silently lowered.
2. Read the `Makefile` text and assert that a **single recipe line** contains
   **both** the token `interrogate` and the substring `$(PYTHON_TARGETS)`
   (iterate the lines and require co-occurrence on one line; do **not** perform
   two independent whole-file substring checks, because `$(PYTHON_TARGETS)`
   appears eight times and a future edit could delete the interrogate recipe line
   while another mention survives). This is robust to reformatting yet fails when
   the interrogate invocation is removed.
3. Assert `interrogate` is a declared dev dependency
   (`data["dependency-groups"]["dev"]` contains an entry whose distribution name
   is `interrogate`), so removing the dependency fails the gate.

Read first: `Makefile` lines 92-97; `AGENTS.md` lines 81-92 (the Makefile-wiring
list); `pyproject.toml` lines 17-28 and the new `[tool.interrogate]` table;
`tests/test_pyproject_scripts.py` and `tests/test_command_names_registry.py`
(the `tomllib` guard pattern to mirror); `.rules/python-00.md`,
`.rules/python-return.md`.

Skills: `python-router`, then `python-testing` (the `tomllib` + text-read
guard); `en-gb-oxendict` for the AGENTS.md prose edit.

Tests added/updated:

- `tests/test_interrogate_gate.py` (new) — three example-based tests: the
  `fail-under == 100` config pin, the same-line Makefile-invocation pin, and the
  dev-dependency pin. Each test function carries a docstring (interrogate scans
  `tests/`). This is the load-bearing new gate that makes the standard
  enforceable against future regressions.

Validation: `make lint` still enforces 100% (now from config) and is green;
`make test` includes the new guard and passes; `make check-fmt` and
`make typecheck` pass over the new test; `make all` is green. Because AGENTS.md
is Markdown, also run `make markdownlint` and `make nixie` over the AGENTS.md
edit in this commit. Concretely re-confirm the threshold-from-config behaviour
with the `Concrete steps` transcript (now the Makefile no longer passes
`--fail-under`).

### Work item 3 — Reconcile the developers' guide

Implements: roadmap task 1.2.5; AGENTS.md ("Record internally facing conventions
… in `docs/developers-guide.md`").

There are **two** statements of the old literal in this file; both must drop the
removed `--fail-under 100` so the guide matches the Makefile and AGENTS.md.

In `docs/developers-guide.md` lines 12-13 (the one-line gate statement):

- Update the sentence so it states the standard once and names
  `[tool.interrogate]` in `pyproject.toml` as where the threshold lives, e.g.:
  "`make lint` runs Ruff, `interrogate` over `$(PYTHON_TARGETS)` to enforce 100%
  docstring coverage (the threshold is pinned in `[tool.interrogate]` in
  `pyproject.toml`; `tests/test_interrogate_gate.py` guards it), and Pylint."
  Keep it to one or two wrapped lines at 80 columns; do not restate the whole
  gate. (Exact wording pinned by the implementer; en-GB Oxford spelling.)

In `docs/developers-guide.md` line 157 (the CI-job paragraph describing
`.github/workflows/ci.yml` running `make lint`):

- This line currently reads "`make lint` (Ruff + `interrogate --fail-under 100
  $(PYTHON_TARGETS)` + Pylint)". Drop the `--fail-under 100` literal so it reads,
  for example, "`make lint` (Ruff + `interrogate` over `$(PYTHON_TARGETS)` +
  Pylint)" — the CI job runs the same recipe, so it must not re-spell the removed
  flag. This is the only "GitHub Actions"-flavoured statement of the gate; it is
  in the developers' guide, **not** in the design document.

Do **not** edit `docs/novel-ralph-harness-design.md`: it contains no interrogate
reference (verified by grep), so there is no design-doc sentence to reconcile.

Read first: `docs/developers-guide.md` lines 12-13 and 150-160 (the CI
paragraph); `docs/documentation-style-guide.md`; AGENTS.md "Markdown guidance".

Skills: `python-router` (context), then `en-gb-oxendict` for the prose.

Tests added/updated: none (documentation only; the guard test from work item 2
already pins the underlying wiring).

Validation: `make markdownlint` and `make nixie` pass over the edited doc;
`make all` is green.

### Work item 4 — Reconcile the users' guide

Implements: roadmap task 1.2.5; AGENTS.md ("Record externally facing
documentation … in `docs/users-guide.md`"). This is the fourth and final prose
home of the literal, surfaced by the exhaustive `git grep` recorded in Purpose;
reconciling it makes the option-(a) edit set complete.

In `docs/users-guide.md` lines 17-18 (the "Quality Gates" description of what
`lint-python` runs):

- The prose currently reads: "The `lint-python` target runs Ruff, then
  Interrogate with `interrogate --fail-under 100 $(PYTHON_TARGETS)` to enforce
  100% docstring coverage for the Python targets, then Pylint via a PyPy-backed
  runner." Drop the `--fail-under 100` literal and name `[tool.interrogate]` as
  where the threshold lives, e.g.: "The `lint-python` target runs Ruff, then
  Interrogate over `$(PYTHON_TARGETS)` to enforce 100% docstring coverage for the
  Python targets (the threshold is pinned in `[tool.interrogate]` in
  `pyproject.toml`), then Pylint via a PyPy-backed runner." Keep the surrounding
  sentences (the Pylint runner, the `uv tool run` note) unchanged; wrap at 80
  columns; en-GB Oxford spelling. (Exact wording pinned by the implementer.)

Do **not** touch any other section of the users' guide (the `make all` target
list, the pytest-discovery paragraph, or the Rust sections are out of scope).

Read first: `docs/users-guide.md` lines 1-26 (the "Quality Gates" section);
`docs/documentation-style-guide.md`; AGENTS.md "Markdown guidance".

Skills: `python-router` (context), then `en-gb-oxendict` for the prose.

Tests added/updated: none (documentation only; the guard test from work item 2
already pins the underlying wiring; the repo's guards do not pin prose, by
design).

Validation: `make markdownlint` and `make nixie` pass over the edited doc;
`make all` is green. After this commit, re-run the exhaustive
`git grep -niE 'interrogate.*(fail.under|100)' -- ':!docs/execplans' ':!uv.lock'`
and confirm the only surviving home is `Makefile:96` reduced to the no-flag form
— i.e. the literal `--fail-under 100` no longer appears in any tracked prose.

## Concrete steps

All commands run from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-5`.

Confirm the branch first:

```bash
git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-2-5 \
  branch --show-current
```

Expect `roadmap-1-2-5`.

Confirm the edit set is exhaustive before changing the Makefile (option (a)):

```bash
git grep -niE 'interrogate.*(fail.under|100)' -- ':!docs/execplans' ':!uv.lock'
# expect EXACTLY five lines (the literal's only homes):
#   Makefile:96
#   AGENTS.md:86
#   docs/developers-guide.md:12
#   docs/developers-guide.md:157
#   docs/users-guide.md:18
# If a sixth line appears, the edit set is incomplete — stop and escalate
# (add the new home or take option (b)).
```

Re-verify the load-bearing facts on the target machine before relying on them
(verified at planning time against `interrogate/config.py` and the official
docs):

```bash
# interrogate is the locked 1.7.0 and on PATH via uv
uv run interrogate --version
# expect: interrogate 1.7.0

# Baseline: the package is at 100% today (proves the gate stays green).
uv run interrogate -v novel_ralph_skill tests
# expect: RESULT: PASSED (minimum: 80.0%, actual: 100.0%)   [before config]
```

After work item 1 (config added; Makefile still has the literal flag), prove the
config governs the threshold when no CLI flag is passed:

```bash
uv run interrogate novel_ralph_skill tests
# expect: RESULT: PASSED (minimum: 100.0%, actual: 100.0%)
# KEY: minimum must read 100.0%, NOT 80.0%. If it reads 80.0%, the config is
# not being honoured — stop and escalate (Makefile-recipe tolerance trigger).
```

Per-work-item validation:

```bash
make all          # build check-fmt lint typecheck test (work items 1, 2, 3, 4)
make markdownlint # AGENTS.md (item 2), dev-guide (item 3), users-guide (item 4)
make nixie        # Mermaid validation (items 2, 3, 4; no diagrams expected)
```

Expected high-level transcript after work item 2 (illustrative):

```plaintext
$ make test
... tests/test_interrogate_gate.py::test_fail_under_is_one_hundred PASSED
... tests/test_interrogate_gate.py::test_makefile_invokes_interrogate PASSED
... tests/test_interrogate_gate.py::test_interrogate_is_a_dev_dependency PASSED
===== N passed in Xs =====

$ make lint
... interrogate novel_ralph_skill tests
RESULT: PASSED (minimum: 100.0%, actual: 100.0%)
```

## Validation and acceptance

Acceptance, phrased as observable behaviour:

- `pyproject.toml` carries a `[tool.interrogate]` table with `fail-under = 100`
  and `ignore-*` flags pinned to their non-relaxing defaults; the threshold is
  recorded once, as data.
- A bare `uv run interrogate novel_ralph_skill tests` (no `--fail-under` flag)
  reports `minimum: 100.0%` and passes, proving the config governs the gate.
- `make lint` enforces 100% docstring coverage sourced from the config (the
  Makefile recipe no longer re-spells the threshold), and is green against the
  already-fully-documented package and tests.
- `tests/test_interrogate_gate.py` pins the gate: it asserts the config
  `fail-under == 100`, that a single Makefile recipe line invokes `interrogate`
  over `$(PYTHON_TARGETS)` (same-line co-occurrence), and that `interrogate`
  is a declared dev dependency; any regression fails `make test`.
- AGENTS.md line 86, `docs/developers-guide.md` lines 12-13 and 157, and
  `docs/users-guide.md` line 18 no longer spell the removed `--fail-under 100`
  literal; they state the standard and name `[tool.interrogate]` as where the
  threshold lives. The exhaustive `git grep` for the literal returns no prose home
  afterwards (only the reduced Makefile recipe survives, without the flag). The
  design document is untouched (it never mentioned interrogate).

Quality criteria (what "done" means):

- Tests: `make test` passes; `tests/test_interrogate_gate.py` is present and
  green; all pre-existing suites still pass.
- Lint/typecheck: `make lint` (Ruff, `interrogate` at 100% from config, Pylint),
  `make check-fmt` (`ruff format --check`), and `make typecheck` (`ty check`)
  all pass; the new test carries full docstrings (interrogate at 100% over
  `tests/`).
- Markdown/Mermaid: `make markdownlint` and `make nixie` pass over the edited
  doc(s).
- Aggregate: `make all` is green at each code work item's commit.

Quality method (how it is checked): run the `Concrete steps` transcript to prove
the config governs the threshold; run `make all` before and after each code work
item; run `make markdownlint` and `make nixie` after the documentation edit in
work item 3.

## Idempotence and recovery

- The `[tool.interrogate]` table is pure declarative configuration; adding it is
  re-runnable and deterministic.
- The guard test is pure (a `tomllib` parse and a text read of `Makefile`);
  re-running it is deterministic and touches no tracked file or `working/`
  state.
- The Makefile edit is a one-line change (drop the literal flag); re-running
  `make all` rebuilds the venv and re-runs the suite from a clean state.
- If a Markdown gate fails, re-wrap the edited line to 80 columns and re-run
  `make markdownlint`.
- If `make build` leaves a partial environment, `make clean` then `make build`
  restores a known state.
- No step is destructive to tracked files beyond the intended edits and updates
  to this execplan.

## Artifacts and notes

- Locked versions, verified: `interrogate 1.7.0`, `cuprum 0.1.0`,
  `cyclopts 4.18.0` (`uv.lock`); syrupy, hypothesis, and CrossHair are **not**
  locked, so no snapshot or property suite is added.
- `[tool.interrogate]` config behaviour pinned against `interrogate/config.py`
  (v1.7.0): table name `[tool.interrogate]`, keys normalized `-`→`_`, default
  `fail_under = 80.0`, config injected into `ctx.default_map` so a CLI
  `--fail-under` would override it (hence the literal flag is removed),
  `pyproject.toml` auto-detected from the project root. Corroborated by the
  interrogate official docs (v1.7.0).
- `tomllib` is standard-library on Python 3.14 (`requires-python = ">=3.14"`)
  and is already used by `tests/test_pyproject_scripts.py` and
  `tests/test_command_names_registry.py`; the new guard reuses that pattern with
  no new dependency.
- The scripting-standards `Catalogue.from_programs` example is **not** part of
  the locked cuprum `0.1.0` public surface (`cuprum/__init__.py` `__all__` at
  tag `v0.1.0`); the static-parse guard shells out to nothing, so this mismatch
  does not affect the plan. Recorded here so a future implementer does not reach
  for `Catalogue.from_programs` if they instead choose a subprocess guard.
- Scope fences restated: this task does **not** change any command body, the
  `make_stub_app` factory, the cuprum run-loop, the command-name registry, the
  venv resolver, the `slow`/`timeout` markers, or the `[project.scripts]`
  targets; it does **not** rename, add, or remove a command; it does **not**
  introduce the JSON envelope (step 1.3) or any new dependency; it does **not**
  narrow the interrogate scan scope or add an `exclude`.

## Interfaces and dependencies

Dependencies: **no change** to `[project] dependencies` or `[dependency-groups]
dev`, and no change to `uv.lock`. This task adds no runtime and no test
dependency; it configures and pins the already-locked `interrogate 1.7.0`.

New configuration (illustrative; the implementer pins the exact key set against
the interrogate `1.7.0` surface):

```toml
# pyproject.toml
[tool.interrogate]
fail-under = 100
ignore-init-method = false
ignore-init-module = false
ignore-magic = false
ignore-private = false
ignore-semiprivate = false
ignore-module = false
ignore-nested-functions = false
```

Guard-test shape (illustrative; assertions pinned by the implementer; each test
carries a docstring):

```python
# tests/test_interrogate_gate.py
import tomllib
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _pyproject() -> dict:
    """Parse and return the worktree ``pyproject.toml`` as a dict."""
    text = (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def test_fail_under_is_one_hundred() -> None:
    """The interrogate gate is pinned to 100% docstring coverage."""
    assert _pyproject()["tool"]["interrogate"]["fail-under"] == 100


def test_makefile_invokes_interrogate() -> None:
    """A single Makefile recipe line runs interrogate over the Python targets."""
    makefile = (_PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    # Same-line co-occurrence: deleting the interrogate recipe line must fail
    # this gate even though $(PYTHON_TARGETS) appears on several other lines.
    assert any(
        "interrogate" in line and "$(PYTHON_TARGETS)" in line
        for line in makefile.splitlines()
    )


def test_interrogate_is_a_dev_dependency() -> None:
    """interrogate is declared as a dev dependency so the gate is installable."""
    dev = _pyproject()["dependency-groups"]["dev"]
    assert any(spec.split()[0].split("[")[0] == "interrogate" for spec in dev)
```

Makefile change (illustrative): the `lint-python` recipe's interrogate line
becomes `$(UV_ENV) $(UV) run interrogate $(PYTHON_TARGETS)` (the literal
`--fail-under 100` is dropped; the threshold is sourced from
`[tool.interrogate]`).

Out of scope (do not build here): any command body, `make_stub_app`, registry,
or `[project.scripts]` change; a rename/add/remove of a command; the JSON
envelope or `--human` switch (step 1.3); any narrowing of the interrogate scan
scope or an `exclude`; any new dependency; any snapshot (syrupy) or property
(hypothesis/CrossHair) suite; any mutation pass (mutmut).

## Revision note

- 2026-06-22 (planning round 1): Authored the self-contained plan against the
  locked toolchain. Discovered that the roadmap remediation text ("no
  configuration or Makefile/CI invocation") reflects the 1.2.1-era state; the
  Makefile (`interrogate --fail-under 100 $(PYTHON_TARGETS)`, line 96) and CI
  (`make lint`) invocation were added by tasks 1.2.1-1.2.4 and exist today.
  Re-scoped the task to its live gap: the **configuration** half. Pinned,
  against `interrogate/config.py` (v1.7.0) and the official docs, that
  `[tool.interrogate]` is the pyproject table, keys normalize `-`→`_`, the
  default `fail-under` is
  `80.0`, the config is injected into `ctx.default_map` (so a CLI `--fail-under`
  overrides it), and `pyproject.toml` is auto-detected from the project root.
  Decided to make `[tool.interrogate] fail-under = 100` the single source of
  truth and drop the Makefile literal (recording the belt-and-braces alternative
  as a tolerance trigger), to keep the config minimal (only `fail-under` is
  load-bearing; ignore flags are documentary), and to pin the wiring with a fast
  `tomllib`/text guard test rather than a subprocess run. Confirmed via
  `python-verification` that no snapshot/property/mutation suite is warranted.
  Noted that the scripting-standards `Catalogue.from_programs` example is not in
  the locked cuprum `0.1.0` surface, so the static-parse guard avoids cuprum
  entirely. Decomposed into three atomic work items (config; Makefile + guard
  test; documentation) and fenced out command bodies, the registry, the JSON
  envelope, and any scope narrowing. The plan remains DRAFT pending review.
- 2026-06-22 (planning round 2): Resolved the two blocking defects from the
  round-1 Logisphere design review. (1) AGENTS.md staleness: adopted option (a)
  — config is the single source of truth, the Makefile drops `--fail-under 100`,
  and AGENTS.md line 86 is reconciled in the **same commit** (work item 2) so no
  authoritative document contradicts the recipe. Added AGENTS.md to the edit set,
  raised the file-count tolerance from 6 to 7, added a high-severity
  documentation-staleness risk, and recorded option (b) (keep the literal) as an
  explicit escalation-only alternative, not a silent default. (2) Misattributed
  source: corrected throughout — verified by grep that
  `docs/novel-ralph-harness-design.md` mentions interrogate **nowhere**, so the
  phantom "design-doc GitHub-Actions section" references in Purpose, Constraints,
  Surprises, Context, Authoritative sources, and work item 3 are removed. The two
  real homes of the literal are named: AGENTS.md line 86 and
  `docs/developers-guide.md` lines 12-13 and 157. Work item 3 now reconciles both
  developers'-guide lines and explicitly does **not** touch the design doc. Also
  actioned the advisory: the Makefile guard test now asserts **same-line**
  co-occurrence of `interrogate` and `$(PYTHON_TARGETS)` (illustrative code and
  prose updated) so deleting the recipe line fails the gate even though
  `$(PYTHON_TARGETS)` appears eight times. Updated the Markdown-gate notes so
  both work item 2 (AGENTS.md) and work item 3 (developers' guide) run
  `make markdownlint` and `make nixie`. The plan remains DRAFT pending review.
- 2026-06-22 (planning round 3): Resolved the single round-2 blocking defect — the
  incomplete edit set. An exhaustive `git grep -niE
  'interrogate.*(fail.under|100)'` (excluding `docs/execplans` and `uv.lock`)
  proves the literal has **exactly five** tracked homes: `Makefile:96`,
  `AGENTS.md:86`, `docs/developers-guide.md:12`, `docs/developers-guide.md:157`,
  and the previously-missed user-facing `docs/users-guide.md:18`. Added
  `docs/users-guide.md` (line 18) to the edit set as new **work item 4** (a
  Markdown doc, so it runs `make markdownlint` and `make nixie`); raised the
  file-count tolerance from 7 to 8 (seven besides this plan) and added the users'
  guide to its enumeration; corrected every "two real homes"/"three statements"
  enumeration to "four prose homes across three files" in Purpose, Constraints,
  the staleness Risk, Surprises, the Decision Log, Context, Authoritative sources,
  the Plan-of-work intro, and Validation; pinned the exhaustive grep as both a
  Surprises observation and a mandatory `Concrete steps` pre-flight check so the
  option-(a) edit set is provably complete before the Makefile is changed; and
  recorded a "sixth home discovered" condition as an additional Makefile-recipe
  escalation trigger. The plan remains DRAFT pending review.
