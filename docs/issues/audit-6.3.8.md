# Post-merge audit — roadmap task 6.3.8

Audit of the codebase after roadmap task 6.3.8 ("Make the remaining exit-3
write/file-fault arms actionable") merged to `main` at commit `de2f9cc`. The
task routed the three remaining raw-OS-text leaks on the exit-3 (state-input)
channel — the compile-write fault, the `desloppify --pack` rule-pack-read
fault, and the `desloppify --ledger` device-ledger-read fault — through three
new shared formatters in the dependency-free leaf module
`novel_ralph_skill/commands/_state_load.py`: `_compile_write_error`,
`_rule_pack_read_error`, and `_device_ledger_read_error`. They join the
pre-existing `_state_input_error` (roadmap §6.3.1) and `_draft_read_error`
(roadmap §6.3.5), so there are now five sibling formatters, all re-exported
through `novel_ralph_skill/commands/novel_state.py`. A cross-arm tripwire
(`tests/test_state_load_actionable_parity.py`) pins the no-raw-leak property
structurally, and each command arm has e2e behavioural coverage in
`tests/test_compile_e2e.py` and `tests/test_desloppify_command.py`.

Trail followed: `docs/novel-ralph-harness-design.md` §3.2 (the exit-code
contract), `docs/scripting-standards.md` lines 603-605 and 678 (actionable
prose, never raw OS text), `docs/developers-guide.md` §"exit-3 messages are
actionable" (line 619), the ADRs (ADR-001 deterministic/judgemental boundary,
ADR-003 shared interface contract, ADR-005 command surface), `AGENTS.md`
(quality gates, the 400-line file cap, CQS, en-GB Oxford spelling), the
`python-router` skill (routing to `python-errors-and-logging` and
`python-testing`), and `leta`/`sem` for navigation and history. Files
inspected: `novel_ralph_skill/commands/_state_load.py`,
`novel_ralph_skill/commands/_compile.py`,
`novel_ralph_skill/commands/_desloppify.py`,
`novel_ralph_skill/commands/_desloppify_ledger.py`,
`novel_ralph_skill/commands/_gate_drafting_mutators.py`,
`novel_ralph_skill/commands/novel_state.py`,
`tests/test_state_load_actionable_parity.py`,
`tests/test_desloppify_command.py`, `tests/test_compile_e2e.py`,
`pyproject.toml`, and `docs/developers-guide.md`.

The merged change is high quality. The leak-removal is genuine (verified by the
parity tripwire and the per-arm e2e tests, all of which assert the artefact path
is named, the operator-facing flag is present, and no `Errno`, class name, or
`str(exc)` repr leaks), the import direction avoids the `_state_mutators` →
`novel_state` cycle as the module docstring claims, and the file stays inside
the 400-line cap. The findings below are at the ergonomics, similarity, and
documentation-narrative layer; none is a correctness defect.

## Finding 1 — `exc` is a dead parameter on every exit-3 formatter

- **Category:** cqs / ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_state_load.py:94`,
  `:140`, `:189`, `:230`, `:271` (`_state_input_error`, `_draft_read_error`,
  `_compile_write_error`, `_rule_pack_read_error`, `_device_ledger_read_error`)

Each of the five formatters accepts `exc: Exception` (or the typed equivalent)
but never reads it: the only use of a caught exception anywhere in the module is
the `raise … from exc` chaining performed by the *caller* and by
`_load_or_state_error` (`:338-339`). The parameter is a deliberate convenience
— it lets `tests/test_state_load_actionable_parity.py` drive all five formatters
through one `(path, exc)` call signature — but on the production call sites it
reads as if the exception influences the message, which is exactly the coupling
6.3.8 set out to remove. The docstrings even have to spend a paragraph each
explaining that `exc` is *not* consulted ("the caller chains `exc` via `from`
for debugging while `exc.messages` carries only the actionable prose"). Note
that `ARG` (flake8-unused-arguments) is **not** in the `pyproject.toml` ruff
`select` list, so the dead parameter passes lint silently.

**Proposed fix:** drop the `exc` parameter from the four file/write-fault
formatters whose body is path-only (`_draft_read_error`, `_compile_write_error`,
`_rule_pack_read_error`, `_device_ledger_read_error`), changing call sites from
`raise _draft_read_error(root, exc) from exc` to
`raise _draft_read_error(root) from exc` — the `from exc` chaining is unchanged
and stays the single source of the debugging link. Update the parity test to
build the formatter args by `label` (it already parametrizes by label) rather
than assuming a uniform two-arg signature, or keep `exc` only where a future arm
genuinely needs to branch on the exception. `_state_input_error` may keep `exc`
if a future arm is expected to branch on exception type, but should then say so;
otherwise drop it too. As a cheaper alternative, add `ARG` to the ruff `select`
set so any future dead argument is caught, and annotate the intentional ones
with `del exc` or a `# noqa: ARG001` carrying the parity-signature rationale.

