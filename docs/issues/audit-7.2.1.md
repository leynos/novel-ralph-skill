# Post-merge audit — roadmap task 7.2.1

Audit of the codebase after task 7.2.1 ("Collapse the duplicated `tomlkit`
inline-table builders onto one shared helper") merged to `main` at commit
`86d6bce`. The task introduced `build_inline_table`
(`novel_ralph_skill/state/document.py`), re-exported it from
`novel_ralph_skill.state`, and routed five former hand-copied inline-table
builders onto it: `init` (`state/initial.py`), `recount`
(`commands/_recount.py`), `reconcile` (`commands/_reconcile.py`),
`set-chapters`'s two sites (`commands/_set_chapters.py`), and the working-corpus
reference builder (`tests/working_corpus/_builder.py`).

The merged change is clean and well-pinned: the helper is a pure query (it builds
structure and returns it, touching no state), it preserves the caller's iteration
order (the load-bearing property for `recount`'s byte-for-byte determinism), and
it carries both an example suite and a Hypothesis property
(`tests/test_build_inline_table.py`). The developers' guide names the helper as
the single home of the idiom and lists its five consumers. No correctness defect
was found in the 7.2.1 blast radius.

The findings below are maintainability and consistency opportunities surfaced
while auditing the change and its neighbours. The two duplication candidates with
the widest blast radius — the `_coerce`/scan near-copies across the `ledger` and
`rulepack` packages, and the array-of-inline-tables skeleton — are already partly
tracked: 7.2.2 owns the former. The array-of-inline-tables skeleton is recorded
here as the one genuine untracked gap.

The exploration used `leta` for code navigation (`leta show`, `leta refs`,
`leta grep`, `leta calls`) and `sem`/`git show` for history tracing. The sources
of truth consulted were `docs/novel-ralph-harness-design.md` (§5.3 inline-table
materialisation), `docs/adr-002-toml-round-trip-tomlkit.md`, `docs/roadmap.md`
(steps 7.2 and 7.3), `docs/developers-guide.md`, `AGENTS.md`, and the existing
audit issues under `docs/issues/`. Prose follows the en-GB Oxford spelling
convention (`AGENTS.md`).

## Finding 1 — Untracked array-of-inline-tables skeleton duplication

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_set_chapters.py:151-170`
  (`_chapter_array`) and `tests/working_corpus/_builder.py:108-132`
  (`_chapters_array`)

Task 7.2.1 folded the *inner* inline-table idiom into `build_inline_table`, but
the *outer* skeleton that wraps it remains duplicated. Both `_chapter_array` and
`_chapters_array` open with the identical three-line pattern —
`tomlkit.array()`, `array.multiline(multiline=True)`, then a loop that appends
`build_inline_table({…})` — and both materialise the same four-key
`[[chapters]]` entry (`number`, `slug`, `title`, `target_words`) in the same
on-disk schema order. The only divergence is how each derives the ordered
chapter sequence: `_set_chapters` receives an already-ordered
`Sequence[ChapterPlanEntry]`, while the corpus builder computes the ordered
number set from a `WorkingTreeSpec` and fills gaps with synthesised slugs and
titles.

The 7.2.1 developers'-guide note (line 1276) explicitly names this skeleton as
"a separate, wider idiom left as a deferred follow-up, not folded in here", and
the round-1 Logisphere review on the task flagged the same pair. But — unlike the
`_coerce` duplication, which roadmap task 7.2.2 owns — no roadmap task currently
captures this follow-up. The deferral therefore dangles: the developers' guide
records the debt but points at no work item, so the next renumber or a future
sixth `[[chapters]]` writer can re-fork the skeleton with nothing to catch it.

This is the same class of debt 7.2.1 itself was created to retire (a hand-copied
`tomlkit` builder idiom with no single home), one level up.

- **Proposed fix:** Add a 7.2.x roadmap task (sibling to 7.2.1, in the same
  "Single-source the loaders, builders, and scan primitives" step) to extract a
  shared `build_chapter_array` (or similarly named) helper into the `state`
  package that takes an ordered sequence of `(number, slug, title,
  target_words)` records and returns the multiline `[[chapters]]` array, routing
  both `_chapter_array` and `_chapters_array` through it and pinning it with a
  test, exactly as 7.2.1 did for `build_inline_table`. Until the task lands,
  replace the bare "deferred follow-up" phrasing in `developers-guide.md` with a
  reference to that task ID so the deferral is traceable. Proposing the roadmap
  item is reserved to the root agent; this audit only records the gap.

## Finding 2 — `_coerce` near-copy: confirm 7.2.2 scope still matches

- **Category:** duplication
- **Severity:** low (tracking confirmation, not new work)
- **Location:** `novel_ralph_skill/ledger/_coerce.py` and
  `novel_ralph_skill/rulepack/_coerce.py`

For completeness within the 7.2.1 blast radius (both packages are `tomlkit`
loaders neighbouring the inline-table work), the two `_coerce` modules remain
near-verbatim copies: identically-named `_where`, `_reject_unknown_keys`,
`_require`, `_require_str`, and `_require_int`, with bodies differing only in the
raised error type (`LedgerError` vs `RulePackError`), the identifier kwarg
(`device_id` vs `rule_id`), and the noun in prose. The ledger module's own
docstring labels itself "a deliberate near-copy" and explains the constraint
that produced it (the command routes on the typed error, and the rule-pack path
was a frozen-byte Tolerance at the time it was written).

This duplication is already owned by roadmap task 7.2.2 (`[ ]`, medium), whose
success criterion is exactly "shared coercion primitives parameterised on an
error factory … each package's typed error type … unchanged". No new action is
needed; this finding records that the audit re-verified the duplication still
exists and that 7.2.2's scope still describes it accurately, so the task should
not be retired or narrowed without addressing it.

- **Proposed fix:** None beyond keeping 7.2.2 open. When 7.2.2 is implemented,
  the error-factory parameterisation the task already prescribes will retire the
  duplication; the audit confirms the "frozen rule-pack path" rationale in the
  ledger docstring is the constraint 7.2.2's error-factory approach is designed
  to dissolve, so that rationale can be retired together with the duplication.

## Finding 3 — `pure.py` versus `_freeze.py` ergonomics

- **Category:** ergonomics
- **Severity:** low
- **Location:** `novel_ralph_skill/pure.py` (16 lines) and
  `novel_ralph_skill/_freeze.py` (34 lines)

Two small top-level modules sit beside the package's clear feature slices
(`commands/`, `contract/`, `ledger/`, `rulepack/`, `state/`). `pure.py` and
`_freeze.py` are general-purpose helpers whose home is less obvious than the
slice modules around them; a reader orienting via `docs/repository-layout.md` has
to open each to learn its responsibility. This is a minor wayfinding cost, not a
defect — both are short, documented, and correctly placed at package root if they
are genuinely cross-slice.

- **Proposed fix:** Confirm `docs/repository-layout.md` names both modules and
  states their cross-slice responsibility, so the top-level placement reads as
  deliberate rather than residual. If either is consumed by only one slice,
  relocate it into that slice to keep the group-by-feature convention
  (`AGENTS.md`) intact. No code change is warranted if the layout doc already
  accounts for them.

## Summary

The 7.2.1 refactor is clean, correctly scoped, and well-pinned; the new
`build_inline_table` helper is a pure query with both example and property
coverage, and the single-home documentation is accurate. The one genuinely
untracked issue is the array-of-inline-tables skeleton (Finding 1): the *inner*
idiom now has a single home, but the *outer* `[[chapters]]`-array skeleton
remains duplicated across `_set_chapters` and the corpus builder, recorded as a
"deferred follow-up" in the developers' guide with no roadmap task behind it. The
`_coerce` near-copy (Finding 2) is already owned by task 7.2.2 and needs only to
stay open. Finding 3 is a minor wayfinding nicety. No correctness defects were
found.
