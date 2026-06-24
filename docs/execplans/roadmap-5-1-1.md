# Implement the versioned rule-pack loader and schema

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: DONE

## Purpose / big picture

A *rule pack* is a versioned TOML file of prose-detection rules. Each rule names
a regular-expression `pattern`, a `threshold` (the allowed number of hits), and
a counting `basis` (how the hits are tallied), so that `desloppify` — the
deterministic slop detector — can report uniform per-hit structured output
without baking the rules into code (design §4.4 and §6.1). This plan delivers
the *loader and schema* for that pack, and nothing else: the typed in-memory
shape of a rule pack, plus the boundary function that turns a decoded TOML
mapping into that shape, *validating at runtime* `schema_version` and every rule's
`id`, `pattern`, `threshold`, `basis`, and `page_words` — raising a typed,
rule-naming error on any missing, wrong-typed, or out-of-range field rather than
silently coercing or letting a raw `KeyError`/`TypeError` surface. This is the
load-bearing difference from `state/parse.py`, which is a structural-only parse
(see Constraints).

After this change, a developer (and the `desloppify` detection logic that
roadmap task 5.1.2 builds on top of this) can load a rule pack from disk into a
frozen, fully typed `RulePack` object, with every pattern pre-compiled, and can
rely on the loader to reject a malformed pack *loudly* — naming the offending
rule id — rather than silently skipping a bad rule. This is the precise outcome
the roadmap demands for 5.1.1: "a pack with an invalid regular expression fails
loudly, naming the rule, rather than silently skipping it" (`docs/roadmap.md`
lines 521-528).

This task is the *schema and loader only*. It writes no command, no CLI, no
envelope, and no detection logic. It does not count words, scan a manuscript,
or emit a JSON envelope. Those are roadmap task 5.1.2 (`desloppify` detection
over the §6 offender table), which this plan deliberately leaves untouched so
the two land as separate, independently gate-passable commits. The loader does,
however, classify its failures into the two exit-code *channels* 5.1.2 will
surface — a malformed pack (bad `schema_version`, missing/invalid field,
uncompilable pattern) is the usage-error channel (exit 2), and an unreadable or
absent pack file is the state/input channel (exit 3) — by raising two distinct,
typed exceptions that 5.1.2 maps to `ExitCode.USAGE_ERROR` and
`ExitCode.STATE_ERROR` respectively (design §4.4, §10; `docs/roadmap.md` line
525 for the exit-2 requirement). The loader itself does not call `sys.exit`;
exit-code translation is the command body's job (the established split in
`novel_ralph_skill/contract/runner.py`).

