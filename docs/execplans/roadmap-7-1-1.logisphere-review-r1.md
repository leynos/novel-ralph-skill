# Logisphere design review — roadmap 7.1.1 (round 1)

Adversarial pre-implementation review of
`docs/execplans/roadmap-7-1-1.md` (single-source the compile-currency
projection and the `compiled.md` path seam).

Verdict: **Proceed with conditions.** The refactor is structurally sound,
correctly scoped against audit-4.1.2 and the roadmap, and every load-bearing
source claim was verified against the tree. The blocking defects are confined
to the plan's *self-described success observables*: two grep commands in the
Purpose section overclaim and contradict the plan's own non-goal (docstring
prose is 7.1.2). Left as written, an implementer or auditor running those
commands verbatim would see false failures and might either be blocked or be
tempted to edit docstrings and stray into 7.1.2.

## Source verification (all confirmed against the worktree)

- Two `is CompiledComparison.MATCHES` sites exist exactly where claimed:
  `_compile.py:221`, `done_predicate.py:263`.
- Four `"manuscript" / "compiled.md"` code joins exist:
  `_compile.py:147`, `_novel_done.py:128`, `_novel_done.py:173`,
  `compile_model.py:105` (the internal read).
- `_COMPILED_REL` uses in `_compile.py`: lines 74, 156, 161, 165, 225, 229,
  240 (the plan's enumeration "156,161,165,225,229,234,240" maps correctly;
  234 is the second `"checked"` key).
- Detector polarity untouched: `disk_evidence.py:209` uses
  `is not CompiledComparison.DIVERGES` — correctly excluded (non-goal).
- `WORKING_DIR_NAME = "working"` (`_state_load.py:36`); `working_dir()` returns
  the bare `working/` segment, so the working-prefix asymmetry analysis (token
  is `working/manuscript/compiled.md`; the `Path` join must not double it) is
  correct.
- `COMPILED_REL` byte-value is pinned by `test_compile_check_unit.py:117,139`,
  `test_compile_unit.py:114`, `contract_drive_support.py:90`, and the snapshot
  suites, as claimed.
- `state/__init__.py` already re-exports the `compile_model` surface
  (import block 30-36; `__all__` carries `compiled_matches_drafts` etc.).
- Red-first is viable: no test currently imports the three new symbols.
- Module line caps: all four edited modules are well under 400
  (`compile_model.py` 179, `done_predicate.py` 337, `_compile.py` 273,
  `_novel_done.py` 173); `interrogate` fail-under 100 confirmed.
- audit-4.1.2 Findings 1/2 map exactly; Finding 3 (prose) = 7.1.2; Finding 4
  (race) = out of scope. Roadmap 7.1.1 names exactly the three predicate
  consumers the plan routes.
- No external-library (cuprum / Cyclopts / pytest-timeout / uv) behaviour is
  load-bearing: verified no new subprocess, flag, or import crosses a library
  boundary. The "no undecided external fork" claim holds.

## Blocking defects

1. **Purpose-section success grep contradicts the 7.1.2 non-goal (path
   literal).** Purpose (lines 59-63) asserts `git grep -n 'manuscript/compiled.md'`
   over `novel_ralph_skill/` will "resolve every hit to the new seam in
   `compile_model.py` (the literals no longer appear in `_compile.py` or
   `_novel_done.py`)". This is false: the slash-form path appears in
   **docstrings** at `_compile.py:5,110`, `_novel_done.py:164`, and
   `done_predicate.py:86,217`, which this task deliberately does not touch
   (prose consolidation is 7.1.2). The precise WI3 validation grep
   (`'"manuscript" / "compiled.md"'`, quoted code-join form) is correct and
   should be the stated observable; the Purpose-section claim must be narrowed
   to the code-join form or explicitly scoped to "code joins, not docstring
   prose".

