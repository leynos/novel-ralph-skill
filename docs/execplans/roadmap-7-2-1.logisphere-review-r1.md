# Logisphere design review — roadmap 7.2.1 (round 1)

Verdict: REVISE. The refactor is well-conceived, the cuprum-equivalent
(tomlkit) claims were verified against the real installed library, and the
import/cycle analysis is sound. But the plan asserts a global "exactly one home
/ exactly three copies" structure that the codebase contradicts: two further
byte-identical copies of the same idiom live in `commands/_set_chapters.py`,
untouched by the plan. As written, the plan's own acceptance criterion is
impossible to satisfy.

## What was verified (and holds)

- tomlkit empirical claims (D-TOMLKIT): on the installed 0.14.0,
  `inline_table().update({"c":3,"a":1,"b":2})` dumps `{c = 3, a = 1, b = 2}`
  (insertion order, not sorted); `update` is inherited, not overridden on
  `InlineTable`; values are copied in, so the table does not alias the source
  mapping (mutating the source after the call did not change the dump). Locked
  version 0.15.0 confirmed in `uv.lock`; installed 0.14.0 confirmed.
- The three named call sites exist exactly as described: `_recount.py:102`
  `_inline_by_chapter(cabc.Mapping[str, int])`; `initial.py:43` `_inline(dict)`;
  `_builder.py:35` `_inline(dict)`.
- No import cycle: `document.py` imports nothing from `initial`/`commands`;
  `parse.py` does not import `document`. The sibling import is safe.
- After deleting `_inline_by_chapter`, both `import tomlkit` (22) and
  `import tomlkit.items` (23) become unused in `_recount.py` — Ruff F401 forces
  removal; the plan anticipates this.
- The developers-guide `recount_words` single-home note (line ~1244) the plan
  proposes to mirror does exist.
- Roadmap 7.2.1 names exactly three consumers; the plan's scope matches the
  roadmap as written.

## Findings

### 🔴 BLOCKING-1 (Pandalump / Telefono) — undisclosed fourth and fifth copies

`grep -rn "inline_table(" novel_ralph_skill tests` returns five sites, not the
three the plan claims:

- `novel_ralph_skill/commands/_set_chapters.py:161` (`_chapter_array`, the
  `[[chapters]]` array entries) and
- `novel_ralph_skill/commands/_set_chapters.py:183` (`_zero_word_counts`, the
  `by_chapter` table).

Both are the identical `tomlkit.inline_table()` + `update({...})` idiom. The
plan never mentions them. Two concrete consequences:

1. The acceptance criterion is false as written. The plan's "Structure" quality
   criterion (and the `## Validation and acceptance` step) states: "grepping
   the source for `tomlkit.inline_table(` finds it only inside
   `build_inline_table` … the three former copies are gone." After implementing
   the plan verbatim, that grep still returns the two `_set_chapters.py` sites.
   The implementer either (a) believes they have failed, or (b) scope-creeps
   into `_set_chapters.py`, breaching the 8-file/150-line Tolerance and the
   roadmap's named scope. Both are bad outcomes the plan must pre-empt.

