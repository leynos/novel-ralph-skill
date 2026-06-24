# novel-ralph-skill Users' Guide

## Quality Gates

Generated projects use `make all` as the standard local quality gate. It runs
these targets in order:

- `build`: create the local virtual environment and install development
  dependencies with `uv sync --group dev`.
- `check-fmt`: check Ruff formatting for Python sources and, when Rust is
  enabled, `cargo fmt` for the Rust extension.
- `lint`: run `lint-python` and, when Rust is enabled, `lint-rust`.
- `typecheck`: run `ty check`.
- `test`: run pytest and, when Rust is enabled, Rust tests.
- `audit`: run `pip-audit` and, when Rust is enabled, `cargo audit`.

The `lint-python` target runs Ruff, then Interrogate over `$(PYTHON_TARGETS)`
to enforce 100% docstring coverage for the Python targets (the threshold is
pinned in `[tool.interrogate]` in `pyproject.toml`), then Pylint via a
PyPy-backed runner. The Pylint runner is installed through `uv tool run` from
the pinned `pylint-pypy-shim` repository.

Pytest discovery is limited to the top-level `tests/` tree. Keep generated
project unit tests there rather than in package module directories or
`unittests/` subdirectories, because CI coverage runs through xdist-backed
SlipCover support.

When the Rust extension is enabled, `lint-rust` runs:

- `cargo doc` with warnings denied;
- `cargo clippy` with the generated Clippy configuration; and
- Whitaker with `whitaker --all`.

The generated Makefile installs Whitaker on demand before local Rust linting
when it is not already available.

## Dependency Auditing

Run `make audit` to check generated project dependencies for known
vulnerabilities. All generated projects run `pip-audit` against the Python
environment created by `uv sync --group dev`. Rust-enabled projects also run
`cargo audit` from the `rust_extension` crate directory.

## Rust Test Behaviour

Rust-enabled projects use `cargo nextest run` when `cargo-nextest` is
available. If `cargo-nextest` is not installed, the generated `test` target
falls back to `cargo test`. Rust documentation tests still run through
`cargo test --doc`.

If cargo is missing from the local environment, generated Rust test targets
fail early with a clear error instead of falling through to an unusable `cargo`
invocation.

## Local GitHub Actions Validation

