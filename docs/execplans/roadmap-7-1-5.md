# Derive the envelope field order from the `Envelope` dataclass everywhere

This ExecPlan (execution plan) is a living document. The sections
`Constraints`, `Tolerances`, `Risks`, `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work
proceeds.

Status: COMPLETE (all four work items landed and gated)

## Purpose / big picture

Roadmap task 7.1.5 removes the last hand-spelled copies of the envelope's
six-name field order so that the order has a single canonical home: the
`Envelope` dataclass declaration. After this change, adding, removing, renaming,
or reordering an envelope field is a one-line edit to the dataclass that every
renderer and every test oracle inherits automatically, instead of a four-way
hand-edit that can silently drift.

The envelope is the shared JSON object every deterministic command emits on
stdout (design §3.1; ADR-003). Its field order is fixed by contract:
`command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`. Roadmap
task 6.3.7 already made `dataclasses.fields(Envelope)` the canonical source for
the agent-facing `SKILL.md` copy of that order (its drift-guard reads the
dataclass), but three sites still spell the same order by hand:

- `render_machine` in `novel_ralph_skill/contract/envelope.py` (the renderer of
  record) builds an `ordered` dict by listing the six keys in sequence
  (line 143);
- `_FIXED_FIELD_ORDER` in `tests/test_contract_envelope.py` (line 33) is a
  literal six-tuple that asserts `render_machine`'s output order;
- `ENVELOPE_KEY_ORDER` in `tests/cross_command_contract/__init__.py` (line 81)
  is a second literal six-tuple, reused across roughly seven cross-command
  identity assertions via `assert_envelope_skeleton`
  (`tests/cross_command_contract/_identity_assertions.py:96`).

This is the precise "single un-pinned copy" pattern §6.3 set out to eliminate,
left standing one layer down in the code the SKILL guard imports (audit:6.3.7
Finding 1, severity medium).

After this change a reader can observe the single canonical home directly:

- `make test` stays green (no behaviour changes).
- Editing the order of fields in the `Envelope` dataclass (for example swapping
  `result` and `messages`) and running `make test` reddens exactly the one
  literal tripwire test plus the order assertions that read the renderer — never
  a hand-edit of a second literal copy that silently re-tracks the swap.
- `grep -n` for the six-name order across the renderer and the two test oracles
  finds the literal sequence in exactly one place (the tripwire test).

## Constraints

Hard invariants that must hold throughout implementation. Violation requires
escalation, not a workaround.

- The wire contract is frozen. `render_machine` must continue to emit a
  single-line JSON object with keys in the order
  `command, schema_version, ok, working_dir, result, messages` and identical
  values to today (design §3.1; ADR-003 §"Decision"). No snapshot under
  `tests/**/__snapshots__/` may change. If any `.ambr` snapshot would change,
  stop and escalate: that is a real contract regression, not a refactor.
- `render_machine` must keep coercing `result` to a plain `dict` and `messages`
  to a plain `list` before `json.dumps`, exactly as today (envelope.py
  lines 148-149). The dataclass stores `result`/`messages` as frozen
  read-only containers (`__post_init__`, lines 62-65, via
  `novel_ralph_skill/_freeze.py`); `json.dumps` of a `MappingProxyType` or a
  tuple is not guaranteed to round-trip to the same JSON, so the coercion is
  load-bearing and must survive the refactor.
- `ENVELOPE_KEY_ORDER` must remain a `tuple[str, ...]`: it is compared with
  `==` against `tuple(envelope)` in
  `tests/cross_command_contract/_identity_assertions.py` (line 96), and the
  module annotates it `typ.Final[tuple[str, ...]]`. `_FIXED_FIELD_ORDER` is
  likewise compared with `tuple(parsed)` (`tests/test_contract_envelope.py`
  line 165), so both oracles need a tuple, not a list.
- Exactly one literal six-name tripwire survives in the renderer-and-oracle
  scope. The new shared constant is *derived* from the dataclass; the human
  tripwire is the one place that re-spells the expected names by hand, so an
  accidental dataclass reorder reddens a test rather than silently propagating
  (audit:6.3.7 Finding 1 proposed fix, step 2).
- No file may exceed 400 lines after the change (AGENTS.md "Keep file size
  manageable").
- All prose, comments, docstrings, and the commit messages use en-GB Oxford
  spelling ("-ize"/"-yse"/"-our"; AGENTS.md / repository convention).
- 100% docstring coverage is enforced by `make lint`; every new public symbol
  (the `ENVELOPE_FIELD_ORDER` constant and any new helper) carries a docstring.

## Tolerances (exception triggers)

- Scope: if the implementation touches more than 4 files or more than ~120 net
  lines of code, stop and escalate. The expected footprint is one source file
  and two test files (plus this plan).
- Interface: the public signatures of `render_machine`, `render_human`,
  `build_envelope`, and `Envelope` must not change. If any must change, stop and
  escalate.
- Dependencies: no new external dependency. Only the stdlib `dataclasses`
  module (already imported in `envelope.py`) is used. If a new dependency seems
  needed, stop and escalate.
- Snapshots: if any `.ambr` snapshot file would change, stop and escalate (see
  Constraints).
- Iterations: if `make all` still fails after 3 fix attempts on any work item,
  stop and escalate.
- Ambiguity: the audit (audit:6.3.7 Finding 1) and the roadmap entry name three
  scoped sites. Work item 4 proposes an *optional* extension to the two existing
  drift-guard `_envelope_field_order()` helpers; if that extension turns out to
  widen scope or churn the §6.3 guards, drop it and record the decision rather
  than escalating (it is explicitly out of the roadmap's three-site scope).

## Risks

    - Risk: a naive "iterate fields and getattr" rewrite of render_machine drops
      the dict/list coercion of result/messages, producing JSON that differs
      (e.g. a MappingProxyType serialized differently) or a snapshot churn.
      Severity: medium
      Likelihood: medium
      Mitigation: keep an explicit per-field coercion (a small mapping of
      field-name to coercion callable, default identity) so result->dict and
      messages->list are preserved verbatim; the snapshot tests and the existing
      order assertion catch any regression (Work item 2).

    - Risk: changing ENVELOPE_KEY_ORDER from a literal tuple to an imported one
      breaks the `typ.Final` annotation or the tuple-equality comparison in the
      cross-command identity assertions.
      Severity: low
      Likelihood: low
      Mitigation: the shared constant is a tuple[str, ...]; re-export it under
      the existing names with the existing `typ.Final[tuple[str, ...]]`
      annotation; the cross-command suite pins the equality (Work item 3).

    - Risk: dataclasses.fields() ordering is assumed to equal declaration order.
      Severity: low
      Likelihood: low
      Mitigation: this is a documented CPython guarantee (fields are returned in
      definition order; requires-python is >=3.14, where this holds). The
      surviving literal tripwire test pins the exact six names in the exact
      order, so any drift between the assumed and actual ordering reddens a test
      rather than silently shipping (Work item 1).

    - Risk: a future contributor "tightens" the surviving tripwire or deletes it
      believing the dataclass derivation makes it redundant, removing the one
      human-readable anchor.
      Severity: low
      Likelihood: medium
      Mitigation: the tripwire test carries a docstring stating it is the
      deliberate human-readable contract anchor that must not be deleted
      (Work item 1).

## Progress

    - [x] Work item 1: promote the shared `ENVELOPE_FIELD_ORDER` constant and
      the surviving literal tripwire test. `ENVELOPE_FIELD_ORDER` added to
      `envelope.py` after the dataclass; `_FIXED_FIELD_ORDER` renamed to the
      documented tripwire `_EXPECTED_FIELD_ORDER`;
      `test_envelope_field_order_matches_expected` added;
      `test_render_machine_emits_fixed_field_order` repointed at the derived
      constant. `make all` green; no snapshot change.
    - [x] Work item 2: derive `render_machine`'s ordered mapping from the
      dataclass fields with explicit coercion. `render_machine` now iterates
      `ENVELOPE_FIELD_ORDER` and applies the `_FIELD_COERCIONS` map
      (`result -> dict`, `messages -> list`, others identity); docstring updated
      to state the order is read from the dataclass. Added
      `test_render_machine_coerces_frozen_containers_to_plain_json` (the
      medium-severity coercion regression test, fed a `MappingProxyType` and a
      tuple). `make all` green; no `.ambr` snapshot change. CodeRabbit: 0
      findings.
    - [x] Work item 3: import the shared constant into both test oracles,
      deleting the two hand-spelled tuples. `ENVELOPE_KEY_ORDER` in
      `tests/cross_command_contract/__init__.py` is now a single-line alias of
      `ENVELOPE_FIELD_ORDER` (name and `typ.Final[tuple[str, ...]]` annotation
      preserved, so the ~seven `_identity_assertions.py` consumers are
      untouched). Added `test_envelope_key_order_is_the_canonical_constant` to
      `tests/cross_command_contract/test_envelope_shape.py` pinning identity
      (`is`, not just `==`). Single-source proof: a `grep` for the literal
      six-name sequence across the renderer and the two oracles now finds it in
      exactly one place — the surviving `_EXPECTED_FIELD_ORDER` tripwire.
      `make all` green; CodeRabbit: 0 findings.
    - [x] Work item 4 (optional, in-scope-adjacent): route the two existing
      drift-guard `_envelope_field_order()` helpers through the shared constant.
      APPLIED. Both `_envelope_field_order()` helpers
      (`tests/test_skill_contract_drift_guard.py`,
      `tests/test_developers_guide_contract_drift_guard.py`) now
      `return list(ENVELOPE_FIELD_ORDER)`. The change was clean: in each file the
      imported `Envelope` symbol and `import dataclasses` were used *only* in the
      helper, so both were dropped and `ENVELOPE_FIELD_ORDER` imported in their
      place; no parsing or region logic was touched. Both §6.3 guard suites stay
      green; `make all` green; CodeRabbit: 0 findings.

## Surprises & discoveries

    - Work item 1 CodeRabbit review raised two findings, both against this
      ExecPlan markdown, neither an actionable code defect:
      (a) major — claimed the Constraints line "No file may exceed 400 lines"
      conflicts with the 400-line cap; this is a false positive: that line is a
      *constraint on the source files* (both well under 400 lines), not a claim
      about the plan file. Left as written.
      (b) minor — the runbook hardcodes the worktree root path; this is the
      canonical git-donkey worktree root the task's standing rules require the
      runbook to name verbatim, so the absolute path is intentional. Left as
      written.

## Decision log

    - Decision: derive the field order from `dataclasses.fields(Envelope)` and
      promote one shared `ENVELOPE_FIELD_ORDER` tuple beside the `Envelope`
      declaration in `novel_ralph_skill/contract/envelope.py`, rather than in a
      test module.
      Rationale: 6.3.7 already established the dataclass as canonical for the
      SKILL copy; co-locating the derived constant with the declaration keeps the
      production renderer and both test oracles importing from one home in the
      package, and matches the audit's proposed fix (audit:6.3.7 Finding 1, "promote
      ENVELOPE_FIELD_ORDER ... beside the Envelope definition in envelope.py").
      Date/Author: 2026-06-27, planning agent.

    - Decision: keep one literal six-tuple tripwire in
      `tests/test_contract_envelope.py` rather than deriving every assertion from
      the dataclass.
      Rationale: a fully derived test would pass vacuously after an accidental
      dataclass reorder (both sides move together). The roadmap success criterion
      requires "exactly one literal tripwire survives"; the audit names
      `test_contract_envelope.py` as the home for it. The tripwire pins the
      *expected* names so a reorder reddens a test.
      Date/Author: 2026-06-27, planning agent.

    - Decision: render_machine keeps an explicit per-field coercion (result->dict,
      messages->list, others identity) when iterating the dataclass fields, rather
      than a blanket getattr.
      Rationale: result/messages are stored frozen (MappingProxyType / tuple) by
      `__post_init__`; json.dumps must see a plain dict/list to reproduce today's
      wire output (Constraints). A blanket getattr would change the serialized
      shape and churn the snapshots.
      Date/Author: 2026-06-27, planning agent.

    - Decision: external-library research (cuprum, Cyclopts, pytest-timeout, uv)
      is not applicable to this task.
      Rationale: the change is pure-stdlib `dataclasses` introspection inside the
      contract package; it adds no command surface, no subprocess, no CLI flag,
      and no test-timeout behaviour. The only library claim is the stdlib
      `dataclasses.fields()` definition-order guarantee, which is pinned by the
      surviving literal tripwire (Work item 1). No cuprum catalogue, Cyclopts
      app, or uv-run path is touched.
      Date/Author: 2026-06-27, planning agent.

    - Decision: Work item 4 (the optional, gated consolidation) was APPLIED
      rather than skipped.
      Rationale: the decision rule said apply it if pointing each helper at
      `ENVELOPE_FIELD_ORDER` is a clean change that leaves both §6.3 guard suites
      green without touching their parsing or region logic. In each guard the
      imported `Envelope` symbol and `import dataclasses` were used *only* inside
      `_envelope_field_order()`, so the helper body became
      `return list(ENVELOPE_FIELD_ORDER)`, the two now-unused imports were
      dropped, and `ENVELOPE_FIELD_ORDER` imported in their place. No region or
      parsing logic changed; both §6.3 suites stayed green. This collapses the
      last two redundant derivations of the field-order projection onto the
      single canonical constant. The footprint (6 files, ~95 net lines across the
      four work items) stays within the Tolerances scope budget.
      Date/Author: 2026-06-27, implementation agent.

## Outcomes & retrospective

    - All four work items landed as four atomic commits, each gated by
      `make all` (build, check-fmt, lint, typecheck, test) and `coderabbit
      review --agent`. The single canonical home for the envelope field order is
      now `novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER`, derived
      from `dataclasses.fields(Envelope)`.
    - Single-source proof holds: a literal six-name sequence appears in exactly
      one place across the renderer and its oracles — the deliberate
      `_EXPECTED_FIELD_ORDER` tripwire in `tests/test_contract_envelope.py`. The
      renderer, the cross-command `ENVELOPE_KEY_ORDER` alias, and both §6.3
      drift-guard helpers now read the canonical constant.
    - No `.ambr` snapshot changed; the wire contract is byte-for-byte unchanged,
      as required by the Constraints. No interface signatures changed.
    - CodeRabbit raised two findings total, both against this ExecPlan markdown
      on Work item 1 (a 400-line-cap false positive and an intentional worktree
      path), neither an actionable code defect; recorded under Surprises &
      discoveries. Work items 2-4 drew zero findings.
    - Retrospective: the gated optional Work item 4 was worth taking — it was
      mechanical and removed the last two independent derivations, leaving the
      field order genuinely single-homed. No deviations from the plan's
      Constraints or Tolerances.

## Context and orientation

The reader needs no prior plan. The relevant files, by full repository-relative
path:

- `novel_ralph_skill/contract/envelope.py` — defines the `Envelope` frozen
  dataclass (lines 33-65), `build_envelope` (lines 68-123), `render_machine`
  (lines 126-151, the machine-mode JSON renderer), and `render_human`
  (lines 154-181). `render_machine` today builds a dict literal `ordered` whose
  module docstring claims the order is "asserted by this function rather than
  implied" — yet the function does not read the dataclass it renders. The
  `Envelope` dataclass declares the six fields in contract order:
  `command`, `schema_version`, `ok`, `working_dir`, `result`, `messages`.
  `__post_init__` freezes `result` to a read-only mapping and `messages` to a
  tuple via `novel_ralph_skill/_freeze.py` (`freeze_mapping`/`freeze_sequence`).

- `tests/test_contract_envelope.py` — unit and snapshot tests for the envelope.
  `_FIXED_FIELD_ORDER` (line 33) is a literal six-tuple;
  `test_render_machine_emits_fixed_field_order` (line 148) asserts
  `tuple(parsed) == _FIXED_FIELD_ORDER` after `json.loads(render_machine(env))`.
  The success and per-code snapshot tests (using `syrupy`) pin the rendered
  shape; their `.ambr` files live under `tests/__snapshots__/`.

- `tests/cross_command_contract/__init__.py` — the cross-command identity
  proof's package init. `ENVELOPE_KEY_ORDER` (line 81) is a second literal
  six-tuple, annotated `typ.Final[tuple[str, ...]]`.

- `tests/cross_command_contract/_identity_assertions.py` — `assert_envelope_skeleton`
  compares `tuple(envelope) == ENVELOPE_KEY_ORDER` (line 96) for every spaced
  command; this is the ~seven-site consumer that must keep working unchanged.

- `tests/test_skill_contract_drift_guard.py` (line 207) and
  `tests/test_developers_guide_contract_drift_guard.py` (line 139) each define a
  private `_envelope_field_order()` that returns
  `[field.name for field in dataclasses.fields(Envelope)]` — the 6.3.7-era
  derivation. These already read the dataclass; Work item 4 considers routing
  them through the new shared constant.

Term definitions:

- "field order" / "the six-name order": the fixed sequence
  `command, schema_version, ok, working_dir, result, messages` (design §3.1).
- "tripwire": a deliberately hand-written literal that a derived value is
  checked against, so an accidental change to the source of truth fails a test
  rather than silently propagating.
- "snapshot churn": a change that makes a `syrupy` `.ambr` snapshot file differ;
  here it would signal an unintended wire-format change (forbidden by
  Constraints).

## Plan of work

Four work items, each independently committable and gate-passable. Work items 1
through 3 are the roadmap's three-site scope; Work item 4 is an in-scope-adjacent
consolidation gated by the Tolerances.

### Work item 1 — Promote the shared `ENVELOPE_FIELD_ORDER` constant and the surviving tripwire

Docs to read first: design §3.1 (`docs/novel-ralph-harness-design.md`);
`docs/adr-003-shared-interface-contract.md` (§"Decision", the six-field
envelope); `docs/issues/audit-6.3.7.md` Finding 1 (the proposed fix this item
implements). Skills to load: `python-router`, then `python-data-shapes` (the
dataclass-introspection question is "derive a tuple from declaration order")
and `python-types-and-apis` (the `typ.Final[tuple[str, ...]]` public-constant
shape).

In `novel_ralph_skill/contract/envelope.py`, immediately after the `Envelope`
dataclass definition (after line 65), add a module-level public constant:

    # novel_ralph_skill/contract/envelope.py
    ENVELOPE_FIELD_ORDER: typ.Final[tuple[str, ...]] = tuple(
        field.name for field in dataclasses.fields(Envelope)
    )
    """The envelope's fixed contract field order, derived from Envelope.

    This is the single source of truth for the six-name order
    (command, schema_version, ok, working_dir, result, messages; design
    §3.1, ADR-003). render_machine and the contract and cross-command test
    oracles all read this rather than re-spelling the order, so a field
    added, dropped, renamed, or reordered in Envelope propagates to every
    consumer.
    """

Then, in `tests/test_contract_envelope.py`, replace the literal
`_FIXED_FIELD_ORDER` tuple (line 33) with the surviving *tripwire*: keep a
hand-written literal six-tuple, but rename and re-document it so its role as the
one deliberate human-readable anchor is explicit, and add a test pinning the
derived constant to it. Concretely, keep a local literal (e.g.
`_EXPECTED_FIELD_ORDER`) and add:

    # tests/test_contract_envelope.py
    from novel_ralph_skill.contract.envelope import ENVELOPE_FIELD_ORDER

    _EXPECTED_FIELD_ORDER = (
        "command",
        "schema_version",
        "ok",
        "working_dir",
        "result",
        "messages",
    )
    """The deliberate human-readable tripwire for the envelope field order.

    This literal is the one place the six-name order is spelled by hand. Do
    NOT delete it as "redundant": it pins the expected names so an accidental
    reorder of the Envelope dataclass reddens a test rather than silently
    propagating through the derived ENVELOPE_FIELD_ORDER (audit:6.3.7
    Finding 1).
    """


    def test_envelope_field_order_matches_expected() -> None:
        """The derived field order equals the hand-written tripwire."""
        assert ENVELOPE_FIELD_ORDER == _EXPECTED_FIELD_ORDER

Update `test_render_machine_emits_fixed_field_order` to assert against
`ENVELOPE_FIELD_ORDER` (the derived constant), so that test now proves the
renderer matches the dataclass-derived order, while the new tripwire test proves
the dataclass-derived order matches the expected names. Together they form a
spanning tree with the dataclass at the root.

Tests this item adds/updates:

- New unit test `test_envelope_field_order_matches_expected` (the tripwire).
- Updated `test_render_machine_emits_fixed_field_order` to read
  `ENVELOPE_FIELD_ORDER`.

No `hypothesis`, `crosshair`, or `mutmut` is warranted here: the order is a
fixed six-element constant, not an invariant over a range of inputs (AGENTS.md
"Use property tests ... when a change introduces an invariant over a range of
inputs"). A single example-based equality is the correct adversary; the
surviving literal is itself the falsifier for a dataclass reorder.

Validation: `make all` (build, check-fmt, lint, typecheck, test). Because this
plan file and no other markdown changed in this item, also run
`make markdownlint` and `make nixie` for the plan. Expect the new tripwire test
to pass and no snapshot change.

### Work item 2 — Derive `render_machine`'s ordered mapping from the dataclass

Docs to read first: design §3.1 (the wire envelope and its field semantics);
ADR-003 §"Decision"; `docs/scripting-standards.md` (return-shape and pure-helper
conventions). Skills to load: `python-router`, then
`python-iterators-and-generators` (the field-iterating comprehension) and
`python-data-shapes` (the dataclass-to-dict projection with per-field coercion).

In `novel_ralph_skill/contract/envelope.py`, rewrite `render_machine` (lines
126-151) so the ordered mapping is built by iterating `ENVELOPE_FIELD_ORDER`
(equivalently `dataclasses.fields(Envelope)`), pulling each value via `getattr`,
and applying an explicit per-field coercion so `result` becomes a plain `dict`
and `messages` a plain `list` exactly as today. For example:

    # novel_ralph_skill/contract/envelope.py
    _FIELD_COERCIONS: typ.Final[
        dict[str, cabc.Callable[[object], object]]
    ] = {
        "result": lambda v: dict(typ.cast("cabc.Mapping[str, object]", v)),
        "messages": lambda v: list(typ.cast("cabc.Sequence[str]", v)),
    }


    def render_machine(env: Envelope) -> str:
        """Render env as a single-line JSON object in the fixed field order.

        The ordered mapping is built by iterating ENVELOPE_FIELD_ORDER — the
        order declared on the Envelope dataclass — so the renderer cannot
        diverge from the contract it renders. result and messages are coerced
        to a plain dict/list so the frozen read-only containers serialize to
        the same JSON as before.
        ...
        """
        ordered: dict[str, object] = {}
        for name in ENVELOPE_FIELD_ORDER:
            value = getattr(env, name)
            coerce = _FIELD_COERCIONS.get(name)
            ordered[name] = coerce(value) if coerce is not None else value
        return json.dumps(ordered)

The exact spelling (a coercion map, or a small `match`/`if`) is an implementer
choice, but the *behaviour* is fixed: `result -> dict`, `messages -> list`,
every other field passed through, keys emitted in `ENVELOPE_FIELD_ORDER`. Update
the docstring so it no longer claims the order is "asserted by this function
rather than implied" — after this change the order is *read from the dataclass*,
which is stronger; the docstring must state that plainly. Cross-reference the
defining symbol via its module-qualified path
(`novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER`) per the §7.1
docstring convention (the convention task 7.1.6 settles; using the
defining-module path here keeps this consumer consistent with it ahead of time).

Tests this item adds/updates:

- No new test is strictly required because `test_render_machine_emits_fixed_field_order`
  (Work item 1) and the existing `syrupy` snapshot tests already pin the output
  order and the exact rendered bytes. Add one focused unit assertion that
  `render_machine` round-trips a representative envelope whose `result` is passed
  as a non-dict mapping and `messages` as a non-list sequence (e.g. a
  `MappingProxyType` and a tuple), proving the coercion still yields plain
  `dict`/`list` JSON. This is the regression test for the medium-severity
  coercion risk; place it beside the existing render tests.
- Confirm no `.ambr` snapshot changes (Constraints): the snapshot suite is the
  behavioural guard for this item.

Validation: `make all`. Expect every existing snapshot to match unchanged and
the new coercion regression test to pass.

### Work item 3 — Import the shared constant into both test oracles

Docs to read first: `tests/cross_command_contract/__init__.py` module docstring
(the cross-command identity proof, design §3.1/§3.2, ADR-003 Table 2);
`tests/cross_command_contract/_identity_assertions.py` (the consumer). Skills to
load: `python-router`, then `python-testing` (fixture and oracle hygiene) and
`python-types-and-apis` (preserving the `typ.Final[tuple[str, ...]]` annotation).

In `tests/cross_command_contract/__init__.py`, delete the literal
`ENVELOPE_KEY_ORDER` six-tuple (line 81) and replace it with a re-export of the
shared constant under the same name and annotation, so the ~seven consumers in
`_identity_assertions.py` keep working unchanged:

    # tests/cross_command_contract/__init__.py
    from novel_ralph_skill.contract.envelope import ENVELOPE_FIELD_ORDER

    # The six contract-fixed envelope keys, in the order render_machine emits
    # them (result before messages; ADR-003, design §3.1), re-exported from
    # the canonical novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER
    # so this package carries no second copy of the order.
    ENVELOPE_KEY_ORDER: typ.Final[tuple[str, ...]] = ENVELOPE_FIELD_ORDER

Keep the name `ENVELOPE_KEY_ORDER` (it is referenced by string in
`tests/test_novel_state_check.py:333` prose and imported by
`_identity_assertions.py`), so this is a single-line aliasing change, not a
rename.

In `tests/test_contract_envelope.py`, the literal removal already happened in
Work item 1 (the old `_FIXED_FIELD_ORDER` was replaced by the tripwire plus the
derived-constant import). Confirm no module under the renderer-and-oracle scope
still spells the six-name order outside the single surviving tripwire.

Tests this item adds/updates:

- No new behavioural test: the existing cross-command identity suite
  (`tests/cross_command_contract/`) is the behavioural guard. It drives all five
  spaced commands in-process and asserts `tuple(envelope) == ENVELOPE_KEY_ORDER`;
  re-pointing the alias at the canonical constant must leave that suite green.
- Add or extend one assertion (in `tests/test_contract_envelope.py` or the
  cross-command package's own unit coverage) that `ENVELOPE_KEY_ORDER is
  ENVELOPE_FIELD_ORDER` (identity, not just equality), pinning that the alias is
  a re-export and cannot silently re-fork into a second literal.

Validation: `make all`. Expect the full cross-command identity suite green and
the new identity assertion green.

### Work item 4 — Route the two drift-guard helpers through the shared constant (optional, gated)

Docs to read first: `docs/issues/audit-6.3.7.md` Finding 1 (scope note: the
audit names exactly the three sites above); the roadmap 7.1.5 entry (its three
named sites). Skills to load: `python-router`, then `python-testing`.

The two existing drift-guards each carry a private `_envelope_field_order()` that
re-derives `[field.name for field in dataclasses.fields(Envelope)]`
(`tests/test_skill_contract_drift_guard.py:207`;
`tests/test_developers_guide_contract_drift_guard.py:139`). These already read
the dataclass, so they are not a *hand-spelled* copy of the order — they are a
second *derivation* of the same projection. The roadmap's three-site scope does
not include them, and the §6.3 drift-guards are settled.

Decision rule for this item:

- If pointing each helper at `ENVELOPE_FIELD_ORDER` (returning
  `list(ENVELOPE_FIELD_ORDER)`) is a clean one-line change per file that leaves
  both §6.3 guard suites green and does not touch the guards' parsing or region
  logic, do it: it collapses the two redundant derivations onto the canonical
  constant and removes the last places the field-order projection is computed
  outside its home.
- If it would churn the §6.3 guards, change their public surface, or risk the
  settled documentation hypothesis, **do not** do it. Record in the Decision Log
  that the two helpers are left as independent derivations because they read the
  same canonical dataclass and the roadmap scopes 7.1.5 to the renderer and its
  two oracles only.

Tests this item adds/updates:

- If applied: no new test; the existing §6.3 drift-guard suites
  (`tests/test_skill_contract_drift_guard.py`,
  `tests/test_developers_guide_contract_drift_guard.py`) are the behavioural
  guards and must stay green.
- If skipped: no code change; the Decision Log entry is the artefact.

Validation: `make all`. Expect both §6.3 drift-guard suites green either way.

## Concrete steps

Run everything from the worktree root
`/data/leynos/Projects/novel-ralph-skill.worktrees/roadmap-7-1-5`.

1. Confirm a clean baseline:

       # working dir: repo root
       git status --short
       make test

   Expect no pending changes and a green suite.

2. Work item 1: add `ENVELOPE_FIELD_ORDER` to `envelope.py`; add the tripwire
   and its test to `tests/test_contract_envelope.py`; repoint
   `test_render_machine_emits_fixed_field_order` at the derived constant. Then:

       make all
       git add -A && git commit

   Use a file-based commit message (see `commit-message` skill); never `-m`.
   Expect `make all` green; the new tripwire test passes; no `.ambr` diff.

3. Work item 2: rewrite `render_machine` to iterate `ENVELOPE_FIELD_ORDER` with
   explicit `result`/`messages` coercion; update its docstring; add the coercion
   regression test. Then `make all` and commit. Expect every snapshot unchanged.

4. Work item 3: alias `ENVELOPE_KEY_ORDER = ENVELOPE_FIELD_ORDER` in the
   cross-command package init; add the identity assertion. Then `make all` and
   commit. Expect the cross-command identity suite green.

5. Work item 4: apply or skip per the decision rule; update the Decision Log;
   `make all`; commit (or record the skip in the plan and commit the plan
   update).

6. After each plan edit, validate the markdown:

       make markdownlint
       make nixie

   Expect no lint findings and no Mermaid errors (this plan has no diagrams, so
   `nixie` is a no-op pass).

## Validation and acceptance

Quality criteria (what "done" means):

- Tests: `make test` passes. The new tripwire test
  `test_envelope_field_order_matches_expected` fails if the `Envelope` dataclass
  is reordered without updating the literal (verify once by temporarily swapping
  two fields and observing the red, then revert). The coercion regression test
  passes. The cross-command identity suite and the contract envelope suite stay
  green. No `.ambr` snapshot changes.
- Lint/typecheck: `make lint` (Ruff + 100% docstring coverage) and
  `make typecheck` (pyright/mypy per the repo config) pass. The new public
  constant and any helper carry docstrings.
- Markdown (this plan): `make markdownlint` and `make nixie` pass.
- Single-source proof: `grep -rn` for the literal six-name sequence across
  `novel_ralph_skill/contract/envelope.py`,
  `tests/test_contract_envelope.py`, and
  `tests/cross_command_contract/__init__.py` finds it in exactly one place — the
  surviving tripwire in `tests/test_contract_envelope.py`.

Quality method (how we check):

- `make all` is the single gate per work item (build, check-fmt, lint,
  typecheck, test). Run it before each commit (AGENTS.md "Run all code commit
  gateways ... prior to committing").
- The behaviour proof is the unchanged snapshot suite plus the unchanged
  cross-command identity suite: both render the real envelope and would redden
  on any wire-format or order regression.

## Idempotence and recovery

Every step is a small, self-contained edit followed by `make all` and a commit,
so each work item is independently re-runnable. If a step half-applies, `git
diff` shows the partial edit; revert with `git checkout -- <file>` and re-apply.
No step is destructive: there are no migrations, no generated artefacts, and no
file deletions beyond replacing two in-module literal tuples with imports. If a
snapshot unexpectedly changes, do not `--snapshot-update`; stop and escalate
(Constraints), because a snapshot change here means a real contract regression.

## Artefacts and notes

The load-bearing before/after is the `render_machine` body. Before (today,
`envelope.py` lines 143-151):

    # novel_ralph_skill/contract/envelope.py (before)
    ordered: dict[str, object] = {
        "command": env.command,
        "schema_version": env.schema_version,
        "ok": env.ok,
        "working_dir": env.working_dir,
        "result": dict(env.result),
        "messages": list(env.messages),
    }
    return json.dumps(ordered)

After (Work item 2): the same JSON, but the key order and field set are read
from `ENVELOPE_FIELD_ORDER` (itself `tuple(f.name for f in
dataclasses.fields(Envelope))`), with `result`/`messages` coerced as before.

## Interfaces and dependencies

Only the stdlib `dataclasses` module is used (already imported in
`novel_ralph_skill/contract/envelope.py`). No external library is added or
relied upon for behaviour; cuprum, Cyclopts, pytest-timeout, and uv are not
involved in this change (Decision Log). The one stdlib behavioural guarantee —
`dataclasses.fields()` returns fields in definition order — is pinned by the
surviving literal tripwire test (Work item 1).

At the end of this work the following symbols must exist:

- `novel_ralph_skill.contract.envelope.ENVELOPE_FIELD_ORDER`, annotated
  `typ.Final[tuple[str, ...]]` — the single canonical field order, derived from
  `dataclasses.fields(Envelope)`.
- `novel_ralph_skill.contract.envelope.render_machine(env: Envelope) -> str`
  — unchanged signature; body now iterates `ENVELOPE_FIELD_ORDER`.
- `tests/cross_command_contract.ENVELOPE_KEY_ORDER` — re-export alias of
  `ENVELOPE_FIELD_ORDER`, same `typ.Final[tuple[str, ...]]` annotation.
- The surviving literal tripwire and its equality test in
  `tests/test_contract_envelope.py`.

## Addenda (post-merge follow-ups)

Lightweight addendum work items folded back onto this completed task from the
reviews and audits of step 7.1's tasks. Execute each as a small addendum pass —
no plan or design-review cycle: make the change, run `make all` (plus `make
markdownlint`/`make nixie` for Markdown), `coderabbit review --agent`, commit,
and tick the matching roadmap sub-task on merge.

- [x] 7.1.5.1 — Register this envelope field-order projection as a row in the
  §7.1 projection-docstring drift guard (from review:7.1.6, audit:7.1.6; low;
  two near-identical proposals merged). Task 7.1.6 authored
  `tests/test_projection_docstring_drift_guard.py` as an extensible registry and
  deliberately deferred 7.1.5's row to "when 7.1.5 lands" (its Decision Log: the
  guard must not import `ENVELOPE_FIELD_ORDER` while 7.1.5 was unmerged). Now that
  7.1.5 has merged, add the `(authoritative, consumers, canonical_path,
  reexport_tail, table_markers)` row binding `ENVELOPE_FIELD_ORDER`
  (authoritative) to its consumers (`render_machine` and the two test oracles) so
  the envelope field-order consolidation is enforced by the guard rather than
  merely conventionally documented. `render_machine` already cross-references
  `ENVELOPE_FIELD_ORDER` via the defining-module path, so no docstring rewrite is
  needed; this is the registry-row addition alone. Gate with `make all`.

  Implementation note (addendum pass). The guard reads `symbol.__doc__`, but
  `ENVELOPE_FIELD_ORDER` is a module-level tuple whose runtime `__doc__` is the
  built-in tuple docstring, not its PEP 224 attribute docstring, so it cannot
  carry the field-order table the marker assertion checks. The row therefore
  keys `authoritative` to the `Envelope` dataclass — the single source
  `ENVELOPE_FIELD_ORDER` is derived from, whose docstring already enumerates the
  six fields and so needs no rewrite — exactly as
  `test_developers_guide_contract_drift_guard.py` keys its field set off the
  imported `Envelope` by symbol identity. `canonical_path` is the
  `ENVELOPE_FIELD_ORDER` dotted path the three consumers (`render_machine` and
  the contract and cross-command oracles) cite, and `reexport_tail` is the
  `contract`-package façade (`novel_ralph_skill.contract.ENVELOPE_FIELD_ORDER`)
  that bypasses the defining `.envelope` module; it is not a substring of
  `canonical_path`, keeping the tail check non-vacuous on the green tree. The
  contract-side oracle gained a one-sentence canonical cross-reference in its
  docstring (a test-only edit, not a production change) so it satisfies the
  consumer cross-reference assertion. The two oracle functions are imported under
  non-`test_` aliases so pytest does not re-collect them.
