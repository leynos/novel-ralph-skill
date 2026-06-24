# Anchor the unresolved-BLOCKER resolution rule positionally and cover the false-clean direction

This ExecPlan (execution plan) is a living document. The sections `Constraints`,
`Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`, `Decision Log`,
and `Outcomes & Retrospective` must be kept up to date as work proceeds.

Status: DONE

## Purpose / big picture

The `novel-done` predicate is the harness's terminator: it exits `0` only when
the novel is genuinely finished, so an exit-`0` lie is the single worst failure
mode in the whole system. One clause, `no_unresolved_blockers`, currently
decides a `critic-notes.md` BLOCKER is *resolved* whenever the literal token
`[resolved]` appears **anywhere** on the line. That substring test is unsound
in the false-clean direction: a live blocker whose prose happens to quote
`[resolved]` — for example
`BLOCKER the ending still depends on the [resolved] issue in chapter 2` — is
silently declared clean, and `novel-done` reports the novel done while a real
BLOCKER stands. The false-clean direction is also **untested**: the corpus pins
only the false-dirty near-miss (a BLOCKER that mentions resolution *in prose
without the token* and correctly stays unresolved).

After this change, the resolution marker is **positional**: a BLOCKER line is
treated as resolved only when its stripped text *ends with* the `[resolved]`
token, so an incidental mid-line mention no longer clears the blocker. A novice
can observe the fix by writing
`BLOCKER the ending still depends on the [resolved] issue\n` into a chapter's
`critic-notes.md` on an otherwise-done tree and running `novel-done`: before
the change it exits `0` (the lie); after the change it exits `1` and the result
reports `no_unresolved_blockers` false. The genuinely-resolved tree
(`BLOCKER … [resolved]` as a trailing marker) still clears, and the existing
false-dirty near-miss stays unresolved. A new §1.3.2 corpus tree pins the
false-clean direction so the substring trap cannot return.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- `novel-done` remains read-only on every path: the predicate engine writes
  nothing to disk (ADR-001; design §3.3 puts `novel-done` in the read-only
  checker column). This task touches only in-memory line classification and
  test fixtures; it must not add any write.
- The six clause names and their design §4.2 order are fixed
  (`phase_is_done`, `final_pass_complete`, `all_chapters_flagged`,
  `knitting_gates_passed`, `compile_consistent`, `no_unresolved_blockers`).
  This task changes the *internal grammar* of one clause, not the clause set,
  its order, or the `DoneClauses` shape.
- The fault boundary is preserved exactly (ExecPlan D-FAULT, design §4.2): an
  absent `critic-notes.md` is benign-clean (`FileNotFoundError` absorbed);
  every other read fault (`PermissionError`, `UnicodeDecodeError`) propagates
  to the command layer's exit-`3` channel. The grammar change must not swallow
  or introduce any fault.
- The production rule and the corpus oracle must stay deliberate twins: the
  `tests/working_corpus/_done_predicate_oracle.py`
  `_notes_has_unresolved_blocker` twin re-implements the grammar
  *independently* of the production constants (so a copy-paste cannot mask a
  drift) yet must agree with the production clause on every corpus tree. Both
  sides change together.
- The two existing BLOCKER corpus specs stay green and semantically unchanged:
  `DONE_PREDICATE_RESOLVED_BLOCKER` (trailing `[resolved]`) still clears, and
  `DONE_PREDICATE_NEAR_MISS_BLOCKER` (prose mention, no token) stays unresolved.
- No source file exceeds 400 lines (AGENTS.md). Prose, comments, and commit
  messages use en-GB Oxford spelling (`-ize`/`-yse`/`-our`).
- `done_predicate.py` reads no outline prose and iterates the **manifest**
  (`state.chapters`), unchanged here (design §4.3; D-CLAUSES).

## Tolerances (exception triggers)

- Scope: this is a tightly-bounded soundness fix. If the implementation needs to
  touch more than 6 files or more than ~150 net lines, stop and escalate — the
  task has been mis-scoped.
- Grammar ambiguity: the success criterion says "anchor … to a positional marker
  (or a more precise grammar / a structured marker)". This plan selects the
  *trailing-marker* grammar (D-BLOCKER-POSITIONAL below) and justifies why a
  heavier structured-marker grammar is out of scope. If review rejects the
  trailing-marker grammar, **escalate** with the trade-offs rather than
  silently widening the rule (matching the 3.1.1 D-BLOCKER escalation
  instruction).
- Interface: `no_unresolved_blockers(state, working_dir)` and
  `_contains_unresolved_blocker(notes_path)` keep their signatures and return
  types. If a signature must change, stop and escalate.
- Dependencies: no new external dependency. If one seems required, stop and
  escalate.
- Iterations: if the done-predicate or working-corpus suites still fail after 3
  focused attempts, stop and escalate.
- Format escalation: if the actual critic-notes format
  (`skill/novel-ralph/references/critic-personas.md` — `## BLOCKER` section
  headers and `### B1 — label` finding headers, with **no** documented
  `[resolved]` token) is judged to make the line-prefix grammar itself wrong,
  stop and escalate rather than rewriting the grammar to parse the section
  format — that is a larger redesign than this low-severity step-task.

## Risks

- Risk: The chosen trailing-marker grammar accidentally changes the verdict on
  one of the two existing BLOCKER corpus specs, breaking the "keep the
  near-miss corpus spec green" success criterion. Severity: medium ·
  Likelihood: low Mitigation: Both existing notes are confirmed compatible by
  inspection —
  `RESOLVED_BLOCKER_NOTE = "BLOCKER the pacing sagged in the middle [resolved]\n"`
  ends with the token (stays clean); `UNRESOLVED_BLOCKER_NOTE` and
  `NEAR_MISS_BLOCKER_NOTE` contain no token (stay unresolved). Work item W1
  adds a failing false-clean test *before* the grammar change (red/green), and
  the existing two specs run unchanged through the corpus cross-check.

