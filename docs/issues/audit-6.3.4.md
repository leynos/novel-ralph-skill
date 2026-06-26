# Post-merge audit — roadmap task 6.3.4

Task 6.3.4 made the `working/` directory resolve robustly and surfaced the
resolved path (commit `a52def8`). It adds a `resolved_working_dir()` accessor in
`novel_ralph_skill/commands/_state_load.py` that returns
`working_dir().resolve()` — the absolute, non-strict-resolved `working/` — and
stamps that absolute path at the two production stamps: the envelope
`working_dir` field built by `novel.main` and the `result.working_dir` body of
`novel state init`. It documents the absolute-path contract in the harness
design doc, the developers' guide, and ADR-003, and covers the behaviour with
new unit tests (`test_state_load_resolved_working_dir.py`), entry-point
behavioural tests (`test_novel_main_working_dir.py`), a refreshed mutator
snapshot, and an installed-binary error-arm assertion.

This audit reviews the merged state at `origin/main` (commit `a52def8`) for
refactoring opportunities, duplication, complex conditionals, ergonomic
awkwardness, high-similarity functions, inconsistencies, separation-of-concerns
and command/query-segregation issues, and gaps in documentation comments,
developer/user documentation, and behavioural/unit test coverage. Each finding
records a location and a concrete proposed fix.

The 6.3.4 change itself is well-targeted: `resolved_working_dir()` is a thin,
well-documented accessor pinned by three unit tests (absolute, succeeds without
`working/`, coherent with `working_dir()`), the entry-point tests prove the
production stamp is absolute and that the inside-`working/` footgun surfaces as
`.../working/working`, and the resolution rule itself is left unchanged. The
material findings are about the *boundary the change drew*: it made the JSON
`working_dir` **field** absolute but left every human-readable **message** that
names the same directory cwd-relative, so the "a misresolution is visible"
contract the design doc now asserts holds only for the field, not for the prose
an operator reads. The remaining findings are pre-existing duplication that the
6.3.4 surface sits adjacent to.

## 1. The `working_dir` field is absolute but every error/result message naming the same directory is still relative

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/novel_state.py:158` (disk-evidence
  read fault), `novel_state.py:248` (init refusal), `novel_state.py:271` (init
  success message), `_state_load.py:127,132` (`_state_input_error` arms),
  `_novel_done.py:92` (done-predicate read fault)

6.3.4's stated intent (commit message, design doc, developers' guide) is that a
misresolution becomes "visible in the field the harness already reads" — a stray
`cd` into `working/` shows `.../working/working` rather than failing silently.
That now holds for the envelope `working_dir` field and for `init`'s
`result.working_dir`. But every *message* that names the working tree still
embeds a cwd-relative path:

- `_disk_evidence_or_state_error` raises `f"cannot read disk evidence under
  {working_dir}: …"` where `working_dir` is `working_dir()` (relative
  `working`).
- `_novel_done`'s clause wrapper raises `f"cannot evaluate the done predicate
  under {root}: …"` where `root = working_dir()` (relative).
- `_init` raises `f"refusing to overwrite existing {path}"` and emits
  `messages=[f"initialised {path}"]` where `path = state_path()` (relative
  `working/state.toml`).
- `_state_input_error`'s corrupt-file arm names `{path}` (relative).

An operator who reads the exit-3 message (rather than parsing the JSON field)
sees the bare relative token, so the very footgun 6.3.4 set out to surface stays
silent in the message channel. The split is starkest *inside* `_init`: the same
`CommandOutcome` carries `result.working_dir` as the absolute resolved path and
a `messages` line as the relative path — visible in
`tests/__snapshots__/test_novel_state_mutator_snapshots.ambr:22`, where
`result.working_dir` is `<working-dir>` (a redacted absolute path) while the
message is `initialised working/state.toml`.

- **Proposed fix:** Decide the directory-naming polarity once and apply it
  consistently. Either (a) thread `resolved_working_dir()` into the message
  builders so the disk-evidence fault, done-predicate fault, `init` refusal, and
  `init` success message name the absolute path the field already carries; or
  (b) explicitly document that messages stay cwd-relative by design and the
  field is the canonical machine signal, and add a one-line note to the design
  doc / developers' guide saying so. Option (a) better matches the stated
  "visible misresolution" goal. In either case the `_state_input_error`
  missing-`working/` arm should also be reviewed: it names `pathlib.Path.cwd()`
  (absolute) and the relative `path` in the same message, which is already a
  mixed-polarity message today.

## 2. No test pins the resolved/relative polarity of the message channel

- **Category:** test-gap
- **Severity:** medium
- **Location:** `tests/test_novel_main_working_dir.py`,
  `tests/test_console_scripts_error_arms_e2e.py:273` (machine-envelope arm)

