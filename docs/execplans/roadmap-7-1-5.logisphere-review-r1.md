# Logisphere design review — ExecPlan roadmap-7-1-5 (round 1)

Verdict: PROCEED (no blocking defects). The plan is implementable and
design-conformant as written. Findings below are advisory (🟢/💡) only.

Reviewer: adversarial Logisphere crew, round 1. Every load-bearing claim in the
plan was checked against real source in this worktree (and the requires-python
3.14 `dataclasses.fields()` ordering verified empirically); nothing was taken on
the planner's word.

## Verification log (claims checked against source)

- `render_machine` dict literal at envelope.py:143-151; `result`/`messages`
  frozen by `_freeze.py` (`MappingProxyType` + `tuple`) — accurate. The
  `dict()`/`list()` coercion is genuinely load-bearing.
- `_FIXED_FIELD_ORDER` at test_contract_envelope.py:33, referenced only at
  line 165 (`tuple(parsed) == _FIXED_FIELD_ORDER`) — safe to rename/replace.
- `ENVELOPE_KEY_ORDER` at cross_command_contract/__init__.py:81, annotated
  `typ.Final[tuple[str, ...]]`, compared `== tuple(envelope)` at
  `_identity_assertions.py:96` — accurate; a tuple alias preserves both.
- Drift guards `_envelope_field_order()` at test_skill_contract_drift_guard.py
  :207/:209 and test_developers_guide_contract_drift_guard.py:139/:141 already
  derive from `dataclasses.fields(Envelope)` — accurate; Work item 4's "second
  derivation, not hand-spelled" framing is correct.
- String reference at test_novel_state_check.py:333 is a docstring mention of
  `ENVELOPE_KEY_ORDER`; the plan preserves the name, so no breakage.
- audit-6.3.7 Finding 1 + roadmap 7.1.5 + roadmap 7.1.6 cross-checked: the
  three-site scope, the "exactly one literal tripwire" success criterion, and
  the "derive render_machine by iterating dataclass fields" instruction all
  match. The audit lives at docs/issues/audit-6.3.7.md (path the plan cites).
- `requires-python >=3.14`; `dataclasses.fields()` returns declaration order
  (not alphabetical) — verified empirically.
- The proposed `_FIELD_COERCIONS` constant uses `cabc.Callable`/`typ.cast` even
  though `cabc` is TYPE_CHECKING-only in envelope.py. Verified empirically: under
  `from __future__ import annotations` the variable annotation is a lazy string
  and `typ.cast("...", v)` never evaluates its first arg, so the module imports
  and the lambdas execute at runtime. NOT a defect.
- AGENTS.md citations accurate: 400-line cap (line 24), en-GB Oxford spelling
  (line 19), property-test-when-invariant-over-a-range guidance (lines 162-163).
  The plan's justification for skipping hypothesis/crosshair/mutmut is sound.
- interrogate `fail-under=100` but does not gate module-level constants; the
  plan adds the constant docstring anyway (matches `ENVELOPE_SCHEMA_VERSION`'s
  existing post-assignment-docstring style). Harmless.

## Findings

### 🟢 Pandalump (structural) — spanning tree is sound

The four-way pin collapses to a spanning tree rooted at the dataclass:
`Envelope` declaration -> `ENVELOPE_FIELD_ORDER` (derived) -> render_machine,
`_FIXED_FIELD_ORDER` replacement, `ENVELOPE_KEY_ORDER` alias; with one
hand-spelled `_EXPECTED_FIELD_ORDER` tripwire pinning the names. No cycle, no
orphan. The decision to keep one literal tripwire (so a derived-vs-derived
comparison cannot pass vacuously after a reorder) is the correct structural
call and matches the audit's proposed fix verbatim.

### 🟢 Telefono (contracts) — wire contract preserved, alias is type-stable

The alias re-export keeps `ENVELOPE_KEY_ORDER` a `tuple[str, ...]` with the
`typ.Final` annotation, so the `== tuple(envelope)` comparison and the string
docstring mention both survive. The added `is`-identity assertion
(`ENVELOPE_KEY_ORDER is ENVELOPE_FIELD_ORDER`) is a genuinely stronger guard than
equality and forecloses a silent re-fork. Good contract hygiene.