- Risk: The production constant and the independently-re-spelled corpus oracle
  drift, so the cross-check passes by coincidence rather than by agreement.
  Severity: medium · Likelihood: low Mitigation: The oracle is *deliberately* a
  re-spelling, and the corpus cross-check test pins it equal to production on
  every corpus tree; W3 updates both in the same commit and the cross-check
  fails if they disagree on the new false-clean tree.

- Risk: A "positional" reading that anchors on `startswith` only (e.g. "the line
  starts with BLOCKER and the token is *anywhere after the first word*") is
  still defeatable. Severity: high · Likelihood: low Mitigation:
  D-BLOCKER-POSITIONAL pins the marker to the *end* of the stripped line
  (`rstrip().endswith(_RESOLVED_TOKEN)`), which the mid-line counter-example
  cannot satisfy; W2's Hypothesis property asserts that any BLOCKER line with
  the token strictly mid-line (token followed by non-whitespace text) stays
  unresolved.

- Risk: Case/format variants (`RESOLVED`, `(resolved)`) named in the roadmap
  remain mis-classified. Severity: low · Likelihood: medium Mitigation: This
  step-task's success criteria scope the fix to the false-clean positional
  defect plus a corpus near-miss; broader case-insensitive or
  alternative-spelling handling is **explicitly out of scope** and recorded in
  the Decision Log (D-BLOCKER-SCOPE) and the developers'-guide caveat as a
  known, documented limitation in *both* directions, so reviewers see the
  boundary rather than a silent gap.

## Progress

- [x] W1 — Pin the false-clean direction with a failing unit test (red). Folded
  into W2 per the default: `test_incidental_resolved_mention_stays_unresolved`
  was added unmarked, observed red against the substring rule
  (`assert True is False`), then turned green by the same commit.
- [x] W2 — Add the failing false-clean unit test, anchor the resolution token
  positionally in the production engine (green), and add the property test.
  Commit `96fa6dc`. `make all` green (715 passed, 1 skipped). The one-line
  grammar change (`not stripped.endswith(_RESOLVED_TOKEN)`) and the
  `test_blocker_resolution_is_positional` Hypothesis property both landed; the
  two existing BLOCKER tests (`test_resolved_blocker_is_clean`,
  `test_no_unresolved_blockers_clean_and_blocking`) re-ran green unchanged.
- [x] W3 — Add the false-clean §1.3.2 corpus tree, update the corpus oracle
  twin, widen `blocker_edge_trees` to a 3-tuple with both consumers in lockstep
  (B1), and extend the corpus/BDD coverage. Commit `3aa248f`. `make all` green
  (716 passed, 1 skipped). The incidental tree, oracle twin, fixture 3-tuple,
  both consumer updates, and the new BDD scenario all landed; no snapshot was
  added because the exit-1 + `no_unresolved_blockers:false` envelope shape is
  already pinned by the `no_unresolved_blockers` failer snapshot and the BDD
  `Then` assertions (AGENTS.md "avoid snapshot-only coverage").
- [x] W4 — Reconcile the documentation (developers' guide, done-conditions
  reference, design note) to the positional grammar and both failure directions.
  The developers' guide BLOCKER-format paragraph, the `done-conditions.md`
  `contains_unresolved_blocker` reference, and the design §4.2
  implementation-status note now describe the trailing-positional rule and both
  failure directions (false-dirty prose mention; out-of-scope case variants).
  `make markdownlint`, `make nixie`, and `make all` all green.

## Surprises & discoveries

- Observation: The *actual* critic output format is section-structured, not
  line-prefixed. Evidence: `skill/novel-ralph/references/critic-personas.md`
  lines 83–144 specify the strict output as `## BLOCKER` headers and
  `### B1 — <label>` finding headers, and define **no** `[resolved]` token
  anywhere. Impact: The `BLOCKER`-line-prefix + `[resolved]` grammar is a
  pragmatic ExecPlan invention (3.1.1 D-BLOCKER), not the critic's documented
  format. This task tightens that invention's soundness without re-deriving it
  from the section format; the mismatch between the predicate grammar and the
  critic format is recorded as a known limitation (D-BLOCKER-SCOPE) so a later,
  larger task can reconcile them.
- Observation: This task is entirely in-process Python with no subprocess
  execution. Evidence: `grep` for `cuprum`/`subprocess`/`catalogue`/`sh.` across
  `novel_ralph_skill/state/done_predicate.py`,
  `tests/working_corpus/_done_predicate_specs.py`, and
  `tests/working_corpus/_done_predicate_oracle.py` returns nothing. Impact: The
  scripting-standards `cuprum`/catalogue/allowlisting conventions and the
  locked external-library behaviours (Cyclopts `--help`/`--version`, `uv run`,
  pytest-timeout under xdist) are **not load-bearing** for this change; no
  firecrawl/cuprum-API research is required and none is asserted from memory.
  The only external libraries this plan leans on — `pytest`, `pytest-bdd`,
  `hypothesis`, `syrupy` — are already used by the existing
  `tests/test_done_predicate.py` (`from hypothesis import given, settings`,
  line 27) and the `novel-done` BDD/snapshot suites, so the plan reuses
  established in-repo patterns rather than new library surface.

## Decision log

- Decision (D-BLOCKER-POSITIONAL): A BLOCKER line is *resolved* iff its stripped
  text starts with `BLOCKER` (case-sensitive, unchanged) **and ends with** the
  `[resolved]` token, i.e. `stripped.endswith(_RESOLVED_TOKEN)` after the
  existing `.strip()`. An incidental mid-line mention no longer clears the
  blocker. Rationale: This is the smallest grammar that makes the clause sound
  in the false-clean direction while keeping both existing corpus specs green
  (the resolved note ends with the token; the unresolved and near-miss notes do
  not contain it). It treats the token as a *trailing marker the loop appends
  when it closes a blocker*, which matches the existing resolved-note shape. A
  heavier "structured marker" (e.g. a dedicated `## RESOLVED` section, or a
  per-finding `[resolved B1]` back-reference) would be sounder still but
  requires parsing the critic section format — out of scope for a low-severity
  step-task and a larger redesign than the success criteria call for.
  Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-SCOPE): Case and alternative-spelling variants
  (`RESOLVED`, `(resolved)`) named in the roadmap stay **out of scope** for
  this task and remain documented limitations. Rationale: The success criteria
  scope the fix to the positional false-clean defect plus one corpus near-miss.
  Widening to case-insensitive or alternative-spelling matching changes the
  resolution *vocabulary*, which is a separable decision the field critic
  format does not yet pin. Recording it as a documented limitation in *both*
  directions (false-dirty prose mentions and the now-closed false-clean
  mid-line mention) keeps the boundary visible without silently widening the
  rule. If review wants the variants handled now, escalate per the Tolerances
  rather than widening silently. Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-NO-NETWORK): No firecrawl/cuprum research underpins this
  plan. Rationale: the change is a pure in-process line-classification fix plus
  test fixtures; the verified load-bearing facts are the in-repo grammar, the
  existing corpus specs, and the critic-personas format, all cited by path and
  line. Date/Author: 2026-06-24, planning agent.

