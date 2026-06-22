# Post-merge audit — roadmap task 2.1.2

Audit of the codebase after roadmap task 2.1.2 ("Implement the invariant
validator behind `novel-state check`") merged to `main` at commit `895343c`.
The slice delivers the §5.2 pure-state validator
([`validate.py`](../../novel_ralph_skill/state/validate.py): `validate_state`,
`Violation`, the eight owned invariant-name constants, and
`PURE_STATE_INVARIANT_NAMES`) and wires it behind the read-only `check`
subcommand
([`novel_state.py`](../../novel_ralph_skill/commands/novel_state.py):
`build_app`, `_check`, `parse_global_flags`). It is re-exported from the
[`state` package `__init__.py`](../../novel_ralph_skill/state/__init__.py),
documented in the developers' guide §"Invariant validation" and the users'
guide, and guarded by the corpus-agreement suite
([`tests/test_validate_state_corpus.py`](../../tests/test_validate_state_corpus.py)),
the Hypothesis property suite
([`tests/test_validate_state_property.py`](../../tests/test_validate_state_property.py)),
and the behavioural/e2e suite
([`tests/test_novel_state_check.py`](../../tests/test_novel_state_check.py)).

The slice is sound and discharges its success criterion: a self-contradicting
`state.toml` exits `4` naming each breached invariant, a coherent one exits `0`
with an empty `result.violations`, and a missing or unparseable file is routed
to the separate exit-`3` state-error channel. The checker/mutator split (design
§5.4) holds (`check` writes nothing, pinned by `test_check_writes_nothing`), the
validator is total over every constructible `State` (the `target <= 0` guard,
Decision Log B7), the verdict order is deterministic, and the
deterministic/judgemental boundary (ADR-001) is respected (the validator checks
self-consistency, never judges prose). The findings below are tidy-up,
consistency, duplication, and coverage opportunities; none is a blocking defect.

## 1. Knitting-gate thresholds duplicated across three modules (`(0.30, 0.50, 0.80)`)

- **Category:** duplication
- **Severity:** medium
- **Location:** [`novel_ralph_skill/state/validate.py:73`](../../novel_ralph_skill/state/validate.py)
  (`_GATE_THRESHOLDS`), [`tests/working_corpus/_specs.py:44`](../../tests/working_corpus/_specs.py)
  (`GATE_THRESHOLDS`), [`tests/test_validate_state_property.py:52`](../../tests/test_validate_state_property.py)
  (`_GATE_THRESHOLDS`).

The literal triple `(0.30, 0.50, 0.80)` is defined three times. The corpus
`_specs.GATE_THRESHOLDS` even carries the comment "the single source of truth
`0.30 / 0.50 / 0.80`", yet the production validator and the property suite each
keep their own private copy of the same numbers. The property suite's
`_gates_for_ratio` deliberately mirrors the validator's `ratio >= threshold`
comparison (Decision Log A5), so if the production thresholds ever changed the
property suite could silently agree with a wrong validator because it reads its
own copy rather than the validator's.

**Proposed fix:** make `validate._GATE_THRESHOLDS` the single production source
of truth (it is the §5.2 design constant). Have `tests/test_validate_state_property.py`
import the production constant
(`from novel_ralph_skill.state.validate import _GATE_THRESHOLDS`, or expose a
read-only accessor) instead of redeclaring it, so the property suite cannot
drift from the validator it checks. Pin the corpus `_specs.GATE_THRESHOLDS`
equal to the production constant with a one-line test, the same way
`test_owned_names_equal_corpus_vocabulary` pins the invariant-name vocabulary;
this keeps the corpus's independent copy honest (intentional, so the oracle
stays an independent cross-check) without letting it drift unnoticed.

## 2. Validator predicates and corpus oracle are structural twins with no shared contract test of their algebra

- **Category:** similarity
- **Severity:** low
- **Location:** [`novel_ralph_skill/state/validate.py:93-250`](../../novel_ralph_skill/state/validate.py)
  vs [`tests/working_corpus/_oracle.py:70-174`](../../tests/working_corpus/_oracle.py).

