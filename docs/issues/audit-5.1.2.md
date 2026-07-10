# Post-merge audit — roadmap task 5.1.2

Audit of the codebase after roadmap task 5.1.2 ("Implement desloppify detection
over the §6 offender table") merged to `main` at commit `f55a2bb`. The slice
wires the detect-only `desloppify` checker (ADR-001) on top of the 5.1.1
rule-pack loader: a pure aggregation core
([`rulepack/detect.py`](../../novel_ralph_skill/rulepack/detect.py):
`ScannedChapter`, `LineHit`, `RuleFinding`, `DetectionReport`, `detect`), the
shipped §6 offender pack
([`rulepack/packs/offenders.toml`](../../novel_ralph_skill/rulepack/packs/offenders.toml)),
the command body and working-tree sourcing
([`commands/_desloppify.py`](../../novel_ralph_skill/commands/_desloppify.py)),
the envelope projection and packaged-pack resolver
([`commands/_desloppify_report.py`](../../novel_ralph_skill/commands/_desloppify_report.py)),
and a widened `load_rulepack` signature
([`rulepack/parse.py`](../../novel_ralph_skill/rulepack/parse.py)) accepting any
`Traversable`. It is guarded by
[`tests/test_rulepack_detect.py`](../../tests/test_rulepack_detect.py),
[`tests/test_desloppify_command.py`](../../tests/test_desloppify_command.py),
[`tests/test_desloppify_sourcing.py`](../../tests/test_desloppify_sourcing.py),
[`tests/test_desloppify_snapshots.py`](../../tests/test_desloppify_snapshots.py),
[`tests/test_desloppify_e2e.py`](../../tests/test_desloppify_e2e.py), and
[`tests/test_offenders_pack.py`](../../tests/test_offenders_pack.py).

The slice is sound and discharges its success criterion: `desloppify` scans the
working tree against the §6 pack, reports the enumerated per-hit envelope
(`phrase`, `count`, `density`, `threshold`, `passed`, `lines`), and routes
faults correctly across the exit-2/3/4 channels. The pure detection core is
well factored and thoroughly unit-tested, and the report module keeps the
projection out of the body to honour the 400-line cap. The findings below are
duplication, consistency, and coverage opportunities; none is a blocking
defect.

This audit checks the new code against the design's authoritative artefacts and
the recurring themes carried by the prior audits (`docs/issues/audit-2.3.1.md`,
`docs/issues/audit-5.1.1.md`). Each finding records a category, a location, a
description, a concrete proposed fix, and a severity.

Trail followed: explored with `leta`/`Read` over the `rulepack` and `commands`
packages, `state/wordcount.py`, `commands/_recount.py`, and the desloppify
tests; traced history with `git show f55a2bb` and `sem` over the merged commit.
Source of truth consulted: `docs/novel-ralph-harness-design.md` §3.1, §3.2,
§3.3, §4.4, §5.1, §6, and §9;
[`docs/adr-001-deterministic-judgemental-boundary.md`](../adr-001-deterministic-judgemental-boundary.md);
[`docs/adr-003-shared-interface-contract.md`](../adr-003-shared-interface-contract.md);
`docs/scripting-standards.md`; `docs/developers-guide.md`;
`docs/users-guide.md`; and `AGENTS.md`. Language router: `python-router`
(Python data shapes, errors and logging, testing). Spelling per `en-gb-oxendict`.

## Finding 1 — `_chapter_text` and `_chapter_word_count` duplicate the draft-path derivation and the read fault boundary

- **Category:** duplication
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/commands/_desloppify.py:73-113`](../../novel_ralph_skill/commands/_desloppify.py)
  (`_chapter_text`) against
  [`novel_ralph_skill/state/wordcount.py:41-83`](../../novel_ralph_skill/state/wordcount.py)
  (`_chapter_word_count`)

Both helpers compute the identical draft path
(`working_dir / "manuscript" / f"chapter-{number:02d}" / "draft.md"`), read it as
UTF-8, and apply the same fault boundary — `FileNotFoundError` is the one benign
fault (an undrafted chapter), every other `OSError`/`UnicodeDecodeError`
propagates for the command layer to route to exit 3. The only difference is the
last line: `_chapter_word_count` returns `len(text.split())`, `_chapter_text`
returns the raw text. Both even carry near-verbatim docstrings and the same
"a broad `except OSError` would swallow a `PermissionError`" comment. This is the
load-bearing convention design §5.1 and both modules' docstrings claim "cannot
disagree on which file a chapter maps to" — but the agreement is currently
enforced by two hand-kept copies, so a change to the path layout (for example a
`drafts/` subdirectory, or a `.md` rename) or to the fault boundary must be
mirrored in both or they silently drift, and the cross-module "cannot drift"
claim becomes false.

**Proposed fix:** extract one shared reader in the `state` package — for example
`read_chapter_draft(working_dir, number) -> str | None` (or returning `""`) that
owns the path derivation and the `FileNotFoundError`-to-absent boundary — and
have `_chapter_word_count` call it then `.split()`, and `_desloppify._chapter_text`
call it directly. The path/fault contract then has one home, the "cannot drift"
docstring claims become structurally true rather than aspirational, and the later
`wordcount` command (roadmap §4.5) inherits the same reader. Cross-layer
direction is clean: `commands` already depends on `state`. Gated by Ruff,
`pyright`, `interrogate`, and `pytest`.

## Finding 2 — `source_chapters` repeats `_recount`'s "map `STATE_INPUT_ERRORS` to `StateInputError`" wrapper

- **Category:** duplication
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/_desloppify.py:190-200`](../../novel_ralph_skill/commands/_desloppify.py)
  (`source_chapters`'s `try`/`except STATE_INPUT_ERRORS`) against
  [`novel_ralph_skill/commands/_recount.py:75-79`](../../novel_ralph_skill/commands/_recount.py)
  (`_recount_or_state_error`)

Both bodies wrap a per-chapter draft read in a `try` block whose
`except STATE_INPUT_ERRORS as exc` arm re-raises
`StateInputError(f"cannot ...: {exc}") from exc`,
differing only in the prose ("cannot read chapter drafts" versus "cannot recount
chapter drafts"). This is the third instance of the same "translate a read fault
to the exit-3 channel" idiom (the shared `_load_or_state_error` is the first).
The pattern is small, but it is now hand-repeated across two command modules, and
`_desloppify.py`'s own docstring explicitly notes it does "exactly as
`_recount._recount_or_state_error` does" — an acknowledgement that the seam is
shared but the code is not.

**Proposed fix:** lift a single helper into `novel_state.py` beside the existing
`_load_or_state_error`, for example
`_as_state_error(action: str, fn: Callable[[], T]) -> T` (or a context manager
`with state_error_context("read chapter drafts"):`) that runs the body and
re-raises `STATE_INPUT_ERRORS` as `StateInputError` with a `f"cannot {action}: {exc}"`
message. `source_chapters` and `_recount_or_state_error` then both call it,
giving the exit-3 translation one definition. Purely internal; the exit-code
behaviour the command tests assert is unchanged. Gated by Ruff, `pyright`, and
`pytest`.

## Finding 3 — `detect`'s "cannot drift from `recount_words`" claim is misleading under `--chapter` scope

- **Category:** docs-gap
- **Severity:** medium
- **Location:**
  [`novel_ralph_skill/rulepack/detect.py:126-131`](../../novel_ralph_skill/rulepack/detect.py)
  (`DetectionReport.total_words` attribute doc) and
  [`novel_ralph_skill/rulepack/detect.py:242-245,259`](../../novel_ralph_skill/rulepack/detect.py)
  (`detect` docstring and body)

`detect` computes `total_words = sum(len(ch.text.split()) for ch in chapters)`
over exactly the *scanned* chapters, and both the attribute doc and the function
docstring justify the `.split()` rule by asserting it matches
`recount_words` "so the two counts cannot drift". The token *rule* matches, but
the *scope* does not: `recount` always counts the whole `[chapters]` manifest,
whereas `desloppify --chapter N` passes a single `ScannedChapter`, so its
`total_words` (and therefore its `per_page` density denominator) is that one
chapter's word count, not the manuscript total. This is the correct behaviour for
"density over the scanned text", but the docstrings invite a reader to believe
`total_words` equals `recount`'s `current`, which it does not under `--chapter`.
The "cannot drift" phrasing conflates "same per-token rule" with "same value",
and the per-page semantics under chapter scope are undocumented for both
developers and users.

**Proposed fix:** reword the two `detect` docstrings to claim only what holds —
the *token rule* (`len(text.split())`) is identical to `recount_words`, so a
whole-manuscript scan's `total_words` equals `recount`'s `current`, while a
`--chapter N` scan's `total_words` is that chapter's count and the per-page
density is therefore relative to the scanned chapter, not the manuscript. Add one
sentence to the users' guide `desloppify` section noting that `--chapter N`
computes per-page density over that chapter alone. No behaviour change. Gated by
`interrogate`, `make markdownlint`, and `make nixie`.

## Finding 4 — The `per_page` density failure message branch is never exercised by a test

- **Category:** test-gap
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/_desloppify_report.py:115-120`](../../novel_ralph_skill/commands/_desloppify_report.py)
  (`_finding_message` density branch) against
  [`tests/__snapshots__/test_desloppify_snapshots.ambr`](../../tests/__snapshots__/test_desloppify_snapshots.ambr)
  and [`tests/test_desloppify_command.py:81-103`](../../tests/test_desloppify_command.py)

`_finding_message` has two arms: the `manuscript` arm
(`"{rule_id} exceeds threshold ({count} > {threshold})"`) and the `per_page` arm
(a `density {density:.2f} > {threshold} per {page_words} words` rendering).
The snapshot suite pins the `manuscript` arm (`smirked exceeds threshold (2 > 1)`
appears in the `.ambr`), and `test_em_dash_flood_exits_four` drives a `per_page`
failure but asserts only the exit code and `result.violations`, never the
emitted message. So the density-message branch — which carries user-facing prose
with its own `:.2f` formatting and `per N words` phrasing — has no assertion
guarding its text. A regression that mis-formatted the density message (for
example dropping `page_words`, or changing the precision) would pass every test.

**Proposed fix:** extend the em-dash flood test (or add a focused snapshot/unit
case) to assert the human-mode message contains the density rendering — for
example that the `em-dash` message matches
`density <n.nn> > 5 per 300 words`. A direct `_finding_message` unit test over a
hand-built `per_page` `RuleFinding` is the cheapest guard and pins both arms.
Gated by `pytest`.

## Finding 5 — `_finding_payload` and `_finding_message` reach across module layers into `RuleFinding` internals

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/commands/_desloppify_report.py:90-99`](../../novel_ralph_skill/commands/_desloppify_report.py)
  (`_finding_payload`) and
  [`novel_ralph_skill/commands/_desloppify_report.py:115-123`](../../novel_ralph_skill/commands/_desloppify_report.py)
  (`_finding_message`)

The report module hand-projects every field of `RuleFinding`/`LineHit` into the
`result` dict and reaches into `finding.basis.value`, `finding.page_words`,
`hit.chapter`, and `hit.line` to build both the machine payload and the prose. The
contract knowledge — which fields are emitted, that `basis` must be pinned to
`.value`, the `(chapter, line)` line shape — lives entirely in the `commands`
layer, while the data shape lives in `rulepack/detect.py`. Adding a field to the
envelope (the roadmap's ai-isms/device-ledger packs at §7.1 will want richer
findings) means editing the `commands` projection by hand and risks the payload
and the schema diverging, since no single place owns "the JSON shape of a
finding". This is the lighter, forward-looking cousin of audit-5.1.1 Finding 1's
"contract re-keyed by hand" theme.

**Proposed fix:** consider giving `RuleFinding` (and `LineHit`) a small
`as_payload()` / `to_mapping()` method, or a sibling pure projector in the
`rulepack` package, so the "JSON shape of a finding" has one home next to the
shape it serializes; the `commands` report module then composes those payloads
into the envelope and owns only the message prose and the success/finding split.
This is a judgement call, not a defect — flag it for the §7.1 multi-pack work
rather than refactoring pre-emptively. Gated by Ruff, `pyright`, and `pytest`.

## Finding 6 — `_finding`'s zero-page fallback couples a divide-guard to an `count <= 0` pass rule that is hard to follow

- **Category:** complexity
- **Severity:** low
- **Location:**
  [`novel_ralph_skill/rulepack/detect.py:211-217`](../../novel_ralph_skill/rulepack/detect.py)
  (`_finding`, the `PER_PAGE` arm)

The `per_page` arm computes `pages`, then `density`, then `passed` with three
chained `if pages > 0 else` ternaries:
`pages = total_words / page_words if page_words else 0.0`;
`density = count / pages if pages > 0 else 0.0`;
`passed = density <= rule.threshold if pages > 0 else count <= 0`. The same
`pages > 0` predicate is evaluated three times and the empty-manuscript fallback
(`count <= 0`) is buried in the third ternary's `else`, so the invariant "an empty
manuscript passes iff it has no hits, with `0.0` density and no `ZeroDivisionError`"
is spread across three lines rather than stated once. It is correct (the unit test
`test_empty_manuscript_passes_without_zero_division` proves it), but the reader
must mentally re-derive the empty-page case from three separate ternaries.

**Proposed fix:** lift the empty-manuscript case to a single early branch — e.g.
`if pages <= 0: density, passed = 0.0, count <= 0` then an `else` that computes
`density = count / pages` and `passed = density <= rule.threshold` once — so the
zero-page semantics are named in one place and `pages > 0` is tested once. Purely
a readability refactor; the existing detect unit tests pin the behaviour.
Gated by Ruff and `pytest`.
