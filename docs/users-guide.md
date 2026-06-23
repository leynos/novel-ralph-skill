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
PyPy-backed runner. The
Pylint runner is installed through `uv tool run` from the pinned
`pylint-pypy-shim` repository.

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

`novel-done`, `novel-compile`, `desloppify`, and `wordcount` are still
**stubs**: running one prints "`<name>` is not yet implemented" to standard
error and exits with code `2`. Each will be filled in by a later release.

`novel-state` now has its first real subcommand, `novel-state check` (roadmap
task 2.1.2). It validates the state coherence invariants of `./working/state.toml`
and writes nothing. The working directory is the fixed `working/` directory
relative to the current directory; there is no `--working-dir` flag. By default
it prints a one-line JSON envelope on standard output; pass the global `--human`
flag (`novel-state --human check`) for a readable rendering instead.

`novel-state check` uses the shared exit-code table:

- `0` — every checked invariant holds; `result.violations` is empty.
- `4` — one or more invariants are violated; the breached invariant names appear
  in `result.violations` for the agent to adjudicate.
- `3` — `./working/state.toml` is missing or unparseable (the state-error
  channel).

The names that can appear in `result.violations` are the pure-state half of the
invariant set (the on-disk-evidence invariants below arrive in a later release):

- `phase-in-enum` — the current phase is not one of the known workflow phases.
- `completed-prefix` — the completed-phase list is not the in-order run of phases
  before the current one (a phase is missing or out of order).
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

The on-disk evidence invariants (the chapter manifest matching the directory
set, `done.flag`/`draft.md` consistency, and `compiled.md` freshness) are
validated by a later release; `novel-state check` currently checks only the
invariants decidable from `state.toml` alone.

`result.violations` is the *checker's* read shape: it belongs to `novel-state
check` alone. The write subcommands (`init`, `set-cursor`, `advance-phase`)
instead report *what they changed* in `result` — `set-cursor` returns the cursor
it set, `advance-phase` returns the `{from, to}` transition — so do not expect a
`violations` key from a write.