- Decision (D-BLOCKER-EDGE-ARITY): The `blocker_edge_trees` fixture grows from a
  2-tuple `(resolved, near_miss)` to a 3-tuple
  `(resolved, near_miss, incidental)`, and both consumers in
  `tests/test_working_corpus_done_predicate.py` are edited in the same W3
  commit: `test_blocker_edges` unpacks three and asserts the incidental tree
  fails on exactly `no_unresolved_blockers`; `test_blocker_oracle_twin_agrees`
  keeps its `cases.extend(...)` (length-agnostic) and only updates the
  parameter annotation. Rationale: a position-keyed 3-tuple is the minimal
  change that keeps both existing consumers working and adds the incidental
  tree to the cross-check; a name-keyed mapping was considered but rejected as
  it would force a larger rewrite of both consumers for no soundness gain. This
  resolves the round-1 blocking point B1 (the round-1 plan instructed "extend
  `blocker_edge_trees`" without naming the consumer edits, which would have
  broken `test_blocker_edges`'s two-element unpack and the type annotations,
  failing the W3 `make all` gate). Date/Author: 2026-06-24, planning agent.

## Outcomes & retrospective

All four work items landed against the purpose. The production grammar now reads
`stripped.startswith(_BLOCKER_PREFIX) and not stripped.endswith(_RESOLVED_TOKEN)`,
so a live BLOCKER quoting `[resolved]` mid-line is reported unresolved while a
trailing-marker resolution still clears; the oracle twin mirrors it. The
false-clean direction is pinned three ways — a unit test, a Hypothesis property,
a §1.3.2 corpus tree — plus a `novel-done` BDD scenario, and the existing
false-dirty near-miss and genuinely-resolved specs run unchanged. `make all` is
green at HEAD (716 passed, 1 skipped); markdownlint and nixie pass for the doc
changes.

Commits: `96fa6dc` (W1+W2, fold), `3aa248f` (W3),
plus the W4 documentation commit.

Deviation (recorded): `make fmt`'s `mdformat-all` step reflows every tracked
markdown file in the repository, not just the edited ones — the well-known
spurious churn this repo's stash history documents across many branches. For W4
the churn (130+ unrelated `docs/` and `skill/` files) was stashed away and only
the three intended documentation edits were re-applied by hand, so the W4 commit
carries no collateral reflow. `make markdownlint` + `make nixie` + `make all`
were run directly (not via `make fmt`) to gate the markdown without
re-triggering the churn. One pre-existing over-length line in this execplan's
W3 step was wrapped into a fenced `python` block to satisfy MD013.

## Context and orientation

The repository builds the `novel-ralph` skill harness: a set of deterministic,
read-only checkers and write-once mutators over a `working/` directory tree and
a typed `state.toml`. `novel-done` is the terminator checker. This plan and the
current working tree are the only inputs required.

Key files for this task (full repository-relative paths):

- `novel_ralph_skill/state/done_predicate.py` — the pure per-clause predicate
  engine (design §4.2). The relevant parts are the module-level constants
  `_BLOCKER_PREFIX = "BLOCKER"` and `_RESOLVED_TOKEN = "[resolved]"` (around
  lines 60–68), the helper `_contains_unresolved_blocker(notes_path)` (around
  lines 274–293), and the clause `no_unresolved_blockers(state, working_dir)`
  (around lines 296–311). The current resolution test is
  `stripped.startswith(_BLOCKER_PREFIX) and _RESOLVED_TOKEN not in stripped` —
  the `not in` substring test is the unsound part.
- `tests/test_done_predicate.py` — the unit + property suite. It already imports
  `from hypothesis import HealthCheck, given, settings` and
  `from hypothesis import strategies as st` (lines 27–28) and exercises the
  clause in `test_no_unresolved_blockers_clean_and_blocking`,
  `test_resolved_blocker_is_clean`, and
  `test_undecodable_critic_notes_propagates` (around lines 240–268).
