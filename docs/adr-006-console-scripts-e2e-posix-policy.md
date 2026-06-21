# Architectural decision record (ADR) 006: console-scripts e2e is POSIX-only

## Status

Accepted, 2026-06-21. The console-scripts end-to-end test
(`tests/test_console_scripts_e2e.py`) runs only where `os.name == "posix"`. It
is skipped on non-POSIX platforms rather than executing a Windows-specific
lookup path.

## Date

2026-06-21.

## Context and problem statement

The end-to-end test builds a wheel, installs it into a fresh `uv venv`, and
asserts that all five console-scripts (ADR 005) resolve on disk and exit `2`.
Its venv-scripts resolver branched on `sys.platform == "win32"`, choosing the
`nt_user` sysconfig scheme — a roaming per-user path, not the venv `Scripts/`
directory `uv venv` creates — and looked up commands with no `.exe` suffix. That
Windows branch was therefore both dead and wrong: dead because the only
continuous-integration lane that runs the test suite is `ubuntu-latest`
(`.github/workflows/ci.yml`), and wrong because the path it would have computed
on Windows does not exist.

A remediation raised against roadmap task 1.2.1 asked that the policy be settled
rather than left half-portable: either commit to Linux-only execution or make
the lookup truly portable on Windows. This ADR records that decision so a future
contributor does not silently re-introduce the broken branch.

## Decision drivers

- The test suite runs only on `ubuntu-latest`; the Windows and macOS lanes
  (`.github/workflows/build-wheels.yml`) build wheels with `cibuildwheel` and
  never invoke `pytest`.
- A "truly portable" Windows lookup would be untested in every CI lane, so it
  could rot exactly as the original branch did.
- The contract should be honest: a test that branches on a platform it never
  runs on is dead code masquerading as coverage.

## Requirements

### Functional requirements

- The test proves, on the platform it runs on, that all five console-scripts
  install and exit `2`.
- On any platform where the test cannot run correctly, it is skipped with a
  recorded reason rather than failing or silently passing on a wrong path.

### Technical requirements

- The venv-scripts directory resolves through the canonical sysconfig scheme on
  the supported platform.
- The decision integrates with the `make`-driven quality gates in `AGENTS.md`.

## Options considered

### Option A: POSIX-only execution

Skip the test on non-POSIX platforms with a `pytest.mark.skipif` guard, and
resolve the venv-scripts directory through the canonical `venv` sysconfig scheme
(the default scheme on Python 3.14), which returns the venv `bin/` directory on
POSIX. The contract matches the Linux-only CI lane exactly.

### Option B: Make the lookup truly portable on Windows

Resolve the venv `Scripts/` directory and append a `.exe` suffix on Windows, so
the test runs on every platform. This restores a real Windows code path — but no
CI lane would exercise it, so it would be unverified and free to rot.

| Topic                     | Option A: POSIX-only          | Option B: truly portable        |
| ------------------------- | ----------------------------- | ------------------------------- |
| Exercised by CI           | Yes, on `ubuntu-latest`       | Windows path never runs         |
| Honesty of the contract   | Skips where it cannot run     | Pretends to cover Windows       |
| Maintenance cost          | One guard, one scheme         | A second, untested code path    |
| Rot risk                  | Low                           | High (unverified Windows arm)   |

_Table 1: Comparison of options._

## Decision outcome / proposed direction

Adopt Option A. The test is guarded with a module-level
`pytestmark = pytest.mark.skipif(os.name != "posix", …)` whose reason names this
ADR, and `_venv_scripts_dir` resolves through the `venv` sysconfig scheme. The
installed console-scripts run through a cuprum catalogue keyed on their absolute
paths — cuprum 0.1.0 allowlists any `Program` string, including an absolute
path — so no raw `subprocess` is required and the scripting standards are met.
The decision is recorded in
[novel-ralph-harness-design.md](novel-ralph-harness-design.md) §4 and the
[developers' guide](developers-guide.md).

## Goals and non-goals

- Goals:
  - Make the e2e contract honest: run on POSIX, skip elsewhere.
  - Resolve the venv-scripts directory through the canonical `venv` scheme.
  - Record the policy so the broken Windows branch is not re-introduced.
- Non-goals:
  - A real, tested Windows lookup (explicitly rejected — no CI lane runs it).
  - A single source of truth for the command names (roadmap task 1.2.4).

## Migration plan

Not applicable; the change is in-place in the existing test. The Windows branch
is removed, the resolver switches to the `venv` scheme, and the skip guard is
added.

## Known risks and limitations

- If the project ever adds a Windows CI lane that runs `pytest`, this ADR should
  be revisited and a real, tested Windows path added. No such lane exists.
- The skip guard relies on `os.name`; should the project target a non-POSIX,
  non-Windows platform, the guard would skip there too — which is the safe
  default until that platform is in CI.

## Outstanding decisions

None. The policy is fixed at POSIX-only; the command-name single source of truth
is settled separately in roadmap task 1.2.4.