The generated Makefile supports optional local workflow validation using
[`act`](https://github.com/nektos/act). When `act` is installed and Docker is
available, pass `WITH_ACT=1` to the `test` target:

```bash
make test WITH_ACT=1
```

This sets `RUN_ACT_VALIDATION=1` for the pytest invocation, enabling the
act-based integration tests that run the generated CI workflow locally. Omitting
`WITH_ACT` (or setting it to `0`) skips act validation; the rest of the test
suite runs unchanged.

## Cleaning Local State

Run `make clean` to remove local build and cache outputs, including `.venv`,
`.uv-cache`, `.uv-tools`, Python cache directories, coverage outputs, and Rust
`target` output when the Rust extension is enabled.

## Installed Commands

Installing a wheel built from this package puts five console-scripts onto
`PATH`:

- `novel-state` — read and mutate the harness state.
- `novel-done` — evaluate the done predicate.
- `novel-compile` — regenerate the compiled manuscript.
- `desloppify` — report prose tics.
- `wordcount` — report per-chapter and cumulative word counts.

`wordcount` is still a **stub**: running it prints
"`wordcount` is not yet implemented" to standard error and exits with code `2`.
It will be filled in by a later release. `novel-done` (see below) and
`novel-compile` now drive their real checkers.

`novel-compile` regenerates `working/manuscript/compiled.md` by concatenating the
chapter drafts in zero-padded chapter-index order (`chapter-01/draft.md`,
`chapter-02/draft.md`, …), joined by one fixed separator. The order is taken from
the `[chapters]` manifest, not from the directory listing, so identical drafts
always produce a byte-identical `compiled.md`: it is deterministic and idempotent,
and a second run over unchanged drafts rewrites nothing observable. The working
directory is the fixed `working/` directory relative to the current directory.
When the `[chapters]` manifest is absent or empty there is no authoritative
ordering, so `novel-compile` writes nothing and exits `3` (the state/input code
in the shared exit-code table below): plan the chapters first. Any other state or
input fault — a missing or unparseable `state.toml`, or an unreadable draft —
likewise exits `3`.

`novel-state` now has its first real subcommand, `novel-state check` (roadmap
task 2.1.2). It validates the state coherence invariants of
`./working/state.toml` and writes nothing. The working directory is the fixed
`working/` directory relative to the current directory; there is no
`--working-dir` flag. By default it prints a one-line JSON envelope on standard
output; pass the global `--human` flag (`novel-state --human check`) for a
readable rendering instead.

`novel-state check` uses the shared exit-code table:

- `0` — every checked invariant holds; `result.violations` is empty.
- `4` — one or more invariants are violated; the breached invariant names appear
  in `result.violations` for the agent to adjudicate.
- `3` — `./working/state.toml` is missing or unparseable (the state-error
  channel).

As of roadmap task 2.3.2 `novel-state check` is **disk-aware**: it validates
the pure-state invariants decidable from `state.toml` alone *and* the
disk-evidence invariants that compare `state.toml` against the `working/` tree.
When a disk-evidence invariant is violated it also attaches a
`result.reconciliation` describing the repair a stale tree implies (the action —
`recount`, `refuse`, `complete-pending-turn`, or `rollback-pending-turn` — and
the discrepancy names); `check` still writes nothing on any path.

The pure-state names that can appear in `result.violations` are:

- `phase-in-enum` — the current phase is not one of the known workflow phases.
- `completed-prefix` — the completed-phase list is not the in-order run of
  phases before the current one (a phase is missing or out of order).
- `by-chapter-sum` — the per-chapter word counts do not add up to the recorded
  current total.
- `consecutive-clean-within-target` — the consecutive-clean-pass counter is
  negative or above its configured convergence target.
- `convergence-target-at-least-one` — the convergence target is below one.
- `consecutive-clean-within-drafted` — the consecutive-clean-pass counter claims
  more clean chapters than have actually been drafted.
- `cursor-coherent` — the drafting cursor (chapter, scene, beat) is negative or
  points past the chapters in the manifest.
- `gate-ratio-consistent` — a knitting gate is set true or false in a way that
  disagrees with the drafted-word ratio against its threshold.

The disk-evidence names compare the recorded state against the `working/` tree:

- `manifest-disk-bijection` — the chapter manifest and the on-disk
  `chapter-NN/` directories are not in one-to-one correspondence.
- `done-flag-without-draft` — a chapter carries a `done.flag` beside an empty or
  absent `draft.md`.
- `compiled-matches-drafts` — `compiled.md` is not the ordered concatenation of
  the present drafts.
- `pending-turn-cleared` — `state.toml` records an uncleared `[pending_turn]` (a
  torn multi-file turn).
- `cursor-plan-present` — a non-zero scene or beat cursor has no on-disk
  `scenes.md`/`beats.md` plan for its chapter.
- `word-counts-match-drafts` — the recorded per-chapter `[word_counts]` table
  disagrees, on a chapter both sides record, with the words actually on disk (a
  stale done-claim, or a real `done.flag` over a draft the table under-counts).
- `word-counts-cover-drafts` — the recorded `[word_counts].by_chapter` *key set*
  diverges from the drafts: the table omits a drafted chapter, or carries an
  entry for a chapter the manifest never declared. `novel-state reconcile`
  repairs it with the same recount that repairs `word-counts-match-drafts`,
  re-keying the table off the manifest so the missing key is supplied and any
  orphan key dropped.

`novel-state` also exposes three write subcommands that mutate the project —
`init`, `set-cursor`, and `advance-phase` (roadmap task 2.2.2). Every one of
them honours the same **validate-before-persist, write-nothing-on-refusal**
contract: each derives the state its arguments would produce, checks it against
the coherence invariants above, and writes atomically only when the result is
coherent. A refusal exits `3` (the state-error channel), names the breached
invariant on standard error, and changes nothing on disk, so the prior
`state.toml` is left byte-for-byte intact. A missing or unparseable
`state.toml` is itself an exit-`3` refusal. The sections below describe only
each subcommand's own arguments and the extra refusals specific to it; the
shared contract holds for all three.

`novel-state init` bootstraps a fresh project: it creates the `working/`
directory skeleton — the `characters/`, `world/`, `reader/`, `plan/`,
`manuscript/`, and `reviews/` subdirectories plus an empty `log.md` — and writes
a coherent initial `state.toml`. It takes `--title` (the novel title),
`--slug` (the project slug), and `--target-word-count` (the target word count,
defaulting to `80000`). To protect a live project, `init` *creates* but never
overwrites: when `working/state.toml` already exists it refuses with exit `3`
rather than clobbering it, so re-running `init` over an initialised project is
safe.

`novel-state set-cursor` moves the drafting cursor. It takes three integer
options — `--chapter`, `--scene` (default `0`), and `--beat` (default `0`) — and
records them as the `[drafting]` cursor. Per the shared contract it refuses (the
`cursor-coherent` invariant) when the cursor is incoherent: a chapter past the
end of the manifest, or a scene or beat set while the cursor names no chapter.

`novel-state advance-phase` takes no arguments and always advances
`phase.current` to the immediate next workflow phase, appending the phase it
leaves to `phase.completed`. Because it can only ever step to the successor, a
phase *skip* cannot be requested; it instead refuses (exit `3`) when advancing
from the terminal `done` phase (which has no successor) and when advancing into
`drafting` with an empty chapter manifest.

`novel-state recount` re-derives the word counts from the chapter drafts, so
you never type a word count by hand. It reads each chapter's
`working/manuscript/chapter-NN/draft.md`, counts its words, and rewrites
`[word_counts].current` and `[word_counts].by_chapter` to match what is
actually on disk (`current` is the sum of the per-chapter counts). It is
idempotent: running it twice over unchanged drafts leaves `state.toml`
byte-for-byte identical. Like the other write subcommands it writes nothing on
refusal (exit `3`) — a missing or unparseable `state.toml`, an unreadable
draft, or a recount that would leave the state incoherent each leaves the prior
file untouched.

`novel-state reconcile` (roadmap task 2.3.2) carries out the repair
`novel-state check` reports when `state.toml` has drifted from the on-disk
manuscript — the recovery routine you used to run by hand, now run as code. It
re-derives the reconciliation from disk independently (it never trusts a
payload from `check`), then:

- when the `[word_counts]` table is stale against the drafts — whether on a
  shared chapter's count or on the `by_chapter` key set (a missing or orphan
  entry) — it rewrites `[word_counts]` from the drafts (a recount) and exits `0`;