- `tests/working_corpus/_done_predicate_specs.py` — the §1.3.2 corpus specs.
  The BLOCKER note bodies are `RESOLVED_BLOCKER_NOTE`,
  `UNRESOLVED_BLOCKER_NOTE`, and `NEAR_MISS_BLOCKER_NOTE` (lines 60–72); the
  trees are `DONE_PREDICATE_RESOLVED_BLOCKER` and
  `DONE_PREDICATE_NEAR_MISS_BLOCKER` (lines 156–161).
  `_note_on_first_chapter(spec, note)` (lines 127–130) attaches a note body to
  the first chapter of a base tree.
- `tests/working_corpus/_done_predicate_oracle.py` — the deliberate corpus-side
  twin. `_BLOCKER_PREFIX`/`_RESOLVED_TOKEN` are re-spelled independently (lines
  34–35) and `_notes_has_unresolved_blocker(notes_path)` (lines 58–66)
  re-implements the same substring rule. It must change in lockstep with
  production.
- `tests/working_corpus/__init__.py` — re-exports the corpus specs, note
  constants, and the oracle `no_unresolved_blockers` twin (the `__all__` and
  the imports around lines 31–115). A new spec/constant must be added here too.
- `tests/corpus_done_predicate_fixtures.py` — the pytest fixtures
  (`blocker_edge_trees`, `oracle_no_blockers`) that build the BLOCKER edge
  trees and expose the oracle twin (around lines 91–182). The
  `blocker_edge_trees` fixture (lines 91–115) is typed
  `cabc.Callable[[], tuple[Path, Path]]` and its inner `_build` returns the
  two-element `(resolved_working, near_miss_working)` tuple. Its **two**
  consumers, both in `tests/test_working_corpus_done_predicate.py`, destructure
  exactly two elements: `test_blocker_edges` (lines 90–97) does
  `resolved, near_miss = blocker_edge_trees()`, and
  `test_blocker_oracle_twin_agrees` (lines 123–136) does
  `cases.extend(blocker_edge_trees())`. W3 changes all three together.
- `tests/test_working_corpus_done_predicate.py` — the corpus cross-check suite
  that drives `blocker_edge_trees`: `test_blocker_edges` (lines 90–97) asserts
  the per-tree verdict, and `test_blocker_oracle_twin_agrees` (lines 123–136)
  pins the oracle twin equal to production
  (`oracle_no_blockers(working) == no_unresolved_blockers(state, working)`) on
  every BLOCKER edge tree.
- `tests/features/novel_done.feature` and `tests/steps/novel_done_steps.py` —
  the behavioural suite; the `no_unresolved_blockers` clause already appears in
  the per-clause failer Scenario Outline (feature line 28). The existing
  `single_failer_tree` step (`novel_done_steps.py` lines 89–98) is keyed off
  `DONE_PREDICATE_FAILERS[clause]`, **not** an arbitrary tree-by-name, and the
  new incidental tree is *not* a member of `DONE_PREDICATE_FAILERS`, so W3 must
  add a new Given step (or a new dict entry), not reuse the failer step.

Terms of art, defined:

- "BLOCKER" — the most severe critic finding; a chapter with a live BLOCKER is
  not done (design §4.2; `critic-personas.md`).
- "false-clean" — the predicate reporting a clause *satisfied* (clean) when it
  is
  not; here, declaring a live-BLOCKER tree done. This is the "exit-0 lie".
- "false-dirty" — the opposite error: declaring a clean tree not-done. The
  existing near-miss pins this direction.
- "positional marker" — a token whose *position* on the line (here, the end)
  carries meaning, so an incidental occurrence elsewhere does not trigger the
  rule.
- "oracle twin" — a test-side re-implementation of a production read, written
  independently and pinned equal to production on every corpus tree, so the two
  cannot drift unnoticed.
- "§1.3.2 corpus" — the working-tree corpus under `tests/working_corpus/`; the
  design's §1.3.2 corpus discipline requires each behaviour be pinned by a
  concrete tree.

Skills to load before touching code: `python-router` (it routes to
`python-errors-and-logging` for the fault-boundary discipline and
`python-data-shapes`/`python-types-and-apis` for the frozen `DoneClauses`
shape), then `python-testing` for the pytest/pytest-bdd/syrupy layering and
`python-verification` to confirm Hypothesis is the right adversary (it is — a
positional grammar with a clear invariant over generated lines), which routes
to the `hypothesis` skill for the property test. Use `leta` (`leta show`,
`leta refs`, `leta grep`) for navigation and `sem` for history. No Rust, no
markdown-diagram, no scripting/`cuprum` skills are relevant.

## Plan of work

Four atomic, independently committable, gate-passable work items, in order.
Each follows red → green → refactor/docs and ends with its own validation.

### W1 — Pin the false-clean direction with a failing unit test (red)

Implements: design §4.2 (`no_unresolved_blockers` soundness); roadmap 3.1.4
success criterion "a live BLOCKER line that incidentally contains `[resolved]`
is reported as unresolved"; `docs/issues/audit-3.1.1.md` Finding 3.

Read first: design §4.2; the audit Finding 3 description; the existing
`test_resolved_blocker_is_clean` and
`test_no_unresolved_blockers_clean_and_blocking` in
`tests/test_done_predicate.py`. Load: `python-router` → `python-testing`.

Add one unit test to `tests/test_done_predicate.py`, beside the existing
BLOCKER tests, named `test_incidental_resolved_mention_stays_unresolved`. It
writes
`BLOCKER the ending still depends on the [resolved] issue in chapter 2\n` into
the first chapter's `critic-notes.md` on the all-hold tree and asserts
`no_unresolved_blockers(state, working) is False`. Under the current substring
rule this test **fails** (the clause wrongly returns `True`); that is the red
state W2 turns green. Do not change production code in W1.