The 6.3.4 tests assert the envelope `working_dir` *field* is absolute and that
the `init` *result* body is absolute, but nothing pins what the *message* says
about the directory. `test_main_surfaces_inside_working_footgun` asserts the
footgun is visible in the field; there is no companion assertion that the
exit-3 message either does or does not carry the resolved path. As a result,
finding 1's inconsistency is invisible to the suite, and whichever polarity is
chosen in finding 1's fix could silently regress.

- **Proposed fix:** Add a behavioural assertion (extending
  `test_novel_main_working_dir.py` or the error-arm e2e) that pins the message
  channel's directory polarity for at least the no-`working/` and
  inside-`working/` arms, matching whatever finding 1 settles. If messages stay
  relative by design (option b), pin that explicitly so the choice is a tested
  contract rather than an accident.

## 3. The `log.md` receipt-append helper is duplicated near-verbatim across two mutators

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_set_chapters.py:205-215`
  (`_append_receipt`), `novel_ralph_skill/commands/_reconcile.py:78-88`
  (`_append_recovery_entry`)

The two helpers are byte-for-byte identical apart from the operation label
embedded in the line. Both compute `dt.datetime.now(dt.UTC).isoformat()` and
open `working_dir / "log.md"` in UTF-8 append mode to write
`f"- {timestamp} {operation}: {line}\n"`. `_set_chapters._append_receipt`'s own
docstring acknowledges this: "Mirrors `_reconcile._append_recovery_entry`". The
RFC 3339 UTC timestamp construction is repeated a third time in
`novel_state._init:253` (`created_at`).

- **Proposed fix:** Extract one `_append_log_receipt(working_dir, operation,
  line)` helper (and optionally a `_utc_timestamp()` seam) into a dependency-free
  leaf shared by the mutators — `_state_load.py` is the natural home, mirroring
  how the state-load boundary was already carved out there. Route both call
  sites and `_init`'s `created_at` through the shared timestamp seam. This is
  consolidation hygiene, so it belongs in phase 7 ("single-source the duplicated
  implementations") rather than as a new step. No behavioural change.

## 4. The draft-read state-error wrapping idiom remains duplicated and now spans nine sites

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_wordcount.py`, `_recount.py`,
  `_compile.py` (three sites), `_desloppify.py`, `_state_mutators.py`,
  `_novel_done.py:90-93`, and `novel_state.py:156-159`
  (`_disk_evidence_or_state_error`)

This is a recurrence, not a new finding: audit-6.3.3 already documented the
`try: <reader> / except STATE_INPUT_ERRORS as exc: raise StateInputError(f"…:
{exc}") from exc` idiom repeated across eight command bodies. The
disk-evidence wrapper in `novel_state.py` is the ninth instance of the same
shape, and 6.3.4 left it untouched. The sites differ only in the reader called
and the context phrase. Recording it here keeps the recurring debt visible at
the 6.3.4 step boundary so it is not lost between audits.

- **Proposed fix:** As proposed in audit-6.3.3, extract one
  `read_or_state_error(reader, *, context)` wrapper (or a decorator) into the
  state-load leaf so every working-tree reader routes its `STATE_INPUT_ERRORS`
  translation through one place; the context phrase becomes the one varying
  argument. Fold into the phase 7 consolidation step alongside finding 3 so the
  two `working/`-tree DRY moves land together. If finding 1 chooses the
  resolved-path polarity for messages, this shared wrapper is the single point at
  which to apply it to the read-fault arms.

## 5. `resolved_working_dir`'s docstring duplicates the resolution rule by line number, which will drift

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_state_load.py:50-65`
  (`resolved_working_dir`), cross-referenced from `novel.py:159` and the
  developers' guide

The `resolved_working_dir` docstring, the `novel.main` docstring, and the
developers' guide all point at the cwd-relative resolution rule by *source line
number* ("the rule at `_state_load.py:32-48`"). Line-number cross-references
inside docstrings are brittle: any edit above line 48 in `_state_load.py`
silently invalidates three references, and there is no guard that catches the
drift. The `working_dir()` docstring and the `WORKING_DIR_NAME` comment likewise
cite "design line 151", which has the same fragility against design-doc edits.

- **Proposed fix:** Replace the intra-file line-number citations with a named
  anchor — point at `working_dir` (the symbol) or a short named paragraph
  ("the cwd-relative resolution rule documented on `working_dir`") rather than a
  numeric span. This is the lowest-severity finding and is best folded into the
  phase 7 documentation-reconciliation leg rather than actioned standalone.

## Summary

The 6.3.4 implementation is sound and well-tested for the contract it pins (the
absolute `working_dir` *field*). The one material gap is a polarity
inconsistency the change introduced: the JSON field is now absolute while every
human-readable message that names the same directory stays cwd-relative —
including two channels within a single `init` envelope — so the "misresolution
is visible" goal holds for the field but not for the prose, and no test pins the
message channel either way (findings 1 and 2). The remaining findings are
pre-existing `working/`-tree duplication (findings 3 and 4, the latter a
recurrence from audit-6.3.3) and brittle line-number doc cross-references
(finding 5), all of which belong in the phase 7 consolidation step rather than
as new roadmap steps.