## Finding 2 — the four file-fault formatters are near-identical single-arm builders

- **Category:** similarity / duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_state_load.py:140-307`
  (`_draft_read_error`, `_compile_write_error`, `_rule_pack_read_error`,
  `_device_ledger_read_error`)

The four read/write-fault formatters share an identical shape: a single arm, no
branching, a `message = f"…{path}…"` f-string, and
`return StateInputError(message)`. They differ only in the artefact noun ("the
drafts under", "rule pack", "device ledger", "write {target}") and the remedy
clause. Each also carries a ~25-line docstring that re-states the same
invariants (single arm, never advises `init`, no `Errno`/`{exc}`/traceback
leak), so the bulk of `_state_load.py`'s growth from 6.3.5 to 6.3.8 is
copy-adapted prose. This is acceptable for five arms but will not scale: a sixth
file-fault arm means a sixth copy of the same scaffold and docstring.

**Proposed fix:** factor the common shape into one private builder, e.g.
`_file_fault_error(message: str) -> StateInputError` that wraps the
`StateInputError(message)` construction and hosts the shared "no-raw-leak"
contract docstring once, leaving each named formatter as a thin
artefact-and-remedy wrapper (`return _file_fault_error(f"cannot read rule pack
{pack_path}; …")`). The named wrappers stay the public seam the parity test and
call sites import, the per-arm docstrings shrink to the artefact/remedy
specifics, and the shared invariant is documented in exactly one place. This
also makes Finding 1 a one-line change (the shared builder takes no `exc`).

## Finding 3 — duplicated content-vs-file exception-routing in the desloppify modes

- **Category:** duplication / separation-of-concerns
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_desloppify.py:257-272`
  (rule-pack load) and `novel_ralph_skill/commands/_desloppify_ledger.py:80-95`
  (ledger load)

The `--pack` and `--ledger` load boundaries implement the same two-arm routing
verbatim: catch the *content* error (`RulePackError` / `LedgerError`) and return
an exit-2 `CommandOutcome`, then catch the *file* error (`RulePackFileError` /
`LedgerFileError`) and `raise _<artefact>_read_error(path, exc) from exc` for
exit 3. The structure, the comments, and the `messages=list(exc.messages) or
[str(exc)]` projection are duplicated between the two modes. The two artefact
families (`rulepack` and `ledger`) are genuinely distinct domains, so the catch
*types* differ, but the load-and-route *policy* ("malformed content → exit 2;
unreadable file → exit 3 actionable") is one rule expressed twice.

**Proposed fix:** introduce a small shared helper that takes the loader, the
path, the content-error type, the file-error type, and the file-fault formatter,
and applies the two-arm policy once — for example
`load_or_route(loader, path, content_error=…, file_error=…,
file_formatter=…) -> Resource | CommandOutcome` returning either the loaded
resource or the exit-2 outcome and raising the exit-3 `StateInputError`. The two
call sites collapse to one line each, and a future third rationing input
inherits the policy for free. Keep the domain-specific catch types as
parameters so the rulepack→contract and ledger→contract couplings stay out of
the shared seam (the existing rationale for catching them locally).

## Finding 4 — the `list(exc.messages) or [str(exc)]` idiom is repeated four times

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_desloppify.py:262`, `:352`,
  `novel_ralph_skill/commands/_desloppify_ledger.py:86`,
  `novel_ralph_skill/commands/_gate_drafting_mutators.py:205`

The "project a usage error onto an exit-2 `CommandOutcome`, falling back to the
stringified exception when `messages` is empty" idiom appears at four sites
across three modules with identical text. It is a single decision — *how a typed
usage error becomes a `CommandOutcome`* — copied rather than named, so a change
to the fallback policy (or a future requirement to strip a trailing newline,
say) must be made in four places.

**Proposed fix:** add one constructor on the contract layer, e.g.
`CommandOutcome.usage_error(exc)` or a free helper
`usage_outcome(exc) -> CommandOutcome` in `novel_ralph_skill/contract/runner.py`
that owns the `code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or
[str(exc)]` projection, and route the four sites through it. This pairs
naturally with the Finding 3 helper (the shared loader can return
`usage_outcome(exc)` on the content arm).

## Finding 5 — the developer guide still describes "two sibling formatters"

- **Category:** docs-gap
- **Severity:** medium
- **Location:** `docs/developers-guide.md:619-636`

The exit-3 section opens "The exit-3 messages are actionable, never raw OS text.
**Two** sibling formatters in the dependency-free leaf module `_state_load` own
the prose." After 6.3.8 there are **five** formatters. `_state_input_error` and
`_draft_read_error` are described in full, but the three 6.3.8 additions are
compressed into a single trailing sentence — "The `novel compile`
atomic-*write* tail and the desloppify rule-pack/device-ledger faults keep their
own write- and file-shaped messages" — without naming `_compile_write_error`,
`_rule_pack_read_error`, or `_device_ledger_read_error` or stating their
remedies (re-create `working/manuscript/`; check or omit `--pack`; check
`--ledger`). A developer reading the guide would under-count the formatters and
miss where the new prose lives. This is the only finding that touches a stated
source of truth (the developers' guide) and so carries the higher severity.

**Proposed fix:** update the sentence at line 619 to say "Five sibling
formatters" and add a short paragraph (or bullet list) naming the three 6.3.8
formatters, the artefact each names, and the write-/file-shaped remedy each
offers, mirroring the existing treatment of `_state_input_error` and
`_draft_read_error`. Cross-reference roadmap §6.3.8 as the existing prose does
for §6.3.1 and §6.3.5. Confirm the `users-guide.md` exit-code narrative needs no
change (the operator sees the rendered message, not the formatter names).

## Finding 6 — the file-fault remedy wording is unpinned by any test

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_desloppify_command.py:125-177`,
  `:276-329`, `tests/test_compile_e2e.py:229-260`,
  `tests/test_state_load_actionable_parity.py`

The behavioural tests assert the *structural* invariants well — the artefact
path is present, the operator-facing flag (`--pack` / `--ledger`) is present,
and no `Errno`/class-name/`str(exc)` leaks — but no test pins the *remedy*
clause that makes the message actionable: "omit --pack to use the shipped
default pack", "check the --ledger path is correct and readable", or "re-create
it or restore the working tree". A regression that silently dropped the remedy
clause (leaving only the artefact name) would still pass every current
assertion, defeating the actionability contract `scripting-standards.md` line
678 exists to protect. This is a genuine gap but a narrow one — the no-leak
property, the harder invariant, is fully guarded — so it is low severity.

**Proposed fix:** add one substring assertion per arm pinning a stable fragment
of the remedy (e.g. `assert "omit --pack" in joined`,
`assert "re-create" in joined` for the compile-write arm). Prefer a short,
deliberately stable token over the whole sentence so wording polish does not
churn the test. Alternatively, extend the parity tripwire with a
`_REMEDY_TOKENS` table mapping each formatter label to the fragment it must
emit, keeping the actionability contract enforced structurally alongside the
no-leak contract it already guards.