Tests this work item adds: the one failing unit test above (unit). No BDD,
property, snapshot, or e2e change in W1 — those land in W2/W3 where the green
fix and corpus tree exist.

Selected approach (round-1 advisory A2): **fold W1 into W2** by default. The
fix is a one-line soundness change, and the repo convention lands the failing
test and its fix in the same diff where the commit gate would otherwise reject
a red suite. So add `test_incidental_resolved_mention_stays_unresolved`
**unmarked** as the first edit of the W2 commit, confirm it fails against the
current substring rule (run `make test` once and observe the red before
applying the production change in the same working tree), then apply the
positional grammar so the same commit turns it green. This satisfies AGENTS.md
("Bug fixes include a failing test before the fix") via the verified
red-then-green transition within one commit, without the `xfail` marker churn.

Alternative (only if a reviewer explicitly wants a recorded red commit): keep
W1 as its own commit and mark the test
`@pytest.mark.xfail(strict=True, reason="false-clean BLOCKER fixed in W2")`
(repo precedent: `tests/test_novel_state_mutators.py:17`,
`tests/test_working_corpus.py:523`) so the gate passes on a recorded
expected-failure; W2 then removes the marker. Do not default to this heavier
path; choose it deliberately, and escalate per Tolerances "Iterations" only if
a gate cannot pass.

Validation (when folded): the verified red-then-green transition is shown
inside the W2 `make all`; there is no standalone W1 commit. Validation
(alternative path): `make test` shows the xfailing test, suite green, committed
on its own.

### W2 — Anchor the resolution token positionally and add the property test (green)

