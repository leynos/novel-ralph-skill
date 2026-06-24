# Post-merge audit — roadmap task 2.3.3

Audit of the codebase after task 2.3.3 ("Add disk-authoritative cross-checks to
the corpus oracle") merged to `main` at commit `c7ebfaf`. The task rerouted three
corpus-oracle disk-evidence predicates (`_check_manifest_disk_bijection`,
`_check_done_flag_without_draft`, `_check_compiled_matches_drafts`) from reading
the `WorkingTreeSpec` to reading the materialised `working/` tree, so all six
disk-evidence twins are now genuinely disk-vs-disk.

Trail followed: `docs/novel-ralph-harness-design.md` §§3.3/5.2/5.4,
`docs/developers-guide.md` §"Invariant validation", `docs/adr-001`, `AGENTS.md`
(quality gates and the 400-line cap), the `python-router` skill (Python work),
and `leta`/`sem` for navigation and history. Files inspected:
`tests/working_corpus/_oracle.py`, `novel_ralph_skill/state/disk_evidence.py`,
`tests/test_working_corpus_disk_divergence.py`,
`tests/test_novel_state_check_disk.py`, `tests/working_corpus/_specs.py`,
`novel_ralph_skill/state/wordcount.py`, `docs/developers-guide.md`.

The merged change is high quality: the divergence-proof self-tests are precise,
the agreement suite pins both twin sides on every corpus tree, and the docstrings
are thorough. The findings below are refinements, not defects in the merged
behaviour.

## Finding 1 — `_oracle.py` is one line from the 400-line cap (severity: medium)

**Category:** ergonomics

**Location:** `tests/working_corpus/_oracle.py` (399 lines);
`pyproject.toml` `[tool.pylint.main] max-module-lines = 400`; `AGENTS.md`
§"Keep file size manageable".

**Description:** Task 2.3.3 grew the oracle to 399 lines, one below the hard
400-line module cap enforced by pylint and AGENTS.md. The module's own
`tests/test_working_corpus_disk_divergence.py` docstring already notes the sibling
`tests/test_working_corpus.py` is "already past the 400-line cap", confirming the
cap bites in this area. The next corpus invariant — the roadmap already
anticipates one (`docs/roadmap.md` lines 1342-1345 defer a follow-up "until at
least one further corpus category") — will breach the cap and force an unplanned
carve-out mid-task.

**Proposed fix:** Pre-emptively carve the six disk-evidence predicates
(`_on_disk_chapter_numbers`, `_check_manifest_disk_bijection`,
`_check_done_flag_without_draft`, `_disk_drafts`, `_disk_present_draft_bodies`,
`_check_compiled_matches_drafts`, `_disk_by_chapter`,
`_check_word_counts_match_drafts`, `_check_by_chapter_sum`,
`_check_cursor_plan_present`) into a `tests/working_corpus/_oracle_disk.py`
sibling, re-exported from `_oracle.py`, mirroring the existing
`test_working_corpus_divergent` / `test_working_corpus_disk_divergence`
carve-out idiom. This restores headroom and groups the disk-vs-disk checks that
now share a reading model.

## Finding 2 — `state.toml` is re-parsed up to five times per `corpus_check` (severity: low)

**Category:** duplication

**Location:** `tests/working_corpus/_oracle.py` — `_check_by_chapter_sum`
(line 120), `_check_manifest_disk_bijection` (line 178),
`_check_done_flag_without_draft` (line 231), `_disk_drafts` (line 262),
`_check_word_counts_match_drafts` (line 322) each independently call
`tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))`.

**Description:** A single `corpus_check` invocation reads and parses the same
`state.toml` from disk up to five times. The literal
`tomllib.loads((working_dir / "state.toml").read_text(encoding="utf-8"))` is
copy-pasted across five predicates, so a change to the read convention (encoding,
filename, error handling) must be made in five places and is easy to skew. This
mirrors the production twin, where `disk_word_counts`/`_present_draft_bodies`
already share reads, so the oracle side is the laggard.

**Proposed fix:** Extract a private `_load_state_table(working_dir) -> Mapping`
helper in the oracle (parsing `state.toml` once) and have the five predicates call
it. The per-`corpus_check` re-parse cannot be collapsed without threading the
parsed table through `corpus_check` (the predicates take `working_dir`, not a
parsed view), but centralising the read literal removes the copy-paste and the
skew risk; if the repeated parse becomes a measured cost, pass the parsed table
into the disk predicates from `corpus_check`. Keep the helper oracle-local so the
deliberate-twin independence from production is preserved.

## Finding 3 — `_on_disk_chapter_numbers` twins diverge in control flow (severity: low)

**Category:** similarity

**Location:** `tests/working_corpus/_oracle.py` lines 155-167 vs
`novel_ralph_skill/state/disk_evidence.py` lines 86-100.

**Description:** The two `_on_disk_chapter_numbers` twins compute the identical
set but spell the guard differently: the oracle uses
`if entry.is_dir() and suffix.isdigit():` after computing `suffix`
unconditionally, while production uses an early `if not entry.is_dir(): continue`
then `if suffix.isdigit():`. They are behaviourally equivalent, but the
deliberate-twin policy is precisely that a reader must hand-verify the two sides
agree; gratuitous structural difference makes that verification harder than it
need be and is not pinned by any same-shape test (the agreement suite pins the
*verdict*, not the predicate body). The oracle docstring even claims it "mirrors
production `_on_disk_chapter_numbers`" while the body does not mirror it.

**Proposed fix:** Align the oracle helper's control flow to production's
(early `continue` on non-directories, then the `isdigit` guard), so "mirrors
production" is literally true and the twin diff is the minimum the policy allows.
This is a presentational alignment only — do **not** de-duplicate across the
twin boundary (the developers' guide forbids collapsing the twins).

## Finding 4 — developers' guide omits the disk-evidence twin discipline and task 2.3.3 (severity: medium)

**Category:** docs-gap

**Location:** `docs/developers-guide.md` §"Invariant validation", lines 336-348
(disk-evidence prose) and 426-434 (the "deliberate twins" paragraph).

**Description:** The guide's explicit twin-policy paragraph (lines 426-434) covers
only the *six pure-state* `validate_state` twins ("Six of `validate_state`'s
structural predicates are deliberate twins…"). The disk-evidence side now has its
own deliberate-twin discipline — `check_disk_evidence`'s six predicates are twins
of the oracle's disk-reading predicates, and after task 2.3.3 **all six read disk
on both sides** (disk-vs-disk), pinned by `tests/test_disk_evidence.py` and
`tests/test_novel_state_check_disk.py`. None of that disk-vs-disk twin discipline,
nor task 2.3.3 itself, nor the retirement of the former spec-reading asymmetry
("advisory A1"), appears in the guide. The §5.2 invariant table (lines 355-363)
still labels invariant 5 "deferred to task 2.3.2", which 2.3.2/2.3.3 have now
delivered. A maintainer editing a disk-evidence predicate has only the source
docstrings to learn the policy from; the guide — the stated source of truth —
is silent.

**Proposed fix:** Add a short subsection to the developers' guide §"Invariant
validation" recording: (a) the six disk-evidence invariants are deliberate twins
between `disk_evidence.py` and the oracle, pinned by the disk-evidence agreement
suite; (b) after task 2.3.3 both sides read disk (disk-vs-disk on every
invariant), so neither side may be reverted to reading the spec; (c) refresh the
invariant table so invariant 5's status reflects the delivered disk-evidence
check rather than "deferred to task 2.3.2".

## Finding 5 — `chapter-NN` path convention is open-coded across production (severity: low)

**Category:** duplication

**Location:** `novel_ralph_skill/state/disk_evidence.py` line 83
(`_chapter_dir_name`), `novel_ralph_skill/state/wordcount.py` line 75,
`novel_ralph_skill/commands/_desloppify.py` lines 81, 106. The corpus side has
its own `chapter_dir_name` in `tests/working_corpus/_specs.py` line 186.

**Description:** The `chapter-{number:02d}` directory-name convention
(`state-layout.md` lines 54-56) is open-coded in at least four production sites:
`disk_evidence.py` defines a private `_chapter_dir_name`, while `wordcount.py` and
`_desloppify.py` inline the f-string `f"chapter-{number:02d}"`. A change to the
padding width or prefix (the layout doc caps it at two digits / 99 chapters)
would require touching every site, and there is no single production home for the
rule. This is pre-existing and broader than task 2.3.3, but the task added a fresh
consumer (`disk_evidence._chapter_dir_name`), so the spread is now worth flagging.

**Proposed fix:** Promote a single `chapter_dir_name(number)` helper into a shared
production module (e.g. alongside `recount_words` in
`novel_ralph_skill/state/wordcount.py`, or a small `layout` module) and have
`disk_evidence.py`, `wordcount.py`, and `_desloppify.py` call it. Leave the
corpus copy (`_specs.chapter_dir_name`) independent so the test corpus does not
import the production layout rule it cross-checks.