Six of the validator's predicates (`_check_completed_prefix`,
`_check_consecutive_clean_within_target`, `_check_convergence_target_at_least_one`,
`_check_consecutive_clean_within_drafted`, `_check_cursor_coherent`,
`_check_gate_ratio_consistent`) are line-for-line structural twins of the
oracle's same-named predicates, differing only in the input type (`State`
attributes vs `WorkingTreeSpec` fields) and in returning `Violation | None` vs
`bool`. This duplication is **deliberate and correct**: the oracle is an
independent cross-check and must not import the thing it checks (the agreement
suite proves they agree on every corpus tree). The residual risk is that the
duplication is implicit — a reader editing one predicate has no in-code signal
that a twin exists and that the agreement suite is the safety net.

**Proposed fix:** no de-duplication (it would defeat the cross-check). Add a
short cross-reference comment at the head of each module's predicate block —
`validate.py` already cites the oracle per-predicate; add the reciprocal
pointer in `_oracle.py` so an editor of either side is told the twin exists and
that `test_incoherent_agreement_restricted_to_owned` is the contract that pins
their equivalence. Optionally record the deliberate-twin policy once in the
developers' guide so it reads as a design choice, not an oversight.

## 3. `_check_phase_in_enum` is unreachable on the production (disk) path

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:** [`novel_ralph_skill/state/validate.py:93-100`](../../novel_ralph_skill/state/validate.py)
  (`_check_phase_in_enum`) and the guard at
  [`validate.py:111`](../../novel_ralph_skill/state/validate.py)
  (`_check_completed_prefix`'s out-of-enum early return).

`parse_state` constructs `Phase(current)` and raises `ValueError` on any
out-of-enum phase, so a `State` loaded from disk can never carry an out-of-enum
`phase.current`. Consequently `_check_phase_in_enum` only fires for a `State`
built directly in-memory (the property suite's `_perturb_phase`), never on the
real `novel-state check` path, and `_check_completed_prefix`'s
`if … not in PHASE_ORDER: return None` guard is dead on that same disk path.
This is documented in the developers' guide and validator docstring, so it is
not a hidden trap — but the invariant is enforced in two layers (parser and
validator) with the validator layer being a pure-construction safety net only.

**Proposed fix:** keep both layers (the validator must stay total over any
constructible `State`), but make the redundancy explicit and tested. Add a unit
test asserting that `_check_phase_in_enum` fires for a directly-constructed
out-of-enum `State` (the property suite exercises it indirectly; a named unit
test documents the in-memory contract). The existing
`test_phase_in_enum_is_parser_enforced` already pins the disk-path side; a
paired in-memory test makes the two-layer design self-documenting.

## 4. `_check` couples I/O, parsing, validation, and envelope construction in one body

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:** [`novel_ralph_skill/commands/novel_state.py:74-119`](../../novel_ralph_skill/commands/novel_state.py)
  (`_check`).

`_check` resolves the path, loads and parses the file, maps five exception
types to `StateInputError`, runs the validator, and assembles two distinct
`CommandOutcome` shapes — four responsibilities in one function. The exit-`3`
exception tuple `(OSError, tomllib.TOMLDecodeError, KeyError, ValueError,
TypeError)` is the same set `tests/test_validate_state_corpus.py:_PARSE_ERRORS`
hand-lists (minus `OSError`), so the "what counts as a state-input error"
vocabulary is duplicated between production and test with no shared constant.

**Proposed fix:** extract the load-and-translate step into a small helper (e.g.
`_load_or_state_error(path) -> State`) that owns the exception-to-`StateInputError`
mapping, leaving `_check` to read as "load → validate → build outcome". Define
the state-input exception tuple as a named module constant and have the corpus
test reference it (or assert its own list is a subset), so the parse-error
vocabulary has one home. This also makes the mapping reusable for the four
later mutators that will hit the same load boundary.

## 5. The two `CommandOutcome` branches in `_check` repeat the result/messages plumbing

- **Category:** complexity
- **Severity:** low
- **Location:** [`novel_ralph_skill/commands/novel_state.py:108-119`](../../novel_ralph_skill/commands/novel_state.py).

The coherent and incoherent branches each construct a `CommandOutcome` with a
hand-written `result={"violations": …}` and `messages=…`. The shapes are close
enough that the "violations" key and the verdict-to-messages projection could be
expressed once, with only the exit code differing.

**Proposed fix:** compute the verdict once, then build a single `CommandOutcome`
whose `code` is `SUCCESS` when the verdict is empty else `ACTIONABLE_FINDING`,
`result={"violations": [v.invariant for v in verdict]}`, and
`messages=[v.detail for v in verdict] or ["state is coherent"]`. This removes
the branch duplication and makes the "empty verdict ⇒ success" rule a single
expression rather than two parallel constructors.

## 6. Validator subtly distinguishes "eight invariant names" from "seven §5.2 invariants" only in prose

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`novel_ralph_skill/state/validate.py:42-69`](../../novel_ralph_skill/state/validate.py)
  and [`docs/developers-guide.md:289`](../../docs/developers-guide.md).

The validator owns **eight** names but covers only design §5.2 invariants 1, 2,
3, 4, 6, and 7 — invariant 4 is split into three sub-rules, and invariant 5
(`manifest-disk-bijection`) is deferred to §5.4 / task 2.3.2. The mapping from
"eight names" to "the design's numbered invariants" (which numbers are covered,
which split, which deferred) lives only in scattered prose. A maintainer
counting design invariants against owned names could mis-conclude a gap.

**Proposed fix:** add a compact mapping table — design invariant number → owned
name(s) / deferred — to the validator module docstring or the developers' guide
§"Invariant validation", e.g. "§5.2 inv 4 → {within-target, at-least-one,
within-drafted}; §5.2 inv 5 → manifest-disk-bijection (deferred, task 2.3.2)".
This makes the eight-vs-seven relationship checkable at a glance.

