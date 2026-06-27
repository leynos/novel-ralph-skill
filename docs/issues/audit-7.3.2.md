# Post-merge audit — roadmap task 7.3.2

Task 7.3.2 collapsed the five hand-copied mount lines in
`novel_ralph_skill/commands/novel.py`'s `build_multiplexer` onto a single
registry-driven construction table. A new module-level helper,
`_build_mount_table`, returns a bare-verb-keyed mapping of mount verb to each
leaf module's `build_app` factory; `build_multiplexer` now iterates the
registry-derived `_SUBCOMMAND_FOR_VERB` map and mounts `table[verb]()` for each
verb. The five deferred leaf imports moved inside the helper, preserving the
per-command import laziness the retired `stub.py` relied on. A new structural
test module, `tests/test_multiplexer_mount_table.py`, pins the table against the
registry (verb set, builder identity, registered-mount set) and pins the
import-laziness invariant by static source inspection.

This audit reviews the merged state at `origin/main` (commit `429be4b`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-separation (CQS) issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The refactor itself is disciplined and well-tested: the table-vs-registry
invariant, the builder-identity guard, and the import-laziness guard are all
pinned, and the behavioural parity proof in `tests/test_multiplexer_behaviour.py`
is untouched. The material findings concern a **documentation/code naming
mismatch** (the developers' guide names the wrong verb map as the mount driver),
a **fourfold duplication of the five-verb literal set** across the multiplexer
modules that the refactor's "no inline verb literals survive" framing was meant
to retire, a **near-duplicate registered-mounts test** now split across two test
modules, a **fragile substring-based laziness guard**, and an
**untested ordered-mapping claim**.

Documentation and skills relied on for this audit:
`docs/developers-guide.md` (the "`novel` multiplexer" section at lines 432-476),
`docs/adr-007-command-surface-novel-multiplexer.md`, the merged ExecPlan and its
three Logisphere reviews (`docs/execplans/roadmap-7-3-2.md`,
`roadmap-7-3-2.logisphere-review-r1..r3.md`), and `AGENTS.md` (quality gates,
400-line file cap, en-GB Oxford spelling). Code navigation used `leta`
(`show`, `refs`, `grep`); history was traced with `sem diff --from 791dfc7 --to
429be4b`. The `python-router` skill routed the typing/ergonomics observations.

## Finding 1 — the developers' guide names `_VERB_FOR_SUBCOMMAND` as the mount driver, but the code iterates `_SUBCOMMAND_FOR_VERB`

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `docs/developers-guide.md:451-453` ("`build_multiplexer` mounts
  each leaf in `SUBCOMMAND_NAMES` order (via the registry-derived
  `_VERB_FOR_SUBCOMMAND` map)") versus `novel_ralph_skill/commands/novel.py:129`
  (`for verb in _SUBCOMMAND_FOR_VERB:`).

The developers' guide attributes the mount loop's ordering to
`_VERB_FOR_SUBCOMMAND`, the map keyed by the *spaced* names (`"novel state"` →
`"state"`). The mount loop actually iterates `_SUBCOMMAND_FOR_VERB`, the reverse
map keyed by the *bare* verbs (`"state"` → `"novel state"`). The two maps are
both derived from `SUBCOMMAND_NAMES`, so the resulting order is the same and no
behaviour is wrong, but the named map in the prose is the wrong one: iterating
`_VERB_FOR_SUBCOMMAND` would yield the spaced names (`"novel state"`), which are
not the verbs the table is keyed by, so `table[verb]` would `KeyError`. A reader
who trusts the guide and reaches for `_VERB_FOR_SUBCOMMAND` is pointed at a map
that cannot drive the loop. `leta refs` confirms `_VERB_FOR_SUBCOMMAND` has no
consumer other than the comprehension that builds `_SUBCOMMAND_FOR_VERB`
(`novel.py:54`), so naming it as the mount driver is doubly misleading.

**Proposed fix:** correct the guide to name `_SUBCOMMAND_FOR_VERB` as the map the
mount loop iterates, or — better, since both maps trace back to one source —
describe the ordering as "in `SUBCOMMAND_NAMES`/ADR 007 surface order (the order
the registry-derived `_SUBCOMMAND_FOR_VERB` map preserves)" without over-committing
to a specific intermediate map. Sweep the same passage for the "via the
registry-derived" parenthetical so it points at the map the code actually reads.

## Finding 2 — the five-verb literal set is hand-spelled in four places the refactor's "no inline verb literals" framing was meant to retire

- **Category:** duplication
- **Severity:** medium
- **Location:** the bare-verb set `{state, done, compile, desloppify, wordcount}`
  appears as inline literals in `novel_ralph_skill/commands/novel.py:90-96` (the
  `_build_mount_table` return dict keys), `tests/test_multiplexer_mount_table.py:41-47`
  (`_VERB_MODULE_PAIRS`), `tests/test_multiplexer_behaviour.py:68-74`
  (`_OPERATIONS`), and `tests/test_multiplexer_dispatch.py:47`
  (`{"state", "done", "compile", "desloppify", "wordcount"}`).

The ExecPlan and the `build_multiplexer` docstring sell the refactor as removing
inline verb literals so "the names the dispatcher mounts cannot drift from the
names it stamps" (`novel.py:109-110`). The *loop verbs* now come from the
registry, which is the genuine win. But the verb set itself is still hand-typed
as literals in four collaborating locations. The mount-table key literals
(`novel.py:91-95`) are guarded against drift by
`test_mount_table_verbs_equal_the_registry_bare_verbs` (so a typo there fails a
test), and the test-side copies are partially load-bearing (they pair a verb with
its leaf module). However, `test_multiplexer_dispatch.py:47` is a *fourth*,
fully redundant copy of the bare-verb set that is not tied back to the registry
at all — adding a sixth verb to the surface requires editing four files, three of
them by hand-copying the same five strings.

**Proposed fix:** drive the dispatch test's expected set from the registry rather
than a literal: replace the literal in `test_multiplexer_dispatch.py:47` with
`set(novel._SUBCOMMAND_FOR_VERB)` (or fold this assertion into the mount-table
module, see Finding 3). For the `_VERB_MODULE_PAIRS`/`_OPERATIONS` test fixtures,
the verb strings are intrinsically paired with leaf modules and argv, so a full
de-duplication is not warranted; instead add a single guard that the verb keys of
those fixtures equal `set(novel._SUBCOMMAND_FOR_VERB)`, so a fixture that drifts
from the registry fails rather than silently testing a stale surface. The
mount-table return-dict keys are already guarded and may stay as literals.

## Finding 3 — two near-identical "registers exactly the verbs" tests now live in separate modules

- **Category:** similarity
- **Severity:** low
- **Location:** `tests/test_multiplexer_dispatch.py:37-47`
  (`test_build_multiplexer_registers_the_five_subcommands`) and
  `tests/test_multiplexer_mount_table.py:105-116`
  (`test_build_multiplexer_registers_exactly_the_table_verbs`).

Both tests build the multiplexer, filter the flag keys
(`name for name in app if not name.startswith("-")`), and assert the registered
mount names equal the five verbs. The only difference is the comparand: the
dispatch test compares against an inline literal set; the mount-table test
compares against `_build_mount_table()` keys (which the sibling test ties to the
registry). The two assertions are the same structural claim verified twice, with
the same filtering boilerplate copied verbatim. The mount-table version is
strictly stronger (it chains back to the registry), making the dispatch version
redundant.

**Proposed fix:** retire `test_build_multiplexer_registers_the_five_subcommands`
from `test_multiplexer_dispatch.py` (its concern now lives, more strongly, in
`test_multiplexer_mount_table.py`), or, if the dispatch module should keep a
smoke check of the registered surface, repoint its assertion at
`set(novel._build_mount_table())` so both tests share the single registry-tied
comparand and the duplicate literal of Finding 2 disappears with it. Update the
dispatch module's docstring (lines 4-9), which still claims it pins "exactly the
five sub-apps," if that assertion moves.

## Finding 4 — the import-laziness guard is a substring scan that will false-positive if any leaf name appears in prose outside the helper

- **Category:** test-gap
- **Severity:** low
- **Location:** `tests/test_multiplexer_mount_table.py:119-139`
  (`test_leaf_import_lives_inside_the_mount_table_helper`, the two arms
  `leaf_name in _build_mount_table_source()` and
  `leaf_name not in _novel_module_source_outside_mount_table()`).

The laziness guard removes `_build_mount_table`'s source slice from the module
source and asserts no leaf name (`_compile`, `_desloppify`, `_novel_done`,
`_wordcount`, `novel_state`) survives in the remainder. This is a raw substring
scan over text that includes the module docstring, `build_multiplexer`'s
docstring, and `main`'s docstring. Today those docstrings happen not to mention
any leaf module by name, so the guard passes — but the invariant it protects
(no module-scope leaf *import*) is narrower than the property it checks (no leaf
*string* anywhere outside the helper). A future docstring that legitimately
mentions, say, `novel_state` in prose would turn this test red even though no
import was hoisted, and conversely the scan cannot distinguish an import from a
comment. The guard is also coupled to `inspect.getsource(...).replace(...)`
string slicing, which breaks if the helper is decorated or reformatted.

**Proposed fix:** parse `novel.py` with `ast` and walk only module-scope
(`col_offset == 0`) `Import`/`ImportFrom` nodes, asserting no leaf module is
imported at module scope, and that each leaf *is* imported inside the
`_build_mount_table` `FunctionDef` body. An AST guard pins the actual invariant
(import location, not string presence), tolerates leaf names appearing in
docstrings, and survives reformatting. (See `python-quality-tools` and the
`ast`-based scanners already used in `tests/_state_layout_scanner.py` for the
in-repo pattern.)

## Finding 5 — `_build_mount_table` and its docstring promise an "ordered" mapping, but no test pins the mount order

- **Category:** test-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/novel.py:58-96` (the docstring twice
  calls the result an "ordered mapping ... in registry/surface order") and
  `tests/test_multiplexer_mount_table.py:78-116` (every assertion compares
  `set(...)`, discarding order).

The helper's docstring stresses that the table is ordered "in the ADR 007 surface
order" and the developers' guide repeats the surface-order claim, but all three
structural tests compare *sets*, so a table that returned the five entries in any
order — or a `build_multiplexer` that mounted them out of surface order — would
still pass. The surface order is observable (it determines `--help` listing
order), so the ordering claim is a real, currently-untested property. Note that
because the mount loop iterates `_SUBCOMMAND_FOR_VERB` (registry order), not the
table's own iteration order, the table's *internal* order is in fact irrelevant
to mounting — which makes the docstring's emphasis on the table being "ordered ...
in surface order" mildly over-stated as well.

**Proposed fix:** add one assertion that the *registered* mount order equals the
registry surface order — e.g.
`assert [n for n in novel.build_multiplexer() if not n.startswith("-")] ==
list(novel._SUBCOMMAND_FOR_VERB)` (a list, not a set). This pins the only
order that is behaviourally observable. Separately, soften the `_build_mount_table`
docstring to note that the loop, not the table, fixes the mount order (the table
is consulted by key), so the "ordered mapping" framing does not imply the table's
own order is load-bearing.

## Finding 6 — `_command_name_for` carries a ~30-line docstring over a two-line body, with the value-carrying-flag rationale duplicated against the test

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/novel.py:134-174`
  (`_command_name_for`: a 33-line docstring and an inline comment over a
  two-statement body) and `tests/test_multiplexer_dispatch.py:133-144`
  (`test_command_name_for_falls_back_on_unrecognised_tokens`, whose docstring
  re-states the same value-carrying-global-flag rationale).

The function body is two statements: find the first non-flag token, then
`_SUBCOMMAND_FOR_VERB.get(verb, MULTIPLEXER_NAME)`. The surrounding docstring
(lines 135-167) and the inline comment (171-173) spend roughly thirty lines on a
hypothetical future value-carrying global flag (`--config foo.toml`) and the
single-value-less-flag assumption. The same rationale is restated almost verbatim
in the dispatch test's docstring. The reasoning is valuable, but its weight is
disproportionate to the body and it is now maintained in two places that can
drift; the inline comment (171-173) also paraphrases the docstring it sits below.

**Proposed fix:** lift the value-carrying-global-flag assumption into a single
named anchor — either a short module-level note next to `parse_global_flags`'s
documentation, or a one-line `# See module note: value-less-global-flag
assumption` — and trim `_command_name_for`'s docstring to the contract (input,
output, fallback) plus a cross-reference, removing the duplicated inline comment.
Have the test docstring cite the same anchor rather than re-deriving the
rationale. This keeps the reasoning discoverable without maintaining three copies.
(See `python-router` → `python-types-and-apis` for docstring-to-signature
proportion guidance.)