Implements: design §4.2; roadmap 3.1.4 success ("a genuinely resolved blocker
still clears"); audit Finding 3 proposed fix (D-BLOCKER-POSITIONAL).

Read first: D-BLOCKER-POSITIONAL above; the existing
`_contains_unresolved_blocker` docstring (it currently cites the substring rule
and must be reworded to the trailing-marker rule); the `python-verification`
skill to confirm Hypothesis, then the `hypothesis` skill. Load: `python-router`
→ `python-errors-and-logging` (preserve the fault boundary) and
`python-testing` → `hypothesis`.

In `novel_ralph_skill/state/done_predicate.py`:

1. Change the per-line test in `_contains_unresolved_blocker` from
   `stripped.startswith(_BLOCKER_PREFIX) and _RESOLVED_TOKEN not in stripped`
   to a positional form: the line is an *unresolved* blocker iff
   `stripped.startswith(_BLOCKER_PREFIX) and not stripped.endswith(_RESOLVED_TOKEN)`.
   (Because `stripped` is already `line.strip()`, `endswith` matches a
   trailing token with no further trailing whitespace; the existing resolved
   note ends exactly with `[resolved]`.)
2. Update the module-level comment on `_RESOLVED_TOKEN` (lines ~60–67) and the
   `_contains_unresolved_blocker` docstring to describe the **trailing
   positional** rule and cite D-BLOCKER-POSITIONAL, replacing the "does not
   contain" wording. Keep the `# noqa: S105` rationale.
3. Do **not** touch the fault boundary: the `try/except FileNotFoundError`
   stays; only the per-line predicate changes.

Then in `tests/test_done_predicate.py`:

1. Remove the `xfail` marker added in W1 (or, if W1 was folded in, add the test
   here unmarked); it now passes.
2. Add a Hypothesis property test, `test_blocker_resolution_is_positional`,
   using the already-imported `given`/`st`. Per the `hypothesis` skill's
   filtering-trap guidance, **construct** valid inputs rather than `.filter()`
   them, so the property cannot flake on an adverse example (round-1 advisory
   A1). Concretely:
   - Draw `prefix` and `suffix` from `st.text(...)` constrained to printable
     characters that **exclude newlines and the literal `[`** (so neither field
     can accidentally introduce a `[resolved]` token or split the line). The
     simplest safe alphabet is
     `st.text(alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7e,
     blacklist_characters="[]\n"), max_size=40)`; this guarantees neither field
     contains the token and neither contains a newline.
   - False case (token strictly mid-line, stays unresolved): build the line as
     `f"BLOCKER {prefix} {_RESOLVED_TOKEN} {suffix}X"`, appending a fixed
     non-space sentinel `X` so the line, after `.strip()`, provably **does not**
     end with `[resolved]` regardless of whether `suffix` is empty or
     whitespace-only. Assert the clause is `False`.
   - True case (token trailing, clears): build the line as
     `f"BLOCKER {prefix} {_RESOLVED_TOKEN}"`; after `.strip()` this ends exactly
     with the token. Assert the clause is `True`.
   Constructing the sentinel-terminated false-case line removes the whitespace
   flip the production `line.strip().endswith(...)` rule would otherwise expose
   (A1 (a)/(b)/(c)); the alphabet constraint removes the newline-split and
   token-collision traps. Mirror the existing `@settings(...)`/`@given(...)`
   style already in the file (around lines 201–206); add
   `suppress_health_check` only if the existing tests need it. This is the
   invariant the `python-verification` skill confirms Hypothesis owns:
   *position of the token determines resolution, content does not*.

Tests this work item adds/updates: the W1 unit test now green (unit); the new
positional property test (property/Hypothesis); the existing
`test_resolved_blocker_is_clean` and
`test_no_unresolved_blockers_clean_and_blocking` re-run unchanged to prove the
genuinely-resolved and genuinely-blocking cases still hold.

Validation: `make test` — the false-clean unit test and the property test pass,
all prior done-predicate tests stay green. Then the full `make all` (build,
check-fmt, lint, typecheck, test) before commit.

### W3 — Add the false-clean §1.3.2 corpus tree, update the oracle twin, and extend corpus/BDD coverage

Implements: design §4.2; roadmap 3.1.4 success ("the false-clean direction is
pinned by a new §1.3.2 corpus near-miss"); the twin-discipline constraint;
audit Finding 3 ("add a corpus near-miss whose body is `BLOCKER … [resolved] …`
mid-sentence yet remains unresolved").

Read first: the existing BLOCKER specs and `_note_on_first_chapter` in
`_done_predicate_specs.py`; the oracle twin in `_done_predicate_oracle.py`; the
`blocker_edge_trees`/`oracle_no_blockers` fixtures in
`tests/corpus_done_predicate_fixtures.py`; the corpus cross-check test that
pins oracle-equals-production (`tests/test_working_corpus.py` and the BLOCKER
assertions in `tests/test_done_predicate.py` that drive `blocker_edge_trees`).
Load: `python-router` → `python-testing`.

1. In `tests/working_corpus/_done_predicate_specs.py`, add a note constant
   `INCIDENTAL_RESOLVED_BLOCKER_NOTE` whose body is a live BLOCKER quoting the
   token mid-sentence, e.g.
   `"BLOCKER the ending still depends on the [resolved] issue in chapter 2\n"`,
   with a comment citing D-BLOCKER-POSITIONAL and audit Finding 3. Add a tree

   ```python
   DONE_PREDICATE_INCIDENTAL_RESOLVED_BLOCKER = _note_on_first_chapter(
       DONE_PREDICATE_ALL_HOLD, INCIDENTAL_RESOLVED_BLOCKER_NOTE
   )
   ```

   beside the existing `…_NEAR_MISS_BLOCKER`. This tree must remain *not done*
   on exactly the `no_unresolved_blockers` clause and be §5.2/§5.4-coherent on
   every other clause (it is, since it differs from the all-hold tree only in
   the note body, like the existing near-miss).
2. Export the new constant and tree from `tests/working_corpus/__init__.py`
   (imports and `__all__`).
3. Update the **oracle twin** in `_done_predicate_oracle.py`:
   `_notes_has_unresolved_blocker` must adopt the same trailing-positional rule
   (`stripped.endswith(_RESOLVED_TOKEN)`), re-spelled independently of
   production. The corpus cross-check that pins the oracle equal to
   `done_predicate.no_unresolved_blockers` then exercises the new incidental
   tree and proves both sides agree it is unresolved (this is the constraint
   that the twin not drift).
4. Extend `tests/corpus_done_predicate_fixtures.py`'s `blocker_edge_trees`
   factory to also build the incidental-resolved tree, and **update its two
   consumers in lockstep** so the cross-check genuinely covers the new tree and
   `make all` stays green (this is the round-1 blocking gap B1). The fixture is
   typed `cabc.Callable[[], tuple[Path, Path]]` with two destructuring
   consumers, so a silent return-arity bump breaks them. Make exactly these
   mechanical edits:
   1. In `tests/corpus_done_predicate_fixtures.py`, widen the
      `blocker_edge_trees` fixture's annotated return type from
      `cabc.Callable[[], tuple[Path, Path]]` to
      `cabc.Callable[[], tuple[Path, Path, Path]]` (both the decorator's return
      annotation and the docstring's `Returns` type), rename the inner `_build`
      return annotation to `tuple[Path, Path, Path]`, and add a third
      sub-directory build:
      `incidental = tmp_path / "incidental"; incidental.mkdir()` then append
      `wc.build_working_tree(wc.DONE_PREDICATE_INCIDENTAL_RESOLVED_BLOCKER,
      incidental)` as the third tuple element after `near_miss`. Update the
      docstring's callable signature line to
      `() -> (resolved_working, near_miss_working, incidental_working)`.
   2. In `tests/test_working_corpus_done_predicate.py`, update
      `test_blocker_edges` (lines 90–97): change the parameter annotation to
      `cabc.Callable[[], tuple[Path, Path, Path]]`, change the unpack to
      `resolved, near_miss, incidental = blocker_edge_trees()`, and **assert the
      third tree**: `incidental = _evaluate(incidental_working)` then
      `assert incidental.failed_clause_names == ("no_unresolved_blockers",)`
      (the incidental tree differs from all-hold only in the note body, so it
      fails on exactly that clause). Keep the existing resolved/near-miss
      assertions.
   3. In the same file, update `test_blocker_oracle_twin_agrees` (lines
      123–136): change its `blocker_edge_trees` parameter annotation to
      `cabc.Callable[[], tuple[Path, Path, Path]]`. Its body uses
      `cases.extend(blocker_edge_trees())`, which consumes any tuple length
      unchanged, so the loop now exercises the incidental tree automatically and
      pins `oracle_no_blockers(incidental) == no_unresolved_blockers(state,
      incidental)` — proving the twin agrees the incidental tree is unresolved.
      No body edit beyond the annotation is required here.

   With these three edits the cross-check provably covers the incidental tree
   and the W3 commit passes its own `make all` gate, closing B1.
5. Add a BDD scenario to `tests/features/novel_done.feature`: a Scenario named
   e.g. "an incidental [resolved] mention does not clear a live BLOCKER" that
   Given a working tree whose first chapter's `critic-notes.md` is the
   incidental note, When `novel-done` runs, Then it exits 1 and the result
   reports `no_unresolved_blockers` false. The existing `single_failer_tree`
   step (`tests/steps/novel_done_steps.py` lines 89–98) is keyed off
   `DONE_PREDICATE_FAILERS[clause]` and the incidental tree is **not** a member
   of `DONE_PREDICATE_FAILERS`, so the failer step does **not** generalise. Add
   a dedicated Given step in `tests/steps/novel_done_steps.py` that materialises
   `DONE_PREDICATE_INCIDENTAL_RESOLVED_BLOCKER` via `wc.build_working_tree`
   (matching the existing tree-build step pattern in that file), wired to the
   new Scenario's Given phrase. Do not extend `DONE_PREDICATE_FAILERS`, which
   is the one-clause-per-failer dict and the incidental tree is a deliberate
   twin of the `no_unresolved_blockers` failer, not a new failer.

Tests this work item adds/updates: the new corpus spec/tree (corpus fixture);
the `blocker_edge_trees` fixture widened to a 3-tuple with its two consumers
(`test_blocker_edges`, `test_blocker_oracle_twin_agrees`) updated in lockstep
per step 4; `test_blocker_edges` now asserts the incidental tree fails on
exactly `no_unresolved_blockers`; the oracle-equals-production cross-check
(`test_blocker_oracle_twin_agrees`) now covering the incidental tree
(property-style corpus invariant); the new BDD scenario (behavioural). If the
`novel-done` snapshot suite (`tests/test_novel_done_snapshots.py`) snapshots a
per-clause-failer result envelope, add/extend the snapshot for the incidental
tree so the exit-1 + `no_unresolved_blockers:false` envelope is pinned
(snapshot) — but only if it captures a meaningful contract, per AGENTS.md
snapshot guidance; otherwise rely on the BDD assertion and skip a snapshot-only
test.

Validation: `make all`. Expect the corpus cross-check and the new BDD scenario
green; the existing resolved/near-miss specs unchanged.

### W4 — Reconcile the documentation to the positional grammar and both failure directions

Implements: AGENTS.md "Documentation maintenance"; roadmap 3.1.4 `See` targets
(design §4.2; `skill/novel-ralph/references/done-conditions.md`); records
D-BLOCKER-POSITIONAL and D-BLOCKER-SCOPE for future readers.

Read first: the BLOCKER-format paragraph in `docs/developers-guide.md` (lines
566–571), the BLOCKER mentions in
`skill/novel-ralph/references/done-conditions.md` (the
`contains_unresolved_blocker` reference at lines 181–185 pins no grammar), and
design §4.2's implementation-status note. Load: `en-gb-oxendict` for the prose;
no code skills.

1. In `docs/developers-guide.md`, replace the "acknowledged brittle … substring"
   wording with the **trailing positional** rule: an unresolved BLOCKER is a
   `critic-notes.md` line whose stripped text starts with `BLOCKER` and does
   not *end with* the `[resolved]` token; an incidental mid-line mention no
   longer clears the blocker (cite design §4.2 and audit Finding 3). Document
   the remaining limitations in **both** directions: false-dirty prose mentions
   (existing near-miss) and the still-unhandled case/alternative-spelling
   variants (`RESOLVED`, `(resolved)`), per D-BLOCKER-SCOPE.
2. In `skill/novel-ralph/references/done-conditions.md`, add a one-line note
   beside the `contains_unresolved_blocker` reference (around line 185) stating
   the deterministic grammar the shipped predicate uses (trailing `[resolved]`
   marker), so the reference no longer leaves the grammar unpinned — mirroring
   how 3.1.1.1 reconciled the manifest-vs-outline reference. Keep the en-GB
   Oxford spelling and the 80-column prose / 120-column code-block wrapping.
3. Update the design §4.2 implementation-status note (the block-quote at lines
   310–318) with a sentence recording that roadmap 3.1.4 tightened
   `no_unresolved_blockers` to the positional resolution marker and pinned the
   false-clean direction in the corpus. Do not restate the whole clause set.

Tests this work item adds/updates: none (documentation only), but the prose
must pass the markdown gates.

Validation: `make markdownlint` and `make nixie` (both required for any
markdown change, per the standing rules), plus `make fmt` to format
tables/markup, then a final `make all` to confirm the code gates remain green
after the doc edits.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-3-1-4`.

1. Confirm the branch and a clean tree:

   ```bash
   git branch --show-current   # expect roadmap-3-1-4
   git status --short          # expect empty
   ```

2. W1+W2 (default: folded) — add the failing false-clean unit test unmarked,
   observe red, then apply the positional grammar and the property test so the
   same commit turns it green:

   ```bash
   # add test_incidental_resolved_mention_stays_unresolved (unmarked), then:
   make test    # observe the new test FAILING against the current substring rule
   # apply the done_predicate.py positional change + property test, then:
   make all     # build check-fmt lint typecheck test — all green
   git add novel_ralph_skill/state/done_predicate.py tests/test_done_predicate.py
   git commit   # "Anchor unresolved-BLOCKER resolution to a trailing marker"
   ```

   (Recorded-red alternative only if a reviewer asks: commit the xfail-marked
   test first — `git add tests/test_done_predicate.py; git commit` — then
   remove the marker in the grammar commit above.)

   Expected transcript fragment:

   ```plaintext
   tests/test_done_predicate.py::test_incidental_resolved_mention_stays_unresolved PASSED
   tests/test_done_predicate.py::test_blocker_resolution_is_positional PASSED
   tests/test_done_predicate.py::test_resolved_blocker_is_clean PASSED
   ```

3. W3 — add the corpus tree, oracle twin, fixtures, BDD scenario:

   ```bash
   make all     # corpus cross-check + new BDD scenario green
   git add tests/working_corpus/ tests/corpus_done_predicate_fixtures.py \
           tests/test_working_corpus_done_predicate.py \
           tests/features/novel_done.feature tests/steps/novel_done_steps.py
   git commit   # "Pin false-clean BLOCKER corpus tree and oracle twin"
   ```

4. W4 — documentation reconciliation:

   ```bash
   make fmt
   make markdownlint
   make nixie
   make all
   git add docs/developers-guide.md docs/novel-ralph-harness-design.md \
           skill/novel-ralph/references/done-conditions.md
   git commit   # "Document positional BLOCKER resolution grammar"
   ```

Use file-based commit messages (the `commit-message` skill / never `-m`).

## Validation and acceptance

Behavioural acceptance (a human can verify):

- On an otherwise-done tree, writing
  `BLOCKER the ending still depends on the [resolved] issue\n` into a chapter's
  `critic-notes.md` and running `novel-done` exits `1` and reports
  `no_unresolved_blockers` false. Before the positional fix the same input exits
  `0` (the lie); the false-clean unit test (added unmarked at the head of the
  W2 commit, or as the recorded-red W1 commit on the alternative path) pins
  this transition.
- A genuinely resolved blocker (`BLOCKER … [resolved]` as the trailing marker)
  still clears: the all-hold tree with `RESOLVED_BLOCKER_NOTE` exits `0`.
- The existing false-dirty near-miss (prose mention, no token) still reports
  unresolved.

Quality criteria (what "done" means):

- Tests: `make test` passes; the new
  `test_incidental_resolved_mention_stays_unresolved` fails before W2 and
  passes after; `test_blocker_resolution_is_positional` (Hypothesis) passes;
  the new corpus cross-check and BDD scenario pass; all prior done-predicate,
  corpus, snapshot, and `novel-done` e2e suites stay green.
- Lint/format/type: `make check-fmt`, `make lint` (Ruff + interrogate 100%
  docstring coverage + Pylint), and `make typecheck` (`ty`) all pass.
- Audit: `make audit` (pip-audit) passes — no new dependency, so unchanged.
- Markdown: `make markdownlint` and `make nixie` pass for the W4 doc changes.

Quality method: `make all` is the gate for code commits (W1–W3);
`make markdownlint` + `make nixie` + `make all` for the markdown commit (W4).
Do not commit any change that fails a gate (AGENTS.md).

## Idempotence and recovery

Every step is a re-runnable edit plus `make`; nothing is destructive and the
predicate writes nothing to disk. If a `make` gate fails, fix forward within
the Tolerances; if the done-predicate or corpus suites cannot be made green in
3 attempts, stop and escalate. To revert a work item, `git revert` its single
commit — each work item is one atomic commit.

## Artifacts and notes

The load-bearing change is one line in
`novel_ralph_skill/state/done_predicate.py`'s `_contains_unresolved_blocker`:

```python
# before (unsound false-clean):
stripped.startswith(_BLOCKER_PREFIX) and _RESOLVED_TOKEN not in stripped
# after (positional, D-BLOCKER-POSITIONAL):
stripped.startswith(_BLOCKER_PREFIX) and not stripped.endswith(_RESOLVED_TOKEN)
```

The mirrored change in `tests/working_corpus/_done_predicate_oracle.py`'s
`_notes_has_unresolved_blocker` keeps the deliberate twin equal to production.

## Interfaces and dependencies

No new dependencies. The plan reuses, by exact name, the following signatures
(internal grammar changed where noted; all signatures unchanged):

```python
# done_predicate.py — internal grammar changed, signature unchanged:
_contains_unresolved_blocker(notes_path: Path) -> bool
# done_predicate.py — unchanged signature and polarity (True when clean):
no_unresolved_blockers(state: State, working_dir: Path) -> bool
# _done_predicate_oracle.py — the corpus twin, kept equal to production:
no_unresolved_blockers(working_dir: Path) -> bool
# _done_predicate_specs.py — new false-clean corpus tree, exported via __init__:
DONE_PREDICATE_INCIDENTAL_RESOLVED_BLOCKER: WorkingTreeSpec
# corpus_done_predicate_fixtures.py — fixture return type widened (B1):
#   was: cabc.Callable[[], tuple[Path, Path]]
#   now: cabc.Callable[[], tuple[Path, Path, Path]]
#   inner _build returns (resolved_working, near_miss_working, incidental_working)
blocker_edge_trees: cabc.Callable[[], tuple[Path, Path, Path]]
```

- `pytest`, `pytest-bdd`, `hypothesis`, `syrupy` — already in the dev
  dependency set and already used by `tests/test_done_predicate.py` and the
  `novel-done` suites.

## Revision note

- Round 2 (2026-06-24): Resolved the round-1 design-review blocking point B1.
  W3 step 4 now names the exact mechanical edits to the `blocker_edge_trees`
  fixture (`tests/corpus_done_predicate_fixtures.py`) and its two destructuring
  consumers in `tests/test_working_corpus_done_predicate.py`
  (`test_blocker_edges`, `test_blocker_oracle_twin_agrees`): the fixture return
  type widens to `tuple[Path, Path, Path]`, `test_blocker_edges` unpacks three
  and asserts `incidental.failed_clause_names == ("no_unresolved_blockers",)`,
  and `test_blocker_oracle_twin_agrees`'s length-agnostic `cases.extend(...)`
  keeps working with only an annotation update. Decision log records this as
  D-BLOCKER-EDGE-ARITY. Also tightened the advisory items: A1 (W2 Hypothesis
  property now constructs sentinel-terminated false-case lines and a token/
  newline-free alphabet instead of filtering), A2 (W1 folded into W2 by
  default, recorded-red kept as an explicit alternative), and A3 (W3 step 5 now
  states definitively that a new Given step is required because the incidental
  tree is not in `DONE_PREDICATE_FAILERS`). Why: B1 would have failed the W3
  `make all` gate as written; A1 would have flaked the property on first
  adverse example. Effect on remaining work: scope, tolerances, and the
  four-work-item shape are unchanged; the W3 commit now also touches
  `tests/test_working_corpus_done_predicate.py`.
