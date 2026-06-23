# Post-merge audit — roadmap task 7.3.3

Audit of the codebase after roadmap task 7.3.3 ("Extend the direct-edit guard
to every skill-recipe reference") merged to `main` at commit `b28eaad`. The
slice widens the `state.toml` direct-write guard from `state-layout.md` alone to
every skill markdown file under `skill/novel-ralph/`. It adds a multi-file
driver
([`find_direct_state_write_recipes_in_files`](../../tests/_state_layout_scanner.py))
that applies the single-file detector per document, promotes the planted
hand-edit corpus to a shared
[`tests/_planted_recipes.py`](../../tests/_planted_recipes.py) support module,
and rewires
[`tests/test_state_layout_reference.py`](../../tests/test_state_layout_reference.py)
to scan a glob-discovered file set with a hard-coded inventory tripwire. The
developers' guide gains a "multi-file guard" subsection.

The slice is sound and discharges its success criterion: every executable-
carrying skill reference is now scanned by one shared detector with no per-file
duplication, the discovery is glob-driven so a new reference needs no guard
edit, and a tripwire forces a human to confirm the glob caught any added file.
The detector reuse is exemplary — the multi-file driver invents no second
matcher and a test pins that invariant. The findings below are coverage,
ergonomics, and consistency tidy-ups; none is a blocking defect, and none
weakens the guard.

This audit checks the new surface against the design's authoritative artefacts
and the recurring themes carried by the prior audits
(`docs/issues/audit-1.2.1.md` through `docs/issues/audit-5.1.1.md`). Each
finding records a category, a location, a description, a concrete proposed fix,
and a severity.

Trail followed: created a `git-donkey` worktree off `origin/main` and explored
with `leta`/`Read` over `tests/_state_layout_scanner.py`,
`tests/_planted_recipes.py`, `tests/test_state_layout_reference.py`,
`tests/conftest.py`, `novel_ralph_skill/state/validate.py`, and
`novel_ralph_skill/contract/runner.py`; traced history with `sem`/`git show
b28eaad` and `git log origin/main`. Source of truth consulted:
`docs/novel-ralph-harness-design.md` §3.4, §4.1, §5.3, and §5.4;
[`docs/adr-002-toml-round-trip-tomlkit.md`](../adr-002-toml-round-trip-tomlkit.md);
`docs/developers-guide.md` ("The state-layout direct-edit guard");
`docs/scripting-standards.md`; and `AGENTS.md`. Language router: `python-router`
(pure functions over text, data shapes, testing). Spelling per `en-gb-oxendict`.

## Finding 1 — Six executable fence labels are never exercised in the flagged direction

- **Category:** test-gap
- **Severity:** medium
- **Location:**
  [`tests/_planted_recipes.py:34-81`](../../tests/_planted_recipes.py)
  (`PLANTED_RECIPES`) against the declared executable set in
  [`tests/_state_layout_scanner.py:27-39`](../../tests/_state_layout_scanner.py)
  (`_PYTHON_INFO_STRINGS`, `_EXECUTABLE_INFO_STRINGS`)

The scanner treats nine info strings as executable: `python`, `python3`, `py`,
`py3`, `pycon` (the Python set), plus `sh`, `bash`, `shell`, and `console`. The
planted corpus, however, only ever uses three of them as a *flagged* fence:
`python` (8 rows), `python3` (1 row), and `sh` (8 rows). The labels `py`, `py3`,
`pycon`, `bash`, `shell`, and `console` are never planted as a positive case, so
the suite never proves that:

- a `bash`/`shell`/`console` redirect or heredoc to `state.toml` is flagged
  (the shell-redirect rule is exercised only through `sh`); and
- a `py`/`py3`/`pycon` fence carrying the bare `.write(` backstop, or any other
  Python write primitive, is flagged (the `_PYTHON_INFO_STRINGS`-gated backstop
  at line 176 is exercised only through `python`/`python3`).

Membership of these labels in the executable set is asserted only implicitly —
nothing fails if a future edit drops `bash` or `console` from
`_EXECUTABLE_INFO_STRINGS`, because no test plants a recipe in one of those
fences. The clean-direction cases do cover `pycon` (the read-only REPL
transcript) and `toml`/non-executable fences, but the *flagged* direction for
the six labels above is a hole, which is precisely where a guard regression
would let a hand-edit recipe through.

**Proposed fix:** add a small parametrized positive case (or extend
`PLANTED_RECIPES`) covering one flagged recipe per under-exercised label: a
`bash`, a `shell`, and a `console` shell-redirect to `working/state.toml`, and a
`py`, a `py3`, and a `pycon` fence carrying a write primitive (the `.write(`
backstop for `py`/`py3`; a write-mode `open(` for `pycon`). This pins every
member of the executable set to its detection path so dropping a label from the
frozenset fails a test. Gated by `pytest`.

## Finding 2 — `_iter_executable_fences` is named as an iterator but eagerly returns a `list`

- **Category:** ergonomics
- **Severity:** low
- **Location:**
  [`tests/_state_layout_scanner.py:134-151`](../../tests/_state_layout_scanner.py)
  (`_iter_executable_fences`)

The helper is named with the `_iter_` prefix — the Python convention for a lazy
generator — but its body builds and returns a concrete
`list[tuple[str, str]]`. Its sole caller,
`find_direct_state_write_recipes`, iterates the result once in a `for` loop, so
a generator would serve identically and the eager list buys nothing. The name
and the return type disagree: a reader reaching for `_iter_executable_fences`
expects a lazy stream (and might, for example, call `next(...)` on it), but
receives a materialised list. This is the inverse of the `python-router`
iterators guidance, which reserves the `iter`/`yield` vocabulary for genuinely
lazy producers.

**Proposed fix:** pick one and make the name and shape agree. Either (a) convert
the body to a generator (`yield (label, body)` inside the loop, drop the
`fences` accumulator, and annotate the return as
`cabc.Iterator[tuple[str, str]]`), keeping the `_iter_` name honest; or (b)
rename to `_executable_fences` and keep the eager list, if a re-scan of the same
fences is ever wanted. Option (a) is the smaller change and matches the
single-pass caller. Purely internal; the detector's behaviour is unchanged.
Gated by Ruff, `ty`, and `pytest`.

## Finding 3 — The multi-file driver is a hand-written loop where a dict comprehension reads more directly

- **Category:** complexity
- **Severity:** low
- **Location:**
  [`tests/_state_layout_scanner.py:201-219`](../../tests/_state_layout_scanner.py)
  (`find_direct_state_write_recipes_in_files`)

The driver accumulates findings with an explicit `findings: dict = {}`, a `for`
loop, a `messages = ...` call, an `if messages:` guard, and an assignment. The
whole body expresses "map each document to its non-empty message list, dropping
the clean ones", which a single dict comprehension states directly:

```python
return {
    label: messages
    for label, markdown in documents.items()
    if (messages := find_direct_state_write_recipes(markdown))
}
```

The walrus keeps the detector called exactly once per document (preserving the
no-second-matcher invariant the docstring and
`test_recipe_in_one_document_keyed_by_label` pin) while removing the mutable
accumulator and the imperative guard. The current form is correct, merely more
verbose than the data transformation it performs.

**Proposed fix:** replace the loop body with the walrus dict comprehension
above, keeping the docstring's "calls the detector once per document, adds no
second matcher" note. The four existing `TestFindDirectStateWriteRecipesInFiles`
tests already pin the behaviour, so the change is purely a readability tidy-up.
Gated by Ruff and `pytest`.

## Finding 4 — The skill-markdown inventory is duplicated between the tripwire constant and the discovery fixture

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_reference.py:55-64`](../../tests/test_state_layout_reference.py)
  (`_KNOWN_SKILL_MARKDOWN`) and the
  [`skill_markdown_documents`](../../tests/test_state_layout_reference.py)
  fixture (lines 67-86), cross-checked by `test_discovery_covers_known_skill_files`

The eight-name `_KNOWN_SKILL_MARKDOWN` frozenset restates, by hand, the file set
that `skill_markdown_documents` discovers by globbing
`skill/novel-ralph/**/*.md`. This duplication is *deliberate* — the developers'
guide and the test docstring both explain it as an intentional tripwire so a
contributor who adds or removes a reference is forced to update the reviewed
inventory. That rationale is sound and the design should stay. The audit-worthy
gap is that the *justification* lives only in the test docstring and the
developers' guide prose, while the constant itself carries only a terse comment;
a future reader simplifying the suite could mistake the hard-coded list for
accidental duplication and "fix" it by deriving it from the glob, silently
removing the tripwire. The risk is that the intent is documented adjacent to,
but not on, the line a refactor would touch.

**Proposed fix:** keep the duplication, but strengthen the in-code signal so the
tripwire cannot be optimised away: add a short comment directly above
`_KNOWN_SKILL_MARKDOWN` stating "Intentionally hand-maintained — do NOT derive
from the glob; this is a tripwire (see test_discovery_covers_known_skill_files
and developers-guide 'The state-layout direct-edit guard')." The constant
already has a comment explaining what it is; this makes the "and why you must not
collapse it" explicit at the edit site. No behaviour change. Gated by Ruff and
`pytest`.

## Finding 5 — The `console` fence carries no `.write(` backstop, a documented-but-unflagged Python-in-shell gap

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`tests/_state_layout_scanner.py:154-178`](../../tests/_state_layout_scanner.py)
  (`_write_token`), and the executable-set comment at lines 30-39

`console` is in `_EXECUTABLE_INFO_STRINGS` (so its shell redirects and library
writers are scanned) but not in `_PYTHON_INFO_STRINGS`, so the bare `.write(`
backstop at line 176 never fires for a `console` fence. The module comment
justifies this for the Python-flavoured set ("the bare `.write(` backstop only
makes sense for Python fences, where `.write(` is a method call rather than a
shell token"). The reasoning holds for a pure shell `console` transcript.
However, a `console` info string is also commonly used for *mixed* sessions that
embed a `python -c '...write(...)'` one-liner, and the design treats `console`
as executable precisely because a reader could copy-run it. A `console`
transcript that mutates `state.toml` via a `python -c` write that uses neither a
known library writer, an `open(`-with-mode, nor a redirect — only a bare
`.write(` — would slip the guard. This is a narrow edge, and the design
acknowledges fence-extension hardening is roadmap 7.3.4's job, but it is an
unflagged gap the current comment does not name.

**Proposed fix:** record the gap explicitly rather than leaving it implicit.
Either (a) add `console` to the set of labels eligible for the `.write(`
backstop (accepting a marginally higher false-positive risk on a shell line
containing a literal `.write(`), or (b) leave the behaviour as-is but extend the
module comment at lines 30-39 to state that a `console` fence's bare-`.write(`
Python one-liner is a known, accepted gap deferred to roadmap 7.3.4, so a future
reader does not assume `console` is fully covered. Option (b) is the smaller,
honest change pending 7.3.4. Gated by Ruff and `pytest`.

## Finding 6 — The `.markdown`/`.mdx` extension gap is documented but unguarded by any test

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`docs/developers-guide.md:397-405`](../developers-guide.md) ("The `.md`
  extension is a **gate assumption**") against the
  [`skill_markdown_documents`](../../tests/test_state_layout_reference.py)
  fixture glob (lines 67-86)

The developers' guide is admirably candid that the `**/*.md` discovery glob is a
gate assumption: a reference added as `.markdown` or `.mdx` "would slip past the
guard silently", flagged as a review smell until roadmap 7.3.4. But no test
encodes that assumption, so the documented risk has no executable tripwire. The
companion `test_discovery_covers_known_skill_files` catches an added `.md` file,
but a `.markdown` file is invisible to *both* the glob and the inventory check —
it simply does not appear in the discovered set, so the tripwire passes while the
guard silently skips the new file. The one safety the prose promises ("a human
must inspect the new file") does not hold for a non-`.md` extension.

**Proposed fix:** add a narrow tripwire that fails if any non-`.md` markdown-like
file appears under `skill/novel-ralph/` — for example, glob
`skill/novel-ralph/**/*` for files whose suffix is in `{".markdown", ".mdx",
".mkd"}` and assert the set is empty, with a message pointing at roadmap 7.3.4
and the gate-assumption prose. This converts the documented smell into a failing
test the moment a non-`.md` reference lands, closing the silent-skip window
without waiting for the full 7.3.4 property hardening. Gated by `pytest`.

## Finding 7 — Two near-identical "temp-file is not flagged" tests differ only by language, inviting a parametrize

- **Category:** similarity
- **Severity:** low
- **Location:**
  [`tests/test_state_layout_reference.py:162-198`](../../tests/test_state_layout_reference.py)
  (`test_python_write_to_new_temp_not_flagged` and
  `test_shell_redirect_to_new_temp_not_flagged`)

The two atomic-write-temp cases assert the same proposition — a write to the
`state.toml.new` temporary is clean because the live-file gate is filename-
boundary-anchored — once for a Python `write_text` fence and once for a shell
redirect fence. Their bodies are structurally identical: build a fence string
naming `state.toml.new`, assert `not find_direct_state_write_recipes(fence)`.
The same shape recurs in the clean unrelated-redirect trio
(`test_unrelated_redirect_not_flagged`,
`test_unrelated_no_space_redirect_not_flagged`,
`test_indented_unrelated_redirect_not_flagged`). Each is independently readable,
but the repeated "assert this fence is clean" skeleton is a candidate for a
single parametrized clean-case table, which would also make it obvious at a
glance which clean shapes are covered and surface any gap (Finding 1's missing
labels among them).

**Proposed fix:** consider folding the clean-case asserts into one
`@pytest.mark.parametrize` table of `(id, fence)` rows feeding a single
`test_clean_fence_not_flagged`, keeping the distinct docstring rationale as the
parametrize `ids`. This is a judgement call — the current one-test-per-rationale
form documents *why* each shape is clean, which a table flattens — so weigh
readability against the de-duplication before applying. Lower priority than the
coverage findings. Gated by `pytest`.