### 🟢 Doggylump (failure modes) — snapshot guard is the right safety net

Iterating `ENVELOPE_FIELD_ORDER` yields the identical key order and the explicit
coercion preserves `dict`/`list`, so the `.ambr` snapshots and the cross-command
identity suite are byte-for-byte unchanged. The "if any snapshot changes, stop
and escalate, do not --snapshot-update" rule is exactly the right tripwire for
the one real failure mode (an accidental wire regression). The added coercion
regression test (passing a `MappingProxyType`/tuple through render_machine) is a
well-targeted guard for the medium-severity coercion risk.

### 🟢 Buzzy Bee / Dinolump — scale and viability are non-issues

Pure-stdlib, single source file plus two test files, ~120-line ceiling. No
runtime cost, no new dependency, no operational surface. The change strictly
reduces maintenance toil (one-line dataclass edit vs four-way hand-edit). Nothing
to flag.

### 💡 Wafflecat (alternatives checkpoint)

Strongest alternative considered: derive *every* assertion from the dataclass and
drop the literal tripwire entirely (a "fully derived" design). The plan correctly
rejects this in its Decision Log — a fully-derived test passes vacuously after an
accidental reorder because both sides move together, and the roadmap success
criterion explicitly requires "exactly one literal tripwire survives". No
credible alternative beats the proposed design on the stated criteria. This is a
strong signal the design is on solid ground.

### 💡 Pre-mortem (advisory, not blocking)

1. *Most likely failure:* an implementer "simplifies" render_machine to a blanket
   `getattr` loop without the per-field coercion, shipping `MappingProxyType`
   into `json.dumps`. Mitigation already designed in: the snapshot suite + the
   new coercion regression test redden. Adequate.
2. *Second failure:* a future contributor deletes the `_EXPECTED_FIELD_ORDER`
   tripwire as "redundant". Mitigation already designed in: the tripwire's
   docstring states it must not be deleted. Adequate.

## Advisory items for the planner (non-blocking; address if cheap)

1. (💡, low) Work item 2 instructs cross-referencing `ENVELOPE_FIELD_ORDER` via
   the §7.1 defining-module-path docstring convention "ahead of" task 7.1.6,
   which is the task that *settles* that convention and its drift-guard. 7.1.5
   "Requires 6.3.7" only, and 7.1.6 "Requires 7.1.2, 7.1.3, 7.1.4" (not 7.1.5),
   so there is no hard ordering conflict — but the plan is pre-committing to a
   convention 7.1.6 may finalize differently, and 7.1.6 explicitly says it will
   "apply the convention and guard to 7.1.5". Recommend the planner either (a)
   note in the Decision Log that any 7.1.6 convention delta will be reconciled
   when 7.1.6 lands, or (b) keep the Work-item-2 cross-reference minimal so 7.1.6
   has nothing to rewrite. Purely a forward-compatibility nicety.

2. (💡, low) The Constraints bullet claims interrogate "enforces" a docstring on
   the new `ENVELOPE_FIELD_ORDER` *constant*. interrogate does not gate
   module-level assignments (only modules/classes/functions/methods), so the
   constant docstring is house-style, not a hard gate. Cosmetic wording only; the
   plan correctly adds the docstring regardless.

3. (🟢, low) Work item 4's decision rule is sound, but note the two drift-guard
   helpers return `list[str]` while `ENVELOPE_FIELD_ORDER` is a `tuple`. If
   applied, `list(ENVELOPE_FIELD_ORDER)` (as the plan already specifies) keeps the
   `list[str]` return type stable for the `==` comparisons in those guards. The
   plan already says exactly this; flagged only so the implementer does not return
   the tuple directly and break the guards' list comparisons.

## Conclusion

No blocking defects. The plan's work items are atomic, correctly ordered (each
independently committable behind `make all`), testable (snapshot + identity +
tripwire + coercion-regression coverage named per item), and complete against the
audit and roadmap scope. Validation is specified per work item. Nothing
contradicts the deterministic wire contract, the frozen-container invariant, or
the established `tuple`-typed oracle contracts. Safe to implement as written; the
three advisory items are optional polish.