2. The Purpose/Context "single home" prose is overstated. "the inline-table
   materialisation rule lives in exactly one place" / "exactly one function
   owns the idiom" is untrue after this task while `_set_chapters.py`
   hand-rolls it twice. The step-7.2 DoD ("exactly one canonical implementation
   survives") would be visibly violated.

Required fix (planner's choice, but it must be made explicit):

- Option A (preferred — completes the step's intent): bring the two
  `_set_chapters.py` sites into scope as additional reroutes, route them through
  `build_inline_table`, and update the Tolerance/Progress/scope counts
  accordingly. `_zero_word_counts` passes `dict[str, int]` and
  `_chapter_array`'s entries pass `dict[str, object]` (mixed int/str), both
  covered by `Mapping[str, object]`. Note that `_chapter_array` and the corpus
  `_chapters_array` are themselves near-duplicates — flag, do not necessarily
  fix.
- Option B (stay within the roadmap's literal three): keep the scope, but
  (i) correct every "exactly one place / exactly three copies / exactly one
  function owns the idiom" claim to "the three roadmap-named copies," (ii)
  rewrite the acceptance grep so it does not assert a global uniqueness the
  task does not deliver (e.g. assert the three named former definitions are
  gone and the three named call sites import the shared symbol, and explicitly
  record that `_set_chapters.py` retains two out-of-scope copies deferred to a
  follow-up), and (iii) raise the `_set_chapters.py` duplication as a roadmap
  gap (a 7.2.x follow-up or an addendum), since step-7.2's DoD demands a true
  single home.

Either way the plan must stop claiming a uniqueness it does not establish.

### 🟡 RISK-1 (Telefono) — acceptance verification command is unreliable

`leta refs build_inline_table` (the plan's final check) confirms call sites but
does not prove the old definitions are gone. The companion "ripgrep for
`inline_table(`" is the check that catches a stale copy — but per BLOCKING-1 it
currently returns out-of-scope matches, so the implementer cannot use a bare
"zero/one match" pass/fail. Specify an exact, scoped command whose expected
output is unambiguous (e.g. assert no surviving `def _inline`/
`def _inline_by_chapter` in the three target files, and that
`build_inline_table` is the sole definition site), so "done" is mechanically
checkable rather than eyeballed.

### 🟢 IMPROVEMENT-1 (Dinolump) — §5.3 has no "single-writer discipline" to mirror

Work item 5 says to add a §5.3 sentence "mirroring the §5.3 single-writer
discipline" at "the existing §5.3 prose density." §5.3 as written is solely
about choosing `tomlkit` over an owned serialiser; it contains no
single-home/single- writer sentence to mirror. The instruction is harmless (a
sentence can still be added) but the cited precedent is inaccurate; reword to
"add a single-home sentence to §5.3 in the style of the developers-guide
`recount_words` note (which does exist, line ~1244)."

### 🟢 IMPROVEMENT-2 (Telefono) — annotation style departs from house pattern

Every existing module annotates this return type as qualified
`tomlkit.items.InlineTable` / `tomlitems.InlineTable` with a runtime
`import tomlkit.items`. Work item 1's import note proposes
`from tomlkit.items import InlineTable` and a bare `InlineTable`, and waffles
between TYPE_CHECKING and runtime import. With
`from __future__ import annotations` the return annotation is a string, so a
TYPE_CHECKING import suffices for the annotation; a runtime import is only
needed if a test does
`from novel_ralph_skill.state.document import InlineTable` (it should not — the
test should `import tomlkit.items` and assert against
`tomlkit.items.InlineTable`, the public type). Recommend: follow the house
pattern (runtime `import tomlkit.items`, annotate `tomlkit.items.InlineTable`)
to avoid a gratuitous style fork, and have the test assert
`isinstance(result, tomlkit.items.InlineTable)` (already what test assertion 1
says).

### 💡 OPEN-1 (Wafflecat) — is `state/document.py` the right home, or `state/initial.py`?

The Decision Log argues `document.py` over a new `state/_inline.py` or
`initial.py`. That reasoning is sound for the three named consumers. But if
Option A folds in the two `_set_chapters.py` (a `commands`-package mutator)
sites, the helper is consumed by `state`, `commands`, and `tests` — reinforcing
`document.py` (already imported across all three) as correct. The choice
survives the wider scope; record that explicitly so a future reader does not
relitigate.

## Pre-mortem (Doggylump)

Scenario 1 — silent scope failure. Six weeks on, an audit greps
`inline_table(`, finds the two `_set_chapters.py` copies, and concludes 7.2.1
did not achieve its single-home goal. Root cause: the plan asserted a
uniqueness it never scoped for. Prevention: BLOCKING-1 (scope them in, or
explicitly defer and stop claiming uniqueness).

Scenario 2 — snapshot churn surprise. An implementer reroutes the corpus
`_chapters_array` (mixed int/str values) and a snapshot reddens because a
value's TOML rendering shifted. Mitigation already present: the plan makes any
snapshot regeneration an escalation trigger, and the byte-for-byte round-trip
property guards it. Verified the helper preserves order and value identity for
mixed types, so this is low-likelihood — but the implementer must honour the
"stop and escalate, do not `--snapshot-update`" rule.

Scenario 3 — order-determinism regression unnoticed. A future tomlkit bump
sorts inline-table keys; `recount` determinism silently breaks. Mitigation
present and good: work item 1's order test re-pins behaviour against the
installed version in CI. Keep it.

## Strongest alternative (Wafflecat)

Do nothing / annotate-and-defer. The three copies are two lines each, with no
behavioural drift today; the "drift" the docstring admits is documentation, not
logic. One could close 7.2.1 by deleting the misleading "hand-copied twin"
docstring line and adding a shared test that pins all sites to identical
behaviour, without extracting a helper — trading the DRY win for zero churn and
zero new cross-package import (preserving the corpus oracle's clean import
graph). What it gives up: the roadmap explicitly mandates a single shared
helper consumed by all three, and step-7.2's DoD demands "exactly one canonical
implementation." So the alternative is viable engineering but non-conformant to
the roadmap — the proposed extraction is the right call. This calibration
strengthens, not weakens, the plan: the extraction is justified, but only if it
actually achieves the single home BLOCKING-1 is about.

## Bottom line

Fix BLOCKING-1 (resolve the `_set_chapters.py` copies — fold in or explicitly
defer-and-stop-overclaiming) and RISK-1 (make the acceptance check mechanically
checkable). IMPROVEMENT-1/-2 and OPEN-1 are quick prose/style corrections. The
tomlkit, cycle, and import-removal analysis is verified and sound.