- when `state.toml` left an uncleared `[pending_turn]`, it completes or rolls
  the
  torn turn back (it never fabricates a draft or a `done.flag`) and exits `0`;
- when `log.md` is absent beside a present `state.toml` — the partial-`init`
  bootstrap, where a crash struck between `init`'s two writes (`state.toml`
  first, `log.md` second) and re-running `init` refuses — it recreates an empty
  `log.md`, appends a recovery receipt, and exits `0` (roadmap task 2.3.4);
- when disk *contradicts itself* — a `done.flag` beside an empty draft, a
  `compiled.md` referencing absent content, a non-bijective manifest, or a
  plan-less cursor — it **refuses**: it writes no state change and exits `4`
  for you to adjudicate.

The recreated `log.md` is **empty** save for the recovery receipt: the
`log-present` detector fires solely on `log.md` absence and cannot tell a clean
partial-`init` crash from a later loss of a populated log, so `RECREATE_LOG`
always restores a fresh, empty file and exits `0`. Prior receipts are **not
recoverable** by this repair; if you need them back, restore `log.md` from a
backup before reconciling.

Every repair or refusal is logged as a recovery receipt appended to
`working/log.md`, and `reconcile` removes no file under `working/`. It is
idempotent: running it twice over an already-reconciled tree is a no-op that
leaves `state.toml` byte-for-byte unchanged. A repair that would cross a
knitting gate the recorded gates do not reflect is refused (exit `3`) rather
than silently mis-repaired, because integrating a knitting pass is your
judgement, not a deterministic recompute.

`result.violations` is the *checker's* read shape: it belongs to
`novel-state check` alone. The write subcommands (`init`, `set-cursor`,
`advance-phase`, `recount`, `reconcile`) instead report *what they changed* in
`result` — `set-cursor` returns the cursor it set, `advance-phase` returns the
`{from, to}` transition, `recount` returns the `{current, by_chapter}` counts
it wrote, and `reconcile` returns the `{action, discrepancies, detail}` it
enacted (plus the written counts for a recount) — so do not expect a
`violations` key from a write.

