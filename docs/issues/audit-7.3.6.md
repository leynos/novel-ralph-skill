# Post-merge audit — roadmap task 7.3.6

Audit of the codebase after roadmap task 7.3.6 ("Relocate `WORKING_DIR_NAME`
and the command-name vocabulary into the `contract` package") merged to `main`
at commit `2d6525f`. The slice repairs the `contract` -> `commands` layering
inversion flagged in `audit:1.2.12` by moving two contract-level facts — the
command-name vocabulary (`MULTIPLEXER_NAME`, `SUBCOMMAND_NAMES`,
`ENVELOPE_COMMAND_NAMES`) and `WORKING_DIR_NAME` — out of the command layer and
into the new
[`novel_ralph_skill/contract/names.py`](../../novel_ralph_skill/contract/names.py).
It rewires [`contract/envelope.py`](../../novel_ralph_skill/contract/envelope.py)
to source both from `contract.names`, re-exports the vocabulary from
[`commands/names.py`](../../novel_ralph_skill/commands/names.py) and
`WORKING_DIR_NAME` from
[`commands/state_sourcing.py`](../../novel_ralph_skill/commands/state_sourcing.py)
for back-compatibility, widens the layering guard to police the whole
`contract` package, and adds
[`tests/test_contract_names_home.py`](../../tests/test_contract_names_home.py)
plus registry coverage. Behaviour, exit codes, and the absolute `working_dir`
stamp are unchanged.

The slice is sound and discharges its success criterion: the contract layer now
owns the two facts it validates against, the no-`contract`->`commands`-cycle
constraint is held by both a structural AST guard and a `same-object` re-export
test, and the relocation introduces no second copy. The new module's docstrings
are exemplary, and the back-compat re-exports keep every existing seam import
resolving. The findings below are tidy-ups; none is a blocking defect, and none
weakens the new home or its guards. The headline opportunity is that 7.3.6
re-anchored `WORKING_DIR_NAME` precisely so callers can route through the
`working_dir()` accessor, yet two leaf verbs still rebuild
`pathlib.Path(WORKING_DIR_NAME)` inline — the canonical "straggler off the
accessor" pattern this roadmap has repeatedly closed (cf. 7.2.4, 7.3.5).

This audit reviews the merged state at `origin/main` (commit `2d6525f`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a category, a location, a description, a concrete proposed fix, and a
severity. The trail: design §3.1, §3.2 and line 151, ADR 003 (shared interface
contract), ADR 007 (novel multiplexer surface),
[`docs/developers-guide.md`](../developers-guide.md),
[`docs/scripting-standards.md`](../scripting-standards.md), `AGENTS.md`, and the
execplan [`docs/execplans/roadmap-7-3-6.md`](../execplans/roadmap-7-3-6.md).
Navigation used `leta` and history used `sem`.

## Finding 1 — Two leaf verbs rebuild `pathlib.Path(WORKING_DIR_NAME)` inline instead of using the `working_dir()` accessor

- Category: duplication
- Severity: medium
- Location:
  [`novel_ralph_skill/commands/_desloppify.py`](../../novel_ralph_skill/commands/_desloppify.py)
  (line 202, `source_chapters`) and
  [`novel_ralph_skill/commands/_wordcount.py`](../../novel_ralph_skill/commands/_wordcount.py)
  (line 130, `_build_recount_inputs`).

`state_sourcing.working_dir()` exists specifically so commands "resolve the same
cwd-relative directory rather than each rebuilding `pathlib.Path(WORKING_DIR_NAME)`"
(its own docstring, Decision B4/B5). Every other command routes through it:
`_compile`, `_novel_done`, `novel_state`, and `_state_mutators` all import and
call `working_dir()`. But `_desloppify` and `_wordcount` instead import the raw
`WORKING_DIR_NAME` constant and rebuild `working_dir = pathlib.Path(WORKING_DIR_NAME)`
inline — exactly the line the accessor was created to delete. The same two sites
then write `load_or_state_error(working_dir / "state.toml")`, re-spelling the
`working/state.toml` path that the `state_path()` accessor already centralises
(audit:1.3.5, audit:2.2.2) and that `_compile`/`_novel_done`/`novel_state` all
route through as `load_or_state_error(state_path())`. 7.3.6 re-anchored
`WORKING_DIR_NAME` in the contract package, so these two stragglers are now the
*only* command-layer sites that reach for the bare constant rather than the
accessor pair.

Proposed fix: in both modules, replace the `WORKING_DIR_NAME` import with
`working_dir` (and add `state_path`), drop the inline
`working_dir = pathlib.Path(WORKING_DIR_NAME)` in favour of
`working_dir = working_dir()`, and load via `load_or_state_error(state_path())`.
This removes both raw-constant imports from the command layer, leaving
`WORKING_DIR_NAME` consumed only by the accessor that owns it (and the
`state_sourcing` re-export shim), and makes the "no command rebuilds the working
path inline" invariant hold uniformly. Behaviour is unchanged: `working_dir()`
returns `pathlib.Path(WORKING_DIR_NAME)` and `state_path()` returns
`working_dir() / "state.toml"`, so the resolved paths are identical.

## Finding 2 — `_recount_or_state_error` is near-duplicated across `_recount.py` and `_wordcount.py`

- Category: similarity
- Severity: medium
- Location:
  [`novel_ralph_skill/commands/_recount.py`](../../novel_ralph_skill/commands/_recount.py)
  (`_recount_or_state_error`, lines 55–93) and
  [`novel_ralph_skill/commands/_wordcount.py`](../../novel_ralph_skill/commands/_wordcount.py)
  (`_recount_or_state_error`, lines 61–101).

Both modules carry a private `_recount_or_state_error` whose load-bearing body is
the same "recount the drafts under the exit-3 read guard" seam:
`with draft_read_guard(working_dir): recount_words(working_dir, manifest)`. The
docstrings are near-identical, re-telling the same `recount_words` /
`draft_read_guard` / exit-3 reasoning (roadmap §7.3.3) twice. They differ only at
the edges: `_recount.py` resolves `working_dir` internally via the accessor and
returns `(total, by_chapter)`; `_wordcount.py` takes `working_dir` as a
parameter and returns only `by_chapter` (its caller derives the total via
`state.word_counts.target` rather than the recount sum). The guard itself was
already consolidated into `state_sourcing.draft_read_guard` by 7.3.3, so the
remaining duplication is the *recount-under-guard* shell that wraps it, not the
guard.

Proposed fix: hoist one shared `recount_under_guard(working_dir, manifest)` seam
into `state_sourcing` (beside `draft_read_guard`), returning the full
`(total, by_chapter)` tuple, and have both callers route through it —
`_recount.py` taking both values, `_wordcount.py` taking `by_chapter` and
discarding the total. This collapses the twice-told docstring onto one home,
keeps the per-caller `working_dir` resolution choice at the call site (resolve
vs. accept), and matches the 7.3.3 precedent of housing the read-guard plumbing
in `state_sourcing`. If the two return shapes are judged too divergent to share,
at minimum de-duplicate the docstring by having one reference the other rather
than restating the exit-3 reasoning verbatim.

## Finding 3 — The two loader error hierarchies differ only in the id keyword and noun

- Category: similarity
- Severity: medium
- Location:
  [`novel_ralph_skill/rulepack/errors.py`](../../novel_ralph_skill/rulepack/errors.py)
  (`RulePackError`, `RulePackFileError`) and
  [`novel_ralph_skill/ledger/errors.py`](../../novel_ralph_skill/ledger/errors.py)
  (`LedgerError`, `LedgerFileError`).

The two loader families carry parallel two-class error hierarchies that are
structurally identical. `RulePackError` and `LedgerError` differ only in the name
of the stored offending-id attribute (`rule_id` vs `device_id`) and the prose
nouns; their `__init__` signatures and bodies (`super().__init__(*messages)`;
`self.<id> = <id>`) are otherwise the same shape. `RulePackFileError` and
`LedgerFileError` are pure pass-through subclasses of `EnvelopeMessagesError`
adding nothing but a docstring, and both are already handled as interchangeable
parameters: each is passed as the `file_error=` factory to the shared
`loaderkit.load.load_toml`. This mirrors the coercion duplication that 7.2.2
already retired by lifting the scalar-coercion bodies into
`loaderkit.coerce` — the error hierarchies are the same near-copy one layer up,
not yet consolidated.

Proposed fix: add a `loaderkit.errors` home with a factory (or parametrised base)
that mints a content-error class carrying a configurable id-attribute name plus
a file-error class, mirroring how `loaderkit.coerce.CoercionErrors` parametrises
the
nouns and content-error constructor. Each package then declares its pair by
binding the id keyword (`rule_id`/`device_id`) and nouns, exactly as
`rulepack/_coerce.py` and `ledger/_coerce.py` already bind their one
`CoercionErrors` bundle. Preserve the public `rule_id`/`device_id` attribute
names so no call site or test changes. A third loader family then adds a binding,
not a third copy. If the per-package attribute name is judged to belong with the
package (so the class stays hand-written), record the deliberate parallelism in
both modules' docstrings the way `_coerce.py` already cross-references its twin.

## Finding 4 — `commands.names` re-export keeps `WORKING_DIR_NAME` and the vocabulary on two different shims

- Category: ergonomics
- Severity: low
- Location:
  [`novel_ralph_skill/commands/names.py`](../../novel_ralph_skill/commands/names.py)
  (re-exports the command-name vocabulary) and
  [`novel_ralph_skill/commands/state_sourcing.py`](../../novel_ralph_skill/commands/state_sourcing.py)
  (re-exports `WORKING_DIR_NAME`).

7.3.6 relocated two contract facts into `contract.names`, then re-exported them
from *two different* command-layer modules for back-compat: the command-name
vocabulary from `commands.names`, and `WORKING_DIR_NAME` from
`commands.state_sourcing`. This is internally consistent with where each was
*previously* owned, and the docstrings justify it, but it means a command-layer
reader looking for "the contract naming facts the command layer re-exposes" must
know to look in two places, and the split is historical rather than principled
(both are pure `contract.names` data). The `state_sourcing` re-export in
particular sits among substantive load-and-translate plumbing, so the one-line
back-compat constant is easy to miss.

Proposed fix: no behavioural change is warranted — the re-exports are correct and
the `same-object` tests pin them. The tidy-up is documentation: add a one-line
cross-reference in each shim's docstring naming the other (so a reader at either
shim learns the full set of `contract.names` facts the command layer re-exposes),
or note in the developers' guide's naming subsection that the vocabulary lands
back via `commands.names` while `WORKING_DIR_NAME` lands back via
`commands.state_sourcing`. This records the split as a deliberate
back-compat decision rather than an inconsistency a future tidy might "fix" by
collapsing the two shims.

## Finding 5 — `contract.names` carries WI2-conditional language now that WI2 has landed

- Category: docs-gap
- Severity: low
- Location:
  [`novel_ralph_skill/contract/names.py`](../../novel_ralph_skill/contract/names.py)
  (module docstring, line 6).

The module docstring still reads "and (once roadmap task 7.3.6 WI2 lands it) the
`working/` directory name the envelope stamps", framing `WORKING_DIR_NAME` as a
future arrival. WI2 *has* landed in this same merged commit — `WORKING_DIR_NAME`
is defined at line 60, re-exported from the contract package and from
`state_sourcing`, and pinned by `test_contract_names_home.py`. The conditional
clause now describes the merged state inaccurately, reading as if the constant is
still pending. This is a documentation-only staleness; the constant and its
guards are correct.

Proposed fix: drop the "(once roadmap task 7.3.6 WI2 lands it)" conditional and
state plainly that the module carries both the command-name vocabulary and
`WORKING_DIR_NAME`. A one-line docstring edit; no code change.

## Finding 6 — No structural guard pins the `WORKING_DIR_NAME` re-export the way the vocabulary re-export is guarded

- Category: test-gap
- Severity: low
- Location:
  [`tests/test_contract_names_home.py`](../../tests/test_contract_names_home.py)
  (`test_state_sourcing_reexports_contract_working_dir_name`) versus
  `test_contract_names_imports_no_commands_module`.

The new test module guards the *vocabulary* relocation with both an identity test
(`commands.names.X is contract_names.X`) and a structural AST guard
(`contract.names` imports no `commands` module at module scope, so no cycle can
form). The `WORKING_DIR_NAME` relocation gets the identity test
(`state_sourcing.WORKING_DIR_NAME is contract_names.WORKING_DIR_NAME`) but no
structural counterpart asserting the *direction* of the new
`state_sourcing -> contract.names` import — i.e. that `state_sourcing` reaches
*down* into `contract.names` and `contract.names` does not reach back up. The
existing no-commands AST guard already covers `contract.names` as a whole, so the
cycle is in fact prevented, but the `WORKING_DIR_NAME` arm has no test naming
that the constant's home moved *down* a layer (the value of the relocation),
where the vocabulary arm does.

Proposed fix: this is a low-value belt-and-braces gap given the whole-module AST
guard already holds the no-cycle invariant. If pinned at all, extend the existing
identity test with a one-line assertion that `WORKING_DIR_NAME` is *not* defined
at module scope in `state_sourcing` (e.g. via the same `ast`-walk helper the
module already imports), proving it is re-exported rather than redefined — the
direct structural analogue of the vocabulary guard. Otherwise, record in the test
module docstring that the whole-module no-commands guard subsumes the
`WORKING_DIR_NAME` direction so the asymmetry reads as intentional.

## Summary

Task 7.3.6 is a clean, well-guarded relocation: the `contract` package now owns
the two naming facts it validates against, the no-`contract`->`commands`-cycle
constraint is held by both an identity test and a static AST guard, and the
back-compat re-exports keep every existing seam import resolving with no second
copy. No finding blocks. The highest-value follow-up is Finding 1: repoint
`_desloppify` and `_wordcount` off the raw `WORKING_DIR_NAME` constant and onto
the `working_dir()`/`state_path()` accessors that 7.3.6's relocation exists to
feed, closing the last two command-layer stragglers and matching the
straggler-cleanup pattern this roadmap has applied repeatedly (7.2.4, 7.3.5).
Findings 2 and 3 are near-duplication that the established `loaderkit`/`state_sourcing`
consolidation seams are the natural home for. Findings 4–6 are documentation and
coverage tidy-ups that record the slice's deliberate back-compat splits and close
the small asymmetry between the vocabulary and `WORKING_DIR_NAME` guards.
