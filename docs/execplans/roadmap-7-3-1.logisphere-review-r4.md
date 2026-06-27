# Logisphere design review — roadmap 7.3.1, round 4

Verdict: **Proceed** (satisfied). No blocking defects. Two advisories noted.

Reviewed against the tree at worktree `roadmap-7-3-1`, the design doc
(`docs/novel-ralph-harness-design.md` §3.1/§4), ADR-003, the developers' guide,
AGENTS.md, the roadmap 7.3.1/7.3.6 entries, and the read-only cuprum checkout.
Every load-bearing factual claim in the plan was re-verified against source,
not the planner's summary.

## What round 4 had to prove

Round 3 raised B7 (an ungated `_state_mutators.py:64-66` stale "single accessor
home" comment) and advisory A1 (a `_load_or_state_error` insurance grep).
Revision 4 of the plan resolves both:

- **B7 resolved.** WI5 clean-up 1 now enumerates `_state_mutators.py:64-66` and
  the `state_sourcing.py` docstring import-home prose, rewriting both onto
  `state_sourcing`. **Gate 3** (the keyword pattern below)

  ```text
  novel_state.*(single accessor home|accessor home|the home|seam home|re-exported from)
  ```

  over `commands/` plus an enumerate-and-eyeball backstop is added. Verified:
  the defect comment exists at `_state_mutators.py:65` exactly as described,
  and Gate 1/Gate 2 are both blind to it (no `_state_load` token, no
  `._<…>error` suffix). Gate 3's keyword pattern matches it; the backstop's
  kept-set (`_state_mutators.py:6`, `_chapter_plan_entry.py:6/9`,
  `_gate_drafting_mutators.py:11/349/353`, `novel.py:82/86`) matches the tree
  exactly.
- **A1 resolved.** The `_load_or_state_error` insurance grep is in the WI5 and
  WI6 gate blocks and is re-run after WI6 (devguide:1242). Verified it catches
  every current `_load_or_state_error` token — including the bare-prose mentions
  (`_wordcount.py:117`, `_novel_done.py:28`, `devguide:976/1242`) that
  `leta rename` will not touch and the three `:func:` roles WI5 clean-up 2
  rewrites.

## Verification performed (all passed)

- **Gate 1/2/3 dry-run against the current tree** reproduces exactly the
  enumerated sets in WI5. No omission found.
- **Six test seam-importers (D8)** confirmed verbatim against
  `grep -rn 'novel_state import' tests/`: `multiplexer_support.py:25`
  (WORKING_DIR_NAME, conftest plugin per `conftest.py:64`),
  `test_state_input_message_unit.py:22`,
  `test_state_input_message_parity.py:20`, `test_draft_read_message_unit.py:25`
  (private `_draft_read_error`), `test_compile_unit.py:30`,
  `test_validate_state_corpus.py:30`. Every other `tests/` `novel_state` import
  is `build_app` or `_render_reconciliation`.
- **`novel_state` body usage (D8 drop-list)** confirmed: `WORKING_DIR_NAME` and
  `_state_input_error` have zero executable body uses (WORKING_DIR_NAME's only
  hit is the module docstring at line 4), so WI5 can drop them; the kept set
  (`STATE_INPUT_ERRORS`, `_draft_read_error`, `_load_or_state_error`,
  `state_path`, `working_dir`, `resolved_working_dir`) is used by `_check`/
  `_init`/`_disk_evidence_or_state_error` as claimed.
- **`INSPECT_REPAIR_REMEDY` exclusion (WI2)** confirmed: used only at
  `_state_load.py:142` and `:215`; no consumer imports it.
- **`_state_mutators` `__all__` re-export tail** (`_state_path`/`_working_dir`)
  confirmed unchanged in name; only the upstream source moves, so `_recount`/
  `_reconcile` need no edit.
- **cuprum exclusion (D4)** confirmed against the read-only checkout and the
  design doc: `grep -rn cuprum novel_ralph_skill/commands/` is empty; design
  doc lines 285-286 say "none [shell out] in v1". No subprocess on this task's
  path.
- **No uncited locked-library claim.** The plan makes no Cyclopts /
  pytest-timeout
  / uv behavioural assertion that needs a citation or a pinning test; the seam
  is pure `tomllib`/`pathlib`.
- **Roadmap coordination (D2)** confirmed: 7.3.6 (roadmap lines 2906-2908) owns
  the `WORKING_DIR_NAME` → `contract` move and asks 7.3.1 to keep it
  command-layer. The plan obeys.

## Adversarial probe — the round-N+1 "fresh token" pattern

The recurring failure mode across rounds is: each round a fresh stale-prose
token slips a gate scoped to the prior token (`_state_load` → B1;
`novel_state._<fmt>` → B5; `novel_state`-as-home → B7). I therefore hunted for
a *fourth* fresh token that survives all three gates plus A1 plus the eyeball
backstop.

The one structural soft spot: **Gate 3 and the enumerate-and-eyeball backstop
are scoped to `commands/` only**, not `tests/` or `docs/`. A genuinely novel
home-ownership phrasing in `tests/` or the developers' guide that contained
neither a `_state_load` token (Gate 1) nor a `._<…>error` suffix (Gate 2) nor a
`_load_or_state_error` token (A1) would be caught by no gate.

I tested whether such a survivor actually exists post-migration. It does not:

- The only `tests/` home claim — `test_state_load_actionable_parity.py:13`
  ("not the `novel_state` re-export") — carries the `_state_load` token on the
  same line, so **Gate 1 catches it**, and WI5 clean-up 1 enumerates it.
- The only `docs/` seam-home claim — `devguide:976` ("`novel state`'s
  `working_dir`, `state_path`, `_load_or_state_error`, … seams") — uses the
  display name `novel state` (a space, not the module token), which Gate 3
  would not match; but it carries `_load_or_state_error`, so **A1 catches it**,
  and WI6 explicitly enumerates and rewrites line 976.
- Every other tree-wide `novel_state` / `novel state` mention is a genuine
  command-surface fact (the 400-line cap at devguide:395, the multiplexer mount
  at devguide:441/`novel.py:82/86`, `init`/`check` location at devguide:1203 /
  `_state_mutators.py:6`), correctly left in place.

So the structural fragility is real but does **not** translate into a surviving
defect in this plan: both off-`commands/` home claims that exist are
independently double-covered (Gate 1 + WI5; A1 + WI6). The plan does not depend
on the eyeball backstop catching them.

## Advisories (non-blocking)

- **A1 (advisory — gate scope, for 7.3.6).** Gate 3 and the eyeball backstop are
  `commands/`-scoped. They happen to be sufficient here only because the two
  off-`commands/` home claims are independently covered by Gate 1 and A1. A
  future task that introduces a home claim in `tests/` or the guide phrased
  without any of those four tokens would have no net. Cheap hardening: widen
  the Gate 3 / backstop pattern to also include the display name `novel state`
  (with a space) and scope it to `tests/` + `docs/developers-guide.md` as well
  as `commands/`. Not required to ship 7.3.1 (no such survivor exists today),
  but it retires the whack-a-mole structurally. This aligns with Wafflecat's
  round-3 structural-import-gate suggestion, recorded for 7.3.6's `contract`↔
  `commands` rewire.
- **A2 (advisory — Gate 2 pattern vs the post-rename public name).** Gate 2's
  pattern `novel_state\._[a-z_]*error` requires a dot-underscore; after
  `leta rename` makes the symbol public, a role reading
  `novel_state.load_or_state_error` (no underscore) would **not** match Gate 2.
  This is harmless because (a) WI5 clean-up 2 hand-rewrites all three current
  `novel_state._load_or_state_error` roles (`_wordcount.py:112`,
  `_desloppify.py:168`, `_state_mutators.py:91`) onto `state_sourcing`, and (b)
  the A1 grep proves no `_load_or_state_error` token of any form survives. The
  plan's D9 sentence claiming Gate 2 "includes `load_or_state_error`" is
  therefore *slightly* inaccurate (Gate 2 catches the underscore form before
  the rename, not the public form after it), but the net is closed by A1. Worth
  a one-line correction to D9 for precision; not blocking.

## Pre-mortem (Doggylump)

The round-3 pre-mortem scenario (a future `novel-state` refactor re-pins the
`_state_mutators` tail through `novel_state` because a stale comment says
`novel_state` is the home) is now mitigated: B7 sweeps the comment and Gate 3
holds the home assertion in one place. The residual six-months-later risk is
the A1-advisory case — a *new* home claim added later in `tests/`/`docs/`
phrased outside all four tokens — which is out of scope for 7.3.1 and flagged
for 7.3.6.

## Bottom line

The migration order is correct and each WI is a single gate-passing commit; the
import inventories, keep/drop lists, line citations, and all three gates are
verified accurate against the tree; the deterministic/judgemental boundary is
untouched (pure module-boundary + rename refactor, no behaviour change); cuprum
is correctly excluded; and no locked-library claim is uncited. B7 and A1 from
round 3 are resolved. The two advisories are precision/hardening items, not
must-fix design defects. I would stake my name on this being implementable and
design-conformant as written.
