# Logisphere design review — roadmap 7.3.1 — round 3

Adversarial pre-implementation review of `docs/execplans/roadmap-7-3-1.md`
(Revision 3), verified against the live tree in the `roadmap-7-3-1` worktree
and the read-only cuprum sibling checkout.

Verdict: **🔄 Revise** — one blocking stale-home prose reference survives every
gate (the exact six-months-later trap rounds 1 and 3 were chasing, on a comment
the two hard gates' patterns cannot match). Everything else verified accurate.

## What was verified against the tree (and holds)

- `_state_load.py` exists, is **364 lines** (`wc -l`), and every cited seam
  definition line is correct (`WORKING_DIR_NAME` 38, `working_dir` 41,
  `resolved_working_dir` 52, `state_path` 68, `STATE_INPUT_ERRORS` 85,
  `_state_input_error` 103, `_file_fault_error` 146, `_draft_read_error` 173,
  `_compile_write_error` 220, `_rule_pack_read_error` 259,
  `_device_ledger_read_error` 299, `_load_or_state_error` 335,
  `INSPECT_REPAIR_REMEDY` 100). `stub.py` does not exist (Surprises §2 holds).
- Command-consumer inventory (WI3) matches the tree exactly: `_compile.py:46`,
  `_recount.py:29`, `_novel_done.py:39`, `_desloppify.py:46`,
  `_wordcount.py:42`, `_desloppify_ledger.py:35`, `_state_mutators.py:35/39/42`
  (three blocks), `novel.py:36`.
- WI4 / Decision D8 six-seam-importer claim is **exactly right**: a full
  `grep -rn 'novel_state import' tests/` yields precisely six seam files
  (`multiplexer_support.py:25`, `test_state_input_message_unit.py:22`,
  `test_state_input_message_parity.py:20`, `test_draft_read_message_unit.py:25`,
  `test_compile_unit.py:30`, `test_validate_state_corpus.py:30`); every other
  hit is `build_app` or `_render_reconciliation`. `multiplexer_support.py` is
  indeed a conftest-registered plugin (`tests/conftest.py:64`). The B4
  collection-error risk is real and correctly mitigated.
- WI5 clean-up 3 keep/drop split is **exactly right**, verified by body-usage
  grep of `novel_state.py`: kept (used in body) = `STATE_INPUT_ERRORS` (line
  164), `_draft_read_error` (165), `_load_or_state_error`/`load_or_state_error`
  (200), `state_path` (200/252), `working_dir` (199/251),
  `resolved_working_dir` (276); dropped (no body use) = `_compile_write_error`,
  `_rule_pack_read_error`, `_device_ledger_read_error`, `_state_input_error`,
  `WORKING_DIR_NAME`.
- Gate 2 (`novel_state\._[a-z_]*error`) **does** match
  `novel_state._load_or_state_error` (the `_[a-z_]*` segment absorbs
  `_load_or_state_`), so all six dotted `:func:` roles in `commands/` plus the
  four test-docstring roles are caught. Confirmed the pattern does **not** match
  `novel_state.build_app` / `novel_state._render_reconciliation`.
- D4 (cuprum off-path) holds: `grep -rn cuprum novel_ralph_skill/commands/`
  returns nothing; design §4 lines 284-289 confirm "none [shells out] in v1".
  No cuprum API is on this task's path, so there is nothing to pin against the
  cuprum source. Confirmed against the read-only checkout's design notes too.
- `_state_mutators` second-hop re-export (`_state_path`/`_working_dir` for
  `_recount`/`_reconcile`) is real and the plan keeps it coherent (names
  unchanged, only the upstream source moves).

## 🔴 BLOCKING

**B7 (Doggylump / Pandalump — stale seam-home comment survives both hard
gates).** `novel_ralph_skill/commands/_state_mutators.py:64-65` carries the
comment:

> `# ``_state_path`` and ``_working_dir`` are re-exported from`
> `# :mod:`novel_ralph_skill.commands.novel_state
> `(the single accessor home) for`
> `# the sibling ``_recount``/``_reconcile`` mutator modules …`

WI3 repoints this module's imports (lines 35-44) onto `state_sourcing`. After
that repoint the comment is **factually wrong on both halves**: `_state_path`/
`_working_dir` are then re-exported from `state_sourcing`, and
`state_sourcing` — not `novel_state` — is "the single accessor home". This is
precisely the stale-prose-naming-the-old-home defect that B1 (round 1) and B5
(round 3) were created to eliminate, and **neither hard gate catches it**: Gate
1 matches only the `_state_load` token (this says `novel_state`); Gate 2
matches only `novel_state\._<…>error` formatter roles (this is a plain `:mod:`
role plus free prose with no `._error` suffix). The plan enumerates
`_state_mutators.py` at lines 35-44 (imports), 89/91/130 (`:func:` roles) — but
never lines 64-65.

Required fix: add `_state_mutators.py:64-65` to the WI5 clean-up-1 enumeration
(rewrite "re-exported from `novel_state` (the single accessor home)" to name
`state_sourcing` as the single accessor home), and **broaden the WI5 hard gate
to a third pattern that can see a plain `novel_state` `:mod:` role / prose that
asserts seam ownership**. A `_state_load`-style token gate cannot see this
class; the round-1/round-3 gates were each scoped to exactly the token they
were chasing and a new token (`novel_state` as home) has slipped through the
same blind spot a third time. Either enumerate-and-eyeball the residual `:mod:`
`novel_ralph_skill.commands.novel_state` references in `commands/` (filtering
out the genuine command-surface ones at `_state_mutators.py:6`,
`_chapter_plan_entry.py:6/9`, `_gate_drafting_mutators.py:11/349/353`,
`novel.py:82/86`), or add a guard. Until this reference is swept and gated, the
single-home property the task exists to establish is contradicted by a comment
in the very module that performs the second-hop re-export.

## 🟡 Unresolved risks (not blocking, but should be addressed)

- **A1 (no gate proves the underscore actually dropped in surviving prose).**
  After the `_load_or_state_error` → `load_or_state_error` rename, several
  hand-swept prose/role sites must lose the leading underscore as well as
  moving module (`devguide:976`, `devguide:1242`, the `:func:` roles at
  `_wordcount:112`, `_desloppify:168`, `_state_mutators:91`, and the four
  test-docstring roles). Gate 1 cannot see them (they say `novel_state`/bare),
  and after the fix Gate 2 passes whether the result reads
  `state_sourcing.load_or_state_error` (correct) or
  `state_sourcing._load_or_state_error` (a dangling underscore role that no
  longer resolves to any symbol). With nixie Mermaid-only and no Sphinx xref
  resolution in CI, a retained-underscore slip rots silently. Recommend a
  belt-and-braces post-WI6 grep
  `grep -rn '_load_or_state_error' novel_ralph_skill/ tests/ docs/developers-guide.md`
  returning nothing (the symbol is now public everywhere), added to the
  WI5/WI6 gate block.

- **A2 (devguide:620 `_state_load` is on the WI5 Gate-1 path but edited in
  WI6).**
  The plan acknowledges line 620 is touched by both WI5 (gate enumeration) and
  WI6 (the "Five … `state_sourcing`" edit) and says "whichever lands first must
  change it". Because WI5 lands before WI6 and Gate 1 must pass at WI5 commit
  time, WI5 must actually perform the 620 edit (not just enumerate it), or
  WI5's own Gate 1 fails. The plan's WI5 clean-up-1 list does include
  `devguide:620`, so this is consistent — flagging only so the implementer does
  not defer 620 to WI6 and break the WI5 gate.

## 🟢 Improvements

- WI5 Gate 2's comment claims it "catches the four dangling docstring roles".
  It catches considerably more (all ten pre-WI5 dotted `_…error` roles in
  `commands/` + `tests/`); the wording undersells it. Cosmetic.

## Pre-mortem (Doggylump)

*Six months on, a `novel-state` refactor (the future task this carve-out is
meant to protect against) is in flight. A developer reads
`_state_mutators.py:64-65`, sees "re-exported from `novel_state` (the single
accessor home)", and rewires the mutator second-hop back through
`novel_state` — reintroducing the `_state_mutators → novel_state` seam
dependency this task spent six work items removing.* Blast radius: `_recount`/
`_reconcile` silently re-pin to the façade; the WI2 structural test only
forbids *direct* `novel_state` seam imports in command modules, and re-exporting
`_state_path` from `_state_mutators` is not a seam-name import, so the AST
guard does not fire. Missed signal: the stale comment asserting the wrong home.
Wrong bet: "the two token gates cover every stale-home reference." Prevention
designable now: B7 — sweep the comment and add a `novel_state`-as-home gate so
the home assertion lives in exactly one place (`state_sourcing`) and the
codebase never again claims otherwise.

## Alternatives checkpoint (Wafflecat)

The strongest alternative to the per-pattern-token gate strategy is a single
**structural import gate** asserting "no module under `commands/` other than
`novel_state.py` and `state_sourcing.py` imports — directly or via the
`_state_mutators` re-export tail — any seam symbol sourced from `novel_state`",
enforced by walking the import graph rather than grepping tokens. Trade-off: it
costs one more careful AST test (the plan's WI2 test already does most of the
walk) but it would have caught B7-class *import* regressions structurally and
retired the whack-a-mole of adding a new grep pattern each review round. It
does **not** replace the prose gates (comments are not imports), so the token
sweeps still stand — but it would make the *behavioural* single-home property
self-defending rather than gate-dependent. Not required to ship 7.3.1; worth
noting for 7.3.6, which performs the larger `contract`↔`commands` rewire.

## Bottom line

The plan is structurally sound, the migration order is correct, the
six-importer and keep/drop inventories are verified accurate against the tree,
and the cuprum boundary is correctly excluded. It is **one ungated stale-home
comment (B7) away from being implementable as written**. Fix B7 (sweep + gate),
and the underscore-drop belt (A1) is a cheap insurance grep worth adding in the
same edit.
