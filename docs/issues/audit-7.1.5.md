# Post-merge audit — roadmap task 7.1.5

Audit of the codebase after task 7.1.5 ("Derive the envelope field order from the
`Envelope` dataclass across the renderer, the cross-command oracle, and the
prose drift guards") merged to `main` at commit `1441ff1`. The task promoted a
derived `ENVELOPE_FIELD_ORDER` constant
(`novel_ralph_skill/contract/envelope.py`) sourced from
`dataclasses.fields(Envelope)`, routed `render_machine` and the test oracles
through it, re-exported `ENVELOPE_KEY_ORDER`
(`tests/cross_command_contract/__init__.py`) from that constant, and pointed the
SKILL.md and developers'-guide drift guards at the same order with a tripwire
that fails if the dataclass and the declared order diverge.

The merged change is clean and well-pinned: the renderer, the cross-command
identity oracle, and both prose drift guards now share one canonical field
order, and the re-export identity is itself tested
(`tests/cross_command_contract/test_envelope_shape.py:148`,
`assert ENVELOPE_KEY_ORDER is ENVELOPE_FIELD_ORDER`). The findings below are
maintainability and consistency opportunities surfaced while auditing the 7.1.5
blast radius; none is a correctness defect.

The exploration used `leta` for code navigation and `sem`/`git show` for history
tracing. The sources of truth consulted were `docs/novel-ralph-harness-design.md`
(§3.1 envelope contract), `docs/adr-003-shared-interface-contract.md`, and the
existing audit issues under `docs/issues/`. Prose follows the en-GB Oxford
spelling convention (`AGENTS.md`).

## Finding 1 — Duplicated `_meaning_has_keyword` helper across both drift guards

- **Category:** duplication
- **Severity:** low
- **Location:** `tests/test_skill_contract_drift_guard.py:203-206` and
  `tests/test_developers_guide_contract_drift_guard.py:135-138`

The `_meaning_has_keyword(meaning, keywords)` helper — a four-line
case-insensitive keyword presence check over an exit-code Meaning cell — is
byte-identical in both drift-guard modules (verified with `diff`). The
duplication predates 7.1.5 (it arrived with the developers'-guide guard at
6.3.9), but 7.1.5 is the natural moment to fold it away, because the same commit
consolidated the *other* shared anchor (the field order) into a single source of
truth and left this one un-deduplicated. Both modules already import their
markdown-parsing helpers from the shared pure sibling
`tests/_skill_contract_scanner.py`.

A future wording or matching-semantics change (for example, switching to
whole-word matching, or normalizing punctuation) would have to be made in two
places, and a drift between the two copies would silently weaken one guard.

**Proposed fix:** Move `_meaning_has_keyword` into
`tests/_skill_contract_scanner.py` (it is pure string logic with no contract-
module dependency, so it belongs beside `extract_exit_code_meanings`) and import
it in both guard modules, exactly as they already import
`extract_exit_code_meanings` and `parse_markdown_table`. Add one focused unit
test for it under `TestDevelopersGuideContractScanner` /
`TestSkillContractScanner` so the relocated helper is directly exercised.

## Finding 2 — `_envelope_field_order()` wrappers are now redundant indirection

- **Category:** ergonomics
- **Severity:** low
- **Location:** `tests/test_skill_contract_drift_guard.py:209-218` and
  `tests/test_developers_guide_contract_drift_guard.py:141-150`

After 7.1.5 both `_envelope_field_order()` helpers collapsed to a one-line
`return list(ENVELOPE_FIELD_ORDER)` over an already-public canonical constant.
Before 7.1.5 each helper carried load-bearing logic — it called
`dataclasses.fields(Envelope)` and was the local point that derived the order —
so the wrapper earned its place. Now the wrapper only re-spells a public
constant behind a private name and a five-line docstring, duplicated across both
modules. This is indirection without abstraction: a reader must follow the
helper to discover it does nothing but `list(...)` the imported constant.

**Proposed fix:** Delete both `_envelope_field_order()` helpers and reference
`list(ENVELOPE_FIELD_ORDER)` directly at the (few) call sites
(`test_guide_envelope_fields_match_dataclass`,
`test_regions_are_non_empty`, and the SKILL twin), or introduce a single
module-level `EXPECTED_ENVELOPE_FIELDS = list(ENVELOPE_FIELD_ORDER)` constant per
module if a named binding is preferred. This removes the duplicated docstring
and the layer of indirection while keeping the single-source-of-truth coupling
that 7.1.5 established. If the helper is retained for symmetry, the two copies
should be consolidated (see Finding 1's pattern) rather than maintained twice.

## Finding 3 — `render_human` field selection is undocumented as a deliberate divergence from `ENVELOPE_FIELD_ORDER`

- **Category:** docs-gap
- **Severity:** low
- **Location:** `novel_ralph_skill/contract/envelope.py:181-208` (`render_human`)

7.1.5 routed `render_machine` through `ENVELOPE_FIELD_ORDER` so it provably
cannot diverge from the dataclass. Its sibling `render_human` deliberately
emits a *different, hand-spelled* subset — `command`, `ok`, `working_dir`,
`messages` — omitting `schema_version` and `result`. The function docstring
explains why `result` is omitted (it is the machine channel) but does not
mention that `schema_version` is also omitted, and the human renderer is the one
envelope consumer that 7.1.5's single-source-of-truth guarantee does *not* cover:
adding a seventh field to `Envelope` updates `render_machine` automatically but
silently leaves `render_human` stale, with no drift guard.

**Proposed fix:** Tighten the `render_human` docstring to state explicitly that
it surfaces a curated human subset (`command`, `ok`, `working_dir`, `messages`)
and omits `schema_version` and `result` by design, so a future reader does not
mistake the omission for a bug. Optionally, add a small unit assertion that the
human-rendered line set is the intended subset of `ENVELOPE_FIELD_ORDER`, so a
renamed field surfaces in the human channel rather than vanishing silently.

## Finding 4 — Several command/state modules sit one or two lines under the 400-line cap

- **Category:** complexity
- **Severity:** low
- **Location:** `novel_ralph_skill/commands/_gate_drafting_mutators.py` (399
  lines), `novel_ralph_skill/rulepack/parse.py` (392),
  `novel_ralph_skill/commands/_desloppify.py` (389)

`AGENTS.md` imposes a 400-line per-file cap. Three modules are within a handful
of lines of it, so the next routine change (a new parameter, an extra docstring
paragraph, a new branch) will breach the cap and force an unplanned split mid-
task. This is outside the 7.1.5 blast radius but is a standing maintainability
risk worth flagging for the roadmap rather than fixing reactively under time
pressure.

**Proposed fix:** Pre-emptively identify a natural seam in each of the three
near-cap modules (for example, extracting the pure validation helpers from
`_gate_drafting_mutators.py` into a sibling, mirroring the established
`_skill_contract_scanner.py` split pattern) so the split is a deliberate design
decision rather than a forced reaction. Track as a low-priority roadmap item, not
an immediate fix.
