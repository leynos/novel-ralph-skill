# Post-merge audit — roadmap task 1.2.14

Task 1.2.14 swept `docs/novel-ralph-harness-design.md` and
`skill/novel-ralph/SKILL.md` to the single `novel` multiplexer surface (commit
`5559198`). The change is documentation-only: no production module under
`novel_ralph_skill/` was touched, and no behaviour changed. The sweep itself is
clean — the design document and `SKILL.md` now present the `novel` surface
consistently, and the accompanying ExecPlan and Logisphere review are
self-contained.

Because 1.2.14 carried no code, this audit treats the merge as a checkpoint and
reviews the surrounding production surface — chiefly the `novel-state` command
package and the rule-pack/ledger validating boundaries — for refactoring
opportunities, duplication, inconsistencies, separation-of-concerns and CQS
issues, and gaps in documentation and tests. Each finding records a location and
a concrete proposed fix.

The codebase explored: the worktree at `5559198` (origin/main HEAD at the time
of writing is `0eee0c1`; the docs-only change in this audit is rebased onto
current main before push). Exploration used `leta` for navigation and `sem` for
history; files inspected include `novel_ralph_skill/commands/novel_state.py`,
`_state_mutators.py`, `_gate_drafting_mutators.py`, `_recount.py`,
`_reconcile.py`, `_set_chapters.py`, `_desloppify.py`; the validating boundaries
`novel_ralph_skill/rulepack/_coerce.py` and `novel_ralph_skill/ledger/_coerce.py`
and their `detect.py` counterparts; `novel_ralph_skill/contract/runner.py`; the
developers' guide §"State mutators"; and `docs/roadmap.md`.

The most material **new** finding is that the load-edit-validate-write mutator
skeleton is now hand-copied across eight command bodies with no shared
orchestrator, even though its three disciplines are documented as conventions.
Two further structural duplications — the rule-pack/ledger `_coerce` near-copy
and the body-detected exit-2 usage-error adapter — are real and persistent, but
both are **already triaged onto the roadmap** (the `_coerce` reroute near
`docs/roadmap.md:4201-4219`, and task `7.16.7` for the usage adapter), so they
are recorded here as standing items for continuity rather than as new proposals.

## 1. The load-edit-validate-write mutator skeleton is hand-copied across eight bodies

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_state_mutators.py`
  (`set_cursor` lines 234-256; `advance_phase` lines 323-347);
  `novel_ralph_skill/commands/_gate_drafting_mutators.py`
  (`_set_gate` 168-183; `_complete_final_pass` 242-253; `_set_fangirl` 278-300;
  `_set_critic_pass` 327-342);
  `novel_ralph_skill/commands/_recount.py` (lines 222-232);
  `novel_ralph_skill/commands/_set_chapters.py` (lines 280-346)

Every state mutator re-spells the same seven-step sequence by hand: resolve
`_state_path()`, `_load_document_or_state_error(path)`, derive the structural-
completeness view via `_state_view_or_state_error(document)`, edit the live
`tomlkit` document in place, re-derive the proposed view, `_refuse_if_incoherent`,
`write_document_atomically(document, path)`, then build a `CommandOutcome`. The
shared *leaf* helpers exist (`_load_document_or_state_error`,
`_state_view_or_state_error`, `_refuse_if_incoherent`), but the *orchestration*
that wires them in the mandated order does not, so each new mutator copies the
skeleton and its load-bearing ordering comments. The bodies' own docstrings admit
this: `_gate_drafting_mutators.py` says "Every body follows the `set_cursor`
skeleton". The developers' guide (§"State mutators", around line 1006) documents
the validate-before-persist discipline as a *convention* — i.e. a rule enforced
by reviewer vigilance and copy-paste fidelity, not by a single tested function.

The harm is shotgun-surgery risk: the structural-completeness pre-derivation
(the "derive the view first so a missing table does not exit 1" guard, breaching
the exit-3 contract — BR2-1) must be repeated verbatim in every body, and a
mutator author who omits it reintroduces the exact exit-1 leak the comments warn
against. Eight copies is past the threshold where a missed copy is likely.

- **Proposed fix:** Introduce one orchestrator in `_state_mutators.py` (or a
  contract-adjacent location), for example
  `apply_state_mutation(*, edit, build_result, context, remedy=None)`, where
  `edit(document, prior_view) -> dict[str, object]` performs the in-place edit
  and returns the write-shaped `result`, and the helper owns load → pre-derive →
  edit → re-derive → `_refuse_if_incoherent` → atomic write → `CommandOutcome`.
  Each body shrinks to its edit closure plus any write-time precondition. Gate on
  the existing per-mutator unit, property, snapshot, and BDD suites to prove no
  envelope or exit-code drift, then update the developers' guide so the
  discipline is described as *embodied in the orchestrator* rather than a
  hand-followed convention. This is a new finding (audit:2.2.4 covered the
  usage-error adapter, the registration-idiom split, and the 400-line ceiling,
  but not the skeleton itself).

## 2. `_set_fangirl` and `_set_critic_pass` duplicate the precondition-refusal idiom

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_gate_drafting_mutators.py`
  (`_set_fangirl` lines 282-291; `_set_critic_pass` lines 330-333)

Both bodies carry the same write-time precondition shape: test a bound, build a
`summary` naming the breached rule (`fangirl-chapter-in-manifest`,
`critic-pass-at-least-one`), build a human `detail`, then
`raise StateInputError(summary, detail)`. The wording is parallel and the
construction is identical save for the predicate and the two strings. This is the
"check a bound, refuse with a named rule" idiom that `set-chapters`'
`manifest_coherence_violations` (ADR 008) generalizes for its own domain, but the
two scalar preconditions here re-spell it inline.