## 7. Users' guide does not enumerate the eight invariant names `result.violations` can carry

- **Category:** docs-gap
- **Severity:** low
- **Location:** [`docs/users-guide.md:92-109`](../../docs/users-guide.md).

The users' guide explains that `novel-state check` exits `4` and names breached
invariants, but does not list the eight names a user might see in
`result.violations` (`phase-in-enum`, `completed-prefix`, `by-chapter-sum`, the
three `consecutive-clean-*` / `convergence-*` sub-rules, `cursor-coherent`,
`gate-ratio-consistent`). A user reading an exit-`4` envelope has no reference
explaining what each name means or how to remedy it.

**Proposed fix:** add a short reference list (name → one-line plain-English
meaning) to the users' guide `novel-state check` section, noting that the set is
the pure-state half and that disk-evidence invariants arrive in a later release.
This closes the loop between the envelope a user sees and the guide.

## 8. No test pins the `Violation.detail` prose, leaving the human-facing message channel uncovered

- **Category:** test-gap
- **Severity:** low
- **Location:** [`novel_ralph_skill/state/validate.py:77-250`](../../novel_ralph_skill/state/validate.py)
  (the `detail` field) and the test suites.

Every test asserts on `violation.invariant` (the machine name) but none asserts
on `violation.detail`, the human-readable prose surfaced in the envelope's
`messages` and rendered for `--human`. A predicate could compute a wrong or
empty `detail` (e.g. an f-string referencing the wrong attribute) and every
existing test would still pass. The detail strings embed live values
(`f"sum(by_chapter) {drafted_total} != current {…}"`) that are exactly the kind
of message most likely to rot under refactor.

**Proposed fix:** add a focused test (or a snapshot) asserting that each
predicate's `detail` is non-empty and mentions the offending values for a known
breach — at minimum one assertion per invariant that `detail` contains the
expected numbers/identifiers. This brings the human-facing channel under the
same coverage as the machine-name channel.

## 9. `parse_global_flags` lives in the command module but is a generic argv concern reused by four later commands

- **Category:** separation-of-concerns
- **Severity:** low
- **Location:** [`novel_ralph_skill/commands/novel_state.py:44-71`](../../novel_ralph_skill/commands/novel_state.py)
  (`parse_global_flags`, `_HUMAN_FLAG`).

The docstring states the conventions this module sets "are the ones the four
later commands inherit", and `parse_global_flags` is a command-agnostic `--human`
splitter (ADR-003 §3.1) with no dependency on `novel-state`. Leaving it in the
`novel_state` command module means the four later command entry points must
either import it cross-command from `novel_state` (an awkward dependency
direction between sibling commands) or re-implement it.

**Proposed fix:** when the second command lands, hoist `parse_global_flags` and
`_HUMAN_FLAG` into a shared seam (e.g. `novel_ralph_skill.contract.runner` or a
small `commands/_global_flags.py`) so every command imports the one splitter and
no command depends on a sibling. Recorded now as a pre-emptive note; it is not
worth moving until a second consumer exists, but the eventual home should be
chosen before that import direction sets.
</content>
</invoke>