2. **Purpose-section success claim contradicts the 7.1.2 non-goal (MATCHES
   references).** Purpose (lines 55-58) asserts "the only surviving
   `CompiledComparison.MATCHES` references are inside `compile_model.py`". False:
   `_compile.py:184,202` and `done_predicate.py:229-231` retain
   `CompiledComparison.MATCHES` `:attr:` references in docstring prose (7.1.2).
   The narrow WI3 grep `"is CompiledComparison.MATCHES"` (with leading `is`)
   is correct and unaffected; the loose Purpose-section claim about *all*
   `CompiledComparison.MATCHES` references must be restricted to the
   `is CompiledComparison.MATCHES` projection form.

## Advisory (non-blocking)

- **WI3 step 3 presupposes a non-existent import block.** `_novel_done.py`
  currently has no `compile_model`/`state` import (verified). The plan says
  "add `compiled_manuscript_path` to the module's `compile_model`/state import";
  there is no such block — a new import statement must be created. Reword to
  "add a new `from novel_ralph_skill.state import compiled_manuscript_path`
  import" so a novice is not hunting for a block that isn't there.

- **Dead-import pruning is correctly conditional.** After routing,
  `done_predicate.py` and `_compile.py` keep `CompiledComparison.MATCHES` only
  in docstrings (textual, not imports), so the `CompiledComparison` import
  becomes unused in both and the plan's "drop iff no other reference remains"
  guard is right. `make all` (Ruff F401) will catch it either way.

- **Idempotence of the seam test's red-first.** WI2 acknowledges WI1+WI2 may be
  committed together; the "temporarily remove a member, watch red, restore"
  dance is sound but should be recorded in `Progress`/`Surprises` so the
  red-first evidence survives compaction.

## Pre-mortem (Doggylump)

Most likely six-months-later incident: someone runs the Purpose-section grep
during a later audit, sees docstring hits in `_compile.py`/`_novel_done.py`,
concludes the refactor is "incomplete", and edits the docstrings to satisfy the
grep — silently doing 7.1.2's work and possibly desynchronizing the prose that
7.1.2 wants to consolidate authoritatively. Prevention: fix defects 1 and 2 so
the stated observables match the actual (correct) end state. Blast radius: low
(docs only), but it corrodes the audit trail. Signal missed: the Purpose grep
and the WI3 grep disagree, and only the WI3 form was validated against source.

Second scenario: the working-prefix asymmetry is the genuine structural hazard,
but the plan defends it well (two distinct seam members, a unit assertion that
`compiled_manuscript_path(Path("working")).as_posix() == COMPILED_REL`, and the
snapshot suites as backstop). No mitigation gap found.

## Alternatives checkpoint (Wafflecat)

Strongest alternative: collapse the path seam to a single member by having the
envelope derive its token from `compiled_manuscript_path(working_dir()).as_posix()`
rather than carrying a separate `COMPILED_REL` constant. Trade: removes one
member but reintroduces exactly the working-prefix coupling the plan's Decision
Log rejects — the envelope token is `working/...`-prefixed whereas the `Path`
is built from an already-`working/`-anchored dir, so the single-member form
needs an asymmetry-hiding transform. The plan's two-member split is the better
call; the alternative is viable but trades clarity for a spurious line saving.
The plan is on solid ground here.

## Conditions to clear before implementation

- Fix defect 1: narrow the Purpose-section path grep to the code-join form (or
  scope it explicitly to code joins, excluding docstring prose).
- Fix defect 2: restrict the Purpose-section MATCHES claim to the
  `is CompiledComparison.MATCHES` projection form.
- (Advisory) Reword WI3 step 3 to add a new import rather than extend a
  non-existent block.

Docs and skills relied on: `logisphere-design-review`; design doc §4.2/§4.3/§5.4;
`docs/issues/audit-4.1.2.md`; `docs/roadmap.md` 7.1.1; ADR-001, ADR-003;
AGENTS.md. Source verified directly in the worktree (`compile_model.py`,
`_compile.py`, `done_predicate.py`, `_novel_done.py`, `_state_load.py`,
`state/__init__.py`, `disk_evidence.py`, the cited tests).