- **Proposed fix:** Extract a small `_refuse_unless(condition, *, rule, detail)`
  helper in the mutator module that raises `StateInputError(f"… {rule}", detail)`
  when `condition` is false, so each body reads as a single guarded assertion and
  the "rule name first, detail second" message contract has one home (mirroring
  the `_refuse_if_incoherent` precedent). Fold this into Finding 1's refactor if
  that lands first, since the orchestrator can accept the precondition list
  directly. Gate on the `set-fangirl`/`set-critic-pass` unit and property suites.

## 3. The `novel-state` builder mixes three command-registration import idioms

- **Category:** inconsistency
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/novel_state.py` (`build_app`,
  lines 320-399)

`build_app` registers its subcommands three different ways: `_state_mutators` is
imported once at the top of `build_app` and its bodies are called from the nested
`@app.command` wrappers (`set_cursor`, `advance_phase`); `recount`, `reconcile`,
and `set_chapters` each import their body module *inside the nested wrapper
function* (lazy per-call import); and `_gate_drafting_mutators` is imported just
before its `register_gate_drafting_commands(app)` call and registers its four
commands through a registrar. Three idioms for the same job make the module
harder to scan and obscure which imports are deferred for cycle-breaking versus
incidental. (audit:2.2.4 Finding 6 already flagged that *two* registration idioms
coexist — direct `@app.command` wrappers versus the registrar; this finding
extends that to the three distinct *import* placements now present.)

- **Proposed fix:** Pick one idiom. The cleanest is to hoist all the mutator-
  module imports to a single deferred block at the top of `build_app` (they must
  stay inside the function to break the `commands → novel_state` cycle, as the
  existing comments note) and have every subcommand call `module.body(...)`
  uniformly, dropping the per-wrapper lazy imports. Document the one remaining
  reason an import is deferred (cycle-breaking) in a single comment rather than
  repeating it per wrapper. Gate on the command-registration and
  command-surface-matrix suites.

## 4. Standing item — rule-pack/ledger `_coerce` near-copy (already on the roadmap)

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/ledger/_coerce.py` (whole module) versus
  `novel_ralph_skill/rulepack/_coerce.py` (whole module)

The two `_coerce` modules remain near-byte-for-byte identical — `_where`,
`_reject_unknown_keys`, `_require`, `_require_str`, `_require_int` share their
entire control flow, message structure, and `bool`-rejection logic — differing
only in the raised error type (`LedgerError` versus `RulePackError`), the noun
(`"device"`/`"device ledger"` versus `"rule"`/`"rule pack"`), and the keyword
name (`device_id` versus `rule_id`). The ledger module's docstring (lines 10-18)
acknowledges the copy and explains why a *direct* import would mis-route the typed
error and prose. The duplication persists at 1.2.14 only because the 1.2.13–1.2.16
lane was a documentation/naming sweep, not a refactoring lane.

- **Proposed fix:** No new action required from this audit. This is already
  triaged as the `_coerce` reroute at `docs/roadmap.md:4201-4219` (source
  audit:7.1.2 Finding 2): extract a shared coercion module parameterized on an
  injected error factory plus a shared scan-pattern primitive, with each package
  binding its own error type, noun, and keyword. Recorded here for continuity so
  the standing duplication is visible from the 1.2.14 checkpoint.

## 5. Standing item — body-detected exit-2 usage-error adapter is duplicated (already on the roadmap)

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_desloppify.py`
  (`DesloppifyUsageError` lines 69-90; `_scan_or_usage` 341-346) versus
  `novel_ralph_skill/commands/_gate_drafting_mutators.py`
  (`GateDraftingUsageError` lines 97-110; `_set_gate_or_usage` 201-206)

Both command modules define a domain `*UsageError(EnvelopeMessagesError)`
subclass and a thin `try: <body>; except <DomainUsageError>: return
CommandOutcome(code=ExitCode.USAGE_ERROR, messages=list(exc.messages) or
[str(exc)])` adapter. The exit-2 `CommandOutcome` construction is duplicated at
three sites. The cleaner shape is structural: the runner (`contract/runner.py`,
`run`, lines 223-239) already catches `StateInputError` (an `EnvelopeMessagesError`
subclass) and maps it to exit 3, but has *no* corresponding exit-2 catch arm for
body-raised usage errors, which is exactly why each command bolts on its own
adapter.

- **Proposed fix:** No new action required from this audit. This is already
  triaged as roadmap task `7.16.7`: lift a `BodyUsageError(EnvelopeMessagesError)`
  base and one `usage_error_outcome(exc)` helper into the `contract` layer so the
  exit-2 envelope has one tested home, with each command keeping a thin domain
  subclass for its docstring-level trigger. (A `run`-level catch arm — symmetric
  with the existing `StateInputError` arm — would be the most direct realization
  and is worth weighing against the helper-only approach when 7.16.7 is planned.)
  Recorded here for continuity.

## Summary

Task 1.2.14 is a clean documentation-only sweep with no production-code surface
of its own. The surrounding command package is well-factored at the leaf-helper
level and exhaustively tested, but it carries one **new** medium duplication —
the hand-copied load-edit-validate-write mutator skeleton across eight bodies
(Finding 1) — plus a low-severity precondition-refusal copy (Finding 2) and a
low-severity registration-import inconsistency (Finding 3). The two larger
structural duplications (Findings 4 and 5) are real but already triaged onto the
roadmap, so they are logged here only for continuity. No documentation or test
regressions were introduced by 1.2.14.
