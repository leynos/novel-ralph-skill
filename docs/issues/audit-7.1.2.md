# Post-merge audit — roadmap task 7.1.2

Audit of the codebase after roadmap task 7.1.2 ("Consolidate the
`CompiledComparison` absent-file projection prose into one authoritative
docstring") merged to `main` at commit `dcd58a8`. The task is a documentation-DRY
reroute (source: audit:4.1.2; carry-forward of audit-3.1.3 Finding 3): it makes
`compiled_matches_drafts`'s docstring the single authoritative description of the
three-valued `CompiledComparison` verdict and the two opposite absent-file
polarities, and trims the three consumers (`compile_is_current`,
`compile_consistent`/`_check_compiled_matches_drafts`, and `check_compiled`) to
a self-projection plus a cross-reference. No behaviour changes; `make all` is
reported green (1377 passed, 1 skipped).

Trail followed: `docs/roadmap.md` task 7.1.2 (and the §7.1 theme tasks 7.1.1,
7.1.3–7.1.5), `docs/novel-ralph-harness-design.md` §4.3/§5.4,
`docs/issues/audit-4.1.2.md`, `docs/issues/audit-3.1.3.md` (Finding 3),
`docs/issues/audit-3.1.1.md`, ADR-001 (deterministic/judgemental boundary),
`AGENTS.md` (quality gates, en-GB Oxford spelling), the `python-router` and
`en-gb-oxendict` skills, and `leta`/`sem` for navigation and history. Files
inspected: `novel_ralph_skill/state/compile_model.py`, `done_predicate.py`,
`disk_evidence.py`, `commands/_compile.py`, `state/__init__.py`, and the pinning
tests `tests/test_compile_model_seam.py`, `test_compiled_matches_drafts.py`,
`test_compile_check_agreement.py`, `test_disk_evidence.py`,
`test_done_predicate.py`.

The merged change is correct and the consolidation is real: the four docstrings
no longer carry four full copies of the absent-file projection table, every
consumer points at `compiled_matches_drafts`, and the behaviour is pinned by the
existing seam and agreement suites. The most important finding below is **a stale,
mismatched pre-existing `audit-7.1.2.md`** that this audit replaces (Finding 1);
the rest concern a **cross-reference target inconsistency** the consolidation
itself left (Finding 2), the **absence of a drift-guard** for the new
single-authoritative-docstring invariant (Finding 3), and two smaller
observations.

## Finding 1 — the pre-existing `audit-7.1.2.md` audited a different task entirely (severity: high)

**Category:** inconsistency

**Location:** `docs/issues/audit-7.1.2.md` (the file as it stood before this
audit, recorded by commit `65e5679`).

**Description:** The `audit-7.1.2.md` present on `main` before this step audited
a task titled "Implement per-novel `device-ledger.toml` enforcement" at commit
`d6d5f78`, covering a `novel_ralph_skill/ledger/` package, `desloppify --ledger`,
and ledger snapshot tests. None of that is roadmap task 7.1.2. The actual task
7.1.2 (`docs/roadmap.md` lines 2486–2513, merged at `dcd58a8`) is the
`CompiledComparison` docstring consolidation, which touches no ledger code. The
referenced commit `d6d5f78` is not reachable in this repository's history
(`git cat-file -t d6d5f78` returns a tree-shaped object, not the documented
commit). This is a roadmap-renumbering collision: a previous roadmap iteration's
"7.1.2" was the device-ledger task, and its audit file was never renamed when the
numbering changed, so the filename now points at the wrong work. A reader
consulting `audit-7.1.2.md` for the state of the compile-projection consolidation
would instead read about an unrelated ledger feature, and the stale file's own
findings (e.g. its "Finding 4", an MD012 breakage in `developers-guide.md`) no
longer reproduce — `make markdownlint` is green on `main`.

**Proposed fix:** Replace the stale file with this audit of the real task 7.1.2
(done by this step). Separately, the device-ledger audit content is not worthless:
its Findings 2/3 (rule-pack vs ledger `_coerce`/`_entries`/`_scan_*` duplication)
and its consolidation roadmap proposal are still live against today's
`novel_ralph_skill/ledger/` and `rulepack/` packages. Preserve that analysis by
re-homing it under the correct task number (the ledger task's *current* roadmap
id) rather than discarding it; otherwise a genuine cross-package duplication
finding is silently lost in the rename. Going forward, derive audit filenames from
the roadmap id at merge time so a renumber cannot orphan an audit.

## Finding 2 — the authoritative cross-reference target is spelled two different ways (severity: low)

**Category:** inconsistency

**Location:** `novel_ralph_skill/commands/_compile.py:34`, `:175`, `:186`
(`:func:`~novel_ralph_skill.state.compiled_matches_drafts``) versus
`novel_ralph_skill/state/done_predicate.py:37`, `:224`, `:234` and
`novel_ralph_skill/state/disk_evidence.py:197`, `:209`
(`:func:`~novel_ralph_skill.state.compile_model.compiled_matches_drafts``).

**Description:** The whole point of 7.1.2 is to route every consumer at one
authoritative docstring. Two of the three consumers do so through the canonical
defining-module path
(`novel_ralph_skill.state.compile_model.compiled_matches_drafts`), but
`check_compiled` and the `_compile.py` module docstring point at the re-export
path (`novel_ralph_skill.state.compiled_matches_drafts`). Both resolve at runtime
because `state/__init__.py` re-exports the symbol, but a consolidation that pins
a single authoritative home should reference that home consistently: the mixed
spelling weakens the "one canonical target" intent the task asserts, and if the
re-export were ever pruned the `_compile.py` references would dangle while the
others would not. The same re-export-vs-defining-module split applies to the
sibling references in `_compile.py` (e.g. `~novel_ralph_skill.state.CompiledComparison`).

**Proposed fix:** Normalise the three `_compile.py` references (and the sibling
`CompiledComparison`/`compile_is_current` mentions) to the defining-module path
`novel_ralph_skill.state.compile_model.*` so every consumer names the authoritative
home identically. Doc-only; no behaviour change. Fold into task 7.1.4/7.1.5 if
they touch these docstrings, or take as a trivial standalone edit.

## Finding 3 — no drift-guard prevents the consolidated prose from being re-duplicated (severity: low)

**Category:** test-gap

**Location:** `tests/test_compile_model_seam.py` (pins the seam behaviour but not
the docstring invariant); no test references the consolidated docstrings' text or
cross-references.

**Description:** This codebase pins single-source-of-truth invariants with
explicit drift-guard tests (for example the SKILL.md command contract at roadmap
6.3.7, the developers'-guide contract restatement at 6.3.9, and the corpus
invariant-name equality). The 7.1.2 consolidation establishes a comparable
invariant — *exactly one* authoritative copy of the absent-file projection table,
with the three consumers carrying only a self-projection plus a pointer — but
nothing guards it. A future edit could re-expand any consumer's docstring back to
a full projection table (re-introducing the precise duplication 7.1.2 removed) or
break a cross-reference, and the change would ship green: the behavioural suites
test the verdict, not the prose. The seam test exhaustively pins
`compile_is_current`'s truth table, which is excellent, but it does not assert the
documentation invariant the task delivers.

**Proposed fix:** Add a lightweight drift-guard (e.g. in
`test_compile_model_seam.py` or a new `test_compile_projection_docs.py`) asserting
that the authoritative phrase "authoritative" / "three-valued table" appears in
`compiled_matches_drafts.__doc__` and that each consumer's `__doc__`
(`compile_is_current`, `compile_consistent`, `_check_compiled_matches_drafts`,
`check_compiled`) contains a cross-reference to `compiled_matches_drafts` and does
*not* re-enumerate all three `CompiledComparison` members with both polarities.
This is judgement-call hardening — a textual guard can be brittle — so scope it
to the cross-reference presence (the load-bearing invariant) rather than the full
prose, mirroring the existing contract-restatement drift-guards.

## Finding 4 — `compile_consistent`'s docstring restates the full polarity rule the task meant to centralise (severity: low)

**Category:** docs-gap

**Location:** `novel_ralph_skill/state/done_predicate.py:213-261`
(`compile_consistent`).

**Description:** The roadmap Success criterion for 7.1.2 is that each consumer
"carry only a one-sentence self-projection pointing at the authoritative
docstring". `_check_compiled_matches_drafts` (disk_evidence.py) and
`check_compiled` (_compile.py) meet that bar closely. `compile_consistent`,
however, still spells out the full content-polarity rule in prose ("An absent
`manuscript/compiled.md` is `False` … a present one is `True` iff its bytes equal
the ordered draft concatenation and `False` otherwise"), plus the byte-compare
rationale and the soundness/Risk-R-STALE history. That is materially more than a
one-sentence self-projection, so a slice of the polarity prose the task aimed to
centralise still lives in a consumer. The retained history (B1 soundness, R-STALE)
is arguably worth keeping locally, so this is a soft deviation, not a defect.

**Proposed fix:** Trim `compile_consistent`'s docstring to its own polarity in one
sentence ("`compile_consistent` holds iff the verdict is `MATCHES` via
`compile_is_current`; absent and diverging compiles are both false") plus the
cross-reference it already carries, moving the absent/present-stale enumeration
to rely on the authoritative table. Keep a one-line note of the B1/R-STALE
provenance if the maintainers want the history local. Pair with Finding 3's
drift-guard so the trimmed shape is pinned. If the maintainers judge the retained
rationale load-bearing for the done-predicate reader, leave it and let it stand
as documentation of the trade-off.

## Finding 5 — the §7.1 theme will keep generating near-identical projection/cross-reference work (severity: low)

**Category:** similarity

**Location:** `docs/roadmap.md` §7.1 (tasks 7.1.3 `Reconciliation` payload
projection, 7.1.4 shared finding-outcome envelope skeleton, 7.1.5
`ENVELOPE_FIELD_ORDER`), against the pattern just executed by 7.1.1 and 7.1.2.

**Description:** Tasks 7.1.1 and 7.1.2 each extracted a single canonical
projection (the compile-currency predicate; the absent-file table) and rerouted
consumers through it with cross-referencing docstrings. Tasks 7.1.3–7.1.5 are the
same shape over the reconciliation payload and the envelope field order. The
repeated work is the per-consumer cross-reference wiring and its (currently
unguarded) documentation invariant — Findings 2 and 3 will recur once per theme
task unless the cross-reference convention and a drift-guard helper are settled
once. This is an observation about the theme's trajectory, not a defect in 7.1.2.

**Proposed fix:** Before 7.1.3 lands, settle one convention for "authoritative
docstring + consumer self-projection" — a fixed cross-reference path style (the
defining-module form from Finding 2) and a reusable drift-guard helper
(Finding 3) — and apply it across 7.1.3–7.1.5 so each later task inherits the
convention rather than re-deciding it. This is a process note for the root agent's
sequencing, captured in the proposed roadmap item below.

## Proposed roadmap items

Adding to the roadmap is reserved to the root agent; these are proposals only.

- **Re-home the orphaned device-ledger audit and pin audit filenames to roadmap
  ids.** The stale `audit-7.1.2.md` (Finding 1) carried live cross-package
  duplication findings (rule-pack vs ledger `_coerce`/`_entries`/`_scan_*`) under
  the wrong task number. Re-home that analysis under the ledger task's current
  roadmap id so the duplication finding is not lost, and derive future audit
  filenames from the roadmap id at merge time so a renumber cannot orphan an audit.
- **Settle the §7.1 "authoritative-docstring + consumer self-projection"
  convention once, with a drift-guard.** Findings 2, 3, and 5 show 7.1.1/7.1.2
  established a projection-consolidation pattern that 7.1.3–7.1.5 repeat, but the
  cross-reference path style is inconsistent and the single-authoritative-copy
  invariant is unguarded. A small task to fix the canonical cross-reference style
  and add a reusable docstring drift-guard helper, applied across the remaining
  §7.1 tasks, would stop the inconsistency and the test-gap recurring per theme
  task.
