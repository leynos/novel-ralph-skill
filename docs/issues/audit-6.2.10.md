# Post-merge audit: roadmap task 6.2.10

Audit of the codebase after roadmap task 6.2.10 ("Cross the installed-binary
command-agnostic error arms (exit 2 usage and exit 3 state) over a wheel",
commit `72a9b99`) merged to `main`. The task added
`tests/test_console_scripts_error_arms_e2e.py`, which exercises the runner's
two command-agnostic diagnostic arms — the usage error (exit 2) and the
state-or-input error (exit 3) — over an installed `novel-state` in both output
modes, closing the in-process-versus-binary asymmetry the 6.2.8 in-process
matrix left open. It also recorded that coverage in the harness design doc
(§4.2 commentary) and the developers' guide, and captured the execplan.

The task itself is test-and-docs only and is correct: the new e2e module mirrors
the existing installed-e2e fixtures and marks, the design-doc and
developers'-guide prose match the test, and the cited line ranges
(`runner.py:223-239` two-arm `try/except`) check out. No finding below is a
defect in 6.2.10's diff. The findings are pre-existing hygiene observations
surfaced while reading the command and state layers the new e2e drives; none
block the merge.

Sources relied on: `docs/issues/audit-6.2.8.md` and `docs/issues/audit-6.1.1.md`
(the prior duplication-by-copy-paste theme); `docs/roadmap.md` (completed tasks
2.2.2.2 — the single `working/state.toml` accessor — and 3.1.1.2 — the
`_chapter_dir_name` `chapter-NN` single source); `docs/novel-ralph-harness-
design.md` (§3.2 exit codes, §4.1 disk-authoritative counting, §4.2 done
predicate, §4.5 wordcount); `docs/adr-003-shared-interface-contract.md` (the
shared `run`/envelope contract); `docs/scripting-standards.md`; and `AGENTS.md`
(en-GB Oxford spelling, the 400-line module cap, the single-source-of-truth
stance). Code navigated with `leta` (`grep`/`refs`/`show`); history traced with
`sem`/`git show` over commit `72a9b99`. Skills consulted: `python-router`,
which routed to `python-data-shapes` (the path-helper boundary) and
`python-errors-and-logging` (the `FileNotFoundError`-is-benign read boundary).

## Finding 1: Two commands bypass the canonical `state_path()` accessor

- **Category:** inconsistency
- **Severity:** medium
- **Location:** `novel_ralph_skill/commands/_wordcount.py:130-131`
  (`source_state_and_drafts`) and
  `novel_ralph_skill/commands/_desloppify.py:198-199` (`_scan` chapter source).

Roadmap task 2.2.2.2 promoted a single `working/state.toml` accessor —
`novel_state.state_path()` (and `working_dir()`) — and routed `_check`, `init`,
and the two `_state_mutators` through it "so the path has a single home"
(roadmap lines 668-674). The `state_path()` docstring restates this: it is "the
single accessor every command routes through ... so the canonical `state.toml`
path is constructed in exactly one place", and `working_dir()` warns against
each caller "rebuilding `pathlib.Path(WORKING_DIR_NAME)`".

Both `_wordcount` (task 6.1.1) and `_desloppify` (task 5.1.2) were added after
2.2.2.2 and bypass the accessors, rebuilding the path inline:

```python
working_dir = pathlib.Path(WORKING_DIR_NAME)
state = _load_or_state_error(working_dir / "state.toml")
```

This re-spells both the `working/` root and the `state.toml` join the accessors
were created to centralise, so the invariant 2.2.2.2 established is now only
partially held: `novel-state`, the mutators, `_reconcile`, `_compile`, and
`_novel_done` route through the accessors, while `wordcount` and `desloppify`
do not. The two modules already import `_load_or_state_error` from
`novel_state`; they simply do not import `working_dir`/`state_path` beside it.

- **Proposed fix:** in both modules, import `working_dir` and `state_path` from
  `novel_ralph_skill.commands.novel_state` (as `_reconcile` already imports
  `_working_dir`/`_state_path` via `_state_mutators`) and replace the inline
  `pathlib.Path(WORKING_DIR_NAME)` / `... / "state.toml"` construction with
  `root = working_dir()` and `_load_or_state_error(state_path())`. Use `root`
  for the subsequent `manuscript/` joins so the working-root token is sourced
  once per call. This restores the single-home invariant without changing
  behaviour and lets `WORKING_DIR_NAME` drop from the two import lists.

## Finding 2: Three draft paths rebuild `chapter-NN` instead of `_chapter_dir_name`

