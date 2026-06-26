# Post-merge audit — roadmap task 6.3.6

Audit of the codebase after roadmap task 6.3.6 ("Extend the cross-command
identity proof to the installed-wheel boundary") merged to `main` at commit
`1b4dcbe`.

The merged change extends
[`tests/test_novel_state_check.py`](../../tests/test_novel_state_check.py)'s
`test_installed_novel_state_check_exits_zero` from a thin exit-0/`ok: true`
smoke test into the installed-boundary *success*-arm skeleton-identity
tripwire. Over the built-and-installed wheel it now pins the full exit-0
envelope skeleton for `novel state check`: the six contract keys in
`ENVELOPE_KEY_ORDER`, `schema_version`, `command == "novel state"` (and its
membership of `ENVELOPE_COMMAND_NAMES`), the `ok`-iff-exit-0 mapping, the
resolved-absolute `working_dir`, `result["violations"] == []`, and `str`-typed
`messages`. The test reuses the existing `installed_novel_state`,
`single_program_catalogue`, and `baseline_tree` fixtures, was extended in place
to avoid a second module-scoped wheel build, carries the same
`slow`/`timeout(180)`/POSIX-`skipif` marks as the other installed e2es, and the
developers-guide records the three-proof boundary (this test for the success
arm, `test_console_scripts_error_arms_e2e.py` for the error arms, and
`tests/cross_command_contract/` in-process). The work is correct, well-marked,
and well-documented.

The findings below concern *how* the new test asserts the identity contract,
not whether it asserts the right one. The cross-command suite already owns a
canonical encoding of the skeleton-identity claim
(`assert_envelope_skeleton`), reused at seven in-process sites, but the new
installed mirror re-spells that claim inline rather than reusing the helper —
so the two halves of the proof now state "the same contract" in two different
sets of `assert` lines that can drift independently. A second, smaller finding
records that the installed *success*-arm run-and-assert mechanics duplicate the
shape that `assert_installed_state_error` already consolidated for the
installed *error* arm.

## Finding 1 — The installed identity mirror re-spells `assert_envelope_skeleton` inline instead of reusing the canonical helper

- **Category**: duplication
- **Severity**: medium
- **Location**:
  `tests/test_novel_state_check.py`
  (`test_installed_novel_state_check_exits_zero`, the inline skeleton
  assertions at lines 363-380) versus the canonical
  `tests/cross_command_contract/_identity_assertions.py::assert_envelope_skeleton`
  (lines 57-122).

The cross-command suite factors the skeleton-identity claim into one helper,
`assert_envelope_skeleton(envelope, *, command, code)`, whose docstring frames
it as "the *identity* claim every cross-command module asserts" and which is
already reused at seven sites
(`tests/cross_command_contract/test_envelope_shape.py` lines 67 and 100,
`test_error_channels.py` lines 136/236/331/366, `test_mutator_identity.py`
lines 127/162, and `tests/steps/cross_command_contract_steps.py`). It pins, in
one place: the `ENVELOPE_KEY_ORDER` key tuple, `command` equality, `command in
ENVELOPE_COMMAND_NAMES`, `schema_version == ENVELOPE_SCHEMA_VERSION`, `ok` is a
`bool`, `ok is (code == ExitCode.SUCCESS)`, `result` is a mapping, and
`messages` is a list of `str`.

The new installed test, whose own docstring says it asserts "against the same
constants the in-process cross-command suite uses, so the installed surface
cannot silently diverge from the in-process contract", re-derives every one of
those checks by hand (lines 363-380) rather than calling the helper. The two
encodings are equivalent today, but they are now two independent spellings of
one contract: a future change to the skeleton claim — a seventh envelope key, a
`schema_version` bump, a tightening of the `ok` mapping — must be made twice,
and the in-process helper change would silently leave the installed mirror
asserting the *old* skeleton. That is the precise drift the test exists to
prevent, reintroduced one layer up.

The only field that legitimately diverges between the in-process proof and the
installed boundary is `working_dir`: the in-process helper hardcodes
`WORKING_DIR_CONSTANT` (`"working"`), whereas the installed binary stamps the
resolved-absolute path (roadmap 6.3.4). That single divergence is why the test
could not call the helper as it stands — not a reason to re-spell the other
eight checks. `result["violations"] == []` is a command-specific *body* payload
and is correctly asserted separately; the helper is explicit that the `result`
contents are "asserted elsewhere".

- **Proposed fix**: Parameterise `assert_envelope_skeleton` with an optional
  `working_dir: str | None = None` argument that defaults to
  `WORKING_DIR_CONSTANT`, so existing in-process callers are unchanged and the
  installed test can pass the resolved-absolute path. Then replace the inline
  block at `tests/test_novel_state_check.py` lines 363-380 with a single
  `assert_envelope_skeleton(envelope, command=_COMMAND,
  code=result.exit_code, working_dir=str((dest / "working").resolve()))`,
  keeping only the command-specific `result["violations"] == []` assertion
  beside it. This makes the "same constants" claim structural — one helper,
  one place to change — rather than parallel-by-convention. Proposed as a
  roadmap item below; not applied here (this is a read-only audit step).

## Finding 2 — The installed success-arm run-and-assert duplicates the shape `assert_installed_state_error` consolidated for the error arm

- **Category**: duplication
- **Severity**: low
- **Location**:
  `tests/test_novel_state_check.py`
  (`test_installed_novel_state_check_exits_zero`, the
  `sh.make(prog, catalogue=...)(...).run_sync(context=ExecutionContext(...),
  capture=True)` drive and the subsequent `json.loads(result.stdout or "{}")`
  parse, lines 350-380) versus
  `tests/installed_binary_fixtures.py::assert_installed_state_error`
  (lines 169-232).

The installed *error* arm already has a shared asserter:
`assert_installed_state_error` is a function-scoped fixture returning a
`(script_path, run_dir, *argv) -> None` callable that builds the one-program
catalogue, runs the installed script under `ExecutionContext(cwd=run_dir)`,
parses the JSON envelope, and asserts the exit-3 state-error contract. Its
docstring records that it was introduced precisely to fold the run plus the
contract assertions into one shared harness across the `recount`, `reconcile`,
and `wordcount` installed exit-3 proofs, so a regression (such as an empty
`messages` list) cannot slip past three near-identical hand-rolled copies.

The new installed *success* arm does not follow that established pattern: it
inlines the catalogue build, the `sh.make(...).run_sync(...)` drive, the
`json.loads(result.stdout or "{}")` parse, and the no-`Traceback` guard
directly in the test body — the same mechanics `assert_installed_state_error`
consolidated for the error arm. Today there is a single installed success-arm
site, so the duplication is latent rather than realised, and the wider
"run an installed script and parse its envelope" idiom appears across roughly a
dozen e2e modules (a separately scoped concern). But the asymmetry is worth
recording: the error arm has a sanctioned shared run-and-assert harness while
the success arm, added by the same family of work, does not, so the next
installed success-arm proof has no helper to reuse and will hand-roll the same
shape again.

- **Proposed fix**: When (and only when) a second installed success-arm proof
  is needed, promote a sibling `assert_installed_success_envelope` harness
  beside `assert_installed_state_error` in
  `tests/installed_binary_fixtures.py` that runs the script over `*argv` in a
  `run_dir`, parses the envelope, asserts exit 0 and the shared skeleton
  (delegating to the Finding 1 `assert_envelope_skeleton` helper for the
  identity half), and returns the parsed envelope so the caller can assert its
  command-specific `result` payload. Migrate
  `test_installed_novel_state_check_exits_zero` onto it. Until a second
  consumer exists, this stays a documented asymmetry rather than a refactor.
  Proposed as a roadmap item below; not applied here.

## Proposed roadmap items (for the root agent only)

- **Reuse `assert_envelope_skeleton` in the installed identity mirror**
  (severity: medium). Parameterise
  `tests/cross_command_contract/_identity_assertions.py::assert_envelope_skeleton`
  with an optional `working_dir` override (default `WORKING_DIR_CONSTANT`) and
  replace the inline skeleton assertions in
  `test_installed_novel_state_check_exits_zero`
  (`tests/test_novel_state_check.py` lines 363-380) with a single helper call,
  keeping only the command-specific `result["violations"] == []` assertion.
  Rationale: 6.3.6's test claims to assert "the same constants" as the
  in-process identity proof but re-spells that proof's canonical helper inline,
  so the two halves can drift independently — the exact divergence the
  installed mirror exists to catch.

- **Add a shared installed success-arm run-and-assert harness when a second
  consumer arrives** (severity: low). Mirror
  `assert_installed_state_error` with an
  `assert_installed_success_envelope` harness in
  `tests/installed_binary_fixtures.py` and migrate
  `test_installed_novel_state_check_exits_zero` onto it once a second installed
  success-arm proof is needed. Rationale: the installed error arm already has a
  consolidated run-and-assert harness while the success arm hand-rolls the same
  mechanics, leaving the next success-arm proof without a seam to reuse.
