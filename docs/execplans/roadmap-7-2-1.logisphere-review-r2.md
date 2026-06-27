# Logisphere design review — roadmap 7.2.1 (round 2)

Verdict: PROCEED WITH CONDITIONS (advisory-only). The round-2 plan resolves
both round-1 blockers (BLOCKING-1 via Option A — all five copies routed; RISK-1
via mechanically-checkable scoped greps) and folds in IMPROVEMENT-1/-2 and
OPEN-1. Every structural, import, and behavioural claim was re-verified against
real source; the locked-library (`tomlkit 0.15.0`) claim was verified against
the upstream changelog and is correctly cited. No blocking defects remain. Two
factual inaccuracies in the plan's prose and one stale roadmap-Success note are
advisory — fix in passing, they do not gate implementation.

## What was verified this round (and holds)

- Five `tomlkit.inline_table()` sites confirmed at the cited lines:
  `_recount.py` (call line 120), `_set_chapters.py` (161 `_chapter_array`, 183
  `_zero_word_counts`), `initial.py` (50), `_builder.py` (37). The two
  `_set_chapters.py` copies are real and identical idiom — Option A scope is
  correct.
- `tomlkit` locked 0.15.0 (`uv.lock:769-770`), installed 0.14.0 — matches plan.
- **Locked-library claim verified and cited.** Upstream changelog: the 0.15.0
  release (2026-05-10) has exactly one Changed entry — "Update parser to
  support TOML spec v1.1.0" (#456). It does not touch `inline_table`/
  `InlineTable`/`update`/`dumps`. D-TOMLKIT is accurate.
- **Test pins the *locked* version, not the system one.** `make test` →
  `$(UV) run pytest` (Makefile:126), so CI runs under `uv.lock`'s 0.15.0. The
  work-item-1 order/no-alias/mixed-type test therefore re-pins the locked
  version's behaviour, satisfying the "pin or cite" rule end-to-end.
- Helper body re-verified empirically on installed tomlkit: order preserved,
  mixed int/str intact, no aliasing after source mutation, empty → `{}`, and a
  non-dict `Mapping` subclass (`MappingProxyType`) works through `update`
  without the `dict()` wrap the recount copy carries. The planned body
  (`inline_table(); update(pairs); return`) is correct for all five callers.
- Import facts hold: `document.py` aliases `cabc` under `TYPE_CHECKING`
  (line 50) and does **not** yet import `tomlkit.items` (plan says add it only
  if absent — correct). `_recount.py` uses a runtime `import tomlkit.items`
  (line 23) annotating `tomlkit.items.InlineTable` — the house pattern D-SIG
  cites is real. `_builder.py` imports only `tomlkit` + sibling `_specs` today,
  so the corpus reroute is genuinely the first production import (D-CORPUS
  premise holds).
- No import cycle: `document.py` imports nothing from `initial`/`commands`/
  `tests`; the sibling/intra-package imports are acyclic.
- `write_document_atomically` is the correct sanctioned-writer name (exported in
  `state/__init__.py`); the plan does not confuse it with
  `write_text_atomically` (both exist).