You can see it working by running, from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-5-1-1`:

```bash
make test
```

and observing the new tests in `tests/test_rulepack_schema.py`,
`tests/test_rulepack_loader.py`, and `tests/test_rulepack_properties.py` pass.
Before the implementation lands they fail at import (the module does not exist);
after, they pass. The headline behavioural assertion is that loading a pack
whose rule `id = "broken"` carries `pattern = "a("` raises
`RulePackError`, and the raised error's message and structured detail name
`broken` as the offending rule — proving the "fails loudly, naming the rule"
success criterion.

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- Work exclusively inside the worktree
  `/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-5-1-1` on branch
  `roadmap-5-1-1`. Never edit the control worktree at
  `/data/leynos/Projects/novel-ralph-skill`.
- The deterministic/judgemental boundary (ADR-001) is absolute: the loader
  *detects shape*; it never judges prose, never edits, and never decides whether
  a flagged pattern is justified. The loader compiles patterns and validates
  structure only.
- No CLI, no Cyclopts app, no JSON envelope, no `sys.exit`, and no detection or
  counting logic in this task. Those belong to roadmap task 5.1.2. The loader is
  a pure boundary constructor that mirrors the *structure* of
  `novel_ralph_skill/state/parse.py` (a pure `parse_*(mapping) -> typed`
  boundary, a thin `load_*(path)` `tomllib` file convenience, every TOML array
  coerced to a `tuple`) but, *unlike* `parse_state`, is a **validating** boundary
  — see the next constraint.
- The loader is a **validating boundary**, which is the load-bearing difference
  from `state/parse.py`. `parse_state` is deliberately a structural-only parse:
  it uses `typ.cast` (a static-only hint that performs **zero** runtime checking
  — `typ.cast("int", "x")` returns the string unchanged) and lets a missing key
  surface as a raw `KeyError` (see its own `Raises` block,
  `novel_ralph_skill/state/parse.py` lines 208-213), deferring all field
  mapping to "task 2.2.x". That discipline cannot satisfy 5.1.1's success
  criterion. `parse_rulepack` must instead perform a **runtime `isinstance`
  check on every field** (`schema_version`, `pack`, `id`, `pattern`,
  `threshold`, `basis`, `page_words`) and convert *every* missing, absent,
  wrong-typed, or out-of-range fault into a typed `RulePackError` (with
  `rule_id` set for a per-rule fault, `None` for a pack-level fault). Do **not**
  use `typ.cast` as the narrowing mechanism for a validated field: a cast names
  nothing and lets a `KeyError`/`TypeError` surface raw, which fails the
  "fails loudly, naming the rule" criterion for every fault except the
  bad-pattern case. Use `typ.cast` only to satisfy the type checker *after* a
  runtime check has already proven the value's type (the cast then merely
  restates a fact the runtime guard established).
- No new runtime dependency. The loader reads with the standard-library
  `tomllib` (the established read path; writes go through `tomlkit` per
  ADR-002, but this task only reads) and compiles patterns with the
  standard-library `re`. cuprum is *not* used: it is "required only where a
  command shells out (none do)" (design §9, lines 241 and 710), and this task
  shells out to nothing.
- The rule-pack `schema_version` is its own independent version, separate from
  the envelope's and `state.toml`'s (design §3.1, lines 166-173). The loader
  must validate `schema_version` and report an unexpected value rather than
  silently coercing it. The current rule-pack schema version is `1` (design
  §6.1, line 518).
- Follow the house style exactly: frozen, slotted, keyword-only dataclasses with
  numpy-style docstrings (`novel_ralph_skill/contract/envelope.py`,
  `novel_ralph_skill/state/schema.py`); a pure parse boundary that never lets a
  raw `dict` leak inward (`novel_ralph_skill/state/parse.py`; python-data-shapes
  "parse to a schema type at the boundary"). Read-only mapping/sequence fields
  are frozen via `novel_ralph_skill/_freeze.py` in `__post_init__`.
- en-GB Oxford spelling (`-ize`/`-yse`/`-our`) in all prose, comments, and
  docstrings, except verbatim external API names. No code file exceeds 400 lines
  (AGENTS.md). 100% docstring coverage (`interrogate`) is gated by `make lint`.
- Public names introduced here are stable contract for task 5.1.2: do not rename
  them in a later revision without escalating.

## Tolerances (exception triggers)

Thresholds that trigger escalation when breached.

- Scope: if the implementation requires changes to more than 7 files or more
  than ~450 net lines of non-test code, stop and escalate. (Two small package
  modules plus three test modules and one fixture data file is the expected
  shape.)
- Interface: if delivering the loader appears to require a new public symbol on
  the `contract` layer, or a change to any existing public signature in
  `contract/` or `state/`, stop and escalate.
- Dependencies: if any work item appears to need a new external dependency (for
  example, a TOML schema-validation library or `msgspec` at runtime), stop and
  escalate. The expectation is stdlib-only (`tomllib`, `re`).
- Design ambiguity: if the design does not pin a needed semantic — for example,
  whether an unknown `basis` value is a usage error or a tolerated extension —
  resolve it in favour of the *strictest* loud-failure reading (reject, naming
  the rule), record the choice in the Decision Log, and continue. If the
  strictest reading conflicts with an explicit design statement, stop and
  escalate.
- Iterations: if `make all` still fails after 3 focused fix attempts on the same
  failure, stop and escalate.
- Verification adversary: this task adds Hypothesis property tests (see the
  testing section). If a property test surfaces a genuine loader defect that
  cannot be fixed within the scope tolerance above, stop and escalate rather
  than weakening the property.

## Risks

- Risk: the design fixes the rule-pack *shape* by example (§6.1) but does not
  enumerate every field's type or which fields are optional per `basis` (for
  example, `page_words` appears only on a `per_page` rule).
  Severity: medium. Likelihood: high.
  Mitigation: model the `basis` field as a closed set (`manuscript`,
  `per_page`) and make `page_words` required-when-`per_page`,
  absent-otherwise, validated by the loader. Pin every field type in
  `tests/test_rulepack_schema.py` and the boundary behaviour in
  `tests/test_rulepack_loader.py`. Record the closed-set decision in the
  Decision Log. (See Decision Log seed "basis is a closed set".)
- Risk: `re.compile` raising on a bad pattern must be caught at the precise
  rule, not at pack level, so the error names the offending rule id.
  Severity: medium. Likelihood: medium.
  Mitigation: compile each pattern inside the per-rule constructor and wrap
  `re.error` into `RulePackError` carrying the rule id. Verified empirically:
  `re.compile("a(")` raises `re.error` (aliased `re.PatternError` since Python
  3.13) eagerly at compile time (see Surprises & Discoveries "re.error pins").
- Risk: confusing the two failure channels — a malformed *pack content* (exit 2)
  versus an absent/unreadable *pack file* (exit 3) — would break the contract
  5.1.2 surfaces (design §10, lines 732-734 and the §9 desloppify error-path
  paragraph, lines 700-703).
  Severity: medium. Likelihood: medium.
  Mitigation: raise two distinct exception types — `RulePackError` (malformed
  content → 2) and `RulePackFileError` (absent/unreadable file or undecodable
  TOML → 3) — and assert both channels in
  `tests/test_rulepack_loader.py`. Note: a TOML *decode* failure is a file/input
  fault (exit 3), matching how `state.toml` parse failures map (design §10 line
  715; developers-guide line 253). A *structurally valid* TOML that violates the
  rule-pack schema is content malformation (exit 2).
- Risk: the runtime integer guard silently accepts `bool`, because
  `isinstance(True, int)` is `True` in Python, so a TOML `threshold = true` (or
  `schema_version = true`) would pass a naive `isinstance(value, int)` check and
  be treated as `1`.
  Severity: medium. Likelihood: medium.
  Mitigation: the `_require_int` helper must reject `bool` explicitly
  (`type(value) is int`, or `isinstance(value, int) and not isinstance(value,
  bool)`). Add a `bool-threshold.toml` fixture (or an in-memory
  `{"threshold": True}` case in the `parse_rulepack` unit test) asserting
  `RulePackError`. (Round-2 addition, surfacing the trap behind review B2.)
- Risk: scope creep into detection logic or CLI wiring.
  Severity: low. Likelihood: medium.
  Mitigation: the Constraints bar it; the Progress checklist contains no command
  or envelope item. Detection is task 5.1.2.

## Progress

- [x] Work item 1: typed rule-pack schema (`RuleBasis`, `Rule`, `RulePack`) and
      the two error types (`RulePackError`, `RulePackFileError`) — module
      `novel_ralph_skill/rulepack/schema.py` and `errors.py`; tests
      `tests/test_rulepack_schema.py`. Done 2026-06-22: `make all` green (170
      passed); one coderabbit run addressed (see Decision Log "WI1 review").
- [x] Work item 2: the pure boundary loader (`parse_rulepack`, `load_rulepack`)
      — module `novel_ralph_skill/rulepack/parse.py`; tests
      `tests/test_rulepack_loader.py` plus the `tests/data/rulepacks/` fixtures.
      Done 2026-06-22: `make all` green (197 passed); one coderabbit run
      addressed (see Decision Log "WI2 review").
- [x] Work item 3: Hypothesis property coverage of the loader's validation
      invariants — tests `tests/test_rulepack_properties.py`. Done 2026-06-22:
      `make all` green (201 passed); coderabbit's WI2 "add property tests for the
      type guards" finding is satisfied here (see Decision Log "WI3").
- [x] Work item 4: developers-guide documentation of the rule-pack loader and
      its parse boundary, mirroring the existing "State and on-disk layout"
      entry. Done 2026-06-22: added the "Rule packs and the loader boundary"
      subsection; `make all`, `make markdownlint`, and `make nixie` all green;
      coderabbit run returned zero findings.

## Surprises & discoveries

- Observation: `re.compile` validates eagerly and raises `re.error` (whose name
  is `PatternError` since Python 3.13) at compile time, not at first match.
  Evidence: `uv run python -c "import re; re.compile('a(')"` raises
  `re.error: missing ), unterminated subpattern at position 1` (run on
  CPython 3.14.3 in this worktree, 2026-06-22).
  Impact: the loader can compile every pattern at load time and catch the bad
  one precisely, satisfying the "fails loudly, naming the rule" criterion
  without deferring to match time.
- Observation: `tomllib.loads` raises `tomllib.TOMLDecodeError` on undecodable
  TOML.
  Evidence: `uv run python -c "import tomllib; tomllib.loads('x = = 1')"` raises
  `tomllib.TOMLDecodeError` (same environment).
  Impact: the file loader catches `TOMLDecodeError` and re-raises as
  `RulePackFileError` (exit-3 channel), keeping a decode fault distinct from a
  schema-content fault (exit-2 channel).
- Observation: cuprum is locked at `0.1.0` (`uv.lock`) but is irrelevant here.
  Evidence: design §9 lines 241 and 710 — "cuprum is required only where a
  command shells out (none do)" and "v1 commands shell out to nothing".
  Impact: no cuprum API is on this task's critical path; the loader is
  stdlib-only. No firecrawl research of cuprum/Cyclopts library behaviour is
  load-bearing for 5.1.1 because the task introduces no subprocess and no CLI.

## Decision log

- Decision: model `basis` as a closed two-member set (`manuscript`,
  `per_page`), implemented as a `enum.StrEnum` named `RuleBasis`, and reject any
  other value by naming the offending rule.
  Rationale: design §6.1 shows exactly these two bases; the strictest
  loud-failure reading (Tolerances "Design ambiguity") rejects unknown bases so
  a typo cannot silently disable a rule — exactly the failure mode 5.1.1 exists
  to eliminate. The §6.3 device-ledger and §6.2 ai-isms packs are deferred
  (roadmap 7.1), so their additional keys are out of scope here.
  Date/Author: 2026-06-22, planning agent.
- Decision: `page_words` is required when and only when `basis = "per_page"`,
  and must be absent (or rejected) otherwise; it is a positive integer.
  Rationale: design §6.1 attaches `page_words = 300` to the `per_page` rule and
  to no other; the per-page density basis is meaningless without a page size.
  Date/Author: 2026-06-22, planning agent.
- Decision: `threshold` is a non-negative integer (design's example shows
  `threshold = 0` for zero tolerance and `threshold = 5`).
  Rationale: a threshold is the allowed hit count; negative is incoherent.
  Date/Author: 2026-06-22, planning agent.
- Decision: two error types — `RulePackError` (malformed content; the command
  maps to exit 2) and `RulePackFileError` (absent/unreadable file or undecodable
  TOML; maps to exit 3) — both carrying a `rule_id: str | None` and a `messages`
  tuple for the envelope the *command* (task 5.1.2) will build.
  Rationale: design §10 splits an invalid pattern (exit 2, naming the rule)
  from an unreadable/absent pack (exit 3); the loader must distinguish them at
  the type level so 5.1.2 maps each to the right `ExitCode` without re-parsing a
  message. Mirrors `StateInputError` in `contract/runner.py`.
  Date/Author: 2026-06-22, planning agent.
- Decision: the loader does not call `sys.exit` and emits no envelope; it raises
  typed errors and returns a typed `RulePack`.
  Rationale: command/exit-code translation is the command body's job (the
  established split in `contract/runner.py`); keeping the loader pure lets 5.1.2
  and any future pack consumer reuse it without a process boundary, exactly as
  `parse_state`/`load_state` separate parsing from the CLI.
  Date/Author: 2026-06-22, planning agent.
- Decision (round 2, resolving review B1): `parse_rulepack` is a **validating**
  boundary — runtime `isinstance` guards on every field, raising `RulePackError`
  naming the rule — and is *not* a structural-only mirror of `parse_state`. The
  `typ.cast` idiom of `state/parse.py` is explicitly rejected as the narrowing
  mechanism because a cast performs no runtime check and names nothing.
  Rationale: the round-1 review correctly observed that `parse_state` uses
  `typ.cast` (zero runtime checking) and lets `KeyError`/`TypeError` surface raw
  (its `Raises` block, lines 208-213), which cannot satisfy 5.1.1's "fails
  loudly, naming the rule" criterion for any fault except the bad-pattern case.
  Date/Author: 2026-06-22, planning agent.
- Decision (round 2, resolving review B3): the property tests follow the
  `tests/test_contract_properties.py` precedent — strategies-only inputs (no
  function-scoped fixtures, to avoid `HealthCheck.function_scoped_fixture`),
  explicit bounded `@settings(max_examples≈100, deadline≈400ms)`, and
  cheap-to-compile curated patterns — so the suite stays inside the global
  `timeout = 30` per test under `pytest -n auto`. No new Hypothesis profile is
  registered (the tree has none).
  Rationale: the global 30 s timeout (`pyproject.toml` line 325) and `-n auto`
  xdist scheduling (Makefile lines 14, 116) interact with Hypothesis's default
  deadline/example count; bounding them and keeping regex compilation cheap is
  what makes the suite deterministic.
  Date/Author: 2026-06-22, planning agent.
- Decision (advisory A2): `pack` is a **required** top-level key in a v1 rule
  pack; a missing `pack` raises `RulePackError(rule_id=None, …)`.
  Rationale: design §6.1's example carries `pack = "ai-isms"`. The §6.3
  device-ledger example omits `pack` and uses a different rule vocabulary
  (`[[device]]`, `max_count`/`allowed_chapters`); that pack is deferred to
  roadmap 7.1 and is out of scope here, so making `pack` mandatory for the v1
  prose-rule schema is a deliberate, recorded choice 7.1 may revisit.
  Date/Author: 2026-06-22, planning agent.
- Decision (advisory A3): a stray `page_words` on a non-`per_page` rule is
  **rejected** (the strict reading), not ignored.
  Rationale: §6.1 shows `page_words` only on the `per_page` rule; it does not
  state it is forbidden elsewhere, so this is a strictness choice (an extra key
  a future basis might legitimately use). Recorded so 7.1 can relax it if a new
  basis needs `page_words`.
  Date/Author: 2026-06-22, planning agent.

- Decision (WI1 implementation, 2026-06-22): the frozen-instance assertion uses
  `setattr(instance, field_name, …)` with a *non-literal* attribute name, not a
  direct `instance.field = …` assignment. Two gates disagree on a direct
  frozen-field write: `ty` raises `invalid-assignment` (the field is read-only
  statically) and ruff B010 forbids `setattr` with a *literal* name. Binding the
  name to a local variable first satisfies both — `ty` cannot resolve the
  dynamic attribute, and ruff sees no literal. Recorded so a later edit does not
  "simplify" it back into a gate failure.
- Decision (WI1 review, 2026-06-22): one coderabbit run, nine findings. Applied
  the one major finding on `rulepack/__init__.py` (its docstring claimed
  `parse_rulepack`/`load_rulepack` already existed; reworded to future tense, as
  the loader lands in WI2) and the parametrize suggestion (consolidated the two
  frozen/slotted tests into one parametrized test). Skipped the seven minor
  "add an assertion failure message" findings: the established house style omits
  assertion messages (2 of 34 asserts carry one in `test_state_schema.py`, 0 of
  10 in `test_contract_properties.py`); descriptive test names and docstrings
  are the convention here, and adding messages everywhere would diverge from it.
  Skipped the `review-r1.md` line-length finding: that file is a planning review
  artefact outside this task's edit scope (not a file WI1 creates or changes).

- Decision (WI2 implementation, 2026-06-22): every validating-helper error
  message is prefixed by a `_where(rule_id)` helper (`rule '...'` or `rule
  pack`) so the message text is self-describing, not just the `rule_id`
  attribute. The loader test asserts the *message* names the offending rule, so
  the envelope task 5.1.2 builds can quote the message verbatim and still name
  the rule. Recorded because the first WI2 `make all` failed exactly here:
  `rule_id` was set, but the helper messages did not yet contain the id.
- Decision (WI2 implementation, 2026-06-22): the file-channel `except` catches
  `(OSError, tomllib.TOMLDecodeError)`. `FileNotFoundError` and
  `PermissionError` are `OSError` subclasses, so naming all four (as the plan's
  prose lists) is redundant and ruff B014 would flag it; the two-type tuple is
  equivalent and lint-clean. `TOMLDecodeError` is a `ValueError`, not an
  `OSError`, so it must be named explicitly. A comment records the coverage.
- Decision (WI2 review, 2026-06-22): one coderabbit run, two findings. Applied
  the minor finding (the `missing-id.toml` fixture was orphaned — added it to
  the pack-level parametrized test and a focused index-naming test). Deferred
  the trivial "add Hypothesis property tests for the type guards" finding to
  Work item 3, which is exactly that suite.
- Decision (WI3 implementation, 2026-06-22): the property suite follows the
  `tests/test_contract_properties.py` precedent — strategies-only inputs (no
  function-scoped fixtures), an explicit bounded
  `@settings(max_examples=100, deadline=400ms)` shared across the four
  properties, and curated cheap-to-compile pattern sets — so each test stays far
  inside the global 30 s per-test timeout under `pytest -n auto`. Inputs are
  built valid-by-construction (`page_words` present iff `per_page`), avoiding the
  filtering trap; the one `.filter` excludes a single value from a 101-value
  range. The four invariants covered: round-trip fidelity, schema-version
  rejection, the "names the offending rule" headline (across patterns and
  positions), and `_require_int` type-guard exhaustiveness (string/float/bool
  thresholds, including the `bool`-is-`int` trap). `datetime` is imported as the
  module (`import datetime as dt`) because ruff bans `from datetime import …`.
  A `_rules_of` cast helper restates the strategy's `list[dict[str, object]]`
  shape for `ty` so the test bodies index entries without a stream of
  `isinstance` narrowings (which `ty` narrows to `dict[Unknown, Unknown]` with a
  `Never`-keyed `__getitem__`).
- Decision (WI3 review, 2026-06-22): one coderabbit run, four findings. Applied
  the one in-scope finding — strengthened the round-trip property to assert
  `parsed.basis is RuleBasis(source["basis"])` and `isinstance(..., RuleBasis)`,
  rather than the weaker `str(parsed.basis) == source["basis"]`, so a regression
  that left `basis` a plain string would fail. Skipped the three findings against
  `roadmap-5-1-1.review-r1.md`: that file is a planning review artefact this task
  does not create or commit (it is untracked and out of scope); its substantive
  points (the runner hand-off contract, the `pack`-mandatory and stray-
  `page_words` decisions) are already recorded in this plan's Outcomes hand-off
  note and Decision Log (advisories A1, A2, A3).
- Decision (round-1 fix, 2026-06-23, resolving review blocking item 1): the two
  `typ.cast("str", …)`/`typ.cast("int", …)` calls in `_require_str`,
  `_require_int`, and `_rule` (parse.py) were **deleted**. `ty` had already
  narrowed `value`/`entry["id"]` to the asserted type after the preceding
  `isinstance` guard, so the casts were redundant and `ty` flagged them as the
  tree's only two `warning[redundant-cast]` diagnostics. The round-2 Decision-Log
  rationale ("cast only to satisfy the type checker after a runtime check") was
  contradicted by `ty` here: a post-guard cast restates nothing the checker
  cannot already see, and the python-types-and-apis skill lists "a `cast(...)`
  call sits next to a runtime check that would let the checker narrow on its own"
  as a red flag. The functions now `return value` / `rule_id = entry["id"]`
  directly. `make typecheck` reports zero diagnostics. The genuine widening cast
  in `_entries` (`list` -> `cabc.Sequence[_Mapping]`) is **kept**: it is not
  redundant (it changes the static type) and `ty` does not flag it.
  Date/Author: 2026-06-23, fix agent.
- Decision (round-1 fix, 2026-06-23, resolving review blocking item 2): unknown
  keys are now **rejected**, naming the offending rule (or the pack level),
  via a `_reject_unknown_keys(mapping, allowed, *, rule_id)` helper checked
  against the closed v1 vocabularies `_PACK_KEYS = {schema_version, pack, rule}`
  and `_RULE_KEYS = {id, pattern, threshold, basis, page_words}`. The rule-level
  check runs inside `_rule` after `id` resolution so the error names the rule;
  the pack-level check runs first in `parse_rulepack`. Rationale: silent
  tolerance of extra keys contradicts the ExecPlan's "Design ambiguity ->
  strictest loud-failure reading" Tolerance and 5.1.1's mission, and is
  inconsistent with advisory A3's deliberate rejection of a misplaced
  `page_words` (A3 rejects a known-but-misplaced key while an unknown key was
  sailing through). Fixtures
  `unknown-rule-key.toml` (a `thresold = 99` typo) and `unknown-pack-key.toml`
  (a stray `extra = "y"`) plus loader and in-memory `parse_rulepack` tests cover
  both levels. The §6.3 device-ledger / §6.2 ai-isms pack variants (roadmap 7.1)
  may extend these vocabularies; doing so is a 7.1 concern, recorded here.
  Date/Author: 2026-06-23, fix agent.
- Decision (round-1 fix, 2026-06-23, resolving review blocking item 3): duplicate
  rule ids are now **rejected**, naming the colliding id, via a
  `_reject_duplicate_ids(rules)` check run in `parse_rulepack` after the rules are
  built. Rationale: a `RulePackError(rule_id="x")` (or a later detection fault in
  5.1.2) cannot disambiguate two rules sharing `id = "x"`, so the "naming the
  rule" contract 5.1.2 builds on requires id-uniqueness. The design does not pin
  uniqueness, so per the "Design ambiguity -> strictest loud-failure reading"
  Tolerance this rejects the collision. Fixture `duplicate-id.toml` plus loader
  and in-memory tests cover it.
  Date/Author: 2026-06-23, fix agent.
- Decision (round-1 fix, 2026-06-23, file-length note): adding the two validators
  with full numpy docstrings grew `parse.py` from 436 to ~516 lines, past the
  AGENTS.md 400-line guideline. The guideline is **not gated** (pylint's
  `too-many-lines`/`C0302` is not in the enabled set; the file already shipped at
  436 lines in WI2 and passed `make all`), and the standing instruction bars
  introducing scope beyond the three blocking items, so a module split was not
  performed in this fix round. Flagged for a follow-up refactor (split the
  validating helpers out of `parse.py`) so 5.1.2 inherits a compliant module.
  Date/Author: 2026-06-23, fix agent.

- Decision (addendum 5.1.1.5, 2026-06-24): the `str(...)` wrappers in the
  `RuleBasis` diagnostic builders were **kept**, with a one-line `StrEnum` note
  added at each site, rather than dropped. The audit's premise ("`repr(member)`
  and `basis!r` render identically") does not hold on this Python: a `StrEnum`'s
  `__repr__` is the Enum form (`<RuleBasis.PER_PAGE: 'per_page'>`), so dropping
  `str(...)` would render that verbose form instead of the bare `'per_page'` a
  pack author types — a regression in diagnostic readability, not a cosmetic
  no-op. The sub-task's own text offers "add a one-line `StrEnum` note" as the
  alternative; that path was taken. Verified empirically:
  `repr(RuleBasis.PER_PAGE)` is `<RuleBasis.PER_PAGE: 'per_page'>` while
  `repr(str(RuleBasis.PER_PAGE))` is `'per_page'`.
  Date/Author: 2026-06-24, addendum agent.

- Decision (mdformat churn, 2026-06-22): `make fmt` reflows every Markdown file
  in the tree (mdformat-all), not just touched files, so running it produces
  spurious churn across unrelated docs and re-wraps this ExecPlan. Per the
  pattern established by prior tasks (see the repo stash log "spurious make-fmt
  mdformat churn"), that churn is stashed rather than committed: this commit
  carries only hand-wrapped, markdownlint-clean prose for this ExecPlan and no
  changes to unrelated docs. `make markdownlint` (the gate) passes either way.

## Outcomes & retrospective

Delivered (2026-06-22), all four work items complete and committed, `make all`
green at HEAD:

- The roadmap 5.1.1 success criterion is met:
  `tests/test_rulepack_loader.py::test_bad_pattern_names_rule` loads
  `bad-pattern.toml` (rule `id = "broken"`, `pattern = "a("`) and asserts the
  raised `RulePackError` carries `rule_id == "broken"` and a message naming
  `broken`. The property suite generalises this across patterns and positions.
- The loader is a validating boundary, not a structural-only mirror of
  `parse_state`: every field is runtime-checked, and `_require_int` rejects
  `bool` (the `isinstance(True, int)` trap). The eleven missing/wrong-typed
  fixtures and matching parametrized assertions prove a cast-only boundary would
  fail the suite.
- The two failure channels are distinct types: `RulePackError` (exit-2 content
  fault, naming the rule) and `RulePackFileError` (exit-3 file/decode fault),
  asserted in both directions.
- No new dependency (stdlib `tomllib` + `re`); no CLI, envelope, or `sys.exit`;
  the loader package is read-only and detect-only. Four atomic commits, each
  gate-passing; one coderabbit run per work item (zero findings on WI4).

Field-shape decisions task 5.1.2 should be aware of when wiring `desloppify`:
`pack` is mandatory (advisory A2); a stray `page_words` on a non-`per_page` rule
is rejected, not ignored (advisory A3); `basis` is the closed set
`{manuscript, per_page}`. The §6.2 ai-isms and §6.3 device-ledger pack variants
(roadmap 7.1) may revisit these, since the device-ledger example omits `pack`
and uses a different rule vocabulary.

Hand-off note for task 5.1.2 (advisory A1): `contract/runner.py` currently
catches only `CycloptsError` and `StateInputError`. A bare
`RulePackError`/`RulePackFileError` reaching the runner today would be uncaught.
Task 5.1.2 must therefore either catch these two errors inside the `desloppify`
command body and map them to `ExitCode.USAGE_ERROR` / `ExitCode.STATE_ERROR`, or
extend the runner's `except` chain. This is explicitly *not* 5.1.1's job (the
loader stays a pure boundary), but it is a contract the loader's two error types
assume — record it so the hand-off is explicit, not silently presumed.

## Context and orientation

You are working inside the git worktree at
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-5-1-1`, on branch
`roadmap-5-1-1`. Do every edit here; never touch the control worktree.

