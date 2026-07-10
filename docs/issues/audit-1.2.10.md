# Post-merge audit — roadmap task 1.2.10

Audit of the codebase after roadmap task 1.2.10 ("Replace the bare `sh.make(...)`
expression statement in `test_conftest_helpers` with an explicit assertion")
merged to `main` at commit `0624db7`. The slice itself is small and correct: the
formerly discarded `sh.make(...)` call in
[`tests/test_conftest_helpers.py`](../../tests/test_conftest_helpers.py)
(`test_single_program_catalogue_builds_usable_allowlist`) now binds the returned
builder, asserts it is callable, builds the `SafeCmd`, and asserts the resolved
`program`, so the "does not raise" intent is explicit and a regression in
`sh.make` resolution would fail the test rather than pass silently. That work
needs nothing further.

This audit re-checks the wider codebase against the recurring themes carried by
`docs/issues/audit-1.2.1.md` through `docs/issues/audit-1.2.8.md`. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity. None is a blocking defect; they are tidy-up opportunities. Several map
onto roadmap items already queued (1.2.11, 1.2.12, 1.2.13) — those are noted as
such so the root agent does not double-book them.

Trail followed: explored with `leta` (`leta show`, `leta refs`, `leta files`)
and traced history with `sem diff --commit`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.1–3.2, ADR 003
(`docs/adr-003-shared-interface-contract.md`), ADR 005 and 006,
`docs/developers-guide.md`, `docs/contents.md`, and `AGENTS.md`.

## Finding 1 — `render_human`'s empty-messages branch is never exercised

- **Category:** test-gap
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/contract/envelope.py:166-170`](../../novel_ralph_skill/contract/envelope.py)
  (the `else` arm emitting `messages: (none)`),
  [`tests/test_contract_envelope.py`](../../tests/test_contract_envelope.py)

Every call to `render_human` in the suite passes a non-empty `messages`
sequence: `test_render_human_lists_messages_without_result_json` passes two
notes, and both `test_render_human_success_snapshot` and the per-code human
snapshot pass one note. The `if env.messages:` branch is therefore always
taken, and the `else` branch that emits the literal `messages: (none)` line for
a message-less envelope is dead with respect to the test suite. A success
envelope with no human prose is a real, expected shape (a checker that is
satisfied and has nothing to say), so the unrendered branch is exactly the path
a future edit could break unnoticed — for example collapsing the `(none)`
sentinel or dropping the line entirely.

**Proposed fix:** add a focused test that builds an envelope with `messages=[]`
and asserts `render_human(env)` contains the literal `messages: (none)` line and
does *not* contain a two-space-and-dash message bullet. A syrupy snapshot of
the empty-messages human rendering would also pin the exact line, mirroring the
existing
`test_render_human_success_snapshot`. `make test` over the new case suffices.

## Finding 2 — A third copy of the wrapper-configured app builder (`_build_app` / `_make_app`)

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_contract_runner.py:32`](../../tests/test_contract_runner.py)
  (`_build_app`),
  [`tests/test_contract_properties.py:131`](../../tests/test_contract_properties.py)
  (`_build_app`),
  [`tests/test_cyclopts_contract.py:49`](../../tests/test_cyclopts_contract.py)
  (`_make_app`)

`audit-1.2.8.md` Finding 3 flagged two copies of the `run`-driver app builder
(`test_contract_runner.py` and `test_cyclopts_contract.py`). A third near-clone
now exists in `test_contract_properties.py`: `_build_app(outcome)` builds a
Cyclopts app with the same load-bearing
`result_action="return_value", exit_on_error=False, print_error=False,
help_on_error=False` configuration the `run` wrapper requires. All three encode
the identical fragile pin in three places; a future cyclopts upgrade that
changes one of those keyword defaults must be re-discovered and re-fixed three
times, and a copy that silently drifts from the pin would weaken its module's
guarantees without any single failing test pointing at the drift.

