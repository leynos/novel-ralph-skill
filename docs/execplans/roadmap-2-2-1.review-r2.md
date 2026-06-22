# Adversarial Logisphere design review — roadmap 2.2.1 (round 2)

Target: `docs/execplans/roadmap-2-2-1.md` ("Implement the `tomlkit` round-trip
and atomic write helper"). Status of plan at review: DRAFT.

Verdict: **Proceed with conditions.** The round-1 blocking defects (B1/B2/B3)
and advisories (A1/A2/A3) are all properly resolved, and the plan's central
empirical bet was independently re-verified at the real locked `tomlkit`
0.15.0. One blocking defect remains that round 1 did not surface: the
behavioural test the plan mandates uses `pytest-bdd`, which is not an installed
dependency, and the plan neither adds it nor reconciles the gap with its own
dependency Tolerance. This goes back to the planner.

## Round-1 defects — re-verified as resolved

- **B1 (comment-free property).** Resolved. The round-trip *property* now draws
  over a hand-authored comment-and-layout-bearing `COMMENT_BEARING_STATE_TOML`
  fixture (block comments, an inline value comment, blank-line layout, an
  inline table, an array-of-tables); the comment-free corpus sweep is demoted
  to "an additional case, never the sole carrier." (Work item 1; Risk "guards
  nothing"; Decision log.)
- **B2 (surgical mutation by example only).** Resolved. Work item 2 now pins the
  surgical `word_counts.current` mutation as a Hypothesis *property* over the
  comment-bearing fixture, asserting only the touched value's bytes change and
  every comment/blank-line survives — the §9 "no-op recount preserves
  formatting and comments" criterion.
- **B3 (probe at 0.14.0, equivalence asserted from memory).** Resolved, and
  independently re-confirmed. The probe is re-run under the uv-resolved 0.15.0
  (`tomlkit.__version__` == `0.15.0`, confirmed here), and the "behaves
  identically" cross-version claim is removed in favour of "the 0.15.0 property
  test under `make test` is the verification of record." I reproduced the probe
  myself at 0.15.0: no-op byte-identical `True`; surgical mutation exact with
  block and inline comments kept `True`; add-then-remove `pending_turn` not
  byte-reversible (138 vs 137 bytes on my fixture; the plan reports 507 vs 506
  — same residual-byte phenomenon).
- **A1 (clean-exit write source).** Resolved. The `pending_turn` docstring,
  Decision log, and work item 3 all now state the yielded caller-mutated
  `TOMLDocument` is the *single write source* for the clean-exit write, and a
  test pins that an in-bracket value edit survives a clean exit.
- **A2 (§5.4 producer/consumer boundary).** Resolved. The plan repeatedly
  signposts that this task owns only the *producer* side (leaving the populated
  record); §5.4 rollback-to-prior-coherent-point is `reconcile`'s (2.3.2). I
  confirmed §5.4 line 491 assigns that to `reconcile`.
- **A3 (factory-callable fixtures).** Resolved. The plan now states the corpus
  fixtures are factory callables and the state file is at
  `working_dir / "state.toml"`. Confirmed against `corpus_fixtures.py`:
  `phase_state_tree -> Callable[[str], Path]`,
  `baseline_tree -> Callable[[], Path]`,
  `coherent_oracle_cases -> list[tuple[WorkingTreeSpec, Path]]`.

## Verified against source (round 2)

- `tomlkit` locked at 0.15.0 (`uv.lock` 667-669), uv-resolved env reports
  0.15.0. `requires-python = ">=3.14"`; deps `cyclopts`, `tomlkit`.
- Atomic-write pattern in the plan matches `docs/scripting-standards.md` 409-414
  verbatim (`NamedTemporaryFile("w", delete=False, dir=f.parent, ...)` then
  `tmp_path.replace(f)`).
- ADR-002 functional req 1 ("byte-for-byte, including comments and whitespace")
  and req 2 ("a real mutation changes only the targeted values") match the
  plan's two property strengths. ADR-002 "Known risks" names the round-trip
  property as the regression guard, exactly what the plan delivers at 0.15.0.
- Design §3.4 (atomic write; `pending_turn` open-before/clear-after; "died
  mid-write" signature), §5.4 (rollback is `reconcile`'s), §9 (no-op recount
  preserves comments; v1 shells out to nothing, suite touches only the
  filesystem) all cited accurately.
- `PendingTurn` fields are `operation: str`, `paths: tuple[str, ...]`
  (`schema.py` 264-280); the plan's `open_pending_turn(operation, paths)` and
  the `parse_state` read-back via `_pending_turn` (`parse.py` 175-186) line up.
- Corpus builder inserts zero comments (no comment call anywhere in
  `_builder.py`), confirming the plan's premise that the corpus cannot carry
  the comment-preservation guarantee.
- No-cuprum / no-shell-out is correct (design §4 line 241; the helper touches
  only `pathlib`/`tempfile`). `document.py` will sit well under the 400-line
  cap (existing state modules: 52/248/68/315).
- No load-bearing memory-based claims about Cyclopts, `pytest-timeout`, or `uv`
  internals. The only `pytest-xdist` claim (simulate the crash
  deterministically rather than fork/signal) is sound and is the right call for
  xdist.

## Blocking defect (new in round 2)

### B4 — The mandated `pytest-bdd` behavioural test relies on an uninstalled dependency, and the plan neither adds it nor reconciles it with the dependency Tolerance

Work item 3 and "Validation and acceptance" both mandate a `pytest-bdd`
behavioural scenario for the torn-turn recovery flow ("A behavioural test
(`pytest-bdd` …)"; "A `pytest-bdd` scenario shows an interrupted multi-file
turn …"). AGENTS.md line 143 does sanction this choice ("use `pytest` for unit
tests and `pytest-bdd` for behavioural tests"), so the *style* is
design-conformant.

But `pytest-bdd` is **not installed**: it is absent from `pyproject.toml`'s
`[dependency-groups].dev` (which is `pytest, interrogate, pip-audit, ruff,
pyright, ty, pytest-timeout, pytest-xdist, cuprum, hypothesis, syrupy`)
and absent from `uv.lock`. No `.feature` file and no `from pytest_bdd` import
exists anywhere in `tests/`; this plan is the first to need it. As written,
work item 3's `make all` would fail at collection with
`ModuleNotFoundError: pytest_bdd`, so the work item is not implementable as
specified.

Worse, the plan's own Tolerances say: "If a new external dependency beyond the
locked `tomlkit` is required, stop and escalate." Adding `pytest-bdd` trips
that trigger on a literal reading. The plan must resolve this contradiction
rather than leave the implementer to discover it mid-work item.

Required fix — pick one and state it explicitly in the plan (Interfaces /
Tolerances / the work item):

1. Add `pytest-bdd` to `[dependency-groups].dev` as an explicit step in work
   item 3 (and update `uv.lock`), and amend the dependency Tolerance to
   distinguish a *runtime* dependency (forbidden beyond `tomlkit`) from a
   *dev/test* dependency that AGENTS.md already mandates for behavioural tests.
   This is the most design-conformant resolution: AGENTS.md asks for
   pytest-bdd, so introducing it as the project's first behavioural-test
   dependency is a sanctioned, not a smuggled, addition — but it must be a
   named work item, not an implicit side effect, and the Tolerance must be
   reconciled so the implementer does not stop-and-escalate on hitting it.
2. Or, if introducing the project's first `pytest-bdd` dependency is judged out
   of scope for this task, write the torn-turn behavioural assertion with the
   already-installed `pytest` (a plain test exercising the Given/When/Then as
   an ordinary function) and remove the `pytest-bdd` wording, noting the
   deviation from AGENTS.md line 143 and why. This keeps the dependency set
   frozen but forgoes the AGENTS-preferred behavioural form.

Either way the plan must not assert a `pytest-bdd` scenario while leaving
`pytest-bdd` uninstalled and unaccounted for.

## Pre-mortem (Doggylump leads)

Scenario: the implementer reaches work item 3, writes the `pytest-bdd` scenario
per the plan, runs `make all`, and collection dies with
`ModuleNotFoundError: pytest_bdd`. They consult the plan's Tolerances, read "no
new external dependency beyond `tomlkit` — stop and escalate," and halt —
correctly, by the plan's own rule — on what is really a routine dev-dependency
addition AGENTS.md already blesses. A half-day is lost to an escalation the
plan could have pre-empted. Mitigation is B4: name the dependency addition as a
step and reconcile the Tolerance so the runtime-vs-test distinction is explicit.

Second scenario (already mitigated): a later 2.2.2 mutator wraps a value edit in
`pending_turn`, exits cleanly, and the edit is silently lost because the
clean-exit write reloaded a fresh document. The round-2 plan pins the
yielded-document-is-the-single-write-source contract and adds a test that an
in-bracket value edit survives a clean exit (A1). No further action.

## Strongest alternative (Wafflecat)

The Wafflecat alternative from round 1 (make the `pending_turn` open/clear
cycle byte-reversible via a permanently-present sentinel `[pending_turn]` shell
in the §5.1 baseline) remains rejected for the same reason: it leaks a writer
concern into the schema the design did not ask for, and the empirical
residual-byte artefact (re-confirmed here at 0.15.0) makes the two-strength
split (byte-for-byte for value edits, parsed-equality for the open/clear cycle)
the lower-risk choice. The chosen split is correct. No change required on this
axis.

## Required next step (ordered)

1. B4: resolve the `pytest-bdd` dependency gap — either add it as an explicit
   dev-dependency step in work item 3 and amend the dependency Tolerance to
   carve out dev/test dependencies AGENTS.md mandates, or rewrite the torn-turn
   behavioural test on the installed `pytest` and drop the `pytest-bdd` wording
   (noting the AGENTS.md deviation). State the choice in the plan.

Trail followed: ADR-002 (functional reqs, Known risks); design §3.4, §5.1,
§5.4, §9; `docs/scripting-standards.md` §"Reading / writing files and atomic
updates"; AGENTS.md (dependency Tolerance, line 143 pytest-bdd guidance,
400-line cap, gate-green-at-commit); `state/parse.py`, `state/schema.py`,
`state/__init__.py`; `tests/working_corpus/_builder.py`;
`tests/corpus_fixtures.py`; `uv.lock`, `pyproject.toml`; cuprum read-only
checkout (no-cuprum confirmed); independent `uv run` probe of tomlkit 0.15.0
(no-op, surgical mutation, add-then-remove residual byte). Skills:
`logisphere-design-review`.