`desloppify` reports prose tics (roadmap task 5.1.2). It reads the chapter
drafts under `./working/`, scans them against a versioned rule pack — the §6
high-frequency-offender table shipped with the package by default — and reports
a per-rule finding without editing the manuscript or touching `state.toml` (it
is a detect-only checker). By default it scans the whole manuscript (every
chapter in
the `[chapters]` manifest); pass `--chapter N` to scan a single chapter, or
`--pack PATH` to use a different rule pack. A second pack, `ai-isms.toml`, ships
with the package and flags lexical AI-isms ("load-bearing", "a testament to");
it is opt-in, selected with `--pack
novel_ralph_skill/rulepack/packs/ai-isms.toml`. Like `novel-state check`
`desloppify` prints a one-line JSON envelope by default and a readable rendering
under the global `--human` flag.

`desloppify` uses the shared exit-code table:

- `0` — every rule is within threshold; `result.violations` is empty.
- `4` — one or more rules exceed threshold; the offending rule ids appear in
  `result.violations` for the agent to adjudicate, and each finding's `rule_id`
  (the canonical slug the `violations` list references), `phrase` (the rule's
  authored pattern source — the regex that names the offender, not a literal
  matched span), hit count, threshold, per-page density, and per-`{chapter,
  line}` matches are in `result.findings`.
- `2` — a usage error: `--chapter N` names a chapter absent from the manifest,
  or `--pack` points at a rule pack whose *content* is malformed.
- `3` — a state or input error: `./working/state.toml` is missing or
  unparseable, a chapter draft is unreadable, or `--pack` points at an absent or
  undecodable file.

A per-page rule reports density as hits per `page_words` tokens, and a partial
page still counts: the scanned text is divided by `page_words` as a float rather
than rounded up to a whole page. On a short or near-empty draft — an early
chapter, or a `--chapter N` scan of a chapter barely begun — the scanned text is
a fraction of one page, so a single offending hit extrapolates to a high
per-page density and can trip the threshold. This is design-correct: the density
measures the rate the tic appears at, not the raw count, so a draft that is one
tenth of a page with one hit is reported at the same rate as a full page with
ten. Do not be surprised when a short chapter trips a per-page rule on one hit;
re-scan once the chapter is fuller to read the settled rate.

`novel-done` evaluates the done predicate (roadmap task 3.1.1): it answers "is
the novel finished?" deterministically, so the harness can check it every turn
with one call. It reads `./working/state.toml` and the `working/` tree, evaluates
six done clauses against disk, and writes nothing on any path (it is a read-only
checker). It takes no arguments. Like the other checkers it prints a one-line
JSON envelope by default and a readable rendering under the global `--human`
flag.

The `result` reports each clause as a boolean, so an operator sees exactly which
conditions are unmet:

- `phase_is_done` — `state.phase.current` has reached the terminal `done` phase.
- `final_pass_complete` — the final-pass gate (`[gates.final]`) is set.
- `all_chapters_flagged` — every manifest chapter has an on-disk `done.flag`.
- `knitting_gates_passed` — all three knitting gate booleans are true *and* all
  three `working/reviews/knitting-{30,50,80}.md` reviews are present.
- `compile_consistent` — `working/manuscript/compiled.md` is present (see the v1
  caveat below).
- `no_unresolved_blockers` — no chapter's `critic-notes.md` carries an unresolved
  BLOCKER (a line beginning `BLOCKER` without a `[resolved]` marker).

`novel-done` uses the shared exit-code table:

- `0` — every clause holds; the novel is done.
- `1` — at least one clause is false (the benign "not yet done" the harness loops
  on); `messages` names the unmet clauses.
- `3` — a state or input error: `./working/state.toml` is missing or unparseable,
  or a chapter artefact (such as `critic-notes.md`) is unreadable.

**v1 caveat.** In this release `compile_consistent` checks only that
`compiled.md` *exists*: an *absent* compile is always reported (a tree with no
`compiled.md` can never be declared done), but a *present-but-stale* compile —
one that no longer matches the chapter drafts — is not yet caught, so it can
still pass. Catching a stale compile, and the exit-`4` compile-divergence finding
that goes with it, lands with roadmap task 3.1.2. No `novel-done` path emits
exit `4` in v1.
