# Extract a shared envelope-`messages`-carrying exception base for the domain error types

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: COMPLETE

## Purpose / big picture

Three domain exception types hand-repeat the same `messages`-carrying
`__init__`: `StateInputError` (in `novel_ralph_skill/contract/runner.py`), and
`RulePackError` plus `RulePackFileError` (both in
`novel_ralph_skill/rulepack/errors.py`). Each stores
`self.messages: tuple[str, ...]` so the command body can build the contract's
JSON envelope (`messages` field, design §3.1; ADR-003 §"Functional
requirements"). Because the storage logic is copied across three sites in two
layers, a future change to the envelope-messages contract — for example
normalising or validating the prose, or changing how it is frozen — must be
mirrored in three places, and the three can silently drift.

After this change, a single base exception, `EnvelopeMessagesError`, lives in a
neutral `novel_ralph_skill/contract` module and records
`self.messages: tuple[str, ...]` exactly once. The three domain exceptions
subclass it; `RulePackError` adds its own `rule_id` attribute. The
freeze-on-construct decision (that `messages` is captured once as an immutable
tuple) then has one home.

Success is observable three ways. First, a new unit test asserts that all
three domain exceptions are subclasses of `EnvelopeMessagesError` and that an
instance of each carries its `messages` tuple verbatim. Second, the existing
suites that exercise these exceptions — `tests/test_rulepack_schema.py`,
`tests/test_rulepack_loader.py`, `tests/test_rulepack_properties.py`,
`tests/test_contract_runner.py`, `tests/test_contract_properties.py` — continue
to pass unchanged in behaviour, proving the refactor is behaviour-preserving.
Third, `make all` passes (build, format check, lint including N818 naming and
100% `interrogate` docstring coverage, type check via `ty`, and the full pytest
suite under xdist).

This is a pure-Python, internal refactor. It touches no command-line surface,
no envelope wire format, no cuprum-driven subprocess execution, and no external
library behaviour. It serves the step-1.3 shared-contract-scaffolding
hypothesis (one envelope contract for every command), per roadmap task 1.3.4.

## Constraints

Hard invariants that must hold throughout implementation.

- **Layering direction (roadmap 1.3.4; design §3.1).** `rulepack` may depend on
  a `contract` base, never the reverse. The new base must live in the
  `contract` package; `novel_ralph_skill/rulepack/errors.py` imports it.
  `novel_ralph_skill/contract` must not import anything from
  `novel_ralph_skill/rulepack`.
- **No public-surface drift.** The names `StateInputError`, `RulePackError`,
  and `RulePackFileError`, their import paths
  (`novel_ralph_skill.contract.runner.StateInputError`,
  `novel_ralph_skill.rulepack.errors.RulePackError`,
  `novel_ralph_skill.rulepack.errors.RulePackFileError`), their re-exports from
  `novel_ralph_skill.contract.__init__` and `novel_ralph_skill.rulepack`
  `__init__`, and their constructor signatures (`StateInputError(*messages)`,
  `RulePackFileError(*messages)`, `RulePackError(*messages, rule_id=None)`)
  must all remain exactly as they are today. Consumers
  (`commands/novel_state.py`, `rulepack/parse.py`, `contract/runner.py`,
  `tests/conftest.py`) must not need edits to keep compiling.
- **Distinctness invariant (existing test must keep passing).**
  `tests/test_rulepack_schema.py::test_the_two_error_types_are_distinct` asserts
  `RulePackError` and `RulePackFileError` are not subclasses of one another. A
  shared common ancestor is permitted (and intended); a sibling-of-each-other
  relationship is not. The hierarchy must remain a fan-out from the base, not a
  chain.
- **`messages` immutability.** `self.messages` must remain a `tuple[str, ...]`
  captured once at construction (today it is the `*messages` varargs tuple,
  which is already immutable). Do not weaken it to a list or a re-aliased
  mutable sequence.
- **No new dependency.** Use only the standard library and the existing
  package. Do not add a dependency to `pyproject.toml`.
- **en-GB Oxford spelling** ("-ize"/"-yse"/"-our") in all docstrings, comments,
  and the commit message (AGENTS.md house style).
- **Docstring coverage stays at 100%.** Every new public class and `__init__`
  must carry a docstring; `interrogate` is pinned at the `[tool.interrogate]`
  threshold and runs in `make lint`.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- **Scope.** If the change touches more than 6 source/test files or more than
  ~160 net lines of code, stop and escalate; this is a small extraction.
- **Interface.** If any of the three exception constructor signatures, names, or
  import paths must change to make the refactor work, stop and escalate — that
  contradicts a Constraint.
- **Dependencies.** If a new external dependency seems required, stop and
  escalate (none should be).
- **Iterations.** If `make all` still fails after 3 fix attempts on any work
  item, stop and escalate with the failing output.
- **Ambiguity.** If the design or ADR is read to require a different base-class
  shape (for example a frozen dataclass exception, or messages validation),
  stop and present the options before coding.

## Risks

- Risk: A frozen-dataclass-style exception is tempting (to match
  `CommandOutcome`/`RunContext` in `runner.py`), but exceptions must remain
  ordinary classes that call `super().__init__(*messages)` so the base
  `Exception` args/`str()` behaviour is preserved. Severity: medium.
  Likelihood: medium. Mitigation: implement the base as a plain class
  subclassing `Exception`, mirroring the current `__init__` exactly; pin the
  behaviour with a unit test asserting `str(err)` and `err.args` round-trip,
  and that `messages` is a tuple.
- Risk: a shared base could accidentally make `RulePackError` and
  `RulePackFileError` siblings that an `isinstance`/`except` clause then
  catches too broadly, or break the explicit distinctness test. Severity:
  medium. Likelihood: low. Mitigation: keep the distinctness test; add an
  assertion that both subclass the new base while remaining unrelated to each
  other. Do not change any `except` clause in `runner.py` or `parse.py` to
  catch the base.
- Risk: import cycle — placing the base where `contract` already imports
  `rulepack`, or vice versa, would create a cycle. Severity: low. Likelihood:
  low. Mitigation: put the base in a leaf module (new
  `novel_ralph_skill/contract/errors.py`) that imports nothing from the package;
  `runner.py` and `rulepack/errors.py` import from it. Verify with `ty check`
  and a successful `make test` collection.
- Risk: the `rulepack/errors.py` module docstring currently says the rule-pack
  errors "mirror `StateInputError`"; after extraction that prose is stale.
  Severity: low. Likelihood: high. Mitigation: update the module docstring to
  state they share the `EnvelopeMessagesError` base, citing design §3.1.

## Progress

- [x] (done) Work item 1: add the `EnvelopeMessagesError` base in
  `novel_ralph_skill/contract/errors.py` with a failing-first unit test.
  Committed as `8755221`. `make all` green (277 passed). CodeRabbit flagged one
  minor finding (test assertions lacked descriptive messages); fixed by adding
  messages to all four assertions. Note: `make fmt` also reformats unrelated
  Markdown docs under `docs/`; those reformats are left in the working tree and
  excluded from each atomic commit via explicit `git add` pathspecs (the Safety
  Net blocks `git restore`).
- [x] (done) Work item 2: rebase `StateInputError` onto the base in
  `contract/runner.py`. Deleted its redundant `__init__` (the base supplies it);
  `interrogate` stays at 100% (a subclass without a local `__init__` needs none
  documented). Extended `tests/test_contract_errors.py` with a subclass/messages
  assertion. `make all` green (278 passed). CodeRabbit raised three minor
  docs-style findings (first/second-person pronouns in this execplan); all
  fixed. `make markdownlint`/`make nixie` pass for `roadmap-1-3-4.md` (no errors
  in this file; nixie validates clean).
- [x] (done) Work item 3: rebase `RulePackError` and `RulePackFileError` onto
  the base in `rulepack/errors.py` and refresh the stale module docstring.
  `RulePackFileError` drops its redundant `__init__`; `RulePackError` keeps a
  local `__init__` for `rule_id`, calling `super().__init__(*messages)` (which
  now sets `self.messages` via the base) and dropping its redundant local
  `self.messages` assignment. Module docstring updated: "Both mirror
  `StateInputError`" replaced with the shared-base statement and the
  `rulepack` → `contract` dependency direction (design §3.1). `make all` green
  (278 passed). CodeRabbit: 0 findings.
- [x] (done) Work item 4: add the cross-layer hierarchy test and run the full
  validation gate. Added three consolidating tests to
  `tests/test_contract_errors.py`: all three domain errors subclass the base,
  `RulePackError`/`RulePackFileError` stay unrelated to each other (fan-out, not
  chain), and each subclass round-trips its payload (`RulePackError` keeps
  `rule_id`). The cross-layer test imports the rulepack errors from
  `novel_ralph_skill.rulepack` and the base from `novel_ralph_skill.contract`.
  `make all` green (281 passed). CodeRabbit hit a rate limit; cleared after six
  exponential-backoff retries (30/60/120/240/480/560s) and reported 0 findings.

## Surprises & discoveries

- Observation: the three exceptions already store `messages` as the `*messages`
  varargs tuple, so "freeze-on-construct" is already satisfied per site; the
  value of this task is consolidating the one line into one home, not
  introducing new freezing. Evidence:
  `novel_ralph_skill/contract/runner.py:91-100` and
  `novel_ralph_skill/rulepack/errors.py:38-52,65-74`. Impact: the base's
  `__init__` is a faithful lift of the existing body; no behaviour change is
  intended, which is why the existing suites must pass unchanged.
- Observation: `make fmt` reformats many unrelated Markdown documents under
  `docs/` via `mdformat-all`. This is a known, recurring repo nuisance (the
  worktree's stash list holds numerous "spurious make-fmt mdformat churn"
  entries from prior tasks). The Safety Net blocks `git restore`, so the churn
  was left in the working tree and excluded from every commit by staging only
  the intended files with explicit `git add` pathspecs. `make all` itself does
  not run `mdformat`, so the deterministic gate is unaffected.
- Observation: `make markdownlint` reports pre-existing line-length and
  list-spacing errors in other execplan files (roadmap-1-2-1, 1-2-11, 1-3-1,
  1-3-3, 2-1-1, 2-1-2); `roadmap-1-3-4.md` itself is clean. These were not
  introduced by this task.

## Decision log

- Decision: place the base in a new leaf module
  `novel_ralph_skill/contract/errors.py` rather than in `contract/runner.py`.
  Rationale: `runner.py` is the run-wrapper module and already imports the
  envelope and exit-code helpers; `rulepack/errors.py` importing the base from
  `runner.py` would couple the rule-pack layer to the run wrapper. A dedicated
  leaf errors module keeps the dependency direction clean (`rulepack` →
  `contract.errors`) and gives the base an obvious, neutral home, satisfying
  the roadmap's "neutral `contract` module" success criterion. Date/Author:
  2026-06-23, planning agent.
- Decision: implement the base as a plain
  `class EnvelopeMessagesError(Exception)`, not a dataclass.
  Rationale: the three current exceptions are plain `Exception` subclasses using
  `*messages` varargs and `super().__init__`; preserving `str()`/`args` and
  the varargs signature is a Constraint. A dataclass would change construction
  semantics. Date/Author: 2026-06-23, planning agent.
- Decision: re-export `EnvelopeMessagesError` from
  `novel_ralph_skill.contract.__init__` (add to the import block and
  `__all__`). Rationale: it is part of the shared contract surface and the new
  cross-layer test imports it; exporting it keeps the contract package's public
  surface coherent with how `StateInputError` is already exported. Date/Author:
  2026-06-23, planning agent.

## Outcomes & retrospective

Outcome matches the purpose. `EnvelopeMessagesError` in the new leaf module
`novel_ralph_skill/contract/errors.py` records `self.messages` exactly once. The
three domain exceptions subclass it: `StateInputError` and `RulePackFileError`
drop their `__init__` entirely, and `RulePackError` keeps only the `rule_id`
extension while deferring `messages` storage to the base. The hierarchy fans out
from the base (the rulepack errors stay unrelated to each other), so the
distinctness test still holds. No public name, import path, or constructor
signature changed; consumers needed no edits.

The existing rulepack and contract suites pass unchanged, confirming the
refactor is behaviour-preserving; `make all` is green at every work item (281
tests at completion). Scope stayed well within the tolerance: four source/test
files plus the execplan, a small net change. No constraint or tolerance was
breached; no escalation was required.

The four work items committed cleanly in order. The only friction was a
CodeRabbit rate limit on work item 4, cleared after six exponential-backoff
retries. The `make fmt` mdformat churn on unrelated docs (a known repo nuisance)
was kept out of every commit by explicit `git add` pathspecs.

## Context and orientation

This repository is the `novel-ralph` harness: a set of deterministic Python
commands that read and mutate a novel's `working/` directory and emit a shared
JSON envelope. The relevant package is `novel_ralph_skill`. Only the following
files are needed.

- `novel_ralph_skill/contract/runner.py` — the shared `run` wrapper that drives
  a Cyclopts app to the contract. It defines `StateInputError` (lines 82-100),
  whose `__init__` stores `self.messages: tuple[str, ...] = messages` (the
  `*messages` varargs tuple). `run` catches `StateInputError` and emits an
  exit-`3` envelope built from `exc.messages` (lines 210-216).
- `novel_ralph_skill/rulepack/errors.py` — defines `RulePackError`
  (lines 27-52) and `RulePackFileError` (lines 55-74). Each `__init__` stores
  `self.messages` identically to `StateInputError`; `RulePackError` also stores
  `self.rule_id: str | None`.
- `novel_ralph_skill/contract/__init__.py` — re-exports the contract surface,
  including `StateInputError`, via an import block and an `__all__` list.
- `novel_ralph_skill/rulepack/__init__.py` — re-exports `RulePackError` and
  `RulePackFileError`.
- `novel_ralph_skill/_freeze.py` — read-only normalisers (`freeze_mapping`,
  `freeze_sequence`) used by frozen dataclasses such as `CommandOutcome`. This
  task does **not** use them: a `*messages` varargs tuple is already immutable,
  so the base does not need `freeze_sequence`. Mentioned only to forestall
  reaching for it by reflex.
- Tests that pin the current exception behaviour and must keep passing:
  - `tests/test_rulepack_schema.py` (lines 100-126) — asserts `RulePackError`
    carries `rule_id` and `messages`, that `rule_id` defaults to `None`, that
    `RulePackFileError` carries `messages`, and `test_the_two_error_types_are_distinct`
    (lines 122-126) asserts the two are not subclasses of each other.
  - `tests/test_contract_runner.py` (lines 88-109) — a body raising
    `StateInputError` exits `3`.
  - `tests/test_contract_properties.py` (around line 182), `tests/conftest.py`
    (lines 31, 318) — exercise the exit-`3` path via `StateInputError`.
  - `tests/test_rulepack_loader.py`, `tests/test_rulepack_properties.py` —
    assert per-rule and pack-level faults raise `RulePackError`/`RulePackFileError`.

Term definitions:

- **Envelope `messages`** — the contract's `messages` array, human-oriented
  prose the harness never parses (design §3.1; ADR-003 §"Functional
  requirements", §"Decision outcome"). The command body reads `exc.messages` to
  populate it on the error path.
- **N818** — the Ruff naming rule (selected via the `N` family in
  `pyproject.toml`) that requires exception class names to end in `Error`.
  `EnvelopeMessagesError` satisfies it.
- **`make all`** — the project gate: `build check-fmt lint typecheck test`
  (Makefile line 28). `make lint` includes Ruff (`N`, `TRY`, `D`, `ANN`, …) and
  100% `interrogate` docstring coverage. `make test` runs `pytest -v -n`.

### Verified external facts

- **cuprum is not on this task's path.** A search of `novel_ralph_skill` for
  `cuprum` returns nothing; cuprum appears only in the e2e/console-script tests
  (`tests/test_console_scripts_e2e.py`, `tests/test_venv_scripts_dir.py`,
  `tests/test_conftest_helpers.py`), which this refactor does not touch. No
  cuprum API (catalogue construction, allowlisting, absolute-path executables,
  run/output options) is load-bearing for extracting an exception base. This
  was verified against the local cuprum 0.1.0 source under
  `/data/leynos/Projects/cuprum` and the e2e test comments at
  `tests/test_console_scripts_e2e.py:8-11,77-82`. No external-library behaviour
  beyond what existing tests already pin is needed.
- **N818 / exception-base guidance.** The `python-errors-and-logging` skill's
  working stance is explicit: "design a small hierarchy with a package base
  class and `*Error` suffix (`N818`)." This refactor implements exactly that,
  so the lint gate aligns with the design rather than fighting it.

## Plan of work

Four ordered, independently committable, gate-passable work items. Each ends
with `make all` passing.

### Stage B/C: Work item 1 — add the `EnvelopeMessagesError` base (red, then green)

Add a new leaf module `novel_ralph_skill/contract/errors.py` containing:

```python
# novel_ralph_skill/contract/errors.py
class EnvelopeMessagesError(Exception):
    """A domain error carrying human prose for the envelope's ``messages``."""

    def __init__(self, *messages: str) -> None:
        """Record the human-prose messages once, for the error envelope."""
        super().__init__(*messages)
        self.messages: tuple[str, ...] = messages
```

The module docstring must explain that this is the single home for the
envelope-`messages`-carrying contract (design §3.1; ADR-003), that domain error
types across the `contract` and `rulepack` layers subclass it, and that the
`messages` tuple is captured once at construction (the freeze-on-construct
decision). Cite design §3.1 and `docs/adr-003-shared-interface-contract.md`.
Re-export `EnvelopeMessagesError` from `novel_ralph_skill/contract/__init__.py`
(add to the import block and to `__all__`, keeping `__all__` sorted to satisfy
Ruff `RUF022`/import ordering as the existing list is).

Add a failing-first unit test at `tests/test_contract_errors.py`:

- `EnvelopeMessagesError("a", "b").messages == ("a", "b")` and is a `tuple`.
- `str()`/`args` round-trip: `EnvelopeMessagesError("a").args == ("a",)`.
- `isinstance(EnvelopeMessagesError("a"), Exception)`.
- The class is importable from both
  `novel_ralph_skill.contract.errors` and `novel_ralph_skill.contract`.

Run the new test first to confirm it fails (module absent → ImportError), then
add the module to make it pass.

**Docs to read:** design §3.1; `docs/adr-003-shared-interface-contract.md`
(Functional requirements, Decision outcome); AGENTS.md §"Quality gates" and
§"Python verification and testing".

**Skills to load:** `python-router` → `python-errors-and-logging` (exception
hierarchy and N818), `python-testing` (unit-test placement and pytest style),
`leta` (navigate `contract/__init__.py` exports), `commit-message`.

**Tests to add/update:** new `tests/test_contract_errors.py` (unit) — the four
assertions above. No property, snapshot, behavioural, or e2e test is warranted
for a value-holding base class.

**Validation:** `make all`. The new test fails before the module is added and
passes after.

### Work item 2 — rebase `StateInputError` onto the base

In `novel_ralph_skill/contract/runner.py`:

- Import `EnvelopeMessagesError` from `novel_ralph_skill.contract.errors`.
- Change `class StateInputError(Exception):` to
  `class StateInputError(EnvelopeMessagesError):`.
- Delete the now-redundant `__init__` body (the base supplies it). Keep the
  class docstring, which documents the exit-`3` channel semantics (design §3.2,
  §3.4); trim only the `Parameters` block if it no longer describes a local
  `__init__`, or retain a one-line `__init__` override solely if a docstring is
  needed for `interrogate` — prefer deleting the override so the base's
  `__init__` is the single home (the task's whole point). Confirm `interrogate`
  still reports 100% (a subclass without an `__init__` does not need one
  documented).

Do not change `run`'s `except StateInputError` clause (lines 210-216): it still
catches the same concrete type and reads `exc.messages`.

**Docs to read:** design §3.2 and §3.4 (the exit-`3` state/input channel);
`docs/adr-003-shared-interface-contract.md`.

**Skills to load:** `python-errors-and-logging`, `leta` (find `StateInputError`
refs to confirm none break), `commit-message`.

**Tests to add/update:** none new; the existing
`tests/test_contract_runner.py::test_state_error_exits_three` and
`tests/test_contract_properties.py` exit-`3` checks must still pass unchanged.
Extend `tests/test_contract_errors.py` with one assertion:
`issubclass(StateInputError, EnvelopeMessagesError)` and that
`StateInputError("x").messages == ("x",)`.

**Validation:** `make all`. Behaviour is preserved; no test changes its
expected outcome.

### Work item 3 — rebase `RulePackError` and `RulePackFileError` onto the base

In `novel_ralph_skill/rulepack/errors.py`:

- Import `EnvelopeMessagesError` from `novel_ralph_skill.contract.errors` (the
  rulepack-depends-on-contract direction; never the reverse — a Constraint).
- Change `class RulePackFileError(Exception):` to
  `class RulePackFileError(EnvelopeMessagesError):` and delete its redundant
  `__init__`.
- Change `class RulePackError(Exception):` to
  `class RulePackError(EnvelopeMessagesError):`. `RulePackError` keeps a local
  `__init__` because it adds `rule_id`: have it call
  `super().__init__(*messages)` (which sets `self.messages`) and then set
  `self.rule_id: str | None = rule_id`. Keep its `Parameters` docstring.
- Update the module docstring (lines 17-21): the prose "Both mirror
  `StateInputError`" is now stale. Replace it with a statement that both share
  the `EnvelopeMessagesError` base from `novel_ralph_skill.contract.errors`,
  citing design §3.1, so the cross-layer dependency is documented at the import
  site.

Do not change `rulepack/parse.py` (it raises the same types with the same
signatures) or the `rulepack/__init__.py` re-exports.

**Docs to read:** design §3.1, §4.4, §10 (the two rule-pack failure channels);
`docs/adr-003-shared-interface-contract.md`.

**Skills to load:** `python-errors-and-logging`, `leta` (confirm
`RulePackError` / `RulePackFileError` call sites in `parse.py` are unaffected),
`commit-message`.

**Tests to add/update:** none new in the rulepack suites; the existing
`tests/test_rulepack_schema.py` (carries `rule_id`/`messages`; defaults;
distinctness), `tests/test_rulepack_loader.py`, and
`tests/test_rulepack_properties.py` must all pass unchanged. Note the
distinctness test (`test_the_two_error_types_are_distinct`) is the guard for
the fan-out-not-chain hierarchy and must remain green.

**Validation:** `make all`.

### Stage D: Work item 4 — cross-layer hierarchy test and final hardening

Add to `tests/test_contract_errors.py` a consolidating test that pins the whole
hierarchy in one place:

- `issubclass(StateInputError, EnvelopeMessagesError)`.
- `issubclass(RulePackError, EnvelopeMessagesError)`.
- `issubclass(RulePackFileError, EnvelopeMessagesError)`.
- `RulePackError` and `RulePackFileError` remain unrelated to each other
  (`not issubclass(RulePackError, RulePackFileError)` and the reverse) — the
  fan-out invariant, complementing the rulepack-local distinctness test.
- An instance of each subclass round-trips its `messages` tuple, and
  `RulePackError(..., rule_id="r").rule_id == "r"`.

This test imports the rulepack exceptions from `novel_ralph_skill.rulepack` and
the base/`StateInputError` from `novel_ralph_skill.contract`, demonstrating the
cross-layer consolidation from a single test module.

Then run the full gate and confirm green.

**Docs to read:** AGENTS.md §"Quality gates" (the full gate list) and §"Python
verification and testing" (unit-test placement rules — tests live in the
top-level `tests/` tree). No Markdown is changed by work items 1-4, so
`make markdownlint`/`make nixie` are not required for the source commits; they
**are** required for the commit that adds/updates this execplan Markdown file
(see "Validation and acceptance").

**Skills to load:** `python-testing`, `code-review` (self-review the diff for
behaviour preservation), `commit-message`.

**Tests to add/update:** the consolidating hierarchy test above.

**Validation:** `make all`.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-4`.

1. Confirm the branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-4 \
     branch --show-current   # expect: roadmap-1-3-4
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-1-3-4 \
     status --short          # expect: only docs/execplans/roadmap-1-3-4.md
   ```

2. Work item 1: create `tests/test_contract_errors.py` (failing), run it,
   create `novel_ralph_skill/contract/errors.py`, wire the re-export, then:

   ```bash
   make test     # new test passes
   make all      # full gate green
   ```

   Commit (file-based message via the `commit-message` skill; never `-m`).

3. Work item 2: edit `contract/runner.py`; `make all`; commit.

4. Work item 3: edit `rulepack/errors.py` (and its module docstring);
   `make all`; commit.

5. Work item 4: extend `tests/test_contract_errors.py`; `make all`; commit.

Each commit message follows the `commit-message` skill, uses en-GB Oxford
spelling, and references roadmap task 1.3.4.

Expected `make all` tail on success (illustrative):

```plaintext
... passed in N.NNs
```

## Validation and acceptance

Quality criteria (what "done" means):

- **Tests:** `make test` passes the full suite under xdist. The new
  `tests/test_contract_errors.py` fails before work item 1's module exists and
  passes after; the existing rulepack and contract suites pass unchanged in
  behaviour.
- **Lint/typecheck:** `make lint` (Ruff including `N`/N818, `TRY`, `D`, `ANN`;
  `interrogate` at 100%) and `make typecheck` (`ty check`) pass.
- **Format:** `make check-fmt` passes.
- **Gate:** `make all` is green after every work item.
- **Markdown (this execplan only):** because this ExecPlan is a Markdown file,
  run `make markdownlint` and `make nixie` before committing the plan document;
  expect both to pass. (`make nixie` validates Mermaid; this plan has no
  Mermaid diagrams, so it is a no-op pass.)

Quality method (verification): run the commands above in the worktree; compare
output to the expected transcripts.

Behavioural acceptance: running the existing exit-`3` test still exits `3`:

```bash
make test 2>&1 | grep -E "test_state_error_exits_three|test_the_two_error_types_are_distinct"
# both report PASSED
```

## Idempotence and recovery

Every step is re-runnable. Adding the new module and test is additive; rebasing
the three exceptions onto the base is a localised edit. If a `make all` run
fails, fix forward (do not delete the base) and re-run `make all`; the build
cache makes re-runs cheap. To abandon a half-finished work item, `git restore`
the touched files and re-apply from this plan. No step is destructive; no
backups are required.

## Artifacts and notes

The load-bearing current code, for reference during implementation:

`novel_ralph_skill/contract/runner.py` (lines 82-100):

```python
class StateInputError(Exception):
    ...
    def __init__(self, *messages: str) -> None:
        super().__init__(*messages)
        self.messages: tuple[str, ...] = messages
```

`novel_ralph_skill/rulepack/errors.py` (lines 38-52, 65-74): the same
`self.messages` body in `RulePackError.__init__` (which additionally sets
`self.rule_id`) and in `RulePackFileError.__init__`.

## Interfaces and dependencies

At the end of this plan the following must exist:

In `novel_ralph_skill/contract/errors.py`:

```python
class EnvelopeMessagesError(Exception):
    messages: tuple[str, ...]
    def __init__(self, *messages: str) -> None: ...
```

In `novel_ralph_skill/contract/runner.py`:

```python
class StateInputError(EnvelopeMessagesError): ...  # no local __init__
```

In `novel_ralph_skill/rulepack/errors.py`:

```python
class RulePackFileError(EnvelopeMessagesError): ...  # no local __init__

class RulePackError(EnvelopeMessagesError):
    rule_id: str | None
    def __init__(self, *messages: str, rule_id: str | None = None) -> None: ...
```

Re-exports: `EnvelopeMessagesError` is exported from
`novel_ralph_skill.contract` (`__init__.py` import block and `__all__`);
`StateInputError`, `RulePackError`, `RulePackFileError` keep their existing
re-exports. Dependency direction: `novel_ralph_skill.rulepack.errors` →
`novel_ralph_skill.contract.errors`; never the reverse. No new external
dependency.

## Revision note (required when editing an ExecPlan)

Initial draft (2026-06-23): first planning round for roadmap task 1.3.4. No
prior design-review blocking points to address.