- Roadmap §7.2 preamble DoD ("exactly one canonical implementation survives
  under one name … a test pins it") confirmed at roadmap.md:2669-2672. The
  developers-guide `recount_words` single-home note exists at line 1244
  (IMPROVEMENT-1 target). Design §5.3 confirmed to contain no single-writer
  sentence to "mirror" (IMPROVEMENT-1 correctly reworded). `make test` uses
  pytest-xdist (`-n`), but the new tests are pure synchronous
  structure-building with no timeout interaction, so the xdist/pytest-timeout
  caveat is not triggered.

## Findings

### 🟢 ADVISORY-1 (Telefono) — the `dict(...)` inventory claim is half wrong

Purpose (lines 46-48) and the first Risk (lines 166-171) state "Copies 1
(`_recount`) and 5 (`_set_chapters._chapter_array`) wrap the argument in
`dict(...)`." Verified source: only copy 1 wraps in `dict(...)`
(`_recount.py:121` `table.update(dict(by_chapter))`). Copy 5
(`_set_chapters.py:162`) passes a **dict literal** `table.update({...})`, which
is not "wrapping in `dict(...)`". `_zero_word_counts` (copy 4, line 184) passes
a dict-comprehension literal. The distinction is cosmetic to the design — the
helper subsumes literal, comprehension, and `dict()`-wrapped forms identically
(empirically confirmed) — but the plan's inventory misdescribes two sites.
Reword to: "Copy 1 wraps its `Mapping` argument in `dict(...)`; copies 4 and 5
pass dict literals; copies 2 and 3 pass the incoming mapping straight through."
Not blocking: no work-item instruction depends on the mischaracterisation.

### 🟢 ADVISORY-2 (Dinolump) — roadmap Success line is now under-inclusive

Roadmap §7.2.1's "Success" line names three consumers (`recount`,
`state/initial.py`, corpus builder) and the Reroute note says "consumed by all
three." Option A correctly honours the stricter §7.2 *preamble* DoD by also
routing the two `_set_chapters.py` sites, making `set-chapters` a fourth
consumer the Success line does not name. The plan justifies this well
(D-INVENTORY, Purpose) but never flags that the roadmap Success line itself is
now stale. Recommend a one-line note in the plan (or a roadmap-entry amendment
in work item 6) recording that 7.2.1's Success bullet under-counts the
consumers post-Option-A, so a future auditor checking the Success line against
the tree does not read the extra `set-chapters` call sites as scope creep.
Advisory: the preamble DoD is the binding criterion and the plan satisfies it.

### 🟢 ADVISORY-3 (Telefono) — make the version-pin linkage explicit

Risk (lines 194-203) frames the test as re-pinning "against the actually
installed version in CI," and Decision D-TOMLKIT verified behaviour on the
*system* 0.14.0. The load-bearing fact — that `make test` runs `uv run pytest`
under `uv.lock`'s **0.15.0**, so CI pins the *locked* version, not the system
0.14.0 — is left implicit. State it: the determinism/order test guards the
locked 0.15.0 specifically because the gate executes under `uv`. This closes
the only soft spot in the locked-library story.

## Pre-mortem (Doggylump)

- **Scenario 1 — silent scope failure (the r1 blocker).** Resolved. Option A
  brings all five copies into scope; acceptance check 2
  (`rg 'tomlkit\.inline_table\(' novel_ralph_skill` → exactly one match) now
  mechanically proves the single home, and check 1's per-file `def`-gone greps
  prove the old definitions are removed. An audit greppping `inline_table(` six
  weeks on finds only the helper.
- **Scenario 2 — snapshot churn.** Mitigated by construction: helper preserves
  order and value identity for mixed types (re-verified), and any snapshot
  regeneration is an escalation trigger, not a `--snapshot-update`. The
  `set-chapters` mixed-type entries (`number`/`slug`/`title`/`target_words`)
  and the recount ascending-key `by_chapter` both render byte-identically
  through the helper.
- **Scenario 3 — order-determinism regression on a future tomlkit bump.** The
  work-item-1 order test re-pins behaviour against the locked version in CI
  (because `make test` uses `uv run`); a future bump that sorts inline-table
  keys reddens that test before `recount` determinism breaks in the field.

## Strongest alternative (Wafflecat)

Unchanged from r1 and still rejected for the same reason: annotate-and-defer
(delete the "hand-copied twin" docstring line, add a behaviour-pinning test
across sites, skip the extraction) trades the DRY win and the roadmap-mandated
single home for zero cross-package import. It is viable engineering but
non-conformant to §7.2's DoD ("exactly one canonical implementation survives"),
which the extraction is the only way to satisfy. The proposed extraction is the
right call; Option A is the only variant that makes the DoD literally true.

## Bottom line

No blocking defects. The plan is implementable and design-conformant as
written: work items are atomic, ordered (helper-first, then independent
reroutes, then docs), individually gate-passable, and each names its validation
and its escalation trigger; the deterministic-write and round-trip contracts
are preserved and pinned; the locked-library claim is verified and cited; and
the acceptance criteria are mechanically checkable. ADVISORY-1/-2/-3 are prose
corrections to apply in passing — they do not change a single code edit.