- **Category:** duplication
- **Severity:** medium
- **Location:** `novel_ralph_skill/state/wordcount.py:75`
  (`_chapter_word_count`) and `novel_ralph_skill/commands/_desloppify.py:122`
  (`_chapter_text`); contrast `novel_ralph_skill/state/compile_model.py:154`,
  which does route through the helper.

`novel_ralph_skill/state/_disk_paths.py:19` defines `_chapter_dir_name(number)`
→ `f"chapter-{number:02d}"` as the single source for the `chapter-NN` layout;
roadmap task 3.1.1.2 even fixed reference pseudocode that "contradicts the
shipped `_chapter_dir_name`". `done_predicate.py`, `disk_evidence.py`, and
`compile_model.py` all import and call it. But two draft-reading helpers inline
the format string instead:

```python
draft = working_dir / "manuscript" / f"chapter-{number:02d}" / "draft.md"
```

`_chapter_text`'s own docstring acknowledges the coupling — "The path
derivation is the same `chapter-{number:02d}` convention `recount` uses, so the
two cannot disagree" — but enforces it by copy rather than by calling the shared
helper, so a future change to the zero-padding (or a switch to a different
layout) must be made in three places, and the docstring's "cannot disagree"
guarantee is only true by vigilance.

- **Proposed fix:** import `_chapter_dir_name` into `state/wordcount.py` and
  `commands/_desloppify.py` and replace the inline `f"chapter-{number:02d}"`
  segment with `_chapter_dir_name(number)`, matching `compile_model.py:154`.
  Update each docstring to say it derives the directory via `_chapter_dir_name`
  rather than restating the literal convention.

## Finding 3: `_chapter_word_count` and `_chapter_text` duplicate the read boundary

- **Category:** similarity
- **Severity:** low
- **Location:** `novel_ralph_skill/state/wordcount.py:41-83`
  (`_chapter_word_count`) and `novel_ralph_skill/commands/_desloppify.py:84-124`
  (`_chapter_text`).

The two helpers are near-identical: each joins the same
`working_dir/manuscript/chapter-NN/draft.md` path, reads it as UTF-8, treats a
`FileNotFoundError` as a benign undrafted chapter (returning `0` or `""`
respectively), and lets every other `OSError`/`UnicodeDecodeError` propagate
for exit-3 translation. They differ only in the final projection
(`len(text.split())` versus the raw text) and the benign-default value. The
benign-`FileNotFoundError`-but-propagate-everything-else rule is therefore
written out twice, with the subtle "why a broad `except OSError` is wrong"
comment duplicated in both bodies. This is the same draft-read boundary the
codebase already centralised for the structural checks in `disk_evidence.py`.

- **Proposed fix:** extract one shared reader beside the path helpers — e.g.
  `_disk_paths.read_chapter_draft(working_dir, number) -> str | None` returning
  the draft body or `None` when absent (the only benign read). Layer the two
  call sites on top: `_chapter_word_count` becomes
  `len((text := read...) .split()) if text is not None else 0` and
  `_chapter_text` returns `text or ""`. This collapses the duplicated
  fault-classification comment to one home and composes cleanly with Finding 2's
  `_chapter_dir_name` reuse (the new reader is the natural place to call it).

## Finding 4: `"manuscript"` / `"draft.md"` path segments are scattered literals

- **Category:** duplication
- **Severity:** low
- **Location:** `novel_ralph_skill/state/done_predicate.py:184,293`;
  `novel_ralph_skill/state/compile_model.py:105,151,154`;
  `novel_ralph_skill/state/disk_evidence.py:149,152,225`;
  `novel_ralph_skill/state/_disk_paths.py:32`;
  `novel_ralph_skill/state/wordcount.py:75`;
  `novel_ralph_skill/commands/_desloppify.py:122`.

The `"manuscript"` directory name and the `"draft.md"` filename are bare string
literals repeated across at least six modules. `_disk_paths.py` already owns the
`chapter-NN` segment via `_chapter_dir_name`, but the surrounding `manuscript/`
and `draft.md` segments of the same `state-layout.md` path are not centralised,
so the layout the design fixes in one place is spelled out in many. This is the
softest of the four findings — the literals are stable — but it is the residue
of the same layout-knowledge-by-copy pattern Findings 2 and 3 address.

- **Proposed fix:** as part of the Finding 3 extraction, give `_disk_paths.py`
  named segment constants (`MANUSCRIPT_DIR_NAME = "manuscript"`,
  `DRAFT_FILE_NAME = "draft.md"`) and a `chapter_draft_path(working_dir,
  number)` joiner, then route the draft-reading call sites through it. Leave the
  `done.flag`/`critic-notes.md`/`compiled.md` joins as a follow-on if the same
  treatment is wanted for them; scope the first pass to the draft path the three
  duplications above share so the change stays reviewable.