**Proposed fix:** lift a single `wrapper_app` (or `build_wrapper_app`) fixture
into `tests/conftest.py` that returns a builder taking the body/outcome and
returning a `run`-configured `cyclopts.App` with the four pinned keywords in one
place, then migrate all three modules onto it. This is the same consolidation
pattern the conftest fixtures already apply to `read_repo_text`, `toml_table`,
and `single_program_catalogue`. Consider folding it into the 1.2.11 conftest
migration since both touch the same file.

## Finding 3 — Three divergent PEP 508 distribution-name normalizers (carried; roadmap 1.2.11)

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`tests/test_contract_test_deps.py:79`](../../tests/test_contract_test_deps.py)
  (`spec.split()[0].split(">")[0].split("=")[0]`),
  [`tests/test_interrogate_gate.py:24-30`](../../tests/test_interrogate_gate.py)
  (`_DIST_NAME` regex + `_dist_name`),
  [`tests/test_command_names_registry.py:21`](../../tests/test_command_names_registry.py)
  (`_parse_scripts`)

This is the duplication first raised in `audit-1.2.7.md` Findings 1–3 and carried
in `audit-1.2.8.md` Findings 4–6; it remains open after 1.2.10. `test_interrogate_gate.py`
carries a robust regex normalizer (`_dist_name`) that strips version specifiers,
extras, and markers, whereas `test_contract_test_deps.py` carries a weaker
ad-hoc `split()`-chain that only handles `>` and `=` separators and would mis-key
a specifier using `~=`, `<`, `!=`, `;`-markers, or an extras bracket. The two
copies disagree, and `test_contract_test_deps.py` additionally re-parses
`pyproject.toml` through its own `_PYPROJECT`/`_dev_dependencies` helpers rather
than the shared `pyproject`/`toml_table` conftest fixtures.

**Proposed fix:** this is precisely the scope of roadmap task 1.2.11 — lift a
single `dist_name` (PEP 508 bare-name) fixture into `conftest`, migrate
`test_contract_test_deps.py` onto the `pyproject`/`toml_table` fixtures, and
delete the weaker `split()`-chain. No new roadmap item is needed; flagging here
only to record that 1.2.10 did not touch it.

## Finding 4 — `docs/contents.md` omits ADR 006, the terms of reference, and the issues/execplans sets (carried; roadmap 1.2.12)

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/contents.md`](../../docs/contents.md)

The documentation index lists ADRs 001–005 but not
[`adr-006-console-scripts-e2e-posix-policy.md`](../../docs/adr-006-console-scripts-e2e-posix-policy.md),
and it omits [`terms-of-reference.md`](../../docs/terms-of-reference.md) entirely
as well as the now-substantial `docs/issues/` audit-trail set (nine files) and
the `docs/execplans/` per-task plan set. This is the long-open item from
`audit-1.2.5.md` Finding 6 through `audit-1.2.8.md` Finding 7. The audit history
and per-task plans remain undiscoverable from the documentation map.

**Proposed fix:** roadmap task 1.2.12 already covers indexing ADR 006 and the
`docs/issues/`/`docs/execplans/` sets. Extend its scope by one bullet to also add
`terms-of-reference.md` to the index (it predates the ADRs and is genuinely
missing). No new roadmap item required.

## Finding 5 — Leftover project-template scaffold (`pure.py` / `hello` / `test_stub.py`) is unrelated to the harness

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/pure.py`](../../novel_ralph_skill/pure.py),
  [`novel_ralph_skill/__init__.py:15-19`](../../novel_ralph_skill/__init__.py),
  [`tests/test_stub.py`](../../tests/test_stub.py)

