# Post-merge audit — roadmap task 7.3.1

Task 7.3.1 lifted the shared state-sourcing seam — *where* a command looks
(`WORKING_DIR_NAME`, `working_dir`, `resolved_working_dir`, `state_path`),
*what counts* as a state-input fault (`STATE_INPUT_ERRORS`), and *how* a failed
load becomes the contract's exit-`3` error (`_state_input_error`, the four
file-fault formatters, and the promoted public `load_or_state_error`) — out of
`novel_ralph_skill/commands/novel_state.py` into a new neutral, dependency-free
`novel_ralph_skill/commands/state_sourcing.py`. Every command now imports the
seam directly from `state_sourcing` rather than through the `novel_state`
command facade, so a future `novel state` refactor cannot silently break the
other commands. The module imports only from `novel_ralph_skill.state` and
`novel_ralph_skill.contract.runner`, never from `novel_state`, to avoid the
import cycle the `_state_mutators` carve-out already navigates.

This audit reviews the merged state at `origin/main` (commit `51b3b7d`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The migration itself is clean and disciplined: no module still references the
old `_state_load`, the developers' guide is updated to name the new home and its
formatters, and a dedicated structural test (`test_state_sourcing_home.py`) pins
both the public-seam export and the no-`novel_state`-dependency invariant. The
material findings concern an **API-privacy inconsistency** between the seam's
declared `__all__`/docstring and its actual cross-module callers, a
**re-export hop** through `_state_mutators` that partially undermines the
canonical-home goal, and structural duplication between the two state loaders.

Documentation and skills relied on for this audit:
`docs/developers-guide.md` (the "exit-3 messages are actionable" passage at
lines 619-666, and the `state_sourcing` seam summary at lines 656-666),
`docs/novel-ralph-harness-design.md` (§7.3.1), the merged ExecPlan reviews
`docs/execplans/roadmap-7-3-1.logisphere-review-r1..r4.md`, `docs/adr-003`
(shared interface contract), and `AGENTS.md` (quality gates, 400-line file cap,
en-GB Oxford spelling). Code navigation used `leta`; history was traced with
`sem diff --commit 51b3b7d` and `git show`.

## Finding 1 — six underscore-private formatters are imported across six sibling modules yet declared "module-private"

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/state_sourcing.py:38-50` (`__all__`
  and the docstring comment "the underscore-private actionable-message
  formatters move with the module but stay module-private") and lines 1-22
  (module docstring: the seam lives "in exactly one place"); cross-module
  importers at `_desloppify_ledger.py:35` (`_device_ledger_read_error`),
  `_novel_done.py:39`, `_recount.py:22`, `_wordcount.py:42`, `_compile.py:46`
  (`_compile_write_error`, `_draft_read_error`), and `_desloppify.py:46`
  (`_draft_read_error`, `_rule_pack_read_error`).

The module docstring and the `__all__` comment both assert the actionable-message
formatters are "module-private," and the seam test (`test_state_sourcing_home.py`
lines 25-36) records the same claim. In fact `_state_input_error`,
`_draft_read_error`, `_compile_write_error`, `_rule_pack_read_error`, and
`_device_ledger_read_error` are imported by six sibling command modules. Under
PEP 8 a leading underscore signals a module-private name not meant for import by
other modules; the developers' guide (lines 619-647) simultaneously documents
these same names as the developer-facing contract for the exit-3 message
surface. The code, the docstring, and the prose disagree on whether these are
private implementation or public seam.

**Proposed fix:** treat the formatters as what they are — part of the public
state-sourcing seam — and rename them without the leading underscore
(`state_input_error`, `draft_read_error`, `compile_write_error`,
`rule_pack_read_error`, `device_ledger_read_error`), adding them to `__all__`
and updating the docstring, the developers' guide `:func:` roles, and the seam
test's `_PUBLIC_SEAM`/`_SEAM_SYMBOLS`. Keep only genuinely internal helpers
(`_file_fault_error`, `INSPECT_REPAIR_REMEDY`) underscore-prefixed. Alternatively,
if the design intends them to stay private, re-route the six consumers through a
public dispatcher (a single `file_fault_error(kind, path)` factory) so the
underscore claim becomes true. The rename is the lower-risk option because the
prose already documents them as a stable contract.

## Finding 2 — `_recount` and `_reconcile` reach the seam accessors via a re-export hop through `_state_mutators`, not the canonical home

- **Category:** separation-of-concerns
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_state_mutators.py:39-44` (imports
  `state_path`/`working_dir` from `state_sourcing`, aliases them to
  `_state_path`/`_working_dir`) and lines 64-76 (re-exports them via `__all__`
  so `_recount`/`_reconcile` import them from here); consumers at
  `_recount.py:22-27` and `_reconcile.py:51-56`
  (`from novel_ralph_skill.commands._state_mutators import _state_path,
  _working_dir, _load_document_or_state_error`).

The stated goal of 7.3.1 (developers' guide lines 661-664) is that "every command
imports the seam directly from `state_sourcing` rather than through the
`novel_state` command facade." Two mutator modules instead import the
`working_dir`/`state_path` accessors *via* `_state_mutators`, which re-exports
them from `state_sourcing` purely to satisfy those importers (the `__all__`
comment at lines 64-67 confirms the re-export exists only to silence the
unused-import lint). This swaps the old `novel_state` facade for a new
`_state_mutators` facade: the accessors still reach two consumers through an
intermediary command module, so the "single canonical home" property the task
sells is only partially realised.

**Proposed fix:** repoint `_recount` and `_reconcile` to import `state_path`
and `working_dir` directly from `state_sourcing` (the document loader
`_load_document_or_state_error` legitimately lives in `_state_mutators` and may
stay), then drop the `_state_path`/`_working_dir` aliases and their `__all__`
re-export entries from `_state_mutators`. This removes a hop and makes the
canonical-home invariant uniform across all consumers.

## Finding 3 — the no-`novel_state`-facade test does not guard against the `_state_mutators` re-export hop

- **Category:** test-gap
- **Severity:** medium
- **Location:** `tests/test_state_sourcing_home.py:73-128`
  (`_seam_imports_from_novel_state` and
  `test_no_command_imports_the_seam_from_novel_state` only inspect imports whose
  `node.module == "novel_ralph_skill.commands.novel_state"`).

The structural test forbids re-pinning the seam onto the *old* `novel_state`
facade, but it walks only `ImportFrom` nodes whose module is `novel_state`. It
is therefore blind to Finding 2: `_recount`/`_reconcile` importing the
`working_dir`/`state_path` seam symbols from `_state_mutators` passes the test
even though it is the same class of indirection the test exists to prevent. The
invariant the test claims to protect ("the seam has a single home") is wider
than the property it actually checks.

**Proposed fix:** generalise the guard to assert that the migrated *accessor*
seam symbols (`working_dir`, `state_path`, `resolved_working_dir`,
`STATE_INPUT_ERRORS`, `WORKING_DIR_NAME`, `load_or_state_error`) are imported
only from `state_sourcing` by any command module — i.e. flag an `ImportFrom`
that pulls a seam symbol from *any* command module other than `state_sourcing`.
Land this together with Finding 2 so the test passes on the corrected imports.

## Finding 4 — `load_or_state_error` and `_load_document_or_state_error` are structural twins differing only in the loader called

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/state_sourcing.py:379-382`
  (`try: return load_state(path) except STATE_INPUT_ERRORS as exc: raise
  _state_input_error(path, exc) from exc`) and
  `novel_ralph_skill/commands/_state_mutators.py:111-113` (identical body with
  `load_document` in place of `load_state`).

The read-only loader and the document loader share an identical
load-and-translate body; only the wrapped loader (`load_state` → `State` vs
`load_document` → `TOMLDocument`) differs. The two are deliberately kept in
parity (both route through `_state_input_error`), but the parity is currently
enforced by hand rather than structurally, so a future edit to one
`except`/`raise … from` arm could silently drift the other.

**Proposed fix:** extract a private generic helper in `state_sourcing`, e.g.
`_load_or_state_error[T](loader: Callable[[Path], T], path: Path) -> T` that
owns the `try/except STATE_INPUT_ERRORS/raise _state_input_error(...) from exc`
arm, and have both `load_or_state_error` and `_load_document_or_state_error`
delegate to it (the document loader keeps living in `_state_mutators` but calls
the shared arm). This makes the parity structural. Weigh against the cost of a
`ParamSpec`/`TypeVar` signature; if the team prefers explicitness over the
generic, leave a cross-reference comment on each body instead and downgrade to a
documentation note. (See `python-types-and-apis` for the generic-callable
signature.)

## Finding 5 — `_file_fault_error` is a one-line constructor wrapper whose indirection may not earn its keep

- **Category:** complexity
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/state_sourcing.py:164-188`
  (`_file_fault_error` wraps a single `return StateInputError(message)`),
  called by `_draft_read_error` (235), `_compile_write_error` (274),
  `_rule_pack_read_error` (314), and `_device_ledger_read_error` (350).

`_file_fault_error` exists to deduplicate the `return StateInputError(message)`
tail across four formatters that each build their own prose. The deduplicated
body is a single constructor call, so the wrapper adds a layer of indirection
and a 25-line docstring to save four characters of typing per call site; it does
not centralise any behaviour the four formatters could otherwise diverge on
(they already build the message themselves). The abstraction is documented as an
intentional `audit:6.3.8` dedup, so this is a judgement call rather than a
defect.

**Proposed fix:** inline `return StateInputError(message)` at the four call
sites and delete `_file_fault_error`, or — if a shared seam is genuinely
wanted — give it a reason to exist by having it own the common file-fault *message
scaffold* (the "cannot {verb} {artefact}; {remedy}" shape) rather than only the
constructor call, so the four formatters supply just verb/artefact/remedy. If
neither change is desired, keep as-is; the cost is small. (See
`python-errors-and-logging` for error-construction ergonomics.)

## Finding 6 — `state_sourcing.py` carries a high docstring-to-code ratio that risks drift under future edits

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/state_sourcing.py` (382 lines, of
  which roughly 250 are module/function docstrings citing specific design-line
  and Decision-Log anchors, e.g. "design line 151", "Decision Log B4/B5",
  "audit:1.3.5", "Addendum 6.3.5.1").

The module is meticulously documented, which is a strength, but several
docstrings hard-code positional references ("design line 151",
`state_sourcing.py:52-67`, "ledger/parse.py:311", "rulepack/parse.py:390") that
will silently rot when those files shift. There is no gate that these line
anchors still resolve, so the documentation can drift from the code it cites
without any test failing.

**Proposed fix:** prefer symbolic anchors over line numbers in docstrings —
cite the function/section name (`:func:`/`:mod:` roles or a named heading)
rather than `file.py:NNN`. Where a line citation is unavoidable, consider a
lightweight docs-link checker in the test suite (or a `markdownlint`/custom
gate) that resolves `:func:` roles and flags dangling `file.py:NN` anchors. At
minimum, sweep the existing `parse.py:NNN` citations to symbolic form during the
next touch of those modules.
