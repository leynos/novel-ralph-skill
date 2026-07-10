# Post-merge audit — roadmap task 1.3.5

Audit of the codebase after roadmap task 1.3.5 ("Settle a deliberate mutator
success-result vocabulary") merged to `main` at commit `e057853`. The slice is
the remediation of `audit-2.2.2` Finding 2 (cqs, medium): it gives the
`set-cursor` and `advance-phase` *write* mutators their own write-shaped success
`result` instead of echoing the `check` *query*'s `{"violations": []}` read
shape. `set-cursor` now returns the cursor it set
(`{current_chapter, current_scene, current_beat}`), `advance-phase` returns the
transition (`{from, to}`), the change is documented in the harness design, the
developers' guide, and the users' guide, and a cross-subcommand test
([`test_novel_state_violations_ownership.py`](../../tests/test_novel_state_violations_ownership.py))
pins `violations` to `check` alone. The two mutator bodies live in
[`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
and are registered by
[`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py).

The slice is sound, well documented, and well covered. The new ownership guard,
the refreshed snapshots, and the unit assertions pin the write-shaped result
from several angles, and the documentation (harness design, developers' guide,
users' guide) is consistent and forward-looking — it instructs the later
`recount`/`reconcile` mutators to follow the same discipline. None of the
findings below is a blocking defect. The dominant theme is a small ergonomic and
duplication snag in the two-mutator skeleton, plus a clutch of carry-over items
from `audit-2.2.2` that this slice did not target and that remain open
(`_state_path` triplication and the `rulepack/parse.py` cap breach are not yet
on the roadmap).

Trail followed: explored with `leta`/reads over `commands/_state_mutators.py`,
`commands/novel_state.py`, `state/validate.py`, `contract/runner.py`,
`tests/test_novel_state_mutators.py`,
`tests/test_novel_state_mutator_snapshots.py`, and
`tests/test_novel_state_violations_ownership.py`; traced history with
`git show e057853` and `git log origin/main`, and confirmed roadmap triage of the
prior findings with `grep` over `docs/roadmap.md`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.1/§3.3/§4.1/§5.2, `docs/users-guide.md`,
`docs/developers-guide.md` "State mutators", `docs/adr-003-shared-interface-contract.md`,
prior `docs/issues/audit-2.2.2.md`, and `AGENTS.md`. Skills relied on:
`python-router` (routing the Python read), `leta` (navigation), and `sem`/`git`
(history). Each finding records a category, a location, a description, a concrete
proposed fix, and a severity.

## Finding 1 — `set-cursor` calls the typed-view query for its side effect and discards the result

- Category: cqs
- Severity: low
- Location:
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  line 203 (`_state_view_or_state_error(document)` with the return value
  discarded).

`_state_view_or_state_error` is a *query*: it derives and returns the typed
`State` read view (its return type is `State`). In `set_cursor` the first call
on line 203 is made purely for its raise-on-incomplete side effect — the
returned view is thrown away ("The view is discarded; the document remains the
write source"). The sibling `advance_phase` calls the *same* function on line
288 and binds the result to `prior`, which it then uses. So one mutator treats
the call as a structural-completeness *assertion* and the other as a *value
producer*, using one function in two roles. Calling a value-returning query and
discarding its result is the inverse of command/query separation and reads as a
latent smell: a future reader may "fix" the discard by wiring the unused view
into the edit, or may not realize the call is load-bearing (it must run before
the `document["drafting"]` scalar edits, or a missing `[drafting]` table would
raise `NonExistentKey` uncaught and exit `1`, breaching the exit-`3` contract).

Proposed fix: extract a void guard, e.g.
`_require_structurally_complete(document) -> None` that wraps
`_state_view_or_state_error` and exists solely to raise on an incomplete
document, and call it on line 203. Keep `_state_view_or_state_error` for the two
sites that actually consume the view (`set_cursor`'s `proposed`,
`advance_phase`'s `prior` and `proposed`). That names the two intents
distinctly — "prove complete" versus "derive view" — and stops a query being
invoked for its exception alone.

## Finding 2 — The two write mutators share an unfactored load → derive → edit → re-derive → refuse → write skeleton

- Category: duplication
- Severity: low
- Location:
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  `set_cursor` lines 197–219 and `advance_phase` lines 286–310.

Both mutators follow the same fixed skeleton: resolve `_state_path()`, load via
`_load_document_or_state_error`, derive the typed view, mutate the live
`tomlkit` document in place, re-derive the proposed view, gate it through
`_refuse_if_incoherent`, `write_document_atomically`, and return a
`CommandOutcome(code=SUCCESS, result=…, messages=[…])`. Only the in-place edit
and the result/message shapes differ. The shared head (path + load + complete
check) and the shared tail (re-derive + refuse + write + outcome) are
copy-aligned rather than factored, so a change to the validate-before-persist
ordering, the atomic-write call, or the load channel must be made twice and kept
in lock-step. The audit notes this is a deliberate trade in a two-mutator
module; it is flagged because two more mutators (`recount`, `reconcile`) are
slated to land in this same module (per the module docstring), at which point
four near-identical skeletons make the duplication material.

Proposed fix: when `recount`/`reconcile` land, factor the invariant skeleton —
e.g. a `_edit_state(path, *, edit: Callable[[TOMLDocument], None], context: str)
-> State` helper that loads, proves completeness, applies `edit`, re-derives,
refuses if incoherent, and writes, returning the proposed view for the caller to
shape its `result` from. Each mutator then supplies only its edit closure and
its outcome shape. Defer until the third mutator to avoid a premature one-caller
abstraction; record the intent now so the third mutator factors rather than
copies.

## Finding 3 — `working/state.toml` path is still constructed in three places (carry-over from audit-2.2.2 Finding 3, untriaged)

- Category: duplication
- Severity: low
- Location:
  [`commands/novel_state.py`](../../novel_ralph_skill/commands/novel_state.py)
  line 146 (`_check`) and line 192 (`_init`); the helper
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  lines 57–59 (`_state_path`).

`_state_mutators._state_path()` centralizes the fixed cwd-relative
`working/state.toml` path for the two write mutators, but `_check` re-derives it
inline as `pathlib.Path(WORKING_DIR_NAME) / "state.toml"` and `_init` builds it
as `working / "state.toml"`. Three independent constructions of one canonical
path persist after 1.3.5. This was raised as `audit-2.2.2` Finding 3 (low) but,
unlike that audit's Finding 1 (which became roadmap task 2.2.2.1) and Finding 2
(roadmap task 1.3.5, the slice just merged), it was **not** triaged onto
`docs/roadmap.md` (a `grep` for `_state_path`/`three places` over the roadmap
finds nothing). It is re-surfaced here so the carry-over is not silently lost.

Proposed fix: as `audit-2.2.2` proposed, define a single path accessor in
`novel_state.py` beside `WORKING_DIR_NAME` and have both `_check`/`_init` and the
`_state_mutators` module import it, retiring the three inline constructions. The
root agent may wish to add a roadmap item, or fold this into roadmap task 2.2.2.1
(the users'-guide addendum) as a paired tidy.

## Finding 4 — `rulepack/parse.py` still exceeds the 400-line file cap (carry-over from audit-2.2.2 Finding 5, untriaged)

- Category: complexity
- Severity: low
- Location:
  [`novel_ralph_skill/rulepack/parse.py`](../../novel_ralph_skill/rulepack/parse.py)
  (515 lines).

AGENTS.md "Keep file size manageable" caps a single code file at 400 lines;
`rulepack/parse.py` is 515. Task 1.3.5 did not touch this file, so this is a
standing overflow, not a regression. It was raised as `audit-2.2.2` Finding 5
(low) and, like Finding 3 above, was not triaged onto the roadmap. It is recorded
again so the cap breach is not normalized by repetition.

Proposed fix: split the scalar-coercion helpers (`_where`,
`_reject_unknown_keys`, `_require`, `_require_str`, `_require_int`, `_entries`)
into a sibling `rulepack/_coerce.py` leaf module, leaving `parse.py` holding the
rule-level resolvers and the public `parse_rulepack`/`load_rulepack` entry
points. The root agent may wish to add a roadmap item.

## Finding 5 — The `from`/`to` transition-label intent lives only in prose, with no behavioural assertion that the keys are *not* `state.toml` schema keys

- Category: docs-gap
- Severity: low
- Location:
  [`commands/_state_mutators.py`](../../novel_ralph_skill/commands/_state_mutators.py)
  lines 271–277 (`advance_phase` docstring) and
  [`docs/novel-ralph-harness-design.md`](../../docs/novel-ralph-harness-design.md)
  (the new "transition labels" paragraph).

The slice is careful, in three documents and the docstring, to warn that
`advance-phase`'s `from`/`to` are *transition labels*, not on-disk schema keys —
`state.toml` persists `phase.current` plus `phase.completed`, never a
`[from]`/`[to]` table. This is a real and useful distinction, but it is asserted
only in prose. The tests pin that the success `result == {"from": "premise",
"to": "treatment"}` and that `violations` is absent, but nothing pins the
*other half* of the documented claim: that the post-advance `state.toml` on disk
carries `phase.current == "treatment"` and appends `premise` to
`phase.completed`, and carries **no** `from`/`to` keys. A regression that wrote
the transition labels into the document (the exact confusion the prose guards
against) would leave the envelope assertions green.

Proposed fix: extend `test_advance_phase_success_envelope_snapshot` (or add a
focused unit test) to re-read the written `state.toml` and assert
`phase.current == "treatment"`, `"premise" in phase.completed`, and that the
parsed document has no top-level `from`/`to` key. That turns the documented
"transition labels are not schema keys" claim into an on-disk behavioural proof,
closing the gap between the prose and the test surface.

## Summary

The 1.3.5 slice cleanly resolves `audit-2.2.2` Finding 2: the two write mutators
now report what they changed, the `violations` read shape is owned by `check`
alone and pinned by a dedicated cross-subcommand guard, and the change is
documented consistently across the design, developers', and users' guides with
forward instructions for the later mutators. The fresh findings are minor: a
query invoked for its side effect in `set-cursor` (Finding 1) and the
two-mutator skeleton that will want factoring once `recount`/`reconcile` land
(Finding 2). The remaining findings are carry-overs from `audit-2.2.2` that
1.3.5 did not target and that remain open and (for Findings 3 and 4) untriaged:
the `working/state.toml` path triplication (Finding 3) and the
`rulepack/parse.py` cap breach (Finding 4). Finding 5 notes that the
`from`/`to` transition-label intent deserves an on-disk behavioural proof rather
than prose alone.