`pure.py` exports a single `hello()` returning `"hello from Python"`, and
`__init__.py` carries the matching Rust-or-Python fallback wiring
(`import_module("._novel_ralph_skill_rs")` … `from .pure import hello`) with
`test_stub.py` asserting the greeting. This is boilerplate from the pure-Python
project template, not part of the deterministic spine the design describes: there
is no Rust extension in this repository, `hello` is not part of the contract
surface (ADR 003), and the docstrings ("Generated pure-Python projects use this
module…") describe a generator, not this harness. The dead fallback path is
`# pragma: no cover`'d, so it inflates the public surface and the docstring count
without earning its place. It is harmless but it muddies the package's domain:
a reader opening `__init__.py` first meets template greeting machinery rather
than the command/contract architecture.

**Proposed fix:** decide the package's intended public entry shape and either
(a) remove `pure.py`, the `hello` re-export, and `test_stub.py`, trimming
`__init__.py` to the genuine package surface; or (b) if a `_rs` accelerator is
genuinely planned, record that intent in a short ADR or design note so the
fallback wiring reads as deliberate rather than vestigial. Given the design names
no Rust component, (a) is the likelier correct call. This is a small, isolated
cleanup that the root agent may wish to track as a roadmap item.

## Finding 6 — `STUB_EXIT_CODE` re-spells the contract's usage-error code as a bare literal

- **Category:** inconsistency
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/stub.py:18`](../../novel_ralph_skill/commands/stub.py)
  (`STUB_EXIT_CODE = 2`),
  [`novel_ralph_skill/contract/exit_codes.py:26`](../../novel_ralph_skill/contract/exit_codes.py)
  (`ExitCode.USAGE_ERROR = 2`)

The stub module defines `STUB_EXIT_CODE = 2` with a docstring naming it "usage
error, design 3.2", which is exactly `ExitCode.USAGE_ERROR`. The contract package
now exists (`novel_ralph_skill.contract.exit_codes`) as the single source of
truth for the exit-code vocabulary, yet the stub hard-codes the integer `2`
independently. If a future contract revision were ever to renumber the usage-error
code, the stubs would silently diverge from the contract they are meant to honour.
This is a latent instance of the same single-source-of-truth principle the
command-names registry (`names.py`) already enforces.

**Proposed fix:** import `ExitCode` from `novel_ralph_skill.contract.exit_codes`
and define `STUB_EXIT_CODE = ExitCode.USAGE_ERROR` (or use the enum member
directly in the `sys.exit` call), so the stubs bind to the contract's vocabulary
rather than re-spelling its value. Because `ExitCode` subclasses `int`,
`sys.exit(ExitCode.USAGE_ERROR)` already exits `2`, so behaviour is unchanged.
A small test could assert `STUB_EXIT_CODE == ExitCode.USAGE_ERROR` to pin the
binding. This is best sequenced when the stubs adopt the envelope contract
(roadmap 1.3.x), so they migrate onto the contract module in one move rather than
twice.

## Notes on what was checked and found sound

- The `run` wrapper (`contract/runner.py`) cleanly separates command bodies from
  exit-code translation and envelope emission; the `CommandOutcome`/`RunContext`
  split and the `StateInputError` exit-3 channel are well-documented and match
  design §3.2 and ADR 003. No command-query-separation violation found:
  `build_envelope` is a pure query, `_emit`/`run` are the commands, and the
  boundary is clean.
- `build_envelope` deriving `ok` from `is_ok(code)` (rather than accepting it as
  a parameter) correctly forecloses the inconsistent-`ok` failure mode, and
  `render_machine` building the ordered dict explicitly rather than leaning on
  dataclass field order is a deliberate, well-reasoned choice.
- The command-names registry (`commands/names.py`) remains the single source of
  truth, with `MappingProxyType` guarding the underlying dict and
  `project_scripts_table` returning a fresh dict per call; the stub entry points
  read their names back through the reverse map rather than re-spelling them.
- `interrogate` 100% docstring coverage is enforced and pinned by a static gate;
  the contract and command modules carry full numpydoc docstrings.
