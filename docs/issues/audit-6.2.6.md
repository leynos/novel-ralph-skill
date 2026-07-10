# Post-merge audit: roadmap task 6.2.6

Audit of the codebase after roadmap task 6.2.6 ("extend the installed-binary
exit-3 coverage to `reconcile` and `wordcount`", commit `fdb351d`) merged to
`main`. The task closed the installed-binary exit-3 asymmetry that the 6.2.4
audit recorded as Finding 6: `recount` already had an installed exit-3 proof,
but `reconcile` and `wordcount` had only happy-path installed proofs. Task 6.2.6
added parametrized (missing / unparseable `state.toml`) installed exit-3 e2e
proofs for both commands.

The new tests are correct, well-documented, and prove the intended boundary. The
findings below are not defects in the new behaviour: they are the duplication and
build-cost consequences of landing the exit-3 proofs by inline copy-paste while
the shared scaffolding those proofs were always meant to consume — proposed by
the 6.2.4 audit and already triaged onto the roadmap as tasks 7.23.1 and
7.23.2 — does not yet exist. Task 6.2.6 therefore widened the blast radius of two
roadmap items that already carry the consolidation work, and the proposed fixes
below are to keep those items honest rather than to open new work. None block the
merge.

Sources relied on: `docs/issues/audit-6.2.4.md` (Findings 1, 3, 4, 6 — the
direct predecessors of this change), `docs/roadmap.md` (tasks 6.2.6, 7.23.1,
7.23.2), `docs/developers-guide.md` ("Shared test scaffolding"),
`docs/novel-ralph-harness-design.md` (§3.2 mutator-refusal-is-3, §9
installed-binary criteria, §10 message-not-traceback),
`docs/adr-003-shared-interface-contract.md` (Table 2 exit-code contract),
`docs/adr-006-console-scripts-e2e-posix-policy.md`, and `AGENTS.md` (module and
local-variable caps, bare-`assert` policy). Code navigated with `leta`; history
traced with `git show` over commit `fdb351d`. Skills consulted: `python-router`,
`python-testing` (fixture scope and parametrize-over-copy-paste guidance).

## Finding 1: The installed exit-3 test body is now copy-pasted across three modules

- **Category:** duplication
- **Severity:** medium
- **Location:** `tests/test_recount_e2e.py:150`
  (`test_installed_novel_state_recount_state_error_exits_three`, the 6.2.4
  original); `tests/test_reconcile_e2e.py:254`
  (`test_installed_novel_state_reconcile_state_error_exits_three`, added by
  6.2.6); `tests/test_wordcount_e2e.py:134`
  (`test_installed_wordcount_state_error_exits_three`, added by 6.2.6).

The `recount` and `reconcile` installed exit-3 test bodies are byte-for-byte
identical apart from the single subcommand literal (`"recount"` versus
`"reconcile"`). Both build the same `run_dir / "working"` tree, write the same
`state_bytes`, build the same `Program` / catalogue / `sh.make(...)(<sub>)`
incantation under `ExecutionContext(cwd=run_dir)`, and close with the same
three-assertion triplet:

```python
assert result.exit_code == 3, result.stderr
assert json.loads(result.stdout or "{}")["ok"] is False
assert "Traceback" not in (result.stderr or "")
```

The `wordcount` copy differs only in that it builds its own script (function
helper rather than the `novel-state` fixture) and invokes the empty call `()`
rather than a subcommand; the tree-setup and assertion triplet are again the
same. The triplet now appears verbatim at three e2e sites (plus
`tests/test_console_scripts_e2e.py:121` carries the `Traceback`-absence
assertion), so a future change to the exit-3 contract — say, pinning the
envelope `error.code` once the contract fixes it — must be edited in three
places that have no shared anchor.

The 6.2.4 audit's proposed fix for its Finding 6 stated the intent plainly:
"Once Finding 3's `run_installed` helper exists, each addition is a few lines."
Task 6.2.6 added the cases before that helper existed, so each addition is a
full ~15-line copy instead.

- **Proposed fix:** Land roadmap task 7.23.2 (the shared `run_installed` helper)
  and then express these three tests as thin delegations: a single
  parametrized body that takes the invocation arguments
  (`("recount",)`, `("reconcile",)`, `()`) and the script source, calls
  `run_installed(...)`, and asserts the shared exit-3 triplet through one helper
  (e.g. `assert_state_error_envelope(result)`). This collapses three near-identical
  bodies to one parametrized case and gives the exit-3 contract assertion a single
  owner. Because the consolidation is already triaged at 7.23.2, the actionable
  step is to record on that roadmap item that 6.2.6 added two more call sites it
  must now retire (see Finding 4).

## Finding 2: The `wordcount` e2e rebuilds the wheel three times where module scope would build once

- **Category:** complexity
- **Severity:** medium
- **Location:** `tests/test_wordcount_e2e.py:51`
  (`_build_and_install_wordcount`, function-scoped helper);
  `tests/test_wordcount_e2e.py:87`
  (`test_installed_wordcount_reports_gate_triggers`, one build) and
  `tests/test_wordcount_e2e.py:134`
  (`test_installed_wordcount_state_error_exits_three`, parametrized
  `[None, b"not = toml ="]`, one build per case).

`reconcile` and `recount` draw their installed script from the module-scoped
`installed_novel_state` fixture (`tests/installed_binary_fixtures.py`), so each
module builds the wheel exactly once no matter how many cases it runs. The
`wordcount` module instead calls the function-scoped `_build_and_install_wordcount`
helper from every test. Before 6.2.6 that module had one installed test (one
build). Task 6.2.6 added a two-case parametrized test, each case of which calls
the helper, so the module now performs **three** full wheel-build + venv +
`uv pip install` cycles where one would do. Each cycle is the slow part the
harness design (§9) and the `installed_novel_state` docstring both call out, and
the per-test `180s` timeout exists precisely because a single cycle is slow. The
6.2.4 audit recorded this exact per-test-rebuild asymmetry as its Finding 4;
6.2.6 measurably worsened it for `wordcount` specifically.

- **Proposed fix:** Route `wordcount` through a module-scoped installed-script
  fixture, as roadmap task 7.23.1 already proposes (a binary-parametrized
  module-scoped fixture factory in `installed_binary_fixtures.py`). Until that
  lands, the narrow stop-gap is to convert `_build_and_install_wordcount` into a
  module-scoped fixture local to the module so the two test functions share one
  build; the exit-3 case writes its faulty `working/` into a per-test `tmp_path`
  subdirectory (it already does — `run-state-error`), so the build is genuinely
  reusable across cases. Record on roadmap 7.23.1 that the `wordcount` module now
  carries a parametrized consumer, making the per-test-rebuild cost it converges
  three builds rather than one.

## Finding 3: A binary-shaped seam (`novel-state <sub>` versus top-level script) is encoded by copy rather than expressed once

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:** `tests/test_reconcile_e2e.py:286`
  (`sh.make(prog, catalogue=catalogue)("reconcile")`),
  `tests/test_recount_e2e.py:180`
  (`...("recount")`), and `tests/test_wordcount_e2e.py:171`
  (`sh.make(prog, catalogue=catalogue)()` — empty call).

The five console-scripts split into two invocation shapes: `recount` and
`reconcile` are `novel-state` subcommands (called with a subcommand string),
while `wordcount` is its own top-level script (called with `()`). Today each e2e
re-derives that distinction inline, and the `wordcount` docstring has to explain
in prose why its call is empty ("`wordcount` is its own top-level
console-script invoked with no subcommand, so it runs with the empty call
`()`"). The knowledge of "which binary takes which call shape" is duplicated
between the prose and the call site in every module instead of living in one
table the e2es read.

- **Proposed fix:** When task 7.23.1 introduces the binary-parametrized fixture
  factory, carry the invocation shape alongside the script name in one place —
  e.g. a small mapping `{"reconcile": ("reconcile",), "recount": ("recount",),
  "wordcount": ()}` — so a test names its binary and the harness supplies both
  the built script and the correct call arguments. The per-module prose then
  shrinks to a reference rather than re-deriving the seam.

## Finding 4: Roadmap tasks 7.23.1 and 7.23.2 understate their scope after 6.2.6

- **Category:** docs-gap
- **Severity:** low
- **Location:** `docs/roadmap.md:2763` (task 7.23.1) and `docs/roadmap.md:2791`
  (task 7.23.2). Both cite their evidence as `docs/issues/audit-6.2.4.md`
  Findings 1–5 and enumerate the call sites as they stood at 6.2.4.

The two consolidation tasks were written against the 6.2.4 snapshot. Since then,
task 6.2.6 has added a second installed exit-3 copy (Finding 1 above) and a
parametrized function-scoped-build consumer to `test_wordcount_e2e.py`
(Finding 2 above). Task 7.23.2's success criterion ("one shared `run_installed`
helper owns the installed-script run convention every e2e site delegates to")
and 7.23.1's
("the installed-binary e2e builds are uniformly module-scoped so each wheel is
built once per module rather than per test") are still correct, but the call-site
inventories the tasks cite no longer match the tree: the `reconcile` and
`wordcount` exit-3 tests are new sites that the consolidation must retire, and
the `wordcount` module now rebuilds three times rather than one.

- **Proposed fix:** Append a 6.2.6 addendum note to roadmap tasks 7.23.1 and
  7.23.2 recording the two new call sites (`test_reconcile_e2e.py:254`,
  `test_wordcount_e2e.py:134`) and the three-build `wordcount` module, so the
  consolidation work is scoped against the current tree rather than the 6.2.4
  snapshot. (Roadmap edits are reserved to the root agent; this is proposed, not
  applied.)

## Finding 5: No installed exit-3 proof for `desloppify`, the fifth state-input command

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_desloppify_e2e.py` (happy-path installed proofs
  only) versus `tests/test_recount_e2e.py:150`,
  `tests/test_reconcile_e2e.py:254`, `tests/test_wordcount_e2e.py:134`
  (installed exit-3 proofs).

Task 6.2.6's commit message frames the step-6.2 hypothesis as "the five commands
behave correctly across the full command × output-mode matrix when run as
installed binaries". After 6.2.6, three of the state-reading commands
(`recount`, `reconcile`, `wordcount`) carry installed exit-3 proofs. `desloppify`
also reads a `working/` tree and a pack file and can exit 3 — its in-process
suite proves `test_absent_pack_file_exits_three` and
`test_absent_working_dir_exits_three` (`tests/test_desloppify_command.py:123`,
`151`) — but it has no installed exit-3 proof. This is the same narrow
installed-versus-in-process asymmetry that 6.2.4's Finding 6 recorded for
`reconcile` and `wordcount`, now carried for `desloppify` alone. The gap is
small (in-process coverage exists), but it is the symmetric remainder of the very
asymmetry 6.2.6 set out to close.

- **Proposed fix:** Once the `run_installed` helper (7.23.2) and the shared
  installed exit-3 assertion (Finding 1) exist, add a parametrized installed
  exit-3 case to `tests/test_desloppify_e2e.py` mirroring the three siblings, so
  every state-input command's exit-3 path is proven at the packaging boundary,
  not only in-process. Until then, record the `desloppify` gap explicitly so it
  is carried knowingly rather than silently (design §9).

## Finding 6: The 6.2.4-audit cross-reference in the new docstrings points at a moving target

- **Category:** docs-gap
- **Severity:** low
- **Location:** `tests/test_reconcile_e2e.py` module docstring
  ("...anchors its exit-3 state-or-input-error path at the packaging boundary
  (audit Finding 6)") and the same phrase in `tests/test_wordcount_e2e.py`.

The new module docstrings cite "audit Finding 6" without naming which audit. The
reference is to `docs/issues/audit-6.2.4.md` Finding 6, but a bare "Finding 6"
will not survive: each post-merge audit restarts its finding numbering, so a
future reader landing on this docstring cannot resolve which audit's Finding 6 is
meant without external knowledge. The harness's own convention elsewhere (e.g.
roadmap reroute notes) qualifies the reference as `audit:6.2.4 Finding 6`.

- **Proposed fix:** Qualify the docstring citation as `audit-6.2.4 Finding 6`
  (matching the roadmap's `audit:N.N.N Finding N` convention) so the reference
  is stable across subsequent audits. A one-line edit in each of the two module
  docstrings.
