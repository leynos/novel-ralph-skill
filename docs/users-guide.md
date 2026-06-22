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

As of roadmap task 1.2.1 every one of these commands is a **stub**: running it
prints "`<name>` is not yet implemented" to standard error and exits with code
`2`. None performs any real work yet, and none writes to the working tree. Each
command's behaviour will be filled in by a later release; until then the
commands exist only so the harness spine is invocable end to end.