Read these before starting, in order:

1. `docs/novel-ralph-harness-design.md` §6.1 "Rule-pack schema" (lines 512-533)
   — the authoritative shape: a versioned TOML file, each rule carrying
   `pattern`, `threshold`, and `basis`, with `page_words` on a `per_page` rule.
   This is the field inventory this task models.
2. `docs/novel-ralph-harness-design.md` §4.4 "`desloppify`" (lines 346-360) —
   why the pack exists and the detect-only, never-judge contract. Note the
   exit-2-on-malformed-pack statement (a malformed rule pack raises usage error
   code 2).
3. `docs/novel-ralph-harness-design.md` §3.1 "envelope" (lines 144-173) — the
   three independent `schema_version` numbers; the rule pack's is its own and
   must be validated, not coerced.
4. `docs/novel-ralph-harness-design.md` §9 (lines 668-711) and §10 (lines
   713-734) — the verification strategy (snapshot + boundary examples for
   desloppify, plus the loader/validator error-path coverage that is "the
   surface most exposed to bad input") and the failure mode "Rule-pack pattern
   invalid → exit 2, naming the offending rule id".
5. `docs/roadmap.md` lines 514-528 — task 5.1.1 itself: the requirement to load
   a pack of `pattern`/`threshold`/`basis` rules, validate `schema_version`, and
   reject malformed patterns with exit 2 naming the offending rule id; success
   = "fails loudly, naming the rule".
6. `docs/adr-001-deterministic-judgemental-boundary.md` — the detect-and-report
   rule the loader sits inside.
7. `docs/adr-002-toml-round-trip-tomlkit.md` — why writes use `tomlkit`
   (relevant only to confirm this *read-only* loader correctly uses `tomllib`,
   not `tomlkit`).
8. `docs/scripting-standards.md` "Language and runtime" and the regex/pathlib
   sections — but note cuprum (the "typed command execution" section) is *out of
   scope*: this task runs no subprocess.
9. `docs/developers-guide.md` "State and on-disk layout" (lines 256-280) — the
   parse-boundary pattern (`parse_state` pure; `load_state` thin `tomllib`
   convenience) this loader mirrors exactly.
10. `AGENTS.md` — code style, the 400-line cap, en-GB Oxford spelling, the
    Python testing rules, and the quality gates.

Skills to load before touching code:

- `python-router` first, then follow it to:
  - `python-data-shapes` — for the frozen/slotted/keyword-only dataclass and
    `StrEnum` choices and the "parse to a schema type at the boundary" rule.
  - `python-errors-and-logging` — for the `RulePackError`/`RulePackFileError`
    hierarchy (the `Error` suffix, narrow `except`, `raise … from …`).
  - `python-types-and-apis` — for the public function signatures.
  - `python-testing` — for the pytest structure and fixture placement.
  - `python-verification` then `hypothesis` — to confirm Hypothesis is the right
    adversary for the loader's validation invariants and to write the property
    tests (Work item 3). Do not pull in CrossHair or mutmut: they are not in the
    project's dev dependencies (only `hypothesis` and `syrupy` are), so adding
    them is a dependency change that breaches the Tolerances.
- `leta` for code navigation (`leta show`, `leta refs`, `leta grep`) and `sem`
  for history, per the standing rules.

Key existing files you will mirror or consume (do not modify them):

- `novel_ralph_skill/state/schema.py` — the house style for frozen, slotted,
  keyword-only dataclasses with numpy docstrings; the `__post_init__` freeze of
  read-only containers via `_freeze.py`. Your `Rule`/`RulePack` follow this.
- `novel_ralph_skill/state/parse.py` — the house style for the *structure* of a
  pure boundary constructor: `parse_state(mapping) -> State` is pure,
  `load_state(path)` is the thin `tomllib`-backed file convenience, every TOML
  array is coerced to a `tuple`. **Mirror this structure but not its validation
  discipline.** `parse_state` is structural-only: it narrows with `typ.cast`
  (which performs no runtime check) and lets a bad/missing field surface as a
  raw `KeyError`/`ValueError` (its `Raises` block, lines 208-213, says so, and
  defers mapping to "task 2.2.x"). Your `parse_rulepack`/`load_rulepack` keep the
  same *shape* (pure boundary, file-convenience split, array-to-tuple coercion)
  but add the validation `parse_state` lacks: a runtime `isinstance` guard on
  every field that raises `RulePackError` naming the offending rule. Do not copy
  the cast-and-let-it-surface idiom; that idiom is the exact anti-pattern the
  round-1 review flagged (B1).
- `novel_ralph_skill/contract/exit_codes.py` — the `enum.IntEnum` house style;
  your `RuleBasis` is a sibling `enum.StrEnum` (the same style the phase enum
  uses, per `state/phase.py`).
- `novel_ralph_skill/contract/runner.py` — `StateInputError` is the model for a
  typed, message-carrying exception that a command body raises and the runner
  maps to an exit code. Your two rule-pack errors follow the same idea (but live
  in the `rulepack` package, since they are raised by the loader, not the
  runner).
- `novel_ralph_skill/_freeze.py` — `freeze_mapping`/`freeze_sequence` for the
  `__post_init__` immutability guarantee.

New package layout (group by feature, AGENTS.md "Group by feature, not layer"):

```plaintext
novel_ralph_skill/rulepack/
  __init__.py      # package marker; may re-export the public surface
  errors.py        # RulePackError, RulePackFileError
  schema.py        # RuleBasis, Rule, RulePack
  parse.py         # parse_rulepack (pure), load_rulepack (tomllib file convenience)
```

## Plan of work

The work proceeds in four atomic, independently committable, gate-passable work
items. Each ends with `make all` green. Work items that touch only Python need
`make all`; Work item 4 touches Markdown and additionally needs `make
markdownlint` and `make nixie`.

### Work item 1 — typed rule-pack schema and error types

Implements: design §6.1 (rule shape), §3.1 (independent `schema_version`),
§4.4/§10 (the two failure channels), roadmap 5.1.1.

Create `novel_ralph_skill/rulepack/errors.py`:

- `RulePackError(Exception)` — malformed *pack content*: a bad `schema_version`,
  a missing or wrong-typed field, an unknown `basis`, a non-positive
  `page_words`, a negative `threshold`, or an uncompilable `pattern`. Carries
  `rule_id: str | None` (the offending rule, or `None` for a pack-level fault
  such as a bad `schema_version`) and `messages: tuple[str, ...]` for the
  envelope the command will build. The command (task 5.1.2) maps this to
  `ExitCode.USAGE_ERROR` (exit 2).
- `RulePackFileError(Exception)` — the pack file is absent, unreadable, or holds
  undecodable TOML. Carries `messages: tuple[str, ...]`. The command maps this
  to `ExitCode.STATE_ERROR` (exit 3).

Both follow the `StateInputError` pattern (store messages on the instance, call
`super().__init__`), and the python-errors-and-logging `Error`/exception-naming
guidance.

Create `novel_ralph_skill/rulepack/schema.py`:

- `class RuleBasis(enum.StrEnum)` with members `MANUSCRIPT = "manuscript"` and
  `PER_PAGE = "per_page"`, each with a docstring (the §6.1 counting bases).
- `@dataclasses.dataclass(frozen=True, kw_only=True, slots=True) class Rule`
  with fields: `id: str`, `pattern: str` (the source pattern, kept verbatim for
  reporting), `compiled: re.Pattern[str]` (the compiled form, so detection in
  5.1.2 never recompiles), `threshold: int`, `basis: RuleBasis`, and
  `page_words: int | None` (`None` unless `basis is RuleBasis.PER_PAGE`). numpy
  docstring per attribute.
- `@dataclasses.dataclass(frozen=True, kw_only=True, slots=True) class RulePack`
  with fields: `schema_version: int`, `pack: str` (the pack name, e.g.
  `"ai-isms"`), and `rules: tuple[Rule, ...]`. The `rules` tuple is already
  immutable; no `_freeze` needed unless a mapping field is added (it is not).
- `RULEPACK_SCHEMA_VERSION: int = 1` module constant (design §6.1 line 518),
  documented as independent of the envelope and state versions.

Validation lives in the parser (Work item 2), not in `__post_init__`, mirroring
`state/schema.py` (which carries shapes only; the §5.2 invariants live in the
parser/validator). The schema module performs no parsing and no validation.

Tests — `tests/test_rulepack_schema.py` (unit):

- Construct a `Rule` and a `RulePack` directly and assert every field round-trips
  to the right attribute (the depth/without-transposition guarantee, mirroring
  `tests/test_state_schema.py`).
- Assert `Rule` and `RulePack` are frozen (assigning a field raises
  `FrozenInstanceError`) and that `Rule.__slots__`/`RulePack.__slots__` exist
  (slotted).
- Assert `RuleBasis` has exactly the two members with the expected string values.
- Assert `RULEPACK_SCHEMA_VERSION == 1`.
- Assert `RulePackError` carries `rule_id` and `messages`; `RulePackFileError`
  carries `messages`. Assert both subclass `Exception` and are distinct types.

Validation: `make all` green; the new schema tests pass.

### Work item 2 — the pure boundary loader

Implements: design §6.1, §3.1, §4.4, §9 (the loader/validator is "the surface
most exposed to bad input"), §10 (the two failure channels), roadmap 5.1.1.

Create `novel_ralph_skill/rulepack/parse.py`. It mirrors the *structure* of
`novel_ralph_skill/state/parse.py` (pure `parse_*` boundary, thin `load_*` file
convenience, array-to-tuple coercion) but is a **validating** boundary: unlike
`parse_state`, it runtime-checks every field and raises a rule-naming
`RulePackError` rather than letting a `KeyError`/`TypeError` surface or trusting
a `typ.cast` (Constraints, B1).

Provide a small set of validating narrowing helpers — these replace the
`_table`/`typ.cast` helpers of `state/parse.py`, which only cast. Suggested
helpers (keep them private and well-docstringed):

- `_require(mapping, key, *, rule_id) -> object` — raise `RulePackError` naming
  the missing key (and `rule_id`) when `key not in mapping`; otherwise return the
  value. Use this instead of `mapping[key]` so a missing field never surfaces as
  a raw `KeyError`.
- `_require_str(mapping, key, *, rule_id) -> str` — `_require` then
  `isinstance(value, str)`; raise `RulePackError` naming the field and `rule_id`
  on a non-string. (`typ.cast` *after* the guard, only to satisfy the type
  checker.)
- `_require_int(mapping, key, *, rule_id) -> int` — `_require` then a guard that
  rejects non-`int`. **Reject `bool`** (`isinstance(True, int)` is `True` in
  Python): require `type(value) is int` or `isinstance(value, int) and not
  isinstance(value, bool)`. A TOML float or string for a numeric field must
  raise `RulePackError`, never be cast.
- `_optional(mapping, key) -> object | None` — `mapping.get(key)` for the
  absent-allowed case (`page_words` on a non-`per_page` rule, `pending_turn`-like
  optionals).

`parse_rulepack(raw: cabc.Mapping[str, object]) -> RulePack` — pure: a decoded
mapping in, a validated `RulePack` out. Validation steps, each raising
`RulePackError` (with `rule_id` where applicable) on failure, each performed with
a runtime `isinstance`/membership guard (never a bare `typ.cast`):

1. `schema_version` present (else `RulePackError(rule_id=None, …)`), an `int`
   (reject `bool`, `str`, `float`), and equal to `RULEPACK_SCHEMA_VERSION`;
   otherwise `RulePackError(rule_id=None, …)` naming the unexpected version
   (design §3.1: report, do not coerce).
2. `pack` present (else `RulePackError(rule_id=None, …)`) and a `str`.
3. `rule` present, a `list`, and **non-empty**; each entry a `Mapping`. A
   missing or empty `rule` array raises `RulePackError(rule_id=None, …)` naming
   the empty/absent pack body.
4. For each rule entry, build a `Rule`:
   - `id` present and a `str`. Resolve `id` **first** so it can be the `rule_id`
     in any subsequent error this entry raises (the error must name the offending
     rule). If `id` itself is missing/non-string, raise
     `RulePackError(rule_id=None, …)` stating the rule's *index* in the array
     (there is no id to name yet).
   - `pattern` present and a `str`; compiled with `re.compile`, catching
     `re.error` and re-raising `RulePackError(rule_id=id, …) from exc` — this
     is the roadmap's headline behaviour. A missing or non-string `pattern`
     raises `RulePackError(rule_id=id, …)` *before* compilation is attempted.
   - `threshold` present, an `int` (reject `bool`/`str`/`float`), and `>= 0`; a
     negative `threshold` raises `RulePackError(rule_id=id, …)`.
   - `basis` present, a `str`, and a `RuleBasis` member. Coerce via
     `RuleBasis(value)`, catching `ValueError` and re-raising
     `RulePackError(rule_id=id, …) from exc` (Decision Log "basis is a closed
     set"). An unknown `basis` therefore names the rule.
   - `page_words`: required and a positive `int` (reject `bool`/`str`/`float`,
     reject `<= 0`) when `basis is RuleBasis.PER_PAGE`; must be **absent**
     otherwise — a stray `page_words` on a non-`per_page` rule raises
     `RulePackError(rule_id=id, …)` (Decision Log; this is a strictness choice,
     advisory A3).
5. Coerce the rule array to a `tuple[Rule, ...]` (the §6.1 order is the
   authoring order), mirroring how `parse_state` coerces every TOML array to a
   tuple.

`load_rulepack(path: Path) -> RulePack` — the thin file convenience: open
`path` in binary mode, decode with `tomllib.load`, delegate to `parse_rulepack`.
Wrap `FileNotFoundError`, `PermissionError`, `OSError`, and
`tomllib.TOMLDecodeError` into `RulePackFileError` (exit-3 channel) via
`raise … from exc`. A `RulePackError` from `parse_rulepack` propagates unchanged
(exit-2 channel).

Keep the module under 400 lines (split a `_rule(entry, *, index) -> Rule`
constructor out, as `state/parse.py` splits `_novel`, `_phase`, etc.). The
validating helpers above keep each constructor short.

Fixture data — create `tests/data/rulepacks/`:

- `valid.toml` — a minimal well-formed pack with one `manuscript` rule
  (`threshold = 0`) and one `per_page` rule (`threshold = 5`, `page_words =
  300`), echoing the §6.1 example.
- `bad-pattern.toml` — a structurally valid pack whose rule `id = "broken"`
  carries `pattern = "a("` (the uncompilable pattern from the empirical check).
- `bad-version.toml` — `schema_version = 2`.
- `unknown-basis.toml` — a rule with `basis = "per_paragraph"`.
- `per-page-missing-page-words.toml` — a `per_page` rule with no `page_words`.
- `negative-threshold.toml` — a rule with `threshold = -1`.
- `undecodable.toml` — syntactically broken TOML (for the `TOMLDecodeError` →
  exit-3 path).

Plus the **missing/wrong-typed-field** fixtures the round-1 review (B2) requires
— exactly the faults a non-validating `typ.cast` boundary would wave through, so
their presence proves the boundary actually validates:

- `missing-id.toml` — a rule with no `id` key (error names the rule *index*,
  `rule_id is None`).
- `missing-pattern.toml` — a rule (`id = "noprose"`) with no `pattern` key
  (`rule_id == "noprose"`).
- `non-string-pattern.toml` — `pattern = 42` (integer, not a string;
  `rule_id` names the rule).
- `non-integer-threshold.toml` — `threshold = "0"` (a TOML string; must raise,
  not be cast to/treated as `0`).
- `float-threshold.toml` — `threshold = 0.0` (a TOML float; must raise — a float
  is not an `int`).
- `non-integer-page-words.toml` — a `per_page` rule with `page_words = "300"`
  (a TOML string; must raise).
- `non-integer-schema-version.toml` — `schema_version = "1"` (a TOML string;
  must raise with `rule_id is None`, not be cast).
- `missing-pack.toml` — no top-level `pack` key (`rule_id is None`).
- `missing-rule-array.toml` — a pack with `schema_version`/`pack` but no `rule`
  array at all (`rule_id is None`).
- `empty-rule-array.toml` — `rule = []` declared with no `[[rule]]` entries, or
  the TOML equivalent of an empty array (`rule_id is None`).
- `stray-page-words.toml` — a `manuscript` rule that nonetheless carries
  `page_words = 300` (the strict-rejection case, advisory A3; `rule_id` names the
  rule).

(Per AGENTS.md, "Large blocks of test data should be moved to external data
files"; these packs are small but external keeps the test bodies readable and
lets the e2e/loader tests share them.)

Tests — `tests/test_rulepack_loader.py` (unit + boundary + CLI-error-path-style
channel coverage, per design §9's desloppify error-path paragraph):

- `load_rulepack("valid.toml")` returns a `RulePack` with two rules, the
  `per_page` rule's `page_words == 300`, and both `compiled` patterns matching a
  known string (proves patterns compiled).
- `load_rulepack("bad-pattern.toml")` raises `RulePackError`, and the raised
  error's `rule_id == "broken"` and a message names `broken` — the roadmap
  success criterion, asserted directly.
- `load_rulepack("bad-version.toml")` raises `RulePackError` with `rule_id is
  None` and a message naming the unexpected version.
- `load_rulepack("unknown-basis.toml")`, `…per-page-missing-page-words.toml`,
  `…negative-threshold.toml` each raise `RulePackError` naming the offending
  rule id (the exit-2 channel).
- **Missing/wrong-typed-field assertions (B2), each `RulePackError` with the
  correct `rule_id`.** Parametrize over the new fixtures so a non-validating
  (cast-only) implementation fails the suite:
  - `missing-id.toml` → `RulePackError`, `rule_id is None`, message names the
    rule index.
  - `missing-pattern.toml` → `RulePackError`, `rule_id == "noprose"`.
  - `non-string-pattern.toml` → `RulePackError` naming the rule (and **not** a
    raw `re.error`/`TypeError`).
  - `non-integer-threshold.toml` and `float-threshold.toml` → `RulePackError`
    naming the rule; explicitly assert the loader does **not** treat `"0"`/`0.0`
    as a valid `threshold` of `0`.
  - `non-integer-page-words.toml` → `RulePackError` naming the rule.
  - `non-integer-schema-version.toml` → `RulePackError`, `rule_id is None`
    (asserting `"1"` is **not** cast to the integer `1`).
  - `missing-pack.toml` → `RulePackError`, `rule_id is None`.
  - `missing-rule-array.toml` and `empty-rule-array.toml` → `RulePackError`,
    `rule_id is None`.
  - `stray-page-words.toml` → `RulePackError` naming the rule (strict-rejection,
    A3).
- `load_rulepack` on a non-existent path raises `RulePackFileError` (exit-3
  channel), not `RulePackError`.
- `load_rulepack("undecodable.toml")` raises `RulePackFileError` (decode fault is
  exit-3), not `RulePackError` — the channel split from the Risks section.
- A focused unit test on `parse_rulepack` directly (mapping in) covering at least
  the bad-pattern, missing-`id`, wrong-typed-`threshold`, and good cases, proving
  the pure boundary validates and is reusable without a filesystem (mirrors
  `parse_state`'s pure-boundary tests). Build the wrong-typed cases as in-memory
  mappings (e.g. `{"threshold": "0"}`) so the `isinstance` guard is exercised
  directly, independent of TOML decoding.

Validation: `make all` green; the channel-split assertions pass.

### Work item 3 — Hypothesis property coverage

Implements: AGENTS.md "Use property tests with `hypothesis` … when a change
introduces an invariant over a range of inputs"; design §9 (the loader is the
input-exposed surface). The loader's *invariants* — not its envelope — earn
property coverage; the envelope/snapshot coverage of `desloppify` is task
5.1.2's, per design §9 ("`desloppify` … need only snapshot coverage … not a
property-based suite of their own"), so this item stays scoped to the loader's
validation invariants, which *are* an invariant over a range of inputs.

Tests — `tests/test_rulepack_properties.py` (load the `hypothesis` skill first;
read `tests/test_contract_properties.py` for the established `@given`/`@settings`
precedent this suite must follow — see "Hypothesis configuration" below):

- Strategy that builds *well-formed* rule mappings (valid `id`, a curated set of
  always-compilable patterns, `threshold >= 0`, a `basis` drawn from
  `RuleBasis`, and `page_words` present iff `per_page`). Property:
  `parse_rulepack` accepts every such pack and the returned `RulePack` preserves
  rule count, order, and each rule's `id`/`threshold`/`basis` — the round-trip
  fidelity invariant. Avoid the filtering trap (build valid inputs directly;
  do not `.filter()` away invalid ones).
- Property: for a well-formed pack mutated to carry a `schema_version` drawn from
  `integers().filter(!= 1)` *constructed directly* (use
  `integers().map`/exclusion via `assume` sparingly), `parse_rulepack` raises
  `RulePackError`. Keep the mutation construction direct to avoid heavy
  filtering.
- Property: for any rule whose `pattern` is drawn from a small curated set of
  *known-uncompilable* patterns (`"a("`, `"["`, `"(?P<>x)"`), `parse_rulepack`
  raises `RulePackError` whose `rule_id` equals that rule's `id`. This is the
  "names the offending rule" invariant, generalised across patterns and
  positions.

**Hypothesis configuration under the project harness (B3).** `make test` runs
`pytest -v -n auto` (Makefile line 116, `PYTEST_XDIST_WORKERS ?= auto` line 14)
with a global `timeout = 30` per test (`pyproject.toml` line 325) and **no**
registered Hypothesis profile or deadline override anywhere in the tree. Each
`@given` test must therefore stay well inside the 30 s per-test wall clock while
sharing CPU with the other xdist workers. Follow the established precedent in
`tests/test_contract_properties.py` (read it first):

- **Strategies only; no function-scoped fixtures in any `@given` test.** That
  file's header comment records the rule: a `@given` test that takes a
  function-scoped fixture trips `HealthCheck.function_scoped_fixture`. Build the
  fixture-`tmp_path`-free packs entirely from strategies and call
  `parse_rulepack` on the in-memory mapping (never `load_rulepack`, so no
  filesystem and no `tmp_path` fixture is involved). If a property genuinely
  needs a session-scoped resource, suppress the health check explicitly with
  `@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])` as that
  file does, and document why.
- **Bound the work with an explicit `@settings`.** Add
  `@settings(max_examples=100, deadline=timedelta(milliseconds=400))` (or a
  smaller `max_examples`) to each property. The default 200 ms per-example
  deadline is tight when an example compiles a regex; a 400 ms deadline absorbs
  worker-scheduling jitter under `-n auto` without masking a real slowdown.
  100 examples, each a sub-millisecond build plus a single cheap `re.compile`,
  stay far under the 30 s wall timeout even on a contended worker.
- **Keep each generated pattern cheap to compile.** Draw patterns from a small
  curated literal set (for the well-formed strategy) or a small curated
  uncompilable set (for the names-the-rule strategy). Do **not** generate
  arbitrary regex source: a pathological generated pattern can make
  `re.compile` slow or hang and blow the deadline/timeout. This is the concrete
  mechanism that keeps the suite deterministic and inside 30 s.

Import `from datetime import timedelta` and
`from hypothesis import HealthCheck, settings` alongside `given`/`strategies`.
Register no new Hypothesis profile (the bounded `@settings` per test suffice;
the project has no profile registry and this task should not add one). Do not
add a new dependency.

Validation: `make all` green; property tests pass deterministically and each
completes well within the 30 s per-test timeout under `pytest -n auto` (no flaky
strategy, no deadline/timeout breach).

### Work item 4 — developers-guide documentation

Implements: AGENTS.md "Document internally facing interfaces … in the relevant
component architecture document" and "Internal interfaces"; design §6.1.

Edit `docs/developers-guide.md`: add a short subsection (mirroring the "State and
on-disk layout" entry, lines 256-280) under the harness-architecture section,
describing the rule-pack loader: the `novel_ralph_skill/rulepack/` package, the
pure `parse_rulepack(mapping) -> RulePack` boundary and the thin
`load_rulepack(path)` `tomllib` convenience, the `RuleBasis` closed set, the
independent `schema_version`, and the two failure channels (`RulePackError` →
exit 2 naming the rule; `RulePackFileError` → exit 3), noting that task 5.1.2
wires the `desloppify` command on top. Cross-reference design §4.4 and §6.1.

Wrap prose at 80 columns, code blocks at 120, use `-` bullets and GFM footnotes
if any. Do not add a Mermaid diagram unless one clarifies the boundary; if added,
it must pass `make nixie`.

Validation: `make markdownlint` and `make nixie` green; `make all` still green.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-5-1-1`.

1. Confirm the branch and a clean tree:

   ```bash
   git -C /data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-5-1-1 \
     branch --show-current
   ```

   Expect `roadmap-5-1-1`.

2. Work item 1 — write `novel_ralph_skill/rulepack/__init__.py`,
   `errors.py`, `schema.py`, and `tests/test_rulepack_schema.py`. Then:

   ```bash
   make all
   ```

   Expect all gates green and the new schema tests collected and passing.
   Commit (see commit-message skill; file-based message, imperative mood).

3. Work item 2 — write `novel_ralph_skill/rulepack/parse.py`, the
   `tests/data/rulepacks/*.toml` fixtures, and `tests/test_rulepack_loader.py`.
   Then `make all`. The headline assertion to watch:

   ```plaintext
   tests/test_rulepack_loader.py::test_bad_pattern_names_rule PASSED
   ```

   Commit.

4. Work item 3 — write `tests/test_rulepack_properties.py`. Then `make all`.
   Commit.

5. Work item 4 — edit `docs/developers-guide.md`. Then:

   ```bash
   make markdownlint
   make nixie
   make all
   ```

   Expect all green. Commit.

Each `make all` runs `build check-fmt lint typecheck test` (Makefile line 28).
Do not run the sub-targets in parallel; let Cargo/SlipCover caching serialise
(global instructions). Commit only when every gate for that work item is green.

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes; the new tests
  `tests/test_rulepack_schema.py`, `tests/test_rulepack_loader.py`, and
  `tests/test_rulepack_properties.py` all pass. The named test
  `tests/test_rulepack_loader.py::test_bad_pattern_names_rule` fails at import
  before Work item 2 (module absent) and passes after — proving the roadmap
  5.1.1 success criterion that an invalid regular expression fails loudly,
  naming the rule.
- Lint/typecheck: `make lint` (Ruff, `interrogate` 100% docstrings, Pylint) and
  `make typecheck` (`ty check`) pass. `make check-fmt` passes.
- Audit: `make audit` (`pip-audit`) passes — no new dependency is introduced.
- Markdown (Work item 4 only): `make markdownlint` and `make nixie` pass.

Quality method (how we check):

- `make all` after each work item, plus `make markdownlint` and `make nixie`
  for Work item 4. The full command surface is the CI gate; running `make all`
  locally reproduces it.

Behavioural acceptance, phrased as observable behaviour:

- Loading `tests/data/rulepacks/valid.toml` yields a `RulePack` of two rules
  with compiled patterns; the `per_page` rule reports `page_words == 300`.
- Loading `tests/data/rulepacks/bad-pattern.toml` raises `RulePackError` whose
  `rule_id` is `"broken"` and whose message names `broken`.
- Loading a pack with `schema_version = 2` raises `RulePackError` naming the
  unexpected version (not silently coerced).
- Loading an absent path or `undecodable.toml` raises `RulePackFileError` (the
  exit-3 channel), distinct from the exit-2 `RulePackError`.

## Idempotence and recovery

Every step is additive (new package, new tests, new fixtures, one
documentation subsection) and re-runnable. `make all` is idempotent. If a work
item's gate fails, fix forward within the iteration tolerance (3 attempts) and
re-run `make all`; do not commit a red gate. No step is destructive; there is
nothing to roll back beyond `git restore` on the uncommitted files. If a
property test flakes, it indicates a strategy that is not building inputs
directly — fix the strategy (avoid the filtering trap) rather than re-running for
a green.

## Interfaces and dependencies

Use the standard-library `tomllib` (read) and `re` (compile). No new external
dependency. cuprum is not used (no subprocess; design §9). At the end of the
work, these public symbols must exist:

```python
# novel_ralph_skill/rulepack/errors.py
class RulePackError(Exception):
    rule_id: str | None
    messages: tuple[str, ...]

class RulePackFileError(Exception):
    messages: tuple[str, ...]

# novel_ralph_skill/rulepack/schema.py
import enum, re, dataclasses

RULEPACK_SCHEMA_VERSION: int  # == 1

class RuleBasis(enum.StrEnum):
    MANUSCRIPT = "manuscript"
    PER_PAGE = "per_page"

@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class Rule:
    id: str
    pattern: str
    compiled: re.Pattern[str]
    threshold: int
    basis: RuleBasis
    page_words: int | None

@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class RulePack:
    schema_version: int
    pack: str
    rules: tuple[Rule, ...]

# novel_ralph_skill/rulepack/parse.py
import collections.abc as cabc
from pathlib import Path

def parse_rulepack(raw: cabc.Mapping[str, object]) -> RulePack: ...
def load_rulepack(path: Path) -> RulePack: ...
```

These names are stable contract for roadmap task 5.1.2, which builds the
`desloppify` detection logic on top of `load_rulepack` and maps `RulePackError`
to `ExitCode.USAGE_ERROR` and `RulePackFileError` to `ExitCode.STATE_ERROR`.

## Revision note

Initial draft (2026-06-22): first planning round. Decomposes roadmap task 5.1.1
into four atomic work items (schema + errors; pure loader; Hypothesis
properties; developers-guide). Pins the stdlib-only mechanism (`tomllib` read,
`re.compile` eager validation) against empirical checks recorded in Surprises &
Discoveries, and confirms cuprum is out of scope per design §9.

Round 2 (2026-06-22): resolved the three blocking points from the round-1
Logisphere review (`docs/execplans/roadmap-5-1-1.review-r1.md`).

- B1 (validating boundary): replaced every "mirrors `parse_state` exactly" /
  "use the `_table`/`typ.cast` narrowing helpers" instruction. The plan now
  states that `parse_rulepack` mirrors only the *structure* of `parse_state`
  (pure boundary, file-convenience split, array-to-tuple coercion) and is a
  **validating** boundary that runtime-`isinstance`-checks every field and
  raises a rule-naming `RulePackError`, never relying on a `typ.cast` (which
  performs no runtime check) or letting `KeyError`/`TypeError` surface. Added
  validating helper signatures (`_require`, `_require_str`, `_require_int`,
  `_optional`) that replace the cast-only helpers, and a Decision-Log entry.
  Affects Purpose, Constraints, the "key existing files" orientation, and
  Work item 2.
- B2 (missing/wrong-typed coverage): added eleven fixtures and matching
  parametrized assertions for missing/wrong-typed `id`, `pattern`, `threshold`
  (string and float), `page_words`, `schema_version`, `pack`, and a
  missing/empty `rule` array, each asserting `RulePackError` with the correct
  `rule_id`. Stated that non-integer `threshold`/`schema_version`/`page_words`
  must raise rather than be cast, added a `bool`-is-`int` trap Risk, and added an
  in-memory `parse_rulepack` unit test for the wrong-typed cases. Affects
  Work item 2's fixture list and test matrix, and Risks.
- B3 (Hypothesis under xdist + 30 s timeout): added a "Hypothesis configuration"
  paragraph requiring the property tests to follow the
  `tests/test_contract_properties.py` precedent — strategies-only inputs (no
  function-scoped fixtures), explicit bounded `@settings(max_examples≈100,
  deadline≈400ms)`, and curated cheap-to-compile patterns — and explained how
  this keeps each test inside the global `timeout = 30` under `pytest -n auto`
  with no new profile. Affects Work item 3 and Risks/Decision Log.

Also recorded the round-1 advisories: A1 (5.1.2 must catch the two errors or
extend `contract/runner.py`) in Outcomes; A2 (`pack` made mandatory
deliberately) and A3 (`page_words` strict-rejection) in the Decision Log.

Implementation round-1 fix (2026-06-23): resolved the three blocking items from
the dual implementation review (see the Decision Log entries dated 2026-06-23):

- Blocking item 1 (redundant casts): deleted the two `typ.cast` calls in
  `_require_str`/`_require_int`/`_rule`; `ty` had already narrowed after the
  `isinstance` guards, so they were the tree's only two `redundant-cast`
  warnings. `make typecheck` now reports zero diagnostics. The genuine widening
  cast in `_entries` is kept.
- Blocking item 2 (silent unknown keys): added `_reject_unknown_keys` and the
  closed `_PACK_KEYS`/`_RULE_KEYS` vocabularies; an unknown rule key names the
  rule, an unknown pack key names the pack level. Fixtures
  `unknown-rule-key.toml` and `unknown-pack-key.toml` plus loader and in-memory
  tests.
- Blocking item 3 (silent duplicate ids): added `_reject_duplicate_ids` in
  `parse_rulepack`, naming the colliding id. Fixture `duplicate-id.toml` plus
  loader and in-memory tests.

`make all` is green (210 passed) and one `coderabbit review --agent` run returned
zero findings. A follow-up note: `parse.py` now exceeds the ungated 400-line
AGENTS.md guideline and should be split in a later refactor (recorded in the
Decision Log).

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
post-merge audit (`docs/issues/audit-5.1.1.md`). Execute each as a small
addendum pass — no plan or design-review cycle: make the change, run `make all`
(plus `make markdownlint`/`make nixie` for Markdown), `coderabbit review
--agent`, commit, and tick the matching roadmap sub-task on merge. The
substantial cross-layer finding (the shared envelope-`messages` exception base
spanning `contract` and `rulepack`) was re-routed to roadmap step 1.3 (task
1.3.4); the duplicate "ship a canonical pack as an artefact" suggestion is
already owned by roadmap task 7.1.1 and is dropped here. These five are the
small fixes, doc gaps, and coverage only.

- [x] 5.1.1.1 — Document the on-disk rule-pack TOML format for pack authors
  (from audit:5.1.1, medium). Add a worked fenced TOML example to the developers'
  guide "Rule packs" section showing both bases (a `manuscript` rule with
  `threshold = 0`, a `per_page` rule with `page_words`) and enumerate the v1 key
  vocabulary (`schema_version`, `pack`, per-rule `id`/`pattern`/`threshold`/
  `basis`/`page_words`) with the strict rules the loader enforces (`page_words`
  required iff `per_page`; ids unique; unknown keys rejected). Gate with
  `make markdownlint` and `make nixie`.
- [x] 5.1.1.2 — Make `parse_rulepack`'s total exception surface explicit (from
  audit:5.1.1, low). Add one sentence to its `Raises`/`Notes` stating
  `RulePackError` is the only exception the pure boundary raises and that file
  and decode faults belong to `load_rulepack` (`RulePackFileError`), pinning the
  contract task 5.1.2 catches against. Gate with `interrogate` via `make all`.
- [x] 5.1.1.3 — Route every per-rule diagnostic through `_where(rule_id)` (from
  audit:5.1.1, low). Replace the six inline `f"rule {rule_id!r} …"` prefixes in
  `_compile_pattern`, `_resolve_basis`, `_resolve_page_words`, `_rule`, and
  `_reject_duplicate_ids` with `_where(rule_id)`. Internal only; the public
  `error.rule_id` and existing substring assertions are unchanged. Gate with
  `make all`.
- [x] 5.1.1.4 — Reconcile `_entries`' concrete `list`/`dict` guard with the
  boundary's advertised `Mapping` input and pin it with a test (from audit:5.1.1,
  low; merges Findings 5 and 6). Pick one: tighten the documented contract to a
  `tomllib`-shaped mapping (arrays `list`, tables `dict`), or loosen the guards
  to abstract shapes (`cabc.Sequence` not `str`/`bytes`; `cabc.Mapping`); then
  add the matching purity test — a `MappingProxyType` pack that loads, or a
  recognisable error on a non-`list` `rule` value — so the contract is asserted
  rather than implied. Gate with `pyright`/Ruff/`pytest` via `make all`.
- [x] 5.1.1.5 — Drop the redundant `str(...)` wrappers in the `RuleBasis`
  diagnostic builders (from audit:5.1.1, low). `RuleBasis` is a `StrEnum`, so
  `repr(member)` and `basis!r` render identically; remove the `str(...)` in
  `_resolve_basis` and `_resolve_page_words` (or add a one-line `StrEnum` note).
  Cosmetic; the `unknown-basis` assertions are unchanged. Gate with `make all`.
- [x] 5.1.1.6 — Split `rulepack/parse.py` to bring it under the 400-line file
  cap (from audit:1.3.5, low; re-surfaced from audit:2.2.2 Finding 5).
  `novel_ralph_skill/rulepack/parse.py` is 515 lines, breaching the AGENTS.md
  400-line file cap. Extract the scalar-coercion helpers into a
  `rulepack/_coerce.py` leaf module (no new public surface; `parse.py` re-imports
  what it needs) so the cap breach is recorded as actionable work and resolved
  rather than normalised. Gate with `make all`.
